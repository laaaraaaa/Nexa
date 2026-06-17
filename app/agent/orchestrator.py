from groq import Groq
from sqlalchemy.ext.asyncio import AsyncSession
from app.memory.operations import store_memory, search_similar_failures, get_recent_failures
from app.tools.github_client import get_workflow_run_logs
import os

# Initialize the Groq client with our API key
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


async def analyze_failure(
    repo: str,
    workflow_name: str,
    run_id: int,
    error_message: str,
    db: AsyncSession
) -> dict:
    """
    The main orchestrator function. Called when a CI failure is detected.
    1. Checks memory for similar past failures
    2. Asks the LLM to analyze the error and suggest a fix
    3. Stores the result back in memory
    """

    print(f"\n🤖 Orchestrator awakened for {repo}")

    # Step 0 — Fetch the real failure logs from GitHub
    try:
        real_logs = get_workflow_run_logs(repo, run_id)
        print(f"📋 Fetched real logs:\n{real_logs}")
        if real_logs and real_logs != "No detailed failure info found":
            error_message = real_logs
    except Exception as e:
        print(f"⚠️ Could not fetch real logs: {e}")

    # Step 1 — Check recent history for this repo
    recent = await get_recent_failures(db=db, repo=repo, limit=5)
    history_context = ""
    if recent:
        history_context = "\n".join([
            f"- Past failure: {m.error_type} | Fix attempted: {m.fix_attempted} | Worked: {m.fix_successful}"
            for m in recent
        ])
        print(f"🧠 Found {len(recent)} past failures in memory")
    else:
        print(f"🧠 No past failures found — starting fresh")

    # Step 2 — Ask the LLM to analyze and suggest a fix
    prompt = f"""You are Nexa, an autonomous CI/CD healing agent.

A CI pipeline has failed. Analyze the failure and suggest a fix.

Repo: {repo}
Workflow: {workflow_name}
Error: {error_message}

Past failure history for this repo:
{history_context if history_context else "No past failures recorded."}

Respond in this exact format:
ERROR_TYPE: <one word category like ImportError, SyntaxError, TestFailure, etc>
ROOT_CAUSE: <one sentence explaining why this failed>
FIX: <exact command or code change to fix it>
CONFIDENCE: <HIGH, MEDIUM, or LOW>
"""

    print(f"🔍 Analyzing failure with LLM...")

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2  # low temperature = more focused, less creative
    )

    analysis = response.choices[0].message.content
    print(f"💡 LLM Analysis:\n{analysis}")

    # Step 3 — Parse the response
    lines = analysis.strip().split("\n")
    parsed = {}
    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            parsed[key.strip()] = value.strip()

    # Step 4 — Store this analysis in memory
    await store_memory(
        db=db,
        repo=repo,
        workflow_name=workflow_name,
        error_type=parsed.get("ERROR_TYPE", "unknown"),
        error_message=error_message,
        fix_attempted=parsed.get("FIX", ""),
        fix_successful=False  # we haven't tried it yet
    )

    return {
        "repo": repo,
        "error_type": parsed.get("ERROR_TYPE"),
        "root_cause": parsed.get("ROOT_CAUSE"),
        "fix": parsed.get("FIX"),
        "confidence": parsed.get("CONFIDENCE"),
        "raw_analysis": analysis
    }