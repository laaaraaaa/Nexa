# DECISIONS.md

## Day 1 — Folder structure

Separated the project into agent/, memory/, api/, and tools/ 
to enforce separation of concerns. Each module has one job and 
can be tested and modified independently without breaking others.