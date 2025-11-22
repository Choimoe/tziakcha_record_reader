# batch_process.py

import sys
import os
import json
import requests
import csv
from parser import MahjongRecordParser

# ================== 从原 main.py 复用的代码 ==================

URL = "https://tziakcha.net/_qry/record/"
HEADERS = {
    "accept": "*/*",
    "content-type": "text/plain;charset=UTF-8"
}

def download_record(record_id):
    payload = f"id={record_id}"
    try:
        response = requests.post(URL, data=payload, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Download failed for {record_id}: {e}", file=sys.stderr)
        return None

def save_origin(record_id, data):
    origin_dir = os.path.join("data", "origin")
    os.makedirs(origin_dir, exist_ok=True)
    with open(os.path.join(origin_dir, f"{record_id}.json"), "w", encoding="utf-8") as f:
        f.write(data)

def process_record(record_id):
    origin_file = os.path.join("data", "origin", f"{record_id}.json")
    try:
        with open(origin_file, "r", encoding="utf-8") as f:
            origin_data = f.read().strip()
    except FileNotFoundError:
        print(f"Origin file not found: {origin_file}")
        return False

    parser = MahjongRecordParser(origin_data)
    script_data = parser.script_data

    record_dir = os.path.join("data", "record")
    os.makedirs(record_dir, exist_ok=True)
    with open(os.path.join(record_dir, f"{record_id}.json"), "w", encoding="utf-8") as f:
        json.dump(script_data, f, ensure_ascii=False, indent=2)

    # 执行分析（根据你的 parser 实现）
    parser.run_analysis()
    compare = parser.compute_gb_fan()
    official_list = parser.get_official_fan_list()
    gb_list = []
    error = None
    if compare:
        gb_list = compare.get('node_detail', {}).get('fan_list', []) or []
        error = compare.get('node_detail', {}).get('error')
    return {
        'record_id': record_id,
        'winner_name': parser.win_info and parser.script_data['p'][parser.win_info['winner']]['n'] if parser.win_info else None,
        'hand_string': compare and compare.get('hand_string'),
        'env_flag': compare and compare.get('env_flag'),
        'official_total_fan': compare and compare.get('official_total_fan'),
        'official_base_fan': compare and compare.get('official_base_fan'),
        'gb_total_fan': compare and compare.get('gb_total_fan'),
        'gb_base_fan': compare and compare.get('gb_base_fan'),
        'diff': compare and compare.get('diff'),
        'official_fans': official_list,
        'gb_fans': gb_list,
        'error': error
    }

# ================== 批量处理逻辑 ==================

def load_all_record_ids(json_file="all_record.json"):
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"File not found: {json_file}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in {json_file}: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(data, list):
        print("Invalid format: top-level JSON must be a list.", file=sys.stderr)
        sys.exit(1)

    if data and isinstance(data[0], dict) and 'records' in data[0]:
        flattened = []
        for session_obj in data:
            if not isinstance(session_obj, dict):
                continue
            recs = session_obj.get('records', [])
            if isinstance(recs, list):
                flattened.extend([r for r in recs if isinstance(r, str)])
        return flattened

    if all(isinstance(x, str) for x in data):
        return data

    print("Unrecognized all_record.json structure.", file=sys.stderr)
    sys.exit(1)

def main():
    record_ids = load_all_record_ids("all_record.json")

    print(f"Found {len(record_ids)} records. Starting batch processing...")

    suc_cnt = 0
    fail_cnt = 0
    results = []

    for i, record_id in enumerate(record_ids, start=1):
        print(f"\n\n[{i}/{len(record_ids)}] Processing record: https://tziakcha.net/record/?id={record_id}")

        origin_file = os.path.join("data", "origin", f"{record_id}.json")
        if not os.path.exists(origin_file):
            print(f"  Downloading {record_id}...")
            data = download_record(record_id)
            if data is None:
                print(f"  ❌ Failed to download {record_id}, skipping...")
                continue
            save_origin(record_id, data)
        # else:
        #     print(f"  Already downloaded, skip download.")

        # 处理记录（解析 + 分析）
        
        try:
            r = process_record(record_id)
            if isinstance(r, dict) and r.get('diff') != 0:
                results.append(r)
            suc_cnt += 1
        except Exception as e:
            print(f"  ❌ Error during processing {record_id}: {e}\n")
            fail_cnt += 1

    # print("✅ Batch processing completed.")
    # 输出 CSV 与 JSON
    out_dir = os.path.join('data')
    os.makedirs(out_dir, exist_ok=True)
    csv_file = os.path.join(out_dir, 'batch_compare.csv')
    json_file = os.path.join(out_dir, 'batch_compare.json')
    for r in results:
        off_names = {f['name'] for f in r.get('official_fans', [])}
        gb_names = {f.get('normalizedName') or f.get('name') for f in r.get('gb_fans', [])}
        r['fans_only_official'] = sorted(list(off_names - gb_names))
        r['fans_only_gb'] = sorted(list(gb_names - off_names))
    fieldnames = ['record_id','winner_name','hand_string','env_flag','official_total_fan','official_base_fan','gb_total_fan','gb_base_fan','diff','fans_only_official','fans_only_gb','error']
    try:
        with open(csv_file,'w',newline='',encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in results:
                row = {k: r.get(k) for k in fieldnames}
                w.writerow(row)
        with open(json_file,'w',encoding='utf-8') as f:
            json.dump(results,f,ensure_ascii=False,indent=2)
        print(f"  Batch comparison written: {csv_file}, {json_file}")
    except Exception as e:
        print(f"  ❌ Failed writing comparison outputs: {e}")
    print(f"  Successfully processed: {suc_cnt}")
    print(f"  Failed to process: {fail_cnt}")

if __name__ == "__main__":
    main()