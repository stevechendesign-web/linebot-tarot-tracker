import os
import random
import threading
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from google import genai
from google.genai import types

app = Flask(__name__)

# -----------------------------------------------------------------
# 🔐 設定 Google 試算表雲端連線權限 (終極自動換行與外殼修復寫法)
# -----------------------------------------------------------------
#scope = ["https://google.com", "https://googleapis.com"]

#raw_key = os.environ.get("GOOGLE_KEY_JSON_CONTENT")

#if raw_key:
    # 🧼 第一步：把不小心複製到的空白、引號、換行符號全部剔除乾淨
#    clean_key = raw_key.replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "")
#    clean_key = clean_key.replace("\n", "").replace("\r", "").replace(" ", "").strip()
    
    # 📐 第二步：核心破關！每 64 個字元強迫換行一次，完全對齊 Base64 標準規格
#    formatted_key = ""
#    for i in range(0, len(clean_key), 64):
#        formatted_key += clean_key[i:i+64] + "\n"
        
    # 🛡️ 第三步：自動穿上 Google 官方規定的標準 PEM 安全防護外殼
#    final_private_key = f"-----BEGIN PRIVATE KEY-----\n{formatted_key}-----END PRIVATE KEY-----\n"
    
#    info = {
#     "type": "service_account",
#        "project_id": os.environ.get("GOOGLE_PROJECT_ID", "你的專案ID"),
#        "private_key_id": os.environ.get("GOOGLE_PRIVATE_KEY_ID", "你的私鑰ID"),
#        "private_key": final_private_key,
#        "client_email": os.environ.get("GOOGLE_CLIENT_EMAIL", "你的服務帳號Email"),
#        "client_id": os.environ.get("GOOGLE_CLIENT_ID", "你的客戶端ID"),
#        "auth_uri": "https://google.com",
#        "token_uri": "https://googleapis.com",
#        "auth_provider_x509_cert_url": "https://googleapis.com",
#        "client_x509_cert_url": os.environ.get("GOOGLE_CLIENT_X509_CERT_URL", "你的證書網址")
#    }
    
#    creds = ServiceAccountCredentials.from_json_keyfile_dict(info, scope)
#    sheets_client = gspread.authorize(creds)
#else:
#    print("⚠️ 錯誤：Render 後台未偵測到 GOOGLE_KEY_JSON_CONTENT 環境變數！")
# 🟢 臨時救火線：給系統一個空的 sheets_client，防止下方程式找不到變數而閃退當機！
sheets_client = None
# 🟢 臨時救火線2：給系統一個空的 spreadsheet，防止下方程式找不到變數而閃退！
spreadsheet = None


# 📂 自動打開你的 Google 雲端試算表
try:
#    spreadsheet = sheets_client.open("LINE助理資料庫")
#    expense_sheet = spreadsheet.worksheet("記帳")
#    todo_sheet = spreadsheet.worksheet("待辦")
except Exception as e:
    print(f"Google 試算表連線失敗: {e}")

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
    # 【功能 4】雲端同步版：待辦清單 (格式：待辦 22:00 倒垃圾 / 查詢待辦)
    # -----------------------------------------------------------------
    if user_msg.startswith("待辦"):
        try:
            content = user_msg.replace("待辦", "").strip()
            parts = content.split(maxsplit=1)
            
            if len(parts) == 2:
                todo_time = parts[0]     # 擷取時間，例如：22:00
                todo_task = parts[1]     # 擷取任務，例如：倒垃圾
            else:
                todo_time = "未設定"
                todo_task = content
                
            today_date = datetime.now().strftime("%Y-%m-%d")
            
            # 🚀 同步寫入 Google 試算表「待辦」分頁
            todo_sheet.append_row([today_date, todo_time, todo_task])
            
            line_bot_api.reply_message(
                event.reply_token, 
                TextSendMessage(text=f"🗒️ [雲端同步] 已記錄待辦事項：\n時間：{todo_time}\n任務：{todo_task}")
            )
            return
        except Exception as e:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="❌ 雲端待辦儲存失敗。"))
            return
            
    if user_msg == "查詢待辦":
        try:
            all_records = todo_sheet.get_all_values()
            if len(all_records) <= 1:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🗒️ 目前雲端沒有待辦事項。"))
            else:
                list_items = []
                for i, row in enumerate(all_records[1:]):
                    list_items.append(f"{i+1}. [{row[1]}] {row[2]}")
                list_text = "\n".join(list_items)
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"🗒️ 您的雲端待辦清單：\n{list_text}"))
            return
        except Exception:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="❌ 無法讀取雲端待辦清單。"))
            return


        # -----------------------------------------------------------------
    # 【功能 5】雲端同步版：記帳功能 (格式：記帳 午餐 120 / 查詢記帳)
    # -----------------------------------------------------------------
    if user_msg.startswith("記帳"):
        try:
            parts = user_msg.split()
            item = parts[1]
            amount = int(parts[2])
            today_date = datetime.now().strftime("%Y-%m-%d")
            
            # 🚀 同步寫入 Google 試算表「記帳」分頁
            expense_sheet.append_row([today_date, item, amount])
            
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"💰 [雲端同步] 已記錄消費：{item} 共 {amount} 元。"))
            return
        except Exception:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="❌ 記帳失敗。請使用格式：記帳 午餐 120"))
            return

    if user_msg == "查詢記帳":
        try:
            all_records = expense_sheet.get_all_values()
            if len(all_records) <= 1:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="💰 目前雲端沒有記帳紀錄。"))
            else:
                total = 0
                list_items = []
                for row in all_records[1:]:
                    total += int(row[2])
                    list_items.append(f"· {row[1]}: ${row[2]}")
                list_text = "\n".join(list_items)
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"💰 雲端消費紀錄：\n{list_text}\n----\n總計：${total} 元"))
            return
        except Exception:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="❌ 無法讀取雲端記帳紀錄。"))
            return


         # -----------------------------------------------------------------
    # 【功能 6】其餘對話一律交給 Gemini AI (正常效率對話)
    # -----------------------------------------------------------------
    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_msg,
            # 🟢 修正為標準字典格式，免去引用錯誤，Render 絕對不卡死！
            config={
                'system_instruction': "你是一位專業、有效率的日常生活助手兼客觀命理分析師。請用繁體中文回答使用者的問題或進行占卜算命，不帶多餘的溫柔情感，直接切入核心回答。"
            }
        )
        reply_text = response.text
    except Exception:
        reply_text = "暫時無法提供回覆。"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

