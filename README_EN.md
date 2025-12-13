# Seele Review 🤖

<div align="center">

English | [简体中文](README.md)

**AI-Powered Code Review for GitLab & GitHub**

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Features](#-features) • [Quick Start](#-quick-start) • [Configuration](#️-configuration) • [Usage](#-usage) • [API](#-api-reference)

</div>

---

## 📖 Overview

Seele Review is an intelligent code review assistant that automatically analyzes Merge Requests (MR) and Pull Requests (PR) using Large Language Models (LLM). It provides constructive feedback, identifies potential issues, and helps maintain code quality across your projects.

### 🎯 Key Features

- 🤖 **AI-Powered Analysis** - Leverages GPT-4, Claude, or compatible LLMs for intelligent code review
- 🔄 **Multi-Platform Support** - Works with GitLab and GitHub
- 📊 **Dual Review Modes**
  - 💬 **Comment Mode** - Direct inline comments on changed lines
  - 📄 **Report Mode** - Comprehensive review summary in MR/PR description
- 🌍 **Multi-Language** - Supports Chinese, English, and Japanese review comments
- ⚡ **Smart Token Management** - Automatically splits large diffs into chunks
- 🔔 **Slack Integration** - Real-time notifications for review completion
- 🎨 **Beautiful CLI** - Interactive setup with rich terminal UI
- 🔧 **Highly Configurable** - Flexible configuration via environment variables

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Pipenv
- GitLab or GitHub account with API access
- OpenAI API key or compatible LLM endpoint
- (Optional) Slack webhook URL for notifications

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/seele-review.git
   cd seele-review
   ```

2. **Install dependencies**

   ```bash
   pipenv install
   ```

3. **Initialize configuration**

   ```bash
   pipenv run seele init
   ```

   The interactive CLI will guide you through:

   - Choosing platforms (GitLab/GitHub)
   - Setting default review language
   - Configuring API tokens
   - Setting up LLM endpoint

4. **Start the service**
   ```bash
   pipenv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file or use the CLI to generate it:

```bash
# Platform Configuration
REPO_TARGETS=gitlab,github              # Supported platforms
REPO_REVIEW_LANG=zh                     # Review comment language (zh/en/ja)

# GitLab Configuration
GITLAB_BASE_URL=https://gitlab.com
GITLAB_DEFAULT_TOKEN=your_gitlab_token

# GitHub Configuration
GITHUB_BASE_URL=https://api.github.com
GITHUB_DEFAULT_TOKEN=your_github_token

# LLM Configuration
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your_openai_api_key
LLM_MODEL=gpt-4

# Notification Configuration (Optional)
NOTIFICATION_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Review Configuration
AI_REVIEW_MODE=comment                  # comment or report
PUSH_URL=                               # Default Slack webhook (optional)
```

### Manual Configuration

Alternatively, copy `.env.example` and edit manually:

```bash
cp .env.example .env
nano .env
```

---

## 📚 Usage

### Setting Up Webhooks

#### GitLab

1. Navigate to your project: **Settings > Webhooks**
2. Add webhook URL: `https://your-domain.com/webhook/gitlab`
3. Select trigger: **Merge request events**
4. Add custom headers (optional):
   ```
   X-Ai-Mode: comment
   X-Push-Url: https://hooks.slack.com/services/...
   X-Gitlab-Token: your_secret_token
   ```

#### GitHub

1. Navigate to your repository: **Settings > Webhooks**
2. Add webhook URL: `https://your-domain.com/webhook/github`
3. Content type: `application/json`
4. Select events: **Pull requests**
5. Add secret token (optional)

### Review Modes

#### 💬 Comment Mode (Default)

Posts inline comments directly on changed lines in the MR/PR.

**Request Header:**

```http
X-Ai-Mode: comment
```

**Example:**

```diff
@@ -10,3 +10,5 @@
 def login(username, password):
+    return authenticate(username, password)
```

**AI Comment on line 11:**

> ⚠️ **Security Risk**  
> Consider adding input validation and password hashing before authentication.

#### 📄 Report Mode

Generates a comprehensive review summary in the MR/PR description.

**Request Header:**

```http
X-Ai-Mode: report
```

**Example:**

```markdown
## 🤖 AI Code Review Report

### Summary

Found 3 potential issues across 2 files.

### Issues

| File        | Line | Severity   | Issue                    |
| ----------- | ---- | ---------- | ------------------------ |
| app/auth.py | 11   | ⚠️ Warning | Missing input validation |
| app/db.py   | 45   | 🔴 Error   | SQL injection risk       |
```

### CLI Commands

```bash
# Initialize configuration
pipenv run seele init

# Start development server
pipenv run seele run --host 0.0.0.0 --port 8000 --reload

# Start production server (no reload)
pipenv run seele run --host 0.0.0.0 --port 8000 --no-reload
```

---

## 🔌 API Reference

### Health Check

```http
GET /health
```

**Response:**

```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

### GitLab Webhook

```http
POST /webhook/gitlab
Content-Type: application/json
X-Gitlab-Token: your_token (optional)
X-Ai-Mode: comment (optional, default: comment)
X-Push-Url: slack_webhook_url (optional)
```

**Payload:** GitLab Merge Request webhook payload

**Response:**

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
X-Hub-Signature-256: signature (optional)
X-Ai-Mode: comment (optional, default: comment)
```

**Payload:** GitHub Pull Request webhook payload

**Response:**

```json
{
  "ok": true,
  "reviews_count": 5,
  "mode": "comment"
}
```

---

## 🛠️ Development

### Project Structure

```
seele-review/
├── app/
│   ├── config.py              # Configuration management
│   ├── main.py                # FastAPI application
│   ├── cli.py                 # CLI tool
│   ├── routers/               # API routes
│   │   ├── gitlab.py          # GitLab webhook handler
│   │   └── github.py          # GitHub webhook handler
│   ├── services/              # Business logic
│   │   ├── agent/             # AI agent service
│   │   ├── gitlab.py          # GitLab API client
│   │   ├── github.py          # GitHub API client
│   │   ├── patch/             # Diff parsing
│   │   ├── prompt/            # Prompt templates
│   │   └── publish/           # Review publishing
│   ├── schemas/               # Pydantic models
│   ├── utils/                 # Utilities
│   │   └── token.py           # Token management
│   └── prompt/                # Prompt templates
│       ├── prompt-zh.txt      # Chinese prompt
│       ├── prompt-en.txt      # English prompt
│       └── prompt-ja.txt      # Japanese prompt
├── Pipfile                    # Python dependencies
├── README.md                  # Chinese documentation
├── README_EN.md               # This file
└── .env                       # Environment variables (create this)
```

### Token Management

Seele Review automatically handles large diffs that exceed LLM context limits:

1. **Token Counting** - Accurately counts tokens using tiktoken
2. **Smart Splitting** - Splits by file boundaries to preserve context
3. **Chunk Processing** - Processes each chunk independently
4. **Result Merging** - Deduplicates and merges reviews from multiple chunks

```python
# Example usage
token_handler = TokenHandler(model="gpt-4", max_tokens=6000)

# Check if content fits
if token_handler.is_within_limit(diff_content):
    reviews = await agent.get_prediction(diff_content)
else:
    # Automatically splits and processes
    reviews = await agent.get_prediction(diff_content)
```

### Adding Custom Prompts

1. Create a new prompt file in `app/prompt/`:

   ```bash
   touch app/prompt/prompt-fr.txt
   ```

2. Define the prompt structure:

   ````text
   You are a code review expert...

   ## new_path: file.py
   ## old_path: file.py
   ...

   Output format:
   ```yaml
   reviews:
     - newPath: file.py
       oldPath: file.py
       ...
   ````

3. Update `PromptService` to load the new prompt:
   ```python
   def get_messages(self, query: str) -> list:
       lang = settings.repo_review_lang
       prompt_file = f"app/prompt/prompt-{lang}.txt"
       # ...
   ```

### Running Tests

```bash
# Test Slack integration
python app/test_slack.py

# Test with curl
curl -X POST http://localhost:8000/webhook/gitlab \
  -H "Content-Type: application/json" \
  -H "X-Ai-Mode: comment" \
  -d @test_payload.json
```

---

## 🌟 Advanced Features

### Custom Review Criteria

Modify prompts to focus on specific aspects:

- **Security** - Focus on vulnerabilities and best practices
- **Performance** - Identify bottlenecks and optimization opportunities
- **Code Style** - Enforce coding standards
- **Documentation** - Check for missing comments and docs

### Multi-Chunk Processing

For repositories with large changes:

```
[INFO] Query content: 12000 tokens
[WARNING] Content exceeds limit, splitting...
[INFO] Split into 2 chunks
[INFO] Processing chunk 1/2 (6500 tokens)
[INFO] Processing chunk 2/2 (5500 tokens)
[SUCCESS] Merged 7 unique reviews from 2 chunks
```

### Slack Notifications

Receive real-time updates in Slack:

```
✅ AI Code Review Completed

Project: company/backend-api
MR: Fix authentication bug
Author: John Doe
Branch: feature/auth-fix → main
Result: 3 review comments
```

---

## 🐛 Troubleshooting

### Common Issues

**1. "No reviews generated"**

- Check LLM API key and endpoint
- Verify diff format is correct
- Check token limits

**2. "Slack notification not received"**

- Verify webhook URL is correct
- Check webhook URL format (should contain `hooks.slack.com`)
- Test with `app/test_slack.py`

**3. "GitLab/GitHub API error"**

- Verify token has correct permissions
- Check base URL is accessible
- Review token scopes (api for GitLab, repo for GitHub)

**4. "Token limit exceeded"**

- Increase `max_tokens` in TokenHandler
- Use GPT-4-turbo or Claude for larger context
- Enable automatic chunking (enabled by default)

### Debug Mode

Enable detailed logging:

```python
# app/main.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [tiktoken](https://github.com/openai/tiktoken) - Token counting
- [Typer](https://typer.tiangolo.com/) - CLI framework
- [Rich](https://rich.readthedocs.io/) - Terminal formatting

---

## 📞 Support

- 📧 Email: support@example.com
- 💬 Issues: [GitHub Issues](https://github.com/yourusername/seele-review/issues)
- 📖 Docs: [Documentation](https://docs.example.com)

---

<div align="center">

**Made with ❤️ by the Seele Team**

[⬆ Back to Top](#seele-review-)

</div>
