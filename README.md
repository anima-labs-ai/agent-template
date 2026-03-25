# Anima Agent Template

Fork and deploy your own AI agent with email, phone, and card capabilities.

This template creates an AI-powered email agent using [Anima](https://anima.email) + [OpenAI](https://openai.com). It receives incoming emails via webhooks, uses GPT-4o to generate intelligent replies, and sends them back through Anima — all in ~150 lines of Python.

[![Run on Replit](https://replit.com/badge/github/anima-labs/agent-template)](https://replit.com/@anima/agent-template)

---

## Features

- **AI-Powered Replies** — Uses GPT-4o to understand incoming emails and generate contextual responses
- **Anima SDK Integration** — Full email sending/receiving through the Anima Python SDK
- **Webhook Server** — Built-in Flask server to receive real-time email notifications
- **Agent Management** — Automatically creates or retrieves your agent identity
- **Webhook Verification** — Optional signature verification for secure webhook delivery
- **Graceful Fallback** — Works without OpenAI (sends placeholder replies) so you can test the flow
- **Customizable Personality** — Change the system prompt to make your agent a support bot, sales rep, or anything else
- **Deploy Anywhere** — Runs on Replit, Docker, or any Python hosting

## Prerequisites

- **Python 3.9+**
- **Anima API Key** — Sign up at [anima.email](https://anima.email) and get your API key from the dashboard
- **OpenAI API Key** — Get one at [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

## Quick Start

### 1. Clone / Fork

```bash
git clone https://github.com/anima-labs/agent-template.git
cd agent-template
```

Or click **"Use this template"** on GitHub, or **"Run on Replit"** above.

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and fill in your keys:

```env
ANIMA_API_KEY=mk_your_key_here
OPENAI_API_KEY=sk-your_key_here
ANIMA_ORG_ID=org_your_org_id
AGENT_NAME=my-agent
```

### 4. Run

```bash
python main.py
```

The server starts on port 5000 (configurable via `PORT` in `.env`).

### 5. Register Your Webhook

Point Anima to your server's webhook URL. You can do this from the [Anima dashboard](https://anima.email) or via the SDK:

```python
from anima import Anima
from anima.types import CreateWebhookInput, WebhookEvent

client = Anima(api_key="mk_your_key")
client.webhooks.create(
    CreateWebhookInput(
        url="https://your-server.com/webhook",
        events=[WebhookEvent.MESSAGE_RECEIVED],
        description="AI agent email handler",
    )
)
```

> **Tip:** For local development, use [ngrok](https://ngrok.com) to expose your local server: `ngrok http 5000`

## Architecture

```
Incoming Email
      │
      ▼
  Anima Cloud ──webhook──▶ Flask Server (/webhook)
                                │
                                ▼
                        Parse email payload
                                │
                                ▼
                        OpenAI GPT-4o generates reply
                                │
                                ▼
                        Anima SDK sends reply email
                                │
                                ▼
                          Recipient inbox
```

### Key Components

| File | Purpose |
|---|---|
| `main.py` | Agent setup, webhook handler, AI reply generation, email sending |
| `.env.example` | Environment variable template |
| `requirements.txt` | Python dependencies |
| `.replit` / `replit.nix` | Replit deployment config |
| `Dockerfile` | Docker deployment config |

### How It Works

1. **Agent Setup** — On startup, the app searches for an existing agent by name or creates a new one via `client.agents.create()`
2. **Webhook Listening** — Flask serves `POST /webhook` to receive Anima events
3. **Email Processing** — When a `message.received` event arrives, the handler extracts sender, subject, and body
4. **AI Generation** — The email content is sent to GPT-4o with a customizable system prompt
5. **Reply Sending** — The AI-generated reply is sent back via `client.messages.send_email()`

## Customization

### Change the AI Personality

Set the `SYSTEM_PROMPT` environment variable or edit it in `main.py`:

```env
SYSTEM_PROMPT=You are a customer support agent for Acme Corp. Be helpful and reference our docs at docs.acme.com when relevant.
```

### Use a Different LLM

Replace the OpenAI call in `generate_reply()` with any LLM provider:

```python
# Example: Anthropic Claude
from anthropic import Anthropic
client = Anthropic()
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[{"role": "user", "content": prompt}],
)
```

### Add More Capabilities

The Anima SDK supports more than email. Extend your agent with:

```python
# Send SMS
from anima.types import SendSmsInput
client.messages.send_sms(
    SendSmsInput(agentId=agent_id, to="+15551234567", body="Hello via SMS!")
)

# Provision a phone number
from anima.types import ProvisionPhoneInput
client.agents.provision_phone(
    ProvisionPhoneInput(agentId=agent_id, countryCode="US")
)
```

### Handle Multiple Event Types

Extend the webhook handler to process different events:

```python
@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.get_json()
    event = payload.get("event", "")

    if event == "message.received":
        handle_incoming_email(payload)
    elif event == "message.sent":
        log_sent_message(payload)
    elif event == "message.failed":
        handle_delivery_failure(payload)

    return jsonify({"ok": True})
```

## Deployment

### Replit

1. Fork this repo on Replit
2. Add your API keys as Replit Secrets
3. Click **Run** — the `.replit` config handles everything

### Docker

```bash
docker build -t anima-agent .
docker run -p 5000:5000 --env-file .env anima-agent
```

### Railway / Fly.io / Render

These platforms auto-detect the `Dockerfile`. Just connect your repo, set environment variables, and deploy.

## API Reference

- **Anima SDK** — [docs.anima.email](https://docs.anima.email)
- **OpenAI API** — [platform.openai.com/docs](https://platform.openai.com/docs)

## License

MIT
