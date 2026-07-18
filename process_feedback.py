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
import urllib.request
import urllib.error

# Define paths
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_PATH = os.path.join(ROOT_DIR, "knowledge", "horror.md")

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

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
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

    req = urllib.request.Request(
        url, 
        data=json.dumps(payload).encode("utf-8"), 
        headers=headers, 
        method="POST"
    )

    print("Calling Gemini API...")
    try:
        with urllib.request.urlopen(req) as res:
            response_data = json.loads(res.read().decode("utf-8"))
            analysis_text = response_data["candidates"][0]["content"]["parts"][0]["text"].strip()
            print("Successfully received analysis from Gemini API.")
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.read().decode('utf-8')}")
        exit(1)
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

if __name__ == "__main__":
    main()
