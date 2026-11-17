"""Collect the historical PPS GDP index for 2000–2025 without changing data."""

import sys

import requests

from collect_gdp_pps import main


if __name__ == "__main__":
    try:
        main(dataset_id="prc_ppp_ind_1", end_year=2025)
    except (requests.RequestException, ValueError, KeyError, OSError) as exc:
        print(f"Collection failed: {exc}", file=sys.stderr)
        sys.exit(1)
