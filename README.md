# Oura → Kilometrikisa Sync

Automatically submits your daily cycling kilometers from [Oura Ring](https://ouraring.com) to [Kilometrikisa](https://www.kilometrikisa.fi) via GitHub Actions.

Runs daily at 03:00 Helsinki time, syncing the previous day's cycling workouts.

## How it works

1. Fetches cycling workouts from the Oura API v2 (`/v2/usercollection/workout`)
2. Filters for `activity == "cycling"` (both auto-detected and manually tagged)
3. Sums the `distance` field (meters → km, rounded to 1 decimal)
4. Logs into Kilometrikisa with session cookies and CSRF tokens
5. POSTs the km total to `/contest/log-save/` for the target date

## Setup

### 1. Create an Oura Personal Access Token

1. Go to [cloud.ouraring.com/personal-access-tokens](https://cloud.ouraring.com/personal-access-tokens)
2. Create a new token
3. Copy it — you'll need it in step 3

### 2. Push this repo to GitHub

```bash
git remote add origin https://github.com/YOUR_USER/kilometrikisa-oura.git
git push -u origin master
```

### 3. Configure GitHub Secrets

Go to your repo → Settings → Secrets and variables → Actions, and add:

| Secret | Value |
|--------|-------|
| `OURA_ACCESS_TOKEN` | Personal Access Token from step 1 |
| `KILOMETRIKISA_USERNAME` | Your Kilometrikisa email/username |
| `KILOMETRIKISA_PASSWORD` | Your Kilometrikisa password |

### 4. Done!

The workflow runs daily at 03:00 Helsinki time. You can also trigger it manually from the Actions tab.

## Local development

Create a `.env` file (already in `.gitignore`):

```
OURA_ACCESS_TOKEN=...
KILOMETRIKISA_USERNAME=...
KILOMETRIKISA_PASSWORD=...
```

Then:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Dry run (fetches from Oura but doesn't submit)
python sync.py --dry-run

# Sync a specific date
python sync.py --date 2026-05-05

# Sync yesterday (default)
python sync.py
```

## Notes

- The Oura Ring estimates cycling distance from motion data. For more accurate distances, manually enter them in the Oura app. Workouts with no distance data are skipped with a warning.
- Kilometrikisa doesn't have a public API. This project reverse-engineers the same form endpoints as the web UI (based on [strava2kilometrikisa](https://github.com/jaamo/strava2kilometrikisa)). If the site changes its structure, the submission may need updating.
- The `contest_id` is scraped automatically from the log page JavaScript each run.
