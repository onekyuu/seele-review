# Seele Review 🤖

<div align="center">

[English](README_EN.md) | [简体中文](README.md) | 日本語

**GitLab と GitHub をサポートする AI 駆動型コードレビューツール**

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

<br/>
<img src="assets/seele-review-demo.jpg" alt="Seele Review Demo" width="800">
<br/>

[機能](#-機能) • [クイックスタート](#-クイックスタート) • [設定](#️-設定) • [使い方](#-使い方) • [API ドキュメント](#-api-ドキュメント)

</div>

---

## 📖 概要

Seele Review は、大規模言語モデル（LLM）を使用して GitLab の Merge Request と GitHub の Pull Request を自動的に分析するインテリジェントなコードレビューアシスタントです。建設的なフィードバックを提供し、潜在的な問題を特定することで、チームのコード品質維持を支援します。

### 🎯 機能

- 🤖 **AI インテリジェント分析** - GPT-4、Claude などの大規模言語モデルをサポート
- 🔄 **マルチプラットフォーム対応** - GitLab と GitHub の両方をサポート
- 📊 **デュアルレビューモード**
  - 💬 **コメントモード** - コードの変更箇所に直接インラインコメントを追加
  - 📄 **レポートモード** - MR/PR の説明に完全なレビューレポートを生成
- 🌍 **多言語サポート** - 中国語、英語、日本語のレビューコメントに対応
- ⚡ **スマートなトークン管理** - 非常に長い diff を自動的に複数のチャンクに分割して処理
- 🔔 **通知統合** - レビュー完了時に Slack、Lark（Feishu）へリアルタイム通知
- 🎨 **美しい CLI** - インタラクティブな設定ウィザードで素早く開始
- 🔧 **高度な設定** - 環境変数による柔軟な設定が可能

---

## 🚀 クイックスタート

### 必須環境

- Python 3.12+
- Pipenv
- GitLab または GitHub アカウントと API アクセス権限
- OpenAI API Key または互換性のある LLM エンドポイント
- （オプション）Slack または　 Lark Webhook URL

### インストール手順

1. **リポジトリのクローン**

   ```bash
   git clone https://github.com/yourusername/seele-review.git
   cd seele-review
   ```

2. **依存関係のインストール**

   ```bash
   pipenv install
   ```

3. **設定の初期化**

   ```bash
   pipenv run seele init
   ```

   インタラクティブな CLI が以下を案内します：

   - ターゲットプラットフォームの選択（GitLab/GitHub）
   - デフォルトのレビュー言語の設定
   - API トークンの設定
   - LLM エンドポイントの設定

4. **サービスの起動**
   ```bash
   pipenv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

---

## ⚙️ 設定

### 環境変数

`.env` ファイルを作成するか、CLI を使用して生成します：

```bash
# プラットフォーム設定
REPO_TARGETS=gitlab,github              # サポートするプラットフォーム
REPO_REVIEW_LANG=ja                     # レビューコメントの言語（zh/en/ja）

# GitLab 設定
GITLAB_BASE_URL=https://gitlab.com
GITLAB_DEFAULT_TOKEN=your_gitlab_token

# GitHub 設定
GITHUB_BASE_URL=https://api.github.com
GITHUB_DEFAULT_TOKEN=your_github_token

# LLM 設定
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your_openai_api_key
LLM_MODEL=gpt-4

# 通知設定（オプション：Slack、Lark）
NOTIFICATION_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# レビュー設定
AI_REVIEW_MODE=comment                  # comment または report
PUSH_URL=                               # デフォルトの Slack Webhook（オプション）
```

### 手動設定

サンプル設定ファイルをコピーして手動で編集することも可能です：

```bash
cp .env.example .env
nano .env
```

---

## 📚 使い方

### Webhook の設定

#### GitLab

1. プロジェクトに移動：**Settings > Webhooks**
2. Webhook URL を追加：`https://your-domain.com/webhook/gitlab`
3. トリガーを選択：**Merge request events**
4. カスタムヘッダーを追加（オプション）：
   ```
   X-Ai-Mode: comment
   X-Push-Url: https://hooks.slack.com/services/...
   X-Gitlab-Token: your_secret_token
   ```

#### GitHub

1. リポジトリに移動：**Settings > Webhooks**
2. Webhook URL を追加：`https://your-domain.com/webhook/github`
3. Content type：`application/json`
4. イベントを選択：**Pull requests**
5. Secret を追加（オプション）

### レビューモード

#### 💬 コメントモード（デフォルト）

MR/PR のコード変更箇所に直接インラインコメントを追加します。

**リクエストヘッダー：**

```http
X-Ai-Mode: comment
```

**例：**

```diff
@@ -10,3 +10,5 @@
 def login(username, password):
+    return authenticate(username, password)
```

**11 行目の AI コメント：**

> ⚠️ **セキュリティリスク**  
> 認証の前に入力検証とパスワードのハッシュ化を追加することを検討してください。

#### 📄 レポートモード

MR/PR の説明に完全なレビューレポートの要約を生成します。

**リクエストヘッダー：**

```http
X-Ai-Mode: report
```

**例：**

```markdown
## 🤖 AI コードレビューレポート

### 要約

2 つのファイルで 3 つの潜在的な問題が見つかりました。

### 問題リスト

| ファイル    | 行番号 | 重要度    | 問題                       |
| ----------- | ------ | --------- | -------------------------- |
| app/auth.py | 11     | ⚠️ 警告   | 入力検証の欠落             |
| app/db.py   | 45     | 🔴 エラー | SQL インジェクションリスク |
```

### CLI コマンド

```bash
# 設定の初期化
pipenv run seele init

# 開発サーバーの起動
pipenv run seele run --host 0.0.0.0 --port 8000 --reload

# 本番サーバーの起動（自動リロードなし）
pipenv run seele run --host 0.0.0.0 --port 8000 --no-reload
```

---

## 🔌 API ドキュメント

### GitLab Webhook

```http
POST /webhook/gitlab
Content-Type: application/json
X-Gitlab-Token: your_token （オプション）
X-Ai-Mode: comment （オプション、デフォルト：comment）
X-Push-Url: slack_webhook_url （オプション）
```

**リクエストボディ：** GitLab Merge Request webhook payload

**レスポンス：**

```json
{
  "ok": true,
  "reviews_count": 3,
  "mode": "comment"
}
```

### GitHub Webhook

```http
POST /webhook/github
Content-Type: application/json
X-Hub-Signature-256: signature （オプション）
X-Ai-Mode: comment （オプション、デフォルト：comment）
```

**リクエストボディ：** GitHub Pull Request webhook payload

**レスポンス：**

```json
{
  "ok": true,
  "reviews_count": 5,
  "mode": "comment"
}
```

---

## 🛠️ 開発ガイド

### プロジェクト構造

```
seele-review/
├── app/
│   ├── config.py              # 設定管理
│   ├── main.py                # FastAPI アプリケーション
│   ├── cli.py                 # CLI ツール
│   ├── routers/               # API ルーティング
│   │   ├── gitlab.py          # GitLab webhook ハンドラ
│   │   └── github.py          # GitHub webhook ハンドラ
│   ├── services/              # ビジネスロジック
│   │   ├── agent/             # AI エージェントサービス
│   │   ├── gitlab.py          # GitLab API クライアント
│   │   ├── github.py          # GitHub API クライアント
│   │   ├── patch/             # Diff 解析
│   │   ├── prompt/            # Prompt テンプレート
│   │   └── publish/           # レビュー公開
│   ├── schemas/               # Pydantic モデル
│   ├── utils/                 # ユーティリティ
│   │   └── token.py           # Token 管理
│   └── prompt/                # Prompt テンプレートファイル
│       ├── prompt-zh.txt      # 中国語 prompt
│       ├── prompt-en.txt      # 英語 prompt
│       └── prompt-ja.txt      # 日本語 prompt
├── Pipfile                    # Python 依存関係
├── README.md                  # 本ドキュメント
└── .env                       # 環境変数（作成が必要）
```

### Token 管理

Seele Review は、LLM のコンテキスト制限を超える大規模な diff を自動的に処理します：

1. **Token カウント** - tiktoken を使用して正確に token 数を計算
