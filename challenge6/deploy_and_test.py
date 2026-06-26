# deploy_and_test.py
import vertexai
from vertexai import agent_engines
from main import ReadyNowEmergencyAgent  # Import the class definition

PROJECT_ID = "gen-lang-client-0922909049" 
LOCATION = "us-central1"
STAGING_BUCKET = "gs://gvasend-temp-bucket"

vertexai.init(
    project=PROJECT_ID,
    location=LOCATION,
    staging_bucket=STAGING_BUCKET
)

# ─── LOCAL TEST ───
print("--- RUNNING LOCAL TEST TURN ---")
local_agent = ReadyNowEmergencyAgent()
local_agent.clone_or_build()
for event in local_agent.stream_query(user_id="local-tester", message="What is the evacuation route for Miami, FL?"):
    print(event)

# ─── REMOTE PRODUCTION DEPLOY ───
print("\n--- DEPLOYING TO VERTEX AI AGENT ENGINE ---")

# Pass a clean, un-run class instance to bypass the pickling block and satisfy method validation
deployable_agent = ReadyNowEmergencyAgent()

remote_agent = agent_engines.create(
    agent_engine=deployable_agent,
    requirements=["google-cloud-aiplatform[agent_engines,adk]"],
)

print(f"Deployment complete! Remote Resource Name: {remote_agent.resource_name}")

print("\n--- STREAMING REMOTE PRODUCTION TEST QUERY ---")
for event in remote_agent.stream_query(
    user_id="fema-production-user",
    message="Give me live weather status updates for Houston, TX."
):
    print(event)