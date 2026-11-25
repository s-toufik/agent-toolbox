# agent-toolbox

An MCP server that gives an agent hands: tools to query data, work with files and run Python for analysis — and a sandbox where those tools are callable as plain functions. New tools are added over time; every client discovers the current set over MCP.

It is a standard MCP server: the homelab agents use it, and so can any MCP client. It serves its tools by scope, one endpoint each, so every agent discovers only the tools meant for it (see [Scopes](#scopes)).

**[Using the toolbox](#using-the-toolbox)** — run it, connect a client, know what each tool does.
**[Working on the toolbox](#working-on-the-toolbox)** — how it is built and how to add a tool.

```text
                         ┌──────────────────────────────────────────────┐
  agent / MCP client ───►│  agent-toolbox      /mcp (all) · /mcp/<scope>│
  (X-Request-ID)         │                                              │
                         │  data tools ───────► databases, files, …     │
                         │  python_executor ─► sandbox ─┬─► working dir │
                         │  (per scope that lists it)   └─► its scope's │
                         │                                  data tools  │
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
| Token | `POST http://<host>:<port>/auth/token` with `{"username": …, "expire": …}` (see [Connect a client](#connect-a-client)) |

`/health/readiness` answers `503` until the server has tools registered.

With Docker: `make docker_build` builds the image.

### The tools

The server is the reference for what it offers: an MCP client lists the tools (`tools/list`) with their descriptions and full input and output schemas — the agent does it at boot, then every minute. The tools available today:

| Tool | What it does | Inputs |
|---|---|---|
| `users_tables` | Read-only SQL on the service database (users dashboard, payment data). Anything that writes or changes the schema is refused before it reaches the database | `query`, `dialect` (optional) |
| `file_reader` | Returns a file's contents: a document for `json`, `yml` and `yaml`; rows for `csv`, `xlsx`, `xls` (first sheet) and `parquet`, with dates as ISO strings and binary cells in base64; text for `md`, `txt` and `svg`. A range of lines (`start`, `count`) only for text files | `file_path`, optional `start` and `count` (a range of lines) |
| `file_writer` | Writes (replaces) a file in one of the same formats — a list of row objects for `csv`, `xlsx` and `parquet`; `xls` is read-only | `file_path`, `data` |
| `python_executor` | Runs Python for analysis or computation; the value of the variable `result` is returned, along with what the code printed. When the code fails, the error returns what it printed before failing and the traceback of its own lines (line numbers and source), so the model can fix it | `code` |


The tools of other MCP servers are described in [Tools from other MCP servers](#tools-from-other-mcp-servers), and the tools a scope builds on them in [Scopes](#scopes).

#### Parameters

##### `users_tables`

Execute read-only SQL queries against the service database, which holds service information such as the users dashboard and payment data. Forbidden operations: Insert, Update, Delete, Merge, Create, Drop, Alter, TruncateTable, Transaction, Commit, Rollback, Attach, Detach.

| Parameter | Type | | Description |
|---|---|---|---|
| `query` | `str` | required | SQL query to execute. |
| `dialect` | `str` | default `'sqlite'` | sqlglot source dialect. |

##### `file_reader`

Read a file and return its contents: a document for json, yml, yaml; rows for csv, xlsx, xls, parquet (the first sheet of a workbook); text for md, txt, svg. start and count read lines of a text file.

| Parameter | Type | | Description |
|---|---|---|---|
| `file_path` | `str` | required | File path, including extension. When a working directory is configured, relative paths resolve inside it and paths outside it are refused. |
| `start` | `int \| None` | default `None` | Line number to start reading from (0-based). Giving start or count reads raw lines of a text file (csv included); xlsx, xls and parquet files are read whole. |
| `count` | `int \| None` | default `None` | Maximum number of lines to read. |

##### `file_writer`

Write data to a file, replacing its contents: an object for json, yml, yaml; a list of row objects for csv, xlsx, parquet; a string for md, txt, svg. .xls files can be read, not written.

| Parameter | Type | | Description |
|---|---|---|---|
| `file_path` | `str` | required | File path, including extension. When a working directory is configured, relative paths resolve inside it and paths outside it are refused. |
| `data` | `dict[str, Any] \| list[dict[str, Any]] \| str` | required | What to write: an object for json/yml/yaml, a list of row objects for csv/xlsx/parquet, a string for md/txt/svg. Plain JSON values only. |

##### `python_executor`

Execute Python code for data analysis or computation.

| Parameter | Type | | Description |
|---|---|---|---|
| `code` | `str` | required | Python source code to run in a sandbox. Assign your final value to a variable named 'result'; otherwise set result='no return'. |

A call with invalid arguments gets an error naming the bad fields. Every tool added later follows the same rules: published with its schema, callable directly and from the sandbox.

**The working directory.** When `WORKING_DIRECTORY` is set, every file a tool reads or writes lives there, and relative paths name the same file in a tool call and inside `python_executor` code. Access outside it is refused.

**The Python sandbox** runs each piece of code in its own process:

- allowed modules: pandas, numpy, matplotlib, datetime and the rest of pycraftcore's allowlist (listed in the tool's description);
- 256 MB of memory, at most 8 runs at a time, and a hard timeout;
- with `SANDBOX_TOOL_ACCESS=true`, the other tools are available inside the code as functions that return exactly what the tool returns. The tool's description lists each one in two lines, its Python signature and the first sentence of its description, so it stays small with many tools:

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

#### Their parameters

The deployed versions are pinned in homelab-infra (`environments/versions.yaml`). Names below are as the toolbox publishes them; a parameter with a default is optional.

**MongoDB** (`@mongodb-js/mcp-tools-mongodb` 3.2.2, read-only). Every tool takes `connectionId` (`"preconfigured"`: the server's own connection) and, except `mongodb_list_databases`, `database`; the tools on one collection also take `collection`.

| Tool | Its other parameters |
|---|---|
| `mongodb_find` | `filter` (object: the query, as for `db.collection.find()`), `projection` (object), `limit` (number, default 10), `sort` (object: field to `1`, `-1`, `"asc"` or `"desc"`), `responseBytesLimit` (number, default 1048576) |
| `mongodb_aggregate` | `pipeline` (array of stages, required), `responseBytesLimit` (number, default 1048576) |
| `mongodb_count` | `query` (object: the filter of the documents to count) |
| `mongodb_export` | `exportTitle` (string, required), `exportTarget` (one `find` or `aggregate` call with its arguments, required), `jsonExportFormat` (`"relaxed"` by default, or `"canonical"`) |
| `mongodb_collection_schema` | `sampleSize` (number, default 50), `responseBytesLimit` (number, default 1048576) |
| `mongodb_collection_indexes` | none |
| `mongodb_list_collections` | none (`database` only) |
| `mongodb_list_databases` | none (`connectionId` only) |
| `mongodb_db_stats` | none (`database` only) |

**PostgreSQL** (`crystaldba/postgres-mcp` 0.3.0, `--access-mode=restricted`: SQL runs read-only, with a 30 s timeout). Every tool is published.

| Tool | Parameters |
|---|---|
| `postgres_list_schemas` | none |
| `postgres_list_objects` | `schema_name` (required), `object_type` (`"table"` by default, or `"view"`, `"sequence"`, `"extension"`) |
| `postgres_get_object_details` | `schema_name` (required), `object_name` (required), `object_type` (as above) |
| `postgres_execute_sql` | `sql` (string): runs a read-only query on the `homelab` database |
| `postgres_explain_query` | `sql` (required), `analyze` (boolean, default false: when true the query runs), `hypothetical_indexes` (list of `{table, columns, using}`, default empty; not with `analyze`) |
| `postgres_get_top_queries` | `sort_by` (`"resources"` by default, or `"total_time"`, `"mean_time"`), `limit` (number, default 10) |
| `postgres_analyze_workload_indexes` | `max_index_size_mb` (number, default 10000), `method` (`"dta"` by default, or `"llm"`) |
| `postgres_analyze_query_indexes` | `queries` (list of SQL strings, required, up to 10), `max_index_size_mb`, `method` (as above) |
| `postgres_analyze_db_health` | `health_type` (`"all"` by default, or a comma-separated list of `index`, `connection`, `vacuum`, `sequence`, `replication`, `buffer`, `constraint`) |

**Grafana** (`grafana/mcp-grafana` 2.2.0, `--disable-write`, categories `search`, `datasource`, `dashboard`, `prometheus`, `loki`, `alerting` and `navigation`) offers several dozen tools, which change with its version and categories. The toolbox republishes them unchanged; list them with their parameters from the running toolbox:

```bash
curl -s http://localhost:8001/mcp/observation -H 'content-type: application/json' -H 'accept: application/json, text/event-stream' -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

**Add another server:** a connector named `external_mcp_<name>` in `config/<APP_ENV>/connector/mcp.yml` (its URL from an environment variable, `''` by default), an operation of the same name with its `prefix` in `config/<APP_ENV>/operation/mcp.yml`, both listed in `config/root.yml`, and the variable in `.env.example` and `devops/helm/values.yml`.

### Scopes

The toolbox serves its tools by scope, one MCP endpoint each, so every agent connects to its own scope and discovers only the tools meant for it:

| Scope | Endpoint | Tools |
|---|---|---|
| `all` | `/mcp` | every tool |
| `observation` | `/mcp/observation` | `grafana_*` |
| `analysis` | `/mcp/analysis` | `postgres_*`, `mongodb_*`, `users_tables`, `file_reader`, `file_writer`, `python_executor` |
| `coding` | `/mcp/coding` | `file_reader`, `file_writer`, `python_executor` |
| `security` | `/mcp/security` | `grafana_*`, `users_tables` |
| `kitchen` | `/mcp/kitchen` | `python_executor`, and kitchen-atelier's data only: `recipes_find`, `recipes_count`, `recipe_versions_find`, `recipe_versions_aggregate`, `recipe_versions_schema` (MongoDB `kitchen`), `ingredients_table` (PostgreSQL `kitchen.ingredients`) |
| `travel` | `/mcp/travel` | `python_executor` |

- **`python_executor` only where a scope lists it** (`all` has it: `*` matches it). Each such scope has its own: its description lists, and its code can call, only that scope's tools.
- **Tools from other MCP servers** join or leave each scope whose patterns match them while the toolbox runs.
- **An endpoint shows only its scope's tools** and calls only those, so an agent can't reach a tool outside its scope through this endpoint.
- **A scope can publish a tool under its own name, with arguments fixed:** an entry with `name`, `tool` (the tool it is built on), an optional `description` and `arguments`. The fixed arguments leave the tool's schema, are sent on every call and can't be set by the caller, so `recipes_find` searches only `kitchen.recipes`:

  ```yaml
  tools:
    - python_executor                  # a pattern: tools shown as they are
    - name: recipes_find               # a wrapped tool, only in this scope
      tool: mongodb_find
      description: Find recipes in the recipe index.
      arguments: { connectionId: preconfigured, database: kitchen, collection: recipes }
  ```

  - Its name must be a Python identifier that isn't a builtin, `ToolError`, `WORKING_DIRECTORY` or `result`, so `python_executor` code can call it.
  - A wrapped tool named like the tool it is built on locks that tool in the scope (`{name: mongodb_find, tool: mongodb_find, arguments: {database: kitchen}}`); it never falls back to the unlocked tool.
  - A pattern of the scope may not match a wrapped tool's name: a scope publishes one tool per name.
  - At start-up, a wrapped tool whose arguments don't fit its tool, or whose tool doesn't exist while its server answers, stops the toolbox with the reason. One whose server is down or has no URL is a warning, and it is published as soon as the server answers.
  - Fixed arguments narrow what a tool reaches; they don't make raw SQL safe. A tool that takes a whole query (`postgres_execute_sql`) reaches whatever its server's role can read, so give a scope a server whose role reads only its data.
- **To add or change a scope,** edit `config/debug/operation/scope.yml`: one `mcp` operation on the `self` connector, with the scope's name as `name` and its patterns and wrapped tools as `tools`. Then list it under `operation:` in `config/root.yml`. `all` is built in. Wrapped tools belong in scopes: an operation of another MCP server lists only remote names, to keep some of its tools.

#### The kitchen scope's tools

Each keeps only the parameters below; the scope fixes the rest.

##### `recipes_find`

Find recipes in the recipe index: one document per recipe with _id, title, course, current_version_number, created_at and updated_at. Its content is in recipe_versions.

| Parameter | Type | | Description |
|---|---|---|---|
| `filter` | `dict[str, Any] \| None` | default `None` | Query filter, as for db.collection.find(). |
| `projection` | `dict[str, Any] \| None` | default `None` | Fields to return or leave out. |
| `limit` | `float \| None` | default `10` | Most documents to return. |
| `sort` | `dict[str, Any] \| None` | default `None` | Sort order: field to 1, -1, 'asc' or 'desc'. |
| `responseBytesLimit` | `float \| None` | default `1048576` | Most bytes of documents to return. |

Built on `mongodb_find`, with `connectionId=preconfigured`, `database=kitchen`, `collection=recipes` fixed.

##### `recipes_count`

Count the recipes in the recipe index that match a query.

| Parameter | Type | | Description |
|---|---|---|---|
| `query` | `dict[str, Any] \| None` | default `None` | Filter of the documents to count. |

Built on `mongodb_count`, with `connectionId=preconfigured`, `database=kitchen`, `collection=recipes` fixed.

##### `recipe_versions_find`

Find saved recipe versions: recipe_id, version_number, title, portions, prep and cook times, ingredients (lines with quantity, unit and CIQUAL code), steps, sensory notes. A recipe's current content is the version whose version_number is the recipe's current_version_number.

| Parameter | Type | | Description |
|---|---|---|---|
| `filter` | `dict[str, Any] \| None` | default `None` | Query filter, as for db.collection.find(). |
| `projection` | `dict[str, Any] \| None` | default `None` | Fields to return or leave out. |
| `limit` | `float \| None` | default `10` | Most documents to return. |
| `sort` | `dict[str, Any] \| None` | default `None` | Sort order: field to 1, -1, 'asc' or 'desc'. |
| `responseBytesLimit` | `float \| None` | default `1048576` | Most bytes of documents to return. |

Built on `mongodb_find`, with `connectionId=preconfigured`, `database=kitchen`, `collection=recipe_versions` fixed.

##### `recipe_versions_aggregate`

Run an aggregation pipeline on the saved recipe versions; $lookup can join the recipes collection of the same kitchen database.

| Parameter | Type | | Description |
|---|---|---|---|
| `pipeline` | `list[Any]` | required | Aggregation pipeline stages. |
| `responseBytesLimit` | `float \| None` | default `1048576` | Most bytes of documents to return. |

Built on `mongodb_aggregate`, with `connectionId=preconfigured`, `database=kitchen`, `collection=recipe_versions` fixed.

##### `recipe_versions_schema`

Show the fields of saved recipe versions, inferred from a sample.

| Parameter | Type | | Description |
|---|---|---|---|
| `sampleSize` | `float \| None` | default `50` | Documents sampled to infer the schema. |
| `responseBytesLimit` | `float \| None` | default `1048576` | Most bytes of documents to return. |

Built on `mongodb_collection_schema`, with `connectionId=preconfigured`, `database=kitchen`, `collection=recipe_versions` fixed.

##### `ingredients_table`

Show the columns of the ingredients table (CIQUAL nutrition per 100 g: kcal, protein, carbohydrate, fat and a nutrition object), with its constraints and indexes.

No parameters.

Built on `postgres_get_object_details`, with `schema_name=kitchen`, `object_name=ingredients`, `object_type=table` fixed.

### Connect a client

Point the client's MCP connector at `http://<host>:<port>/mcp` with the `streamable_http` transport. The homelab agent's connector:

```yaml
toolbox:
  name: toolbox
  type: mcp
  base_url: ${oc.env:TOOLBOX_URL}
  timeout: 30
  transport: streamable_http
  auth:
    type: token
    key_name: Authorization
    key_value: Bearer ${oc.env:TOOLBOX_TOKEN}
```

**Tokens.** `/mcp` and every `/mcp/<scope>` ask for `Authorization: Bearer <token>`; a call without a valid token gets `401` and `WWW-Authenticate: Bearer`. `/actuator/*` and `POST /auth/token` stay open, so probes and clients can reach them.

```bash
curl -s -X POST http://localhost:8001/auth/token -H 'content-type: application/json' -d '{"username": "alice"}'
# {"access_token": "eyJ…", "token_type": "bearer", "expires_in": 18000}
```

- A token lasts 5 hours. `expire` (`"30m"`, `"12h"`, `"7d"` or `"never"`) is applied only when `username` is `JWT_USERNAME`; anyone else gets 5 hours whatever they ask. `"never"` gives a token without `exp`, for a deployed agent's `TOOLBOX_TOKEN`.
- Tokens are signed with `JWT_KEY` (HS256, 32 bytes or more); changing it invalidates every token issued before, the never-expiring ones included. The toolbox doesn't start without it.
- The endpoint asks for no password: whoever reaches it can get a token, and claiming `JWT_USERNAME` gets one that never expires. Keep it reachable only from where tokens should come from (the gateway, the cluster's NetworkPolicy).

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
| `DEPLOYMENT_ENVIRONMENT` | Label shown by `/actuator/info` (`unknown` when unset); telemetry's `deployment.environment` comes from `APP_ENV` |
| `TOOLBOX_URL` | The URL clients use, e.g. `http://<host>:<port>/mcp`. Sets the MCP path and the allowed host; the listening address comes from Granian (`--host`/`--port`, or `GRANIAN_HOST`/`GRANIAN_PORT` in Docker) |
| `TOOLBOX_EXTRA_ALLOWED_HOSTS` | Other `host:port` values clients may use, comma-separated |
| `WORKING_DIRECTORY` | The folder file tools and the sandbox are confined to; unset = no working directory |
| `SANDBOX_TOOL_ACCESS` | `true` to make the tools callable from `python_executor` code |
| `JWT_KEY` | Required. Signs and checks the tokens `/mcp` asks for: 32 bytes or more, e.g. `openssl rand -hex 32` |
| `JWT_USERNAME` | The one user who may choose its token's lifetime, `never` included, at `POST /auth/token` |
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

Hexagonal, like the agent: the domain, the use cases and the tools know nothing about MCP or the web framework. They speak to MCP through pycraftcore's framework-free ports (`pycraftcore.mcp`: `ToolServer` to publish tools, `McpClient` to call other servers), the way agent-runtime's core speaks to `pycraftcore.web`. The MCP SDK and Starlette are only met at the edge, in `src/bootstrap/application/mcp_sdk/`, through pycraftcore's `mcp_sdk` and `web_starlette` toolkits; swapping the MCP library means writing another `bootstrap/application/<toolkit>/` next to it, nothing else.

```text
  bootstrap/application/mcp_sdk/        bootstrap/container/              agent_toolbox/
  ───────────────────────────────       ────────────────────              ──────────────
  create_mcp_sdk_app                    ToolboxContainer                  ToolBinder ──► InvokeToolUseCase ──► Tool.run
    one MCPServer per scope ──────────►   serve({scope: ToolServer})        ServedTool     validates, logs,      │
    SdkToolServer (pycraftcore)           boot: bind scopes, start          per Tool       maps failures         ├─► a data tool ──► its backend
    actuator_router, /auth/token          the reconciler                                                         │
    BearerTokenMiddleware                 actuator (pycraftcore.web)      SandboxToolBridge ──► InvokeToolUseCase └─► ExecutePython ──► PythonSandbox
                                                                          McpToolProvider ──► McpClient (SdkMcpClient, wired in bootstrap/di)
```

`tests/architecture/test_boundaries.py` enforces it: no agent, LangChain or LangGraph imports; no framework in the domain; `agent_toolbox/` never imports `mcp`, `starlette` or pycraftcore's `mcp_sdk` and `web_starlette` toolkits; in `bootstrap/`, only `bootstrap/application/mcp_sdk/` imports them, and `bootstrap/di/` may build pycraftcore's `SdkMcpClient`.

Direct calls and calls from sandboxed code go through the same `InvokeToolUseCase`, so they return the same thing — `tests/contract/test_tool_parity.py` checks it.

### Project layout

| Path | What it holds |
|---|---|
| `src/agent_toolbox/domain/` | `ToolScope` and `ToolAlias`, `TokenLifetime`, `WorkingDirectory`, `SandboxRun`, `DependencyHealth`, `ToolFailure`, `UnknownToolException` |
| `src/agent_toolbox/application/` | `InvokeToolUseCase`, `ReconcileExternalTools`, `IssueTokenUseCase`; `ToolCatalog` (the live list of tools), `ScopedToolCatalog` and `AliasedTool` (a scope's view, with its aliases); and their ports: `Tool` (the base every tool extends), `ToolLookup`, `ToolProvider`, `ToolPublisher`, `CodeSandboxPort` |
| `src/agent_toolbox/adapter/inbound/mcp/` | `ToolBinder` (each tool → a pycraftcore `ServedTool` on a `ToolServer`), `McpToolPublisher` (adds and removes tools while it runs) |
| `src/agent_toolbox/adapter/inbound/sandbox/` | `SandboxToolBridge`: lets sandboxed code call the tools |
| `src/agent_toolbox/adapter/outbound/` | The tools, one folder per area (`sql/`, `file/`, `code/`), `mcp/` (other MCP servers' tools through a pycraftcore `McpClient`, prefixed), and `sandbox/` (`PythonSandbox`) |
| `src/bootstrap/configuration/` | `ProcessSettings` (the environment) and the configuration loader |
| `src/bootstrap/di/` | The wiring: `ToolboxDI` composes `InternalToolsDI`, `SandboxDI`, `ExternalMcpDI`, `ScopesDI` and `AuthDI` |
| `src/bootstrap/container/` | `ToolboxContainer`: framework-free; serves each scope on the `ToolServer` it is given, boots and stops the reconciler, builds the actuator |
| `src/bootstrap/application/` | `toolbox_application.py` (the Granian factory), `application_metadata.py`, and `mcp_sdk/`: the only code that knows the MCP SDK and Starlette (servers per scope, routes, middleware) |
| `tests/` | Unit, architecture and contract tests; `tests/bootstrap/` runs the app end to end |

### Adding a tool

1. Define its input and output as pydantic models (`adapter/outbound/<area>/model/`). Field descriptions become the MCP schema the agent reads.
2. Subclass `Tool[Input, Output]` with a `name`, a `description` written for the model, and `async run(arguments)`. Raise `ToolFailure` with a clear message when the call can't be served.
3. If it needs a backend (a database, an API, …), add a connector in `config/<APP_ENV>/connector/`, list it in `config/root.yml`, put its variables in `.env.example`, and build the client in `InternalToolsDI` from that connector.
4. Return it from `InternalToolsDI.tools`, and add its name to the patterns of the scopes that should offer it (`config/debug/operation/scope.yml`). It is then published over MCP at `/mcp` and those scopes' endpoints and, when `SANDBOX_TOOL_ACCESS` is on, callable from `python_executor` code — no change needed in the agent, which discovers it at its next start, nor in `bootstrap/application/`: a tool never touches the MCP library.
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
