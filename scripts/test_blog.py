import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import blog


class BlogCLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "blog"
        self.root.mkdir()
        self.root = self.root.resolve()
        self.remote = Path(self.temp.name) / "origin.git"
        subprocess.run(["git", "init", "--bare", "--initial-branch=main", str(self.remote)], check=True, capture_output=True)
        self.git("init", "--initial-branch=main")
        for key, value in {
            "user.name": "Blog CLI Test", "user.email": "test@example.com",
            "commit.gpgsign": "false", "core.hooksPath": "/dev/null",
        }.items():
            self.git("config", key, value)
        (self.root / "_config.yml").write_text("url: https://example.com\n")
        (self.root / "unrelated.txt").write_text("original\n")
        self.git("add", ".")
        self.git("commit", "-m", "Initial site")
        self.git("remote", "add", "origin", str(self.remote))
        self.git("push", "-u", "origin", "main")
        self.root_patch = patch.object(blog, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True, text=True).stdout

    def cli(self, *args):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            result = blog.main(list(args))
        return result, output.getvalue(), errors.getvalue()

    def new(self, *args):
        code, _, error = self.cli("new", "Compiler Notes", "--no-open", *args)
        self.assertEqual(code, 0, error)
        return self.root / "compiler-notes.md"

    def test_new_handles_quoted_title_tags_images_and_typora(self):
        with patch.object(blog, "open_post") as opener:
            code, _, errors = self.cli("new", 'LLVM: "Hello"', "--tag", "compiler", "--tag", "build system")
        self.assertEqual(code, 0, errors)
        article = self.root / "llvm-hello.md"
        info, _ = blog.metadata(article)
        self.assertEqual(info["title"], 'LLVM: "Hello"')
        self.assertEqual(info["tags"], ["compiler", "build system"])
        self.assertIn("typora-copy-images-to: assets/images/llvm-hello", article.read_text())
        self.assertTrue((self.root / "assets/images/llvm-hello").is_dir())
        self.assertIn('tag: "build system"', (self.root / "_topics/build-system.md").read_text())
        opener.assert_called_once_with(article)

    def test_duplicate_article_and_invalid_date_never_overwrite(self):
        article = self.new()
        before = article.read_text()
        code, _, _ = self.cli("new", "Compiler Notes", "--no-open")
        self.assertEqual(code, 1)
        self.assertEqual(article.read_text(), before)
        code, _, _ = self.cli("new", "Other Notes", "--no-open", "--date", "2026-13-01")
        self.assertEqual(code, 1)
        self.assertFalse((self.root / "other-notes.md").exists())

    def test_tag_collision_is_rejected_before_creating_article(self):
        self.new("--tag", "build system")
        code, _, errors = self.cli("new", "Other Notes", "--tag", "build-system", "--no-open")
        self.assertEqual(code, 1)
        self.assertIn("collision", errors)
        self.assertFalse((self.root / "other-notes.md").exists())

    def test_list_ignores_readme_examples_and_lists_real_articles(self):
        self.new()
        (self.root / "README.md").write_text("# Example\n```yaml\n---\nlayout: post\n---\n```\n")
        code, output, errors = self.cli("list")
        self.assertEqual(code, 0, errors)
        self.assertIn("compiler-notes.md", output)
        self.assertNotIn("README", output)

    def test_publish_includes_images_and_tags_preserves_unrelated_index(self):
        article = self.new("--tag", "compiler")
        image = self.root / "assets/images/compiler-notes/diagram (1).png"
        image.write_bytes(b"test image")
        article.write_text(article.read_text() + '\n![Diagram](assets/images/compiler-notes/diagram%20%281%29.png "caption")\n')
        # This unused screenshot must not accidentally be published.
        (image.parent / "unused.png").write_bytes(b"unused image")
        unrelated = self.root / "unrelated.txt"
        unrelated.write_text("staged change\n")
        self.git("add", "unrelated.txt")
        unrelated.write_text("working change\n")
        code, output, errors = self.cli("publish", "--no-wait")
        self.assertEqual(code, 0, errors)
        self.assertIn("Pushed", output)
        changed = set(self.git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines())
        self.assertEqual(changed, {"compiler-notes.md", "_topics/compiler.md", "assets/images/compiler-notes/diagram (1).png"})
        self.assertEqual(self.git("show", ":unrelated.txt"), "staged change\n")
        self.assertEqual(unrelated.read_text(), "working change\n")
        self.assertEqual(self.git("show", "origin/main:unrelated.txt"), "original\n")
        self.assertEqual(self.git("rev-parse", "HEAD"), self.git("rev-parse", "origin/main"))

    def test_local_only_or_missing_images_abort_without_commit(self):
        article = self.new()
        base, head = article.read_text(), self.git("rev-parse", "HEAD")
        for image in ["/Users/me/private.png", "file:///tmp/private.png", "assets/missing.png", "../private.png"]:
            article.write_text(base + f"\n![image]({image})\n")
            code, _, _ = self.cli("publish", "compiler-notes", "--no-wait")
            self.assertEqual(code, 1, image)
            self.assertEqual(self.git("rev-parse", "HEAD"), head)
            self.assertEqual(self.git("diff", "--cached", "--name-only"), "")

    def test_dry_run_does_not_create_missing_tags_or_touch_index(self):
        article = self.new()
        article.write_text(article.read_text().replace("tags: []", 'tags: ["new topic"]'))
        before = self.git("status", "--porcelain", "--untracked-files=all")
        code, output, errors = self.cli("publish", "compiler-notes", "--dry-run")
        self.assertEqual(code, 0, errors)
        self.assertIn("_topics/new-topic.md", output)
        self.assertEqual(self.git("status", "--porcelain", "--untracked-files=all"), before)
        self.assertFalse((self.root / "_topics/new-topic.md").exists())

    def test_publish_refuses_unrelated_unpushed_commits(self):
        self.new()
        (self.root / "unrelated.txt").write_text("unpublished\n")
        self.git("add", "unrelated.txt")
        self.git("commit", "-m", "Unrelated local change")
        head = self.git("rev-parse", "HEAD")
        code, _, error = self.cli("publish", "compiler-notes", "--no-wait")
        self.assertEqual(code, 1)
        self.assertIn("Unpushed commits", error)
        self.assertEqual(self.git("rev-parse", "HEAD"), head)

    def test_publish_requires_main_and_does_not_rebase_a_behind_checkout(self):
        self.new()
        self.git("checkout", "-b", "draft")
        code, _, errors = self.cli("publish", "compiler-notes", "--no-wait")
        self.assertEqual(code, 1)
        self.assertIn("main branch", errors)
        self.git("checkout", "main")
        other = Path(self.temp.name) / "other-checkout"
        subprocess.run(["git", "clone", str(self.remote), str(other)], check=True, capture_output=True)
        (other / "remote.txt").write_text("Remote change\n")
        for args in [
            ["add", "remote.txt"],
            ["-c", "user.name=Test", "-c", "user.email=test@example.com", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", "commit", "-m", "Remote change"],
            ["push", "origin", "main"],
        ]:
            subprocess.run(["git", "-C", str(other), *args], check=True, capture_output=True)
        before = self.git("rev-parse", "HEAD")
        code, _, errors = self.cli("publish", "compiler-notes", "--no-wait")
        self.assertEqual(code, 1)
        self.assertIn("remote has changes", errors)
        self.assertEqual(before, self.git("rev-parse", "HEAD"))
        self.assertTrue((self.root / "compiler-notes.md").exists())

    def test_publish_can_retry_its_own_unpushed_article_commit(self):
        self.new()
        original_git = blog.git

        def failed_push(*args, **kwargs):
            if args[0] == "push":
                raise blog.BlogError("Test push failure")
            return original_git(*args, **kwargs)

        with patch.object(blog, "git", side_effect=failed_push):
            code, _, error = self.cli("publish", "compiler-notes", "--no-wait")
        self.assertEqual(code, 1)
        self.assertIn("Test push failure", error)
        head = self.git("rev-parse", "HEAD")
        code, _, error = self.cli("publish", "compiler-notes", "--no-wait")
        self.assertEqual(code, 0, error)
        self.assertEqual(head, self.git("rev-parse", "HEAD"))
        self.assertEqual(head, self.git("rev-parse", "origin/main"))

    def test_image_parser_handles_references_html_and_code_examples(self):
        body = '''
![a](<assets/my screenshot (1).png>)
![b][diagram]
[diagram]: assets/ref.png
<img src="/assets/html.png" alt="Diagram">
![remote](https://example.com/image.png)
`![inline example](/Users/example.png)`
```markdown
![code example](/Users/example.png)
```
'''
        self.assertEqual(set(blog.image_sources(body)), {
            "assets/my screenshot (1).png", "assets/ref.png", "/assets/html.png", "https://example.com/image.png",
        })

    def test_wait_reports_failed_deployment_after_push(self):
        run = {"path": ".github/workflows/pages.yml", "status": "completed", "conclusion": "failure", "html_url": "https://github.com/owner/repo/actions/runs/1"}
        response = io.StringIO(json.dumps({"workflow_runs": [run]}))
        with patch.object(blog, "git", return_value=subprocess.CompletedProcess([], 0, "git@github.com:owner/repo.git\n", "")), patch.object(blog, "urlopen", return_value=response), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(blog.BlogError, "Push succeeded, but deployment failure"):
                blog.wait_for_pages("abc", "https://example.com/post.html", 60)


if __name__ == "__main__":
    unittest.main()
