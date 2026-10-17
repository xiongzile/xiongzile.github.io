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

`analytics-config.json` contains only public account/site identifiers, hostname,
and the date tracking started. The beacon token in `_config.yml` is a public
site identifier, not an API credential. Keep the API token in Actions secrets.

Only dates, paths, and page-view counts are exported. Popular articles are
matched against this site's posts. Counts include repeat page loads; they do
not represent unique people and Cloudflare may sample them. No traffic before
the beacon was installed can be recovered. An API error keeps the last
successful snapshot and its timestamp instead of publishing zeros; articles
can still deploy. Check workflow warnings if updates stop. GitHub may disable scheduled workflows in public repositories after
extended inactivity; re-enable the workflow if necessary.

To rotate access, replace the `CF_ANALYTICS_TOKEN` Actions secret with a new
read-only token, run the workflow, and revoke the old token in Cloudflare.
Back up the `codex/analytics-data` branch to preserve cumulative history.
