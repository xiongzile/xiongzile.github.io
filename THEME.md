# Theme provenance

The visual reference is the live [MaskRay blog](https://maskray.me/blog/), retrieved on 17 October 2026. This site uses the actual assets served by that site, rather than a separately designed approximation.

## Unmodified assets

`assets/maskray/` contains byte-for-byte copies of:

- `main.css`, the compiled tabi theme.
- `css/maskray.css`, MaskRay's wider layout, scrolling tables, and side table of contents.
- `inter_subset_en.css`, including its embedded font subset.
- `giallo.css` and `no_js.css`.
- The Inter, Source Serif 4, and Cascadia Code fonts.
- The theme initialization, theme switcher, and code-copy scripts.
- The RSS and GitHub social icons.

The exact source URLs and SHA-256 checksums are recorded in `assets/maskray/sources.json`. Keep these files unchanged when adjusting content or templates. The tabi MIT license, icon license, and font licenses are included beside the corresponding assets.

## Jekyll integration

The Liquid layouts follow the live site's HTML classes and structure for the navigation, post list, article metadata, table of contents, archives, tags, adjacent-post navigation, and footer. Jekyll supplies this site's posts, dates, tag counts, and links. Existing article URLs are preserved.

`assets/rouge.css` maps Jekyll's syntax token classes to the same GitHub Dark colors in the original `giallo.css`. `assets/code-markup.js` adds the language attributes expected by tabi. These are renderer adaptations; there are no custom layout, font, spacing, or color overrides.

The active table-of-contents script follows MaskRay's live implementation. The footer identifies Jekyll as the generator because that is what this repository uses.

The navigation omits Presentations and TIL as requested. MaskRay's personal social accounts, analytics, comment repository, and visitor statistics are not reused. The About page remains available at `/about.html`.

The Analytics navigation item is a site-specific addition. Its public dashboard
uses this site's own Cloudflare Web Analytics data and a separate stylesheet;
the reference theme assets remain unchanged. See `ANALYTICS.md` for operation.
