#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Horror Writer Project - Static Site Builder
This script converts Markdown files in `stories/` into HTML files in `docs/` and `docs/stories/`.
No external dependencies are required.
"""

import html
import os
import re
import urllib.parse

# Define paths relative to the project root
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
STORIES_DIR = os.path.join(ROOT_DIR, "stories")
DOCS_DIR = os.path.join(ROOT_DIR, "docs")
DOCS_STORIES_DIR = os.path.join(DOCS_DIR, "stories")

# Story files are named YYYY-MM-DD.md (optionally with a suffix such as
# 2026-07-27-b.md when more than one story is published on the same day).
DATE_FROM_FILENAME_RE = re.compile(r'^(\d{4}-\d{2}-\d{2})')

# Frontmatter is a `---` delimited block at the very top of the file.
FRONTMATTER_RE = re.compile(r'\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)', re.DOTALL)

# Shared <option> list (1-10) used by every rating <select> in the feedback form
RATING_OPTIONS_HTML = '<option value="">-</option>' + ''.join(
    f'<option value="{i}">{i}</option>' for i in range(1, 11)
)

def parse_markdown(content, fallback_date=""):
    """
    Parses Markdown frontmatter (YAML block) and main content body.

    `fallback_date` is used when the frontmatter has no `date` key; the caller
    normally passes the date encoded in the file name.
    """
    frontmatter = {}
    content = content.replace('\r\n', '\n').strip()

    match = FRONTMATTER_RE.match(content)
    if match:
        yaml_part = match.group(1)
        body = content[match.end():].strip()
        # Parse YAML-like lines
        for line in yaml_part.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")

                if key == "tags":
                    # Handle tag lists, e.g., [horror, ghost] or horror, ghost
                    tags_str = value
                    if tags_str.startswith("[") and tags_str.endswith("]"):
                        tags_str = tags_str[1:-1]
                    frontmatter["tags"] = [t.strip().strip('"').strip("'") for t in tags_str.split(",") if t.strip()]
                else:
                    frontmatter[key] = value
    else:
        body = content

    # Default values if missing
    if not frontmatter.get("title"):
        frontmatter["title"] = "無題の怪談"
    if not frontmatter.get("date"):
        frontmatter["date"] = fallback_date
    if not frontmatter.get("synopsis"):
        frontmatter["synopsis"] = "解説はありません。"
    if "tags" not in frontmatter:
        frontmatter["tags"] = []

    return frontmatter, body

def inline_markdown(text):
    """
    Converts inline Markdown (bold, italic, links) to HTML.

    The input is treated as plain text: HTML special characters are escaped
    first so that a `<` or `&` inside a story can never inject raw markup.
    """
    text = html.escape(text)
    # Bold: **text** or __text__
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__(.*?)__', r'<strong>\1</strong>', text)
    # Italic: *text* or _text_
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    text = re.sub(r'_(.*?)_', r'<em>\1</em>', text)
    # Links: [text](url)
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', text)
    return text

def markdown_to_html(md_text, heading_offset=0):
    """
    Converts a Markdown string to an HTML block string.

    `heading_offset` shifts every heading down by N levels (e.g. an offset of 2
    renders `#` as `<h3>`), so that story bodies stay below the page's own
    `<h1>`/`<h2>` in the document outline.
    """
    md_text = md_text.replace('\r\n', '\n')
    # Split into blocks by two or more newlines
    raw_blocks = re.split(r'\n\n+', md_text)
    html_blocks = []

    for block in raw_blocks:
        block = block.strip()
        if not block:
            continue

        lines = block.split('\n')

        # Check if horizontal rule (must be tested before the list check,
        # otherwise `---` looks like a bullet list of empty items)
        if re.fullmatch(r'-{3,}|\*{3,}|_{3,}', block):
            html_blocks.append("<hr>")
            continue

        # Check if list (all lines starting with "- ", "* " or "+ ")
        is_list = all(re.match(r'^[-*+]\s+\S', line.strip()) for line in lines)

        if is_list:
            items_html = []
            for line in lines:
                line_content = line.strip()[1:].strip()
                items_html.append(f"<li>{inline_markdown(line_content)}</li>")
            html_blocks.append(f"<ul>{''.join(items_html)}</ul>")
            continue

        # Check if heading
        if block.startswith('#'):
            match = re.match(r'^(#{1,6})\s+(.*)$', block)
            if match:
                level = min(len(match.group(1)) + heading_offset, 6)
                content = inline_markdown(match.group(2).strip())
                html_blocks.append(f"<h{level}>{content}</h{level}>")
                continue

        # Check if blockquote
        if block.startswith('>'):
            quote_lines = []
            for line in lines:
                if line.strip().startswith('>'):
                    quote_lines.append(line.strip()[1:].strip())
                else:
                    quote_lines.append(line.strip())
            # Recursively render blockquote body
            quote_content = markdown_to_html('\n\n'.join(quote_lines), heading_offset)
            html_blocks.append(f"<blockquote>{quote_content}</blockquote>")
            continue

        # Standard paragraph
        # Preserving single line breaks within paragraphs as <br>
        content = inline_markdown(block).replace('\n', '<br>')
        html_blocks.append(f"<p>{content}</p>")

    return '\n'.join(html_blocks)

def strip_duplicate_title(body, title):
    """
    Removes a leading `# タイトル` heading that merely repeats the frontmatter
    title, since the page template already renders the title in its header.
    """
    match = re.match(r'^#\s+(.*?)[ \t]*(?:\n|$)', body)
    if match and match.group(1).strip() == title.strip():
        return body[match.end():].lstrip('\n')
    return body

def render_tags(tags):
    """Renders a list of tags as an HTML block (empty string when there are none)."""
    if not tags:
        return ""
    spans = ''.join(f'<span class="tag">#{html.escape(t)}</span>' for t in tags)
    return f'<div class="tags">{spans}</div>'

# Page Layout Templates
STORY_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - AIホラー作家育成プロジェクト</title>
    <meta name="description" content="{synopsis}">
    <meta property="og:type" content="article">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{synopsis}">
    <link rel="stylesheet" href="../assets/style.css">
</head>
<body>
    <header>
        <h1><a href="../index.html">AIホラー作家育成プロジェクト</a></h1>
        <p>暗闇から紡ぎ出される、人工知能による恐怖の物語群。</p>
    </header>
    
    <div class="container">
        <nav>
            <a href="../index.html">← 作品一覧に戻る</a>
        </nav>
        
        <article class="story-container">
            <div class="story-header">
                <h2>{title}</h2>
                <div class="story-meta">
                    <span>公開日: {date}</span>
                    {tags_html}
                </div>
            </div>
            
            <div class="story-content">
                {content_html}
            </div>
        </article>
        
        <div class="feedback-box">
            <h3>この作品の感想を聞かせてください</h3>
            <p>下のフォームに評価とコメントを入力し、「① 回答をコピーする」を押してください。コピーした内容を「② GitHub Issueを開く」から本文に貼り付けて投稿すると、次回作の改善に活かされます。</p>

            <form class="feedback-form" onsubmit="return false;">
                <div class="rating-grid">
                    <div class="form-group">
                        <label for="rating-atmosphere">雰囲気</label>
                        <select id="rating-atmosphere">{rating_options_html}</select>
                    </div>
                    <div class="form-group">
                        <label for="rating-fear">怖さ</label>
                        <select id="rating-fear">{rating_options_html}</select>
                    </div>
                    <div class="form-group">
                        <label for="rating-structure">構成</label>
                        <select id="rating-structure">{rating_options_html}</select>
                    </div>
                    <div class="form-group">
                        <label for="rating-expression">表現力</label>
                        <select id="rating-expression">{rating_options_html}</select>
                    </div>
                </div>

                <div class="form-group">
                    <label for="feedback-good">良かった点</label>
                    <textarea id="feedback-good" rows="3" placeholder="怖かった描写、印象に残ったセリフなど"></textarea>
                </div>

                <div class="form-group">
                    <label for="feedback-bad">悪かった点</label>
                    <textarea id="feedback-bad" rows="3" placeholder="没入感が削がれた部分、違和感のある設定など"></textarea>
                </div>

                <div class="form-group">
                    <label for="feedback-improve">改善案・その他のコメント</label>
                    <textarea id="feedback-improve" rows="3" placeholder="次回作への要望など"></textarea>
                </div>

                <div class="feedback-actions">
                    <button type="button" class="btn-copy" onclick="copyFeedback()">📋 ① 回答をコピーする</button>
                    <a href="https://github.com/KozueMitarai/horror-ai/issues/new?title={feedback_title}" target="_blank" rel="noopener noreferrer" class="btn-feedback">
                        💬 ② GitHub Issueを開く
                    </a>
                </div>
                <p id="copy-feedback-status" class="copy-status" role="status"></p>
            </form>
        </div>
    </div>

    <footer>
        <p>© 2026 AIホラー作家育成プロジェクト</p>
        <p>This website is automatically generated and deployed.</p>
    </footer>

    <script>
    function copyFeedback() {{
        var atmosphere = document.getElementById('rating-atmosphere').value;
        var fear = document.getElementById('rating-fear').value;
        var structure = document.getElementById('rating-structure').value;
        var expression = document.getElementById('rating-expression').value;
        var good = document.getElementById('feedback-good').value.trim();
        var bad = document.getElementById('feedback-bad').value.trim();
        var improve = document.getElementById('feedback-improve').value.trim();

        var lines = [];
        lines.push('■評価（10点満点、未回答は「-」）');
        lines.push('雰囲気: ' + (atmosphere || '-'));
        lines.push('怖さ: ' + (fear || '-'));
        lines.push('構成: ' + (structure || '-'));
        lines.push('表現力: ' + (expression || '-'));
        lines.push('');
        lines.push('■良かった点');
        lines.push(good || '(未記入)');
        lines.push('');
        lines.push('■悪かった点');
        lines.push(bad || '(未記入)');
        lines.push('');
        lines.push('■改善案・その他のコメント');
        lines.push(improve || '(未記入)');

        var text = lines.join('\\n');
        var statusEl = document.getElementById('copy-feedback-status');

        function showSuccess() {{
            statusEl.textContent = '✅ コピーしました。②のボタンからIssueを開いて、本文に貼り付けてください。';
            statusEl.className = 'copy-status copy-status-ok';
        }}
        function showFailure() {{
            statusEl.textContent = '⚠ 自動コピーに失敗しました。お手数ですが手動でコピーしてください。';
            statusEl.className = 'copy-status copy-status-error';
        }}

        if (navigator.clipboard && navigator.clipboard.writeText) {{
            navigator.clipboard.writeText(text).then(showSuccess, function() {{
                fallbackCopy(text, showSuccess, showFailure);
            }});
        }} else {{
            fallbackCopy(text, showSuccess, showFailure);
        }}
    }}

    function fallbackCopy(text, onSuccess, onFailure) {{
        var temp = document.createElement('textarea');
        temp.value = text;
        temp.style.position = 'fixed';
        temp.style.opacity = '0';
        document.body.appendChild(temp);
        temp.focus();
        temp.select();
        try {{
            var ok = document.execCommand('copy');
            document.body.removeChild(temp);
            if (ok) {{ onSuccess(); }} else {{ onFailure(); }}
        }} catch (err) {{
            document.body.removeChild(temp);
            onFailure();
        }}
    }}
    </script>
</body>
</html>
"""

INDEX_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AIホラー作家育成プロジェクト</title>
    <meta name="description" content="人工知能が執筆するホラー小説。AIによる独自の恐怖、コズミックホラー、心理的恐怖を収録しています。">
    <meta property="og:type" content="website">
    <meta property="og:title" content="AIホラー作家育成プロジェクト">
    <meta property="og:description" content="人工知能が執筆するホラー小説。AIによる独自の恐怖、コズミックホラー、心理的恐怖を収録しています。">
    <link rel="stylesheet" href="assets/style.css">
</head>
<body>
    <header>
        <h1><a href="index.html">AIホラー作家育成プロジェクト</a></h1>
        <p>暗闇から紡ぎ出される、人工知能による恐怖の物語群。</p>
    </header>
    
    <div class="container">
        <div class="story-list">
            {stories_list_html}
        </div>
    </div>
    
    <footer>
        <p>© 2026 AIホラー作家育成プロジェクト</p>
        <p>This website is automatically generated and deployed.</p>
    </footer>
</body>
</html>
"""

def build_story_page(frontmatter, body):
    """Renders a single story page from its frontmatter and Markdown body."""
    # The template already prints the title, so drop a duplicate `# タイトル`
    # heading and push the remaining headings below it in the outline.
    body = strip_duplicate_title(body, frontmatter["title"])
    content_html = markdown_to_html(body, heading_offset=2)

    # Prepare feedback link title (URL encoded)
    feedback_title = urllib.parse.quote(f"感想: {frontmatter['title']} ({frontmatter['date']})")

    return STORY_PAGE_TEMPLATE.format(
        title=html.escape(frontmatter["title"]),
        date=html.escape(frontmatter["date"]),
        synopsis=html.escape(frontmatter["synopsis"]),
        tags_html=render_tags(frontmatter["tags"]),
        content_html=content_html,
        feedback_title=feedback_title,
        rating_options_html=RATING_OPTIONS_HTML
    )

def build_index_page(stories_data):
    """Renders the index page from the collected story metadata."""
    stories_list_html_parts = []
    for story in stories_data:
        story_card = f"""            <article class="story-card">
                <div class="story-meta">
                    <span>公開日: {html.escape(story["date"])}</span>
                    {render_tags(story["tags"])}
                </div>
                <h2>{html.escape(story["title"])}</h2>
                <p class="story-synopsis">{html.escape(story["synopsis"])}</p>
                <a href="stories/{urllib.parse.quote(story["filename"])}" class="story-link">物語を読む</a>
            </article>"""
        stories_list_html_parts.append(story_card)

    return INDEX_PAGE_TEMPLATE.format(stories_list_html="\n".join(stories_list_html_parts))

def remove_orphan_pages(expected_filenames):
    """Deletes generated story pages whose source Markdown no longer exists."""
    for filename in sorted(os.listdir(DOCS_STORIES_DIR)):
        if filename.endswith(".html") and filename not in expected_filenames:
            print(f"Removing orphaned page: {filename}")
            os.remove(os.path.join(DOCS_STORIES_DIR, filename))

def main():
    print("Building static horror stories site...")

    # Check directories
    if not os.path.exists(STORIES_DIR):
        print(f"Error: Stories directory '{STORIES_DIR}' does not exist. Creating it.")
        os.makedirs(STORIES_DIR, exist_ok=True)

    os.makedirs(DOCS_STORIES_DIR, exist_ok=True)

    stories_data = []

    # Process each markdown file in the stories/ directory.
    # Sorting keeps the build output byte-for-byte reproducible.
    for filename in sorted(os.listdir(STORIES_DIR)):
        if not filename.endswith(".md"):
            continue

        filepath = os.path.join(STORIES_DIR, filename)
        print(f"Processing story: {filename}")

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        stem = filename[:-len(".md")]
        date_match = DATE_FROM_FILENAME_RE.match(stem)
        frontmatter, body = parse_markdown(
            content, fallback_date=date_match.group(1) if date_match else ""
        )

        # Base filename for the HTML output (e.g., 2026-07-17.html)
        html_filename = stem + ".html"

        # Write individual story HTML page
        story_out_path = os.path.join(DOCS_STORIES_DIR, html_filename)
        with open(story_out_path, "w", encoding="utf-8") as f:
            f.write(build_story_page(frontmatter, body))

        # Keep data for the main index page
        stories_data.append({
            "title": frontmatter["title"],
            "date": frontmatter["date"],
            "synopsis": frontmatter["synopsis"],
            "tags": frontmatter["tags"],
            "filename": html_filename
        })

    # Sort stories by date descending (latest first). The file name breaks ties
    # so that same-day stories keep a stable order between builds.
    stories_data.sort(key=lambda s: (s["date"], s["filename"]), reverse=True)

    # Drop pages left behind by stories that were renamed or deleted
    remove_orphan_pages({s["filename"] for s in stories_data})

    # Write docs/index.html
    index_out_path = os.path.join(DOCS_DIR, "index.html")
    with open(index_out_path, "w", encoding="utf-8") as f:
        f.write(build_index_page(stories_data))

    print(f"Build complete successfully! ({len(stories_data)} stories)")

if __name__ == "__main__":
    main()
