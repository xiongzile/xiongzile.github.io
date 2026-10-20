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

The `blog` CLI creates articles, configures Typora's image folder, generates tag
pages, and publishes only the selected article and its referenced images. It
requires Python 3.9+, Git, and Typora on macOS; no Python packages are needed.

Install it once from this repository (do not overwrite an existing `blog` command):

```sh
mkdir -p ~/.local/bin
ln -s "$PWD/scripts/blog.py" ~/.local/bin/blog
```

Ensure `~/.local/bin` is on your `PATH`. You can then run these from any directory:

```sh
blog new "Understanding LLVM" --tag compiler
blog new "Build Cache Notes" --tag "build system" --description "Notes on cache correctness."
blog list
blog edit understanding-llvm
blog publish understanding-llvm --dry-run
blog publish understanding-llvm
```

`blog new` without a title prompts for one. Use `--slug english-url-name` to
choose the filename, repeat `--tag` for multiple tags, and use `--no-open` to
skip Typora. The date uses Asia/Shanghai. New articles remain local until
published. Paste images after saving/opening the article; if Typora asks,
allow copying images to the document's configured folder.

`blog publish` can omit the filename when exactly one article has changed. It
checks that local images exist under `assets/`, commits the article, referenced
images and matching tag pages, pushes `main`, and waits until the live site's
revision marker matches the pushed commit. No GitHub API token is needed.
Unrelated staged and working changes are preserved. If
the remote has new commits or local unpushed commits touch other files, it
stops instead of rebasing or publishing them. Use `--no-wait` to return after
the push; this does not confirm deployment. If a push fails, retry with the
same article filename to publish the already-created commit.

For a local-only image path such as `/Users/...`, use Typora's **Format → Image →
Copy All Images to…**, choose the article's `assets/images/<slug>/` folder, and
publish again. External image URLs are kept as external URLs.

### Manual creation

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

For a new tag, add a matching file under `_topics/` using one of the existing files as a template. Use a hyphenated filename for tags with spaces: `build system` uses `_topics/build-system.md` and generates `/tags/build-system/`.

The existing post URLs remain `/mlir-toy-compiler.html` and `/2026-summary.html`.
