---
name: line-bot-tester
description: >-
  Guides the agent to inspect, validate, and test Python code structure for LINE Messaging API
  (line-bot-sdk) syntax, webhook routing, signature verification, and event handling whenever
  the user asks to "test the bot" or review a LINE bot implementation.
---

# LINE Bot Python SDK Tester

This skill provides step-by-step procedures to inspect, validate, and test Python code using the `line-bot-sdk` (both modern v3.x and legacy v2.x). Use this whenever the user asks to "test the bot" or verify their LINE bot implementation.

---

## 1. Trigger Conditions

Activate and execute the checks in this skill when:
- The user asks to "test the bot", "check the bot", or "verify line bot".
- The user asks for a review or validation of LINE Messaging API code in Python.

---

## 2. Testing & Review Workflow

When triggered, execute the following 5-phase inspection:

```
[1. Locate Code] ➔ [2. Detect SDK Version] ➔ [3. Verify Core Architecture] ➔ [4. Syntax & Static Check] ➔ [5. Report & Test Payload]
```

### Phase 1: Locate Target Files
1. Scan the repository for Python files implementing LINE bot handlers or webhooks (look for imports of `linebot` or framework routes like `/callback` or `/webhook`).
2. Identify dependencies from `requirements.txt`, `pyproject.toml`, or `Pipfile` to check which `line-bot-sdk` version is targeted.

### Phase 2: Detect SDK Version
Identify whether the code is using **v3.x (Modern)** or **v2.x (Legacy)**:

| Component | v3.x (Modular / Recommended) | v2.x (Legacy) |
| :--- | :--- | :--- |
| **Imports** | `linebot.v3`, `linebot.v3.messaging`, `linebot.v3.webhook`, `linebot.v3.webhooks` | `linebot`, `linebot.models` |
| **Handler** | `from linebot.v3.webhook import WebhookHandler` | `from linebot import WebhookHandler` |
| **Exceptions**| `from linebot.v3.exceptions import InvalidSignatureError` | `from linebot.exceptions import InvalidSignatureError` |
| **Client** | `ApiClient`, `MessagingApi`, `Configuration` | `LineBotApi` |
| **Events** | `MessageEvent`, `TextMessageContent` | `MessageEvent`, `TextMessage` |
| **Reply Call**| `messaging_api.reply_message(ReplyMessageRequest(...))` | `line_bot_api.reply_message(event.reply_token, ...)` |

> [!WARNING]
> Flag any mixed imports (e.g., importing `linebot.v3.webhook` alongside legacy `LineBotApi`). Recommend standardizing on v3.x.

---

## 3. Structural Checklist

Check the following critical areas in the code:

### A. Credential Handling
- [ ] Channel Secret and Channel Access Token must be loaded via environment variables (`os.getenv`, `os.environ`, or `.env`), **never hardcoded**.
- [ ] Proper initialization:
  - **v3.x**:
    ```python
    configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
    api_client = ApiClient(configuration)
    messaging_api = MessagingApi(api_client)
    handler = WebhookHandler(LINE_CHANNEL_SECRET)
    ```
  - **v2.x**:
    ```python
    line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
    handler = WebhookHandler(LINE_CHANNEL_SECRET)
    ```

### B. Webhook Endpoint & Signature Verification
- [ ] Webhook route (e.g., `/callback`) accepts HTTP POST requests.
- [ ] Reads the `X-Line-Signature` HTTP header (case-sensitive check depending on framework: Flask uses `request.headers['X-Line-Signature']`, FastAPI uses `Header(alias="x-line-signature")`).
- [ ] Retrieves the raw body as text/bytes (`request.get_data(as_text=True)` in Flask or `await request.body()` in FastAPI).
- [ ] Encloses `handler.handle(body, signature)` in a `try...except InvalidSignatureError` block.
- [ ] Returns HTTP 400 on `InvalidSignatureError`.
- [ ] Returns HTTP 200 (`'OK'` or `Response(status_code=200)`) on success.

### C. Event Handlers & Message Syntax
- [ ] Handlers use correct decorator syntax:
  - **v3.x**:
    ```python
    @handler.add(MessageEvent, message=TextMessageContent)
    def handle_text_message(event):
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="Echo: " + event.message.text)]
            )
        )
    ```
  - **v2.x**:
    ```python
    @handler.add(MessageEvent, message=TextMessage)
    def handle_text_message(event):
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="Echo: " + event.message.text)
        )
    ```
- [ ] Reply tokens: Verify reply tokens are used at most once (they are single-use and expire within seconds).
- [ ] Message objects: Ensure response messages are proper message objects (`TextMessage`, `FlexMessage`, etc.), not raw strings or dicts unless wrapped properly.
- [ ] Long tasks: Flag synchronous long-running operations inside event handlers; suggest background tasks/queues to prevent webhook timeouts (LINE expects 200 OK within 1–2 seconds).

---

## 4. Execution & Validation Steps

1. **Python Syntax Compilation**:
   Run a syntax check on the script:
   ```bash
   python -m py_compile <path/to/bot.py>
   ```
2. **Import & Linter Verification**:
   If available, run `flake8`, `ruff`, or `pylint` on the file to check for undefined variables, unused imports, or incorrect arguments.
3. **Mock Payload Test**:
   When testing webhook execution, construct a mock LINE webhook event payload to verify handler routing:
   ```json
   {
     "destination": "Uxxxxxxxxxxxxxx",
     "events": [
       {
         "type": "message",
         "message": {
           "type": "text",
           "id": "100001",
           "text": "Hello"
         },
         "timestamp": 1625642922000,
         "source": {
           "type": "user",
           "userId": "U0123456789abcdef"
         },
         "replyToken": "nHuyWiB7yP5Zw52FIkcQobQuGDXCTA",
         "mode": "active"
       }
     ]
   }
   ```

---

## 5. Output Report Format

When presenting results to the user, structure the response clearly:

1. **Summary Status**: (e.g., Passed / Issues Found)
2. **SDK Version Detected**: (e.g., `line-bot-sdk v3.x`)
3. **Audit Findings**:
   - **Credentials & Security**: [Status & Notes]
   - **Webhook & Signature**: [Status & Notes]
   - **Event Handlers & Payload Structure**: [Status & Notes]
4. **Code Fixes / Recommendations**: Provide exact diffs or code snippets for any syntax or logic errors found.
