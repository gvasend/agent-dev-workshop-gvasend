import os
import asyncio
import logging
from dotenv import load_dotenv

# ADK 2.0 Engine Components
from google.adk import Agent
from google.adk.tools import FunctionTool, google_search
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

import tools

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
load_dotenv()

# =====================================================================
# 1. LIFECYCLE CALLBACK ENGINE DEVELOPMENTS (STRICT SIGNATURES)
# =====================================================================

def validate_user_input_callback(callback_context, **kwargs) -> str | None:
    user_content_obj = getattr(callback_context, "user_content", None)
    input_text = ""
    if user_content_obj and hasattr(user_content_obj, "parts") and user_content_obj.parts:
        input_text = user_content_obj.parts[0].text or ""

    clean_input = input_text.strip()
    if not clean_input:
        raise ValueError("Validation Failed: Prompt cannot be empty.")
    return None

def log_model_prompt_callback(callback_context, llm_request, **kwargs):
    print(f"\n--- 📤 [CALLBACK: before_model] OUTBOUND PROMPT DISPATCH ---")
    if callback_context:
        print(f"Target Agent Node ID: {getattr(callback_context, 'agent_name', 'Unknown')}")
    print(f"-----------------------------------------------------------\n")
    return None

def log_model_response_callback(callback_context, llm_response, **kwargs):
    print(f"\n--- 📥 [CALLBACK: after_model] INBOUND INTERCEPT METRICS ---")
    print(f"-----------------------------------------------------------\n")
    return None

# =====================================================================
# 2. DECLARE SPECIALIZED SUB-AGENTS
# =====================================================================

geocode_tool = FunctionTool(tools.convert_place_to_coordinates)
weather_tool = FunctionTool(tools.retrieve_weather_by_coordinates)

weather_sub_agent = Agent(
    name="WeatherSubAgent",
    model="gemini-2.5-pro",
    instruction=(
        "You are an absolute expert in local US meteorology. "
        "Always resolve the location coordinates first, fetch the raw forecast telemetry, "
        "and return a highly precise weather briefing summary."
    ),
    tools=[geocode_tool, weather_tool]
)

search_sub_agent = Agent(
    name="SearchSubAgent",
    model="gemini-2.5-pro",
    instruction=(
        "You are a ground-truth research investigator. Use the provided Google Search tool "
        "to discover verified up-to-date facts, currents, breaking events, and trivia."
    ),
    tools=[google_search]  # <--- Use the lower_case pre-built tool reference here
)

# =====================================================================
# 3. DECLARE ROOT ORCHESTRATION AGENT WITH AGENT_TOOL WRAPPERS
# =====================================================================
from google.adk.tools import AgentTool  # Ensure AgentTool is imported

ROOT_SYSTEM_INSTRUCTIONS = """
You are a master intelligence coordinator orchestrating specialized subsystem nodes.
You do not answer queries directly if they fall under specialized domains.

Routing Logic Guidelines:
- If the request targets live local weather, forecasts, or current regional alerts, delegate the task entirely to 'WeatherSubAgent'.
- If the request asks about recent events, general knowledge, sports scores, flights, or historical facts, delegate entirely to 'SearchSubAgent'.
- Synthesize responses clearly, calling out which node solved the problem.
"""

# WRAP your sub-agents so Pydantic recognizes them as valid BaseTool instances
weather_agent_tool = AgentTool(agent=weather_sub_agent)
search_agent_tool = AgentTool(agent=search_sub_agent)

root_agent = Agent(
    name="RootCoordinatorAgent",
    model="gemini-2.5-pro",
    instruction=ROOT_SYSTEM_INSTRUCTIONS,
    
    # Pass the wrapped tools instead of the raw Agent objects
    tools=[weather_agent_tool, search_agent_tool],
    
    before_agent_callback=[validate_user_input_callback],
    before_model_callback=[log_model_prompt_callback],
    after_model_callback=[log_model_response_callback]
)
# =====================================================================
# 4. STANDALONE TURN STREAMING ENGINE
# =====================================================================

async def execute_diagnostic_turn(runner, session_id, user_id, user_prompt: str):
    """Handles async engine streaming for standalone output loops."""
    try:
        user_message = types.Content(
            role="user",
            parts=[types.Part(text=user_prompt)]
        )
        
        events_stream = runner.run_async(
            session_id=session_id,
            user_id=user_id,
            new_message=user_message
        )
        
        async for event in events_stream:
            # Catch internal agent call events to demonstrate sub-agent execution
            if hasattr(event, 'agent_call') and event.agent_call:
                print(f"\n🔀 [ROUTE]: Orchestrator routing to sub-agent: '{event.agent_call.agent_name}'\n")
            elif hasattr(event, 'content') and event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(part.text, end="", flush=True)
        print()
    except Exception as e:
        print(f"\n❌ Execution Intercepted Error: {str(e)}\n")

# =====================================================================
# 5. CORE ENTRY SUITE RUNNER
# =====================================================================

async def main():
    session_service = InMemorySessionService()
    runner = Runner(app_name="multi_agent_system", agent=root_agent, session_service=session_service)
    
    # --- PHASE 1: RUN EVALUATION SUITE ---
    logger.info("Initializing Standalone Multi-Agent Test Battery...")
    test_session = await session_service.create_session(state={}, app_name="multi_agent_system", user_id="test_user")
    
    print("\n--- TEST A: Weather Request (Routing Check) ---")
    await execute_diagnostic_turn(runner, test_session.id, test_session.user_id, "Weather forecast for Charleston, SC")
    print("="*70)
    
    print("\n--- TEST B: Search Request (Routing Check) ---")
    await execute_diagnostic_turn(runner, test_session.id, test_session.user_id, "Who won the Stanley Cup hockey match in 2026?")
    print("="*70 + "\n")

    # --- PHASE 2: INTERACTIVE USER SESSION ---
    logger.info("Test suite complete. Entering live user shell context...")
    print("\n" + "*"*60)
    print("  ADK 2.0 STANDALONE MULTI-AGENT INTERACTIVE CONSOLE")
    print("  Type 'exit' to shut down the runtime loop.")
    print("*"*60 + "\n")

    chat_session = await session_service.create_session(state={}, app_name="multi_agent_system", user_id="live_user")

    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "q"]:
                print("Shutting down workspace stream. Goodbye!")
                break
                
            print("\nAgent: ", end="")
            await execute_diagnostic_turn(runner, chat_session.id, chat_session.user_id, user_input)
            print(f"\n{'-'*50}\n")
            
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            break

if __name__ == "__main__":
    if not os.getenv("GOOGLE_CLOUD_PROJECT") and not os.getenv("GEMINI_API_KEY"):
        logger.error("CRITICAL ERROR: Environment configuration context missing. Please initialize ADC profile.")
    else:
        asyncio.run(main())