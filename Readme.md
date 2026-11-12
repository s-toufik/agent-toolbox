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

The server is the reference for what it offers: an MCP client lists the tools (`tools/list`) with their descriptions and full input and output schemas — the agent does it at boot, then every minute. The tools available today:

| Tool | What it does | Inputs |
|---|---|---|
| `users_tables` | Read-only SQL on the service database (users dashboard, payment data). Anything that writes or changes the schema is refused before it reaches the database | `query`, `dialect` (optional) |
| `file_reader` | Returns a file's contents — parsed for `yml`, `yaml`, `json` and `csv`, as text for `md` and `txt` | `file_path`, optional `start` and `count` (a range of lines) |
| `file_writer` | Writes (replaces) a file in one of the same formats | `file_path`, `data` |
| `python_executor` | Runs Python for analysis or computation; the value of the variable `result` is returned, along with what the code printed. When the code fails, the error returns what it printed before failing and the traceback of its own lines (line numbers and source), so the model can fix it | `code` |

| `grafana_*` | Grafana's MCP server: search and read dashboards, datasources, alert rules, PromQL and Loki queries | per tool (see `tools/list`) |
| `mongodb_*` | MongoDB's MCP server: list databases and collections, schema, find, aggregate, count — writes only when the deployment allows them | per tool |
| `postgres_*` | PostgreSQL's MCP server (postgres-mcp): schemas, objects, `execute_sql`, explain, health — read-only unless the deployment allows writes | per tool |

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

### Tools from other MCP servers

The toolbox also republishes the tools of other MCP servers, as its own: listed in `tools/list`, called the same way, and available as functions in `python_executor` code. Each server's tools carry its prefix, and names are made valid Python (`list-databases` → `mongodb_list_databases`):

| Server | Prefix | URL variable | Transport |
|---|---|---|---|
| [Grafana MCP](https://github.com/grafana/mcp-grafana) | `grafana_` | `GRAFANA_MCP_URL` | streamable HTTP |
| [MongoDB MCP Server](https://github.com/mongodb-js/mongodb-mcp-server) | `mongodb_` | `MONGODB_MCP_URL` | streamable HTTP |
| [postgres-mcp](https://github.com/crystaldba/postgres-mcp) | `postgres_` | `POSTGRES_MCP_URL` | SSE |

```python
databases = mongodb_list_databases()
rows = postgres_execute_sql(sql="SELECT schemaname, COUNT(*) FROM pg_tables GROUP BY 1")
result = {"databases": databases["result"], "tables": rows["result"]}
```

- A server whose URL is empty is skipped. The others are read at start-up and again in the background, so the order the pods start in doesn't matter:
  - each server has its own loop, so one that is down never changes how often the others are read;
  - a server that doesn't answer is retried after 5 s, then 10, 20, 40, and every 60 s; its tools appear as soon as it answers, with no restart;
  - a server that answers is re-read every 60 s, so tools it adds, changes or drops follow (`python_executor`'s list of functions too);
  - these numbers are the `refresh` block of each connector in `config/<APP_ENV>/connector/mcp.yml` (`interval`, `retry_delay`, `max_retry_delay`); `MCP_REFRESH_INTERVAL`, `MCP_RETRY_DELAY` and `MCP_MAX_RETRY_DELAY` change them for every server. Leave a variable unset rather than empty, or the configuration fails to load;
  - a server that stops answering keeps its tools listed: a call returns "its server may be down or restarting; try again later" until it's back.
- `/actuator/health` lists each server (`UP`, or `DOWN` since when and why). The readiness probe stays about the toolbox itself, so one server down never takes the toolbox's own tools away.
- What each server may do (read-only or read-write, which tools) is decided where it runs; the toolbox republishes what it offers.
- To keep only some of a server's tools, list their remote names under its operation's `tools` in `config/<APP_ENV>/operation/mcp.yml`.

**Add another server:** a connector named `external_mcp_<name>` in `config/<APP_ENV>/connector/mcp.yml` (its URL from an environment variable, `''` by default), an operation of the same name with its `prefix` in `config/<APP_ENV>/operation/mcp.yml`, both listed in `config/root.yml`, and the variable in `.env.example` and `devops/helm/values.yml`.

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
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` or `CRITICAL`, in upper case; read by `root.yml` (`log`), `INFO` when unset |
| `CONFIGURATION_DIR` | Where `config/` is (`./config` by default) |
| `DEPLOYMENT_ENVIRONMENT` | Label shown by `/actuator/info` and on telemetry |
| `TOOLBOX_URL` | The URL clients use, e.g. `http://<host>:<port>/mcp`. Sets the MCP path and the allowed host; the listening address comes from Granian (`--host`/`--port`, or `GRANIAN_HOST`/`GRANIAN_PORT` in Docker) |
| `TOOLBOX_EXTRA_ALLOWED_HOSTS` | Other `host:port` values clients may use, comma-separated |
| `WORKING_DIRECTORY` | The folder file tools and the sandbox are confined to; unset = no working directory |
| `SANDBOX_TOOL_ACCESS` | `true` to make the tools callable from `python_executor` code |
| `GRAFANA_MCP_URL`, `MONGODB_MCP_URL`, `POSTGRES_MCP_URL` | Other MCP servers whose tools are republished (see [Tools from other MCP servers](#tools-from-other-mcp-servers)); empty = skipped |
| `OTEL_HOST`, `OTEL_PORT` | OpenTelemetry collector (gRPC); an empty host turns telemetry off |

Tools that reach a backend add their own settings, read through a connector in `config/<APP_ENV>/connector/`. Today the SQL tool reads its SQLite database from `USER_DB_HOST` (folder) and `USER_DB_NAME` (file). `.env.example` is the reference for the full list.

Configuration files are in `config/`: `root.yml` sets the log level and lists what exists, and `config/<APP_ENV>/connector/` defines the MCP server itself, telemetry, and each backend a tool uses. `root.yml` keeps `server: {}`: the MCP endpoint is not one of the web servers `server/*.yml` describes.

### Logs

One format for every line the service writes; the third column is the request id sent by the client in `X-Request-ID`. Tool calls made from sandboxed code keep the id of the request that started them.

```text
2026-09-27 10:47:47.785 | INFO     | my-conversation | invoke_tool_usecase:invoke:23 - tool 'file_reader' invoked
```

With `OTEL_HOST` set, the same lines also go to the OpenTelemetry collector. Granian's own start and stop lines (`[INFO] Starting granian…`) keep Granian's format; access-log lines carry no request id.

With `OTEL_HOST` set, every MCP request is a span (`tools/list`, `tools/call <tool>`). A caller that sends its trace context in the request's `_meta`, as the MCP SDK does, gets the toolbox's span in its own trace: the agent's tool calls appear under its `run_tools` step. Notifications (`notifications/initialized`) get no span, so they don't add a one-span trace per session.

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
| `src/agent_toolbox/domain/` | `WorkingDirectory`, `SandboxRun`, `DependencyHealth`, `RefreshPolicy` (the backoff), `ToolFailure`, `UnknownToolException` |
| `src/agent_toolbox/application/` | `InvokeToolUseCase`, `ReconcileExternalTools`, `ToolCatalog` (the live list of tools), and their ports: `Tool` (the base every tool extends), `ToolLookup`, `ToolProvider`, `ToolPublisher`, `CodeSandboxPort` |
| `src/agent_toolbox/adapter/inbound/mcp/` | `ToolBinder` (tools → MCP), `McpToolPublisher` (adds and removes tools while it runs), the ASGI app and allowed hosts, the actuator routes |
| `src/agent_toolbox/adapter/inbound/sandbox/` | `SandboxToolBridge`: lets sandboxed code call the tools |
| `src/agent_toolbox/adapter/outbound/` | The tools, one folder per area (`sql/`, `file/`, `code/`, … ), `mcp/` (other MCP servers' tools, prefixed), and `sandbox/` (`PythonSandbox`) |
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

    async def run(self, arguments: CountRowsInput) -> CountRowsOutput: ...
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

On the homelab it runs as a Helm release: [`devops/helm/values.yml`](devops/helm/values.yml) is how it runs there (env variables, Secrets it reads, port, probes, volumes). homelab-infra adds only this server's choices, in `apps/agent-toolbox/values.yaml.gotmpl` (its NetworkPolicy: who may call it and what it may reach).

#### Git flow: what each branch and tag publishes

```text
 feature/…  ──PR──►  develop  ──PR──►  main
                        │                  │
                        └─ tag             └─ tag vX.Y.Z               a release
                           vX.Y.Z-rc.N        image toufik142/agent-toolbox:X.Y.Z and :latest
                           image :X.Y.Z-rc.N  chart oci://ghcr.io/s-toufik/charts/agent-toolbox:X.Y.Z
                           and :dev           deployed once homelab-infra's versions.yaml says X.Y.Z
                           (never deployed)
```

| Event | CI ([`.github/workflows/cicd.yml`](.github/workflows/cicd.yml)) | Publishes | On the homelab |
|---|---|---|---|
| Pull request to `develop` or `main` | LINT, TYPECHECK, TEST, BUILD | nothing | nothing changes |
| Push to `develop` or `main` | the same | nothing | nothing changes |
| Tag `vX.Y.Z-rc.N` on a commit only on `develop` | the same + RELEASE TARGET + PUBLISH | image `:X.Y.Z-rc.N` and `:dev` | nothing changes |
| Tag `vX.Y.Z` on a commit of `main` | the same + RELEASE TARGET + PUBLISH + CHART | image `:X.Y.Z` and `:latest`, chart `agent-toolbox:X.Y.Z` | nothing yet: deployed once homelab-infra asks for `X.Y.Z` |

- Only tags publish: `:dev` is the last pre-release, `:latest` the last release. Only tags on `main` reach the homelab; to try a pre-release there, homelab-infra's Q&A, *How do I deploy a dev image of the agent?*
- RELEASE TARGET finds the branch the tag is on, the same job in every repository with this pipeline (pycraftcore and homelab-ui too). A commit on both branches counts as `main`. It refuses a tag on neither branch, a pre-release on `main` and a final version only on `develop`, and then nothing is published.

#### What is deployed

The homelab runs the version in homelab-infra's [`environments/versions.yaml`](https://github.com/s-toufik/homelab-infra/blob/develop/environments/versions.yaml), `apps.agentToolbox`. On the server:

```bash
helm -n homelab list --filter '^agent-toolbox$'      # CHART agent-toolbox-X.Y.Z, APP VERSION X.Y.Z
kubectl -n homelab get deploy agent-toolbox -o jsonpath='{.spec.template.spec.containers[0].image}'; echo
```

#### Release a version

1. Merge `develop` into `main` (pull request); CI is green.
2. Tag `main`:
   ```bash
   git switch main && git pull
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```
3. **Actions**: PUBLISH and CHART are green.
4. In homelab-infra: `apps.agentToolbox: X.Y.Z` in `environments/versions.yaml`, commit, push.
5. On the server, in homelab-infra: `git pull`, `make diff R=agent-toolbox`, `make apply R=agent-toolbox` (raw: `helmfile -l name=agent-toolbox apply`).
6. Check: the `helm list` above shows `X.Y.Z`; `make logs R=agent-toolbox`.

Roll back: set the previous version in `versions.yaml` and `make apply R=agent-toolbox`, or right away `make rollback R=agent-toolbox` (raw: `helm -n homelab rollback agent-toolbox`). The step-by-step version is homelab-infra's DevOps guide, **Release an app** and **Roll back**.

The image is served by [Granian](https://github.com/emmett-framework/granian), configured with `GRANIAN_*` variables in the Dockerfile (ASGI interface, factory, host, port, access log). Set any other Granian option the same way in your deployment, without rebuilding: for example `GRANIAN_WORKERS=2` for two worker processes (each one builds its own server and tools), or `GRANIAN_WORKERS_MAX_RSS=1024` to restart a worker that grows above 1 GiB — useful here, since `python_executor` runs user code.
