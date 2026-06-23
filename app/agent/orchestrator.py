from groq import Groq
from app.memory.embeddings import get_embedding
from sqlalchemy.ext.asyncio import AsyncSession
from app.memory.operations import store_memory, search_similar_failures, get_recent_failures
import os
from app.memory.working_memory import (
    set_active_run,
    get_active_run,
    clear_active_run,
    is_repo_being_processed
)
from app.tools.github_client import (
    get_workflow_run_logs,
    create_fix_branch,
    update_file_on_branch,
    open_pull_request,
    get_github_client
)

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

    # Check if we're already processing a failure for this repo
    # This prevents duplicate processing if GitHub fires the webhook twice
    if is_repo_being_processed(repo):
        print(f"⚠️ Already processing a failure for {repo} — skipping duplicate")
        return {
            "repo": repo,
            "error_type": "duplicate",
            "root_cause": "Already processing a failure for this repo",
            "fix": None,
            "confidence": "LOW",
            "raw_analysis": None
        }

    # Store in Redis that we're actively working on this repo
    set_active_run(repo, {
        "run_id": run_id,
        "workflow_name": workflow_name,
        "status": "analyzing"
    })

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

    # Step 1.5 — Semantic search: find similar past failures by meaning, not just recency
    error_embedding_for_search = get_embedding(error_message)
    similar_failures = await search_similar_failures(
        db=db,
        error_embedding=error_embedding_for_search,
        limit=3
    )
    
    history_context = ""
    if recent:
        history_context = "\n".join([
            f"- Past failure: {m.error_type} | Fix attempted: {m.fix_attempted} | Worked: {m.fix_successful}"
            for m in recent
        ])
        print(f"🧠 Found {len(recent)} past failures in memory")
    else:
        print(f"🧠 No past failures found — starting fresh")

    if similar_failures:
        print(f"🎯 Found {len(similar_failures)} SEMANTICALLY similar past failures")
        semantic_context = "\n".join([
            f"- Similar error: {m.error_type} | Fix: {m.fix_attempted} | Worked: {m.fix_successful}"
            for m in similar_failures
        ])
        history_context += f"\n\nSemantically similar failures (by meaning, not just recency):\n{semantic_context}"

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

    # Step 4 — Generate embedding and store this analysis in memory
    embedding = get_embedding(error_message)
    
    await store_memory(
        db=db,
        repo=repo,
        workflow_name=workflow_name,
        error_type=parsed.get("ERROR_TYPE", "unknown"),
        error_message=error_message,
        fix_attempted=parsed.get("FIX", ""),
        fix_successful=False,  # we haven't tried it yet
        error_embedding=embedding
    )

    # Clear the active run from Redis — we're done analyzing
    clear_active_run(repo)

    return {
        "repo": repo,
        "error_type": parsed.get("ERROR_TYPE"),
        "root_cause": parsed.get("ROOT_CAUSE"),
        "fix": parsed.get("FIX"),
        "confidence": parsed.get("CONFIDENCE"),
        "raw_analysis": analysis
    }

async def attempt_autonomous_fix(
    repo: str,
    analysis: dict
) -> dict:
    """
    Attempts to autonomously fix simple, well-understood failures.
    For now, only handles the case where the fix is a pip install
    that's missing from requirements.txt.
    
    This is intentionally conservative — we only act automatically
    when confidence is HIGH and the fix pattern is recognized.
    """
    fix = analysis.get("fix", "")
    confidence = analysis.get("confidence", "")

    # Only attempt autonomous action on high-confidence pip install fixes
    if confidence != "HIGH" or "pip install" not in fix.lower():
        print(f"🛑 Skipping autonomous fix — confidence: {confidence}, fix type not supported yet")
        return {"attempted": False, "reason": "fix type not supported or confidence too low"}

    try:
        # Extract the package name from "pip install X"
        import re
        match = re.search(r"pip install\s+([a-zA-Z0-9_\-]+)", fix)
        if not match:
            return {"attempted": False, "reason": "could not parse package name"}

        package_name = match.group(1)
        print(f"📦 Detected missing package: {package_name}")

        # Step 1 — Create a new branch
        branch_name = create_fix_branch(repo)

        # Step 2 — Get current requirements.txt and add the package
        client_repo = get_github_client().get_repo(repo)
        current_file = client_repo.get_contents("requirements.txt", ref=branch_name)
        current_content = current_file.decoded_content.decode("utf-8")

        if package_name in current_content:
            return {"attempted": False, "reason": "package already in requirements.txt"}

        new_content = current_content.rstrip() + f"\n{package_name}\n"

        # Step 3 — Commit the change
        update_file_on_branch(
            repo_full_name=repo,
            branch_name=branch_name,
            file_path="requirements.txt",
            new_content=new_content,
            commit_message=f"fix: add missing dependency {package_name}"
        )

        # Step 4 — Open the PR
        pr_url = open_pull_request(
            repo_full_name=repo,
            branch_name=branch_name,
            title=f"🤖 Nexa: Add missing dependency '{package_name}'",
            body=f"""## Autonomous fix by Nexa

**Root cause:** {analysis.get('root_cause')}

**Fix applied:** Added `{package_name}` to `requirements.txt`

**Confidence:** {confidence}

---
*This PR was created autonomously by Nexa based on CI failure analysis and memory of past similar failures.*
"""
        )

        # Extract PR number from URL (last part of https://github.com/owner/repo/pull/123)
        pr_number = int(pr_url.split("/")[-1])
        return {"attempted": True, "success": True, "pr_url": pr_url, "pr_number": pr_number}

    except Exception as e:
        print(f"❌ Autonomous fix failed: {e}")
        return {"attempted": True, "success": False, "error": str(e)}