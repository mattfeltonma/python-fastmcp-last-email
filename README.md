# Last Email MCP Server

A Python Model Context Protocol (MCP) server that returns the most recently received Microsoft 365 email for the signed-in user. It is designed to be called by an upstream web application that has already authenticated the user.

The web application obtains a delegated access token for this MCP server through an OAuth 2.0 On-Behalf-Of (OBO) exchange. The MCP server validates that token and performs a second OBO exchange to obtain a delegated Microsoft Graph token.

## Features

- Streamable HTTP MCP transport
- Validation of Microsoft Entra ID bearer tokens issued for the MCP server
- Chained On-Behalf-Of authentication from the web application to the MCP server and Microsoft Graph
- `get_last_email` tool for retrieving the latest message
- Health check endpoint
- Docker support

## Requirements

- Python 3.13 or later
- [uv](https://docs.astral.sh/uv/) for local dependency management
- A Microsoft Entra ID tenant
- App registrations for the upstream web application and MCP server
- Docker, if running the container image

## Authentication flow

1. The user authenticates with the upstream web application.
2. The web application performs an OBO exchange for the MCP server's `user_impersonation` scope.
3. The web application calls `/mcp` with the resulting access token in the `Authorization: Bearer <token>` header.
4. The MCP server validates the token's signature, issuer, audience, expiration, and delegated scope.
5. The MCP server uses the incoming token as the user assertion in another OBO exchange for Microsoft Graph `Mail.Read` access.
6. The MCP server calls Microsoft Graph on behalf of the user.

The MCP server does not perform interactive user authentication and does not require a redirect URI. Any redirect URI used for the initial user sign-in belongs to the upstream web application.

## Microsoft Entra ID configuration

### MCP server app registration

Create an app registration for the MCP server and configure it as follows:

1. Under **Expose an API**, set an Application ID URI, typically `api://<mcp-client-id>`.
2. Add a delegated scope named `user_impersonation`.
3. Under **API permissions**, add the Microsoft Graph delegated permission `Mail.Read`.
4. Grant consent for the required permissions according to your tenant's policies.
5. Create a client secret for the MCP server's OBO exchange with Microsoft Graph.
6. Configure the app registration to issue version 2 access tokens.

Do not add Microsoft Graph application permissions. The server accesses Graph with the signed-in user's delegated permissions.

### Web application app registration

Configure the upstream web application's app registration as follows:

1. Add delegated access to `api://<mcp-client-id>/user_impersonation`.
2. Grant consent according to your tenant's policies.
3. Configure the web application's own user authentication and redirect URI as required by that application.
4. Use the web application's incoming user token in an OBO exchange for the MCP server scope.

The resulting access token must target the MCP server and contain the `user_impersonation` delegated scope. Send an access token, not an ID token, to the MCP endpoint.

## Configuration

The following environment variables are required:

| Variable | Description |
| --- | --- |
| `ENTRA_CLIENT_ID` | Application (client) ID of the MCP server app registration |
| `ENTRA_CLIENT_SECRET` | MCP server client secret used for the Graph OBO exchange |
| `ENTRA_TENANT_ID` | Directory (tenant) ID containing the app registrations |

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
