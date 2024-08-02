import random
import time
import math

def calc_resp(work_time, lv): # return 第一个是 给的GP值， 第二个是hidden_value
    if work_time >= 43200:
        gp_add = int(((work_time - 28800) // 80 + 1100 * math.sqrt(lv)) / 2)
        return gp_add, 0
    elif work_time >= 28800:
        gp_add = int((work_time - 28800) // 80 + 1100 * math.sqrt(lv))
        hdv = int(math.sqrt(lv) * random.randint(55, 110))
        return gp_add, hdv
    else:
        gp_add = int(random.randint(500, int(1000 + work_time / 288)) * math.sqrt(lv) * (work_time / 28800) ** 2)
        hdv = int(math.sqrt(lv) * random.randint(55, int(110 - (work_time / 28800) ** 2 / 30)) * (work_time / 28800) ** 2)
        return gp_add, hdv


def work_start(user, uid):
    try:
        if user[str(uid)]["work"]["start_time"] != 0:
            return "你已经在打工了捏"
    except:
        pass
    user[str(uid)]["work"] = {
        "start_time": time.time()
    }
    return "打工开始！"

def work_end(user, uid):
    try:
        start = user[str(uid)]["work"]["start_time"]
    except:
        return "你今天还没开始打工捏"
    
    if start == 0:
        return "你今天还没开始打工捏"
    
    user[str(uid)]["work"]["start_time"] = 0
    lv = user[str(uid)]["lv"]

    work_time = time.time() - start # 0 - 43200 为合理范围

    gp_add, hdv = calc_resp(work_time, lv)

    user[str(uid)]["gp"] = int(user[str(uid)]["gp"] + gp_add)
    user[str(uid)]["hidden_value"] = user[str(uid)]["hidden_value"] + hdv 

    return f"打工时间: {int(work_time/3600)}h {int(work_time%3600/60)}m {int(work_time%60)}s\nGP: {user[str(uid)]['gp']} (+{gp_add})"
