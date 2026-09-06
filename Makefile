venv:
	uv venv

install:
	uv sync

install_dev:
	uv sync --group dev

update_dependency:
ifdef PACKAGE
	uv lock --upgrade-package $(PACKAGE)
else
	uv lock --upgrade
endif
	uv sync

test:
	uv run pytest -n auto --disable-warnings

lint:
	uv run ruff check .

fix:
	uv run ruff check --fix .

format:
	uv run ruff format .

typecheck:
	uv run ty check

check:
	$(MAKE) lint
	$(MAKE) typecheck
	$(MAKE) test

# --- run -------------------------------------------------------------------
run:
	uv run uvicorn bootstrap.application.toolbox_application:app --host 0.0.0.0 --port 8001

clean:
	rm -rf dist src/*.egg-info

build:
	rm -rf dist src/*.egg-info
	uv build

docker_build:
	docker build -f devops/docker/Dockerfile -t agent-toolbox:local .
