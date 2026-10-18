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
            return {"date": day.isoformat(), "views": 2, "pages": []}
        with patch.object(analytics, "fetch_day", side_effect=fresh) as fetch:
            result = analytics.sync("unused", self.config, previous, self.now)
        self.assertEqual(len(result["days"]), 18)
        self.assertEqual(fetch.call_count, 8)
        self.assertEqual(result["days"][0]["views"], 9)
        self.assertEqual(result["days"][4]["views"], 2)
        self.assertEqual(result["days"][-1]["views"], 2)

    def test_no_data_is_a_valid_zero_and_paths_are_sanitized(self):
        answer = {"viewer": {"accounts": [{"total": [{"count": 3}], "pages": [
            {"count": 2, "dimensions": {"requestPath": "/post.html?private=1"}},
            {"count": 1, "dimensions": {"requestPath": "/post.html#fragment"}}]}]}}
        with patch.object(analytics, "query", return_value=answer) as query:
            day = analytics.fetch_day("unused", self.config, self.now.date(), self.now)
        self.assertIn('requestHost_in: ["example.com", "example.me"]', query.call_args.args[1])
        self.assertEqual(day["pages"], [{"path": "/post.html", "views": 3}])
        answer["viewer"]["accounts"][0] = {"total": [], "pages": []}
        with patch.object(analytics, "query", return_value=answer):
            self.assertEqual(analytics.fetch_day("unused", self.config, self.now.date(), self.now)["views"], 0)

    def test_truncated_or_failed_refresh_never_publishes_false_zero(self):
        answer = {"viewer": {"accounts": [{"total": [{"count": 50}], "pages": []}]}}
        with patch.object(analytics, "query", return_value=answer):
            with self.assertRaises(RuntimeError):
                analytics.fetch_day("unused", self.config, self.now.date(), self.now)
        with patch.object(analytics, "fetch_day", side_effect=RuntimeError("API unavailable")):
            with self.assertRaises(RuntimeError):
                analytics.sync("unused", self.config, {"days": []}, self.now)


if __name__ == "__main__":
    unittest.main()
