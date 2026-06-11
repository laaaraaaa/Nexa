## Day 1 — Project setup and webhook receiver

Chose FastAPI over Flask because it supports async out of the box which 
will matter when the agent is making multiple API calls at once. Built a 
webhook receiver that listens for GitHub CI failure events and verifies 
the request signature to make sure it actually came from GitHub.