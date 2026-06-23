from fastapi import FastAPI, Request, Header, HTTPException
import hmac, hashlib, json
from dotenv import load_dotenv
import os
from app.memory.database import AsyncSessionLocal
from app.agent.orchestrator import analyze_failure, attempt_autonomous_fix
from app.agent.validator import check_pr_ci_status, update_memory_with_fix_result
from app.memory.working_memory import set_fix_in_progress
from app.api.dashboard import router as dashboard_router
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI(title="Nexa")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard_router)

GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")


def verify_signature(payload: bytes, signature: str) -> bool:
    if not GITHUB_WEBHOOK_SECRET:
        return True
    expected = "sha256=" + hmac.new(
        GITHUB_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@app.get("/health")
async def health():
    return {"status": "nexa is alive"}


@app.post("/webhook/github")
async def github_webhook(
    request: Request,
    x_github_event: str = Header(None),
    x_hub_signature_256: str = Header(None)
):
    payload_bytes = await request.body()

    if x_hub_signature_256:
        if not verify_signature(payload_bytes, x_hub_signature_256):
            raise HTTPException(status_code=401, detail="Invalid signature")

    payload = json.loads(payload_bytes)

    if x_github_event == "workflow_run":
        conclusion = payload.get("workflow_run", {}).get("conclusion")
        name = payload.get("workflow_run", {}).get("name")
        repo = payload.get("repository", {}).get("full_name")

        if conclusion == "failure":
            run_id = payload.get("workflow_run", {}).get("id")
            print(f"\n🔴 CI FAILURE DETECTED")
            print(f"   Repo     : {repo}")
            print(f"   Workflow : {name}")
            print(f"   Run ID   : {run_id}")

            # Wake up the orchestrator
            async with AsyncSessionLocal() as db:
                result = await analyze_failure(
                    repo=repo,
                    workflow_name=name,
                    run_id=run_id,
                    error_message=f"Workflow '{name}' failed in {repo}",
                    db=db
                )
                print(f"\n✅ Orchestrator complete:")
                print(f"   Error type : {result['error_type']}")
                print(f"   Root cause : {result['root_cause']}")
                print(f"   Fix        : {result['fix']}")
                print(f"   Confidence : {result['confidence']}")

                # Attempt an autonomous fix if conditions are right
                fix_result = await attempt_autonomous_fix(repo=repo, analysis=result)
                print(f"\n🔧 Autonomous fix attempt: {fix_result}")

                # If a PR was opened, store the PR number in memory and Redis
                if fix_result.get("success") and fix_result.get("pr_number"):
                    pr_number = fix_result["pr_number"]
                    print(f"📌 PR #{pr_number} linked to this failure")
                    set_fix_in_progress(
                        repo=repo,
                        pr_number=pr_number,
                        fix_data={
                            "fix": result.get("fix"),
                            "confidence": result.get("confidence"),
                            "error_type": result.get("error_type")
                        }
                    )

    if x_github_event == "check_run":
        # A CI check completed on some commit
        action = payload.get("action")
        conclusion = payload.get("check_run", {}).get("conclusion")
        
        # Only care about completed check runs
        if action == "completed" and conclusion in ["success", "failure"]:
            # Check if this is on a Nexa-created PR branch
            pr_numbers = [
                pr.get("number") 
                for pr in payload.get("check_run", {}).get("pull_requests", [])
            ]
            
            repo = payload.get("repository", {}).get("full_name")
            
            for pr_number in pr_numbers:
                print(f"\n🔍 Check run completed on PR #{pr_number} — {conclusion}")
                
                async with AsyncSessionLocal() as db:
                    # Check the full CI status for this PR
                    status = await check_pr_ci_status(
                        db=db,
                        repo_full_name=repo,
                        pr_number=pr_number
                    )
                    
                    if status["all_complete"]:
                        # Update memory with whether the fix worked
                        await update_memory_with_fix_result(
                            db=db,
                            pr_number=pr_number,
                            fix_successful=status["all_passed"]
                        )

    return {"status": "received"}