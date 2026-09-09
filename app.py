import random

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
    user_msg = event.message.text.strip() # 去除可能不小心打到的空格
    
    # 1. 判斷是不是要「抽牌」（包含只要訊息裡有提到抽牌兩個字就觸發）
    if "抽牌" in user_msg or "占卜" in user_msg:
        tarot_cards = [
            "愚者", "魔術師", "女祭司", "女皇", "皇帝", "教皇", "戀人", "戰車", "力量", "隱士", 
            "命運之輪", "正義", "倒吊人", "死神", "節制", "惡魔", "高塔", "星星", "月亮", "太陽", 
            "審判", "世界",
            "權杖一", "權杖二", "權杖三", "權杖四", "權杖五", "權杖六", "權杖七", "權杖八", "權杖九", "權杖十", "權杖侍從", "權杖騎士", "權杖皇后", "權杖國王",
            "聖杯一", "聖杯二", "聖杯三", "聖杯四", "聖杯五", "聖杯六", "聖杯七", "聖杯八", "聖杯九", "聖杯十", "聖杯侍從", "聖杯騎士", "聖杯皇后", "聖杯國王",
            "寶劍一", "寶劍二", "寶劍三", "寶劍四", "寶劍五", "寶劍六", "寶劍七", "寶劍八", "寶劍九", "寶劍十", "寶劍侍從", "寶劍騎士", "寶劍皇后", "寶劍國王",
            "金幣一", "金幣二", "金幣三", "金幣四", "金幣五", "金幣六", "金幣七", "金幣八", "金幣九", "金幣十", "金幣侍從", "金幣騎士", "金幣皇后", "金幣國王"
        ]
        chosen_card = random.choice(tarot_cards)
        position = random.choice(["正位", "逆位"])
        
        try:
            response = gemini_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=f"我剛剛抽到了塔羅牌的【{chosen_card}（{position}）】。請針對這張特定的牌，為我目前的現況、或是提問給予詳細且有智慧的解牌占卜。",
                config=types.GenerateContentConfig(
                    system_instruction="你是一位精通塔羅牌與神秘學的專業占卜師。請根據使用者提供的『特定卡牌與正逆位』，用溫慢、充滿啟發性的繁體中文為其進行專業的解牌。"
                )
            )
            reply_text = response.text
        except Exception as e:
            reply_text = "哎呀，我的水晶球現在有點模糊，請稍後再試試看。"
            
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
        return

    # 2. 如果不是要抽牌，不論使用者打「您好」、「嗨」還是聊任何天，都一律交給 Gemini AI 聊天解惑！
    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_msg,
            config=types.GenerateContentConfig(
                system_instruction="你是一位精通塔羅牌與神秘學的專業占卜師，同時也是使用者的『智慧雙重身分助理』，說話語氣溫暖、神秘、幽默且富有智慧。不論使用者跟你聊什麼，你都要用溫暖的繁體中文熱情、聰明地回應他們，引導他們傾訴，有需要時也可以主動提議幫他們抽牌占卜。"
            )
        )
        reply_text = response.text
    except Exception as e:
        print(f"Gemini 發生錯誤: {e}")
        reply_text = "我好像恍神了一下，可以請你再對我說一次嗎？"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
