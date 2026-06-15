from fastapi import FastAPI, Request, Header, HTTPException
import hmac, hashlib, json
from dotenv import load_dotenv
import os

from app.memory.database import AsyncSessionLocal
from app.memory.operations import store_memory, search_similar_failures

load_dotenv()

app = FastAPI(title="Nexa")

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
            print(f"\n🔴 CI FAILURE DETECTED")
            print(f"   Repo     : {repo}")
            print(f"   Workflow : {name}")

            # Store this failure in memory
            async with AsyncSessionLocal() as db:
                # Search for similar past failures first
                similar = await search_similar_failures(db, error_embedding=None)
                if similar:
                    print(f"   🧠 Found {len(similar)} similar past failures")

                # Store the new failure
                await store_memory(
                    db=db,
                    repo=repo,
                    workflow_name=name,
                    error_type="workflow_failure",
                    error_message=f"Workflow '{name}' failed in {repo}",
                )
                print(f"   💾 Failure stored in memory")

    return {"status": "received"}