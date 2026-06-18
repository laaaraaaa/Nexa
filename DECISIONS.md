# DECISIONS.md

## Decision 1 — Chose FastAPI over Flask

FastAPI supports async out of the box which matters because the orchestrator 
will be making multiple concurrent API calls. Also has built-in Pydantic 
validation which we'll use heavily for agent message schemas.

## Decision 2 — Separated project into modules

Split into agent/, memory/, api/, and tools/ folders to enforce separation 
of concerns. Each module has one job and can be tested and modified 
independently without breaking others.

## Decision 3 — Webhook signature verification

GitHub signs every webhook payload with HMAC-SHA256. We verify this to ensure 
only GitHub can trigger our agent. Skipped in dev if secret is empty to make 
local testing easier.

## Decision 4 — PostgreSQL + pgvector over dedicated vector DB

We already need PostgreSQL for structured data like repo names, error messages, 
and fix history. Adding pgvector gives us vector similarity search in the same 
database without managing a second service like Pinecone.

## Decision 5 — UUIDs over auto-incrementing integers

Used UUIDs as primary keys so memory IDs are globally unique and unpredictable. 
Auto-incrementing IDs are sequential and expose how many records exist — UUIDs 
are safer and work better in distributed systems.

## Decision 6 — Episodic memory as the first memory layer

Started with episodic memory (what happened) before semantic or procedural 
because it's the foundation everything else builds on. You can't derive 
patterns without first recording raw events.

## Decision 7 — Only attempt autonomous fixes on HIGH confidence

If Nexa automatically applies a fix it's not sure about, it could introduce 
a broken change on top of the original failure — making things worse. Lower 
confidence fixes are surfaced to humans instead of acted on automatically. 
This is the human-in-the-loop pattern: automate what you're sure about, 
escalate what you're not.
