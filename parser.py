import json
import base64
import zlib
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any




def prev_tile(index: int) -> int:
    return index - 4


def next_tile(index: int) -> int:
    return index + 4


def _parse_script(s: str) -> Dict[str, Any]:
    return json.loads(zlib.decompress(base64.b64decode(s)).decode('utf-8'))


def _parse_acts(acts: List[List[int]]) -> List[Dict[str, int]]:
    return [{'p': (a[0] >> 4) & 3, 'a': a[0] & 15, 'd': a[1], 't': a[2]} for a in acts]


class MahjongRecordParser:
    WIND = ['东', '南', '西', '北']
    TILE_IDENTITY = [
        '1m', '2m', '3m', '4m', '5m', '6m', '7m', '8m', '9m',
        '1s', '2s', '3s', '4s', '5s', '6s', '7s', '8s', '9s',
        '1p', '2p', '3p', '4p', '5p', '6p', '7p', '8p', '9p',
        'E', 'S', 'W', 'N', 'C', 'F', 'B'
    ]
    FLOWER_TILES = ['1f', '2f', '3f', '4f', '5f', '6f', '7f', '8f']
    PACK_ACTION_MAP = {3: "CHI", 4: "PENG", 5: "GANG"}
    S2O = [[0, 1, 2, 3], [1, 2, 3, 0], [2, 3, 0, 1], [3, 0, 1, 2], [1, 0, 3, 2], [0, 3, 2, 1], [3, 2, 1, 0],
           [2, 1, 0, 3], [2, 3, 1, 0], [3, 1, 0, 2], [1, 0, 2, 3], [0, 2, 3, 1], [3, 2, 0, 1], [2, 0, 1, 3],
           [0, 1, 3, 2], [1, 3, 2, 0]]

    def __init__(self, record_json_str: str):
        record_json = json.loads(record_json_str)
        self.script_data = _parse_script(record_json['script'])
        self.actions = _parse_acts(self.script_data.get('a', []))

        self.hands = [[] for _ in range(4)]
        self.packs = [[] for _ in range(4)]
        self.packs_output = [[] for _ in range(4)]
        self.discards = [[] for _ in range(4)]
        self.flower_counts = [0] * 4
        self.flower_tile = [[] for _ in range(4)]
        self.initial_hands = [[] for _ in range(4)]

        self.win_info = None
        self.last_discard_info = {}
        self.current_player_idx = -1
        self.last_action_was_kong = False
        self.wall = []
        self.wall_front_ptr = 0
        self.wall_back_ptr = 0
        self.last_draw_tiles = [None] * 4
        self.dealer_idx = None

    def get_tile_str(self, index: int) -> str:
        if 0 <= index < 136:
            return self.TILE_IDENTITY[index >> 2]
        if 136 <= index < 144:
            return self.FLOWER_TILES[index - 136]
        return '??'

    def get_tile_GB_str(self, index: int) -> str:
        if 0 <= index < 136:
            return self.TILE_IDENTITY[index >> 2]
        return '??'


    def _setup_wall_and_deal(self):
        wall_indices = [int(self.script_data['w'][i:i + 2], 16) for i in range(0, len(self.script_data['w']), 2)]
        dice = [self.script_data['d'] & 15, (self.script_data['d'] >> 4) & 15,
            (self.script_data['d'] >> 8) & 15, (self.script_data['d'] >> 12) & 15]
        dealer_idx = 0
        self.dealer_idx = dealer_idx

        wall_break_pos = (dealer_idx - (dice[0] + dice[1] - 1) + 4) % 4
        start_pos = (wall_break_pos * 36) + (dice[0] + dice[1] + dice[2] + dice[3]) * 2
        start_pos = start_pos % 144


        self.wall = wall_indices[start_pos:] + wall_indices[:start_pos]
        self.wall_back_ptr = len(self.wall) - 1

        for i in range(3):
            for p_offset in range(4):
                player_idx = (dealer_idx + p_offset) % 4
                draw = self.wall[self.wall_front_ptr: self.wall_front_ptr + 4]
                self.hands[player_idx].extend(draw)
                self.wall_front_ptr += 4

        for p_offset in range(4):
            player_idx = (dealer_idx + p_offset) % 4
            self.hands[player_idx].append(self.wall[self.wall_front_ptr])
            self.wall_front_ptr += 1

        self.hands[dealer_idx].append(self.wall[self.wall_front_ptr])
        self.wall_front_ptr += 1

        for i in range(4):
            self.hands[i].sort()
            self.initial_hands[i] = [self.get_tile_str(t) for t in self.hands[i]]

        self.current_player_idx = dealer_idx

    def _print_game_info(self):
        g = self.script_data['g']
        p_info = self.script_data['p']

        config_str = (
            f"配置：{g['n']}盘 | {g['l']}番 ({g['b']}) | {g['r0']}/{g['r1']}+{g['e']} | "
            f"天地人和 {'✓' if g['bl'] else '✕'} | 战术鸣牌 {'✓' if g['s'] else '✕'} | "
            f"手牌 {'✓' if g['o'] else '✕'} | 错和 鸣牌 {'✓' if g['d'] else '✕'} "
            f"{'-30/+10' if g['z'] else '-40/+0'} | {'随机座位' if g['r'] else '固定座位'}"
        )

        start_time_unix = self.script_data['t'] / 1000
        end_time_unix = start_time_unix + (self.actions[-1]['t'] / 1000 if self.actions else 0)
        tz = timezone(timedelta(hours=8))
        start_dt = datetime.fromtimestamp(start_time_unix, tz).strftime('%Y-%m-%d %H:%M:%S UTC%z')
        end_dt = datetime.fromtimestamp(end_time_unix, tz).strftime('%Y-%m-%d %H:%M:%S UTC%z')



    def run_analysis(self):
        self._print_game_info()
        self._setup_wall_and_deal()


        prev_time = 0
        total_action_num = len(self.actions)
        act_cnt = 0

        for act in self.actions:
            act_cnt += 1
            p_idx, a_type, data, time = act['p'], act['a'], act['d'], act['t']
            if a_type == 0 and self.dealer_idx is not None and self.dealer_idx != p_idx:
                self.dealer_idx = p_idx
            player_info = f"{self.WIND[p_idx]}家 {self.script_data['p'][p_idx]['n']}"
            time_str = f"[{((time - prev_time) / 1000.0):.3f}s]"

            output = f"{player_info} "
            lo_byte, hi_byte = data & 0xFF, (data >> 8) & 0xFF

            if a_type == 0:
                output += "开始出牌"
            elif a_type == 1:
                self.flower_counts[p_idx] += 1
                ot = (hi_byte & 15) + 136
                self.flower_tile[p_idx].append(self.get_tile_str(ot))
                self.hands[p_idx].remove(ot)
                self.hands[p_idx].append(lo_byte)
                self.last_draw_tiles[p_idx] = lo_byte
                output += f"{'自动' if data & 0x1000 else '手动'}补花 {self.get_tile_str(ot)}->{self.get_tile_str(lo_byte)}"
            elif a_type == 2:
                self.current_player_idx = p_idx
                tile = lo_byte
                if tile in self.hands[p_idx]: self.hands[p_idx].remove(tile)
                self.discards[p_idx].append(tile)
                self.last_discard_info = {'tile': tile, 'player': p_idx}
                self.last_action_was_kong = False
                discard_type = '手打' if hi_byte & 1 else '摸打'
                output += f"{discard_type} {self.get_tile_str(tile)}"
            elif a_type in [3, 4, 5]:
                pack_type = self.PACK_ACTION_MAP[a_type]
                tile_val = (data & 0x3F) << 2
                offer_from_idx = (p_idx + ((data >> 6) & 3)) % 4
                self.current_player_idx = p_idx
                if data == 0:
                    continue

                if pack_type == "CHI":
                    offer_tile = self.last_discard_info['tile']
                    if tile_val - 4 + ((data >> 10) & 3) < 0:
                        tile_val = offer_tile
                    c1 = tile_val - 4 + ((data >> 10) & 3)
                    c2 = tile_val + ((data >> 12) & 3)
                    c3 = tile_val + 4 + ((data >> 14) & 3)
                    chi_tiles = [c1, c2, c3]
                    chi_id = 1
                    chi_shape = []
                    for t in range(3):
                        if chi_tiles[t] >> 2 == offer_tile >> 2:
                            chi_id = t + 1
                            chi_shape.append(f"({self.get_tile_str(chi_tiles[t])})")
                        else:
                            for _ in self.hands[p_idx]:
                                if (_ >> 2) == (chi_tiles[t] >> 2):
                                    self.hands[p_idx].remove(_)
                                    break
                            chi_shape.append(self.get_tile_str(chi_tiles[t]))
                    self.packs[p_idx].append(("CHI", self.get_tile_GB_str(tile_val), chi_id))
                    self.packs_output[p_idx].append(chi_shape)
                    output += f"吃 {self.get_tile_str(offer_tile)}"
                    try:
                        self.discards[offer_from_idx].pop()
                    except IndexError:
                        pass
                elif pack_type == "PENG":
                    count = 0
                    hand_copy = list(self.hands[p_idx])
                    for t in hand_copy:
                        if (t >> 2) == (tile_val >> 2) and count < 2:
                            self.hands[p_idx].remove(t)
                            count += 1
                    self.packs[p_idx].append(("PENG", self.get_tile_GB_str(tile_val), (data >> 6) & 3))
                    self.packs_output[p_idx].append([self.get_tile_str(tile_val) for _ in range(3)])
                    output += f"碰 {self.get_tile_str(tile_val)}"
                    try:
                        self.discards[offer_from_idx].pop()
                    except IndexError:
                        pass
                elif pack_type == "GANG":
                    self.last_action_was_kong = True
                    action = "加杠" if (data & 0x0300) == 0x0300 else "杠"
                    if action == "加杠":
                        hand_copy = list(self.hands[p_idx])
                        self.last_discard_info = {'tile': tile_val, 'player': p_idx}
                        for t in hand_copy:
                            if (t >> 2) == (tile_val >> 2):
                                self.hands[p_idx].remove(t)
                                break
                        for i, (pt, pstr, po) in enumerate(self.packs[p_idx]):
                            if pt == "PENG" and pstr == self.get_tile_str(tile_val):
                                self.packs[p_idx][i] = ("GANG", pstr, po);
                                self.packs_output[p_idx][i] = ([self.get_tile_str(tile_val) for _ in range(4)])
                                break
                    elif (data >> 6) & 3 == 0:  # Concealed
                        count = 0
                        hand_copy = list(self.hands[p_idx])
                        for t in hand_copy:
                            if (t >> 2) == (tile_val >> 2) and count < 4:
                                self.hands[p_idx].remove(t)
                                count += 1
                        self.packs[p_idx].append(("GANG", self.get_tile_GB_str(tile_val), 0))
                        self.packs_output[p_idx].append([self.get_tile_str(tile_val) for _ in range(4)])
                    else:  # Melded
                        for _ in range(3):
                            count = 0
                            for t in self.hands[p_idx]:
                                if (t >> 2) == (tile_val >> 2) and count < 3:
                                    self.hands[p_idx].remove(t)
                                    count += 1
                        self.packs[p_idx].append(("GANG", self.get_tile_GB_str(tile_val), (data >> 6) & 3))
                        self.packs_output[p_idx].append([self.get_tile_str(tile_val) for _ in range(4)])
                        try:
                            self.discards[offer_from_idx].pop()
                        except IndexError:
                            pass
                    output += f"{action} {self.get_tile_str(tile_val)}"
            elif a_type == 6:
                if data == 0:
                    continue
                is_self_drawn = p_idx == self.current_player_idx
                win_tile = self.last_draw_tiles[p_idx] if is_self_drawn else self.last_discard_info['tile']
                self.win_info = {'winner': p_idx, 'win_tile': win_tile, 'is_self_drawn': is_self_drawn}
                if not is_self_drawn: self.hands[p_idx].append(win_tile)
                fan = data >> 1
                fan_str = f"{fan}番" if fan > 0 else ""
                output += f"{'自动' if data & 1 else '手动'}和 {fan_str}"
                break
            elif a_type == 7:
                self.current_player_idx = p_idx
                tile_to_draw = lo_byte
                self.hands[p_idx].append(tile_to_draw)
                self.last_draw_tiles[p_idx] = tile_to_draw
                draw_type = '摸牌' if not hi_byte else '逆向摸牌'
                output += f"{draw_type} {self.get_tile_str(tile_to_draw)}"
            elif a_type == 8:
                output += "过"
            elif a_type == 9:
                output += "弃"
            
            self.hands[p_idx].sort()
            detail_debug = 0
            # print(output)
            if detail_debug:
                hand_str = ' '.join([self.get_tile_str(t) for t in self.hands[p_idx]])
                packs_str = ' '.join([f"[{''.join(p)}]" for p in self.packs_output[p_idx]])
                print(f"{output} {time_str}")
                print(f"{self.WIND[p_idx]}家 {self.script_data['p'][p_idx]['n']}: {hand_str}  {packs_str}")
            prev_time = time

        if not self.win_info:
            pass
        else:
            self._print_fan_info()



    def _print_fan_info(self):
        w_idx = self.win_info['winner']
        win_data = self.script_data['y'][w_idx]
        total_fan = win_data.get('f') if isinstance(win_data, dict) else None
        fan_details = win_data.get('t', {}) if isinstance(win_data, dict) else {}

        FAN_NAMES = ['无','大四喜','大三元','绿一色','九莲宝灯','四杠','连七对','十三幺','清幺九','小四喜','小三元','字一色','四暗刻','一色双龙会','一色四同顺','一色四节高','一色四步高','一色四连环','三杠','混幺九','七对','七星不靠','全双刻','清一色','一色三同顺','一色三节高','全大','全中','全小','清龙','三色双龙会','一色三步高','一色三连环','全带五','三同刻','三暗刻','全不靠','组合龙','大于五','小于五','三风刻','花龙','推不倒','三色三同顺','三色三节高','无番和','妙手回春','海底捞月','杠上开花','抢杠和','碰碰和','混一色','三色三步高','五门齐','全求人','双暗杠','双箭刻','全带幺','不求人','双明杠','和绝张','箭刻','圈风刻','门风刻','门前清','平和','四归一','双同刻','双暗刻','暗杠','断幺','一般高','喜相逢','连六','老少副','幺九刻','明杠','缺一门','无字','独听・边张','独听・嵌张','独听・单钓','自摸','花牌','明暗杠','\u203b 天和','\u203b 地和','\u203b 人和Ⅰ','\u203b 人和Ⅱ']

        self.hands[w_idx].sort()
        hand_str = ' '.join([self.get_tile_str(t) for t in self.hands[w_idx]])
        packs_str = ' '.join([f"[{''.join(p)}]" for p in self.packs_output[w_idx]])
        print(f"{self.WIND[w_idx]}家 {self.script_data['p'][w_idx]['n']}: {hand_str} {packs_str}")

        calculated_fan_sum = 0
        for fan_id_str, fan_val in fan_details.items():
            fan_id = int(fan_id_str)
            if fan_id == 83:
                continue
            fan_points = fan_val & 0xFF
            count = (fan_val >> 8) + 1
            calculated_fan_sum += fan_points * count

        if total_fan is not None:
            inferred_flower_count = max(total_fan - calculated_fan_sum, 0)
        else:
            inferred_flower_count = None

        actual_flower_count = self.flower_counts[w_idx]
        if inferred_flower_count is not None and inferred_flower_count != actual_flower_count:
            print(f"[WARN] 牌谱番种推导花数为 {inferred_flower_count}，与动作统计花数 {actual_flower_count} 不一致，已以实际为准。")
        flower_count = actual_flower_count

        if flower_count > 0:
            flower_str = f'花牌x{flower_count}: ' + ' '.join(self.flower_tile[w_idx])
        else:
            flower_str = '无花牌'

        tf_str = f"{total_fan}番" if total_fan is not None else "番数未知"
        print(f"{self.WIND[w_idx]}家 {self.script_data['p'][w_idx]['n']} 和牌! 总计: {tf_str} ({flower_str})")
        
        for fan_id_str, fan_val in fan_details.items():
            fan_id = int(fan_id_str)
            if fan_id == 83: continue
            fan_points = fan_val & 0xFF
            count = (fan_val >> 8) + 1
            fan_name = FAN_NAMES[fan_id] if 0 <= fan_id < len(FAN_NAMES) else f"未知番种({fan_id})"
            print(f"  {fan_name}: {fan_points}番" + (f" x{count}" if count > 1 else ""))

    def get_win_analysis(self):
        if not self.win_info:
            return None

        w_idx = self.win_info['winner']
        win_data = self.script_data['y'][w_idx]
        total_fan = win_data.get('f') if isinstance(win_data, dict) else None
        fan_details = win_data.get('t', {}) if isinstance(win_data, dict) else {}

        FAN_NAMES = ['无','大四喜','大三元','绿一色','九莲宝灯','四杠','连七对','十三幺','清幺九','小四喜','小三元','字一色','四暗刻','一色双龙会','一色四同顺','一色四节高','一色四步高','一色四连环','三杠','混幺九','七对','七星不靠','全双刻','清一色','一色三同顺','一色三节高','全大','全中','全小','清龙','三色双龙会','一色三步高','一色三连环','全带五','三同刻','三暗刻','全不靠','组合龙','大于五','小于五','三风刻','花龙','推不倒','三色三同顺','三色三节高','无番和','妙手回春','海底捞月','杠上开花','抢杠和','碰碰和','混一色','三色三步高','五门齐','全求人','双暗杠','双箭刻','全带幺','不求人','双明杠','和绝张','箭刻','圈风刻','门风刻','门前清','平和','四归一','双同刻','双暗刻','暗杠','断幺','一般高','喜相逢','连六','老少副','幺九刻','明杠','缺一门','无字','独听・边张','独听・嵌张','独听・单钓','自摸','花牌','明暗杠','\u203b 天和','\u203b 地和','\u203b 人和Ⅰ','\u203b 人和Ⅱ']

        calculated_fan_sum = 0
        for fan_id_str, fan_val in fan_details.items():
            fan_id = int(fan_id_str)
            if fan_id == 83:
                continue
            fan_points = fan_val & 0xFF
            count = (fan_val >> 8) + 1
            calculated_fan_sum += fan_points * count

        actual_flower_count = self.flower_counts[w_idx]
        if total_fan is None:
            total_fan = calculated_fan_sum + actual_flower_count
            base_fan = calculated_fan_sum
        else:
            base_fan = max(total_fan - actual_flower_count, 0)
        flower_count = actual_flower_count

        win_tile_str = self.get_tile_str(self.win_info['win_tile'])
        game_title = self.script_data['g']['t']

        hand_tiles_str = [self.get_tile_str(t) for t in self.hands[w_idx]]
        suits = {'m': [], 'p': [], 's': [], 'z': []}
        for tile in hand_tiles_str:
            num, suit_char = (tile[:-1], tile[-1]) if tile[:-1] else (tile[0], '')
            if suit_char in suits:
                suits[suit_char].append(num)
            else:
                suits['z'].append(num)
        formatted_hand_parts = []
        for suit_char in ['m', 'p', 's', 'z']:
            if suits[suit_char]:
                nums_str = ''.join(sorted(suits[suit_char]))
                formatted_hand_parts.append(f"{nums_str}{suit_char if suit_char != 'z' else ''}")
        hand_str = ' '.join(formatted_hand_parts)
        packs_str_parts = [f"[{''.join(p)}]" for p in self.packs_output[w_idx]]
        formatted_hand = f"{hand_str} {' '.join(packs_str_parts)}".strip()

        fan_vector = [0] * len(FAN_NAMES)
        for fan_id_str, fan_val in fan_details.items():
            fan_id = int(fan_id_str)
            if 0 <= fan_id < len(FAN_NAMES):
                count = (fan_val >> 8) + 1
                fan_vector[fan_id] = count

        return {
            "winner_name": self.script_data['p'][w_idx]['n'],
            "base_fan": base_fan,
            "flower_count": flower_count,
            "total_fan": total_fan,
            "formatted_hand": formatted_hand,
            "fan_vector": fan_vector,
            "fan_names": FAN_NAMES,
            "winning_tile": win_tile_str,
            "game_title": game_title
        }

    def _winner_wind_char(self, winner_idx: int) -> str:
        return ['E','S','W','N'][winner_idx % 4]

    def _round_wind_char(self) -> str:
        gi = self.script_data.get('i')
        if isinstance(gi, int):
            return ['E','S','W','N'][(gi // 4) % 4]
        return 'E'

    def _is_last_copy(self, tile: int) -> bool:
        if not self.win_info:
            return False
        base = tile >> 2
        w_idx = self.win_info['winner']
        is_self = self.win_info['is_self_drawn']
        exposed_melds = 0
        for p_idx in range(4):
            for j, pack in enumerate(self.packs[p_idx]):
                p_type, base_tile_str, offer = pack
                if p_type == 'GANG' and offer == 0:
                    continue
                meld = self.packs_output[p_idx][j] if j < len(self.packs_output[p_idx]) else []
                for ts in meld:
                    ts_clean = ts.strip('()')
                    if ts_clean in self.TILE_IDENTITY and self.TILE_IDENTITY.index(ts_clean) == base:
                        exposed_melds += 1
        exposed_discards = 0
        for dlist in self.discards:
            for t in dlist:
                if (t >> 2) == base:
                    exposed_discards += 1

        winner_exposed_has = False
        for j, pack in enumerate(self.packs[w_idx]):
            p_type, _, offer = pack
            if p_type == 'GANG' and offer == 0:
                continue
            meld = self.packs_output[w_idx][j] if j < len(self.packs_output[w_idx]) else []
            for ts in meld:
                ts_clean = ts.strip('()')
                if ts_clean in self.TILE_IDENTITY and self.TILE_IDENTITY.index(ts_clean) == base:
                    winner_exposed_has = True
                    break
            if winner_exposed_has:
                break
        if winner_exposed_has:
            return False

        winner_hand_no_win = list(self.hands[w_idx])
        removed_one = False
        for i, t in enumerate(winner_hand_no_win):
            if (t >> 2) == base:
                winner_hand_no_win.pop(i)
                removed_one = True
                break
        if not removed_one:
            return False
        for t in winner_hand_no_win:
            if (t >> 2) == base:
                return False

        if is_self:
            exposed_before = exposed_melds + exposed_discards
            return exposed_before == 3
        else:
            exposed_after = exposed_melds + exposed_discards
            exposed_before = exposed_after - 1
            return exposed_before == 3

    def _is_sea_last(self, is_self_drawn: bool) -> bool:
        return self.wall_front_ptr > self.wall_back_ptr

    def _is_robbing_kong(self, is_self_drawn: bool) -> bool:
        if is_self_drawn:
            return False
        return getattr(self, 'last_action_was_kong', False)

    def _build_env_flag(self) -> str:
        if not self.win_info:
            return ''
        w_idx = self.win_info['winner']
        is_self = self.win_info['is_self_drawn']
        win_tile = self.win_info['win_tile']
        round_w = self._round_wind_char()
        seat_w = self._winner_wind_char(w_idx)
        last_copy = '1' if self._is_last_copy(win_tile) else '0'
        sea_last = '1' if self._is_sea_last(is_self) else '0'
        rob_kong = '1' if self._is_robbing_kong(is_self) else '0'
        self_draw_flag = '1' if is_self else '0'
        return f"{round_w}{seat_w}{self_draw_flag}{last_copy}{sea_last}{rob_kong}"

    def _pack_to_string(self, pack_tuple, pack_shape):
        p_type, base_tile_str, offer = pack_tuple
        if len(base_tile_str) == 1:  # 字牌直接重复，不做花色转换
            num = base_tile_str
            suit_char = ''
        else:
            suit_char = base_tile_str[-1]
            num = base_tile_str[:-1]
        if p_type == 'CHI':
            tiles = [ts.strip('()') for ts in pack_shape]
            nums = ''.join(sorted([t[:-1] for t in tiles]))
            chi_id = offer
            return f"[{nums}{suit_char},{chi_id}]"
        elif p_type == 'PENG':
            nums = num * 3
            return f"[{nums}{suit_char}{',' + str(offer) if offer else ''}]".rstrip(',')
        elif p_type == 'GANG':
            nums = num * 4
            return f"[{nums}{suit_char}{',' + str(offer) if offer else ''}]".rstrip(',')
        return ''

    def _build_hand_string_for_gb(self) -> str:
        if not self.win_info:
            return ''
        return self._build_hand_string_for_gb_with_override(None)

    def _build_hand_string_for_gb_with_override(self, win_tile_override: Any) -> str:
        if not self.win_info:
            return ''
        w_idx = self.win_info['winner']
        flower_list = self.flower_tile[w_idx]
        flower_digits = ''
        if flower_list:
            flower_digits = str(len(flower_list))
        win_tile = win_tile_override if win_tile_override is not None else self.win_info['win_tile']
        sorted_tiles = sorted(self.hands[w_idx])
        removed = False
        for i, t in enumerate(sorted_tiles):
            if (t >> 2) == (win_tile >> 2):
                sorted_tiles.pop(i)
                removed = True
                break
        if removed:
            sorted_tiles.append(win_tile)
        raw_tiles = [self.get_tile_str(t) for t in sorted_tiles]
        win_tile_str = self.get_tile_str(win_tile)
        win_is_honor = len(win_tile_str) == 1
        non_win_tiles = raw_tiles[:-1]
        suit_groups = {'m': [], 'p': [], 's': []}
        honor_tiles = []
        for ts in non_win_tiles:
            if len(ts) == 2 and ts[1] in suit_groups:
                suit_groups[ts[1]].append(ts[0])
            else:
                honor_tiles.append(ts)
        for k in suit_groups:
            suit_groups[k].sort()
        order_suits = ['m', 'p', 's']
        if not win_is_honor:
            win_suit = win_tile_str[-1]
            order_suits = [s for s in order_suits if s != win_suit] + [win_suit]
        hand_parts = []
        for s in order_suits:
            if suit_groups[s]:
                hand_parts.append(''.join(suit_groups[s]) + s)
        honor_tiles.sort()
        hand_parts.extend(honor_tiles)
        hand_parts.append(win_tile_str)
        hand_body = ''.join(hand_parts)
        meld_parts = []
        for i, pack in enumerate(self.packs[w_idx]):
            shape = self.packs_output[w_idx][i]
            meld_parts.append(self._pack_to_string(pack, shape))
        meld_str = ''.join(meld_parts)
        env_flag = self._build_env_flag()
        if env_flag:
            if flower_digits:
                return f"{meld_str}{hand_body}|{env_flag}|{flower_digits}"
            else:
                return f"{meld_str}{hand_body}|{env_flag}"
        return f"{meld_str}{hand_body}"

    def compute_gb_fan(self):
        if not self.win_info:
            return None
        hand_str = self._build_hand_string_for_gb()
        env_flag = self._build_env_flag()
        w_idx = self.win_info['winner']
        win_data = self.script_data['y'][w_idx]
        official_total = win_data.get('f') if isinstance(win_data, dict) else None
        fan_details = win_data.get('t', {}) if isinstance(win_data, dict) else {}
        official_base = 0
        for fan_id_str, fan_val in fan_details.items():
            fan_id = int(fan_id_str)
            if fan_id == 83:
                continue
            fan_points = fan_val & 0xFF
            count = (fan_val >> 8) + 1
            official_base += fan_points * count
        import subprocess, json as _json
        try:
            proc = subprocess.run([
                'node', 'compute_fan.mjs'
            ], input=_json.dumps({'hand': hand_str}).encode('utf-8'), stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            node_res = _json.loads(proc.stdout.decode('utf-8').strip() or '{}')
        except Exception as e:
            node_res = {'error': str(e)}
        gb_total = node_res.get('total_fan')
        gb_base = node_res.get('base_fan')
        diff = None
        if gb_total is not None and official_total is not None:
            diff = gb_total - official_total
        return {
            'hand_string': hand_str,
            'env_flag': env_flag,
            'gb_total_fan': gb_total,
            'gb_base_fan': gb_base,
            'official_total_fan': official_total,
            'official_base_fan': official_base,
            'diff': diff,
            'node_detail': node_res
        }

    def get_official_fan_list(self):
        if not self.win_info:
            return []
        w_idx = self.win_info['winner']
        win_data = self.script_data['y'][w_idx]
        if not isinstance(win_data, dict):
            return []
        fan_details = win_data.get('t', {}) or {}
        FAN_NAMES = ['无','大四喜','大三元','绿一色','九莲宝灯','四杠','连七对','十三幺','清幺九','小四喜','小三元','字一色','四暗刻','一色双龙会','一色四同顺','一色四节高','一色四步高','一色四连环','三杠','混幺九','七对','七星不靠','全双刻','清一色','一色三同顺','一色三节高','全大','全中','全小','清龙','三色双龙会','一色三步高','一色三连环','全带五','三同刻','三暗刻','全不靠','组合龙','大于五','小于五','三风刻','花龙','推不倒','三色三同顺','三色三节高','无番和','妙手回春','海底捞月','杠上开花','抢杠和','碰碰和','混一色','三色三步高','五门齐','全求人','双暗杠','双箭刻','全带幺','不求人','双明杠','和绝张','箭刻','圈风刻','门风刻','门前清','平和','四归一','双同刻','双暗刻','暗杠','断幺','一般高','喜相逢','连六','老少副','幺九刻','明杠','缺一门','无字','独听・边张','独听・嵌张','独听・单钓','自摸','花牌','明暗杠','\u203b 天和','\u203b 地和','\u203b 人和Ⅰ','\u203b 人和Ⅱ']
        result = []
        for fan_id_str, fan_val in fan_details.items():
            fan_id = int(fan_id_str)
            if fan_id == 83:
                continue
            score = fan_val & 0xFF
            count = (fan_val >> 8) + 1
            name = FAN_NAMES[fan_id] if 0 <= fan_id < len(FAN_NAMES) else f"未知番种({fan_id})"
            result.append({'id': fan_id, 'name': name, 'score': score, 'count': count})
        return result

    def print_fan_compare(self):
        res = self.compute_gb_fan()
        if not res:
            print('[INFO] 荒庄，无法比较番数。')
            return
        print('[DEBUG] GB 重算输入:', res['hand_string'])
        if 'error' in res.get('node_detail', {}):
            print('[ERROR] Node 重算失败:', res['node_detail']['error'])
            return
        print(f"官方番数: total={res['official_total_fan']} base={res['official_base_fan']}")
        print(f"GB重算:   total={res['gb_total_fan']} base={res['gb_base_fan']} diff={res['diff']}")
        fan_list = res['node_detail'].get('fan_list', [])
        if fan_list:
            print('GB番种明细:')
            for item in fan_list:
                print(f"  {item['name']}({item['score']}) x{item['count']}")

