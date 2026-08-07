#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for process_feedback.py's knowledge base editing. Standard library only:

    python3 -m unittest discover -s tests
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import process_feedback as pf  # noqa: E402


def entry(n):
    return f"### 【フィードバック分析: 作品{n} (Issue #{n})】\n- **良かった点**:\n  - 点{n}"


def knowledge_with(entries, trailing_section=""):
    body = "".join(f"{e}\n\n" for e in entries)
    return (
        "# ナレッジベース\n\n"
        "## 6. 足枷の類型\n\n"
        "本文。\n\n"
        f"{pf.FEEDBACK_SECTION_HEADER}\n\n"
        f"{pf.FEEDBACK_SECTION_INTRO}\n\n"
        f"{body}"
        f"{trailing_section}"
    )


class SplitFeedbackSectionTest(unittest.TestCase):
    def test_splits_at_the_next_level_two_heading(self):
        content = knowledge_with([entry(1)], trailing_section="## 8. あとがき\n\n末尾。\n")
        before, section, after = pf.split_feedback_section(content)
        self.assertTrue(before.startswith("# ナレッジベース"))
        self.assertIn(entry(1), section)
        self.assertNotIn("## 8.", section)
        self.assertTrue(after.startswith("## 8. あとがき"))

    def test_level_three_entries_do_not_end_the_section(self):
        content = knowledge_with([entry(1), entry(2)])
        _, section, after = pf.split_feedback_section(content)
        self.assertIn(entry(2), section)
        self.assertEqual(after, "")

    def test_returns_none_when_absent(self):
        self.assertIsNone(pf.split_feedback_section("# 見出しだけ\n"))


class AddFeedbackEntryTest(unittest.TestCase):
    def test_appends_into_the_section_not_the_end_of_file(self):
        content = knowledge_with([entry(1)], trailing_section="## 8. あとがき\n\n末尾。\n")
        updated, overflow = pf.add_feedback_entry(content, entry(2))
        self.assertEqual(overflow, [])
        # The new entry lands before the following section, not after it
        self.assertLess(updated.index(entry(2)), updated.index("## 8. あとがき"))
        self.assertTrue(updated.rstrip().endswith("末尾。"))

    def test_keeps_only_the_most_recent_entries(self):
        content = knowledge_with([entry(n) for n in range(1, 6)])
        updated, overflow = pf.add_feedback_entry(content, entry(6))

        self.assertEqual(len(overflow), 1)
        self.assertIn("Issue #1", overflow[0])
        self.assertNotIn(entry(1), updated)
        for n in range(2, 7):
            self.assertIn(entry(n), updated)

    def test_under_the_cap_nothing_is_archived(self):
        content = knowledge_with([entry(1), entry(2)])
        updated, overflow = pf.add_feedback_entry(content, entry(3))
        self.assertEqual(overflow, [])
        self.assertIn(entry(1), updated)

    def test_preamble_is_preserved(self):
        content = knowledge_with([entry(1)])
        updated, _ = pf.add_feedback_entry(content, entry(2))
        self.assertIn(pf.FEEDBACK_SECTION_INTRO, updated)
        self.assertEqual(updated.count(pf.FEEDBACK_SECTION_HEADER), 1)

    def test_creates_the_section_when_missing(self):
        updated, overflow = pf.add_feedback_entry("# ナレッジベース\n", entry(1))
        self.assertEqual(overflow, [])
        self.assertIn(pf.FEEDBACK_SECTION_HEADER, updated)
        self.assertIn(entry(1), updated)

    def test_entries_keep_their_order(self):
        content = knowledge_with([entry(1), entry(2)])
        updated, _ = pf.add_feedback_entry(content, entry(3))
        self.assertLess(updated.index(entry(1)), updated.index(entry(2)))
        self.assertLess(updated.index(entry(2)), updated.index(entry(3)))

    def test_repeated_additions_stay_at_the_cap(self):
        content = knowledge_with([entry(n) for n in range(1, 6)])
        for n in range(6, 12):
            content, _ = pf.add_feedback_entry(content, entry(n))
        _, entries = pf.split_entries(pf.split_feedback_section(content)[1])
        self.assertEqual(len(entries), pf.MAX_FEEDBACK_ENTRIES)
        self.assertIn("Issue #11", entries[-1])


class ArchiveEntriesTest(unittest.TestCase):
    def test_appends_to_the_archive(self):
        archive = pf.archive_entries("# アーカイブ\n\n既存の内容。\n", [entry(1)])
        self.assertTrue(archive.startswith("# アーカイブ"))
        self.assertIn("既存の内容。", archive)
        self.assertTrue(archive.rstrip().endswith("点1"))

    def test_no_entries_leaves_the_archive_untouched(self):
        self.assertEqual(pf.archive_entries("# アーカイブ\n", []), "# アーカイブ\n")


class RoundTripTest(unittest.TestCase):
    """The real knowledge base must survive an update unchanged apart from the entry."""

    def test_against_the_real_knowledge_base(self):
        with open(pf.KNOWLEDGE_PATH, encoding="utf-8") as f:
            original = f.read()

        updated, overflow = pf.add_feedback_entry(original, entry(99))

        # The title and intro above the feedback section are left intact
        self.assertIn("# ホラー小説 読者フィードバック", updated)
        self.assertIn(entry(99), updated)

        _, entries = pf.split_entries(pf.split_feedback_section(updated)[1])
        self.assertLessEqual(len(entries), pf.MAX_FEEDBACK_ENTRIES)
        self.assertEqual(entries[-1], entry(99))
        # The knowledge base already holds the maximum, so exactly one rolls off
        self.assertEqual(len(overflow), 1)


if __name__ == "__main__":
    unittest.main()
