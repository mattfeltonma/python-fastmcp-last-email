# Basic
import sys
import os
import logging
import httpx2
from dotenv import load_dotenv

# FastMCP shit
from fastmcp import FastMCP
from fastmcp.server.auth.providers.azure import AzureJWTVerifier
# This library is because calls to this MCP Server will be made from an upstream application which already authenticated the user
from azure.identity.aio import OnBehalfOfCredential
from fastmcp.server.dependencies import get_access_token
from starlette.requests import Request
from starlette.responses import PlainTextResponse

# Configure logging to stdout so it shows up in the Uvicorn terminal
def configure_logging(level="ERROR"):
    try:
        logging.basicConfig(
            level=getattr(logging, level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
    except Exception as e:
        print(f"Failed to set up logging: {e}", file=sys.stderr)
        sys.exit(1)

# Load environment variables
load_dotenv(override=True)

CLIENT_ID = os.environ["ENTRA_CLIENT_ID"]
CLIENT_SECRET = os.environ["ENTRA_CLIENT_SECRET"]
TENANT_ID = os.environ["ENTRA_TENANT_ID"]

# Verify the incoming Entra ID JWT
auth_provider = AzureJWTVerifier(
    client_id=CLIENT_ID,
    tenant_id=TENANT_ID,
    required_scopes=["user_impersonation"],
)

# Setup MCP server
mcp = FastMCP(
    name="EntraOBOLastEmailMcpServer",
    auth_provider=auth_provider,
    instructions="This server provides one tool: get_last_email. It returns the last email for the signed-in user."
)

# Route for basic health checks
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")

@mcp.tool()
async def get_last_email() -> list[dict]:
    """Get the last email from Microsoft 365 for the signed-in user."""
    incoming_token = get_access_token()
    if incoming_token is None:
        raise RuntimeError("No authenticated access token is available")

    async with OnBehalfOfCredential(
        tenant_id=TENANT_ID,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        user_assertion=incoming_token.token,
    ) as credential:
        graph_access_token = await credential.get_token(
            "https://graph.microsoft.com/Mail.Read"
        )

    async with httpx2.AsyncClient() as client:
        response = await client.get(
            "https://graph.microsoft.com/v1.0/me/messages",
            headers={
                "Authorization": f"Bearer {graph_access_token.token}",
            },
            params={
                "$top": 1,
                "$orderby": "receivedDateTime desc",
                "$select": "subject,from,receivedDateTime,bodyPreview",
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

    return [
        {
            "subject": message.get("subject", ""),
            "from": (
                message.get("from", {})
                .get("emailAddress", {})
                .get("address", "")
            ),
            "receivedDateTime": message.get("receivedDateTime", ""),
            "bodyPreview": message.get("bodyPreview", ""),
        }
        for message in data.get("value", [])
    ]

if __name__ == "__main__":
    configure_logging(level="INFO")
    mcp.run(transport="http", host="0.0.0.0", port=80)