import asyncio
import os
import logging
from google.adk import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# =====================================================================
# 1. DECLARE PIPELINE AGENT NODES
# =====================================================================

generator_agent = Agent(
    name="DraftGenerator",
    model="gemini-2.5-pro",
    instruction=(
        "Provide a detailed, highly comprehensive baseline answer to the user's question. "
        "Lay out all historical facts, technical components, and details clearly."
    )
)

verifier_agent = Agent(
    name="FactVerifier",
    model="gemini-2.5-pro",
    instruction=(
        "You are a critical auditor. Review the provided draft text for factual accuracy, "
        "potential hallucinations, inconsistencies, or gaps. Output a structured audit log "
        "detailing what is correct, what is suspect or wrong, and what needs expansion."
    )
)

refiner_agent = Agent(
    name="ResponseRefiner",
    model="gemini-2.5-pro",
    instruction=(
        "You are an expert technical editor. Review the original draft response along with "
        "the Verifier's audit logs. Rewrite the response completely to fix every issue "
        "and inaccuracy raised. Output ONLY the final polished, verified answer using clean "
        "Markdown formatting. Do not include meta-commentary about the changes made."
    )
)

# =====================================================================
# 2. DEFINE THE VERIFICATION PIPELINE (UNIFORM APP SESSION ROUTER)
# =====================================================================

class AnswerVerificationPipeline:
    def __init__(self, session_service, app_name: str):
        self.session_service = session_service
        
        # FIXED: Share the exact same app_name namespace so the single session context is globally accessible
        self.generator_runner = Runner(app_name=app_name, agent=generator_agent, session_service=session_service)
        self.verifier_runner = Runner(app_name=app_name, agent=verifier_agent, session_service=session_service)
        self.refiner_runner = Runner(app_name=app_name, agent=refiner_agent, session_service=session_service)

    async def run_async(self, session_context, workflow_input: str) -> str:
        """Sequentially routes payloads across runners sharing a shared session context."""
        print("\n" + "="*70)
        print(f"📥 WORKFLOW ENTRY: Processing Query...")
        print("="*70)
        
        # Stage 1: Generate initial draft response
        print("\n⚡ [STAGE 1]: Dispatching to DraftGenerator...")
        draft_response = ""
        user_message = types.Content(role="user", parts=[types.Part(text=workflow_input)])
        
        async for event in self.generator_runner.run_async(
            session_id=session_context.id,
            user_id=session_context.user_id,
            new_message=user_message
        ):
            if hasattr(event, 'content') and event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        draft_response += part.text
        print(f" -> Draft captured ({len(draft_response)} characters generated).")
        
        # Stage 2: Audit the draft for factual accuracy
        print("\n⚡ [STAGE 2]: Running analysis via FactVerifier...")
        audit_payload = f"Original Query: {workflow_input}\nDraft Response: {draft_response}"
        audit_message = types.Content(role="user", parts=[types.Part(text=audit_payload)])
        
        verification_log = ""
        async for event in self.verifier_runner.run_async(
            session_id=session_context.id,
            user_id=session_context.user_id,
            new_message=audit_message
        ):
            if hasattr(event, 'content') and event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        verification_log += part.text
        print(" -> Factual audit log compiled successfully.")
        
        # Stage 3: Polish and patch anomalies
        print("\n⚡ [STAGE 3]: Polishing anomalies via ResponseRefiner...")
        refinement_payload = f"Draft: {draft_response}\nAudit Logs: {verification_log}"
        refine_message = types.Content(role="user", parts=[types.Part(text=refinement_payload)])
        
        final_polished_output = ""
        async for event in self.refiner_runner.run_async(
            session_id=session_context.id,
            user_id=session_context.user_id,
            new_message=refine_message
        ):
            if hasattr(event, 'content') and event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        final_polished_output += part.text
        
        print("\n🏁 WORKFLOW EXIT: Pipeline loop finalized.")
        print("="*70 + "\n")
        
        return final_polished_output

# =====================================================================
# 3. STANDALONE PROCESS RUNNER ENTRYPOINT
# =====================================================================

async def main():
    session_service = InMemorySessionService()
    SHARED_APP_NAME = "verification_system"
    
    # Initialize our pipeline using the matching app identifier
    pipeline = AnswerVerificationPipeline(session_service=session_service, app_name=SHARED_APP_NAME)
    
    test_query = (
        "Explain the dynamic graph node approach to modeling operational knowledge "
        "in maritime container ship logistics, and how it handles real-time disruptions."
    )
    
    print(f"Starting verification pipeline session for standalone test...")
    test_session = await session_service.create_session(
        state={}, 
        app_name=SHARED_APP_NAME, 
        user_id="lead_dev_agent"
    )
    
    verified_answer = await pipeline.run_async(test_session, test_query)
    
    print("### FINAL REFINED AND VERIFIED OUTPUT ###\n")
    print(verified_answer)

if __name__ == "__main__":
    asyncio.run(main())