import requests
import os
import json

selected = json.load(open('selected.json', 'r', encoding='utf-8'))

headers = {
    "accept": "*/*",
    "content-type": "text/plain;charset=UTF-8"
}

all_small_ids = []
for item in selected:
    game_id = item['id']
    response = requests.post(f"https://tziakcha.net/_qry/game/?id={game_id}", headers=headers, data='')
    if response.status_code == 200:
        data = response.json()
        if 'records' in data:
            for record in data['records']:
                all_small_ids.append(record['i'])

json.dump(all_small_ids, open('all_record.json', 'w', encoding='utf-8'), indent=2, ensure_ascii=False)