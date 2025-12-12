import os
import csv
import asyncio
import base64
import random
import logging
from email.message import EmailMessage

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

import mcp.types as types
from mcp.server import Server
import mcp.server.stdio

# --------------------------------------------------
# Logging
# --------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --------------------------------------------------
# Gmail config
# --------------------------------------------------
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
]

BASE_DIR = os.path.dirname(__file__)
CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")

FOI_LIBRARY_CSV = os.path.join(
    BASE_DIR,
    "camden_foi_responses.csv",
)

FOI_TEAM_CSV = os.path.join(
    BASE_DIR,
    "foi_team_contacts.csv",
)

MAX_FOI_ROWS_FOR_CLAUDE = 50

# --------------------------------------------------
# Gmail utilities
# --------------------------------------------------
def get_gmail_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)

# --------------------------------------------------
# Helpers
# --------------------------------------------------
def generate_cam_reference():
    return f"CAM{random.randint(1000, 9999)}"


def generate_external_ack(ref: str) -> str:
    return f"""Dear Sir or Madam,

Thank you for your request for information.

Your request has been logged under the reference number {ref}.
Please quote this reference in any future correspondence.

We will respond within 20 working days in accordance with the
Freedom of Information Act 2000.

Kind Regards,

Information Rights Team
London Borough of Camden
"""


def load_foi_library_for_claude():
    rows = []
    with open(FOI_LIBRARY_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= MAX_FOI_ROWS_FOR_CLAUDE:
                break
            rows.append(
                f"""ID: {row.get('Identifier')}
Title: {row.get('Document Title')}
Text: {row.get('Document Text')}
Link: {row.get('Document Link')}"""
            )
    return "\n\n---\n\n".join(rows)


def load_team_contacts():
    teams = {}
    with open(FOI_TEAM_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            teams[row["team"]] = row["officer_email"]
    return teams

# --------------------------------------------------
# Gmail draft creation
# --------------------------------------------------
def create_gmail_draft(service, to, subject, body, thread_id):
    msg = EmailMessage()
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    service.users().drafts().create(
        userId="me",
        body={
            "message": {
                "raw": raw,
                "threadId": thread_id,
            }
        },
    ).execute()

# --------------------------------------------------
# Claude task prompt
# --------------------------------------------------
def build_claude_prompt(subject, body, foi_library, teams, ref, thread_id):
    team_list = "\n".join([f"- {t}" for t in teams.keys()])

    return f"""
You are an FOI officer at Camden Council.

### New FOI request
Subject:
{subject}

Request body:
{body}

---

### Previous FOI responses
{foi_library}

---

### Available teams
{team_list}

---

### Tasks
1. Select the TOP 5 most relevant previous FOIs.
2. Decide the single best team to handle this request.
3. Draft an INTERNAL allocation email.
4. Call the tool `compose-internal-draft` to save the draft in Gmail.

Use:
- Thread ID: {thread_id}
- Reference: {ref}

---

### Output rules
You MUST call the tool.
Do NOT write the email in chat.
"""

# --------------------------------------------------
# MCP Server
# --------------------------------------------------
server = Server("gmail-foi")


@server.list_tools()
async def list_tools():
    return [
        types.Tool(
            name="process-unread-foi",
            description="Create external FOI acknowledgement draft and request Claude allocation",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="compose-internal-draft",
            description="Create internal FOI allocation Gmail draft",
            inputSchema={
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                    "thread_id": {"type": "string"},
                },
                "required": ["to", "subject", "body", "thread_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    service = get_gmail_service()

    # ----------------------------------------------
    # Tool 1: process unread FOIs
    # ----------------------------------------------
    if name == "process-unread-foi":
        teams = load_team_contacts()
        foi_library = load_foi_library_for_claude()

        results = service.users().messages().list(
            userId="me",
            labelIds=["UNREAD"],
            maxResults=3,
        ).execute()

        outputs = []

        for m in results.get("messages", []):
            msg = service.users().messages().get(
                userId="me", id=m["id"], format="full"
            ).execute()

            headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
            subject = headers.get("Subject", "")
            sender = headers.get("From", "")
            thread_id = msg["threadId"]

            body = ""
            for part in msg["payload"].get("parts", []):
                if part.get("mimeType") == "text/plain":
                    data = part["body"].get("data")
                    if data:
                        body = base64.urlsafe_b64decode(data).decode(errors="ignore")
                        break

            if "foi" not in subject.lower() and "foi" not in body.lower():
                continue

            ref = generate_cam_reference()

            # External acknowledgement draft (automatic)
            create_gmail_draft(
                service,
                sender,
                f"Freedom of Information request – {ref}",
                generate_external_ack(ref),
                thread_id,
            )

            # Claude task for internal allocation
            outputs.append(
                types.TextContent(
                    type="text",
                    text=build_claude_prompt(
                        subject,
                        body,
                        foi_library,
                        teams,
                        ref,
                        thread_id,
                    ),
                )
            )

        if not outputs:
            return [types.TextContent(type="text", text="No unread FOI emails found.")]

        return outputs

    # ----------------------------------------------
    # Tool 2: Claude creates internal draft
    # ----------------------------------------------
    if name == "compose-internal-draft":
        create_gmail_draft(
            service,
            arguments["to"],
            arguments["subject"],
            arguments["body"],
            arguments["thread_id"],
        )
        return [types.TextContent(type="text", text="Internal draft created.")]

    return [types.TextContent(type="text", text="Unknown tool")]


# --------------------------------------------------
# Main
# --------------------------------------------------
async def main():
    async with mcp.server.stdio.stdio_server() as (r, w):
        await server.run(r, w, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())