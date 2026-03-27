import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
    
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        max_output_tokens=150,
        temperature=float(os.getenv("LLM_TEMPERATURE", 0.3)),    
    )
    
    return response.output_text 
