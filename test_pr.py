import asyncio
from app.agent.orchestrator import attempt_autonomous_fix

async def test():
    fake_analysis = {
        "fix": "pip install requests",
        "confidence": "HIGH",
        "root_cause": "Missing requests package causing ModuleNotFoundError"
    }
    
    result = await attempt_autonomous_fix(
        repo="laaaraaaa/Nexa",
        analysis=fake_analysis
    )
    print(f"\nFinal result: {result}")

asyncio.run(test())