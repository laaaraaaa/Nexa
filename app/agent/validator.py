from github import Github
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.memory.models import EpisodicMemory
from app.tools.github_client import get_github_client
import os


async def check_pr_ci_status(
    db: AsyncSession,
    repo_full_name: str,
    pr_number: int
) -> dict:
    """
    Checks if the CI on a Nexa-opened PR passed or failed.
    Called when GitHub sends a check_run webhook event.
    """
    client = get_github_client()
    repo = client.get_repo(repo_full_name)
    pr = repo.get_pull(pr_number)

    # Get all check runs for the PR's head commit
    commit = repo.get_commit(pr.head.sha)
    check_runs = commit.get_check_runs()

    statuses = []
    for check in check_runs:
        statuses.append({
            "name": check.name,
            "status": check.status,
            "conclusion": check.conclusion
        })

    # Determine overall result
    all_complete = all(s["status"] == "completed" for s in statuses)
    all_passed = all(s["conclusion"] == "success" for s in statuses)

    return {
        "pr_number": pr_number,
        "all_complete": all_complete,
        "all_passed": all_passed,
        "checks": statuses
    }


async def update_memory_with_fix_result(
    db: AsyncSession,
    pr_number: int,
    fix_successful: bool
) -> None:
    """
    Updates the episodic memory entry linked to this PR
    with whether the fix actually worked.
    This is how Nexa learns from its own fix attempts.
    """
    # Find the memory entry with this PR number
    result = await db.execute(
        select(EpisodicMemory).where(EpisodicMemory.pr_number == pr_number)
    )
    memory = result.scalar_one_or_none()

    if memory:
        memory.fix_successful = fix_successful
        await db.commit()
        if fix_successful:
            print(f"✅ Memory updated — fix for PR #{pr_number} marked SUCCESSFUL")
            print(f"   Nexa learned: '{memory.fix_attempted}' works for '{memory.error_type}'")
        else:
            print(f"❌ Memory updated — fix for PR #{pr_number} marked FAILED")
            print(f"   Nexa learned: '{memory.fix_attempted}' does NOT work for '{memory.error_type}'")
    else:
        print(f"⚠️ No memory entry found for PR #{pr_number}")