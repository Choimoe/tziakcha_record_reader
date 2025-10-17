import json

def find_matches():
    # 读取 JSON 文件
    try:
        with open('record_lists.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("错误：文件 record_lists.json 未找到")
        return []
    except json.JSONDecodeError:
        print("错误：文件格式无效，不是合法的 JSON")
        return []
    
    # 筛选包含 "竹" 的记录
    matches = []
    for record in data:
        if 'title' in record and '竹' in record['title']:
            matches.append({
                "id": record["id"],
                "title": record["title"]
            })
    
    return matches

if __name__ == "__main__":
    results = find_matches()
    
    # 格式化输出结果（JSON 格式）
    if results:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print("[]")  # 无匹配结果时输出空列表
    
    print(f"总共找到 {len(results)} 条包含 '竹' 的记录。")

    with open('selected.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)