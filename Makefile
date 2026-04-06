.PHONY: runner-image run-pyrunner run-client run-web build-web build-coderunner run-coderunner start-web

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

build-coderunner:
	mkdir -p build
	cd coderunner && go build -o ../build/coderunner .
	@echo "coderunner binary created at ./build/coderunner"

run-coderunner: build-coderunner
	./build/coderunner

start-web:
	cd web && npm run start
