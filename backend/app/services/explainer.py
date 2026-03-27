import os
from openai import OpenAI

def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        return None
    
    return OpenAI(api_key=api_key)


def build_prompt(data: dict) -> str:
    return f"""
You are a real estate investement analyst.

Analyze the following property:

Predicted Price: {data['predicted_price']}
Market Price: {data['market_price']}
ROI Estimate: {data['roi_estimate']}%
Investment Score: {data['investment_score']}

Key Drivers:
{', '.join(data['top_drivers'])}

Provide a concise, professinal summary explanation of whether this property is a good investment.
Be clear, insightful, and inverstor-focused.
"""

def generate_explanation(data: dict) -> str:
    prompt = build_prompt(data)
    client = get_openai_client()
    
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
            max_output_tokens=150,
            temperature=float(os.getenv("LLM_TEMPERATURE", 0.3)),    
        )
        return response.output_text 
    except Exception as e:
        print(f"LLM ERROR: {e}")
        return "AI explanation currently unavailable — analysis based on statistical model only."
    
