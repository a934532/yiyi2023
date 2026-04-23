import os
import json
import time
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient

# 設定
API_ID = int(os.getenv('TG_API_ID'))
API_HASH = os.getenv('TG_API_HASH')
HISTORY_FILE = 'notify_history.json'

def get_tw_now():
    return datetime.now(timezone(timedelta(hours=8)))

async def main():
    tw_now_str = get_tw_now().strftime('%m/%d %H:%M')
    
    # 1. 讀取歷史
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            history = json.load(f)
    else:
        history = {}

    async with TelegramClient('anon', API_ID, API_HASH) as client:
        # 2. 抓取頻道訊息 (假設為 oiscreener)
        async for message in client.iter_messages('oiscreener', limit=20):
            if not message.text: continue
            
            # 提取幣種 (抓最後一個 — 後面的字)
            coin = message.text.split('\n')[0].split('—')[-1].strip().upper()
            
            # 3. 檢查 48 小時冷卻
            last_time = history.get(coin, 0)
            if (time.time() - last_time) > 172800:
                # 發送通知 (附上台灣時間)
                msg = f"🔔 {coin} 訊號出現！\n⏰ 時間：{tw_now_str}\n💬 內容：{message.text[:50]}..."
                # 這裡調用你的發送邏輯
                print(msg)
                
                # 更新歷史
                history[coin] = time.time()

    # 4. 存回紀錄
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f)

# 執行...
