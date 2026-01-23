import asyncio
import os
import sys
import traceback

# Windows event loop fix
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Add path
sys.path.insert(0, os.getcwd())

from dotenv import load_dotenv
load_dotenv()

# Test the Gemini API directly first
from openai import AsyncOpenAI

async def test_gemini_direct():
    api_key = os.environ.get('GEMINI_API_KEY')
    model_name = os.environ.get('GEMINI_MODEL_NAME', 'gemini-2.5-flash')
    
    print(f"\n=== Testing Gemini API directly ===")
    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    
    try:
        response = await client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "Hello, just say 'working'"}],
        )
        print(f"Gemini API Response: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return False

async def test_agent():
    from src.services.agent import run_agent_with_context
    
    print(f"\n=== Testing Agent ===")
    user_id = "f74b2682-2a67-48d3-b1f8-9d6bbce83294"
    messages = [{"role": "user", "content": "list all my tasks"}]
    
    try:
        result = await run_agent_with_context(messages, user_id)
        print(f"Agent Result Response: {result.get('response')}")
        print(f"Agent Result Tool Calls: {result.get('tool_calls')}")
        print(f"Agent Success: {result.get('success')}")
        if not result.get('success'):
             print(f"Agent Error Details: {result.get('error')}")
    except Exception as e:
        print(f"Agent Direct Exception: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    async def main():
        if await test_gemini_direct():
            await test_agent()
    
    asyncio.run(main())
