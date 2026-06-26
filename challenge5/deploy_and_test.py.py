# deploy_and_test.py
import vertexai
from vertexai import agent_engines
from main5 import app  # Import the application wrapper we created

PROJECT_ID = "qwiklabs-gcp-01-26711cfc88a7"
PROJECT_ID = "gen-lang-client-0922909049"
LOCATION = "us-central1"
STAGING_BUCKET = "gs://gvasend-temp-bucket"

# Initialize environment bounds
vertexai.init(project=PROJECT_ID, location=LOCATION, staging_bucket=STAGING_BUCKET)

print("Deploying agent to Vertex AI Agent Engine... (This may take a few minutes)")

# 1. Deploy the app directly to Agent Engine
remote_agent = agent_engines.create(
    agent_engine=app,
    requirements=["google-cloud-aiplatform[agent_engines,adk]"],
    display_name="Sports News Agent Engine",
)

print(f"Agent successfully deployed! Resource Name: {remote_agent.resource_name}")
print("Streaming live query response...\n")

# 2. Execute your live stream test loop
for event in remote_agent.stream_query(
    user_id="agent-engine-test-user",
    message="Give me the news highlights in the world of sports.",
):
    print(event)