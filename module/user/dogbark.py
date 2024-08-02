import re
import random
import time

def get_dogbark_info(uid, user, sender, message, nickname):
    if re.search(r"\[CQ:at,qq=(\d+)\]", message) != None:
        uid = int(re.search(r"\[CQ:at,qq=(\d+)\]", message).groups()[0])
        try:
            sender = nickname[str(uid)]
        except:
            sender = uid
    user_uidList = list(user.keys())
    random.shuffle(user_uidList)
    dogbark = []
    for id in user_uidList:
        dogbark.append((id, user[id]["dogbark"]["dogbark_count"]))
        dogbark = sorted(dogbark, key=lambda x: (x[1]), reverse=True)
    
    dogbark_data = user[str(uid)]["dogbark"]
    rank = dogbark.index((str(uid), dogbark_data["dogbark_count"])) + 1
    if rank == 1:
        previous_count = 0
    else:
        previous_count = dogbark_data["dogbark_count"] - dogbark[rank - 2][1]
        k = 0
        while previous_count == 0:
            k += 1
            previous_count = dogbark_data["dogbark_count"] - dogbark[rank - 2 - k][1]
    
    level = 0
    m = 0
    while dogbark_data["dogbark_count"] >= m:
        m += 10 * 2 ** (level // 10)
        level += 1

    
    message_return = f'{sender} Lv.{level}\n狗叫排名:#{rank}/{len(user_uidList)} ({previous_count})\n总狗叫次数:{dogbark_data["dogbark_count"]}\n今日狗叫次数:{dogbark_data["today_dogbark"]}\n上次狗叫时间:{time.strftime(r"%Y/%m/%d %H:%M", time.localtime(dogbark_data["last_dogbark"]))}'
    return message_return

def get_stat(user):
    user_uidList = list(user.keys())
    total = 0
    daily = 0
    for id in user_uidList:
        total += user[id]["dogbark"]["dogbark_count"]
        daily += user[id]["dogbark"]["today_dogbark"]
    message_return = f"总狗叫次数:{total}\n今日总狗叫次数:{daily}"
    return message_return

def get_dogbark_rank(user, uid, sender, nickname, n=1):
    user_uidList = list(user.keys())
    random.shuffle(user_uidList)
    dogbark = []
    message = "狗叫排行:\n"
    for id in user_uidList:
        dogbark.append((id, user[id]["dogbark"]["dogbark_count"]))
    
    dogbark = sorted(dogbark, key=lambda x: (x[1]), reverse=True)

    
    count = n
    for id in dogbark[n-1:n+9]:
        try:
            nickname_self = nickname[id[0]]
        except:
            nickname_self = id[0]
        message += f"{count}. {nickname_self} - {id[1]}\n"
        count += 1
    
    message += "==========\n"

    user_dogbark = user[str(uid)]["dogbark"]["dogbark_count"]

    rank = dogbark.index((str(uid), user_dogbark)) + 1
    
    message += f"{rank}. {sender['nickname']} - {user_dogbark}"

    return message

def get_daily_dogbark_rank(user, uid, sender, nickname, n=1):
    user_uidList = list(user.keys())
    random.shuffle(user_uidList)
    dogbark = []
    message = "今日狗叫排行:\n"
    for id in user_uidList:
        dogbark.append((id, user[id]["dogbark"]["today_dogbark"]))
    
    dogbark = sorted(dogbark, key=lambda x: (x[1]), reverse=True)
    
    count = n
    for id in dogbark[n-1:n+9]:
        try:
            nickname_self = nickname[id[0]]
        except:
            nickname_self = id[0]
        if id[1] == 0:
            continue
        message += f"{count}. {nickname_self} - {id[1]}\n"
        count += 1
    
    message += "==========\n"

    user_dogbark = user[str(uid)]["dogbark"]["today_dogbark"]

    rank = dogbark.index((str(uid), user_dogbark)) + 1
    
    message += f"{rank}. {sender['nickname']} - {user_dogbark}"

    return message

def append_wordings(message):
    wordings = message.split(" ", 2)[2]
    other = ""
    if re.search(r"\[(.+)\]", wordings) != None:
        wordings = re.search(r"\[(.+)\]", wordings).group()[1:][:-1]
        other = f"\n检测到非法字符，已经自动更正为{wordings}"
    dogbark_sentence = open("./src/dogbark.txt").read().splitlines()
    dogbark_sentence.append(wordings)
    dogbark_string = ""
    for sent in dogbark_sentence:
        dogbark_string += sent + "\n"
    open("./src/dogbark.txt", "w").write(dogbark_string[:-1])
    return "updated" + other

def get_dogbark_king_rank(user, uid, sender, nickname):
    user_uidList = list(user.keys())
    random.shuffle(user_uidList)
    dogbark = []
    message = "单日狗王次数排行:\n"
    for id in user_uidList:
        dogbark.append((id, user[id]["dogbark"]["top"]))
    
    dogbark = sorted(dogbark, key=lambda x: (x[1]), reverse=True)
    
    count = 1
    for id in dogbark[:10]:
        try:
            nickname_self = nickname[id[0]]
        except:
            nickname_self = id[0]
        if id[1] == 0:
            continue
        message += f"{count}. {nickname_self} - {id[1]}\n"
        count += 1
    
    message += "==========\n"

    user_dogbark = user[str(uid)]["dogbark"]["top"]

    rank = dogbark.index((str(uid), user_dogbark)) + 1
    
    message += f"{rank}. {sender['nickname']} - {user_dogbark}"

    return message

def hdvrank(user, uid, sender, nickname):
    user_uidList = list(user.keys())
    random.shuffle(user_uidList)
    dogbark = []
    message = "????:\n"
    for id in user_uidList:
        dogbark.append((id, user[id]["hidden_value"]))
    
    dogbark = sorted(dogbark, key=lambda x: (x[1]), reverse=True)
    
    count = 1
    for id in dogbark[:10]:
        try:
            nickname_self = nickname[id[0]]
        except:
            nickname_self = id[0]
        if id[1] == 0:
            continue
        message += f"{count}. {nickname_self} - {id[1]}\n"
        count += 1
    
    message += "==========\n"

    user_dogbark = user[str(uid)]["hidden_value"]

    rank = dogbark.index((str(uid), user_dogbark)) + 1
    
    message += f"{rank}. {sender['nickname']} - {user_dogbark}"

    return message