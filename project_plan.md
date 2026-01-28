# AI Newsletter Daily Briefing System - Project Plan

## Overview
An automated system that creates daily AI news briefings from 5 newsletters, with future phases for audio podcasts and a multi-user web application.

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
│   ├── gmail_client.py             # Gmail API wrapper (adapted from existing)
│   ├── newsletter_parser.py        # Story extraction logic
│   ├── deduplicator.py             # Deduplication & synthesis
│   ├── briefing_generator.py       # Creates formatted briefing
│   ├── email_sender.py             # Sends briefing via Gmail
│   └── main.py                     # Orchestrator
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

## Phase 2: Audio Podcast (Future)

### Additions to Project
```
src/
├── audio/
│   ├── tts_client.py           # Text-to-speech wrapper
│   ├── podcast_script.py       # Convert briefing to script format
│   └── audio_assembler.py      # Combine intro/stories/outro
```

### TTS Recommendation: ElevenLabs
- **Why:** Most natural-sounding, good podcast voices
- **Cost:** ~$5/month for 30k characters (sufficient for daily briefing)
- **Alternative:** OpenAI TTS ($15/1M chars) - cheaper but less natural

### Podcast Structure
1. **Intro** (5 sec): "Good morning, here's your AI briefing for [date]"
2. **Executive Summary** (30 sec): TL;DR bullets
3. **Top Stories** (3-5 min): Detailed coverage
4. **Outro** (5 sec): "That's your AI briefing. See you tomorrow."

### Delivery
- Attach MP3 to daily email
- Or: Upload to cloud storage, include link in email

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
- [ ] Briefing email arrives by 8:15 AM PT on weekdays
- [ ] All 5 newsletters processed (when available)
- [ ] Stories properly deduplicated across sources
- [ ] HTML email renders correctly in Gmail
- [ ] Error notifications sent on failures

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
