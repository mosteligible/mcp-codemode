.PHONY: runner-image run-pyrunner run-client

runner-image:
	docker build -t mcp-codemode-runner -f Dockerfile.runner .

run-pyrunner:
	cd pyrunner && uv run uvicorn main:app

run-client:
	cd client && uv run main.py
