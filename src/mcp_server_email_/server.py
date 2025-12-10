# src/mcp_server_email/server.py

from __future__ import annotations

from typing import Dict, List, TypedDict

from mcp.server.fastmcp import FastMCP

from .gmail_client import get_unread_emails, create_reply_draft


class EmailSummary(TypedDict):
    id: str
    thread_id: str
    sender: str
    subject: str
    snippet: str


mcp = FastMCP(
    name="gmail-mcp",
    json_response=True,  # return plain JSON the client can easily consume
)


@mcp.tool()
def get_unread(limit: int = 5) -> List[EmailSummary]:
    """
    List unread emails from Gmail.

    Args:
        limit: Maximum number of unread emails to return.

    Returns:
        A list of objects with:
        - id: Gmail message id
        - thread_id: Gmail thread id
        - sender: From header
        - subject: Subject header
        - snippet: small preview of the body
    """
    # Delegate to our Gmail helper
    return get_unread_emails(limit=limit)


@mcp.tool()
def create_draft_reply(message_id: str, reply_body: str) -> Dict[str, str]:
    """
    Create a draft reply in Gmail for the given message.

    Args:
        message_id: The Gmail message id of the email you're replying to.
        reply_body: The plain text content of the reply.

    Returns:
        dict with:
        - status: "ok" or "error"
        - draft_id: id of the Gmail draft (if ok)
        - thread_id: thread id (if ok)
        - error: error message (if status == "error")
    """
    return create_reply_draft(message_id=message_id, reply_body=reply_body)


def main() -> None:
    """
    Entry point for running the MCP server.

    This is what `poetry run mcp-server-email` will execute.
    """
    mcp.run()  # defaults to stdio transport, which Claude Desktop understands


if __name__ == "__main__":
    main()
