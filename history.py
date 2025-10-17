import requests
import os
import json
import sys

url = "https://tziakcha.net/_qry/history/"
cookie = os.getenv('TZI_HISTORY_COOKIE')
if not cookie:
    print("错误: 未设置环境变量 TZI_HISTORY_COOKIE")
    print("请先在浏览器中登录 https://tziakcha.net/history/，然后获取Cookie值")
    sys.exit(1)

headers = {
    "accept": "*/*",
    "accept-language": "zh-CN,zh;q=0.9,en-GB;q=0.8,en;q=0.7,en-US;q=0.6",
    "content-type": "text/plain;charset=UTF-8",
    "priority": "u=1, i",
    "sec-ch-ua": "\"Not;A=Brand\";v=\"99\", \"Microsoft Edge\";v=\"139\", \"Chromium\";v=\"139\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"macOS\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "referrer": "https://tziakcha.net/history/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
    "Cookie": cookie
}

all_records = []
for page in range(1, 101):
    body = f"p={page-1}" if page > 1 else ""
    try:
        response = requests.post(url, headers=headers, data=body)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and 'games' in data:
                all_records.extend(data['games'])
    except Exception as e:
        continue

with open('record_lists.json', 'w', encoding='utf-8') as f:
    json.dump(all_records, f, indent=2, ensure_ascii=False)

filtered = [rec for rec in all_records if '竹' in rec.get('title', '')]
for rec in filtered:
    print(json.dumps(rec, ensure_ascii=False, indent=2))