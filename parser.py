import json
import base64
import zlib
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

try:
    from MahjongGB import MahjongFanCalculator

    MAHJONG_GB_AVAILABLE = True
except ImportError:
    MAHJONG_GB_AVAILABLE = False


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
        'E', 'W', 'S', 'N', 'C', 'F', 'B'
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
        self.initial_hands = [[] for _ in range(4)]

        self.win_info = None
        self.last_discard_info = {}
        self.current_player_idx = -1
        self.last_action_was_kong = False
        self.wall = []
        self.wall_front_ptr = 0
        self.wall_back_ptr = 0

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

    # c1 = tile_val - 4 + ((data >> 10) & 3)
    # c2 = tile_val + ((data >> 12) & 3)
    # c3 = tile_val + 4 + ((data >> 14) & 3)

    def _setup_wall_and_deal(self):
        wall_indices = [int(self.script_data['w'][i:i + 2], 16) for i in range(0, len(self.script_data['w']), 2)]
        dice = [self.script_data['d'] & 15, (self.script_data['d'] >> 4) & 15,
                (self.script_data['d'] >> 8) & 15, (self.script_data['d'] >> 12) & 15]
        # print(dice)
        dealer_idx = self.script_data['i'] % 4

        for p in range(4):
            if self.WIND[p] == '东':
                dealer_idx = p

        wall_break_pos = (dealer_idx - (dice[0] + dice[1] - 1) + 4) % 4
        start_pos = (wall_break_pos * 36) + (dice[0] + dice[1] + dice[2] + dice[3]) * 2
        start_pos = start_pos % 144

        # print(start_pos, wall_break_pos, dealer_idx)

        self.wall = wall_indices[start_pos:] + wall_indices[:start_pos]
        self.wall_back_ptr = len(self.wall) - 1

        for i in range(3):
            for p_offset in range(4):
                player_idx = (dealer_idx + p_offset) % 4
                draw = self.wall[self.wall_front_ptr: self.wall_front_ptr + 4]
                self.hands[player_idx].extend(draw)
                self.wall_front_ptr += 4
                # print([self.get_tile_str(t) for t in draw])

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
        # print(config_str)

        start_time_unix = self.script_data['t'] / 1000
        end_time_unix = start_time_unix + (self.actions[-1]['t'] / 1000 if self.actions else 0)
        tz = timezone(timedelta(hours=8))
        start_dt = datetime.fromtimestamp(start_time_unix, tz).strftime('%Y-%m-%d %H:%M:%S UTC%z')
        end_dt = datetime.fromtimestamp(end_time_unix, tz).strftime('%Y-%m-%d %H:%M:%S UTC%z')

        # print(f"开始时间：{start_dt}")
        # print(f"结束时间：{end_dt}")

        # print("\n--- 玩家信息 ---")
        # for i in range(4):
        #     print(f"{self.WIND[i]}家: {p_info[i]['n']} (分数: {p_info[i]['s']})")

    def run_analysis(self):
        self._print_game_info()
        self._setup_wall_and_deal()

        # print("\n--- 初始配牌 ---")
        # for i in range(4):
        #     hand_str = ' '.join(self.initial_hands[i])
        #     print(f"{self.WIND[i]}家 {self.script_data['p'][i]['n']}:\t {hand_str}")

        # print("\n--- 对局过程 ---")
        prev_time = 0

        for act in self.actions:
            p_idx, a_type, data, time = act['p'], act['a'], act['d'], act['t']
            player_info = f"{self.WIND[p_idx]}家 {self.script_data['p'][p_idx]['n']}"
            time_str = f"[{((time - prev_time) / 1000.0):.3f}s]"

            output = f"{player_info} "
            lo_byte, hi_byte = data & 0xFF, (data >> 8) & 0xFF

            if a_type == 0:
                output += "开始出牌"
            elif a_type == 1:
                self.flower_counts[p_idx] += 1
                ot = (hi_byte & 15) + 136
                # print(self.hands[p_idx])
                # print(ot)
                self.hands[p_idx].remove(ot)
                self.hands[p_idx].append(lo_byte)
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

                if pack_type == "CHI":
                    offer_tile = self.last_discard_info['tile']
                    # print(tile_val, offer_tile)
                    if tile_val - 4 + ((data >> 10) & 3) < 0:
                        tile_val = offer_tile
                    c1 = tile_val - 4 + ((data >> 10) & 3)
                    c2 = tile_val + ((data >> 12) & 3)
                    c3 = tile_val + 4 + ((data >> 14) & 3)
                    chi_tiles = [c1, c2, c3]
                    chi_id = 1
                    chi_shape = []
                    # chi_tiles.remove(offer_tile)
                    # print([self.get_tile_str(t) for t in chi_tiles])
                    for t in range(3):
                        if chi_tiles[t] >> 2 == offer_tile >> 2:
                            chi_id = t + 1
                            chi_shape.append(f"({self.get_tile_str(chi_tiles[t])})")
                        else:
                            # print(self.hands[p_idx], chi_tiles)
                            for _ in self.hands[p_idx]:
                                if (_ >> 2) == (chi_tiles[t] >> 2):
                                    self.hands[p_idx].remove(_)
                                    break
                            # self.hands[p_idx].remove(chi_tiles[t])
                            chi_shape.append(self.get_tile_str(chi_tiles[t]))
                    self.packs[p_idx].append(("CHI", self.get_tile_GB_str(tile_val), chi_id))
                    self.packs_output[p_idx].append(chi_shape)
                    print(self.packs_output[p_idx])
                    output += f"吃 {self.get_tile_str(offer_tile)}"
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
                elif pack_type == "GANG":
                    self.last_action_was_kong = True
                    action = "加杠" if (data & 0x0300) == 0x0300 else "杠"
                    if action == "加杠":
                        # self.hands[p_idx].remove(tile_val)
                        hand_copy = list(self.hands[p_idx])
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
                        print([self.get_tile_str(t) for t in self.hands[p_idx]])
                        self.packs[p_idx].append(("GANG", self.get_tile_GB_str(tile_val), 0))
                        self.packs_output[p_idx].append([self.get_tile_str(tile_val) for _ in range(4)])
                    else:  # Melded
                        for _ in range(3):
                            count = 0
                            for t in self.hands[p_idx]:
                                if (t >> 2) == (tile_val >> 2) and count < 3:
                                    self.hands[p_idx].remove(t)
                                    count += 1
                            # self.hands[p_idx].remove(tile_val)
                        self.packs[p_idx].append(("GANG", self.get_tile_GB_str(tile_val), (data >> 6) & 3))
                        self.packs_output[p_idx].append([self.get_tile_str(tile_val) for _ in range(4)])
                    output += f"{action} {self.get_tile_str(tile_val)}"
                # self.discards[offer_from_idx].pop()
            elif a_type == 6:
                is_self_drawn = p_idx == self.current_player_idx
                win_tile = self.hands[p_idx][-1] if is_self_drawn else self.last_discard_info['tile']
                self.win_info = {'winner': p_idx, 'win_tile': win_tile, 'is_self_drawn': is_self_drawn}
                if not is_self_drawn: self.hands[p_idx].append(win_tile)
                fan = data >> 1
                fan_str = f"{fan}番" if fan > 0 else ""
                output += f"{'自动' if data & 1 else '手动'}和 {fan_str}"
            elif a_type == 7:
                self.current_player_idx = p_idx
                tile_to_draw = lo_byte
                self.hands[p_idx].append(tile_to_draw)
                draw_type = '摸牌' if not hi_byte else '逆向摸牌'
                output += f"{draw_type} {self.get_tile_str(tile_to_draw)}"
            elif a_type == 8:
                output += "过"
            elif a_type == 9:
                output += "弃"
            print(f"{output} {time_str}")
            hand = [self.get_tile_str(t) for t in self.hands[p_idx]]
            hand.sort()
            print(hand)
            prev_time = time

        print("\n--- 最终结果 ---")
        if not self.win_info:
            print("对局为荒庄")
        else:
            self._calculate_fan()

        # print("\n--- 各家舍牌 ---")
        # for i in range(4):
        #     discard_str = ' '.join([self.get_tile_str(t) for t in self.discards[i]])
        #     print(f"{self.WIND[i]}家 {self.script_data['p'][i]['n']}: {discard_str}")

        print("\n--- 最终手牌 ---")
        for i in range(4):
            self.hands[i].sort()
            hand_str = ' '.join([self.get_tile_str(t) for t in self.hands[i]])
            packs_str = ' '.join([f"[{''.join(p)}]" for p in self.packs_output[i]])
            print(f"{self.WIND[i]}家 {self.script_data['p'][i]['n']}: {hand_str}  {packs_str}")

    def _calculate_fan(self):
        if not MAHJONG_GB_AVAILABLE:
            print("MahjongGB 库未安装，无法进行算番。请运行 'pip install MahjongGB'")
            return

        w_idx = self.win_info['winner']
        win_tile_str = self.get_tile_GB_str(self.win_info['win_tile'])

        hand_tiles = [self.get_tile_GB_str(t) for t in self.hands[w_idx]]
        if win_tile_str in hand_tiles:
            hand_tiles.remove(win_tile_str)

        all_tiles_revealed = []
        for p_discard in self.discards:
            all_tiles_revealed.extend([self.get_tile_str(t) for t in p_discard])
        for p_packs in self.packs:
            for p_type, p_tile_str, _ in p_packs:
                if p_type == "PENG":
                    all_tiles_revealed.extend([p_tile_str] * 2)
                elif p_type == "GANG":
                    all_tiles_revealed.extend([p_tile_str] * 3)

        all_tiles_revealed.sort()
        # print(all_tiles_revealed)
        # print(f"{self.WIND[w_idx]}家 {self.script_data['p'][w_idx]['n']} " + ("自摸：" if self.win_info['is_self_drawn'] else "点和：") + self.get_tile_str(self.win_info['win_tile']))
        # print(all_tiles_revealed.count(self.get_tile_str(self.win_info['win_tile'])))
        tiles_num = all_tiles_revealed.count(self.get_tile_str(self.win_info['win_tile']))
        is_4th_tile = False
        if tiles_num == 3 and self.win_info['is_self_drawn']:
            is_4th_tile = True
        if tiles_num == 4:
            is_4th_tile = True

        calculator_args = {
            'pack': tuple(self.packs[w_idx]),
            'hand': tuple(hand_tiles),
            'winTile': win_tile_str,
            # 'flowerCount': self.flower_counts[w_idx],
            'flowerCount': 0,
            'isSelfDrawn': self.win_info['is_self_drawn'],
            'is4thTile': is_4th_tile,
            'isAboutKong': self.last_action_was_kong,
            'isWallLast': self.wall_front_ptr > self.wall_back_ptr,
            'seatWind': w_idx,
            'prevalentWind': self.script_data['i'] // 4,
            'verbose': True
        }

        try:
            fans = MahjongFanCalculator(**calculator_args)
            total_fan = sum(f[0] * f[1] for f in fans)
            print(f"{self.WIND[w_idx]}家 {self.script_data['p'][w_idx]['n']} 和牌! 总计: {total_fan}番")
            for fan_points, count, fan_name_cn, fan_name_en in fans:
                print(f"  {fan_name_cn}: {fan_points}番" + (f" x{count}" if count > 1 else ""))
        except Exception as e:
            print(f"算番时发生错误: {e}")
