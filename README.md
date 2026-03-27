# PubMed MCP

A MCP server that allows to search and fetch articles from PubMed.

PubMed is a database of over 35 million citations for biomedical literature from MEDLINE, life science journals, and online books.

This MCP server relies on the [pubmedclient](https://github.com/grll/pubmedclient) Python package to perform the search and fetch operations.

## Usage

Add the following to your `claude_desktop_config.json` file:

```json
{
    "mcpServers": {
        "pubmedmcp": {
            "command": "uvx",
            "args": ["pubmedmcp@latest"],
            "env": {
                "UV_PRERELEASE": "allow",
                "UV_PYTHON": "3.12"
            }
        }
    }
}
```

Make sure uv is installed on your system and 'uvx' is available in your PATH (claude PATH sometimes is not the same as your system PATH).
You can add a PATH key in your `claude_desktop_config.json` file to make sure uv is available in claude PATH.

## Docker & Kubernetes Deployment

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TRANSPORT` | `stdio` | Transport protocol: `stdio` or `streamable-http` |
| `HOST` | `0.0.0.0` | Bind address (only for `streamable-http`) |
| `PORT` | `8000` | Listen port (only for `streamable-http`) |

### Build the Docker Image

```bash
docker build -t pubmedmcp:latest .
```

### Run Locally with Docker

```bash
docker run -p 8000:8000 pubmedmcp:latest
```

The MCP server will be available at `http://localhost:8000/mcp` and a health check endpoint at `http://localhost:8000/health`.

### Deploy to Kubernetes

```bash
# Update the image reference in k8s/deployment.yaml to your registry, then:
kubectl apply -f k8s/
```

This creates:
- A **Deployment** with 2 replicas, liveness/readiness probes on `/health`, and resource limits
- A **ClusterIP Service** exposing port 80 → 8000

The server runs in **stateless mode** (`stateless_http=True`, `json_response=True`), so no sticky sessions are required and replicas can be freely scaled.