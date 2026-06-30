import redis
import json
import os


# Connect to Redis
_redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)


def set_active_run(repo: str, run_data: dict, ttl_seconds: int = 3600) -> None:
    """
    Stores the current active run data in Redis.
    This is Nexa's short-term working memory — what it's currently doing.
    TTL of 1 hour means it auto-expires if something goes wrong.
    """
    key = f"active_run:{repo}"
    _redis_client.setex(key, ttl_seconds, json.dumps(run_data))
    print(f"🔴 Redis: stored active run for {repo}")


def get_active_run(repo: str) -> dict | None:
    """
    Retrieves the current active run for a repo.
    Returns None if no active run exists (expired or never set).
    """
    key = f"active_run:{repo}"
    data = _redis_client.get(key)
    if data:
        return json.loads(data)
    return None


def clear_active_run(repo: str) -> None:
    """
    Clears the active run once it's complete.
    Called when the validator finishes processing.
    """
    key = f"active_run:{repo}"
    _redis_client.delete(key)
    print(f"✅ Redis: cleared active run for {repo}")


def set_fix_in_progress(repo: str, pr_number: int, fix_data: dict) -> None:
    """
    Tracks that a fix PR is currently open and being validated.
    Prevents Nexa from opening duplicate PRs for the same failure.
    """
    key = f"fix_in_progress:{repo}:{pr_number}"
    _redis_client.setex(key, 86400, json.dumps(fix_data))  # 24 hour TTL
    print(f"🔧 Redis: tracking fix PR #{pr_number} for {repo}")


def get_fix_in_progress(repo: str, pr_number: int) -> dict | None:
    """
    Check if a fix is already in progress for this repo/PR.
    """
    key = f"fix_in_progress:{repo}:{pr_number}"
    data = _redis_client.get(key)
    if data:
        return json.loads(data)
    return None


def clear_fix_in_progress(repo: str, pr_number: int) -> None:
    """
    Clears the fix tracking once the PR is resolved.
    """
    key = f"fix_in_progress:{repo}:{pr_number}"
    _redis_client.delete(key)
    print(f"✅ Redis: cleared fix tracking for PR #{pr_number}")


def is_repo_being_processed(repo: str) -> bool:
    """
    Check if Nexa is already processing a failure for this repo.
    Prevents duplicate processing if webhooks fire multiple times.
    """
    key = f"active_run:{repo}"
    return _redis_client.exists(key) == 1