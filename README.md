# MCP Email Server (FOI Automation)

An MCP (Model Context Protocol) server that integrates with the Gmail API, allowing Claude and other AI assistants to automate Freedom of Information (FOI) request handling for Camden. The server can:
- Read unread emails
- Suggest similar previous FOI responses
- Assign requests to the best team using CSV mapping
- Generate a professional FOI receipt draft (with Camden header and sign-off)


## Features

- **Read Unread Emails**: Fetch unread emails from your Gmail inbox with sender, subject, content, and key points
- **FOI Draft Automation**: Claude suggests the best team and similar FOIs, then generates a professional receipt draft
- **Team Mapping**: Uses CSVs to map subject keywords to teams and officers
- **Knowledge Base**: Looks up similar FOI responses from a CSV
- **Professional Receipts**: Drafts include Camden header, case reference, and correct sign-off
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

5. **Prepare Required CSVs**

Place the following CSV files in the project root (examples below):

- `Camden_Freedom_Of_Information_Responses_Search_20251211.csv` (FOI knowledge base)
- `foi_team_mapping.csv` (maps subject keywords to teams/officers)
- `foi_team_contacts.csv` (maps teams to officer emails)

#### Example: camden_foi_responses.csv

Download from [https://opendata.camden.gov.uk/Your-Council/Camden-Freedom-Of-Information-Responses-Search/fkj6-gqb4/about_data]

```
Identifier,Date,Document Title,Document Text,Document Link
CAM1001,2024-01-15,Children's Services Budget,The budget for children's services in 2023 was £5m.,https://example.com/foi/CAM1001
CAM1002,2024-02-10,Housing Allocations,Details of housing allocations for 2023.,https://example.com/foi/CAM1002
CAM1003,2024-03-05,Finance Reports,Annual finance reports for 2023.,https://example.com/foi/CAM1003
CAM1004,2024-04-20,Information Rights Requests,Summary of information rights requests.,https://example.com/foi/CAM1004
```

#### Example: foi_team_mapping.csv

```
subject_keyword,team,officer
children,Children's Services,Children's Services Officer
housing,Housing Team,Housing Officer
finance,Finance Team,Finance Officer
information rights,Information Rights Team,Information Rights Officer
```

#### Example: foi_team_contacts.csv

```
team,officer_email
Children's Services,childrens.services@camden.gov.uk
Housing Team,housing@camden.gov.uk
Finance Team,finance@camden.gov.uk
Information Rights Team,foi@camden.gov.uk
```

## Claude Desktop Configuration

The server is designed to be launched from Claude Desktop using a configuration JSON file. This file tells Claude Desktop how to start the MCP server and where to find credentials.


**Example: `claude_desktop_config.json`**

```json
{
   "mcpServers": {
      "mcp-server-email": {
         "command": "/path/to/your/virtualenv/bin/python",
         "args": [
            "/path/to/your/mcp-server-email/src/server.py"
         ],
         "cwd": "/path/to/your/mcp-server-email",
         "env": {
            "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/your/mcp-server-email/src/credentials.json"
         }
      }
   }
}
```

**Fields:**
- `command`: Path to the Python executable in your Poetry/virtualenv
- `args`: List of arguments (should point to your `server.py`)
- `cwd`: Working directory for the server
- `env`: Environment variables (e.g., path to Google credentials)

**Security:**
> Do not commit `claude_desktop_config.json` to version control, as it may contain sensitive paths or credentials.


## Scripts

#### 1. `get-unread-emails`

Fetches unread emails from your Gmail inbox.

**Returns:**
- List of emails with:
  - `From`: Sender
  - `Subject`: Email subject
  - `Content`: First 200 characters of the email
  - `Key Points`: Up to 3 key lines from the email
  - `ID`: Gmail message ID


#### 2. `compose-draft`
Creates a professional FOI receipt draft for a request, using team and officer details provided by Claude (after it looks up similar FOIs and the best team).

**Parameters:**
- `recipient_id` (string, required): Recipient email address
- `subject` (string, required): FOI subject
- `team` (string, required): Team to handle the request (from mapping)
- `officer` (string, required): Officer name (from mapping)
- `bcc_email` (string, optional): BCC address for the team
- `foi_id` (string, required): Unique FOI case reference (e.g., CAM1234)
- `request_date` (string, required): Date of request (e.g., 12/12/2025)

**Returns:**
- Confirmation that the FOI receipt draft was created



## How It Works


1. **Authentication**: First run opens a browser for OAuth 2.0 consent. Tokens are stored locally.
2. **Email Fetching**: Uses Gmail API with `is:unread` filter to get recent unread messages.
3. **FOI Draft Flow**:
  - Claude reads the email and extracts the subject
  - Claude calls `find_similar_foi_responses` to look up similar FOIs in the CSV
  - Claude calls `find_best_team_for_subject` to pick the best team
  - Claude calls `compose-draft` with all details to generate a professional FOI receipt draft


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

## References

- [Model Context Protocol Documentation](https://modelcontextprotocol.io/)
- [Gmail API Documentation](https://developers.google.com/gmail/api)
- [Google OAuth 2.0 Guide](https://developers.google.com/identity/protocols/oauth2)
- [Claude Desktop Documentation](https://claude.ai/resources/en/claude-desktop)

