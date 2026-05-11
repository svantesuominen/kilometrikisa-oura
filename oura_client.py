"""
Oura API v2 client for fetching cycling workout data.

Uses a Personal Access Token for authentication (no refresh needed).
Create one at https://cloud.ouraring.com/personal-access-tokens
"""

import logging
import os
from datetime import date, timedelta

import requests

WORKOUTS_URL = "https://api.ouraring.com/v2/usercollection/workout"

logger = logging.getLogger(__name__)


class OuraClient:
    def __init__(self):
        self.access_token = os.environ["OURA_ACCESS_TOKEN"]

    def get_cycling_km(self, day: date) -> float:
        """
        Fetch all cycling workouts for the given day and return total
        distance in kilometers.
        """
        day_str = day.isoformat()
        logger.info("Fetching Oura workouts for %s...", day_str)

        headers = {"Authorization": f"Bearer {self.access_token}"}
        all_workouts = []
        next_token = None

        while True:
            params: dict = {
                "start_date": day_str,
                "end_date": (day + timedelta(days=1)).isoformat(),
            }
            if next_token:
                params["next_token"] = next_token

            resp = requests.get(
                WORKOUTS_URL, headers=headers, params=params,
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
