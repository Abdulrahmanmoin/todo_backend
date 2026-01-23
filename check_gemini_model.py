
import os
import asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")
model_name = os.environ.get("GEMINI_MODEL_NAME", "gemini-2.5-flash")

async def test_model():
    print(f"Testing Gemini connectivity with key: {api_key[:10]}... and model: {model_name}")
    
    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    
    try:
        response = await client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "Hello, are you working?"}],
        )
        print("Success! Response:")
        print(response.choices[0].message.content)
    except Exception as e:
        print(f"Error testing model: {e}")

if __name__ == "__main__":
    if not api_key:
        print("No GEMINI_API_KEY found.")
    else:
        asyncio.run(test_model())
