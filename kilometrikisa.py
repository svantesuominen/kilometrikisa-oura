"""
Kilometrikisa.fi client for logging in and submitting cycling kilometers.

Reverse-engineered from https://github.com/jaamo/strava2kilometrikisa.
Kilometrikisa is a Django app; we handle CSRF tokens and session cookies
via requests.Session.
"""

import logging
import os
import re

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.kilometrikisa.fi"
LOGIN_URL = f"{BASE_URL}/accounts/login/"
LOG_URL = f"{BASE_URL}/contest/log/"
LOG_SAVE_URL = f"{BASE_URL}/contest/log-save/"

logger = logging.getLogger(__name__)


class KilometrikisaClient:
    def __init__(self):
        self.username = os.environ["KILOMETRIKISA_USERNAME"]
        self.password = os.environ["KILOMETRIKISA_PASSWORD"]
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "oura2kilometrikisa",
        })
        self.contest_id: str | None = None

    def login(self):
        """Log in to Kilometrikisa and establish a session."""
        logger.info("Logging in to Kilometrikisa as %s...", self.username)

        resp = self.session.get(LOGIN_URL)
        resp.raise_for_status()

        csrf_token = self.session.cookies.get("csrftoken")
        if not csrf_token:
            raise RuntimeError("Could not get CSRF token from login page")

        resp = self.session.post(
            LOGIN_URL,
            data={
                "username": self.username,
                "password": self.password,
                "csrfmiddlewaretoken": csrf_token,
            },
            headers={
                "Referer": LOGIN_URL,
            },
        )
        resp.raise_for_status()

        if "sessionid" not in self.session.cookies:
            raise RuntimeError(
                "Login failed: no session cookie received. "
                "Check username/password."
            )

        logger.info("Login successful.")

    def _get_contest_id(self) -> str:
        """Scrape the contest_id from the log page."""
        if self.contest_id:
            return self.contest_id

        logger.info("Fetching contest ID from log page...")
        resp = self.session.get(f"{LOG_URL}?calendar=km")
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Look for contest_id in hidden form fields
        hidden = soup.find("input", {"name": "contest_id"})
        if hidden and hidden.get("value"):
            self.contest_id = hidden["value"]
            logger.info("Found contest_id from form field: %s", self.contest_id)
            return self.contest_id

        # Look for contest_id in inline JavaScript
        match = re.search(r"contest_id[\"'\s:=]+(\d+)", resp.text)
        if match:
            self.contest_id = match.group(1)
            logger.info("Found contest_id from JS: %s", self.contest_id)
            return self.contest_id

        # Look for it in log_list_json URLs
        match = re.search(r"log_list_json/(\d+)/", resp.text)
        if match:
            self.contest_id = match.group(1)
            logger.info("Found contest_id from JSON URL: %s", self.contest_id)
            return self.contest_id

        raise RuntimeError(
            "Could not find contest_id on the log page. "
            "The site layout may have changed."
        )

    def submit_km(self, date_str: str, km: float):
        """
        Submit kilometers for a given date.

        Args:
            date_str: Date in YYYY-MM-DD format.
            km: Kilometers to submit (e.g. 15.3).
        """
        contest_id = self._get_contest_id()
        csrf_token = self.session.cookies.get("csrftoken")
        if not csrf_token:
            raise RuntimeError("No CSRF token available; are we logged in?")

        logger.info(
            "Submitting %.1f km for %s (contest_id=%s)...",
            km, date_str, contest_id,
        )

        resp = self.session.post(
            LOG_SAVE_URL,
            data={
                "contest_id": contest_id,
                "km_amount": km,
                "km_date": date_str,
                "is_electric": 0,
                "csrfmiddlewaretoken": csrf_token,
            },
            headers={
                "Referer": LOG_URL,
            },
        )

        if resp.status_code == 403:
            raise RuntimeError(
                "403 Forbidden: session may have expired. "
                "Re-login and try again."
            )

        resp.raise_for_status()
        logger.info("Successfully submitted %.1f km for %s.", km, date_str)
