---
name: data-scraper-agent
description: Build a fully automated AI-powered data collection agent for any public source — job boards, prices, news, GitHub, sports, anything. Scrapes on a schedule, optionally enriches data with an explicitly configured LLM, stores results in Notion/Sheets/Supabase, and learns from user feedback. Confirm provider quotas, data permissions and actual hosting costs before deployment. Use when the user wants to monitor, collect, or track any public data automatically.
metadata:
  origin: community
---

# Data Scraper Agent

Build a production-ready, AI-powered data collection agent for any public data source.
Runs on a schedule, enriches results with a free LLM, stores to a database, and improves over time.

**Example stack: Python · explicitly configured LLM · GitHub Actions · Notion / Sheets / Supabase. Availability and pricing must be checked for the actual account.**

## When to Activate

- User wants to scrape or monitor any public website or API
- User says "build a bot that checks...", "monitor X for me", "collect data from..."
- User wants to track jobs, prices, news, repos, sports scores, events, listings
- User asks how to automate data collection without paying for hosting
- User wants an agent that gets smarter over time based on their decisions

## Core Concepts

### The Three Layers

Every data scraper agent has three layers:

```
COLLECT → ENRICH → STORE
  │           │        │
Scraper    AI (LLM)  Database
runs on    scores/   Notion /
schedule   summarises Sheets /
           & classifies Supabase
```

### Free Stack

| Layer | Tool | Why |
|---|---|---|
| **Scraping** | `requests` + `BeautifulSoup` | No cost, covers 80% of public sites |
| **JS-rendered sites** | `playwright` (free) | When HTML scraping fails |
| **AI enrichment** | Explicit configured model via REST API | Account/model quotas; no guaranteed free allowance |
| **Storage** | Notion API | Free tier, great UI for review |
| **Schedule** | GitHub Actions cron | Free for public repos |
| **Learning** | JSON feedback file in repo | Zero infra, persists in git |

### AI Model Fallback Chain

Configure one approved provider/model explicitly. Never switch models silently
on quota, missing-model or network errors. Return an observable enrichment
failure while retaining the raw item for deterministic processing/retry. The
operator chooses any replacement after checking availability, cost and quality.
Gemini 2.0 Flash/Flash-Lite shut down on 2026-06-01; do not generate new clients
using them. Checked 2026-10-06: [deprecations](https://ai.google.dev/gemini-api/docs/deprecations),
[account-dependent quotas](https://ai.google.dev/gemini-api/docs/rate-limits).


### Batch API Calls for Efficiency

Never call the LLM once per item. Always batch:

```python
# BAD: 33 API calls for 33 items
for item in items:
    result = call_ai(item)  # 33 calls → hits rate limit

# GOOD: 7 API calls for 33 items (batch size 5)
for batch in chunks(items, size=5):
    results = call_ai(batch)  # 7 calls → stays within free tier
```

---

## Workflow

### Step 1: Understand the Goal

Ask the user:

1. **What to collect:** "What data source? URL / API / RSS / public endpoint?"
2. **What to extract:** "What fields matter? Title, price, URL, date, score?"
3. **How to store:** "Where should results go? Notion, Google Sheets, Supabase, or local file?"
4. **How to enrich:** "Do you want AI to score, summarise, classify, or match each item?"
5. **Frequency:** "How often should it run? Every hour, daily, weekly?"

Common examples to prompt:
- Job boards → score relevance to resume
- Product prices → alert on drops
- GitHub repos → summarise new releases
- News feeds → classify by topic + sentiment
- Sports results → extract stats to tracker
- Events calendar → filter by interest

---

### Step 2: Design the Agent Architecture

Generate this directory structure for the user:

```
my-agent/
├── config.yaml              # User customises this (keywords, filters, preferences)
├── profile/
│   └── context.md           # User context the AI uses (resume, interests, criteria)
├── scraper/
│   ├── __init__.py
│   ├── main.py              # Orchestrator: scrape → enrich → store
│   ├── filters.py           # Rule-based pre-filter (fast, before AI)
│   └── sources/
│       ├── __init__.py
│       └── source_name.py   # One file per data source
├── ai/
│   ├── __init__.py
│   ├── client.py            # Gemini REST client with explicit model and bounded failure
│   ├── pipeline.py          # Batch AI analysis
│   ├── jd_fetcher.py        # Fetch full content from URLs (optional)
│   └── memory.py            # Learn from user feedback
├── storage/
│   ├── __init__.py
│   └── notion_sync.py       # Or sheets_sync.py / supabase_sync.py
├── data/
│   └── feedback.json        # User decision history (auto-updated)
├── .env.example
├── setup.py                 # One-time DB/schema creation
├── enrich_existing.py       # Backfill AI scores on old rows
├── requirements.txt
└── .github/
    └── workflows/
        └── scraper.yml      # GitHub Actions schedule
```

---

### Step 3: Build the Scraper Source

Template for any data source:

```python
# scraper/sources/my_source.py
"""
[Source Name] — scrapes [what] from [where].
Method: [REST API / HTML scraping / RSS feed]
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from scraper.filters import is_relevant

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)",
}


def fetch() -> list[dict]:
    """
    Returns a list of items with consistent schema.
    Each item must have at minimum: name, url, date_found.
    """
    results = []

    # ---- REST API source ----
    resp = requests.get("https://api.example.com/items", headers=HEADERS, timeout=15)
    if resp.status_code == 200:
        for item in resp.json().get("results", []):
            if not is_relevant(item.get("title", "")):
                continue
            results.append(_normalise(item))

    return results


def _normalise(raw: dict) -> dict:
    """Convert raw API/HTML data to the standard schema."""
    return {
        "name": raw.get("title", ""),
        "url": raw.get("link", ""),
        "source": "MySource",
        "date_found": datetime.now(timezone.utc).date().isoformat(),
        # add domain-specific fields here
    }
```

**HTML scraping pattern:**
```python
soup = BeautifulSoup(resp.text, "lxml")
for card in soup.select("[class*='listing']"):
    title = card.select_one("h2, h3").get_text(strip=True)
    link = card.select_one("a")["href"]
    if not link.startswith("http"):
        link = f"https://example.com{link}"
```

**RSS feed pattern:**
```python
import xml.etree.ElementTree as ET
root = ET.fromstring(resp.text)
for item in root.findall(".//item"):
    title = item.findtext("title", "")
    link = item.findtext("link", "")
```

---

### Step 4: Build the Gemini AI Client

```python
# ai/client.py
import os, json, time, requests

_last_call = 0.0


def generate(prompt: str, model: str = "", rate_limit: float = 7.0) -> dict:
    """One approved model, one attempt. Raw-item pipeline handles failures."""
    global _last_call
    selected = model or os.environ.get("GEMINI_MODEL", "")
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not selected or not api_key:
        return {"enrichment_error": "missing_model_or_credential"}
    # This client expects a Gemini model ID, not an endpoint or path.
    if not all(c.isalnum() or c in "-_." for c in selected):
        return {"enrichment_error": "invalid_model_id"}
    elapsed = time.monotonic() - _last_call
    if elapsed < rate_limit:
        time.sleep(rate_limit - elapsed)
    _last_call = time.monotonic()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{selected}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.3,
            "maxOutputTokens": 2048,
        },
    }
    try:
        resp = requests.post(url, headers={"x-goog-api-key": api_key}, json=payload, timeout=30)
        if resp.status_code != 200:
            return {"enrichment_error": f"provider_status_{resp.status_code}"}
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {"enrichment_error": "invalid_json_shape"}
    except requests.RequestException:
        return {"enrichment_error": "network_failure"}
    except (ValueError, KeyError, IndexError, TypeError):
        return {"enrichment_error": "invalid_provider_response"}

```

---

### Step 5: Build the AI Pipeline (Batch)

```python
# ai/pipeline.py
import json
import yaml
from pathlib import Path
from ai.client import generate

def analyse_batch(items: list[dict], context: str = "", preference_prompt: str = "") -> list[dict]:
    """Analyse items in batches. Returns items enriched with AI fields."""
    config = yaml.safe_load((Path(__file__).parent.parent / "config.yaml").read_text())
    model = config.get("ai", {}).get("model", "")
    rate_limit = config.get("ai", {}).get("rate_limit_seconds", 7.0)
    min_score = config.get("ai", {}).get("min_score", 0)
    batch_size = config.get("ai", {}).get("batch_size", 5)

    batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
    print(f"  [AI] {len(items)} items → {len(batches)} API calls")

    enriched = []
    for i, batch in enumerate(batches):
        print(f"  [AI] Batch {i + 1}/{len(batches)}...")
        prompt = _build_prompt(batch, context, preference_prompt, config)
        result = generate(prompt, model=model, rate_limit=rate_limit)

        if result.get("enrichment_error"):
            # Retain raw items and an observable failure; do not score them as success.
            enriched.extend({**item, "enrichment_error": result["enrichment_error"]} for item in batch)
            continue
        analyses = result.get("analyses", [])
        for j, item in enumerate(batch):
            ai = analyses[j] if j < len(analyses) else {}
            if ai:
                score = max(0, min(100, int(ai.get("score", 0))))
                if min_score and score < min_score:
                    continue
                enriched.append({**item, "ai_score": score, "ai_summary": ai.get("summary", ""), "ai_notes": ai.get("notes", "")})
            else:
                enriched.append(item)

    return enriched


def _build_prompt(batch, context, preference_prompt, config):
    priorities = config.get("priorities", [])
    items_text = "\n\n".join(
        f"Item {i+1}: {json.dumps({k: v for k, v in item.items() if not k.startswith('_')})}"
        for i, item in enumerate(batch)
    )

    return f"""Analyse these {len(batch)} items and return a JSON object.

# Items
{items_text}

# User Context
{context[:800] if context else "Not provided"}

# User Priorities
{chr(10).join(f"- {p}" for p in priorities)}

{preference_prompt}

# Instructions
Return: {{"analyses": [{{"score": <0-100>, "summary": "<2 sentences>", "notes": "<why this matches or doesn't>"}} for each item in order]}}
Be concise. Score 90+=excellent match, 70-89=good, 50-69=ok, <50=weak."""
```

---

### Step 6: Build the Feedback Learning System

```python
# ai/memory.py
"""Learn from user decisions to improve future scoring."""
import json
from pathlib import Path

FEEDBACK_PATH = Path(__file__).parent.parent / "data" / "feedback.json"


def load_feedback() -> dict:
    if FEEDBACK_PATH.exists():
        try:
            return json.loads(FEEDBACK_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"positive": [], "negative": []}


def save_feedback(fb: dict):
    FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    FEEDBACK_PATH.write_text(json.dumps(fb, indent=2))


def build_preference_prompt(feedback: dict, max_examples: int = 15) -> str:
    """Convert feedback history into a prompt bias section."""
    lines = []
    if feedback.get("positive"):
        lines.append("# Items the user LIKED (positive signal):")
        for e in feedback["positive"][-max_examples:]:
            lines.append(f"- {e}")
    if feedback.get("negative"):
        lines.append("\n# Items the user SKIPPED/REJECTED (negative signal):")
        for e in feedback["negative"][-max_examples:]:
            lines.append(f"- {e}")
    if lines:
        lines.append("\nUse these patterns to bias scoring on new items.")
    return "\n".join(lines)
```

**Integration with your storage layer:** after each run, query your DB for items with positive/negative status and call `save_feedback()` with the extracted patterns.

---

### Step 7: Build Storage (Notion example)

```python
# storage/notion_sync.py
import os
from notion_client import Client
from notion_client.errors import APIResponseError

_client = None

def get_client():
    global _client
    if _client is None:
        _client = Client(auth=os.environ["NOTION_TOKEN"])
    return _client

def get_existing_urls(db_id: str) -> set[str]:
    """Fetch all URLs already stored — used for deduplication."""
    client, seen, cursor = get_client(), set(), None
    while True:
        resp = client.databases.query(database_id=db_id, page_size=100, **{"start_cursor": cursor} if cursor else {})
        for page in resp["results"]:
            url = page["properties"].get("URL", {}).get("url", "")
            if url: seen.add(url)
        if not resp["has_more"]: break
        cursor = resp["next_cursor"]
    return seen

def push_item(db_id: str, item: dict) -> bool:
    """Push one item to Notion. Returns True on success."""
    props = {
        "Name": {"title": [{"text": {"content": item.get("name", "")[:100]}}]},
        "URL": {"url": item.get("url")},
        "Source": {"select": {"name": item.get("source", "Unknown")}},
        "Date Found": {"date": {"start": item.get("date_found")}},
        "Status": {"select": {"name": "New"}},
    }
    # AI fields
    if item.get("ai_score") is not None:
        props["AI Score"] = {"number": item["ai_score"]}
    if item.get("ai_summary"):
        props["Summary"] = {"rich_text": [{"text": {"content": item["ai_summary"][:2000]}}]}
    if item.get("ai_notes"):
        props["Notes"] = {"rich_text": [{"text": {"content": item["ai_notes"][:2000]}}]}

    try:
        get_client().pages.create(parent={"database_id": db_id}, properties=props)
        return True
    except APIResponseError as e:
        print(f"[notion] Push failed: {e}")
        return False

def sync(db_id: str, items: list[dict]) -> tuple[int, int]:
    existing = get_existing_urls(db_id)
    added = skipped = 0
    for item in items:
        if item.get("url") in existing:
            skipped += 1; continue
        if push_item(db_id, item):
            added += 1; existing.add(item["url"])
        else:
            skipped += 1
    return added, skipped
```

---

### Step 8: Orchestrate in main.py

```python
# scraper/main.py
import os, sys, yaml
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from scraper.sources import my_source          # add your sources

# NOTE: This example uses Notion. If storage.provider is "sheets" or "supabase",
# replace this import with storage.sheets_sync or storage.supabase_sync and update
# the env var and sync() call accordingly.
from storage.notion_sync import sync

SOURCES = [
    ("My Source", my_source.fetch),
]

def ai_enabled():
    return bool(os.environ.get("GEMINI_API_KEY"))

def main():
    config = yaml.safe_load((Path(__file__).parent.parent / "config.yaml").read_text())
    provider = config.get("storage", {}).get("provider", "notion")

    # Resolve the storage target identifier from env based on provider
    if provider == "notion":
        db_id = os.environ.get("NOTION_DATABASE_ID")
        if not db_id:
            print("ERROR: NOTION_DATABASE_ID not set"); sys.exit(1)
    else:
        # Extend here for sheets (SHEET_ID) or supabase (SUPABASE_TABLE) etc.
        print(f"ERROR: provider '{provider}' not yet wired in main.py"); sys.exit(1)

    config = yaml.safe_load((Path(__file__).parent.parent / "config.yaml").read_text())
    all_items = []

    for name, fetch_fn in SOURCES:
        try:
            items = fetch_fn()
            print(f"[{name}] {len(items)} items")
            all_items.extend(items)
        except Exception as e:
            print(f"[{name}] FAILED: {e}")

    # Deduplicate by URL
    seen, deduped = set(), []
    for item in all_items:
        if (url := item.get("url", "")) and url not in seen:
            seen.add(url); deduped.append(item)

    print(f"Unique items: {len(deduped)}")

    if ai_enabled() and deduped:
        from ai.memory import load_feedback, build_preference_prompt
        from ai.pipeline import analyse_batch

        # load_feedback() reads data/feedback.json written by your feedback sync script.
        # To keep it current, implement a separate feedback_sync.py that queries your
        # storage provider for items with positive/negative statuses and calls save_feedback().
        feedback = load_feedback()
        preference = build_preference_prompt(feedback)
        context_path = Path(__file__).parent.parent / "profile" / "context.md"
        context = context_path.read_text() if context_path.exists() else ""
        deduped = analyse_batch(deduped, context=context, preference_prompt=preference)
    else:
        print("[AI] Skipped — GEMINI_API_KEY not set")

    added, skipped = sync(db_id, deduped)
    print(f"Done — {added} new, {skipped} existing")

if __name__ == "__main__":
    main()
```

---

### Step 9: GitHub Actions Workflow

```yaml
# .github/workflows/scraper.yml
name: Data Scraper Agent

on:
  schedule:
    - cron: "0 */3 * * *"  # every 3 hours — adjust to your needs
  workflow_dispatch:        # allow manual trigger

permissions:
  contents: write   # required for the feedback-history commit step

jobs:
  scrape:
    runs-on: ubuntu-latest
    timeout-minutes: 20

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - run: pip install -r requirements.txt

      # Uncomment if Playwright is enabled in requirements.txt
      # - name: Install Playwright browsers
      #   run: python -m playwright install chromium --with-deps

      - name: Run agent
        env:
          NOTION_TOKEN: ${{ secrets.NOTION_TOKEN }}
          NOTION_DATABASE_ID: ${{ secrets.NOTION_DATABASE_ID }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: python -m scraper.main

      - name: Commit feedback history
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/feedback.json || true
          git diff --cached --quiet || git commit -m "chore: update feedback history"
          git push
```

---

### Step 10: config.yaml Template

```yaml
# Customise this file — no code changes needed

# What to collect (pre-filter before AI)
filters:
  required_keywords: []      # item must contain at least one
  blocked_keywords: []       # item must not contain any

# Your priorities — AI uses these for scoring
priorities:
  - "example priority 1"
  - "example priority 2"

# Storage
storage:
  provider: "notion"         # notion | sheets | supabase | sqlite

# Feedback learning
feedback:
  positive_statuses: ["Saved", "Applied", "Interested"]
  negative_statuses: ["Skip", "Rejected", "Not relevant"]

# AI settings
ai:
  enabled: true
  model: ""                 # Set an approved current model, or GEMINI_MODEL in env
  min_score: 0               # filter out items below this score
  rate_limit_seconds: 7      # seconds between API calls
  batch_size: 5              # items per API call
```

---

## Common Scraping Patterns

### Pattern 1: REST API (easiest)
```python
resp = requests.get(url, params={"q": query}, headers=HEADERS, timeout=15)
items = resp.json().get("results", [])
```

### Pattern 2: HTML Scraping
```python
soup = BeautifulSoup(resp.text, "lxml")
for card in soup.select(".listing-card"):
    title = card.select_one("h2").get_text(strip=True)
    href = card.select_one("a")["href"]
```

### Pattern 3: RSS Feed
```python
import xml.etree.ElementTree as ET
root = ET.fromstring(resp.text)
for item in root.findall(".//item"):
    title = item.findtext("title", "")
    link = item.findtext("link", "")
    pub_date = item.findtext("pubDate", "")
```

### Pattern 4: Paginated API
```python
page = 1
while True:
    resp = requests.get(url, params={"page": page, "limit": 50}, timeout=15)
    data = resp.json()
    items = data.get("results", [])
    if not items:
        break
    for item in items:
        results.append(_normalise(item))
    if not data.get("has_more"):
        break
    page += 1
```

### Pattern 5: JS-Rendered Pages (Playwright)
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(url)
    page.wait_for_selector(".listing")
    html = page.content()
    browser.close()

soup = BeautifulSoup(html, "lxml")
```

---

## Anti-Patterns to Avoid

| Anti-pattern | Problem | Fix |
|---|---|---|
| One LLM call per item | Hits rate limits instantly | Batch 5 items per call |
| Hardcoded keywords in code | Not reusable | Move all config to `config.yaml` |
| Scraping without rate limit | IP ban | Add `time.sleep(1)` between requests |
| Storing secrets in code | Security risk | Always use `.env` + GitHub Secrets |
| No deduplication | Duplicate rows pile up | Always check URL before pushing |
| Ignoring `robots.txt` | Legal/ethical risk | Respect crawl rules; use public APIs when available |
| JS-rendered sites with `requests` | Empty response | Use Playwright or look for the underlying API |
| `maxOutputTokens` too low | Truncated JSON, parse error | Use 2048+ for batch responses |

---

## Capacity and cost preflight

Check current account quotas, model availability, storage/API limits and scheduled
runner costs before enabling the schedule. Free allowances vary and are not a
production guarantee. Capture the checked date and a bounded request budget.
On 429 keep raw results, report quota exhaustion and defer retries under that
budget; do not expand to another model/provider automatically.

---

## Requirements Template

```
requests  # Resolve a supported version in the project lockfile
beautifulsoup4
lxml
python-dotenv
pyyaml
notion-client   # if using Notion
# playwright   # uncomment for JS-rendered sites
```

---

## Quality Checklist

Before marking the agent complete:

- [ ] `config.yaml` controls all user-facing settings — no hardcoded values
- [ ] `profile/context.md` holds user-specific context for AI matching
- [ ] Deduplication by URL before every storage push
- [ ] Explicit approved model; missing config, 429, 404 and network errors retain raw data without switching providers/models
- [ ] Batch size ≤ 5 items per API call
- [ ] `maxOutputTokens` ≥ 2048
- [ ] `.env` is in `.gitignore`
- [ ] `.env.example` provided for onboarding
- [ ] `setup.py` creates DB schema on first run
- [ ] `enrich_existing.py` backfills AI scores on old rows
- [ ] GitHub Actions workflow commits `feedback.json` after each run
- [ ] README covers: setup in < 5 minutes, required secrets, customisation

---

## Real-World Examples

```
"Build me an agent that monitors Hacker News for AI startup funding news"
"Scrape product prices from 3 e-commerce sites and alert when they drop"
"Track new GitHub repos tagged with 'llm' or 'agents' — summarise each one"
"Collect Chief of Staff job listings from LinkedIn and Cutshort into Notion"
"Monitor a subreddit for posts mentioning my company — classify sentiment"
"Scrape new academic papers from arXiv on a topic I care about daily"
"Track sports fixture results and keep a running table in Google Sheets"
"Build a real estate listing watcher — alert on new properties under ₹1 Cr"
```

---

## Reference Implementation

A complete working agent built with this exact architecture would scrape 4+ sources,
batch Gemini calls, learn from Applied/Rejected decisions stored in Notion, and run
100% free on GitHub Actions. Follow Steps 1–9 above to build your own.
