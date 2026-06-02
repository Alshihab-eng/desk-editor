import os
import json
import anthropic
import requests as http
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
USERS_FILE = os.path.join(DATA_DIR, "registered_users.json")

os.makedirs(DATA_DIR, exist_ok=True)


def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/suggest", methods=["POST"])
def suggest():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    messages = data.get("messages")
    prompt = data.get("prompt")

    if not messages and not prompt:
        return jsonify({"error": "Provide either 'prompt' (string) or 'messages' (array)"}), 400

    if prompt and not messages:
        messages = [{"role": "user", "content": prompt}]

    model = data.get("model", "claude-sonnet-4-6")
    max_tokens = int(data.get("max_tokens", 8192))
    system = data.get("system")
    use_search = bool(data.get("use_search", False))

    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        kwargs["system"] = system
    if use_search:
        kwargs["tools"] = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}]

    message = client.messages.create(**kwargs)

    text_content = " ".join(
        block.text for block in message.content if block.type == "text"
    )

    return jsonify({
        "suggestion": text_content,
        "model": message.model,
        "stop_reason": message.stop_reason,
        "search_used": use_search,
        "usage": {
            "input_tokens": message.usage.input_tokens,
            "output_tokens": message.usage.output_tokens,
        },
    })


@app.route("/api/send-telegram", methods=["POST"])
def send_telegram():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "error": "Request body must be JSON"}), 400

    chat_id = data.get("chat_id")
    message = data.get("message")

    if not chat_id:
        return jsonify({"success": False, "error": "Missing required field: chat_id"}), 400
    if not message:
        return jsonify({"success": False, "error": "Missing required field: message"}), 400

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return jsonify({"success": False, "error": "TELEGRAM_BOT_TOKEN is not configured"}), 500

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = http.post(url, json={"chat_id": chat_id, "text": message}, timeout=10)
        resp.raise_for_status()
        return jsonify({"success": True})
    except http.exceptions.HTTPError as e:
        try:
            detail = resp.json().get("description", str(e))
        except Exception:
            detail = str(e)
        return jsonify({"success": False, "error": detail}), 502
    except http.exceptions.RequestException as e:
        return jsonify({"success": False, "error": str(e)}), 502


@app.route("/api/telegram-webhook", methods=["POST"])
def telegram_webhook():
    update = request.get_json(silent=True)
    if not update:
        return jsonify({"ok": True})

    message = update.get("message") or update.get("edited_message")
    if not message:
        return jsonify({"ok": True})

    text = message.get("text", "")
    chat = message.get("chat", {})
    sender = message.get("from", {})

    chat_id = str(chat.get("id", ""))
    first_name = sender.get("first_name", "")
    last_name = sender.get("last_name", "")
    username = sender.get("username", "")
    full_name = (first_name + " " + last_name).strip() or username or chat_id

    if text.startswith("/start"):
        users = load_users()
        users[chat_id] = {"name": full_name, "username": username, "chat_id": chat_id}
        save_users(users)

        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if token:
            welcome = f"أهلاً {first_name}! 👋\nتم تسجيلك في ديسك التحرير بنجاح.\nسيصلك توزيع مهامك اليومية هنا."
            http.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": welcome},
                timeout=10,
            )

    return jsonify({"ok": True})


@app.route("/api/registered-users", methods=["GET"])
def registered_users():
    users = load_users()
    return jsonify({"users": list(users.values())})


@app.route("/api/setup-webhook", methods=["POST"])
def setup_webhook():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return jsonify({"success": False, "error": "TELEGRAM_BOT_TOKEN is not configured"}), 500

    domains = os.environ.get("REPLIT_DOMAINS", "")
    domain = domains.split(",")[0].strip() if domains else ""
    if not domain:
        return jsonify({"success": False, "error": "Could not detect public domain"}), 500

    webhook_url = f"https://{domain}/api/telegram-webhook"
    try:
        resp = http.post(
            f"https://api.telegram.org/bot{token}/setWebhook",
            json={"url": webhook_url},
            timeout=10,
        )
        resp.raise_for_status()
        result = resp.json()
        return jsonify({"success": result.get("ok", False), "webhook_url": webhook_url, "description": result.get("description", "")})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 502


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
