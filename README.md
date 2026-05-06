# Oura → Kilometrikisa Sync

Automatically submits your daily cycling kilometers from [Oura Ring](https://ouraring.com) to [Kilometrikisa](https://www.kilometrikisa.fi) via GitHub Actions.

Runs daily at 03:00 Helsinki time, syncing the previous day's cycling workouts.

## How it works

1. Fetches cycling workouts from the Oura API v2 (`/v2/usercollection/workout`)
2. Filters for `activity == "cycling"` (both auto-detected and manually tagged)
3. Sums the `distance` field (meters → km)
4. Logs into Kilometrikisa and POSTs the km to `/contest/log-save/`

## Setup

### 1. Create an Oura API application

1. Go to [cloud.ouraring.com/oauth/applications](https://cloud.ouraring.com/oauth/applications)
2. Create a new application
3. Set the redirect URI to `http://localhost:8080/callback`
4. Note the **Client ID** and **Client Secret**

### 2. Bootstrap Oura tokens

Run the auth setup script locally (requires Python 3.10+ and `requests`):

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
| `GH_PAT` | A GitHub Personal Access Token with `repo` scope (for refresh token rotation) |

To create the `GH_PAT`:
1. Go to [github.com/settings/tokens](https://github.com/settings/tokens)
2. Generate a new token (classic) with `repo` scope
3. Store it as the `GH_PAT` secret

### 5. Done!

The workflow runs daily at 03:00 Helsinki time. You can also trigger it manually from the Actions tab.

## Local testing

```bash
pip install -r requirements.txt

# Set env vars
export OURA_CLIENT_ID=...
export OURA_CLIENT_SECRET=...
export OURA_REFRESH_TOKEN=...
export KILOMETRIKISA_USERNAME=...
export KILOMETRIKISA_PASSWORD=...

# Dry run (fetches from Oura but doesn't submit)
python sync.py --dry-run

# Sync a specific date
python sync.py --date 2026-05-05

# Sync yesterday (default)
python sync.py
```

## Refresh token rotation

Oura's OAuth2 issues a new refresh token each time you use the old one. The script automatically updates the `OURA_REFRESH_TOKEN` GitHub secret after each refresh using the `gh` CLI (pre-installed on GitHub Actions runners). This requires a `GH_PAT` with `repo` scope.

If the token chain breaks (e.g., the action fails mid-rotation), re-run `auth_setup.py` locally and update the `OURA_REFRESH_TOKEN` secret manually.

## Notes

- The Oura Ring doesn't have GPS, so cycling distance is estimated from motion data or manually entered in the Oura app. If distance is missing for a workout, it's skipped with a warning.
- Kilometrikisa doesn't have a public API; this uses the same form endpoints as the web UI. If the site changes its structure, the submission may need updating.
- The `contest_id` is scraped automatically from the log page each run.
