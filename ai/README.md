# Plane AI Gateway

Independent FastAPI service providing AI capabilities on top of **Plane
Community Edition** (self-hosted). See `docs/ai-features-plan.md` for the
full roadmap.

## Layout

```
ai/
├── app/
│   ├── main.py            # FastAPI entrypoint
│   ├── core/              # config + logging
│   ├── api/               # deps + routes (health, chat, execute, sessions)
│   ├── llm/               # provider adapters (DeepSeek / OpenAI-compatible)
│   ├── agent/             # orchestrator + read tools + write actions
│   ├── retrieval/         # embeddings + pgvector hybrid search (Phase 3)
│   ├── mcp/               # minimal MCP stdio client (Phase 5)
│   ├── plane/             # Plane REST client (X-Api-Key)
│   └── db/                # conversations/messages/audit/docs/skills/usage
├── tests/
├── Dockerfile
└── pyproject.toml
```

## Endpoints

| Method | Path          | Auth               | Purpose                              |
| ------ | ------------- | ------------------ | ------------------------------------ |
| GET    | `/health`     | none               | Liveness probe                       |
| GET    | `/ready`      | none               | Readiness (verifies Plane API key)   |
| POST   | `/chat`       | `X-AI-Gateway-Key` | SSE streaming agent chat             |
| POST   | `/execute`    | `X-AI-Gateway-Key` | Execute confirmed write actions     |
| POST   | `/retrieval/index` | `X-AI-Gateway-Key` | Index workspace documents        |
| POST   | `/editor/task`  | `X-AI-Gateway-Key` | Selection rewrite (paraphrase/simplify/…) |
| POST   | `/editor/ask`   | `X-AI-Gateway-Key` | Free instruction on selected text   |
| GET/POST/DELETE | `/skills` | `X-AI-Gateway-Key` | Slash-command skill templates |
| GET/POST/DELETE | `/mcp`    | `X-AI-Gateway-Key` | MCP connection management        |
| GET    | `/usage`       | `X-AI-Gateway-Key` | Usage metrics                     |
| GET/PUT | `/settings/ai` | `X-AI-Gateway-Key` | Per-workspace AI toggle         |
| GET    | `/sessions`   | `X-AI-Gateway-Key` | List conversations                  |
| GET    | `/sessions/{id}/messages` | `X-AI-Gateway-Key` | Conversation history |

`POST /chat` body: `{"message", "workspace_slug", "conversation_id"?, "mode"?}`.
`mode` is `ask` (default, read-only), `build` (plan → confirm → execute), or
`autopilot` (write directly). SSE events: `token`, `tool_call`, `tool_result`,
`plan`, `sources`, `done` (carries `conversation_id`), `error`.

`POST /execute` body: `{"workspace_slug", "conversation_id"?, "actions": [{"action", "params"}]}`,
returns `{"results": [...]}` and writes an audit log row per action.

`POST /retrieval/index` body: `{"workspace_slug"}` — syncs work items and
comments into the retrieval store (embedding + pgvector when configured;
keyword-only fallback otherwise).

> When routed through Caddy, `/ai/*` is stripped and forwarded here, e.g.
> `https://team.stableflow.ai/ai/health` → `/health`.

## Local development

```bash
cd ai
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env   # fill in API keys
uvicorn app.main:app --reload
```

Run tests:

```bash
pytest
```

## Configuration

All settings are environment variables prefixed with `AI_GATEWAY_`
(see `.env.example`). Key values:

- `AI_GATEWAY_PLANE_API_KEY` — Plane service-account API token (tool layer).
- `AI_GATEWAY_LLM_API_KEY` / `AI_GATEWAY_LLM_BASE_URL` / `AI_GATEWAY_LLM_MODEL`.
- `AI_GATEWAY_GATEWAY_API_KEY` — shared secret for the gateway's own endpoints.
- `AI_GATEWAY_DATABASE_URL` — Postgres DSN (Phase 1 sessions); defaults to
  local SQLite when unset.

## Compliance note

This service is an **independent program** that interacts with Plane only
through its public REST API. It does not import or modify Plane's AGPL core,
keeping the upgrade surface and license surface clean.
