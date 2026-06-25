import os
import asyncio
import logging
from dotenv import load_dotenv

# Core Google ADK 2.0 Component Framework
from google.adk import Agent
from google.adk.tools import FunctionTool
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

import tools

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

# --- 1. SET UP TOOL REGISTRATION ---

def convert_place_to_coordinates(address: str) -> dict:
    """Convert a city or location name text string into explicit latitude and longitude values.

    Args:
        address: The name of the city or region to look up (e.g., "Minneapolis, MN").
    """
    # Directly invoke the keyless core tool function
    return tools.convert_place_to_coordinates(address)

# Pass the cleanly matched signature straight to the FunctionTool initialization
geocode_tool = FunctionTool(convert_place_to_coordinates)
weather_tool = FunctionTool(tools.retrieve_weather_by_coordinates)

# --- 2. DEFINE SYSTEM INSTRUCTIONS ---
SYSTEM_INSTRUCTIONS = """
You are a real-time meteorology intelligence agent. Your job is to provide accurate weather forecasts for US cities.
Always follow this execution strategy:
1. First, use 'convert_place_to_coordinates' to translate the user's requested city name into coordinates.
2. Pass those exact latitude and longitude values to 'retrieve_weather_by_coordinates'.
3. Synthesize the raw forecast response into a clean, professional weather brief.
"""

# --- 3. CONSTRUCT SYSTEM AGENT ---
gemini_agent = Agent(
    name="GeminiWeatherAgent",
    model="gemini-2.5-pro", 
    instruction=SYSTEM_INSTRUCTIONS,
    tools=[geocode_tool, weather_tool]
)

# --- 4. ASYNCHRONOUS EVALUATION & CHAT RUNNER ---

async def handle_stream_execution(runner, session_id, user_id, message_text: str):
    """Helper function to stream agent response tokens to the terminal."""
    user_message = types.Content(
        role="user",
        parts=[types.Part(text=message_text)]
    )
    
    events_stream = runner.run_async(
        session_id=session_id,
        user_id=user_id,
        new_message=user_message
    )
    
    async for event in events_stream:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(part.text, end="", flush=True)
    print()  # New line after stream ends


async def run_evaluation_suite():
    test_cities = [
        "Minneapolis, MN",
        "Charleston, SC"
    ]
    
    logger.info("=============== INITIALIZING ADK 2.0 RUNNER ===============")
    session_service = InMemorySessionService()
    
    runner = Runner(
        app_name="weather_app",
        agent=gemini_agent,
        session_service=session_service
    )
    
    # --- PHASE 1: RUN AUTOMATED TESTS ---
    logger.info("Executing automated validation suite...")
    for city in test_cities:
        logger.info(f"Processing automated test for: {city}")
        
        session = await session_service.create_session(
            state={}, app_name="weather_app", user_id="test_user"
        )
        
        print(f"\n[Automated Test Response for {city}]:")
        await handle_stream_execution(
            runner, session.id, session.user_id, f"Provide a live weather report summary for {city}."
        )
        print(f"\n{'='*60}\n")

    # --- PHASE 2: INTERACTIVE LIVE CHAT INTERFACE ---
    logger.info("Automated suite finished. Starting interactive chat session...")
    print("\n" + "*"*60)
    print("  ADK 2.0 LIVE WEATHER INTERACTIVE CHAT MODE")
    print("  Type a city name (or 'exit' to quit).")
    print("*"*60 + "\n")

    # Create a single persistent session for the chat history so it remembers context
    chat_session = await session_service.create_session(
        state={}, app_name="weather_app", user_id="interactive_user"
    )

    while True:
        try:
            # Gather user input from terminal
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "q"]:
                print("Exiting chat mode. Goodbye!")
                break
            
            print("\nAgent: ", end="")
            # Execute the live loop against the persistent chat session
            await handle_stream_execution(
                runner, chat_session.id, chat_session.user_id, user_input
            )
            print(f"\n{'-'*40}\n")
            
        except (KeyboardInterrupt, EOFError):
            print("\nExiting chat mode. Goodbye!")
            break


if __name__ == "__main__":
    if not os.getenv("GOOGLE_CLOUD_PROJECT") and not os.getenv("GEMINI_API_KEY"):
        logger.error("CRITICAL: Missing environment configuration variables.")
    else:
        asyncio.run(run_evaluation_suite())