import json
import os
from openai import OpenAI

def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        return None
    
    return OpenAI(api_key=api_key)


def build_prompt(data: dict) -> str:
    return f"""
You are an expert real estate investement analyst.

Analyze the following property using the provided model outputs.

--- PROPERTY DATA ---
Predicted Price: {data['predicted_price']}
Market Price: {data['market_price']}
ROI Estimate: {data['roi_estimate']}%
Investment Score: {data['investment_score']}

Key Drivers:
{', '.join(data['top_drivers'])}

--- TASK ---
Return a structured investment analysis in the following JSON format:
{{
    "summary": "1-2 sentence high-level conclusion",
    "opportunity": "Why this is a good investment (if applicable)",
    "risk": "Potential downsides or uncertainties",
    "recommendation": "Clear action (Buy / Hold / Avoid)",
    "confidence": "Low / Medium / High"
}}

--- RULES ---
- Be concise and professional
- Use investor-style reasoning
- Do NOT include explanations outside JSON
- Do NOT add extra fields
"""

def generate_explanation(data: dict) -> str:
    prompt = build_prompt(data)
    client = get_openai_client()
    
    if client in None:
        return {
            "summary": "AI explanation unavailable",
            "opportunity": "N/A",
            "risk": "N/A",
            "recommendation": "N/A",
            "confidence": "low"
        }
    
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
            max_output_tokens=200,
            temperature=float(os.getenv("LLM_TEMPERATURE", 0.3)),    
        )
        
        text = response.output_text
        
        return json.loads(text)
    
    except Exception as e:
        print(f"LLM ERROR: {e}")
        return {
            "summary": "AI explanation error",
            "opportunity": "N/A",
            "risk": "N/A",
            "recommendation": "N/A",
            "confidence": "low"
        }
    
