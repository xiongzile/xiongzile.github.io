# Zile Xiong's blog

Markdown 文章通过 Jekyll 生成，兼容 GitHub Pages 的默认构建方式。视觉参考 [MaskRay](https://maskray.me/) 使用的 tabi 阅读布局；主题模板和样式保存在本仓库中。

## 本地预览

```sh
bundle install
bundle exec jekyll serve --host 127.0.0.1
```

打开 http://127.0.0.1:4000。执行 `bundle exec jekyll build` 生成 `_site/`。

## 写文章

在根目录添加 Markdown 文件，使用以下 front matter；首页、归档、标签和 RSS 会自动收录。

```yaml
---
layout: post
title: 文章标题
date: 2026-10-17
description: 一段用于首页和 RSS 的摘要。
tags: [compiler]
wip: true
---
```

正文从二级标题开始，文章标题由模板显示。现有文章仍使用 `/mlir-toy-compiler.html` 和 `/2026-summary.html`。
