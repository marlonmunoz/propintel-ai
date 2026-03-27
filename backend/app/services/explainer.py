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
You are an expert real estate investement analyst.

Analyze the following property using the provided model outputs.

--- PROPERTY DATA ---
Predicted Price: {data['predicted_price']}
Market Price: {data['market_price']}
ROI Estimate: {data['roi_estimate']}%
Investment Score: {data['investment_score']}

Key Drivers:
{drivers_text}

--- TASK ---
Return a structured investment analysis in the following JSON format:
{{
    "summary": "1-2 sentence high-level conclusion",
    "opportunity": "Why this is a good investment (if applicable)",
    "risks": "Potential downsides or uncertainties",
    "recommendation": "Clear action (Buy / Hold / Avoid)",
    "confidence": "Low / Medium / High"
}}

--- RULES ---
- Be concise and professional
- Use investor-style reasoning
- Do NOT include explanations outside JSON
- Do NOT add extra fields
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
            max_output_tokens=200,
            temperature=float(os.getenv("LLM_TEMPERATURE", 0.3)),    
        )
        
        text = response.output_text
        
        if not text:
            raise ValueError("Empty LLM response")
        
        try:
            return json.loads(text)
        except Exception:
            return {
                "summary": "AI explanation parsing error",
                "opportunity": "N/A",
                "risks": "N/A",
                "recommendation": "Hold",
                "confidence": "Low"
            }
    except Exception as e:
        print(f"LLM ERROR: {e}")
        return {
            "summary": "AI explanation error",
            "opportunity": "N/A",
            "risks": "N/A",
            "recommendation": "Hold",
            "confidence": "Low"
        }
    
