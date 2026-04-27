import requests
import os
import time

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Gagal ngirim pesan: {e}")

def get_binance_data():
    try:
        # HACK: Pakai jalur Data API Binance yang jarang ke-blokir IP US
        url = "https://data-api.binance.vision/api/v3/ticker/24hr"
        response = requests.get(url)
        return response.json()
    except Exception as e:
        print(f"Error nyambung ke Binance: {e}")
        return None

def scan_anomalies():
    print("📡 Radar Menyala! Mencari anomali...")
    tickers = get_binance_data()
    
    # 🛡️ SABUK PENGAMAN: Kalau Binance ngasih pesan error / bukan list
    if isinstance(tickers, dict):
        print(f"❌ DICEGAT BINANCE! Pesan server: {tickers}")
        return
    if not tickers:
        print("❌ Gagal dapat data dari Binance.")
        return

    for ticker in tickers:
        # Pastikan ini benar-benar data koin
        if isinstance(ticker, dict) and 'symbol' in ticker:
            symbol = ticker['symbol']
            
            if symbol.endswith("USDT") and symbol not in ["BTCUSDT", "ETHUSDT"]:
                volume_24h = float(ticker['quoteVolume'])
                price_change = float(ticker['priceChangePercent'])
                
                # Syarat anomali
                if volume_24h > 1000000 and price_change > 8.0:
                    msg = (
                        f"🚨 <b>ANOMALI TERDETEKSI</b> 🚨\n\n"
                        f"💎 Koin: <b>{symbol}</b>\n"
                        f"📈 Naik: {price_change:.2f}%\n"
                        f"💰 Vol (24h): ${volume_24h:,.0f}\n"
                        f"🔗 <a href='https://www.binance.com/en/trade/{symbol}?type=spot'>Buka Binance</a>"
                    )
                    print(f"Ditemukan: {symbol}")
                    send_telegram_message(msg)
                    time.sleep(1)

if __name__ == "__main__":
    scan_anomalies()
