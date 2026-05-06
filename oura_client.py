"""
Oura API v2 client for fetching cycling workout data.

Handles OAuth2 token refresh and automatic rotation of the refresh token
stored in GitHub Actions secrets.
"""

import logging
import os
import subprocess
from datetime import date

import requests

TOKEN_URL = "https://api.ouraring.com/oauth/token"
WORKOUTS_URL = "https://api.ouraring.com/v2/usercollection/workout"

logger = logging.getLogger(__name__)


class OuraClient:
    def __init__(self):
        self.client_id = os.environ["OURA_CLIENT_ID"]
        self.client_secret = os.environ["OURA_CLIENT_SECRET"]
        self.refresh_token = os.environ["OURA_REFRESH_TOKEN"]
        self.access_token: str | None = None

    def _refresh_access_token(self):
        """Exchange the refresh token for a new access + refresh token pair."""
        logger.info("Refreshing Oura access token...")
        resp = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
        )
        resp.raise_for_status()
        tokens = resp.json()

        self.access_token = tokens["access_token"]
        new_refresh_token = tokens["refresh_token"]

        if new_refresh_token != self.refresh_token:
            self.refresh_token = new_refresh_token
            try:
                self._rotate_github_secret(new_refresh_token)
            except RuntimeError:
                logger.warning(
                    "Could not rotate refresh token in GitHub Secrets. "
                    "Update OURA_REFRESH_TOKEN manually if the next run fails."
                )

    def _rotate_github_secret(self, new_token: str):
        """Update OURA_REFRESH_TOKEN in GitHub Actions secrets."""
        repo = os.environ.get("GH_REPO")
        gh_token = os.environ.get("GH_TOKEN")
        if not repo or not gh_token:
            logger.warning(
                "GH_REPO or GH_TOKEN not set; skipping refresh token rotation. "
                "The next run may fail if Oura invalidated the old token."
            )
            return

        logger.info("Rotating OURA_REFRESH_TOKEN in GitHub secrets...")
        result = subprocess.run(
            [
                "gh", "secret", "set", "OURA_REFRESH_TOKEN",
                "--body", new_token,
                "--repo", repo,
            ],
            capture_output=True,
            text=True,
            env={**os.environ, "GH_TOKEN": gh_token},
        )
        if result.returncode != 0:
            logger.error("Failed to rotate secret: %s", result.stderr)
            raise RuntimeError(f"gh secret set failed: {result.stderr}")
        logger.info("Refresh token rotated successfully.")

    def _get_headers(self) -> dict:
        if not self.access_token:
            self._refresh_access_token()
        return {"Authorization": f"Bearer {self.access_token}"}

    def get_cycling_km(self, day: date) -> float:
        """
        Fetch all cycling workouts for the given day and return total
        distance in kilometers.
        """
        day_str = day.isoformat()
        logger.info("Fetching Oura workouts for %s...", day_str)

        all_workouts = []
        next_token = None

        while True:
            params: dict = {
                "start_date": day_str,
                "end_date": day_str,
            }
            if next_token:
                params["next_token"] = next_token

            resp = requests.get(
                WORKOUTS_URL,
                headers=self._get_headers(),
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

            all_workouts.extend(data.get("data", []))
            next_token = data.get("next_token")
            if not next_token:
                break

        cycling = [
            w for w in all_workouts
            if w.get("activity", "").lower() == "cycling"
        ]

        logger.info(
            "Found %d total workouts, %d cycling",
            len(all_workouts), len(cycling),
        )

        total_meters = 0.0
        for w in cycling:
            distance = w.get("distance")
            if distance is not None:
                total_meters += distance
                logger.info(
                    "  Cycling workout %s: %.0f m",
                    w.get("id", "?"), distance,
                )
            else:
                logger.warning(
                    "  Cycling workout %s has no distance data",
                    w.get("id", "?"),
                )

        km = round(total_meters / 1000, 1)
        logger.info("Total cycling distance for %s: %.1f km", day_str, km)
        return km
