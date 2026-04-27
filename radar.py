import requests
import os
import time

# Mengambil rahasia dari GitHub
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
        # Mengambil data Ticker 24 Jam dari semua koin di Binance
        url = "https://api.binance.com/api/v3/ticker/24hr"
        response = requests.get(url)
        data = response.json()
        return data
    except Exception as e:
        print(f"Error nyambung ke Binance: {e}")
        return []

def scan_anomalies():
    print("📡 Radar Menyala! Mencari anomali...")
    tickers = get_binance_data()
    
    for ticker in tickers:
        symbol = ticker['symbol']
        
        # Cuma fokus ke koin USDT dan bukan koin raksasa (contoh: BTC/ETH)
        if symbol.endswith("USDT") and symbol not in ["BTCUSDT", "ETHUSDT"]:
            volume_24h = float(ticker['quoteVolume']) # Volume dalam bentuk USDT
            price_change = float(ticker['priceChangePercent'])
            
            # Kriteria Anomali Sederhana: 
            # Jika Volume 24 jam di atas 1 Juta Dolar (biar gak murni scam) 
            # DAN harganya naik tiba-tiba lebih dari 5% dalam 24 jam terakhir.
            # (Ini versi simpel. Nanti lu bisa modifikasi ambil data 1 jam pakai kline API).
            
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
                time.sleep(1) # Jeda dikit biar Telegram nggak nge-ban bot kita

if __name__ == "__main__":
    scan_anomalies()
