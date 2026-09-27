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
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING or ERROR
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
ASGI mount path and allowed host, not to bind the listener (the listener's
host/port come from the `--host`/`--port` flags passed to `uvicorn`).

Only the Host header matching `TOOLBOX_URL` is accepted by default (DNS
rebinding protection, from the `mcp` SDK's transport security) -- any other
Host gets a `421 Invalid Host header`. If another client reaches this
service a different way (e.g. a LAN hostname, testing directly from
Postman), add it to `TOOLBOX_EXTRA_ALLOWED_HOSTS` (comma-separated) instead
of changing `TOOLBOX_URL`, which would break clients using the original
host.

---

## Logging

Standard Python `logging`, one format for every line (set up by pycraftcore's
`configure_logging`):

```
2026-09-27 10:47:47.785 | INFO     | demo-logging-123 | invoke_tool_usecase:invoke:23 - tool 'file_reader' invoked
```

- `LOG_LEVEL` sets the level (`INFO` by default).
- The third column is the request id (the `X-Request-ID` header sent by the orchestrator); it
  appears on every line of that request by itself, `-` outside one. Tool calls the sandbox makes
  from `python_executor` code keep the id of the request that started it. Do not put it in log
  messages.
- With `OTEL_HOST`/`OTEL_PORT` set, the same lines also go to the OpenTelemetry collector
  (Loki), with `request_id` as an attribute.

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
