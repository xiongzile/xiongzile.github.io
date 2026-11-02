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

The public snapshot contains daily totals, paths, and independent distributions
for countries, referring hostnames, devices, browsers, and operating systems.
Referrers count visits; the other distributions count page views. Referrer paths,
queries, credentials, literal IP addresses, and private hostnames such as `.local`
are not exported. Dimensions are never joined into individual visitor records.
Popular articles are matched against this site's posts and ranked by page views.
All tables and headline totals follow the selected 7-day, 30-day, or all-time range.
The secondary all-time/today figures remain explicitly labeled.

Schema version 3 adds audience breakdowns. The seven-day refresh fills recent
breakdowns; older snapshots are preserved without inventing missing data. The
dashboard states which dates have breakdowns and calculates each distribution's
percentages using its own available data. An empty API result is a measured zero;
an absent dimension or query error preserves the previous complete snapshot.

## Exclude your browser

Open `https://xiongzile.me/analytics/#exclude-self` in each browser you use, or
press **Ignore my visits** on the dashboard. The site saves only an exclusion
preference (`blog.analytics.excluded`) in localStorage. It does not identify
visitors. The local loader checks this preference before requesting Cloudflare's
beacon, including on the first visit through the opt-out link. Local previews
never load the beacon. Do not enable a second, automatically injected beacon in
Cloudflare, as that would bypass this loader.

The preference survives IP/VPN changes but applies only to that browser profile
and origin. Repeat it in another browser/device or after clearing site storage.
Reload other open blog tabs to unload their existing beacons. This excludes
future Web Analytics events, not Cloudflare's edge HTTP/security logs; it does
not remove past visits. The dashboard reports storage failures rather than
claiming a persistent exclusion. **Include my visits again** reverses it.

## Metrics

The two headline metrics answer different questions and are deliberately not
merged:

- **Page views** — page loads reported by the browser beacon, reloads included. This is the
  content-interest signal.
- **Visits** — page loads whose referer does not match this hostname, i.e. an
  entry from another site or a direct link. One visit can contain several page
  views. This is the entry-traffic signal.

Neither is a unique-reader count. Cloudflare provides no visitor identity, and
no deduplication happens on this end. Repeat loads can add page views, and visit
counts depend on the reported referrer rather than a persistent visitor identity.
Cloudflare may sample or round values, so
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
