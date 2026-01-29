# AI Newsletter Daily Briefing System - Project Plan

## Overview
An automated system that creates daily AI news briefings from 5 newsletters, with future phases for audio podcasts and a multi-user web application.

## Status
- **Phase 1: Daily Email Briefing** - COMPLETE
- **Phase 2: Audio Podcast** - COMPLETE
- **Phase 3: Web Application** - Not started

## Existing Asset: ai_newsletter_curator
Located at: `C:\Users\steph\OneDrive\Desktop\Claude Code\Newsletter\ai-newsletter-curator`

**Reusable components:**
- `gmail_text_extractor.py` - Plain text extraction from Gmail (92% token savings vs HTML)
- `extract_all_newsletters.py` - Claude-powered story extraction patterns
- `deduplicate_and_rank.py` - Deduplication and ranking logic
- `config.yaml` - Newsletter source configuration

**Key difference:** The existing project is a weekly, human-in-the-loop Claude Code skill. This new project needs fully automated daily runs with email delivery.

---

## Technical Architecture

### Tech Stack
| Component | Technology | Justification |
|-----------|------------|---------------|
| Runtime | Python 3.11+ | Matches existing codebase, rich AI/ML ecosystem |
| AI/LLM | Claude API (claude-sonnet-4-5) | Already proven in existing project |
| Email Access | Gmail API (OAuth) | Direct API access for scheduled automation |
| Scheduling | GitHub Actions | Free, reliable, no local machine dependency |
| TTS (Phase 2) | ElevenLabs or OpenAI TTS | High quality, reasonable cost |
| Web (Phase 3) | Next.js + FastAPI | Mobile-ready frontend, Python backend reuse |
| Database (Phase 3) | PostgreSQL + Supabase | Auth, storage, scales well |

### Why GitHub Actions for Scheduling?
- Runs regardless of whether your computer is on
- Free tier: 2,000 minutes/month (plenty for daily 5-min job)
- Built-in secrets management for API keys
- Easy to monitor and debug via logs
- Can trigger email notifications on failure

---

## Project Structure

```
daily-news-synthesizer/
├── .github/
│   └── workflows/
│       └── daily-briefing.yml      # GitHub Actions scheduler
├── src/
│   ├── __init__.py
│   ├── config.py                   # Configuration management
│   ├── gmail_client.py             # Gmail API wrapper (with attachment support)
│   ├── newsletter_parser.py        # Story extraction logic
│   ├── deduplicator.py             # Deduplication & synthesis
│   ├── briefing_generator.py       # Creates formatted briefing
│   ├── email_sender.py             # Sends briefing via Gmail
│   ├── main.py                     # Orchestrator
│   └── audio/                      # Phase 2: Audio generation
│       ├── __init__.py
│       ├── script_generator.py     # Convert stories to spoken script
│       └── tts_client.py           # ElevenLabs TTS wrapper
├── templates/
│   └── briefing_template.html      # Email HTML template
├── tests/
│   └── ...                         # Unit tests
├── config.yaml                     # Newsletter sources, settings
├── requirements.txt
├── .env.example
└── README.md
```

---

## Phase 1: Daily Email Briefing

### Data Flow
```
[8:10 AM PT] GitHub Actions Trigger
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  1. FETCH NEWSLETTERS                                    │
│     Gmail API → Search today's emails from 5 senders    │
│     Extract plain text (not HTML)                        │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  2. EXTRACT STORIES                                      │
│     Claude API → Parse each newsletter                   │
│     Extract: headline, summary, source, URL              │
│     Filter: news only (not tips, tools, tutorials)       │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  3. DEDUPLICATE & SYNTHESIZE                            │
│     Claude API → Group overlapping stories               │
│     Merge: combine info from multiple sources            │
│     Rank: by strategic significance                      │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  4. GENERATE BRIEFING                                    │
│     Format as rich HTML email with sections:             │
│     - Executive Summary (3-5 bullet TL;DR)               │
│     - Top Stories (5 most significant, detailed)         │
│     - All Other Stories (remaining, grouped by tier)     │
│     - Sources (list of newsletters processed)            │
│     Professional styling with colors and formatting      │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  5. SEND EMAIL                                           │
│     Gmail API → Send to configured recipient             │
│     Include: timestamp, story count, source list         │
└─────────────────────────────────────────────────────────┘
```

### Newsletter Sources
1. `superhuman@mail.joinsuperhuman.ai` - Superhuman AI
2. `ai.plus@axios.com` - Axios AI+
3. `newsletters@techcrunch.com` - TechCrunch
4. `thatstartupguy@mail.beehiiv.com` - That Startup Guy
5. `news@daily.therundown.ai` - The Rundown AI

### Schedule
- **Time:** 8:10 AM PT (16:10 UTC) weekdays
- **Cron:** `10 16 * * 1-5` (GitHub Actions uses UTC)

### Error Handling
- If newsletter missing: continue with available newsletters, note in briefing
- If API fails: retry 3x with exponential backoff
- If all fails: send error notification email
- All runs logged to GitHub Actions for debugging

### GitHub Actions Workflow
```yaml
name: Daily AI Briefing
on:
  schedule:
    - cron: '10 16 * * 1-5'  # 8:10 AM PT, weekdays
  workflow_dispatch:          # Manual trigger for testing

jobs:
  generate-briefing:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python src/main.py
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GMAIL_CREDENTIALS: ${{ secrets.GMAIL_CREDENTIALS }}
          RECIPIENT_EMAIL: ${{ secrets.RECIPIENT_EMAIL }}
```

### Gmail Authentication for GitHub Actions
- Create Google Cloud service account or use OAuth refresh token
- Store credentials as GitHub secret
- `gmail_client.py` handles auth from environment variable

---

## Phase 2: Audio Podcast - COMPLETE

### Implementation
- **TTS Provider:** ElevenLabs (Rachel voice)
- **Content:** Top 5 stories + 10 secondary stories (~7 min podcast)
- **Delivery:** MP3 attached to daily briefing email
- **Cost:** ~$5-11/month depending on plan

### Files Added
```
src/audio/
├── __init__.py
├── script_generator.py     # Converts stories to natural spoken script
└── tts_client.py           # ElevenLabs API wrapper
```

### Podcast Structure (as implemented)
1. **Intro:** "Good morning. Here's your AI news briefing for [date]..."
2. **Quick Headlines:** Overview of top 5 stories
3. **Top Stories:** Detailed coverage with "why it matters"
4. **Secondary Stories:** Brief roundup of additional stories
5. **Outro:** Sign-off with source attribution

### GitHub Secrets Required
- `ELEVENLABS_API_KEY` - ElevenLabs API key for TTS

---

## Phase 3: Web Application (Future)

### Architecture
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Next.js App   │────▶│   FastAPI       │────▶│   PostgreSQL    │
│   (Frontend)    │     │   (Backend)     │     │   (Supabase)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │
        │                       ▼
        │               ┌─────────────────┐
        │               │  Background     │
        │               │  Workers        │
        │               │  (Celery/RQ)    │
        │               └─────────────────┘
        │                       │
        ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│   User Gmail    │     │   Claude API    │
│   OAuth         │     │   + TTS         │
└─────────────────┘     └─────────────────┘
```

### Key Features
- **Auth:** Supabase Auth (OAuth with Google)
- **Email Connection:** Each user connects their Gmail via OAuth
- **Newsletter Selection:** Users configure which senders to monitor
- **Processing:** Background workers process per-user briefings
- **Storage:** PostgreSQL for users, preferences, briefing history
- **Mobile-Ready:** Next.js with responsive design, PWA capable

### Scaling Considerations
- Batch user processing in time windows
- Rate limit Claude API calls
- Cache common newsletter parsing
- Consider shared deduplication across users

### Key Challenge: User Email Access

The biggest challenge for Phase 3 is how users connect their email to fetch newsletters. The current MCP token approach won't work for multi-user.

#### The Gmail OAuth Problem
- **Web OAuth flow** requires redirect URLs, server handling
- **Google verification** required for 100+ users (4-6 week process)
- **Sensitive scope restrictions** - `gmail.readonly` gets extra scrutiny
- **Secure token storage** - must encrypt refresh tokens per user

#### Options to Consider

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| **1. Email Forwarding** | Users set up Gmail forwarding rules to central inbox | No OAuth needed, works immediately | Manual setup, trust issues |
| **2. Dedicated Email per User** | Each user gets `user123@yourdomain.com`, subscribes newsletters there | Full control, no Gmail OAuth | Users must re-subscribe, email hosting costs ($15-50/mo) |
| **3. RSS Feeds** | Fetch newsletter content via RSS instead of email | No email access needed | Not all newsletters have RSS |
| **4. Full Gmail OAuth** | Go through Google's verification process | Best UX, professional | 4-6 week delay, compliance burden |
| **5. Google Workspace Only** | Limit to business accounts (internal apps skip verification) | Launch immediately | Excludes personal Gmail users |

#### Recommended Approach
- **MVP:** Start with Option 2 (dedicated email) or Option 1 (forwarding) to validate product
- **Long-term:** Apply for Google OAuth verification in parallel for native Gmail connection later

---

## Implementation Order

### Phase 1 Tasks (Recommended Order)
1. **Setup project structure** - Create folders, requirements.txt, config.yaml
2. **Adapt gmail_client.py** - Port from existing project, add env-based auth
3. **Implement newsletter_parser.py** - Story extraction using Claude API
4. **Implement deduplicator.py** - Deduplication and ranking
5. **Implement briefing_generator.py** - HTML email formatting
6. **Implement email_sender.py** - Send via Gmail API
7. **Create main.py orchestrator** - Wire everything together
8. **Test locally** - Run manually, verify output
9. **Setup GitHub Actions** - Configure secrets, test scheduled run
10. **Monitor first week** - Check logs, adjust as needed

---

## Configuration Reference (config.yaml)
```yaml
newsletter_sources:
  - email: superhuman@mail.joinsuperhuman.ai
    name: Superhuman AI
  - email: ai.plus@axios.com
    name: Axios AI+
  - email: newsletters@techcrunch.com
    name: TechCrunch
  - email: thatstartupguy@mail.beehiiv.com
    name: That Startup Guy
  - email: news@daily.therundown.ai
    name: The Rundown AI

briefing:
  recipient: stephanie.soderborg@gmail.com
  subject_prefix: "[AI Briefing]"
  format: rich_html
  include_all_stories: true

claude:
  model: claude-sonnet-4-5-20250929
  max_tokens: 8000

schedule:
  time: "08:10"
  timezone: "America/Los_Angeles"
  weekdays_only: true
```

---

## Verification Plan

### Phase 1 Testing
1. **Unit tests** - Each module tested independently
2. **Integration test** - Full pipeline with real newsletters
3. **Manual trigger** - Use `workflow_dispatch` to test GitHub Actions
4. **First week monitoring** - Check logs daily, verify email delivery
5. **Edge cases** - Test: missing newsletter, API timeout, empty day

### Success Criteria
- [x] Briefing email arrives by 8:15 AM PT on weekdays
- [x] All 5 newsletters processed (when available)
- [x] Stories properly deduplicated across sources
- [x] HTML email renders correctly in Gmail
- [x] Error notifications sent on failures
- [x] Audio podcast generated and attached (Phase 2)

---

## Estimated Costs

### Phase 1 (Daily)
- **Claude API:** ~$0.50-1.00/day (Sonnet for extraction + dedup)
- **GitHub Actions:** Free tier (well under 2,000 min/month)
- **Gmail API:** Free
- **Total:** ~$15-30/month

### Phase 2 (adds audio)
- **ElevenLabs:** ~$5-11/month (depending on plan)
- **Total:** ~$20-40/month

### Phase 3 (web app)
- **Supabase:** Free tier to start, $25/month at scale
- **Vercel (Next.js):** Free tier to start
- **Background workers:** Depends on scale
- **Total:** Varies with user count

---

## Decisions Made

- **Email format:** Rich HTML with professional styling
- **Story count:** All unique stories after deduplication (tiered by importance)
- **Repository:** Use existing `stephbecksod/dailynews` repo
- **Audio TTS:** ElevenLabs with Rachel voice (natural, professional)
- **Audio content:** Top + secondary stories (~7 min), not "Also Noted" headlines
- **Audio delivery:** MP3 attachment (simpler than streaming link)
- **Gmail auth:** MCP server token reused, base64-encoded for GitHub Actions
