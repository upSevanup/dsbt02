import json
import random
from collections import Counter


def load_json(name):
    with open(name, encoding="utf-8") as jf:
        return json.load(jf)


def write_json(name, content):
    with open(name, "w") as fff:
        json.dump(content, fff, ensure_ascii=True, indent=4)


def poker():
    combos = ['ничего', 'пара', 'две пары', 'сет', 'фулл хаус', 'каре', 'покер']

    player = []

    for i in range(5):
        player.append(random.randint(1, 6))

    pl_combo = Counter(player)
    pl_res = ''
    score = 0
    for key in pl_combo.keys():
        if pl_combo[key] > 1:
            pl_res += str(pl_combo[key])
            score += key * pl_combo[key]

    if pl_res == '2':
        pl_res = combos[1]
    elif pl_res == '22':
        pl_res = combos[2]
    elif pl_res == '3':
        pl_res = combos[3]
    elif pl_res == '23' or pl_res == '32':
        pl_res = combos[4]
    elif pl_res == '4':
        pl_res = combos[5]
    elif pl_res == '5':
        pl_res = combos[6]
    else:
        pl_res = combos[0]

    return pl_res, score, player
