# project-forge

project-forge is a personal project scaffolding platform with a VS Code-integrated CLI.
It lets you spin up production-minded starter repositories from reusable templates.

## Requirements

- Python 3.11+
- Docker + Docker Compose

## Monorepo Layout

- templates/: reusable template source folders
- projects/: generated projects land here
- forge.py: standard-library-only scaffold engine
- forge.json: template registry
- .vscode/tasks.json: VS Code task integration

## Quickstart

1. Set optional author override:
   - export FORGE_AUTHOR="Your Name"
2. Create a project:
   - python forge.py fastapi my-api
3. Start the generated project:
   - cd projects/my-api
   - docker compose up --build

## Placeholder Tokens

Template files may contain the following placeholders:

- {{project_name}}
- {{author}}
- {{created_at}}

During scaffolding, forge.py replaces them across all text files in the generated project.

## VS Code Task

Run the task named "🔨 Forge: New Project" from VS Code.
It prompts for template and project name, then runs python forge.py <template> <name>.

## Template Keys

- fastapi
- flask
- django
- langchain-rag
- multi-agent
- fine-tuning
- streamlit
- tableau-embed
- fastapi-react
- flask-nextjs
