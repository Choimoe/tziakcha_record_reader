# batch_process.py

import sys
import os
import json
import requests
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
    return True

# ================== 批量处理逻辑 ==================

def load_all_record_ids(json_file="all_record.json"):
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        else:
            print("Invalid format: expected a list of record IDs.", file=sys.stderr)
            sys.exit(1)
    except FileNotFoundError:
        print(f"File not found: {json_file}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in {json_file}: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    # 加载所有 record_id
    record_ids = load_all_record_ids("all_record.json")

    print(f"Found {len(record_ids)} records. Starting batch processing...")

    suc_cnt = 0
    fail_cnt = 0

    for i, record_id in enumerate(record_ids, start=1):
        print(f"\n\n[{i}/{len(record_ids)}] Processing record: https://tziakcha.net/record/?id={record_id}")

        # 检查是否已存在本地 origin 文件
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
            process_record(record_id)
            # print(f"  ✅ Processed successfully.\n")
            suc_cnt += 1
        except Exception as e:
            print(f"  ❌ Error during processing {record_id}: {e}\n")
            fail_cnt += 1

    # print("✅ Batch processing completed.")
    print(f"  Successfully processed: {suc_cnt}")
    print(f"  Failed to process: {fail_cnt}")

if __name__ == "__main__":
    main()