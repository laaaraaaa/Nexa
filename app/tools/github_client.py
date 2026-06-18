from github import Github
import os
import base64


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


def create_fix_branch(repo_full_name: str, base_branch: str = "main") -> str:
    """
    Creates a new branch for the fix attempt.
    Returns the branch name so we can use it later.
    """
    client = get_github_client()
    repo = client.get_repo(repo_full_name)

    # Get the latest commit SHA on the base branch
    base_ref = repo.get_branch(base_branch)
    base_sha = base_ref.commit.sha

    # Create a unique branch name using a short timestamp
    import time
    branch_name = f"nexa-fix-{int(time.time())}"

    repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_sha)
    print(f"🌿 Created branch: {branch_name}")
    return branch_name


def update_file_on_branch(
    repo_full_name: str,
    branch_name: str,
    file_path: str,
    new_content: str,
    commit_message: str
) -> bool:
    """
    Updates a file's content on a specific branch and commits it.
    """
    client = get_github_client()
    repo = client.get_repo(repo_full_name)

    # Get the current file to know its SHA (needed to update it)
    file = repo.get_contents(file_path, ref=branch_name)

    repo.update_file(
        path=file_path,
        message=commit_message,
        content=new_content,
        sha=file.sha,
        branch=branch_name
    )
    print(f"📝 Updated {file_path} on branch {branch_name}")
    return True


def open_pull_request(
    repo_full_name: str,
    branch_name: str,
    title: str,
    body: str,
    base_branch: str = "main"
) -> str:
    """
    Opens a pull request from the fix branch into main.
    Returns the PR URL.
    """
    client = get_github_client()
    repo = client.get_repo(repo_full_name)

    new_pr = repo.create_pull(
        title=title,
        body=body,
        head=branch_name,
        base=base_branch
    )
    print(f"🚀 Pull request opened: {new_pr.html_url}")
    return new_pr.html_url