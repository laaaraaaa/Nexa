## Day 1 — Project setup and webhook receiver

Chose FastAPI over Flask because it supports async out of the box which 
will matter when the agent is making multiple API calls at once. Built a 
webhook receiver that listens for GitHub CI failure events and verifies 
the request signature to make sure it actually came from GitHub.

## Day 2 — Cloudflared tunnel and GitHub webhook

We set up Cloudflared tunnel, a tool that gives your local server a public URL so GitHub can send webhook events to it. Without it GitHub can't reach your laptop because it's behind a home network. Then we registered that URL as a webhook on your GitHub repo and told it to fire on workflow_run events. We also created a failing GitHub Actions workflow to test it.

## Day 3 — PostgreSQL + pgvector + episodic memory table

Chose PostgreSQL with pgvector over dedicated vector databases like Pinecone because we already need PostgreSQL for storing structured data like repo names, error messages, and fix history. Adding pgvector means we get vector similarity search in the same database without managing a second service. The error_embedding column stores a numerical representation of the error message, this lets Nexa find similar past failures by comparing vectors instead of doing exact text matching.

