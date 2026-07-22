#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Horror Writer Project - Feedback Processor
This script is triggered by GitHub Actions when an issue is opened.
It sends the issue body to the Gemini API to analyze feedback (strengths, weaknesses, improvements)
and appends the analysis results to `knowledge/horror.md`.
"""

import os
import json
import time
import urllib.request
import urllib.error

# Define paths
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_PATH = os.path.join(ROOT_DIR, "knowledge", "horror.md")

# Gemini API occasionally returns transient errors (503 Service Unavailable
# when the model is overloaded, 429 rate limiting, 500/502/504). Retry these
# with exponential backoff instead of failing the whole workflow immediately.
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRIES = 5
INITIAL_BACKOFF_SECONDS = 5


def call_gemini_api(request_factory):
    """Send a Gemini API request, retrying on transient (5xx/429) errors."""
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        req = request_factory()
        try:
            with urllib.request.urlopen(req, timeout=60) as res:
                return json.loads(res.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8")
            last_error = e
            if e.code in RETRYABLE_STATUS_CODES and attempt < MAX_RETRIES:
                wait = INITIAL_BACKOFF_SECONDS * (2 ** (attempt - 1))
                print(
                    f"HTTP Error: {e.code} - {body} "
                    f"(attempt {attempt}/{MAX_RETRIES}, retrying in {wait}s)"
                )
                time.sleep(wait)
                continue
            print(f"HTTP Error: {e.code} - {body}")
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            last_error = e
            if attempt < MAX_RETRIES:
                wait = INITIAL_BACKOFF_SECONDS * (2 ** (attempt - 1))
                print(
                    f"Network error calling Gemini API: {e} "
                    f"(attempt {attempt}/{MAX_RETRIES}, retrying in {wait}s)"
                )
                time.sleep(wait)
                continue
            print(f"Network error calling Gemini API: {e}")
            raise
    raise last_error


def main():
    print("Starting feedback processing script...")
    
    # 1. Read GitHub event payload
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if event_path and os.path.exists(event_path):
        print(f"Reading event payload from {event_path}")
        with open(event_path, "r", encoding="utf-8") as f:
            event_data = json.load(f)
    else:
        # Local mock fallback for testing
        mock_path = os.path.join(ROOT_DIR, "mock_event.json")
        if os.path.exists(mock_path):
            print(f"Reading mock event payload from {mock_path}")
            with open(mock_path, "r", encoding="utf-8") as f:
                event_data = json.load(f)
        else:
            print("No event payload found. Using default mock data.")
            event_data = {
                "issue": {
                    "title": "感想: 隙間の視線 (2026-07-17)",
                    "body": "非常に怖かったです！特に隙間が少しずつ広がって、最後に手や指が伸びてくる描写がリアルでゾッとしました。ただ、主人公の自業自得感があまりなかったので、なぜ彼がその不気味なアパートを選んだのかなどの背景描写が少しあると、より感情移入しやすかったかもしれません。",
                    "number": 1
                }
            }

    issue = event_data.get("issue", {})
    issue_title = issue.get("title", "不明なタイトル")
    issue_body = issue.get("body", "")
    issue_number = issue.get("number", 0)

    if not issue_body:
        print("Error: Issue body is empty. Nothing to analyze.")
        return

    # 2. Retrieve GEMINI_API_KEY
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        exit(1)

    # 3. Call Gemini API
    # Designing the prompt to extract strengths, weaknesses, and improvements
    prompt = f"""あなたは優秀なホラー小説のアナリストです。
以下のホラー小説に対する読者からのフィードバック（Issue）を分析し、今後の創作の参考にするための改善用データを整理してください。
以下の3点を必ず客観的に抽出・整理してください。

1. 良かった点 (読者が恐怖を感じた部分、効果的な演出など)
2. 悪かった点 (没入感が削がれた部分、改善の余地がある描写、物足りない点など)
3. 改善案 (次回以降の執筆に活かせる具体的な執筆アドバイス)

フィードバック本文:
---
{issue_body}
---

出力フォーマット（Markdown）:
必ず以下のフォーマットで出力してください。挨拶文、前置き、まとめ、解説などは一切含めず、このMarkdown構造のみを出力してください。

### 【フィードバック分析: {issue_title} (Issue #{issue_number})】
- **良かった点**:
  - 
- **悪かった点**:
  - 
- **改善案**:
  - 
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={api_key}"
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }

    def build_request():
        return urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )

    print("Calling Gemini API...")
    try:
        response_data = call_gemini_api(build_request)
        analysis_text = response_data["candidates"][0]["content"]["parts"][0]["text"].strip()
        print("Successfully received analysis from Gemini API.")
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        exit(1)

    # 4. Read and update knowledge/horror.md
    if not os.path.exists(KNOWLEDGE_PATH):
        print(f"Knowledge file {KNOWLEDGE_PATH} not found. Creating a new one.")
        os.makedirs(os.path.dirname(KNOWLEDGE_PATH), exist_ok=True)
        with open(KNOWLEDGE_PATH, "w", encoding="utf-8") as f:
            f.write("# ホラー小説執筆ナレッジベース (Horror Writing Knowledge Base)\n\n")

    with open(KNOWLEDGE_PATH, "r", encoding="utf-8") as f:
        knowledge_content = f.read()

    # Section header to separate reader feedback insights
    section_header = "## 5. 読者フィードバックからの知見"
    
    if section_header not in knowledge_content:
        print("Adding section header for reader feedback insights.")
        if not knowledge_content.endswith("\n\n"):
            if knowledge_content.endswith("\n"):
                knowledge_content += "\n"
            else:
                knowledge_content += "\n\n"
        knowledge_content += f"{section_header}\n\n"
        knowledge_content += "ここでは、読者から寄せられたフィードバック（GitHub Issues）を分析し、執筆ナレッジの向上に役立てるための履歴を蓄積します。\n\n"

    # Append the analysis text
    if not knowledge_content.endswith("\n\n"):
        if knowledge_content.endswith("\n"):
            knowledge_content += "\n"
        else:
            knowledge_content += "\n\n"
            
    knowledge_content += f"{analysis_text}\n"

    # Write the updated content back to the file
    with open(KNOWLEDGE_PATH, "w", encoding="utf-8") as f:
        f.write(knowledge_content)

    print(f"Successfully updated knowledge base file: {KNOWLEDGE_PATH}")

    # 5. Call Gemini API again to extract recurring failure patterns
    # from the accumulated feedback, so they can be promoted to a
    # dedicated "priority issues" section at the top of the knowledge base.
    pattern_prompt = f"""あなたは優秀なホラー小説のアナリストです。
以下は、これまでに読者から寄せられたフィードバックを分析した記録を蓄積した、ホラー小説執筆ナレッジベースの全文です。

この中の「5. 読者フィードバックからの知見」に蓄積された複数のフィードバック分析を横断的に確認し、2回以上繰り返し指摘されている問題パターンがあれば、簡潔な原則として3〜5個程度、箇条書きで要約してください。
1回しか出ていない指摘は含めないでください。繰り返し指摘されている問題が見つからない場合は、その旨を1行で述べてください。

ナレッジベース全文:
---
{knowledge_content}
---

出力フォーマット（Markdown）:
必ず箇条書き（`- ` で始まる行）のみを出力してください。見出し、挨拶文、前置き、まとめ、解説などは一切含めないでください。各項目は、次回以降の執筆で踏まえるべき原則として簡潔にまとめてください。
"""

    pattern_payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": pattern_prompt
                    }
                ]
            }
        ]
    }

    def build_pattern_request():
        return urllib.request.Request(
            url,
            data=json.dumps(pattern_payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )

    print("Calling Gemini API to summarize recurring feedback patterns...")
    try:
        pattern_response_data = call_gemini_api(build_pattern_request)
        recurring_patterns_text = pattern_response_data["candidates"][0]["content"]["parts"][0]["text"].strip()
        print("Successfully received recurring pattern summary from Gemini API.")
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        exit(1)

    # 6. Insert (or replace) the "0. 頻出課題" section at the top of the
    # knowledge base, right after the title and before "1. ホラーの基本原則".
    recurring_section_header = "## 0. 頻出課題（要優先対応）"
    first_principle_header = "## 1. ホラーの基本原則"
    recurring_section_block = (
        f"{recurring_section_header}\n\n"
        f"{recurring_patterns_text}\n\n"
        "---\n\n"
    )

    if first_principle_header not in knowledge_content:
        print(f"Warning: '{first_principle_header}' not found. Appending section 0 to the end instead.")
        if not knowledge_content.endswith("\n\n"):
            knowledge_content += "\n" if knowledge_content.endswith("\n") else "\n\n"
        knowledge_content += f"{recurring_section_header}\n\n{recurring_patterns_text}\n"
    else:
        before_part, _, after_part = knowledge_content.partition(first_principle_header)

        if recurring_section_header in before_part:
            print("Replacing the contents of the existing section 0.")
            before_part = before_part.split(recurring_section_header, 1)[0]
        else:
            print("Inserting a new section 0 at the top of the knowledge base.")

        before_part = before_part.rstrip("\n") + "\n\n"
        knowledge_content = before_part + recurring_section_block + first_principle_header + after_part

    with open(KNOWLEDGE_PATH, "w", encoding="utf-8") as f:
        f.write(knowledge_content)

    print(f"Successfully updated the recurring pattern section in: {KNOWLEDGE_PATH}")

if __name__ == "__main__":
    main()
