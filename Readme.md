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

By default this service logs through **loguru**. To switch to Python's
**standard `logging`** module instead:

- Open `src/bootstrap/di/base_di.py`
- Replace the `LoguruLogger` import with `StandardLogger`
  (`from pycraftcore.logger.adapter import StandardLogger`)
- In `_logging`, replace `LoguruLogger()` with `StandardLogger()`
- In `_telemetry_provider`, remove the `self._logging.attach(log_handler)`
  line -- `StandardLogger` already flows into the same pipeline the OTel
  exporter is attached to at the root logger, so keeping that line would
  ship every log line twice
- Restart the service

No config file or environment variable change is needed -- this is a
one-line adapter swap in the composition root.

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
