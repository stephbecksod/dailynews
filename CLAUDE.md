# Daily News Synthesizer - Development Guide

## Project Overview

An automated daily AI news briefing system that:
1. Fetches newsletters from Gmail (5 sources)
2. Extracts news stories using Claude API
3. Deduplicates and ranks stories by significance
4. Generates a professional HTML email briefing
5. Sends via Gmail API

**Target:** 8:10 AM PT weekday delivery via GitHub Actions.

## Technical Architecture

### Stack
- **Runtime:** Python 3.11+
- **LLM:** Claude API (claude-sonnet-4-5-20250929)
- **Email:** Gmail API (OAuth 2.0)
- **Scheduling:** GitHub Actions (cron)
- **Templates:** Jinja2 for HTML emails

### Design Decisions
1. **Plain text extraction** - Extracts text/plain MIME parts, falls back to HTML-to-text conversion. Reduces token usage by ~92%.
2. **Two-stage Claude processing** - First pass extracts stories, second pass deduplicates and ranks. Keeps prompts focused.
3. **GitHub Actions scheduling** - Runs regardless of local machine state, free tier sufficient.
4. **Environment-based auth** - Supports both local development (credentials.json) and GitHub Actions (secrets).

## File Structure

```
daily-news-synthesizer/
├── .github/workflows/
│   └── daily-briefing.yml      # GitHub Actions workflow
├── src/
│   ├── __init__.py
│   ├── config.py               # Load config.yaml + env vars
│   ├── gmail_client.py         # Gmail API: fetch + send
│   ├── newsletter_parser.py    # Extract stories via Claude
│   ├── deduplicator.py         # Dedupe + rank via Claude
│   ├── briefing_generator.py   # Generate HTML email
│   ├── email_sender.py         # Send via Gmail API
│   └── main.py                 # Orchestrator
├── templates/
│   └── briefing_template.html  # Jinja2 email template
├── tests/
│   └── ...
├── config.yaml                 # Newsletter sources, settings
├── requirements.txt
├── .env.example
├── CLAUDE.md                   # This file
└── project_plan.md             # Full project specification
```

## Setup Instructions

### 1. Clone and Install
```bash
git clone https://github.com/stephbecksod/dailynews.git
cd dailynews
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your API keys
```

Required environment variables:
- `ANTHROPIC_API_KEY` - Claude API key
- `GMAIL_CREDENTIALS_PATH` - Path to OAuth credentials.json (local)
- `GMAIL_TOKEN_JSON` - Base64-encoded token (GitHub Actions)
- `RECIPIENT_EMAIL` - Email recipient

### 3. Gmail API Setup
1. Create Google Cloud project
2. Enable Gmail API
3. Create OAuth 2.0 credentials (Desktop app)
4. Download credentials.json to project root
5. Run locally once to complete OAuth flow

### 4. GitHub Actions Setup
1. Store secrets in repository settings:
   - `ANTHROPIC_API_KEY`
   - `GMAIL_TOKEN_JSON` (base64-encoded oauth token)
   - `RECIPIENT_EMAIL`
2. Enable workflow in Actions tab
3. Test with manual workflow_dispatch trigger

## Development Workflow

### Running Locally
```bash
# Full pipeline
python src/main.py

# Test specific module
python -m pytest tests/test_newsletter_parser.py -v
```

### Testing Changes
1. Make changes to relevant module
2. Run local test: `python src/main.py`
3. Check generated HTML in browser
4. Commit and push
5. Trigger GitHub Actions manually to verify

### Adding a Newsletter Source
1. Add entry to `config.yaml` under `newsletter_sources`
2. Update source name mapping in `newsletter_parser.py` if needed
3. Test with local run

## Git Commit Guidelines

CRITICAL: When committing to GitHub:
- All commits are authored by Steph
- NO references to "Claude Code", "AI-generated", "with assistance from Claude", or any AI tool mentions
- Commit messages describe what was changed, not how it was created
- Keep messages professional and clear

### Commit Message Format
```
<type>: <description>

[optional body with more details]
```

Types:
- `feat:` New feature
- `fix:` Bug fix
- `refactor:` Code restructuring
- `docs:` Documentation
- `test:` Tests
- `chore:` Build/config changes

Examples:
```
feat: Add story extraction from newsletters

fix: Handle missing plain text in email payload

refactor: Simplify deduplication logic

docs: Update setup instructions for Gmail OAuth
```

## Key Files Reference

### config.yaml
Central configuration for newsletter sources, Claude settings, and briefing options.

### src/gmail_client.py
Handles Gmail API authentication and operations:
- `authenticate()` - OAuth flow or token refresh
- `search_newsletters()` - Find today's newsletters
- `get_email_text()` - Extract plain text content
- `send_email()` - Send HTML email

### src/newsletter_parser.py
Extracts stories from newsletter text:
- Uses Claude API with extraction prompt
- Returns structured story data (headline, summary, URL, source)

### src/deduplicator.py
Processes raw stories:
- Groups overlapping stories
- Merges information from multiple sources
- Ranks by strategic significance

### src/briefing_generator.py
Creates the final email:
- Loads Jinja2 template
- Renders with story data
- Returns HTML string

### src/main.py
Orchestrates the full pipeline:
- Fetch newsletters
- Extract stories
- Deduplicate and rank
- Generate briefing
- Send email
- Handle errors with retry logic
