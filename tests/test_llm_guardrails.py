"""
Tests for LLM guardrail behaviour:
  - Schema validation of LLM output (Literal enums, max_length)
  - Per-user daily quota enforcement
  - Quota fallback returns the correct safe dict shape
  - Exempt callers (api_key / admin) bypass quota
  - generate_explanation with no db (backward-compatible: no quota check)
"""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from backend.app.schemas.prediction import LLMExplanation
from backend.app.services.explainer import (
    _QUOTA_FALLBACK,
    _SAFE_FALLBACK,
    _check_and_increment,
    _resolve_quota_limit,
    _validate_output,
    generate_explanation,
)


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------
class TestLLMExplanationSchema:
    def test_valid_payload_passes(self):
        obj = LLMExplanation(
            summary="Fine property.",
            opportunity="Good upside.",
            risks="Market risk.",
            recommendation="Buy",
            confidence="High",
        )
        assert obj.recommendation == "Buy"
        assert obj.confidence == "High"

    def test_invalid_recommendation_raises(self):
        with pytest.raises(ValidationError):
            LLMExplanation(
                summary="s",
                opportunity="o",
                risks="r",
                recommendation="approach cautiously",
                confidence="Low",
            )

    def test_invalid_confidence_raises(self):
        with pytest.raises(ValidationError):
            LLMExplanation(
                summary="s",
                opportunity="o",
                risks="r",
                recommendation="Hold",
                confidence="medium",  # wrong case
            )

    def test_summary_max_length_enforced(self):
        with pytest.raises(ValidationError):
            LLMExplanation(
                summary="x" * 601,
                opportunity="o",
                risks="r",
                recommendation="Hold",
                confidence="Low",
            )


# ---------------------------------------------------------------------------
# _validate_output
# ---------------------------------------------------------------------------
class TestValidateOutput:
    def test_valid_dict_passes_through(self):
        raw = {
            "summary": "Good.",
            "opportunity": "Upside.",
            "risks": "None.",
            "recommendation": "Buy",
            "confidence": "High",
        }
        result = _validate_output(raw)
        assert result["recommendation"] == "Buy"

    def test_invalid_recommendation_returns_fallback(self):
        raw = {
            "summary": "Good.",
            "opportunity": "Upside.",
            "risks": "None.",
            "recommendation": "approach cautiously",
            "confidence": "High",
        }
        result = _validate_output(raw)
        assert result == _SAFE_FALLBACK

    def test_empty_dict_returns_fallback(self):
        result = _validate_output({})
        assert result == _SAFE_FALLBACK

    def test_wrong_confidence_case_returns_fallback(self):
        raw = {
            "summary": "s",
            "opportunity": "o",
            "risks": "r",
            "recommendation": "Hold",
            "confidence": "MEDIUM",
        }
        result = _validate_output(raw)
        assert result == _SAFE_FALLBACK


# ---------------------------------------------------------------------------
# _resolve_quota_limit
# ---------------------------------------------------------------------------
class TestResolveQuotaLimit:
    def test_api_key_caller_is_exempt(self):
        assert _resolve_quota_limit("admin", "api_key") is None

    def test_admin_jwt_caller_is_exempt(self):
        assert _resolve_quota_limit("admin", "jwt") is None

    def test_free_user_gets_free_quota(self):
        limit = _resolve_quota_limit("user", "jwt")
        assert limit is not None
        assert limit > 0

    def test_paid_user_gets_higher_quota(self):
        free_limit = _resolve_quota_limit("user", "jwt")
        paid_limit = _resolve_quota_limit("paid", "jwt")
        assert paid_limit > free_limit


# ---------------------------------------------------------------------------
# _check_and_increment  (uses an in-memory SQLite session)
# ---------------------------------------------------------------------------
@pytest.fixture()
def db_session():
    """Create a fresh in-memory SQLite session with the llm_usage table."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.app.db.database import Base
    from backend.app.db.models import LLMUsage  # noqa: F401

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


class TestCheckAndIncrement:
    def test_first_call_allowed(self, db_session):
        assert _check_and_increment(db_session, "user-1", limit=5) is True

    def test_count_increments(self, db_session):
        _check_and_increment(db_session, "user-2", limit=5)
        _check_and_increment(db_session, "user-2", limit=5)
        from backend.app.db.models import LLMUsage
        row = db_session.query(LLMUsage).filter_by(user_id="user-2").first()
        assert row.call_count == 2

    def test_quota_exceeded_returns_false(self, db_session):
        for _ in range(3):
            _check_and_increment(db_session, "user-3", limit=3)
        # 4th call should be denied
        assert _check_and_increment(db_session, "user-3", limit=3) is False

    def test_different_users_have_independent_buckets(self, db_session):
        for _ in range(2):
            _check_and_increment(db_session, "user-a", limit=2)
        # user-a is at limit
        assert _check_and_increment(db_session, "user-a", limit=2) is False
        # user-b is unaffected
        assert _check_and_increment(db_session, "user-b", limit=2) is True


# ---------------------------------------------------------------------------
# generate_explanation  (mocks OpenAI; verifies quota and fallback paths)
# ---------------------------------------------------------------------------
GOOD_LLM_RESPONSE = {
    "summary": "Strong upside.",
    "opportunity": "Undervalued.",
    "risks": "Market volatility.",
    "recommendation": "Buy",
    "confidence": "High",
}

DATA = {
    "predicted_price": 650000,
    "market_price": 500000,
    "roi_estimate": 30.0,
    "investment_score": 80,
    "top_drivers": ["Location", "Size"],
}


class TestGenerateExplanation:
    def test_no_db_skips_quota_and_returns_valid(self):
        """Backward-compatible path: no db → quota not checked, LLM called."""
        mock_response = MagicMock()
        mock_response.output_text = '{"summary":"Good.","opportunity":"Up.","risks":"None.","recommendation":"Buy","confidence":"High"}'

        with patch("backend.app.services.explainer._get_openai_client") as mock_client:
            instance = MagicMock()
            instance.responses.create.return_value = mock_response
            mock_client.return_value = instance

            result = generate_explanation(DATA)

        assert result["recommendation"] == "Buy"

    def test_free_user_within_quota_calls_llm(self, db_session):
        mock_response = MagicMock()
        mock_response.output_text = '{"summary":"Good.","opportunity":"Up.","risks":"None.","recommendation":"Hold","confidence":"Medium"}'

        with patch("backend.app.services.explainer._get_openai_client") as mock_client:
            instance = MagicMock()
            instance.responses.create.return_value = mock_response
            mock_client.return_value = instance

            result = generate_explanation(
                DATA, user_id="uid-free", role="user", auth_method="jwt", db=db_session
            )

        assert result["recommendation"] == "Hold"

    def test_free_user_over_quota_returns_quota_fallback(self, db_session):
        # Exhaust the quota
        with patch.dict(os.environ, {"LLM_QUOTA_FREE": "2"}):
            import importlib
            import backend.app.services.explainer as exp_mod
            importlib.reload(exp_mod)

            for _ in range(2):
                exp_mod._check_and_increment(db_session, "uid-quota", limit=2)

            result = exp_mod.generate_explanation(
                DATA, user_id="uid-quota", role="user", auth_method="jwt", db=db_session
            )

        assert result["summary"].startswith("Daily AI explanation quota reached")

    def test_api_key_caller_bypasses_quota(self, db_session):
        mock_response = MagicMock()
        mock_response.output_text = '{"summary":"Good.","opportunity":"Up.","risks":"None.","recommendation":"Avoid","confidence":"Low"}'

        with patch("backend.app.services.explainer._get_openai_client") as mock_client:
            instance = MagicMock()
            instance.responses.create.return_value = mock_response
            mock_client.return_value = instance

            result = generate_explanation(
                DATA, user_id=None, role="admin", auth_method="api_key", db=db_session
            )

        assert result["recommendation"] == "Avoid"

    def test_llm_returns_invalid_output_falls_back(self, db_session):
        mock_response = MagicMock()
        mock_response.output_text = '{"summary":"G.","opportunity":"U.","risks":"N.","recommendation":"maybe","confidence":"sort of"}'

        with patch("backend.app.services.explainer._get_openai_client") as mock_client:
            instance = MagicMock()
            instance.responses.create.return_value = mock_response
            mock_client.return_value = instance

            result = generate_explanation(
                DATA, user_id="uid-bad", role="user", auth_method="jwt", db=db_session
            )

        assert result == _SAFE_FALLBACK

    def test_llm_unavailable_returns_safe_fallback(self):
        with patch("backend.app.services.explainer._get_openai_client", return_value=None):
            result = generate_explanation(DATA)
        assert result == _SAFE_FALLBACK
