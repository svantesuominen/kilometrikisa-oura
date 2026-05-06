"""
Main sync script: fetches cycling km from Oura and submits to Kilometrikisa.

Intended to run daily via GitHub Actions. Syncs yesterday's data by default.
"""

import argparse
import logging
import sys
from datetime import date, timedelta

from kilometrikisa import KilometrikisaClient
from oura_client import OuraClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Sync cycling km from Oura to Kilometrikisa",
    )
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        default=date.today() - timedelta(days=1),
        help="Date to sync (YYYY-MM-DD). Defaults to yesterday.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch from Oura but don't submit to Kilometrikisa.",
    )
    args = parser.parse_args()

    target_date: date = args.date
    logger.info("Syncing cycling data for %s", target_date.isoformat())

    oura = OuraClient()
    km = oura.get_cycling_km(target_date)

    if km <= 0:
        logger.info("No cycling distance recorded for %s. Nothing to submit.", target_date)
        return

    if args.dry_run:
        logger.info("[DRY RUN] Would submit %.1f km for %s", km, target_date)
        return

    kisa = KilometrikisaClient()
    kisa.login()
    kisa.submit_km(target_date.isoformat(), km)

    logger.info("Done! Submitted %.1f km for %s.", km, target_date)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("Sync failed")
        sys.exit(1)
