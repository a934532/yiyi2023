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
    payload = {
        "chat_id": CHAT_ID, 
        "text": text, 
        "parse_mode": "Markdown",
        "disable_web_page_preview": True  # 關閉網頁縮圖卡片，保持畫面乾淨
    }
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
    oi_1h = "N/A"
    oi_match = re.search(r'([\+\-]\d+\.\d+%\s*\(1h\))', text)
    if oi_match:
        oi_1h = oi_match.group(1).replace(" ", "")

    price_1h = "N/A"
    price_matches = re.findall(r'([\+\-]\d+\.\d+%\s*\(1h\))', text)
    if len(price_matches) >= 2:
        price_1h = price_matches[1].replace(" ", "")
    elif len(price_matches) == 1:
        price_1h = price_matches[0].replace(" ", "")

    ls_1h = "N/A"
    ls_match = re.search(r'Long/Short\s+.*?\b(\d+\.\d+)\s*\(1h\)', text, re.IGNORECASE)
    if ls_match:
        ls_1h = ls_match.group(1)

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

    channel_username = "oi_detector"
    url = f"https://t.me/s/{channel_username}"
    
    try:
        res = requests.get(url, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        # 改為抓取整個 widget_message 容器，才能拿到 data-post 屬性
        message_widgets = soup.find_all('div', class_='tgme_widget_message')
    except Exception as e:
        print(f"網頁讀取失敗: {e}")
        return

    now_ts = time.time()
    found_new = False
    seen_this_run = set()

    for widget in reversed(message_widgets):
        # 尋找文字區域
        msg_div = widget.find('div', class_='tgme_widget_message_text')
        if not msg_div:
            continue
            
        full_text = msg_div.get_text()
        coin = extract_coin(full_text)
        
        if coin and coin not in seen_this_run:
            last_time = history.get(coin, 0)
            
            if (now_ts - last_time) > COOLDOWN_SECONDS:
                data_text = clean_info(full_text)
                tw_time = get_tw_now().strftime('%m/%d %H:%M')
                
                # 抓取這則訊息對應的單則 ID (格式通常為 oi_detector/1234)
                data_post = widget.get('data-post', '')
                if data_post:
                    msg_link = f"https://t.me/{data_post}"
                else:
                    msg_link = f"https://t.me/{channel_username}"
                
                alert_text = (
                    f"💎 *{coin}* (96H首見)\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"{data_text}\n"
                    f"⏰ {tw_time}\n\n"
                    f"🎯 [定位到此訊號]({msg_link})"
                )
                
                send_bot_msg(alert_text)
                print(f"✅ 已發送定位通知: {coin} -> {msg_link}")
                
                history[coin] = now_ts
                seen_this_run.add(coin)
                found_new = True

    if found_new:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f)

if __name__ == "__main__":
    main()
