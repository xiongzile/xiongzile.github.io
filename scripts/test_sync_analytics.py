import datetime as dt
import unittest
from unittest.mock import patch
import sync_analytics as analytics


class SnapshotTests(unittest.TestCase):
    config = {"startedAt": "2026-10-01", "accountId": "account", "siteTag": "site", "hostnames": ["example.com", "example.me"]}
    now = dt.datetime(2026, 10, 18, 12, tzinfo=dt.timezone.utc)

    def test_refresh_recent_days_preserves_archive_and_fills_gaps(self):
        previous = {"days": [{"date": f"2026-10-{day:02d}", "views": 9, "pages": []} for day in range(1, 18) if day != 5]}
        def fresh(token, config, day, now):
            return {"date": day.isoformat(), "views": 2, "visits": 1, "pages": []}
        with patch.object(analytics, "fetch_day", side_effect=fresh) as fetch:
            result = analytics.sync("unused", self.config, previous, self.now)
        self.assertEqual(len(result["days"]), 18)
        self.assertEqual(fetch.call_count, 8)
        self.assertEqual(result["days"][0]["views"], 9)
        self.assertEqual(result["days"][4]["views"], 2)
        self.assertEqual(result["days"][-1]["views"], 2)

    def add_empty_breakdowns(self, answer):
        for key in analytics.BREAKDOWNS:
            answer["viewer"]["accounts"][0][key] = []
        return answer

    def test_no_data_is_a_valid_zero_and_paths_are_sanitized(self):
        answer = {"viewer": {"accounts": [{"total": [{"count": 3, "sum": {"visits": 2}}], "pages": [
            {"count": 2, "dimensions": {"requestPath": "/post.html?private=1"}},
            {"count": 1, "dimensions": {"requestPath": "/post.html#fragment"}}]}]}}
        self.add_empty_breakdowns(answer)
        with patch.object(analytics, "query", return_value=answer) as query:
            day = analytics.fetch_day("unused", self.config, self.now.date(), self.now)
        self.assertIn('requestHost_in: ["example.com", "example.me"]', query.call_args.args[1])
        self.assertEqual(day["pages"], [{"path": "/post.html", "views": 3}])
        self.assertEqual(day["visits"], 2)
        answer["viewer"]["accounts"][0] = {"total": [], "pages": []}
        self.add_empty_breakdowns(answer)
        with patch.object(analytics, "query", return_value=answer):
            self.assertEqual(analytics.fetch_day("unused", self.config, self.now.date(), self.now)["views"], 0)

    def test_truncated_or_failed_refresh_never_publishes_false_zero(self):
        answer = {"viewer": {"accounts": [{"total": [{"count": 50, "sum": {"visits": 10}}], "pages": []}]}}
        with patch.object(analytics, "query", return_value=answer):
            with self.assertRaises(RuntimeError):
                analytics.fetch_day("unused", self.config, self.now.date(), self.now)
        with patch.object(analytics, "fetch_day", side_effect=RuntimeError("API unavailable")):
            with self.assertRaises(RuntimeError):
                analytics.sync("unused", self.config, {"days": []}, self.now)


    def test_visits_cannot_exceed_page_views(self):
        answer = {"viewer": {"accounts": [{"total": [{"count": 10, "sum": {"visits": 40}}], "pages": [
            {"count": 10, "dimensions": {"requestPath": "/post.html"}}]}]}}
        with patch.object(analytics, "query", return_value=answer):
            with self.assertRaises(RuntimeError):
                analytics.fetch_day("unused", self.config, self.now.date(), self.now)

    def test_breakdowns_publish_only_independent_safe_categories(self):
        result = {key: [] for key in analytics.BREAKDOWNS}
        result["referrers"] = [
            {"count": 8, "sum": {"visits": 2}, "dimensions": {"refererHost": "github.com"}},
            {"count": 5, "sum": {"visits": 1}, "dimensions": {"refererHost": ""}},
            {"count": 1, "sum": {"visits": 1}, "dimensions": {"refererHost": "192.0.2.1"}},
            {"count": 1, "sum": {"visits": 1}, "dimensions": {"refererHost": "https://private.example/a?key=secret"}},
        ]
        result["countries"] = [{"count": 8, "dimensions": {"countryName": "US"}}]
        output = analytics.breakdowns(result, self.config)
        self.assertEqual(output["countries"], [{"name": "US", "views": 8}])
        sources = {row["name"]: row["visits"] for row in output["referrers"]}
        self.assertEqual(sources, {"github.com": 2, "Other": 2, "Direct / unknown": 1})
        import json
        serialized = json.dumps(output)
        self.assertNotIn("192.0.2.1", serialized)
        self.assertNotIn("secret", serialized)
        self.assertNotIn("refererHost", serialized)

    def test_missing_or_truncated_breakdowns_fail_instead_of_publishing_empty_data(self):
        with self.assertRaises(KeyError):
            analytics.breakdowns({}, self.config)
        result = {key: [] for key in analytics.BREAKDOWNS}
        result["browsers"] = [{}] * 10000
        with self.assertRaises(RuntimeError):
            analytics.breakdowns(result, self.config)

    def test_legacy_days_are_not_given_invented_breakdowns(self):
        previous = {"days": [{"date": "2026-10-01", "views": 9, "pages": []}]}
        with patch.object(analytics, "fetch_day", side_effect=lambda token, config, day, now:
                          {"date": day.isoformat(), "views": 0, "pages": [], "breakdowns": {}}):
            data = analytics.sync("unused", self.config, previous, self.now)
        self.assertNotIn("breakdowns", data["days"][0])
        self.assertEqual(data["schemaVersion"], 3)


if __name__ == "__main__":
    unittest.main()
