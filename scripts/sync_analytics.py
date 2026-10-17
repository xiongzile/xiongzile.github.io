#!/usr/bin/env python3
"""Publish only daily path/count aggregates; never publish API credentials."""
import datetime as dt
import json
import math
import os
from pathlib import Path
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets/analytics.json"
CONFIG = ROOT / "analytics-config.json"
ENDPOINT = "https://api.cloudflare.com/client/v4/graphql"
BRANCH = "codex/analytics-data"


def git(*args, input=None, check=True):
    return subprocess.run(["git", *args], cwd=ROOT, input=input, text=True,
                          capture_output=True, check=check).stdout.strip()


def query(token, document):
    request = urllib.request.Request(
        ENDPOINT, json.dumps({"query": document}).encode(),
        {"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=60) as response:
        result = json.load(response)
    if result.get("errors"):
        # Errors are fatal: an API failure must never become a zero-traffic day.
        messages = "; ".join(error.get("message", "GraphQL error") for error in result["errors"])
        raise RuntimeError(messages)
    return result["data"]


def fetch_day(token, config, day, now):
    start = dt.datetime.combine(day, dt.time(), dt.timezone.utc)
    end = min(start + dt.timedelta(days=1), now)
    filters = {"siteTag": config["siteTag"], "datetime_geq": start.isoformat(),
               "datetime_lt": end.isoformat(), "requestHost": config["hostname"]}
    # JSON values also safely quote every interpolated GraphQL string.
    selector = ", ".join(f"{key}: {json.dumps(value)}" for key, value in filters.items())
    document = """{ viewer { accounts(filter: {accountTag: %s}) {
      total: rumPageloadEventsAdaptiveGroups(limit: 1, filter: {%s}) { count }
      pages: rumPageloadEventsAdaptiveGroups(limit: 10000, filter: {%s}) {
        count dimensions { requestPath }
      }
    } } }""" % (json.dumps(config["accountId"]), selector, selector)
    accounts = query(token, document)["viewer"]["accounts"]
    if len(accounts) != 1:
        raise RuntimeError("The configured analytics account is unavailable")
    result = accounts[0]
    pages = result["pages"]
    if len(pages) >= 10000:
        raise RuntimeError("Path result limit reached; refusing to publish truncated data")
    total = sum(row["count"] for row in result["total"])
    page_total = sum(row["count"] for row in pages)
    if not math.isclose(total, page_total, rel_tol=0.02, abs_tol=1):
        raise RuntimeError("Path totals differ from the independent daily total")
    aggregate = {}
    for row in pages:
        path = row["dimensions"]["requestPath"]
        # Never publish query strings, fragments, other origins, or malformed paths.
        if not isinstance(path, str) or not path.startswith("/") or path.startswith("//"):
            continue
        path = path.split("?", 1)[0].split("#", 1)[0]
        aggregate[path] = aggregate.get(path, 0) + round(row["count"])
    return {"date": day.isoformat(), "views": round(total), "pages": [
        {"path": path, "views": views} for path, views in sorted(aggregate.items())]}


def sync(token, config, previous, now):
    start = dt.date.fromisoformat(config["startedAt"])
    today = now.date()
    if start > today:
        raise ValueError("Tracking start date must not be in the future (UTC)")
    existing = {day["date"]: day for day in previous.get("days", [])}
    # Re-read the latest seven days for delayed arrivals. Preserve older snapshots
    # rather than replacing them with Cloudflare's later, more heavily sampled data.
    day = start
    while day <= today:
        if day.isoformat() not in existing or day >= today - dt.timedelta(days=6):
            existing[day.isoformat()] = fetch_day(token, config, day, now)
        day += dt.timedelta(days=1)
    return {"schemaVersion": 1, "startedAt": start.isoformat(),
            "updatedAt": now.isoformat(), "days": [existing[key] for key in sorted(existing)]}


def main():
    token = os.environ["CF_ANALYTICS_TOKEN"]
    config = json.loads(CONFIG.read_text())
    parent = None
    if os.environ.get("GITHUB_ACTIONS"):
        exists = git("ls-remote", "--heads", "origin", BRANCH)
        if exists:
            git("fetch", "--depth=1", "origin", BRANCH)
            parent = git("rev-parse", "FETCH_HEAD")
            previous = json.loads(git("show", f"{parent}:analytics.json"))
        else:
            previous = json.loads(OUTPUT.read_text())
    else:
        previous = json.loads(OUTPUT.read_text())
    # Keep the last successful snapshot available if Cloudflare is temporarily
    # unavailable, so an analytics outage does not block publishing new articles.
    OUTPUT.write_text(json.dumps(previous, ensure_ascii=False, separators=(",", ":")) + "\n")
    data = sync(token, config, previous, dt.datetime.now(dt.timezone.utc))
    serialized = json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n"
    temporary = OUTPUT.with_suffix(".tmp")
    temporary.write_text(serialized)
    temporary.replace(OUTPUT)
    if os.environ.get("GITHUB_ACTIONS"):
        git("config", "user.name", "github-actions[bot]")
        git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
        blob = git("hash-object", "-w", "--stdin", input=serialized)
        tree = git("mktree", input=f"100644 blob {blob}\tanalytics.json\n")
        args = ["commit-tree", tree]
        if parent:
            args += ["-p", parent]
        commit = git(*args, input="Update public analytics aggregates\n")
        git("push", "origin", f"{commit}:refs/heads/{BRANCH}")
    print(f"Published {len(data['days'])} daily aggregates")


if __name__ == "__main__":
    main()
