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

### 1. Create an Oura API application

1. Go to [cloud.ouraring.com/oauth/applications](https://cloud.ouraring.com/oauth/applications)
2. Create a new application
3. Set the redirect URI to `http://localhost:8080/callback`
4. Note the **Client ID** and **Client Secret**

### 2. Bootstrap Oura tokens

Run the auth setup script locally (requires Python 3.10+):

```bash
pip install requests
python auth_setup.py
```

This opens your browser, authorizes the app, and prints the tokens. Copy the **refresh token**.

### 3. Create a GitHub repository

Push this code to a GitHub repo (can be private).

### 4. Configure GitHub Secrets

Go to your repo → Settings → Secrets and variables → Actions, and add:

| Secret | Value |
|--------|-------|
| `OURA_CLIENT_ID` | From step 1 |
| `OURA_CLIENT_SECRET` | From step 1 |
| `OURA_REFRESH_TOKEN` | From step 2 |
| `KILOMETRIKISA_USERNAME` | Your Kilometrikisa email/username |
| `KILOMETRIKISA_PASSWORD` | Your Kilometrikisa password |
| `GH_PAT` | A GitHub Personal Access Token (see below) |

**Creating the `GH_PAT`** (needed for automatic refresh token rotation):
1. Go to [github.com/settings/tokens](https://github.com/settings/tokens)
2. Generate a **fine-grained token** scoped to this repo with **Secrets: Read and write** permission, or a classic token with `repo` scope
3. Store it as the `GH_PAT` secret

### 5. Done!

The workflow runs daily at 03:00 Helsinki time. You can also trigger it manually from the Actions tab.

## Local development

Create a `.env` file (already in `.gitignore`):

```
OURA_CLIENT_ID=...
OURA_CLIENT_SECRET=...
OURA_REFRESH_TOKEN=...
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

**Important:** Each run consumes the Oura refresh token (they are single-use). After local testing, re-run `python auth_setup.py` and update both your `.env` and the `OURA_REFRESH_TOKEN` GitHub secret so the scheduled run doesn't break.

## Refresh token rotation

Oura's OAuth2 issues a new refresh token each time you use the old one. When running on GitHub Actions, the script automatically updates the `OURA_REFRESH_TOKEN` secret via the `gh` CLI (pre-installed on runners). This requires a `GH_PAT` with write access to secrets.

If rotation fails (e.g., wrong PAT permissions), the sync still completes but logs a warning with the new token. You can then update the secret manually, or re-run `auth_setup.py`.

## Notes

- The Oura Ring estimates cycling distance from motion data. For more accurate distances, manually enter them in the Oura app. Workouts with no distance data are skipped with a warning.
- Kilometrikisa doesn't have a public API. This project reverse-engineers the same form endpoints as the web UI (based on [strava2kilometrikisa](https://github.com/jaamo/strava2kilometrikisa)). If the site changes its structure, the submission may need updating.
- The `contest_id` is scraped automatically from the log page JavaScript each run.
