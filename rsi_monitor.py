import os
import json
import time
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone

# --- 設定區 ---
TOKEN = os.getenv('TG_TOKEN')
CHAT_ID = os.getenv('TG_CHAT_ID')
HISTORY_FILE = 'notify_history.json'
COOLDOWN_SECONDS = 96 * 3600  # 96 小時冷卻

def get_tw_now():
    return datetime.now(timezone(timedelta(hours=8)))

def send_bot_msg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except:
        pass

def extract_coin(text):
    """
    匹配 #ROBO, #MVLL, #BTCUSDT 格式
    """
    try:
        hash_match = re.search(r'#([A-Z0-9]{1,12})\b', text, re.IGNORECASE)
        if hash_match:
            coin = hash_match.group(1).upper()
            if coin.endswith("USDT") and len(coin) > 4:
                coin = coin[:-4]
            return coin

        dollar_match = re.search(r'\$([A-Za-z][A-Za-z0-9]{0,11})\b', text)
        if dollar_match:
            return dollar_match.group(1).upper()
    except:
        pass
    return None

def clean_info(text):
    """
    精準抽取 1h 的 OI、Price Change 與 Long/Short
    """
    # 1. 抓取 OI 1h (例如 +5.54% (1h))
    oi_1h = "N/A"
    oi_match = re.search(r'([\+\-]\d+\.\d+%\s*\(1h\))', text)
    if oi_match:
        oi_1h = oi_match.group(1).replace(" ", "")

    # 2. 抓取 Price change 1h (例如 +5.54% (1h))
    # 訊息中通常有兩區 (1h)，第二區為 Price
    price_1h = "N/A"
    price_matches = re.findall(r'([\+\-]\d+\.\d+%\s*\(1h\))', text)
    if len(price_matches) >= 2:
        price_1h = price_matches[1].replace(" ", "")
    elif len(price_matches) == 1:
        price_1h = price_matches[0].replace(" ", "")

    # 3. 抓取 Long/Short 1h (例如 0.99 (1h))
    ls_1h = "N/A"
    ls_match = re.search(r'Long/Short\s+.*?\b(\d+\.\d+)\s*\(1h\)', text, re.IGNORECASE)
    if ls_match:
        ls_1h = ls_match.group(1)

    # 組合乾淨的文字輸出
    result = (
        f"📈 *OI (1h)*: {oi_1h}\n"
        f"💰 *Price (1h)*: {price_1h}\n"
        f"⚖️ *L/S (1h)*: {ls_1h}"
    )
    return result

def main():
    print(f"=== 啟動檢查: {get_tw_now().strftime('%H:%M:%S')} ===")
    
    history = {}
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            try: history = json.load(f)
            except: history = {}

    url = "https://t.me/s/oi_detector"
    try:
        res = requests.get(url, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        messages = soup.find_all('div', class_='tgme_widget_message_text')
    except Exception as e:
        print(f"網頁讀取失敗: {e}")
        return

    now_ts = time.time()
    found_new = False
    seen_this_run = set()

    for msg_div in reversed(messages):
        full_text = msg_div.get_text()
        coin = extract_coin(full_text)
        
        if coin and coin not in seen_this_run:
            last_time = history.get(coin, 0)
            
            if (now_ts - last_time) > COOLDOWN_SECONDS:
                data_text = clean_info(full_text)
                tw_time = get_tw_now().strftime('%m/%d %H:%M')
                
                alert_text = (
                    f"💎 *{coin}* (96H首見)\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"{data_text}\n"
                    f"⏰ {tw_time}"
                )
                
                send_bot_msg(alert_text)
                print(f"✅ 已發送精簡通知: {coin}")
                
                history[coin] = now_ts
                seen_this_run.add(coin)
                found_new = True

    if found_new:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f)

if __name__ == "__main__":
    main()
