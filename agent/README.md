# MCP Codemode Agent

The MCP Codemode Agent is a lightweight gRPC server designed to manage containers and execute tasks. This guide will help you install and configure the agent on your virtual machine.

## Installation

1. **Install the Agent**

   Use the following command to install the agent:

   ```bash
   go install github.com/mosteligible/mcp-codemode/agent@latest
   ```

   By default, the binary will be installed in the `bin` folder of your Go workspace (e.g., `$HOME/go/bin`). Ensure this folder is added to your `PATH` environment variable:

   ```bash
   export PATH=$PATH:$HOME/go/bin
   ```

   Alternatively, you can specify a custom installation path by setting the `GOBIN` environment variable before running the `go install` command:

   ```bash
   export GOBIN=/desired/path/to/install
   go install github.com/mosteligible/mcp-codemode/agent@latest
   ```

   The binary will then be installed in the specified path.

2. **Set Environment Variables**

   The agent requires certain environment variables to be set for proper configuration. Below are the required variables:

   - `DOCKER_API_VERSION`: The Docker API version to use (default: `1.41`).
   - `DOCKER_IMAGE_NAME`: The default Docker image name.
   - `WORKER_PORT`: The port for worker communication (default: `8080`).
   - `MIN_ACTIVE`: Minimum number of active containers (default: `1`).
   - `ACTIVE_CONTAINER_CHECK_INTERVAL`: Interval (in seconds) to check active containers (default: `60`).

   Example:

   ```bash
   export DOCKER_API_VERSION=1.41
   export DOCKER_IMAGE_NAME=my-docker-image
   export WORKER_PORT=8080
   export MIN_ACTIVE=1
   export ACTIVE_CONTAINER_CHECK_INTERVAL=60
   ```

3. **Run the Agent**

   Navigate to the folder where the binary is installed (e.g., `$HOME/go/bin` or the custom path set in `GOBIN`) and run the agent:

   ```bash
   cd $HOME/go/bin
   ./agent
   ```

   The agent will start a gRPC server on port `30031` by default.

## Next Steps

### Multi-Language Support

To enable multi-language support, the agent will need to be extended to handle additional runtime environments. This will involve:

- Adding support for custom containers.
- Allowing users to specify runtime environments dynamically.

### Private Container Registries

To pull images from private container registries, you will need to provide an API key. This can be achieved by:

1. Adding a new environment variable `CONTAINER_REGISTRY_API_KEY`.
2. Updating the agent to use this key when authenticating with the registry.

Example:

```bash
export CONTAINER_REGISTRY_API_KEY=my-api-key
```

Stay tuned for updates as these features are implemented.