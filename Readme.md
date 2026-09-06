# agent-toolbox

An MCP tool server exposing sandboxed Python execution and read-only SQL
against a service database. Deployed independently of any agent that talks
to it -- it's a plain MCP server, usable by this project's `agent` repo or
by any other MCP client.

---

## Setup

```bash
uv sync --group dev
```

Copy `.env.example` to `.env` and fill in the paths/URLs:

```bash
cp .env.example .env
```

```bash
APP_ENV=debug
USER_DB_HOST=/absolute/path/to/sqlite
USER_DB_NAME=user
TOOLBOX_URL=http://127.0.0.1:8001/mcp
```

---

## Running it

```bash
make run
# uv run uvicorn bootstrap.application.toolbox_application:app --host 0.0.0.0 --port 8001
```

| | URL |
|---|---|
| MCP endpoint | `http://localhost:8001/mcp` |
| Health | `http://localhost:8001/agent_toolbox/actuator/health` |

Point any MCP client's connector `base_url` at the MCP endpoint above --
timeout, transport (`streamable_http`), and auth are configured the same
way as any other MCP connector.

---

## Configuration

Everything lives under `config/` -- `config/root.yml` plus
`config/debug/connector/*.yml`. `TOOLBOX_URL` must match whatever URL
clients use to reach this service; it's used to derive this server's own
ASGI mount path and allowed host, not to bind the listener (host/port for
that come from `TOOLBOX_HOST`/`TOOLBOX_PORT` or the `--host`/`--port` flags
passed to `uvicorn`).

---

## Development

```bash
make check       # lint + typecheck + tests
make test
make lint
make format
make typecheck
```

### Pre-commit hooks

```bash
uv run pre-commit install --hook-type pre-commit --hook-type pre-push
uv run pre-commit run --all-files --hook-stage pre-commit
```

### MCP inspection

```bash
npx @modelcontextprotocol/inspector
```

---

## Deploying

```bash
make docker_build
helm install agent-toolbox devops/helm -f devops/helm/values.yaml
```
