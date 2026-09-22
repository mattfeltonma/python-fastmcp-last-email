# Basic
import sys
import os
import logging
import httpx2
from dotenv import load_dotenv

from fastmcp import FastMCP
from fastmcp.server.auth.providers.azure import AzureProvider, EntraOBOToken
from starlette.requests import Request
from starlette.responses import PlainTextResponse

## Load environment variables
load_dotenv(override=True)

auth_provider = AzureProvider(
    client_id=os.getenv("ENTRA_CLIENT_ID"),
    client_secret=os.getenv("ENTRA_CLIENT_SECRET"),
    tenant_id=os.getenv("ENTRA_TENANT_ID"),
    required_scopes=["user_impersonation"],
    additional_authorize_scopes=[
        "https://graph.microsoft.com/Mail.Read"
    ]
)

## Configure logging to stdout so it shows up in the Uvicorn terminal
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


## Setup MCP server
mcp = FastMCP(
    name="EntraOBOLastEmailMcpServer",
    auth_provider=auth_provider,
    instructions="This server provides one tool: get_last_email. It returns the last email for the signed-in user."
)

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")

@mcp.tool()
async def get_last_email(
    graph_token: str = EntraOBOToken(["https://graph.microsoft.com/Mail.Read"]),
) -> list[dict]:
    """Get the last email from Microsoft 365 for the signed-in user"""
    async with httpx2.AsyncClient() as client:
        response = await client.get(
            f"https://graph.microsoft.com/v1.0/me/messages",
            headers={
                "Authorization": f"Bearer {graph_token}"
            },
            params={
                "$top": 1,
                "$orderby": "receivedDateTime desc",
                "$select": "subject,from,receivedDateTime,bodyPreview"
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

    return [
        {"subject": msg["subject"], "from": msg["from"]["emailAddress"]["address"], "receivedDateTime": msg["receivedDateTime"], "bodyPreview": msg["bodyPreview"]}
        for msg in data.get("value", [])
    ]

if __name__ == "__main__":
    configure_logging(level="INFO")
    mcp.run(transport="http", host="0.0.0.0", port=80)