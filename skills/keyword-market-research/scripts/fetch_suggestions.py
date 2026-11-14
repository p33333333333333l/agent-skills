import argparse
import json
import math
import re
import sys
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


ENDPOINT = "https://suggestqueries.google.com/complete/search"
MAX_QUERIES = 10
MAX_RESPONSE_BYTES = 128_000


def observed_at():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def build_url(query, language, country):
    parameters = {"client": "firefox", "q": query, "hl": language, "gl": country}
    return f"{ENDPOINT}?{urlencode(parameters)}"


def parse_suggestions(raw_response, query):
    payload = json.loads(raw_response.decode("utf-8"))
    if (
        not isinstance(payload, list)
        or len(payload) < 2
        or payload[0] != query
        or not isinstance(payload[1], list)
        or any(not isinstance(value, str) for value in payload[1])
    ):
        raise ValueError("Unexpected suggestion response schema or echoed query")
    return payload[1]


def fetch_query(query, language, country, timeout):
    url = build_url(query, language, country)
    result = {
        "query": query,
        "source_url": url,
        "observed_at": observed_at(),
        "status": "error",
        "http_status": None,
        "suggestions": [],
    }
    try:
        with urlopen(url, timeout=timeout) as response:
            result["http_status"] = response.status
            raw_response = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw_response) > MAX_RESPONSE_BYTES:
            raise ValueError("Suggestion response exceeds the size limit")
        if result["http_status"] != 200:
            raise ValueError("Unexpected HTTP status")
        result["suggestions"] = parse_suggestions(raw_response, query)
        result["status"] = "ok" if result["suggestions"] else "empty"
    except HTTPError as error:
        result["http_status"] = error.code
        result["status"] = "blocked" if error.code in {403, 429} else "error"
        result["error"] = f"HTTP {error.code}"
    except (URLError, OSError, ValueError) as error:
        result["error"] = f"{type(error).__name__}: {error}"
    return result


def collect(queries, language, country, timeout=20, delay=1):
    responses = []
    keywords = {}
    blocked = False
    for query in queries:
        if blocked:
            responses.append(
                {
                    "query": query,
                    "source_url": build_url(query, language, country),
                    "observed_at": None,
                    "status": "skipped",
                    "http_status": None,
                    "suggestions": [],
                    "error": "Source blocked an earlier request; no request made",
                }
            )
            continue
        if responses:
            time.sleep(delay)
        response = fetch_query(query, language, country, timeout)
        responses.append(response)
        blocked = response["status"] == "blocked"
        seen_in_query = set()
        for position, suggestion in enumerate(response["suggestions"], start=1):
            keyword = suggestion.strip()
            key = keyword.casefold()
            if not keyword or key in seen_in_query:
                continue
            seen_in_query.add(key)
            record = keywords.setdefault(key, {"keyword": keyword, "signals": []})
            record["signals"].append(
                {
                    "query": query,
                    "position": position,
                    "source_url": response["source_url"],
                    "observed_at": response["observed_at"],
                }
            )
    return {
        "schema_version": 1,
        "source": "Google autocomplete",
        "endpoint_kind": "undocumented_public_endpoint",
        "metric_kind": "autocomplete_suggestion",
        "scope": {
            "language_hint": language,
            "country_hint": country,
            "location_verified": False,
        },
        "generated_at": observed_at(),
        "limitations": [
            "Suggestions and their order do not measure search volume, CPC, or KD",
            "Country and language parameters are hints, not verified search location",
            "Empty, blocked, or failed responses do not establish zero demand",
            "The endpoint has no verified official service contract",
        ],
        "responses": responses,
        "keywords": list(keywords.values()),
    }


def parse_arguments(arguments=None):
    parser = argparse.ArgumentParser(
        description="Collect small samples of public autocomplete suggestions, not volume"
    )
    parser.add_argument("--query", action="append", required=True)
    parser.add_argument("--language", default="en")
    parser.add_argument("--country", default="us")
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument("--delay", type=float, default=1)
    args = parser.parse_args(arguments)
    queries = list(dict.fromkeys(query.strip() for query in args.query))
    if any(not query or len(query) > 300 for query in queries):
        parser.error("Each query must contain between 1 and 300 characters")
    if len(queries) > MAX_QUERIES:
        parser.error(f"At most {MAX_QUERIES} distinct queries are allowed")
    if not re.fullmatch(r"[A-Za-z]{2,3}(?:-[A-Za-z]{2,8})?", args.language):
        parser.error("Language must be a language code such as en or zh-CN")
    if not re.fullmatch(r"[A-Za-z]{2}", args.country):
        parser.error("Country must be a two-letter country code such as us or cn")
    if not math.isfinite(args.timeout) or not 0 < args.timeout <= 60:
        parser.error("Timeout must be finite and between 0 and 60 seconds")
    if not math.isfinite(args.delay) or args.delay < 1:
        parser.error("Delay must be finite and at least one second")
    args.query = queries
    args.country = args.country.lower()
    return args


def main(arguments=None):
    args = parse_arguments(arguments)
    report = collect(args.query, args.language, args.country, args.timeout, args.delay)
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return int(any(response["status"] not in {"ok", "empty"} for response in report["responses"]))


if __name__ == "__main__":
    raise SystemExit(main())
