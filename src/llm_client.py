import os
from openai import OpenAI
from .config import LLM_API_KEY, LLM_MODEL

client = OpenAI(api_key=LLM_API_KEY)

def generate_sql(prompt: str) -> str:
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return response.choices[0].message.content.strip()
