import contextlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fetch_suggestions


def response_fixture(query, suggestions):
    response = MagicMock()
    response.status = 200
    response.read.return_value = json.dumps([query, suggestions]).encode("utf-8")
    response.__enter__.return_value = response
    return response


class SuggestionTests(unittest.TestCase):
    def test_query_and_locale_are_encoded_as_hints(self):
        url = fetch_suggestions.build_url("发票 & invoice", "zh-CN", "cn")
        parameters = parse_qs(urlparse(url).query)
        self.assertEqual(parameters["q"], ["发票 & invoice"])
        self.assertEqual(parameters["hl"], ["zh-CN"])
        self.assertEqual(parameters["gl"], ["cn"])

    def test_deduplication_keeps_original_positions_and_sources(self):
        fixtures = [
            response_fixture("invoice", [" Invoice free ", "invoice free", "invoice app"]),
            response_fixture("invoice app", ["INVOICE FREE"]),
        ]
        with patch.object(fetch_suggestions, "urlopen", side_effect=fixtures) as opener:
            with patch.object(fetch_suggestions.time, "sleep") as sleeper:
                report = fetch_suggestions.collect(["invoice", "invoice app"], "en", "us")
        self.assertEqual(opener.call_count, 2)
        sleeper.assert_called_once_with(1)
        self.assertEqual(len(report["keywords"]), 2)
        self.assertEqual(report["keywords"][0]["keyword"], "Invoice free")
        self.assertEqual([signal["position"] for signal in report["keywords"][0]["signals"]], [1, 1])
        self.assertEqual(report["keywords"][1]["signals"][0]["position"], 3)
        self.assertEqual(report["responses"][0]["suggestions"][0], " Invoice free ")
        self.assertFalse(report["scope"]["location_verified"])
        self.assertEqual(report["metric_kind"], "autocomplete_suggestion")

    def test_blocking_stops_remaining_requests_and_preserves_success(self):
        for status in (403, 429):
            with self.subTest(status=status):
                fixtures = [response_fixture("first", ["first app"]), HTTPError("url", status, "blocked", {}, None)]
                with patch.object(fetch_suggestions, "urlopen", side_effect=fixtures) as opener:
                    with patch.object(fetch_suggestions.time, "sleep"):
                        report = fetch_suggestions.collect(["first", "second", "third"], "en", "us")
                self.assertEqual(opener.call_count, 2)
                self.assertEqual([row["status"] for row in report["responses"]], ["ok", "blocked", "skipped"])
                self.assertIsNone(report["responses"][2]["observed_at"])
                self.assertEqual(report["keywords"][0]["keyword"], "first app")

    def test_empty_response_is_not_a_numeric_zero(self):
        with patch.object(fetch_suggestions, "urlopen", return_value=response_fixture("seed", [])):
            report = fetch_suggestions.collect(["seed"], "en", "us")
        self.assertEqual(report["responses"][0]["status"], "empty")
        self.assertEqual(report["keywords"], [])
        self.assertNotIn("search_volume", report)

    def test_bad_schema_and_query_mismatch_are_rejected(self):
        for payload in ({"error": "bad"}, ["other", ["word"]], ["seed", [10]], ["seed"]):
            with self.subTest(payload=payload):
                response = response_fixture("seed", [])
                response.read.return_value = json.dumps(payload).encode()
                with patch.object(fetch_suggestions, "urlopen", return_value=response):
                    result = fetch_suggestions.fetch_query("seed", "en", "us", 20)
                self.assertEqual(result["status"], "error")
                self.assertEqual(result["suggestions"], [])

    def test_invalid_json_and_oversized_responses_are_errors(self):
        for raw_response in (b"<html>challenge</html>", b" " * (fetch_suggestions.MAX_RESPONSE_BYTES + 1)):
            with self.subTest(size=len(raw_response)):
                response = response_fixture("seed", [])
                response.read.return_value = raw_response
                with patch.object(fetch_suggestions, "urlopen", return_value=response):
                    result = fetch_suggestions.fetch_query("seed", "en", "us", 20)
                self.assertEqual(result["status"], "error")

    def test_transport_error_is_preserved(self):
        with patch.object(fetch_suggestions, "urlopen", side_effect=URLError("offline")):
            result = fetch_suggestions.fetch_query("seed", "en", "us", 20)
        self.assertEqual(result["status"], "error")
        self.assertIn("offline", result["error"])
        self.assertIsNone(result["http_status"])

    def test_arguments_deduplicate_explicit_queries(self):
        args = fetch_suggestions.parse_arguments(["--query", " seed ", "--query", "seed", "--country", "JP"])
        self.assertEqual(args.query, ["seed"])
        self.assertEqual(args.country, "jp")

    def test_invalid_arguments_are_rejected_without_requests(self):
        cases = [
            ["--query", " "],
            ["--query", "seed", "--delay", "0"],
            ["--query", "seed", "--delay", "nan"],
            ["--query", "seed", "--timeout", "inf"],
            ["--query", "seed", "--country", "USA"],
            ["--query", "seed", "--language", "english"],
            [argument for index in range(11) for argument in ("--query", f"seed{index}")],
        ]
        for arguments in cases:
            with self.subTest(arguments=arguments), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    fetch_suggestions.parse_arguments(arguments)

    def test_cli_emits_partial_json_and_nonzero_exit_on_failure(self):
        output = io.StringIO()
        with patch.object(fetch_suggestions, "urlopen", side_effect=URLError("offline")):
            with contextlib.redirect_stdout(output):
                exit_code = fetch_suggestions.main(["--query", "seed"])
        self.assertEqual(exit_code, 1)
        self.assertEqual(json.loads(output.getvalue())["responses"][0]["status"], "error")


if __name__ == "__main__":
    unittest.main()
