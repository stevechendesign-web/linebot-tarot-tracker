import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
# 引入新版 Gemini SDK
from google import genai
from google.genai import types

app = Flask(__name__)

# 讀取 LINE 的環境變數
line_bot_api = LineBotApi(os.environ.get('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET'))

# 初始化 Gemini 客戶端（它會自動去讀 Render 上的 GEMINI_API_KEY）
gemini_client = genai.Client()

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
    user_msg = event.message.text
    
    # 這是原本的抽牌關鍵字邏輯
    if user_msg == "抽牌" or user_msg == "紀錄":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="抽牌功能目前正常運作中！"))
        return
        
    # 如果使用者不是輸入特定的指令，就交給 Gemini AI 扮演塔羅占卜師回答
    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_msg,
            config=types.GenerateContentConfig(
                system_instruction="你是一位精通塔羅牌與神祕學的專業占卜師，說話語氣溫暖、神秘且富有智慧。請用繁體中文回答使用者的問題或幫他們解牌。"
            )
        )
        reply_text = response.text
    except Exception as e:
        print(f"Gemini API 發生錯誤: {e}")
        reply_text = "哎呀，我的水晶球現在有點模糊，請稍後再問我一次。"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
