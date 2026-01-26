# Runtime Planner & Scripts

Velu can take a **Blueprint** and produce a **runtime plan** plus concrete
**run scripts** for a target OS (Linux, macOS, Windows).

Core agents:

- `services.agents.runtime_planner`
- `services.agents.runtime_recipe`
- `services.agents.runtime_script_writer`
- CLI entrypoints in `services.console.runtime_plan_cli`

---

## 1. From Blueprint → Runtime

Example blueprint (FastAPI + Next.js):

```python
blueprint = {
  "id": "demo_project",
  "name": "Demo Project",
  "kind": "web_app",
  "frontend": {
    "framework": "nextjs",
    "language": "typescript",
    "targets": ["web"],
  },
  "backend": {
    "framework": "fastapi",
    "language": "python",
    "style": "rest",
  },
  "database": {
    "engine": "sqlite",
    "mode": "single_node",
  },
  "localization": {
    "default_language": "en",
    "supported_languages": ["en", "fr"],
  },
}
