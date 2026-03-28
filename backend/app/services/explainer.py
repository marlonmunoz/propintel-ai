import json
import os
from openai import OpenAI

def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        return None
    
    return OpenAI(api_key=api_key)


def build_prompt(data: dict) -> str:
    drivers = data.get("top_drivers", [])
    drivers_text = ", ".join(drivers) if drivers else "No key drivers identified"
    return f"""
You are a senior real estate investment analyst working at a top-tier investment firm.

Your job is to evaluate property investment opportunities using quantitative model outputs and provide clear, professional, and data-driven insights.

--- PROPERTY DATA ---
Predicted Price: {data['predicted_price']}
Market Price: {data['market_price']}
ROI Estimate: {data['roi_estimate']}%
Investment Score: {data['investment_score']}

Score Interpretation Guide:
- 0 to 20 = Very weak investment profile
- 21 to 40 = Weak / speculative
- 41 to 60 = Mixed / moderate
- 61 to 80 = Strong
- 81 to 100 = Excellent

Key Drivers:
{drivers_text}

--- OUTPUT FORMAT (STRICT JSON FORMAT) ---
{{
    "summary": "Clear 1-2 sentence investment conclusion",
    "opportunity": "Specific upside potential and why it exists",
    "risks": "Concrete risks or uncertainties that could impact returns",
    "recommendation": "Buy, Hold, or Avoid",
    "confidence": "Low, Medium, or High"
}}

--- RULES ---
- NEVER contradict the provided numerical data
- DO NOT return anything outside JSON
- Your entire response MUST be a valid JSON object. No text before or after.
- DO NOT include explanations or commentary outside JSON
- Be concise, precise, and professional
- Avoid generic statements - tie reasoning to the provided data
- Interpret the investment score consistently using the score guide above
- Scores below 20 should not be described as strong, favorable, or attractive
- Negative ROI should materially weaken the recommendation
"""

def generate_explanation(data: dict) -> dict:
    prompt = build_prompt(data)
    client = get_openai_client()

    if client is None:
        return {
            "summary": "AI explanation unavailable",
            "opportunity": "N/A",
            "risks": "N/A",
            "recommendation": "Hold",
            "confidence": "Low"
        }

    try:
        response = client.responses.create(
            model="gpt-5.4-mini",
            input=prompt,
            text={"format": {"type": "json_object"}},
            max_output_tokens=300,
        )

        raw_text = response.output_text
        return json.loads(raw_text)

    except Exception as e:
        print(f"LLM ERROR: {e}")
        return {
            "summary": "AI explanation error",
            "opportunity": "N/A",
            "risks": "N/A",
            "recommendation": "Hold",
            "confidence": "Low"
        }