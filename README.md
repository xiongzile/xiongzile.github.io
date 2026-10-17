# Zile Xiong's blog

An English-language blog built with Jekyll and compatible with GitHub Pages' default build process.

The site uses the stylesheets, fonts, theme controls, and HTML structure served by [MaskRay's blog](https://maskray.me/blog/), with Jekyll templates supplying this site's content. See [THEME.md](THEME.md) for sources, checksums, and the small adaptations needed for Jekyll.

## Local preview

```sh
bundle install
bundle exec jekyll serve --host 127.0.0.1
```

Open http://127.0.0.1:4000. Run `bundle exec jekyll build` to generate `_site/`.

## Writing a post

Add a Markdown file at the repository root with the following front matter. The home page, archives, tag counts, and Atom feed will include it automatically.

```yaml
---
layout: post
title: Post title
date: 2026-10-17
description: A short summary for the home page and Atom feed.
tags: [compiler]
wip: true
---
```

Start the body with second-level headings; the template displays the post title and generates its table of contents. Prefix the title with `[WIP]` for an unfinished post.

For a new tag, add a matching file under `_topics/` using one of the existing files as a template. Jekyll generates its page at `/tags/<tag>/`.

The existing post URLs remain `/mlir-toy-compiler.html` and `/2026-summary.html`.
