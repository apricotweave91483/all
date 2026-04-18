# Simple Agent Case 2

This case is intentionally tiny. It is meant to test whether the agent can:

- inspect a one-file workspace
- make a targeted edit in the correct file
- preserve function behavior
- run a simple verification command

Suggested prompt:

```bash
agent 'rename format_name to format_full_name, update the call site, and run python3 app.py to verify it still prints the full name'
```
