# Last Email MCP Server

A Python Model Context Protocol (MCP) server that returns the most recently received Microsoft 365 email for the signed-in user. The server uses FastMCP, Microsoft Entra ID authentication, the OAuth 2.0 On-Behalf-Of flow, and Microsoft Graph.

## Features

- Streamable HTTP MCP transport
- Microsoft Entra ID authentication through FastMCP
- On-Behalf-Of token exchange for delegated Microsoft Graph access
- `get_last_email` tool for retrieving the latest message
- Health check endpoint
- Docker support

## Requirements

- Python 3.13 or later
- [uv](https://docs.astral.sh/uv/) for local dependency management
- A Microsoft Entra ID tenant and app registration
- Docker, if running the container image

## Microsoft Entra ID configuration

Create an app registration for the MCP server and configure it as follows:

1. Under **Expose an API**, add a delegated scope named `user_impersonation`.
2. Under **API permissions**, add the Microsoft Graph delegated permission `Mail.Read`.
3. Grant consent for the required permissions according to your tenant's policies.
4. Create a client secret.
5. Configure the OAuth redirect URI for the server. FastMCP uses `/auth/callback` by default, so the redirect URI must match the externally reachable server URL and that path.
6. Configure the app registration to issue version 2 access tokens.

Use delegated permissions rather than Microsoft Graph application permissions. The server accesses Microsoft Graph on behalf of the authenticated user.

## Configuration

The following environment variables are required:

| Variable | Description |
| --- | --- |
| `ENTRA_CLIENT_ID` | Application (client) ID of the Entra app registration |
| `ENTRA_CLIENT_SECRET` | Client secret for the Entra app registration |
| `ENTRA_TENANT_ID` | Directory (tenant) ID containing the app registration |

For local development, create `src/.env`:

```dotenv
ENTRA_CLIENT_ID=your-client-id
ENTRA_CLIENT_SECRET=your-client-secret
ENTRA_TENANT_ID=your-tenant-id
```

Environment files are excluded from Git and the Docker build context. Do not commit client secrets.

## Local development

Install the locked dependencies:

```shell
cd src
uv sync --frozen
```

Run the server on an unprivileged local port:

```shell
uv run fastmcp run server.py --transport http --port 8000
```

The MCP endpoint is available at `http://localhost:8000/mcp`, and the health endpoint is available at `http://localhost:8000/health`.

Running `uv run python server.py` uses the entry point defined in the application and binds to `0.0.0.0:80`.

## Docker

Build the image from the repository root:

```shell
docker buildx build --platform=linux/amd64 -t last-email-mcp-server .
```

Run the container and map local port 8000 to container port 80:

```shell
docker run --rm \
  --env-file src/.env \
  -p 8000:80 \
  last-email-mcp-server
```

The MCP endpoint is then available at `http://localhost:8000/mcp`.

## MCP tool

### `get_last_email`

Returns the most recently received message for the authenticated user. The Microsoft Graph request selects the message subject, sender, received date and time, and body preview.

The result is a list containing zero or one message:

```json
[
  {
    "subject": "Example subject",
    "from": "sender@example.com",
    "receivedDateTime": "2026-09-21T12:00:00Z",
    "bodyPreview": "Example message preview"
  }
]
```

An empty list indicates that no messages were returned.

## HTTP endpoints

| Endpoint | Description |
| --- | --- |
| `/mcp` | Streamable HTTP MCP endpoint |
| `/health` | Returns `OK` when the server is running |

## Project structure

```text
.
├── Dockerfile
├── LICENSE
├── README.md
└── src
    ├── pyproject.toml
    ├── server.py
    └── uv.lock
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
