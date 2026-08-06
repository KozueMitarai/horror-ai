#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Consistency checks over the actual stories in `stories/`.

These guard the authoring conventions documented in prompt.md, so a malformed
story is caught in CI instead of silently producing a broken page.

    python3 -m unittest discover -s tests
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import build  # noqa: E402

STORY_FILENAME_RE = re.compile(r'^\d{4}-\d{2}-\d{2}(-[a-z0-9]+)?\.md$')
# Markdown that build.py does not render: tables, code fences, images
UNSUPPORTED_RE = re.compile(r'(?m)^\s*(\||```|!\[)')


def story_files():
    return sorted(f for f in os.listdir(build.STORIES_DIR) if f.endswith(".md"))


def load(filename):
    with open(os.path.join(build.STORIES_DIR, filename), encoding="utf-8") as f:
        return f.read()


class StoryConventionsTest(unittest.TestCase):
    def test_there_are_stories_to_check(self):
        self.assertGreater(len(story_files()), 0)

    def test_filenames_follow_the_convention(self):
        for filename in story_files():
            with self.subTest(filename=filename):
                self.assertRegex(filename, STORY_FILENAME_RE)

    def test_frontmatter_is_complete(self):
        for filename in story_files():
            with self.subTest(filename=filename):
                content = load(filename)
                self.assertTrue(content.lstrip().startswith("---"), "フロントマターがありません")
                frontmatter, body = build.parse_markdown(content)
                self.assertNotEqual(frontmatter["title"], "無題の怪談", "title が未設定です")
                self.assertNotEqual(frontmatter["synopsis"], "解説はありません。", "synopsis が未設定です")
                self.assertTrue(frontmatter["tags"], "tags が空です")
                self.assertTrue(body.strip(), "本文が空です")

    def test_frontmatter_date_matches_the_filename(self):
        for filename in story_files():
            with self.subTest(filename=filename):
                frontmatter, _ = build.parse_markdown(load(filename))
                self.assertEqual(
                    frontmatter["date"],
                    filename[:10],
                    "ファイル名の日付とフロントマターの date が一致していません",
                )

    def test_synopsis_does_not_contain_a_line_break(self):
        # The synopsis goes into a <meta> attribute and an index card
        for filename in story_files():
            with self.subTest(filename=filename):
                frontmatter, _ = build.parse_markdown(load(filename))
                self.assertNotIn("\n", frontmatter["synopsis"])

    def test_no_unsupported_markdown(self):
        for filename in story_files():
            with self.subTest(filename=filename):
                _, body = build.parse_markdown(load(filename))
                match = UNSUPPORTED_RE.search(body)
                self.assertIsNone(
                    match,
                    f"build.py が描画できない記法が含まれています: {match.group(0) if match else ''}",
                )

    def test_every_story_renders_without_error(self):
        for filename in story_files():
            with self.subTest(filename=filename):
                frontmatter, body = build.parse_markdown(load(filename))
                page = build.build_story_page(frontmatter, body)
                self.assertIn("<article", page)
                # The site header is the only <h1> on the page
                self.assertEqual(page.count("<h1>"), 1)


class StoryOutputPathTest(unittest.TestCase):
    def test_output_filenames_are_unique(self):
        outputs = [f[:-len(".md")] + ".html" for f in story_files()]
        self.assertEqual(len(outputs), len(set(outputs)))


if __name__ == "__main__":
    unittest.main()
