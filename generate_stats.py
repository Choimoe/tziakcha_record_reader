import csv
import json
import os
from parser import MahjongRecordParser

def generate_stats():
    origin_dir = 'data/origin'
    output_csv_path = 'win_stats.csv'
    output_csv_bom_path = 'win_stats_bom.csv'
    
    record_files = [f for f in os.listdir(origin_dir) if f.endswith('.json')]
    
    FAN_NAMES = ['无','大四喜','大三元','绿一色','九莲宝灯','四杠','连七对','十三幺','清幺九','小四喜','小三元','字一色','四暗刻','一色双龙会','一色四同顺','一色四节高','一色四步高','一色四连环','三杠','混幺九','七对','七星不靠','全双刻','清一色','一色三同顺','一色三节高','全大','全中','全小','清龙','三色双龙会','一色三步高','一色三连环','全带五','三同刻','三暗刻','全不靠','组合龙','大于五','小于五','三风刻','花龙','推不倒','三色三同顺','三色三节高','无番和','妙手回春','海底捞月','杠上开花','抢杠和','碰碰和','混一色','三色三步高','五门齐','全求人','双暗杠','双箭刻','全带幺','不求人','双明杠','和绝张','箭刻','圈风刻','门风刻','门前清','平和','四归一','双同刻','双暗刻','暗杠','断幺','一般高','喜相逢','连六','老少副','幺九刻','明杠','缺一门','无字','独听・边张','独听・嵌张','独听・单钓','自摸','花牌','明暗杠','\u203b 天和','\u203b 地和','\u203b 人和Ⅰ','\u203b 人和Ⅱ']

    header = ['和牌用户', '和牌素番数（不含花）', '花的数量', '和牌番数', '手牌', '和牌张', '所属局'] + FAN_NAMES + ['对局']
    
    all_rows = []

    for filename in record_files:
        record_id = os.path.splitext(filename)[0]
        filepath = os.path.join(origin_dir, filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                record_content = f.read()
                if not record_content.strip():
                    continue
                parser = MahjongRecordParser(record_content)
                parser.run_analysis()
                win_data = parser.get_win_analysis()

                if win_data:
                    row = [
                        win_data['winner_name'],
                        win_data['base_fan'],
                        win_data['flower_count'],
                        win_data['total_fan'],
                        win_data['formatted_hand'],
                        win_data['winning_tile'],
                        win_data['game_title'],
                    ] + win_data['fan_vector'] + [f"https://tziakcha.net/record/?id={record_id}"]
                    all_rows.append(row)
        except Exception as e:
            print(f"Error processing file {filename}: {e}")

    # Write UTF-8 file
    with open(output_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(header)
        writer.writerows(all_rows)

    # Write UTF-8-BOM file
    with open(output_csv_bom_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(header)
        writer.writerows(all_rows)

if __name__ == '__main__':
    generate_stats()
    print(f"统计完成，已生成文件 win_stats.csv 和 win_stats_bom.csv")
