import random
import time
import math

def sign(user, uid, sender):
    combo = True
    if (time.time() + 8 * 3600) // 86400 > (user[str(uid)]["last_sign"] + 8 * 3600) // 86400 + 1:
        user[str(uid)]["day"] = 0
        combo = False
    elif (time.time() + 8 * 3600) // 86400 <= (user[str(uid)]["last_sign"] + 8 * 3600) // 86400:
        return "你已经签到过了哦"
    user[str(uid)]["day"] = user[str(uid)]["day"] + 1 # 签到天数+1
    user[str(uid)]["last_sign"] = time.time() # 更新上次签到的时间戳

    # GP up
    seed_basic = random.randint(100, 200)
    seed_adv = random.uniform(0.6, 0.9 + user[str(uid)]["lv"] * 0.06)
    gp_add = int(user[str(uid)]["day"] * 5 + seed_basic + user[str(uid)]["hidden_value"] * seed_adv) * 2 # 计算GP的提升
    # (天数 x 5 + 100~200 随机 (基础) + 隐藏值 * 随机seed (额外)) * 2
    # print出来
    print(user[str(uid)]["day"] * 5, seed_basic, seed_adv, user[str(uid)]["hidden_value"], seed_adv * user[str(uid)]["hidden_value"])
    user[str(uid)]["gp"] = int(user[str(uid)]["gp"] + gp_add)

    # EXP up
    exp_add = int((gp_add * random.uniform(0.5, 1.5) + user[str(uid)]["hidden_value"] * random.uniform(0.34, 0.56 + user[str(uid)]["lv"] * 0.08)) * math.sqrt(user[str(uid)]["lv"])) # 经验值提升
    user[str(uid)]["hidden_value"] = 0
    user[str(uid)]["exp"] = int(user[str(uid)]["exp"] + exp_add)
    while user[str(uid)]["exp"] >= user[str(uid)]["lv"] ** 2 * 100:
        user[str(uid)]["exp"] = user[str(uid)]["exp"] - user[str(uid)]["lv"] ** 2 * 100
        user[str(uid)]["lv"] = user[str(uid)]["lv"] + 1
        user[str(uid)]["gp"] = user[str(uid)]["gp"] + user[str(uid)]["lv"] ** 2 * 8
        gp_add += user[str(uid)]["lv"] ** 2 * 8
    nickname = sender["nickname"]
    message = f"{nickname} Lv.{user[str(uid)]['lv']}\nEXP: {user[str(uid)]['exp']}/{user[str(uid)]['lv'] ** 2 * 100} (+{exp_add})\nGP: {user[str(uid)]['gp']}(+{gp_add})\n你已经连续签到了{user[str(uid)]['day']}天哦~"
    return message

def info(user, uid, sender):
    return f"{sender['nickname']} Lv.{user[str(uid)]['lv']}\nEXP: {user[str(uid)]['exp']}/{user[str(uid)]['lv'] ** 2 * 100}\nGP: {user[str(uid)]['gp']}\n你已经连续签到了{user[str(uid)]['day']}天哦~"

def rank_forbes(user, uid, sender, nickname):
    user_uidList = list(user.keys())
    random.shuffle(user_uidList)
    gp = []
    message = "GP排行:\n"
    for id in user_uidList:
        gp.append((id, user[id]["gp"]))
    
    gp = sorted(gp, key=lambda x: (x[1]), reverse=True)
    
    count = 1
    for id in gp[:10]:
        try:
            nickname_self = nickname[id[0]]
        except:
            nickname_self = id[0]
        message += f"{count}. {nickname_self} - {id[1]}\n"
        count += 1
    
    message += "==========\n"

    user_gp = user[str(uid)]["gp"]

    rank = gp.index((str(uid), user_gp)) + 1
    
    message += f"{rank}. {sender['nickname']} - {user_gp}"

    return message