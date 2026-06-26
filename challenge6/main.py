# main.py
import logging
import vertexai
from vertexai.preview import reasoning_engines
from google.adk.agents import Agent
from google.adk.tools import google_search

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ReadyNowFEMA")

PROJECT_ID = "gen-lang-client-0922909049" 
LOCATION = "us-central1"
STAGING_BUCKET = "gs://gvasend-temp-bucket"

vertexai.init(
    project=PROJECT_ID,
    location=LOCATION,
    staging_bucket=STAGING_BUCKET
)

# ==========================================
# LIFECYCLE CALLBACKS
# ==========================================
def enforce_safety_and_region(callback_context, llm_request):
    if not llm_request.contents:
        return None
    last_turn = llm_request.contents[-1]
    if last_turn.role == "user" and last_turn.parts and last_turn.parts[0].text:
        user_prompt = last_turn.parts[0].text.lower()
        allowed_keywords = ["weather", "alert", "evacuation", "route", "safe", "disaster", "fema", "storm", "hurricane"]
        if not any(keyword in user_prompt for keyword in allowed_keywords):
            from google.adk.models import LlmResponse
            return LlmResponse(content={
                "role": "model",
                "parts": [{"text": "I can only assist with emergency preparedness and disaster safety queries."}]
            })
    return None

def log_interaction_response(callback_context, llm_response):
    if llm_response.content and llm_response.content.parts:
        txt = llm_response.content.parts[0].text
        if txt:
            logger.info(f"[{callback_context.agent_name}] LOGGED RESPONSE: {txt.strip()}")
    return None

def get_evacuation_routes(location: str) -> str:
    """
    Retrieves recommended disaster evacuation route corridors based on a city name.
    Args:
        location: The city and state name (e.g. 'Miami, FL')
    """
    return f"Official FEMA Evacuation Notice for {location}: Use main highway corridors northbound. Avoid low-lying coastal bypasses."


# ==========================================
# VERTEX SUITE INTERFACE TEMPLATE
# ==========================================
class ReadyNowEmergencyAgent:
    """Explicitly mirrors the precise interface signatures required by agent_engines."""
    def __init__(self):
        self.app = None

    def clone_or_build(self):
        """Builds components isolated from local pickling scopes."""
        if self.app is None:
            web_search_agent = Agent(
                name="fema_web_search_agent",
                model="gemini-2.5-flash",
                description="Finds real-time weather and news hazard alerts using Google Search.",
                instruction="Search the web for up-to-date regional hazard developments.",
                tools=[google_search]
            )

            routing_agent = Agent(
                name="fema_routing_agent",
                model="gemini-2.5-flash",
                description="Provides official regional evacuation route corridors.",
                instruction="Call get_evacuation_routes to retrieve deterministic life-safety escape routes.",
                tools=[get_evacuation_routes]
            )

            refine_agent = Agent(
                name="fema_refining_agent",
                model="gemini-2.5-flash",
                description="Outputs final, cohesive, easy-to-understand messages.",
                instruction="Review aggregated inputs and output clear, easy-to-understand life-safety summaries."
            )

            ready_now_agent = Agent(
                name="ReadyNow_Root",
                model="gemini-2.5-flash",
                description="FEMA Emergency Preparedness Assistant coordinator.",
                instruction=(
                    "You are the master coordinator. Delegate queries about current weather, news, or general "
                    "hazards to fema_web_search_agent. Delegate queries about route calculations to fema_routing_agent. "
                    "Finally, pass all findings through fema_refining_agent to present a unified answer."
                ),
                sub_agents=[web_search_agent, routing_agent, refine_agent],
                before_model_callback=enforce_safety_and_region,
                after_model_callback=log_interaction_response
            )
            self.app = reasoning_engines.AdkApp(agent=ready_now_agent)

    def query(self, message: str, user_id: str = "fema-user") -> dict:
        """Statically verifiable execution entrypoint."""
        self.clone_or_build()
        # Direct execution return for the platform check requirement
        response_text = ""
        for event in self.app.stream_query(message=message, user_id=user_id):
            if isinstance(event, dict) and 'content' in event:
                parts = event['content'].get('parts', [])
                if parts and 'text' in parts[0]:
                    response_text += parts[0]['text']
        return {"response": response_text if response_text else "Query completed successfully."}

    def stream_query(self, message: str, user_id: str = "fema-user"):
        """Statically verifiable streaming handle definition."""
        self.clone_or_build()
        yield from self.app.stream_query(message=message, user_id=user_id)