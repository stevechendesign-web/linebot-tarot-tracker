# LINE Bot: Tarot Master & Finance Tracker 🔮💰

A Python-based LINE Bot powered by **Flask**, **line-bot-sdk (v3)**, and **Google Generative AI (Gemini)**.

---

## 🌟 Features

1. **🔮 Mysterious Tarot Master (塔羅占卜師)**:
   - When the user asks about Tarot, fortune-telling, love, future, or requests a card reading (e.g., "抽一張塔羅牌", "占卜工作運", "今天運勢"), the bot channels an enigmatic Tarot Master persona, symbolically drawing a card (Upright/Reversed) and delivering deep interpretations and spiritual wisdom.

2. **💰 Smart Finance Tracker (智慧記帳管家)**:
   - When the user inputs expenses or budgets (e.g., "Lunch 120", "午餐 120", "Coffee 65", "計程車 250"), the bot parses the item, amount, category, and confirms with a clean financial ledger receipt.

3. **✨ Intelligent Fallback**:
   - Uses Gemini AI for dynamic natural language understanding, with a built-in offline fallback if the API is momentarily unavailable.

---

## 📁 Project Structure

```text
├── app.py                # Main Flask application & LINE Webhook handler
├── requirements.txt      # Python dependencies
├── Procfile              # Entry point for Render deployment (gunicorn app:app)
├── .env.example          # Template for environment variables
└── README.md             # Setup and deployment documentation
```

---

## 🚀 Deployment to Render

### 1. Push code to GitHub
Push this repository to your GitHub account.

### 2. Create a Web Service on Render
1. Go to [Render Dashboard](https://dashboard.render.com/) and click **New +** -> **Web Service**.
2. Connect your GitHub repository.
3. Configure the service settings:
   - **Name**: `my-tarot-linebot` (or your preferred name)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app` (Render reads this from `Procfile` automatically)

### 3. Add Environment Variables on Render
Under the **Environment** tab in your Render service, add:

| Key | Description | Example |
| :--- | :--- | :--- |
| `LINE_CHANNEL_SECRET` | From LINE Developers Console | `7a8b...` |
| `LINE_CHANNEL_ACCESS_TOKEN` | Long-lived token from LINE Developers Console | `vWxyz...` |
| `GEMINI_API_KEY` | From Google AI Studio | `AIzaSy...` |
| `MAKE_WEBHOOK_URL` | *(Optional)* Make.com Webhook URL for expense sync | `https://hook.us2.make.com/...` |
| `GEMINI_MODEL` | *(Optional)* Default is `gemini-1.5-flash` | `gemini-1.5-flash` |

### 4. Configure Webhook on LINE Developers Console
1. Once deployed on Render, copy your service URL (e.g. `https://my-tarot-linebot.onrender.com`).
2. Go to [LINE Developers Console](https://developers.line.biz/) -> your Messaging API channel -> **Messaging API** tab.
3. Set **Webhook URL** to:
   ```
   https://your-service-name.onrender.com/callback
   ```
4. Click **Verify** to test connection.
5. Enable **Use webhook**.
6. Disable **Auto-reply messages** in LINE Official Account settings to let the bot respond directly.

---

## 💻 Local Development

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your keys:
   ```bash
   cp .env.example .env
   ```
4. Start the application:
   ```bash
   python app.py
   ```
5. Use [ngrok](https://ngrok.com/) to expose port 5000 for local LINE webhook testing:
   ```bash
   ngrok http 5000
   ```
