# PropIntel AI — Product Overview & Demo Guide

> A talk-ready reference for explaining PropIntel AI to anyone — investors, recruiters,
> customers, or engineers — and for running a live demo with confidence.
> Read top-to-bottom once; after that, the **Elevator pitches** and **Demo script**
> sections are all you need on the spot.

---

## 1. The one-liner

**PropIntel AI is an AI-powered property analysis platform for NYC real estate. You type in an address, and in seconds you get a data-driven valuation, an investment score, and a plain-English explanation of whether it's a good deal.**

That's the whole product in one sentence. Everything below is detail you can pull from when someone wants to go deeper.

---

## 2. Elevator pitches (memorize these)

### 10-second version
> "PropIntel AI tells real estate investors what a NYC property is actually worth and whether it's a good deal — in seconds, using machine learning trained on real city sales data."

### 30-second version
> "When investors or brokers evaluate a NYC property today, it takes hours of pulling comps, checking tax records, and guessing. PropIntel AI does it instantly. You enter an address, and our machine learning models — trained on actual NYC sales, tax assessments, and deed history — return a valuation, a confidence range, an investment score, and a written explanation. It's like having an analyst that works in seconds instead of hours."

### 2-minute version
> "NYC real estate is one of the biggest markets in the world, but evaluating a deal is still slow and manual. An investor looking at a Brooklyn two-family has to pull comparable sales, look up the building's tax assessment, check its deed and mortgage history, factor in transit access — and then make a judgment call. That's hours of work per property.
>
> PropIntel AI compresses that into seconds. We built a data pipeline that pulls together six NYC public datasets — sales records, the PLUTO parcel database, Department of Finance tax assessments, ACRIS deed and mortgage records, J-51 tax abatements, and subway station locations. We trained separate machine learning models for each type of building — one-family homes, multi-family, condos, co-ops, and rentals — because a co-op and a single-family house are priced completely differently.
>
> When you enter an address, the system routes to the right model, returns a valuation with a realistic price range, scores the investment, and then an AI layer writes a clear explanation a human can actually act on. It's live in production today — built on a modern full stack with Stripe billing, user accounts, and the whole thing deployed and monitored like real software, not a demo."

---

## 3. The problem we solve

| Without PropIntel AI | With PropIntel AI |
|----------------------|-------------------|
| Hours of manual comp research per property | Seconds |
| Spreadsheets and gut feel | Models trained on real sales data |
| No clear sense of confidence | Explicit price range + confidence tier |
| Hard to explain a number to a partner/client | AI-written investor narrative |
| Generic estimates that ignore building type | A dedicated model per building segment |

**The core insight:** a single "citywide" valuation model is mediocre at everything. NYC has wildly different sub-markets — a SoHo condo, a Bronx walk-up rental, and a Staten Island single-family are not the same problem. We trade one generic model for several specialist ones, and that's what makes the numbers credible.

---

## 4. Who it's for

- **Real estate investors** — screen deals fast, decide what's worth deeper diligence.
- **Brokers & agents** — back up pricing conversations with data.
- **Operators / small funds** — evaluate acquisition targets at portfolio scale.

The common thread: people who deal in real NYC buildings and need a fast, defensible number.

---

## 5. What a user actually does (the journey)

This is the flow to narrate during a demo:

1. **Sign up / log in** — email + password (handled by Supabase Auth).
2. **Go to Analyze** — type a NYC address. The map (Mapbox) drops a pin and auto-fills location details.
3. **Fill in the basics** — building type, square footage, units, year built. Optionally a listing price to compare against.
4. **Hit Analyze.** In a couple of seconds you get back:
   - **Predicted value** with a **P10–P90 price range** (the realistic low-to-high band).
   - **A confidence badge** — "High confidence," "Directional estimate," or "Broad estimate," depending on how much data supports that building type.
   - **An investment score** (0–100) and a **deal label** — Buy / Hold / Avoid.
   - **An AI-written explanation** — the opportunity, the risks, and a recommendation in plain English.
5. **Save it to the portfolio** — revisit saved analyses anytime.
6. **Upgrade to Pro** ($29/mo) for a higher daily analysis quota.

---

## 6. How it works — plain English first

Think of it as four layers stacked on top of each other:

1. **The data foundation.** We continuously combine six NYC public datasets into one clean, joined-up picture of every property, keyed on the city's parcel ID (the "BBL"). Critically, we only use data that was knowable *before* each sale — so the models can't "cheat" by peeking at the future.

2. **The models.** Instead of one model, we trained a family of them — one per building type. When you analyze a property, the system looks at the building class and routes your request to the correct specialist model.

3. **The valuation + scoring engine.** The chosen model predicts a price. We pair it with a realistic price range and a deterministic investment score, so two people analyzing the same property always get the same numbers.

4. **The AI explanation layer.** A large language model (OpenAI) takes the model's output and writes a short, investor-grade narrative — what's good, what's risky, what to do. The model produces the *numbers*; the AI produces the *story*.

> **A line that lands well in interviews:** "The machine learning model produces the number. The AI writes the explanation. They're two different jobs and I kept them separate on purpose."

---

## 7. How it works — the technical version

### Data pipeline (medallion architecture)
We use a **Bronze → Silver → Gold** pattern:
- **Bronze:** raw NYC datasets (Rolling Sales, PLUTO, DOF Assessments, ACRIS, J-51, subway stations).
- **Silver:** cleaned and normalized versions of each.
- **Gold:** "as-of" feature tables — for every property and sale date, the features reflect only what was known the day *before* the sale. This is the anti-leakage discipline that makes the evaluation honest.

Everything joins on **BBL** (Borough-Block-Lot), NYC's universal parcel identifier.

### The data sources and why each matters
| Dataset | What it adds |
|---------|--------------|
| NYC Rolling Sales | The actual sale prices we train on |
| PLUTO | Parcel size, floors, zoning, lat/long |
| DOF Assessments | The city's own tax valuation — the single strongest predictor |
| ACRIS | Deed and mortgage history (prior sales, financing signals) |
| J-51 | Tax abatement flags (affects value) |
| Subway stations | Transit access — distance, density, hub proximity |

### The models
- **Segment-routed:** one_family, multi_family, condo, coop, rentals_all, plus a global fallback.
- **Algorithms:** LightGBM and XGBoost (gradient-boosted trees), with ensemble averaging across multiple seeds on the high-variance segments to reduce noise.
- **Honest evaluation:** trained on sales through 2024, tested on 2025 sales — a true forward-in-time test, not a random split. This is harder and more realistic than the usual academic 80/20 split.
- **Confidence intervals:** each segment also has **P10 and P90 quantile models** that produce a property-specific price range — tight where there's lots of data, wide where there isn't. (This replaced an older fixed-width "±average error" band.)

### Current model performance (forward-time holdout)
| Segment | Test R² | Median error | Notes |
|---------|---------|--------------|-------|
| Condo | 0.83 | ~14% | Best segment; rich unit-level data |
| One-family | 0.72 | ~14.5% | Strong owner-occupier baseline |
| Multi-family | 0.67 | ~17% | Merged 2- & 3-family |
| Co-op | ~0.50 | ~24% | No public unit-level data → wider intervals |
| Rentals (pooled) | ~0.47 | ~26% | Priced per unit; thinner data |

> **Be honest about the weak segments.** Co-ops and rentals are harder because the public data is genuinely thinner — co-op prices are share transactions, not real-property sales. Saying this out loud builds credibility; the confidence tiers in the UI reflect it.

### The serving layer
- **FastAPI** backend exposes a clean v2 prediction API.
- **ModelRegistry** loads the right model lazily and caches it in memory.
- **PredictionService** builds the feature row, runs inference, computes the interval and score, and (optionally) calls the explainer.
- Models load once and stay warm, so requests are fast.

---

## 8. Tech stack (for the engineering audience)

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Vite, Tailwind CSS 4, Mapbox GL |
| Backend | FastAPI, Pydantic v2, SQLAlchemy |
| Database & Auth | Supabase (PostgreSQL + JWT auth) |
| ML | XGBoost, LightGBM, scikit-learn, pandas, Optuna (tuning) |
| Data | Parquet, medallion (Bronze/Silver/Gold) pipeline |
| LLM | OpenAI (quota-controlled narrative generation) |
| Payments | Stripe (hosted Checkout + Customer Portal + webhooks) |
| Email | Resend (contact form + auth emails) |
| Deploy | Frontend on Vercel, API on Railway, Docker-packaged |
| Quality | ~270 automated tests (pytest + Vitest), GitHub Actions CI |

**Production-grade details worth mentioning:** rate limiting, CORS allowlisting, unified JSON error responses with request IDs, optional Sentry error tracking with PII scrubbing, `/health` and `/ready` probes (the readiness probe runs a real inference call to catch model issues before they hit users), and a CI test that verifies the model files and their metadata never drift out of sync.

---

## 9. Live demo script

Keep it to ~3 minutes. Narrate as you click.

1. **Open the homepage.** "This is live in production at propintel-ai.com." Point at the model performance cards.
2. **Log in and go to Analyze.**
3. **Type a real address** you know — ideally a one-family or condo (the strong segments). "Watch — the map finds it and pulls in the location data automatically."
4. **Fill the form, hit Analyze.** "This is hitting the live API, routing to the right model, and running inference."
5. **Walk through the result top to bottom:**
   - "Here's the predicted value, and this is the realistic range — notice it's specific to *this* property, not a flat percentage."
   - "This badge tells the user how much to trust it. For a condo it's high confidence; for a co-op it'd say directional, because the public data is thinner — we're upfront about that."
   - "Here's the investment score and the Buy/Hold/Avoid call."
   - "And this is the AI explanation — it turns the raw numbers into something a human can act on."
6. **Save to portfolio**, then mention **Pro upgrade** as the business model.

**If something breaks during the demo:** stay calm and pivot to the architecture story — "the system has a readiness probe and a model/metadata parity test exactly so production failures get caught before users see them." You turn a hiccup into a credibility point.

---

## 10. Likely questions & strong answers

**"Is this just ChatGPT wrapped around a real estate API?"**
> No. The valuation comes from machine learning models I trained myself on real NYC sales data — gradient-boosted trees, one per building segment, evaluated forward-in-time. The LLM only writes the explanation around numbers the models already produced. The intelligence is in the models and the data pipeline, not the prompt.

**"How accurate is it?"**
> It depends on the building type, and I'm transparent about that. Condos hit about 0.83 R² with ~14% median error on a true forward-in-time test. Co-ops and rentals are weaker because the public data is genuinely thinner, and the UI flags that with a confidence tier instead of pretending every estimate is equally solid.

**"Where does the data come from?"**
> Six NYC public datasets — sales, PLUTO, tax assessments, deed/mortgage records, abatements, and transit — all joined on the city parcel ID, with strict as-of filtering so the model never trains on information that didn't exist yet at sale time.

**"What's the hardest engineering problem you solved?"**
> Keeping the trained models and their metadata in sync in production. When I retrain a model with new features, the serving code has to know about them or inference silently breaks. I built a CI test that fails the build if a model's actual features drift from its declared metadata, plus a readiness probe that runs a real prediction on deploy. Both caught real bugs.

**"How does it make money?"**
> Freemium. Free users get a limited number of AI analyses per day; Pro is $29/month for a much higher quota, via Stripe.

**"Is it really in production?"**
> Yes — frontend on Vercel, API on Railway, Postgres and auth on Supabase, live Stripe billing, automated tests and CI. It's deployed and monitored like real software.

---

## 11. Honest limitations (say these proactively — it builds trust)

- **NYC residential only.** Not built for commercial or other cities.
- **Co-op and rental segments are weaker** due to thin public data; the confidence tiers reflect this.
- **No macroeconomic / interest-rate features** in the current models — it values a property on its own merits, not the market cycle.
- **It's a decision-support tool, not an appraisal.** It accelerates screening; it doesn't replace formal due diligence.

---

## 12. The 30-second "why I built this" story (for recruiters)

> "I wanted to prove I could take something all the way from raw data to a live, paying product. PropIntel AI is the result: I built the data pipeline, trained and evaluated the ML models, wrote the FastAPI backend and React frontend, set up Stripe billing and auth, and deployed the whole thing to production with CI and monitoring. It's not a notebook or a tutorial project — it's a real system that handles real users, and I own every layer of it."

---

*This document reflects the production state as of June 2026. When you retrain models or ship major features, update Sections 7 and 9 so your talking points stay accurate.*
