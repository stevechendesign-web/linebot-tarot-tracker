import os
import random
import threading
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from google import genai
from google.genai import types

app = Flask(__name__)

# LINE 憑證與 Gemini 客戶端初始化
line_bot_api = LineBotApi(os.environ.get('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET'))
gemini_client = genai.Client()

# 記憶體內儲存（注意：Render 免費方案重啟時會清空，僅供簡易操作）
TODO_LIST = {}  # 格式: {user_id: ["任務1", "任務2"]}
EXPENSES = {}   # 格式: {user_id: [{"item": "午餐", "amount": 120}]}

# 定時提醒回呼函式
def send_reminder(user_id, message_text):
    try:
        line_bot_api.push_message(user_id, TextSendMessage(text=f"⏰ 【定時提醒】時間到囉！您的提醒事項：{message_text}"))
    except Exception as e:
        print(f"發送提醒失敗: {e}")

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
    user_id = event.source.user_id
    user_msg = event.message.text.strip()
    
    # -----------------------------------------------------------------
    # 【功能 1】鬧鐘與定時提醒 (格式：提醒我 10 分鐘後 關瓦斯)
    # -----------------------------------------------------------------
    if user_msg.startswith("提醒我") and "分鐘後" in user_msg:
        try:
            parts = user_msg.split("分鐘後")
            minutes = int(parts[0].replace("提醒我", "").strip())
            reminder_content = parts[1].strip()
            
            seconds = minutes * 60
            t = threading.Timer(seconds, send_reminder, args=[user_id, reminder_content])
            t.start()
            
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"✅ 已為您設定提醒：{minutes} 分鐘後通知您「{reminder_content}」。"))
            return
        except Exception:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="❌ 提醒設定失敗。請使用格式：提醒我 5 分鐘後 收衣服"))
            return

    # -----------------------------------------------------------------
    # 【功能 2】宮廟抽籤與擲筊
    # -----------------------------------------------------------------
    if user_msg == "抽籤":
        dice = random.choice(["聖筊", "笑筊", "陰筊"])
        if dice != "聖筊":
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"☯️ 您向神明求籤，但擲出【{dice}】。神明目前未應允，請調整心情再試一次。"))
            return
        
        fortunes = [
            "第一籤【大吉】甲子：日出東方照大地，萬事亨通福祿臨。求財得財，病體安康。",
            "第十籤【下下】癸酉：病中若得苦心勞，到底完全總未遭。多行善事，以求改運。",
            "第二四籤【中平】丁亥：月出光輝本清吉，浮雲總是蔽其明。耐守時運，自得安泰。",
            "第三六籤 trick【上籤】己亥：福如東海壽如山，君爾何須嘆苦艱。命內自然逢大吉，茅屋亦可變成官。"
        ]
        chosen_fortune = random.choice(fortunes)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"☯️ 擲出【聖筊】！神明賜籤如下：\n\n{chosen_fortune}"))
        return

    # -----------------------------------------------------------------
    # 【功能 3】真·隨機塔羅牌
    # -----------------------------------------------------------------
    if user_msg == "抽牌" or user_msg == "塔羅牌":
        tarot_cards = ["愚者", "魔術師", "女祭司", "女皇", "皇帝", "教皇", "戀人", "戰車", "力量", "死神", "太陽", "世界"]
        chosen_card = random.choice(tarot_cards)
        position = random.choice(["正位", "逆位"])
        
        try:
            response = gemini_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=f"我抽到了塔羅牌的【{chosen_card}（{position}）】。請針對這張牌，為我目前的現況給予客觀、直接、簡潔的命理分析。",
                config=types.GenerateContentConfig(
                    system_instruction="你是一位客觀、專業、講話直接效率的命理大師。請根據特定卡牌，提供直白不煽情的解牌分析。"
                )
            )
            reply_text = response.text
        except Exception:
            reply_text = "系統忙碌中，請稍後重試。"
            
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
        return

    # -----------------------------------------------------------------
    # 【功能 4】待辦清單 (格式：待辦 買牛奶 / 查詢待辦)
    # -----------------------------------------------------------------
    if user_msg.startswith("待辦"):
        todo_item = user_msg.replace("待辦", "").strip()
        if user_id not in TODO_LIST:
            TODO_LIST[user_id] = []
        TODO_LIST[user_id].append(todo_item)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🗒️ 已為您記錄待辦事項：{todo_item}"))
        return
        
    if user_msg == "查詢待辦":
        user_todos = TODO_LIST.get(user_id, [])
        if not user_todos:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🗒️ 目前沒有待辦事項。"))
        else:
            list_text = "\n".join([f"{i+1}. {task}" for i, task in enumerate(user_todos)])
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🗒️ 您的待辦清單：\n{list_text}"))
        return

    # -----------------------------------------------------------------
    # 【功能 5】簡易記帳功能 (格式：記帳 午餐 120 / 查詢記帳)
    # -----------------------------------------------------------------
    if user_msg.startswith("記帳"):
        try:
            parts = user_msg.split()
            item = parts[1]
            amount = int(parts[2])
            if user_id not in EXPENSES:
                EXPENSES[user_id] = []
            EXPENSES[user_id].append({"item": item, "amount": amount})
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"💰 已記錄消費：{item} 共 {amount} 元。"))
            return
        except Exception:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="❌ 記帳失敗。請使用格式：記帳 午餐 120"))
            return

    if user_msg == "查詢記帳":
        user_expenses = EXPENSES.get(user_id, [])
        if not user_expenses:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="💰 目前沒有記帳紀錄。"))
        else:
            total = sum(e["amount"] for e in user_expenses)
            list_text = "\n".join([f"· {e['item']}: ${e['amount']}" for e in user_expenses])
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"💰 歷史消費紀錄：\n{list_text}\n----\n總計：${total} 元"))
        return

    # -----------------------------------------------------------------
    # 【功能 6】其餘對話一律交給 Gemini AI (正常效率對話)
    # -----------------------------------------------------------------
    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_msg,
            config=types.GenerateContentConfig(
                system_instruction="你是一位專業、有效率的日常生活助手兼客觀命理分析師。請用繁體中文回答使用者的問題或進行占卜算命，不帶多餘的溫柔情感，直接切入核心回答。"
            )
        )
        reply_text = response.text
    except Exception:
        reply_text = "暫時無法提供回覆。"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
