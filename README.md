# AIホラー作家育成プロジェクト (horror-ai)

人工知能（LLM）によって執筆されたホラー小説を自動的に収集・整理し、美しく不気味なWebサイトとして公開するための静的サイトジェネレータープロジェクトです。

---

## ■ ディレクトリ構成

```text
├── .github/
│   └── workflows/
│       └── deploy.yml       # GitHub Actions デプロイ設定ファイル
├── docs/                     # Webサイトの公開用ディレクトリ（GitHub Pages対象）
│   ├── assets/
│   │   └── style.css        # プレミアムダークホラーテーマのCSSスタイルシート
│   ├── stories/             # 自動生成された各作品のHTMLファイル（例: 2026-07-17.html）
│   └── index.html           # 自動生成された作品一覧ページ
├── knowledge/
│   └── horror.md            # ホラー小説の執筆ナレッジベース（AI用参考資料）
├── stories/                 # 小説の元データ（Markdown形式）
│   ├── 2026-07-16.md        # サンプル小説 1
│   └── 2026-07-17.md        # サンプル小説 2
├── build.py                 # MarkdownをHTMLに変換しサイトを構築するビルドスクリプト
├── prompt.md                # AIホラー作家に執筆指示を出すためのプロンプトテンプレート
└── README.md                # 本セットアップマニュアル
```

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

---

## ■ 新しい作品の執筆・追加手順

1. **プロンプトの使用**:
   [prompt.md](prompt.md) の内容をコピーし、ChatGPTやClaudeなどのLLMのシステムプロンプトまたは指示として入力します。その際、ナレッジベースである [knowledge/horror.md](knowledge/horror.md) を読み込ませると、より高品質で不気味なストーリーが生成されます。

2. **ストーリーの追加**:
   生成された小説（フロントマター付きのMarkdown）を `stories/` ディレクトリに `YYYY-MM-DD.md` というファイル名で保存します。
   *(※ ファイル名の日付とフロントマター内の `date` は一致させてください。)*

   **フロントマターの記述例**:
   ```markdown
   ---
   title: "隙間の視線"
   date: "2026-07-17"
   synopsis: "新居のアパートのクローゼットと壁の隙間。わずか数ミリメートルのその暗闇から、冷たい視線を感じるようになった男の末路。"
   tags: [都市伝説, 心理的恐怖, 日常の亀裂]
   ---
   # ここから本文...
   ```

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
  各作品の下部には「感想を投稿する (GitHub Issues)」というリンクが設置されています。ユーザーがこれをクリックすると、フィードバック専用の GitHub Issue 新規作成画面に遷移します。フォーム等を設置することなく、安全かつオープンに感想を募集できます。
