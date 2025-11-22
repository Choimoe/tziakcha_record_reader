import sys, os, json
from parser import MahjongRecordParser

def load_record(record_id):
    path=os.path.join('data','origin',record_id+'.json')
    with open(path,'r',encoding='utf-8') as f:
        return f.read()

def analyze(record_id):
    data=load_record(record_id)
    p=MahjongRecordParser(data)
    p.run_analysis()
    if not p.win_info:
        print('NO_WIN')
        return
    w=p.win_info['winner']
    raw_final=[p.get_tile_str(t) for t in p.hands[w]]
    hand_str=p._build_hand_string_for_gb()
    counts={}
    for t in raw_final:
        counts[t]=counts.get(t,0)+1
    print('record_id',record_id)
    print('dealer_idx',p.dealer_idx)
    print('raw_tiles',''.join(raw_final))
    print('counts',json.dumps(counts,ensure_ascii=False))
    print('len',len(raw_final))
    print('hand_string',hand_str)
    print('env_flag',p._build_env_flag())
    print('win_tile',p.get_tile_str(p.win_info['win_tile']))

def main():
    rid=sys.argv[1] if len(sys.argv)>1 else 'suK1WwTk'
    analyze(rid)

if __name__=='__main__':
    main()
