import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# Render 部署腳本 (Render Deploy Trigger Script)
#
# 注意說明：
# Render 官方不支援直接將 .zip 檔案 POST 上傳（Render 為 Git 驅動的雲端平台）。
# 官方標準的自動化部署端點為「Deploy Hook」或「Render REST API」。
#
# 此腳本會透過 Render Deploy Hook 或 Render API，直接發送 POST 請求觸發 Render
# 自動從您的 GitHub 儲存庫抓取最新程式碼並進行 Build & Deploy！
# ==============================================================================

# 方法 1：Render Deploy Hook URL（最推薦、最簡單）
# 取得方式：Render 儀表板 -> 您的 Web Service -> Settings -> 找到 "Deploy Hook" 複製網址
RENDER_DEPLOY_HOOK_URL = os.getenv("RENDER_DEPLOY_HOOK_URL", "")

# 方法 2：Render REST API（需 Service ID 與 API Token）
RENDER_API_KEY = os.getenv("RENDER_API_KEY", "")
RENDER_SERVICE_ID = os.getenv("RENDER_SERVICE_ID", "")


def trigger_deploy_hook(hook_url: str):
    """透過 Render Deploy Hook 發送 POST 請求觸發部署"""
    print(f"🚀 正在呼叫 Render Deploy Hook: {hook_url[:40]}...")
    try:
        response = requests.post(hook_url, timeout=15)
        if response.status_code in [200, 201, 202]:
            print("✅ 部署指令發送成功！Render 正在為您構建並重新部署服務。")
            print(f"📄 Render 回應: {response.text}")
        else:
            print(f"❌ 部署請求失敗，HTTP 狀態碼: {response.status_code}")
            print(f"📄 回應內容: {response.text}")
    except Exception as e:
        print(f"❌ 連線失敗: {e}")


def trigger_render_api(service_id: str, api_key: str):
    """透過 Render REST API 發送 POST 請求觸發部署"""
    url = f"https://api.render.com/v1/services/{service_id}/deploys"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    print(f"🚀 正在呼叫 Render API 端點: {url}...")
    try:
        response = requests.post(url, headers=headers, json={"clearCache": "do_not_clear"}, timeout=15)
        if response.status_code in [200, 201]:
            print("✅ 部署請求成功！Render 已排程新的構建。")
            print(f"📄 Deploy ID: {response.json().get('id', 'N/A')}")
        else:
            print(f"❌ API 請求失敗，HTTP 狀態碼: {response.status_code}")
            print(f"📄 回應內容: {response.text}")
    except Exception as e:
        print(f"❌ 連線失敗: {e}")


def main():
    print("=" * 60)
    print("       Render Web Service 一鍵自動部署工具")
    print("=" * 60)

    hook_url = RENDER_DEPLOY_HOOK_URL
    if not hook_url and not (RENDER_SERVICE_ID and RENDER_API_KEY):
        print("\n尚未在環境變數中偵測到 RENDER_DEPLOY_HOOK_URL。")
        print("請直接在此處貼上您的 Render Deploy Hook 網址：")
        print("（格式如：https://api.render.com/deploy/srv-xxxxxxxx?key=yyyyyyyy）")
        try:
            user_input = input("\n請輸入 Deploy Hook URL (或按 Enter 跳過): ").strip()
            if user_input:
                hook_url = user_input
        except (KeyboardInterrupt, EOFError):
            print("\n已取消操作。")
            sys.exit(0)

    if hook_url:
        trigger_deploy_hook(hook_url)
    elif RENDER_SERVICE_ID and RENDER_API_KEY:
        trigger_render_api(RENDER_SERVICE_ID, RENDER_API_KEY)
    else:
        print("\n⚠️ 請提供 Deploy Hook URL 才能觸發部署。")
        print("如何取得：在 Render 儀表板點擊您的 Web Service ➜ 進入 Settings ➜ 複製 Deploy Hook 網址。")


if __name__ == "__main__":
    main()
