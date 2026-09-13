# SmartResume.ai — Job Sources & External Provider Setup Guide

This document details the configuration and architecture of live job opportunity discovery in **SmartResume.ai**.

---

## 1. Architecture Overview

SmartResume.ai utilizes a hybrid multi-source architecture for job matching and discovery:

```
┌──────────────────────────────────────────────────────────────┐
│                    Job Radar Service                         │
└──────────────────────────────┬───────────────────────────────┘
                               │
       ┌───────────────────────┼───────────────────────┐
       ▼                       ▼                       ▼
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│ Saved Target │       │ External API │       │ Curated Demo │
│  Jobs (DB)   │       │  Aggregator  │       │  Seeds (Opt) │
└──────────────┘       └──────────────┘       └──────────────┘
```

1. **User Target Jobs (`DatabaseJobProvider`)**:
   - Primary source of truth.
   - Any job posting created directly by the user in the UI or imported via the SmartApply browser extension is stored in the PostgreSQL database.
   - Matched against the user's Master Profile skills and evidence without external dependencies.

2. **Live External Job Aggregators (`ExternalJobAggregatorProvider`)**:
   - Queries verified job aggregator APIs (such as **Adzuna** or **RapidAPI JSearch**) in real time.
   - Automatically active when API credentials are provided in `.env`.

3. **Curated Demo Seeds (`CuratedSeedJobProvider`)**:
   - High-quality seed listings for testing, initial onboarding, and demonstration purposes.
   - Every seed item is explicitly tagged with `is_seed: true` and `source: "Curated Tech Demo Seeds"`.
   - Seed items can be toggled on/off via the query parameter `include_seeds=true/false`.
   - Never presented as real unverified live market postings.

---

## 2. Environment Variables

Configure the following variables in your `backend/.env` or deployment environment:

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `ADZUNA_APP_ID` | string | `None` | Adzuna Developer Application ID. |
| `ADZUNA_APP_KEY` | string | `None` | Adzuna Developer API Key. |
| `ADZUNA_COUNTRY` | string | `in` | Two-letter country code (`in`, `us`, `gb`, `ca`, `au`). |
| `RAPIDAPI_JOB_SEARCH_KEY` | string | `None` | RapidAPI key for JSearch or Active Jobs API. |

---

## 3. Supported External Providers

### Option A: Adzuna API (Recommended for International & India Coverage)

1. Register for an API developer account at [developer.adzuna.com](https://developer.adzuna.com/).
2. Create an application to receive your **App ID** and **App Key**.
3. Add the following to your `.env` file:
   ```env
   ADZUNA_APP_ID=your_adzuna_app_id
   ADZUNA_APP_KEY=your_adzuna_app_key
   ADZUNA_COUNTRY=in
   ```
4. Adzuna endpoints provide categorized tech positions, compensation data, and direct company apply links.

### Option B: RapidAPI JSearch / Active Jobs API

1. Create an account at [rapidapi.com](https://rapidapi.com).
2. Subscribe to the **JSearch** or **Active Jobs DB** API.
3. Obtain your RapidAPI key and set in `.env`:
   ```env
   RAPIDAPI_JOB_SEARCH_KEY=your_rapidapi_key_here
   ```

---

## 4. Honest Provider Disclosure & Graceful Fallback

When no external job aggregator credentials are configured:
1. The API returns `provider_status: "CONFIGURATION_PENDING"`.
2. The response includes a clear `provider_message`:
   > *"Live external job search aggregator API (Adzuna or RapidAPI) is not configured. Displaying your saved target jobs and curated demo opportunities."*
3. The UI gracefully displays user saved jobs and demo opportunities with clear badges indicating their origin, rather than fabricating live feeds.

---

## 5. Automated Verification

Run the job provider and seed isolation test suite:
```bash
pytest backend/tests/test_job_sources_phase7.py -v
```
