import json
import logging
import os
import re
import threading
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, abort, jsonify, request
import google.generativeai as genai
import requests
from linebot.v3.webhook import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

# Load local environment variables if available
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Load configuration from environment variables
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
MAKE_WEBHOOK_URL = os.getenv(
    "MAKE_WEBHOOK_URL",
    "https://hook.us2.make.com/lea7buy6ose2xc3g87h1tsz68l4f7wh7",
)

# Setup LINE Bot SDK v3 configuration and handler
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# Configure Google Generative AI
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY is not set. Gemini responses will be disabled or simulated.")

# System prompt defining bot personas and behavior
SYSTEM_INSTRUCTION = """
You are an intelligent dual-purpose LINE Bot assistant specializing in two distinct roles:

[ROLE 1: MYSTERIOUS TAROT MASTER (塔羅占卜師)]
- Trigger: The user asks about fortune-telling, Tarot, divination, destiny, cards, love advice, future predictions, or horoscopes (e.g. "抽一張塔羅牌", "占卜工作運", "今天運勢如何").
- Persona: An enigmatic, mystical, and deeply intuitive Tarot Master. Speak poetically and warmly with esoteric wisdom.
- Behavior:
  1. Symbolically draw 1 Tarot card (mention card name and whether it is Upright 正位 or Reversed 逆位).
  2. Reveal its esoteric imagery and deeper psychological / spiritual meaning.
  3. Provide concrete, uplifting guidance.
  4. Use mystical emojis (🔮, 🃏, ✨, 🌙, 🪐, 🕯️).

[ROLE 2: SMART FINANCE TRACKER (記帳管家)]
- Trigger: The user enters an expense, budget, or purchase (e.g. "Lunch 120", "午餐 120", "Coffee 80", "買衣服 1500", "搭計程車 260").
- Persona: A clean, organized, and helpful personal finance tracker.
- Behavior:
  Parse the input into a structured expense receipt with this format:
  📝【記帳確認】
  • 項目：[Extracted item/description]
  • 金額：$[Extracted amount]
  • 類別：[Inferred category e.g., 飲食 / 交通 / 娛樂 / 購物 / 居住 / 醫療]
  • 狀態：已成功記錄（已同步至雲端試算表）
  💡 財務筆記：[A short 1-sentence supportive budget tip]

  CRITICAL: At the very end of your response, append this hidden machine-readable tag with the extracted values:
  <!--EXPENSE_DATA:{"item": "[Extracted item]", "amount": [Extracted amount as number], "category": "[Inferred category]"}-->

[ROLE 3: GENERAL / FALLBACK]
- Trigger: Any message that is not Tarot or finance tracking.
- Persona: Friendly, witty assistant.
- Behavior: Provide a brief, engaging answer and kindly invite the user to try:
  🔮 占卜塔羅（輸入「抽一張塔羅牌」或「測財運」）
  💰 快速記帳（輸入「午餐 120」或「咖啡 85」）
"""


def send_expense_to_make(payload: dict):
    """Asynchronously forward parsed expense to Make.com webhook."""
    if not MAKE_WEBHOOK_URL:
        logger.warning("MAKE_WEBHOOK_URL is not configured; skipping sync.")
        return

    try:
        logger.info(f"Syncing expense to Make.com: {payload}")
        response = requests.post(MAKE_WEBHOOK_URL, json=payload, timeout=5)
        logger.info(f"Make.com response [{response.status_code}]: {response.text[:100]}")
    except Exception as e:
        logger.error(f"Failed to post expense to Make.com: {e}")


def dispatch_make_webhook(item: str, amount: float, category: str, raw_text: str, user_id: str):
    """Helper to dispatch expense payload to Make.com in a separate background thread."""
    payload = {
        "userId": user_id or "anonymous",
        "item": item,
        "amount": amount,
        "category": category,
        "rawText": raw_text,
        "timestamp": datetime.utcnow().isoformat(),
    }
    threading.Thread(target=send_expense_to_make, args=(payload,), daemon=True).start()


def generate_bot_response(user_text: str, user_id: str = "") -> str:
    """Generate response based on user input intent via Google Gemini API and sync expenses."""
    if not GEMINI_API_KEY:
        # Fallback if API key is not configured
        return handle_offline_fallback(user_text, user_id)

    try:
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=SYSTEM_INSTRUCTION,
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 800,
            },
        )
        response = model.generate_content(user_text)
        if response and response.text:
            text = response.text.strip()

            # Check if Gemini extracted expense data
            match = re.search(r"<!--EXPENSE_DATA:(.*?)-->", text, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1).strip())
                    item = data.get("item", "未指定項目")
                    amount = float(data.get("amount", 0))
                    category = data.get("category", "日常支出")
                    dispatch_make_webhook(item, amount, category, user_text, user_id)
                except Exception as ex:
                    logger.error(f"Failed to parse EXPENSE_DATA from Gemini: {ex}")

                # Clean the hidden tag before sending to LINE user
                text = re.sub(r"<!--EXPENSE_DATA:(.*?)-->", "", text).strip()

            return text

        return "🔮 星象迷霧籠罩，請稍後再試一次..."
    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}", exc_info=True)
        return handle_offline_fallback(user_text, user_id)


def handle_offline_fallback(user_text: str, user_id: str = "") -> str:
    """Deterministic fallback in case Gemini API is unavailable or unconfigured."""
    cleaned = user_text.strip()

    # Fast pattern match for finance/expense: e.g. "Lunch 120" or "午餐 120"
    match = re.search(r"^(.*?)\s*[$￥]?\s*(\d+(?:\.\d+)?)\s*$", cleaned)
    if match:
        item = match.group(1).strip() or "日常花費"
        amount = float(match.group(2).strip())
        category = "飲食" if any(k in item for k in ["餐", "吃", "飯", "麵", "茶", "咖", "酒", "肉"]) else "日常支出"

        # Dispatch to Make.com
        dispatch_make_webhook(item, amount, category, user_text, user_id)

        return (
            f"📝【記帳確認】\n"
            f"• 項目：{item}\n"
            f"• 金額：${amount:g}\n"
            f"• 類別：{category}\n"
            f"• 狀態：已成功記錄（已同步至雲端試算表）\n\n"
            f"💡 每一筆紀錄，都是通往財富自由的一小步！"
        )

    # Keywords for Tarot / Fortune
    tarot_keywords = ["塔羅", "占卜", "運勢", "算命", "抽牌", "tarot", "fortune"]
    if any(k in cleaned.lower() for k in tarot_keywords):
        return (
            "🔮【命運之輪．塔羅指引】\n\n"
            "🃏 抽出的卡牌：【星星 (The Star)】— 正位\n"
            "✨ 牌面解讀：象徵希望、靈感與內心的清澈指引。即使黑夜漫長，指引之星始終照耀前路。\n"
            "🌙 大師寄語：相信自己的直覺與潛力，當下的付出將在不久的未來綻放光芒。"
        )

    return (
        "您好！我是您的智慧雙重身分助理 ✨\n\n"
        "您可以輸入：\n"
        "🔮 塔羅占卜：例如「抽一張塔羅牌」或「占卜今日運勢」\n"
        "💰 快速記帳：例如「午餐 120」或「咖啡 75」"
    )


@app.route("/", methods=["GET"])
def index():
    """Health check endpoint for Render and monitoring."""
    return jsonify(
        {
            "status": "healthy",
            "service": "LINE Bot (Tarot & Expense Tracker)",
            "makeWebhookConfigured": bool(MAKE_WEBHOOK_URL),
            "timestamp": datetime.utcnow().isoformat(),
        }
    ), 200


@app.route("/callback", methods=["POST"])
def callback():
    """LINE Webhook callback endpoint."""
    signature = request.headers.get("X-Line-Signature")
    if not signature:
        logger.warning("Missing X-Line-Signature header")
        abort(400)

    body = request.get_data(as_text=True)
    logger.info(f"Received webhook request: {body[:150]}...")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.error("Invalid signature encountered from LINE webhook.")
        abort(400)
    except Exception as e:
        logger.error(f"Unexpected error handling webhook: {e}", exc_info=True)
        abort(500)

    return "OK", 200


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event: MessageEvent):
    """Handle incoming text messages from LINE users."""
    user_text = event.message.text
    user_id = getattr(event.source, "user_id", "")
    logger.info(f"Processing message from {user_id}: {user_text}")

    # Generate response based on intent (Tarot master vs Finance tracker)
    reply_text = generate_bot_response(user_text, user_id=user_id)

    # Send reply using LINE Messaging API Client
    try:
        with ApiClient(configuration) as api_client:
            messaging_api = MessagingApi(api_client)
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_text)],
                )
            )
            logger.info("Successfully sent reply message to LINE.")
    except Exception as e:
        logger.error(f"Failed to send LINE reply: {e}", exc_info=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting server on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
