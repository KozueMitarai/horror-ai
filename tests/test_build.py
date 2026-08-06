#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for build.py. Standard library only:

    python3 -m unittest discover -s tests
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import build  # noqa: E402


class ParseMarkdownTest(unittest.TestCase):
    def test_parses_frontmatter_and_body(self):
        frontmatter, body = build.parse_markdown(
            '---\n'
            'title: "隙間の視線"\n'
            'date: "2026-07-17"\n'
            'synopsis: "壁の隙間からの視線。"\n'
            'tags: [都市伝説, 心理的恐怖]\n'
            '---\n'
            '\n'
            '本文です。\n'
        )
        self.assertEqual(frontmatter["title"], "隙間の視線")
        self.assertEqual(frontmatter["date"], "2026-07-17")
        self.assertEqual(frontmatter["synopsis"], "壁の隙間からの視線。")
        self.assertEqual(frontmatter["tags"], ["都市伝説", "心理的恐怖"])
        self.assertEqual(body, "本文です。")

    def test_body_separators_are_not_mistaken_for_frontmatter(self):
        _, body = build.parse_markdown(
            '---\ntitle: "A"\n---\n\n一段落目。\n\n---\n\n二段落目。\n'
        )
        self.assertEqual(body, "一段落目。\n\n---\n\n二段落目。")

    def test_missing_frontmatter_falls_back_to_defaults(self):
        frontmatter, body = build.parse_markdown("本文だけ。", fallback_date="2026-07-20")
        self.assertEqual(frontmatter["title"], "無題の怪談")
        self.assertEqual(frontmatter["date"], "2026-07-20")
        self.assertEqual(frontmatter["tags"], [])
        self.assertEqual(body, "本文だけ。")

    def test_crlf_input(self):
        frontmatter, body = build.parse_markdown('---\r\ntitle: "A"\r\n---\r\n\r\n本文。\r\n')
        self.assertEqual(frontmatter["title"], "A")
        self.assertEqual(body, "本文。")


class MarkdownToHtmlTest(unittest.TestCase):
    def test_horizontal_rule_is_a_scene_break_not_a_list(self):
        for rule in ("---", "***", "___"):
            with self.subTest(rule=rule):
                self.assertEqual(build.markdown_to_html(rule), "<hr>")

    def test_bullet_list(self):
        self.assertEqual(
            build.markdown_to_html("- 一つ目\n- 二つ目"),
            "<ul><li>一つ目</li><li>二つ目</li></ul>",
        )

    def test_dash_led_prose_is_a_paragraph(self):
        # A line starting with a dash but no space is prose, not a list item
        self.assertEqual(build.markdown_to_html("-そして誰もいなくなった"), "<p>-そして誰もいなくなった</p>")

    def test_html_special_characters_are_escaped(self):
        self.assertEqual(
            build.markdown_to_html('<script>alert("x")</script> & <b>'),
            '<p>&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt; &amp; &lt;b&gt;</p>',
        )

    def test_inline_emphasis_and_links(self):
        self.assertEqual(build.markdown_to_html("**強調**と*斜体*"), "<p><strong>強調</strong>と<em>斜体</em></p>")
        self.assertEqual(
            build.markdown_to_html("[リンク](https://example.com)"),
            '<p><a href="https://example.com">リンク</a></p>',
        )

    def test_single_newlines_become_br(self):
        self.assertEqual(build.markdown_to_html("一行目\n二行目"), "<p>一行目<br>二行目</p>")

    def test_blockquote_keeps_inline_markup(self):
        self.assertEqual(
            build.markdown_to_html("> **録音開始**"),
            "<blockquote><p><strong>録音開始</strong></p></blockquote>",
        )

    def test_heading_offset(self):
        self.assertEqual(build.markdown_to_html("# 見出し"), "<h1>見出し</h1>")
        self.assertEqual(build.markdown_to_html("# 見出し", heading_offset=2), "<h3>見出し</h3>")
        # Never goes past h6
        self.assertEqual(build.markdown_to_html("##### 見出し", heading_offset=2), "<h6>見出し</h6>")


class StripDuplicateTitleTest(unittest.TestCase):
    def test_removes_leading_heading_matching_the_title(self):
        self.assertEqual(build.strip_duplicate_title("# 話す番\n\n本文。", "話す番"), "本文。")

    def test_keeps_a_different_heading(self):
        self.assertEqual(build.strip_duplicate_title("# 第一章\n\n本文。", "話す番"), "# 第一章\n\n本文。")

    def test_keeps_body_without_heading(self):
        self.assertEqual(build.strip_duplicate_title("本文。", "話す番"), "本文。")


class RenderTagsTest(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(build.render_tags([]), "")

    def test_escapes_tags(self):
        self.assertEqual(
            build.render_tags(["民俗ホラー", "a<b"]),
            '<div class="tags"><span class="tag">#民俗ホラー</span>'
            '<span class="tag">#a&lt;b</span></div>',
        )


class PageRenderingTest(unittest.TestCase):
    def test_story_page_escapes_metadata(self):
        frontmatter = {
            "title": '「引用符」 & <危険>',
            "date": "2026-07-17",
            "synopsis": 'あらすじ "引用符" 付き',
            "tags": [],
        }
        page = build.build_story_page(frontmatter, "本文。")
        self.assertNotIn("<危険>", page)
        self.assertIn("&lt;危険&gt;", page)
        # The description meta attribute must not be broken by a quote
        self.assertIn('<meta name="description" content="あらすじ &quot;引用符&quot; 付き">', page)

    def test_story_page_drops_duplicate_title_heading(self):
        frontmatter = {"title": "話す番", "date": "2026-07-27", "synopsis": "s", "tags": []}
        page = build.build_story_page(frontmatter, "# 話す番\n\n本文。")
        # Only the site header <h1> remains
        self.assertEqual(page.count("<h1>"), 1)

    def test_index_page_lists_stories(self):
        page = build.build_index_page([
            {"title": "話す番", "date": "2026-07-27", "synopsis": "s", "tags": ["学校"],
             "filename": "2026-07-27.html"},
        ])
        self.assertIn('<a href="stories/2026-07-27.html" class="story-link">', page)
        self.assertIn("<h2>話す番</h2>", page)


if __name__ == "__main__":
    unittest.main()
