# main.py
import vertexai
from vertexai.agent_engines import AdkApp
from google.adk import Agent
from google.adk.tools import google_search

# 1. Initialize Vertex AI with your Cloud Project details
vertexai.init(project="YOUR_GOOGLE_CLOUD_PROJECT_ID", location="us-central1")

# 2. Define the core ADK Agent logic
sports_agent = Agent(
    name="sports_news_agent",
    model="gemini-2.5-flash",
    instruction=(
        "You are an elite sports journalist. Your job is to fetch, summarize, "
        "and present clean highlights of real-time world sports events. Always use "
        "the search tool to ensure your data is perfectly up to date."
    ),
    tools=[google_search],
)

# 3. Wrap it inside the AdkApp orchestration engine required for Agent Engine
app = AdkApp(agent=sports_agent)