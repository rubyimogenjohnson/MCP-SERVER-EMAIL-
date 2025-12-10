# src/mcp_server_email/gmail_client.py

from __future__ import annotations

import base64
import os
from email.message import EmailMessage
from pathlib import Path
from typing import Dict, List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Scopes:
# - gmail.readonly: read unread messages
# - gmail.compose: create drafts
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
]


def _project_root() -> Path:
    """
    Return the project root (folder containing pyproject.toml),
    assuming this file is inside src/mcp_server_email/.
    """
    here = Path(__file__).resolve()
    # src/mcp_server_email/gmail_client.py -> src/mcp_server_email -> src -> project root
    return here.parents[2]


def _get_credentials() -> Credentials:
    """
    Load Gmail OAuth credentials, or run the browser OAuth flow the first time.

    Requires:
    - credentials.json in the project root
    Creates:
    - token.json in the project root after first successful auth
    """
    root = _project_root()
    token_path = root / "token.json"
    creds_path = root / "credentials.json"

    creds: Credentials | None = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    # If no valid creds, or expired, refresh or run OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not creds_path.exists():
                raise FileNotFoundError(
                    f"credentials.json not found at {creds_path}. "
                    "Download OAuth client credentials from Google Cloud "
                    "and place them in the project root."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(creds_path), SCOPES
            )
            # This opens a browser once to let you log in and approve access
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with token_path.open("w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())

    return creds


def _get_gmail_service():
    """Build and return a Gmail API service client."""
    creds = _get_credentials()
    return build("gmail", "v1", credentials=creds)


def get_unread_emails(limit: int = 5) -> List[Dict[str, str]]:
    """
    Return up to `limit` unread emails from the inbox.

    Each item has:
    - id: Gmail message id
    - thread_id: Gmail thread id
    - sender: "From" header
    - subject: "Subject" header
    - snippet: small preview of the body
    """
    service = _get_gmail_service()
    try:
        response = (
            service.users()
            .messages()
            .list(
                userId="me",
                q="is:unread in:inbox",
                maxResults=limit,
            )
            .execute()
        )
    except HttpError as err:
        # Return a structured error that the model can read
        return [
            {
                "id": "",
                "thread_id": "",
                "sender": "",
                "subject": "Error while listing unread emails",
                "snippet": str(err),
            }
        ]

    messages = response.get("messages", [])
    results: List[Dict[str, str]] = []

    for m in messages:
        msg_id = m["id"]
        try:
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=msg_id, format="full")
                .execute()
            )
        except HttpError as err:
            results.append(
                {
                    "id": msg_id,
                    "thread_id": "",
                    "sender": "",
                    "subject": "Error loading this message",
                    "snippet": str(err),
                }
            )
            continue

        payload = msg.get("payload", {})
        headers = {h["name"]: h["value"] for h in payload.get("headers", [])}

        sender = headers.get("From", "")
        subject = headers.get("Subject", "")
        snippet = msg.get("snippet", "")

        results.append(
            {
                "id": msg.get("id", ""),
                "thread_id": msg.get("threadId", ""),
                "sender": sender,
                "subject": subject,
                "snippet": snippet,
            }
        )

    return results


def create_reply_draft(message_id: str, reply_body: str) -> Dict[str, str]:
    """
    Create a Gmail draft reply to the message with the given message_id.

    - Looks up the original message (to get Subject, From, Message-Id, threadId)
    - Builds a reply email with:
        - To = original sender or Reply-To
        - Subject = "Re: <original subject>" (if not already Re:)
        - In-Reply-To / References headers set for correct threading
        - threadId set so it appears in the same thread
    - Creates a draft and returns basic info.
    """
    service = _get_gmail_service()

    try:
        original = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=message_id,
                format="metadata",
                metadataHeaders=[
                    "Subject",
                    "From",
                    "To",
                    "Reply-To",
                    "Message-Id",
                ],
            )
            .execute()
        )
    except HttpError as err:
        return {
            "status": "error",
            "error": f"Failed to load original message: {err}",
        }

    thread_id = original.get("threadId", "")
    payload = original.get("payload", {})
    headers = {h["name"]: h["value"] for h in payload.get("headers", [])}

    subject = headers.get("Subject", "")
    message_id_header = headers.get("Message-Id", "")
    reply_to = headers.get("Reply-To")
    from_header = headers.get("From")
    to_header = headers.get("To")

    # Decide who to send the reply to
    to_value = reply_to or from_header or to_header or ""

    # Ensure subject starts with "Re:"
    if subject.lower().startswith("re:"):
        reply_subject = subject
    else:
        reply_subject = f"Re: {subject}" if subject else "Re: (no subject)"

    # Build the MIME email
    email_msg = EmailMessage()
    if to_value:
        email_msg["To"] = to_value
    email_msg["Subject"] = reply_subject

    if message_id_header:
        email_msg["In-Reply-To"] = message_id_header
        email_msg["References"] = message_id_header

    email_msg.set_content(reply_body)

    # Encode as base64url for Gmail API
    raw_bytes = email_msg.as_bytes()
    raw_b64 = base64.urlsafe_b64encode(raw_bytes).decode("utf-8")

    message_payload: Dict[str, object] = {"raw": raw_b64}
    if thread_id:
        message_payload["threadId"] = thread_id

    try:
        draft = (
            service.users()
            .drafts()
            .create(userId="me", body={"message": message_payload})
            .execute()
        )
    except HttpError as err:
        return {
            "status": "error",
            "error": f"Failed to create draft: {err}",
        }

    return {
        "status": "ok",
        "draft_id": draft.get("id", ""),
        "thread_id": draft.get("message", {}).get("threadId", thread_id),
    }
