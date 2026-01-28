# Daily AI News Briefing

Automated system that creates daily AI news briefings from 5 newsletter sources, deduplicates stories, ranks by significance, and sends a formatted email briefing.

## Features

- Fetches newsletters from Gmail (5 AI newsletter sources)
- Extracts news stories using Claude API
- Deduplicates stories reported by multiple sources
- Ranks stories by strategic significance
- Generates professional HTML email briefing
- Sends via Gmail API
- Scheduled daily via GitHub Actions (8:10 AM PT weekdays)

## Newsletter Sources

- Superhuman AI
- Axios AI+
- TechCrunch
- That Startup Guy
- The Rundown AI

## Setup

### 1. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

Required:
- `ANTHROPIC_API_KEY` - Claude API key
- `GMAIL_CREDENTIALS_PATH` - Path to OAuth credentials.json
- `RECIPIENT_EMAIL` - Email recipient

### 3. Gmail API Setup

1. Create Google Cloud project
2. Enable Gmail API
3. Create OAuth 2.0 credentials (Desktop app)
4. Download credentials.json to project root
5. Run locally once to complete OAuth flow

### 4. Run Locally

```bash
python -m src.main
```

## GitHub Actions

The workflow runs automatically at 8:10 AM PT on weekdays.

### Required Secrets

- `ANTHROPIC_API_KEY`
- `GMAIL_TOKEN_JSON` (base64-encoded OAuth token)
- `RECIPIENT_EMAIL`

### Manual Trigger

Use the "Run workflow" button in GitHub Actions to trigger manually.

## Project Structure

```
├── src/
│   ├── config.py           # Configuration management
│   ├── gmail_client.py     # Gmail API operations
│   ├── newsletter_parser.py # Story extraction
│   ├── deduplicator.py     # Deduplication & ranking
│   ├── briefing_generator.py # HTML generation
│   ├── email_sender.py     # Email sending
│   └── main.py             # Orchestrator
├── templates/
│   └── briefing_template.html
├── config.yaml             # Newsletter sources, settings
└── requirements.txt
```

## Configuration

Edit `config.yaml` to customize:
- Newsletter sources
- Recipient email
- Claude model settings
- Briefing format options

## License

Private project.
