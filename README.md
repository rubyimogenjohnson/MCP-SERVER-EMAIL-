# MCP Email Server

An MCP (Model Context Protocol) server that integrates with the Gmail API, allowing Claude and other AI assistants to read unread emails and create draft replies.

## Features

- **Read Unread Emails**: Fetch unread emails from your Gmail inbox with sender, subject, snippet, and thread ID
- **Create Draft Replies**: Generate draft replies to emails without automatically sending them

- **OAuth 2.0**: Secure authentication using Google OAuth 2.0
- **Claude Integration**: Works seamlessly with Claude Desktop

## Quick Start

### Prerequisites

- Python 3.14+
- Poetry
- Google Cloud Project with Gmail API enabled
- Claude Desktop 

### Setup

1. **Clone or download this repository**

2. **Install dependencies**:
```bash
cd mcp-server-email
poetry install
```

3. **Set up Gmail OAuth 2.0**:

   a. Go to [Google Cloud Console](https://console.cloud.google.com/)
   
   b. Create a new project:
      - Click "Select a Project" -> "New Project"
      - Name: "MCP Email Server"
      - Click "Create"
   
   c. Enable Gmail API:
      - Go to "APIs & Services" -> "Library"
      - Search for "Gmail API"
      - Click it and press "Enable"
   
   d. Create OAuth 2.0 credentials:
      - Go to "APIs & Services" -> "Credentials"
      - Click "Create Credentials"-> "OAuth client ID"
      - Choose "Desktop application"
      - Name: "MCP Email Server"
      - Click "Create"
      - Click "Download JSON"
      - Save as `credentials.json` in the project root

4. **Configure Claude Desktop** (see [CLAUDE_DESKTOP_SETUP.md](./CLAUDE_DESKTOP_SETUP.md))


## Scripts

#### 1. `get_unread_emails`
Fetches unread emails from your Gmail inbox.

**Parameters:**
- `max_results` (int, optional): Maximum number of emails to fetch (default: 10)

**Returns:**
- List of emails with:
  - `messageId`: Gmail message ID
  - `threadId`: Thread ID (for replies)
  - `from`: Sender email
  - `subject`: Email subject
  - `snippet`: Preview text
  - `body`: Full email body
  - `date`: Email date

**Example Response:**
```json
[
  {
    "messageId": "188b8c5d0bd2e2cc",
    "threadId": "188b8c5d0bd2e2cc",
    "from": "john@example.com",
    "to": "you@gmail.com",
    "subject": "Project Update",
    "snippet": "Here's the latest on the project...",
    "body": "Full email content here...",
    "date": "Mon, 8 Dec 2025 10:30:00 +0000"
  }
]
```

#### 2. `create_draft_reply`
Creates a draft reply to an email in a thread (does not send automatically).

**Parameters:**
- `thread_id` (string, required): Thread ID of the email to reply to
- `to_email` (string, required): Recipient email address
- `subject` (string, required): Reply subject (e.g., "Re: Original Subject")
- `body` (string, required): Body text of the reply

**Example Request:**
```json
{
  "thread_id": "188b8c5d0bd2e2cc",
  "to_email": "john@example.com",
  "subject": "Re: Project Update",
  "body": "Thanks for the update! Here's my feedback..."
}
```

**Returns:**
```json
{
  "success": true,
  "draftId": "18d7b3e4c5f2g1h9",
  "threadId": "188b8c5d0bd2e2cc",
  "message": "Draft created successfully"
}
```


## How It Works

1. **Authentication**: First run opens a browser for OAuth 2.0 consent. Tokens are stored locally.
2. **Email Fetching**: Uses Gmail API with `is:unread` filter to get recent unread messages.
3. **Draft Creation**: Creates properly threaded replies using the Gmail API without sending.
4. **Thread Context**: Can retrieve full thread history for conversation understanding.

## Stretch Goals

This implementation can be enhanced with:

1. **Email Templates**: Add reply templates from Notion for consistent responses
2. **Style Guide**: Integrate with Google Docs for email style guidelines
3. **Knowledge Base**: Pull context from local files or Obsidian vault for intelligent replies
4. **Email Scheduling**: Queue drafts for scheduled sending
5. **Attachment Handling**: Support downloading and analyzing attachments
6. **Sentiment Analysis**: Analyze email sentiment to suggest reply tone
7. **Priority Filtering**: Identify priority emails using custom labels or ML
8. **Multi-account Support**: Handle multiple Gmail accounts

## License

MIT License - See LICENSE file for details

## Support

[FINISH]

## References

- [Model Context Protocol Documentation](https://modelcontextprotocol.io/)
- [Gmail API Documentation](https://developers.google.com/gmail/api)
- [Google OAuth 2.0 Guide](https://developers.google.com/identity/protocols/oauth2)
- [Claude Desktop Documentation](https://claude.ai/resources/en/claude-desktop)

