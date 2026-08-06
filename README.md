# AIホラー作家育成プロジェクト (horror-ai)

人工知能（LLM）によって執筆されたホラー小説を自動的に収集・整理し、美しく不気味なWebサイトとして公開するための静的サイトジェネレータープロジェクトです。

---

## ■ ディレクトリ構成

```text
├── .github/
│   └── workflows/
│       ├── ci.yml                # テストとビルドの自動チェック（push / PR）
│       ├── deploy.yml            # GitHub Pages へのデプロイ
│       └── analyze_feedback.yml  # 感想Issueを解析しナレッジベースへ反映
├── docs/                     # Webサイトの公開用ディレクトリ（GitHub Pages対象）
│   ├── assets/
│   │   └── style.css        # プレミアムダークホラーテーマのCSSスタイルシート
│   ├── stories/             # ★生成物★ 各作品のHTMLファイル（例: 2026-07-17.html）
│   └── index.html           # ★生成物★ 作品一覧ページ
├── knowledge/
│   ├── horror.md            # ホラー小説の執筆ナレッジベース（AI用参考資料）
│   └── feedback_archive.md  # 過去の読者フィードバック分析のアーカイブ
├── stories/                 # 小説の元データ（Markdown形式）※これが唯一の原本
│   ├── 2026-07-16.md
│   └── ...
├── tests/
│   └── test_build.py        # build.py のユニットテスト（標準ライブラリのみ）
├── build.py                 # MarkdownをHTMLに変換しサイトを構築するビルドスクリプト
├── process_feedback.py      # 感想Issueを Gemini API で解析しナレッジベースに追記
├── prompt.md                # AIホラー作家に執筆指示を出すためのプロンプトテンプレート
└── README.md                # 本セットアップマニュアル
```

> **★生成物について**
> `docs/index.html` と `docs/stories/*.html` は `build.py` が毎回生成するため、Gitの管理対象外（`.gitignore`）です。
> 公開サイトはデプロイ時に GitHub Actions 上でビルドされるので、生成物をコミットする必要はありません。
> ローカルで確認したいときは `python3 build.py` を実行してください。
> 一方で `docs/assets/style.css` は手書きの原本なので、Gitで管理されています。

---

## ■ ローカルセットアップ・開発手順

本プロジェクトは外部ライブラリを一切使用せず、Python 3 の標準ライブラリのみで動作します。

### 1. 動作要件
- Python 3.9 以上

### 2. ローカルでのビルド方法
以下のコマンドを実行すると、`stories/` 配下のすべての `.md` ファイルを読み込み、`docs/index.html` および `docs/stories/*.html` を自動生成します。

```bash
python3 build.py
```

### 3. ローカルでのWebサーバー起動方法
ビルドされたWebサイトの表示・確認を行うには、Pythonの内蔵HTTPサーバーを使用します。

```bash
python3 -m http.server 8080 -d docs
```

起動後、ブラウザで [http://localhost:8080](http://localhost:8080) にアクセスすると、ローカル環境でWebサイトを確認できます。

### 4. テストの実行方法
`build.py` のMarkdownパーサ・HTML生成についてのユニットテストを用意しています。こちらも標準ライブラリのみで動作します。

```bash
python3 -m unittest discover -s tests
```

同じテストとビルドは、`main` へのpushおよびPull Request時に GitHub Actions (`.github/workflows/ci.yml`) でも自動実行されます。

---

## ■ 新しい作品の執筆・追加手順

1. **プロンプトの使用**:
   [prompt.md](prompt.md) の内容をコピーし、ChatGPTやClaudeなどのLLMのシステムプロンプトまたは指示として入力します。その際、ナレッジベースである [knowledge/horror.md](knowledge/horror.md) を読み込ませると、より高品質で不気味なストーリーが生成されます。

2. **ストーリーの追加**:
   生成された小説（フロントマター付きのMarkdown）を `stories/` ディレクトリに `YYYY-MM-DD.md` というファイル名で保存します。
   *(※ ファイル名の日付とフロントマター内の `date` は一致させてください。)*
   *(※ 同じ日に2作目を公開する場合は `2026-07-27-b.md` のように接尾辞を付けます。)*

   **フロントマターの記述例**:
   ```markdown
   ---
   title: "隙間の視線"
   date: "2026-07-17"
   synopsis: "新居のアパートのクローゼットと壁の隙間。わずか数ミリメートルのその暗闇から、冷たい視線を感じるようになった男の末路。"
   tags: [都市伝説, 心理的恐怖, 日常の亀裂]
   ---

   新しいアパートに引っ越してきてから三日目の夜、私はその「隙間」に気づいた。
   ```

   **本文の書き方**:
   - 段落は空行で区切ります。段落内の改行は `<br>` として保持されます。
   - 場面転換には `---` だけの行を使うと、区切り線として描画されます。
   - `> ` で始まる行は引用ブロック（録音記録・チャット・通知文など）になります。
   - `**強調**` / `*斜体*` / `[リンク](URL)` が使えます。それ以外の記号はそのまま文字として表示されます（HTMLは自動でエスケープされます）。
   - 本文冒頭に `# タイトル` を置いてもかまいません。フロントマターの `title` と同じ場合は、ページ側で既に見出しを表示しているため自動的に取り除かれます。

3. **コミット & プッシュ**:
   ファイルをリポジトリに追加し、`main` ブランチへプッシュします。

---

## ■ 自動デプロイと動作仕様

- **GitHub Actions 連携**:
  `main` ブランチへ変更がプッシュされると、GitHub Actions ワークフロー (`.github/workflows/deploy.yml`) が自動的に起動します。
  ワークフロー内で自動的に `build.py` が実行され、成果物（`docs/` 配下）が GitHub Pages へ即座にデプロイされます。

- **GitHub Pagesの設定**:
  リポジトリの `Settings` > `Pages` から、**Build and deployment > Source** を「**GitHub Actions**」に設定してください。

- **感想・フィードバックの受付**:
  各作品の下部には感想フォーム（評価4項目 + 自由記述3項目）が設置されています。読者は「① 回答をコピーする」で内容をクリップボードへコピーし、「② GitHub Issueを開く」から本文に貼り付けて投稿します。サーバーを持たずに、安全かつオープンに感想を募集できます。

- **フィードバックの自動解析**:
  Issueが作成されると `.github/workflows/analyze_feedback.yml` が起動し、`process_feedback.py` が Gemini API で内容を分析して `knowledge/horror.md` に追記したうえで、お礼のコメントを投稿してIssueをクローズします。

  - リポジトリの `Settings` > `Secrets and variables` > `Actions` に、シークレット `GEMINI_API_KEY` を登録してください。
  - 使用モデルはリポジトリ変数 `GEMINI_MODEL` で差し替えられます（未設定時は `gemini-3.5-flash`）。
  - このワークフローは**タイトルが「感想」で始まるIssueのみ**を対象とします。感想フォームのリンクが生成するタイトル（`感想: 作品名 (日付)`）がこれに該当します。不具合報告や要望など、それ以外のIssueが自動でクローズされることはありません。
  - 蓄積された知見のうち、`## 7. 読者フィードバックからの知見` は直近5件程度に保ち、古いものは `knowledge/feedback_archive.md` へ手動で移動してナレッジベースの肥大化を防ぎます。
