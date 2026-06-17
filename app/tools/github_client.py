from github import Github
import os


def get_github_client():
    """
    Returns an authenticated GitHub client using our personal access token.
    """
    token = os.getenv("GITHUB_TOKEN")
    return Github(token)


def get_workflow_run_logs(repo_full_name: str, run_id: int) -> str:
    """
    Fetches the actual failure logs for a specific workflow run.
    
    repo_full_name: e.g. "laaaraaaa/Nexa"
    run_id: the GitHub Actions run ID (comes from the webhook payload)
    
    Returns the raw log text so the LLM can analyze the real error,
    not just the workflow name.
    """
    client = get_github_client()
    repo = client.get_repo(repo_full_name)
    run = repo.get_workflow_run(run_id)

    # Get all jobs in this run
    jobs = run.jobs()

    logs_summary = []
    for job in jobs:
        if job.conclusion == "failure":
            logs_summary.append(f"Job: {job.name}")
            logs_summary.append(f"Status: {job.conclusion}")
            
            # Get the steps that failed
            for step in job.steps:
                if step.conclusion == "failure":
                    logs_summary.append(f"  Failed step: {step.name}")

    return "\n".join(logs_summary) if logs_summary else "No detailed failure info found"


def get_recent_commits(repo_full_name: str, limit: int = 3) -> list[dict]:
    """
    Gets the most recent commits to a repo.
    Useful context — recent changes might be what caused the failure.
    """
    client = get_github_client()
    repo = client.get_repo(repo_full_name)
    commits = repo.get_commits()[:limit]

    return [
        {
            "sha": c.sha[:7],
            "message": c.commit.message,
            "author": c.commit.author.name
        }
        for c in commits
    ]