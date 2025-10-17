import sys
import os
import json
import requests
from parser import MahjongRecordParser

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
        print(f"Download failed: {e}", file=sys.stderr)
        sys.exit(1)


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
        print(f"Origin file not found: {origin_file}", file=sys.stderr)
        sys.exit(1)

    parser = MahjongRecordParser(origin_data)
    script_data = parser.script_data

    record_dir = os.path.join("data", "record")
    os.makedirs(record_dir, exist_ok=True)
    with open(os.path.join(record_dir, f"{record_id}.json"), "w", encoding="utf-8") as f:
        json.dump(script_data, f, ensure_ascii=False, indent=2)

    parser.run_analysis()


def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py <record_id>", file=sys.stderr)
        sys.exit(1)

    record_id = sys.argv[1]
    origin_file = os.path.join("data", "origin", f"{record_id}.json")

    if not os.path.exists(origin_file):
        data = download_record(record_id)
        save_origin(record_id, data)

    process_record(record_id)


if __name__ == "__main__":
    main()
