# Public analytics

Cloudflare Web Analytics collects page views with the site's own beacon. The
public `/analytics/` page displays a static, aggregate-only JSON snapshot. No API
credential is sent to browsers or committed to this repository.

The `Publish blog and analytics` workflow runs on pushes, manually, and every six
hours. It reads Cloudflare using the `CF_ANALYTICS_TOKEN` repository Actions
secret (Account Analytics: Read, scoped to this account), refreshes the latest
seven UTC days, preserves older daily aggregates on the `codex/analytics-data` branch,
then builds and deploys Jekyll through GitHub Pages. The Pages publishing source
must be **GitHub Actions**. Scheduled jobs may run late; the page shows the last
successful update and flags snapshots older than 24 hours.

`analytics-config.json` contains only public account/site identifiers, hostnames,
and the date tracking started. The beacon token in `_config.yml` is a public
site identifier, not an API credential. Keep the API token in Actions secrets.

Both `xiongzile.com` and `xiongzile.me` are included in the query so that the
domain migration retains historical views when recent days are refreshed.

Only dates, paths, page-view counts, and per-day visit counts are exported.
Popular articles are matched against this site's posts and ranked by page views.

The two headline metrics answer different questions and are deliberately not
merged:

- **Page views** — every successful HTML response, reloads included. This is the
  content-interest signal.
- **Visits** — page loads whose referer does not match this hostname, i.e. an
  entry from another site or a direct link. One visit can contain several page
  views. This is the entry-traffic signal.

Neither is a unique-reader count. Cloudflare provides no visitor identity, and
no deduplication happens on this end; a reader who reloads ten times adds ten
page views and (at most) one visit. Cloudflare may sample or round values, so
treat both numbers as approximate and comparable over time. Visits are only
available from the first sync after this metric was added; earlier days keep
their page-view totals and show no visit value.

No traffic before the beacon was installed can be recovered. An API error keeps the last
successful snapshot and its timestamp instead of publishing zeros; articles
can still deploy. Check workflow warnings if updates stop. GitHub may disable scheduled workflows in public repositories after
extended inactivity; re-enable the workflow if necessary.

To rotate access, replace the `CF_ANALYTICS_TOKEN` Actions secret with a new
read-only token, run the workflow, and revoke the old token in Cloudflare.
Back up the `codex/analytics-data` branch to preserve cumulative history.
