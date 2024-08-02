import numpy as np
import time
import random

user = {'2154319688': {'gp': 349644, 'lv': 29, 'exp': 8209, 'last_sign': 1706286549.2932322, 'day': 34, 'jrys': {'宜': ['收歌'], '不宜': ['开键盘歌'], 'lucky_number': 63, 'last_jrys': 1694455634.6102688}, 'hidden_value': 108, 'dogbark': {'dogbark_count': 1491, 'today_dogbark': 1, 'last_dogbark': 1706371305.7458959, 'top': 0}, 'daphnis': {'length': 12.613292112914333, 'count': 3, 'time': 1706371929.263566, 'change': 0, 'change_time': 0}, 'work': {'start_time': 1706291771.770587}}}

def generate_penis(user, uid):
    try:
        if user[str(uid)]["daphnis"]["time"] + 7 * 86400 > time.time():
            return f'暂时不允许重置长度捏，请{int(user[str(uid)]["daphnis"]["time"] + 7 * 86400 - time.time())}秒后再试吧'
    except:
        pass
    standard = np.random.normal(loc=13.12, scale=1.66)
    user[str(uid)]["daphnis"] = {
        "length": standard,
        "count": 20,
        "time": time.time(),
        "change_time": 0,
        "change": 0
    }
    return f"生成成功！\n长度为: {round(standard, 2)}"

def change_penis(user, uid):
    try:
        if ((user[str(uid)]["daphnis"]["change_time"] + 15) > time.time()) and uid != 2154319688:
            return f'暂时不允许更改长度捏，请{int(user[str(uid)]["daphnis"]["change_time"] + 15 - time.time())}秒后再试吧'
        elif user[str(uid)]["daphnis"]["count"] <= 0:
            message = f"更改成功！由于次数已经用完，所以消耗2500GP以增加一次次数！\nGP: {user[str(uid)]['gp'] - 2500}\n"
            if user[str(uid)]["gp"] > 2500:
                user[str(uid)]["gp"] -= 2500
            else:
                return "更改失败...余额不足...\n"
        else:
            message = "更改成功！次数-1捏！\n"
        seed = round(random.uniform(-0.5, 0.5), 4)
        user[str(uid)]["daphnis"]["length"] += seed
        user[str(uid)]["daphnis"]["change"] += seed
        user[str(uid)]["daphnis"]["change_time"] = time.time()
        user[str(uid)]["daphnis"]["count"] -= 1
        if seed > 0:
            seed = "+" + str(seed)
        else:
            seed = str(seed)
        message += f'Length: {round(user[str(uid)]["daphnis"]["length"], 4)} ({seed})\nTotal Change: {round(user[str(uid)]["daphnis"]["change"], 4)}'
        return message
    except:
        return "发生错误了捏！会不会是你没有生成？\n可以使用 [/江江 scjb] 生成一下呢"

def change_penis_premium(user, uid):
    try:
        if ((user[str(uid)]["daphnis"]["change_time"] + 15) > time.time()) and uid != 2154319688:
            return f'暂时不允许更改长度捏，请{int(user[str(uid)]["daphnis"]["change_time"] + 15 - time.time())}秒后再试吧'
        elif user[str(uid)]["gp"] > 50000:
            message = f"更改成功！已消耗50000GP！\nGP: {user[str(uid)]['gp'] - 50000}\n"
            user[str(uid)]["gp"] -= 50000
        else:
            return "更改失败...余额不足..."
        seed = round(random.uniform(0.5, 5), 4)
        user[str(uid)]["daphnis"]["length"] += seed
        user[str(uid)]["daphnis"]["change"] += seed
        user[str(uid)]["daphnis"]["change_time"] = time.time()
        user[str(uid)]["daphnis"]["count"] -= 1
        if seed > 0:
            seed = "+" + str(seed)
        else:
            seed = str(seed)
        message += f'Length: {round(user[str(uid)]["daphnis"]["length"], 4)} ({seed})\nTotal Change: {round(user[str(uid)]["daphnis"]["change"], 4)}'
        return message
    except:
        return "发生错误了捏！会不会是你没有生成？\n可以使用 [/江江 scjb] 生成一下呢"

def penis_rank(user, uid, sender, nickname):
    user_uidList = list(user.keys())
    random.shuffle(user_uidList)
    dogbark = []
    message = "__排行(填空题:\n"
    for id in user_uidList:
        try:
            time = user[id]["daphnis"]["change_time"]
            dogbark.append((id, user[id]["daphnis"]["length"]))
        except:
            pass
    
    dogbark = sorted(dogbark, key=lambda x: (x[1]), reverse=True)
    
    count = 1
    for id in dogbark[:10]:
        try:
            nickname_self = nickname[id[0]]
        except:
            nickname_self = id[0]
        if id[1] == 0:
            continue
        message += f"{count}. {nickname_self} - {round(id[1], 4)}\n"
        count += 1
    
    message += "==========\n"

    user_dogbark = user[str(uid)]["daphnis"]["length"]

    rank = dogbark.index((str(uid), user_dogbark)) + 1
    
    message += f"{rank}. {sender['nickname']} - {round(user_dogbark, 4)}"

    return message