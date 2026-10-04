# agent-toolbox

An MCP server that gives an agent hands: tools to query data, work with files and run Python for analysis — and a sandbox where those tools are callable as plain functions. New tools are added over time; every client discovers the current set over MCP.

It is a standard MCP server: the homelab agent uses it, and so can any MCP client.

**[Using the toolbox](#using-the-toolbox)** — run it, connect a client, know what each tool does.
**[Working on the toolbox](#working-on-the-toolbox)** — how it is built and how to add a tool.

```text
                         ┌──────────────────────────────────────────────┐
  agent / MCP client ───►│  agent-toolbox                    /mcp       │
  (X-Request-ID)         │                                              │
                         │  data tools ───────► databases, files, …     │
                         │  python_executor ─► sandbox ─┬─► working dir │
                         │                              └─► data tools  │
                         └──────────────────────────────────────────────┘
```

---

## Using the toolbox

### Run it

Requirements: Python 3.14 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --group dev
cp .env.example .env      # fill in the paths and the URL clients will use
make run
```

| | Endpoint |
|---|---|
| MCP (streamable HTTP) | `http://<host>:<port>/mcp` |
| Health | `GET http://<host>:<port>/actuator/health` (also `/health/liveness`, `/health/readiness`) |
| Version | `GET http://<host>:<port>/actuator/info` |

`/health/readiness` answers `503` until the server has tools registered.

With Docker: `make docker_build` builds the image.

### The tools

The server is the reference for what it offers: an MCP client lists the tools (`tools/list`) with their descriptions and full input and output schemas — the agent does it at boot. The tools available today:

| Tool | What it does | Inputs |
|---|---|---|
| `users_tables` | Read-only SQL on the service database (users dashboard, payment data). Anything that writes or changes the schema is refused before it reaches the database | `query`, `dialect` (optional) |
| `file_reader` | Returns a file's contents — parsed for `yml`, `yaml`, `json` and `csv`, as text for `md` and `txt` | `file_path`, optional `start` and `count` (a range of lines) |
| `file_writer` | Writes (replaces) a file in one of the same formats | `file_path`, `data` |
| `python_executor` | Runs Python for analysis or computation; the value of the variable `result` is returned, along with what the code printed | `code` |

A call with invalid arguments gets an error naming the bad fields. Every tool added later follows the same rules: published with its schema, callable directly and from the sandbox.

**The working directory.** When `WORKING_DIRECTORY` is set, every file a tool reads or writes lives there, and relative paths name the same file in a tool call and inside `python_executor` code. Access outside it is refused.

**The Python sandbox** runs each piece of code in its own process:

- allowed modules: pandas, numpy, matplotlib, datetime and the rest of pycraftcore's allowlist (listed in the tool's description);
- 256 MB of memory, at most 8 runs at a time, and a hard timeout;
- with `SANDBOX_TOOL_ACCESS=true`, the other tools are available inside the code as functions that return exactly what the tool returns:

```python
import pandas as pd

rows = users_tables(query="SELECT country, COUNT(*) AS users FROM users GROUP BY country")
df = pd.DataFrame(rows["rows"])
file_writer(file_path="users_by_country.csv", data=df.to_csv(index=False))
result = df.sort_values("users", ascending=False).head(3).to_dict("records")
```

### Connect a client

Point the client's MCP connector at `http://<host>:<port>/mcp` with the `streamable_http` transport. The homelab agent's connector:

```yaml
toolbox:
  name: toolbox
  type: mcp
  base_url: ${oc.env:TOOLBOX_URL}
  timeout: 30
  transport: streamable_http
```

To try the tools by hand, the MCP Inspector works against the same URL:

```bash
npx @modelcontextprotocol/inspector
```

**Allowed hosts.** Only requests whose `Host` matches `TOOLBOX_URL` are accepted (protection against DNS rebinding); any other host gets `421 Invalid Host header`. When clients reach the toolbox under another name — a LAN hostname, a Tailscale name, a tool like Postman — list it in `TOOLBOX_EXTRA_ALLOWED_HOSTS` rather than changing `TOOLBOX_URL`.

### Configure it

| Variable | Meaning |
|---|---|
| `APP_ENV` | Which `config/<APP_ENV>/` folder is read (`debug` by default) |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING` or `ERROR` |
| `CONFIGURATION_DIR` | Where `config/` is (`./config` by default) |
| `DEPLOYMENT_ENVIRONMENT` | Label shown by `/actuator/info` and on telemetry |
| `TOOLBOX_URL` | The URL clients use, e.g. `http://<host>:<port>/mcp`. Sets the MCP path and the allowed host; the listening address comes from `uvicorn` |
| `TOOLBOX_EXTRA_ALLOWED_HOSTS` | Other `host:port` values clients may use, comma-separated |
| `WORKING_DIRECTORY` | The folder file tools and the sandbox are confined to; unset = no working directory |
| `SANDBOX_TOOL_ACCESS` | `true` to make the tools callable from `python_executor` code |
| `OTEL_HOST`, `OTEL_PORT` | OpenTelemetry collector (gRPC); an empty host turns telemetry off |

Tools that reach a backend add their own settings, read through a connector in `config/<APP_ENV>/connector/`. Today the SQL tool reads its SQLite database from `USER_DB_HOST` (folder) and `USER_DB_NAME` (file). `.env.example` is the reference for the full list.

Configuration files are in `config/`: `root.yml` lists what exists, and `config/<APP_ENV>/connector/` defines the MCP server itself, telemetry, and each backend a tool uses.

### Logs

One format for every line; the third column is the request id sent by the client in `X-Request-ID`. Tool calls made from sandboxed code keep the id of the request that started them.

```text
2026-09-27 10:47:47.785 | INFO     | my-conversation | invoke_tool_usecase:invoke:23 - tool 'file_reader' invoked
```

With `OTEL_HOST` set, the same lines also go to the OpenTelemetry collector.

---

## Working on the toolbox

### Architecture

Hexagonal, like the agent: the use case and the tools know nothing about MCP. `tests/architecture/test_boundaries.py` enforces it (no agent, LangChain or LangGraph imports; no framework in the domain; no transport in the application).

```text
  MCP request ──► ToolBinder ──────────► InvokeToolUseCase ──► Tool.run
  (inbound)       one MCP tool per Tool  validates arguments    │
                  schemas from models    logs, maps failures    ├─► a data tool ──► its backend
                                                                │   (database, files, API, …)
  sandboxed code ─► SandboxToolBridge ──► InvokeToolUseCase     └─► ExecutePython ──► PythonSandbox
  (python_executor)  same use case, same tools, same request id                      (pycraftcore)
```

Direct calls and calls from sandboxed code go through the same `InvokeToolUseCase`, so they return the same thing — `tests/contract/test_tool_parity.py` checks it.

### Project layout

| Path | What it holds |
|---|---|
| `src/agent_toolbox/domain/` | `WorkingDirectory`, `SandboxRun`, `ToolFailure`, `UnknownToolException` |
| `src/agent_toolbox/application/` | `InvokeToolUseCase` and its ports: `Tool` (the base every tool extends), `CodeSandboxPort` |
| `src/agent_toolbox/adapter/inbound/mcp/` | `ToolBinder` (tools → MCP), the ASGI app and allowed hosts, the actuator routes |
| `src/agent_toolbox/adapter/inbound/sandbox/` | `SandboxToolBridge`: lets sandboxed code call the tools |
| `src/agent_toolbox/adapter/outbound/` | The tools, one folder per area (`sql/`, `file/`, `code/`, … ), and `sandbox/` (`PythonSandbox`) |
| `src/bootstrap/` | Settings, `ToolboxDI` (wiring only), the application |
| `tests/` | Unit, architecture and contract tests |

### Adding a tool

1. Define its input and output as pydantic models (`adapter/outbound/<area>/model/`). Field descriptions become the MCP schema the agent reads.
2. Subclass `Tool[Input, Output]` with a `name`, a `description` written for the model, and `async run(arguments)`. Raise `ToolFailure` with a clear message when the call can't be served.
3. If it needs a backend (a database, an API, …), add a connector in `config/<APP_ENV>/connector/`, list it in `config/root.yml`, put its variables in `.env.example`, and build the client in `ToolboxDI` from that connector.
4. Register it in `ToolboxDI._invoke_tool_use_case`. It is then published over MCP and, when `SANDBOX_TOOL_ACCESS` is on, callable from `python_executor` code — no change needed in the agent, which discovers it at its next start.
5. Add unit tests next to the others, and its row to [The tools](#the-tools).

```python
class CountRows(Tool[CountRowsInput, CountRowsOutput]):
    name = "count_rows"
    description = "Count the rows of a table in the service database."
    input_model = CountRowsInput
    output_model = CountRowsOutput

    async def run(self, arguments: CountRowsInput) -> CountRowsOutput:
        ...
```

### Tests and checks

```bash
make check        # ruff + ty + pytest
make test
make lint / make format / make typecheck
```

Pre-commit hooks:

```bash
uv run pre-commit install --hook-type pre-commit --hook-type pre-push
```

### Deploying

`make docker_build` builds `agent-toolbox:local`. It listens on port 8001; set the environment variables above on the container, with `TOOLBOX_URL` matching the address clients use.
