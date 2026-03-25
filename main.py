"""
Anima Agent Template — AI Email Agent

A starter template that creates an AI-powered email agent using Anima + OpenAI.
The agent receives incoming emails via webhooks and uses GPT-4 to generate
intelligent replies, then sends them back through Anima.

Usage:
    1. Copy .env.example to .env and fill in your API keys
    2. pip install -r requirements.txt
    3. python main.py
"""

import logging
import os
import sys

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request

from anima import Anima
from anima.types import CreateAgentInput, SendEmailInput

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ANIMA_API_KEY = os.getenv("ANIMA_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
AGENT_NAME = os.getenv("AGENT_NAME", "my-agent")
ORG_ID = os.getenv("ANIMA_ORG_ID", "")
PORT = int(os.getenv("PORT", "5000"))
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

# The system prompt that defines your agent's personality and behavior.
# Customize this to change how your agent responds to emails.
SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    (
        "You are a helpful AI assistant that responds to emails. "
        "Be concise, professional, and friendly. "
        "If you don't know the answer to something, say so honestly."
    ),
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------

anima = Anima(api_key=ANIMA_API_KEY)

try:
    from openai import OpenAI

    openai_client = OpenAI(api_key=OPENAI_API_KEY)
except ImportError:
    logger.warning("openai package not installed — AI replies disabled")
    openai_client = None

# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Agent setup
# ---------------------------------------------------------------------------


def get_or_create_agent() -> dict:
    """Retrieve an existing agent by name, or create a new one."""
    slug = AGENT_NAME.lower().replace(" ", "-")

    # Check if agent already exists
    existing = anima.agents.list(query=AGENT_NAME, limit=5)
    for agent in existing.items:
        if agent.slug == slug:
            logger.info("Found existing agent: %s (%s)", agent.name, agent.id)
            return {"id": agent.id, "name": agent.name, "slug": agent.slug}

    # Create a new agent
    logger.info("Creating new agent: %s", AGENT_NAME)
    agent = anima.agents.create(
        CreateAgentInput(
            orgId=ORG_ID,
            name=AGENT_NAME,
            slug=slug,
        )
    )
    logger.info("Created agent: %s (%s)", agent.name, agent.id)
    return {"id": agent.id, "name": agent.name, "slug": agent.slug}


# ---------------------------------------------------------------------------
# AI reply generation
# ---------------------------------------------------------------------------


def generate_reply(sender: str, subject: str, body: str) -> str:
    """Use OpenAI GPT-4 to generate a reply to an incoming email."""
    if openai_client is None:
        return f"Thank you for your email regarding '{subject}'. I received your message and will get back to you soon."

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"You received an email from {sender}.\n"
                        f"Subject: {subject}\n\n"
                        f"{body}\n\n"
                        "Write a helpful reply to this email."
                    ),
                },
            ],
            max_tokens=1024,
            temperature=0.7,
        )
        return response.choices[0].message.content or "Thank you for your email."
    except Exception as exc:
        logger.error("OpenAI error: %s", exc)
        return f"Thank you for your email regarding '{subject}'. I received your message and will get back to you soon."


# ---------------------------------------------------------------------------
# Email handling
# ---------------------------------------------------------------------------


def handle_incoming_email(payload: dict) -> None:
    """Process an incoming email and send an AI-generated reply."""
    message = payload.get("data", payload)

    direction = message.get("direction", "")
    if direction == "OUTBOUND":
        logger.debug("Skipping outbound message")
        return

    agent_id = message.get("agentId", "")
    sender = message.get("fromAddress", "unknown")
    subject = message.get("subject", "(no subject)")
    body = message.get("body", "")
    message_id = message.get("id", "")

    logger.info("Incoming email from %s — subject: %s", sender, subject)

    # Generate AI reply
    reply_body = generate_reply(sender, subject, body)

    # Send reply via Anima
    try:
        sent = anima.messages.send_email(
            SendEmailInput(
                agentId=agent_id,
                to=[sender],
                subject=f"Re: {subject}",
                body=reply_body,
            )
        )
        logger.info("Reply sent to %s (message %s)", sender, sent.id)
    except Exception as exc:
        logger.error("Failed to send reply: %s", exc)


# ---------------------------------------------------------------------------
# Webhook routes
# ---------------------------------------------------------------------------


@app.route("/webhook", methods=["POST"])
def webhook():
    """Handle incoming Anima webhook events."""
    # Optional: verify webhook signature
    if WEBHOOK_SECRET:
        signature = request.headers.get("X-Anima-Signature", "")
        try:
            anima.webhooks.verify(
                payload=request.get_data(as_text=True),
                signature=signature,
                secret=WEBHOOK_SECRET,
            )
        except Exception:
            logger.warning("Invalid webhook signature")
            return Response("Invalid signature", status=401)

    payload = request.get_json(silent=True)
    if not payload:
        return Response("Bad request", status=400)

    event_type = payload.get("event", "")
    logger.info("Webhook event: %s", event_type)

    if event_type == "message.received":
        handle_incoming_email(payload)

    return jsonify({"ok": True})


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "agent": AGENT_NAME})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Initialize the agent and start the webhook server."""
    if not ANIMA_API_KEY:
        logger.error("ANIMA_API_KEY is not set. Copy .env.example to .env and add your key.")
        sys.exit(1)

    # Set up the agent
    agent = get_or_create_agent()
    logger.info("Agent ready: %s (%s)", agent["name"], agent["id"])

    if not OPENAI_API_KEY:
        logger.warning(
            "OPENAI_API_KEY is not set — the agent will send placeholder replies. "
            "Add your OpenAI key to .env for AI-powered responses."
        )

    # Start the Flask webhook server
    logger.info("Starting webhook server on port %d ...", PORT)
    logger.info("Webhook URL: http://0.0.0.0:%d/webhook", PORT)
    logger.info(
        "Register this URL in your Anima dashboard or use the SDK to create a webhook."
    )
    app.run(host="0.0.0.0", port=PORT, debug=False)


if __name__ == "__main__":
    main()
