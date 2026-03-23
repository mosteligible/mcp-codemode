.PHONY: runner-image run-pyrunner run-client run-web build-web start-web

runner-image:
	docker build -t mcp-codemode-runner -f Dockerfile.runner .

run-pyrunner:
	cd pyrunner && uv run uvicorn main:app

run-client:
	cd client && uv run main.py

run-web:
	cd web && npm run dev

build-web:
	cd web && npm run build

start-web:
	cd web && npm run start
