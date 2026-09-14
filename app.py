import os
import random
import requests
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# 🔒 安全防護：從環境變數讀取密碼
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")

# 🧼 終極強效清洗：自動把 Render 後台不小心按到的任何鍵盤空白、引號通通擦洗乾淨！
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").replace('"', '').replace("'", "").strip()

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 虛擬變數防錯
sheets_client = None
spreadsheet = None
worksheet = None

def ask_gemini(user_text):
    if not GEMINI_API_KEY:
        return "🤖 助理目前缺少 GEMINI_API_KEY，請檢查 Render 後台設定。"
    
    # 使用目前最穩定的官方 v1beta API 管道
    url = f"https://googleapis.com{GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    
    # 帶入你精心挑選的高冷、客觀命理分析師設定
    payload = {
        "contents": [{"parts": [{"text": user_text}]}],
        "systemInstruction": {
            "parts": [{"text": "你是一位專業、有效率的日常生活助手兼客觀命理分析師。請用繁體中文回答使用者的問題或進行占卜算命，不帶多餘的溫柔情感，直接切入核心回答。"}]
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        return response.json()["candidates"]["content"]["parts"]["text"].strip()
    except Exception:
        return "🤖 助理大腦開機中或稍微短路了，請再試一次看看！"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_msg = event.message.text.strip()
    
    # 【功能 1】主選單選單
    if user_msg == "功能" or user_msg.lower() == "menu":
        reply_text = (
            "🤖 歡迎使用 Gemini 智慧助理！\n"
            "直接跟我聊天，我就會用 Google AI 大腦回覆你囉！\n\n"
            "🔮 輸入【塔羅】: 抽取今日運勢\n"
            "🎯 輸入【抽籤 A B】: 幫你做決定"
        )
    # 【功能 2】趣味塔羅牌
    elif "塔羅" in user_msg:
        tarot_cards = ["大天使", "魔術師", "女祭司", "皇后", "皇帝", "教皇", "戀人", "戰車", "力量", "隱者"]
        luck_levels = ["大吉！今天運勢爆棚！", "中吉，按部就班會有大收穫。", "小吉，平穩美好的一天。"]
        reply_text = f"🔮 點擊抽取今日塔羅...\n您的牌：【{random.choice(tarot_cards)}】\n建議：{random.choice(luck_levels)}"
    # 【功能 3】選擇困難症抽籤
    elif user_msg.startswith("抽籤"):
        try:
            options = user_msg.split()[1:]
            reply_text = f"🎯 決定好囉！選這個：【{random.choice(options)}】！" if options else "⚠️ 請給我選項，例如：抽籤 麥當勞 肯德基"
        except:
            reply_text = "⚠️ 格式錯誤，例如：抽籤 A B"
    # 【功能 4】其餘對話一律交給 Gemini AI
    else:
        reply_text = ask_gemini(user_msg)
        
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
