#!/usr/bin/env python3
"""Create, edit, and publish this Jekyll blog without third-party dependencies."""

import argparse
import csv
import datetime as dt
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import unicodedata
from urllib.parse import quote, unquote, urlsplit
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent.parent


class BlogError(Exception):
    pass


def git(*args, check=True):
    result = subprocess.run(
        ["git", "-C", str(ROOT), "--literal-pathspecs", *args],
        text=True, capture_output=True,
    )
    if check and result.returncode:
        raise BlogError(result.stderr.strip() or result.stdout.strip() or "Git command failed.")
    return result


def scalar(value):
    value = value.strip()
    if value.startswith('"'):
        try:
            return json.loads(value)
        except ValueError as error:
            raise BlogError(f"Unsupported quoted metadata value: {value}") from error
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    return re.sub(r"\s+#.*$", "", value)


def metadata(path):
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---[ \t]*(?:\n|$)", text, re.S)
    if not match:
        raise BlogError(f"{path.name}: missing YAML front matter.")
    values = dict(re.findall(r"(?m)^([\w-]+):[ \t]*(.*)$", match[1]))
    if scalar(values.get("layout", "")) != "post":
        raise BlogError(f"{path.name} is not a blog post (layout: post).")
    result = {key: scalar(values.get(key, "")) for key in ("title", "date")}
    tags = values.get("tags", "[]").strip()
    if tags.startswith("[") and tags.endswith("]"):
        result["tags"] = [scalar(tag) for tag in next(csv.reader([tags[1:-1]], skipinitialspace=True))]
    elif not tags:
        block = re.search(r"(?m)^tags:[ \t]*\n((?:[ \t]+-.*\n?)*)", match[1])
        result["tags"] = re.findall(r"(?m)^[ \t]+-[ \t]+(.+)$", block[1]) if block else []
        result["tags"] = [scalar(tag) for tag in result["tags"]]
    else:
        raise BlogError(f"{path.name}: use tags: [compiler, mlir] or a YAML list.")
    return result, text[match.end():]


def slugify(value):
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def tag_pages(tags):
    pages = {}
    for tag in tags:
        if not re.fullmatch(r"[a-z0-9]+(?:[ -][a-z0-9]+)*", tag):
            raise BlogError(f"Tag {tag!r}: use lowercase English words, numbers, spaces or hyphens.")
        path = ROOT / "_topics" / (slugify(tag) + ".md")
        if path.is_symlink():
            raise BlogError(f"Tag page must not be a symlink: {path}")
        content = f'---\nlayout: tag\ntitle: {json.dumps("Tag: " + tag)}\ntag: {json.dumps(tag)}\n---\n'
        if path.exists():
            match = re.search(r"(?m)^tag:[ \t]*(.+)$", path.read_text(encoding="utf-8"))
            if not match or scalar(match[1]) != tag:
                raise BlogError(f"Tag URL collision at {path.name}; choose a different tag.")
        elif path in pages and pages[path] != content:
            raise BlogError(f"Tags share the same URL: {path.name}")
        pages[path] = content
    return pages


def write_tags(pages):
    for path, content in pages.items():
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8") as output:
                output.write(content)


def open_post(path):
    result = subprocess.run(["open", "-a", "Typora", str(path)], capture_output=True, text=True)
    if result.returncode:
        raise BlogError(f"Article saved at {path}, but Typora could not open it: {result.stderr.strip()}")


def new_post(args):
    title = args.title
    if title is None and sys.stdin.isatty():
        title = input("Post title: ").strip()
    if not title or not title.strip() or any(ord(char) < 32 for char in title):
        raise BlogError('Provide a title, for example: blog new "Understanding LLVM"')
    slug = args.slug if args.slug is not None else slugify(title)
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise BlogError('Use an English URL name: --slug my-new-post')
    path = ROOT / (slug + ".md")
    if path.exists() or path.is_symlink():
        raise BlogError(f"{path.name} already exists. Use 'blog edit {slug}' or choose another --slug.")
    if (ROOT / (slug + ".html")).exists():
        raise BlogError(f"The URL name {slug!r} is already used by a site page. Choose another --slug.")
    tags = list(dict.fromkeys(tag.strip().lower() for tag in args.tag if tag.strip()))
    pages = tag_pages(tags)
    date = args.date or dt.datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
    try:
        dt.date.fromisoformat(date)
    except ValueError as error:
        raise BlogError("Use --date YYYY-MM-DD.") from error
    images = Path("assets/images") / slug
    content = (
        f'---\nlayout: post\ntitle: {json.dumps(title.strip(), ensure_ascii=False)}\n'
        f'date: {date}\ndescription: {json.dumps(args.description, ensure_ascii=False)}\n'
        f'tags: {json.dumps(tags, ensure_ascii=False)}\n'
        f'typora-copy-images-to: {images.as_posix()}\n---\n\n## Introduction\n\n'
    )
    with path.open("x", encoding="utf-8") as output:
        output.write(content)
    (ROOT / images).mkdir(parents=True, exist_ok=True)
    write_tags(pages)
    print(f"Created: {path}\nImages:  {ROOT / images}\nPublish: blog publish {slug}")
    if not args.no_open:
        open_post(path)


def posts():
    found = []
    for path in ROOT.glob("*.md"):
        if path.is_symlink():
            continue
        header = re.match(r"\A---[ \t]*\n(.*?)\n---[ \t]*(?:\n|$)", path.read_text(encoding="utf-8"), re.S)
        layout = re.search(r"(?m)^layout:[ \t]*(.+)$", header[1]) if header else None
        if layout and scalar(layout[1]) == "post":
            info, _ = metadata(path)
            found.append((path, info))
    return sorted(found, key=lambda item: str(item[1]["date"]), reverse=True)


def list_posts(args):
    for path, info in posts():
        print(f'{info["date"]}  {path.name}  {info["title"]}')


def resolve_post(name):
    if name is None:
        changed = set(git("diff", "--name-only", "-z", "HEAD").stdout.split("\0"))
        changed.update(git("ls-files", "--others", "--exclude-standard", "-z").stdout.split("\0"))
        candidates = [path for path, _ in posts() if path.name in changed]
        if len(candidates) != 1:
            listing = ", ".join(path.name for path in candidates) or "none"
            raise BlogError(f"Specify an article: blog publish FILE. Changed articles: {listing}")
        return candidates[0]
    path = Path(name).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    if not path.suffix:
        path = path.with_suffix(".md")
    path = path.resolve()
    if path.parent != ROOT or path.suffix != ".md" or not path.is_file():
        raise BlogError("Choose an existing .md article at the blog repository root.")
    metadata(path)
    return path


class ImageHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sources = []

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            self.sources.extend(value for key, value in attrs if key == "src" and value)


def image_sources(body):
    # Examples inside code fences/inline code are not article image references.
    lines, fence = [], None
    for line in body.splitlines():
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if marker:
            run = marker[1]
            if fence is None:
                fence = run
            elif run[0] == fence[0] and len(run) >= len(fence):
                fence = None
            continue
        if fence is None:
            lines.append(line)
    body = re.sub(r"(`+).*?\1", "", "\n".join(lines))
    sources = []
    for match in re.finditer(r'!\[[^\]]*\]\(\s*(<[^>]+>|(?:\\.|[^()\\]|\((?:\\.|[^()\\])*\))*)\s*\)', body):
        value = match[1].strip()
        if value.startswith("<") and value.endswith(">"):
            value = value[1:-1]
        else:
            value = re.sub(r'''\s+(?:"[^"]*"|'[^']*'|\([^)]*\))\s*$''', "", value)
        sources.append(value)
    definitions = {key.strip().lower(): value.strip("<>") for key, value in re.findall(r"(?m)^ {0,3}\[([^\]]+)\]:\s*(<[^>]+>|\S+)", body)}
    for match in re.finditer(r"!\[([^\]]*)\](?:\[([^\]]*)\])?(?!\()", body):
        key = (match[2] or match[1]).strip().lower()
        if key in definitions:
            sources.append(definitions[key])
    parser = ImageHTMLParser()
    parser.feed(body)
    return sources + parser.sources


def local_images(post, body):
    images = set()
    for source in image_sources(body):
        source = re.sub(r"\\([\\ ()\[\]])", r"\1", source)
        url = urlsplit(source)
        if url.scheme in ("http", "https", "data") or source.startswith("//"):
            continue
        if url.scheme or (source.startswith("/") and not source.startswith("/assets/")):
            raise BlogError(f"Local-only image URL: {source}\nIn Typora, copy the article's images into assets/images/{post.stem} and enable 'Use relative path if possible'.")
        path = (ROOT / unquote(url.path).lstrip("/")).resolve()
        if not path.is_relative_to(ROOT / "assets") or not path.is_file():
            raise BlogError(f"Missing image or image outside assets/: {source}")
        images.add(path)
    return images


def site_url():
    match = re.search(r"(?m)^url:[ \t]*(.+)$", (ROOT / "_config.yml").read_text(encoding="utf-8"))
    return scalar(match[1]).rstrip("/") if match else ""


def wait_for_pages(sha, page_url, timeout):
    remote = git("remote", "get-url", "origin").stdout.strip()
    match = re.search(r"github\.com[:/]([\w.-]+/[\w.-]+?)(?:\.git)?$", remote)
    actions = f"https://github.com/{match[1]}/actions" if match else "the deployment logs"
    deadline = time.monotonic() + timeout
    last_error = "The live site still has an earlier version."
    print("Waiting for the live site to update…", flush=True)
    while time.monotonic() < deadline:
        # A fresh query also avoids cached 404s while the first deployment is running.
        marker = f"{site_url()}/assets/build-info.json?revision={sha}&t={time.time_ns()}"
        try:
            request = Request(marker, headers={"User-Agent": "xiongzile-blog-cli", "Cache-Control": "no-cache"})
            with urlopen(request, timeout=15) as response:
                info = json.loads(response.read(65536))
            if isinstance(info, dict) and info.get("commit") == sha:
                print(f"Published: {page_url}")
                return
            last_error = "The live site still has an earlier version."
        except HTTPError as error:
            last_error = str(error)
            error.close()
        except (OSError, ValueError) as error:
            last_error = str(error)
        time.sleep(min(10, max(0, deadline - time.monotonic())))
    raise BlogError(f"Push succeeded, but the live update was not confirmed. Check {actions}\n{last_error}")


def publish(args):
    post = resolve_post(args.name)
    info, body = metadata(post)
    if not info["title"] or not info["date"]:
        raise BlogError("The article needs a title and date in its front matter.")
    pages = tag_pages(info["tags"])
    paths = sorted(str(path.relative_to(ROOT)) for path in {post, *local_images(post, body), *pages})
    print("Publishing changes only from:\n" + "\n".join(f"  {path}" for path in paths))
    if args.dry_run:
        print("Dry run: no files changed, no commit or push.")
        return
    if git("branch", "--show-current").stdout.strip() != "main":
        raise BlogError("Publishing requires the main branch. Switch branches explicitly first.")
    for state in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply"):
        path = Path(git("rev-parse", "--git-path", state).stdout.strip())
        if (path if path.is_absolute() else ROOT / path).exists():
            raise BlogError("Finish the current Git merge/rebase/cherry-pick before publishing.")
    print("Checking origin/main…", flush=True)
    git("fetch", "origin", "main")
    if git("merge-base", "--is-ancestor", "origin/main", "HEAD", check=False).returncode:
        raise BlogError("The remote has changes. Update main first (git pull --rebase), then publish again.")
    ahead = git("rev-list", "origin/main..HEAD").stdout.split()
    for sha in ahead:
        committed = set(filter(None, git("diff-tree", "--root", "-m", "--no-commit-id", "--name-only", "-r", "-z", sha).stdout.split("\0")))
        if committed - set(paths):
            raise BlogError("Unpushed commits include other files. Push/review those separately before publishing this article.")
    write_tags(pages)
    git("add", "--", *paths)
    changed = git("diff", "--cached", "--quiet", "--", *paths, check=False)
    if changed.returncode not in (0, 1):
        raise BlogError(changed.stderr.strip() or "Could not inspect staged article changes.")
    if changed.returncode:
        git("commit", "--only", "-m", args.message or f"Publish {info['title']}", "--", *paths)
    elif not ahead:
        print("No article changes to publish.")
        return
    sha = git("rev-parse", "HEAD").stdout.strip()
    print(f"Pushing {sha[:7]}…", flush=True)
    git("push", "origin", "HEAD:refs/heads/main")
    url = f"{site_url()}/{quote(post.stem)}.html"
    print(f"Pushed {sha[:7]}.")
    if args.no_wait:
        print(f"GitHub Pages will deploy this commit. Article URL after deployment: {url}")
    else:
        wait_for_pages(sha, url, args.timeout)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="blog", description="Write and publish your Jekyll blog from any directory.")
    commands = parser.add_subparsers(dest="command", required=True)
    new = commands.add_parser("new", help="Create an article and open it in Typora")
    new.add_argument("title", nargs="?", help="Article title (prompted when omitted)")
    new.add_argument("--slug", help="English URL filename, e.g. llvm-notes")
    new.add_argument("-t", "--tag", action="append", default=[], help="Tag; repeat for multiple tags")
    new.add_argument("-d", "--description", default="", help="Summary shown on the homepage")
    new.add_argument("--date", help="Publication date, defaults to today in Asia/Shanghai")
    new.add_argument("--no-open", action="store_true", help="Create without opening Typora")
    new.set_defaults(action=new_post)
    edit = commands.add_parser("edit", help="Open an existing article in Typora")
    edit.add_argument("name", help="Filename or URL slug")
    edit.set_defaults(action=lambda args: open_post(resolve_post(args.name)))
    listing = commands.add_parser("list", help="List articles")
    listing.set_defaults(action=list_posts)
    pub = commands.add_parser("publish", help="Commit the article and its images, push, and wait for Pages")
    pub.add_argument("name", nargs="?", help="Filename/slug; optional if exactly one article changed")
    pub.add_argument("-m", "--message", help="Custom commit message")
    pub.add_argument("--dry-run", action="store_true", help="Show included paths without changing anything")
    pub.add_argument("--no-wait", action="store_true", help="Return after pushing without waiting for deployment")
    pub.add_argument("--timeout", type=int, default=600, help="Deployment wait limit in seconds (default: 600)")
    pub.set_defaults(action=publish)
    args = parser.parse_args(argv)
    try:
        args.action(args)
    except (BlogError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nStopped. Existing files and successful commits/pushes are preserved.", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
