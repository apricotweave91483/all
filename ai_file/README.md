Usage:
  ```bash
  ai_file "prompt"
  echo "prompt" | ai_file
  ```
Generates file contents on stdout using Ollama model gemma4:e2b by default.
Operational messages go to stderr so stdout can be redirected directly into a file.
For generating scripts quickly
