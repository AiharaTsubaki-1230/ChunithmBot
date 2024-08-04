from aiocqhttp import CQHttp, Event
import json
import time
import logging
import module.user, module.chunithm, module.malody, module.other.csvreader, module.chunithm
# import module.chunithm.course as course
# import module.guess_song
import os
import random
from html import unescape
from urllib.parse import quote
import re
from aiocqhttp.message import MessageSegment


bot = CQHttp(api_root="http://127.0.0.1:5700")
# bot = CQHttp()

# 预加载项

user = json.loads(open("./data/user.json").read())
init = json.loads(open("./data/init.json").read())
nickname = json.loads(open("./data/nickname.json").read())
dogbark = open("./src/dogbark.txt").read().splitlines()

# messageReceived_count = 0
# responseTime = 0

def message_to_cq(message): # 将event.message转义成原先的cq码
    message_merged = ""
    for msg in message:
        if msg["type"] == "text":
            message_merged += msg["data"]["text"]
        else:
            key_list = msg["data"].keys()
            type = msg["type"]
            params = ""
            for key in key_list:
                params += "," + key + "=" + msg["data"][key]
            message_merged += f"[CQ:{type}{params}]"
    return message_merged

LOG_FORMAT = "[%(levelname)s] %(asctime)s %(message)s"
DATE_FORMAT = "%m/%d/%Y %H:%M:%S %p"

logging.basicConfig(filename='log/202406.log', level=logging.CRITICAL, format=LOG_FORMAT, datefmt=DATE_FORMAT)

# handle commands
@bot.on_message
async def _(event: Event):
    gid = event.group_id # 群号 / message.private -> None
    uid = event.user_id # QQ号
    message_id = event.message_id

    if uid == event.self_id or gid in [624670021, 366591885, 730020933, 332135728]: # 过滤掉自己发送的消息
        return
    
    if gid not in [928327528, 121271634, 136880140, 203275784, None]:
        return

    message = unescape(event.message)
    message_cq = message_to_cq(message).strip()

    print(uid, gid, message_id, message_cq)
    sender = event.sender # message.private -> {} / message.group ->　dataがある
    try:
        nickname[str(uid)] = sender["nickname"] # 保存每一个人的QQ昵称
    except:
        pass
    
    if message_cq.startswith("/江江"): # 江江模块 分割到plugin/user/__init__.py进行处理再返回
        print(message_cq)
        if user.get(str(uid)) == None:
            user[str(uid)] = { "gp": 0,"lv": 1,"exp": 0,"last_sign": 0,"day": 1,"jrys": {},"hidden_value": 0,"dogbark": {"dogbark_count": 0,"today_dogbark": 0,"last_dogbark": 0,"top": 0},"daphnis": {"length": 0,"last_time": 0,"maximum": 0,"minimum": 0,"count": 10}}
        message_return = await module.user.handle_command(uid, gid, message_cq, user, sender, nickname, bot, message_id)
        try:
            await bot.send(event, message_return) 
        except:
            pass
    elif message_cq.startswith("/malody"):
        try:
            message_return = module.malody.handle_command(message_cq)
            await bot.send(event, message_return)
        except Exception as e:
            print(repr(e))
    elif message_cq.endswith("是什么歌"):
        message_return = module.chunithm.handle(message="/chu search" + message_cq[:-4], uid=uid)
        if not message_return:
            return
        await bot.send(event, f"[CQ:reply,id={message_id}]" + message_return)
    elif message_cq.endswith("有什么别名"):
        message_return = module.chunithm.handle(message="/chu alias" + message_cq[:-5], uid=uid)
        if not message_return:
            return
        await bot.send(event, f"[CQ:reply,id={message_id}]" + message_return)
    elif message_cq.startswith("/chu"): # chunithm模块
        message_return = module.chunithm.handle(message=message_cq, uid=uid)
        if not message_return:
            return
        await bot.send(event, f"[CQ:reply,id={message_id}]" + message_return) 
    elif any([message_cq.startswith(x) for x in ["b30", "level", "info", "dsb", "search", "alias", "bind", "id", "calc", "update", "set", "add", "delete"]]):
        message_return = module.chunithm.handle(message="/chu" + message_cq, uid=uid)
        if not message_return:
            return
        await bot.send(event, f"[CQ:reply,id={message_id}]" + message_return)
        
    # elif message_cq.startswith("随机"):
    #     sel = await course.random_course(message_cq, gid, init, bot, event)
    #     try:
    #         text = f"[CQ:reply,id={message_id}]" + course.text_course(sel)
    #         await bot.send(event, text)
    #     except:
    #         pass
    elif message_cq == "/打开随机功能":
        if sender["role"] != "member":
            init['white_list'].append(gid)
            await bot.send(event, "随机功能已经打开, 如需关闭请发送'/关闭随机功能'")
        else:
            await bot.send(event, "权限不足！")
    elif message_cq == "/关闭随机功能":
        init['white_list'].remove(gid)
        await bot.send(event, "随机功能已经关闭")
    elif message_cq == "/help":
        await bot.send(event, MessageSegment.image(f"file:///{os.getcwd()}/docs/help.png") + "有bug的话可以直接加bot好友反馈, 谢谢捏\n原则上不接受maimai群邀请, 如非必要请不要拉谢谢捏")
    elif message_cq == "/update alias":
        message_return = module.other.csvreader.update()
        module.chunithm.search.chuni_alias = json.loads(open("./module/chunithm/data/chuni_alias.json").read())
        await bot.send(event, message_return)
    elif message_cq == "/clear":
        key_nickname = list(nickname.keys())
        count = 0
        for i in list(user.keys()):
            if i not in key_nickname:
                user.pop(i)
                count += 1
        await bot.send(event, "Delete user: " + str(count))
    # elif message_cq == "/ping":
    #     message_return = f"已处理消息: {messageReceived_count}条\n消息处理速度:{round(messageReceived_count/responseTime,2)}条/s\n消息处理延迟: {round(responseTime/messageReceived_count,2)}s"
    #     await bot.send(event, message_return)
    # elif message_cq == "/保存": # 保存数据 用于调试
    #     json_content_str = json.dumps(user)
    #     open("./data/user.json", "w").write(json_content_str) # 保存 应该狗叫就够
    #     json_content_str = json.dumps(nickname)
    #     open("./data/nickname.json", "w").write(json_content_str)
    #     print("保存成功")
    else: 
        return
    logging.critical(f'{uid}/{gid} {message_cq}'.replace("\n", " "))
    

# 简单三行搞定自动通过好友申请））
@bot.on_request("friend", "group")
async def handle(event: Event):
    if event.request_type == "friend":
        await bot.set_friend_add_request(self_id=event.self_id, flag=event.flag, approve=True)
    # else:
    #     if event.sub_type == "invite":
    #         await bot.set_group_add_request(self_id=event.self_id, flag=event.flag, sub_type=event.sub_type, approve=True)

# 针对一下末白群80事件
@bot.on_notice("group_ban")
async def handle(event: Event):
    if (event.operator_id == 3356366627 or event.user_id == 3356366627) and event.operator_id != 2045015088 and event.group_id == 924684205:
        await bot.set_group_ban(group_id=event.group_id, user_id=event.user_id, duration=0, self_id=event.self_id)

@bot.on_message("group") # 单独检测狗叫模块
async def handle_dogbark_message(event: Event):
    uid = event.user_id
    gid = event.group_id
    if uid == event.self_id or gid in [624670021, 366591885]: # 过滤掉自己发送的消息
        return
    message_cq = message_to_cq(event.message).replace("\n", "").replace("\r", "")
    dogbark = open("./src/dogbark.txt").read().splitlines()
    special = []
    if any(re.search(temp, message_cq) != None for temp in dogbark) or (uid in special and random.randint(0, 100) > 75): # 用any函数检查message_cq变量中是否含有dogbark中的其中一个元素 鉴定狗叫 -> bool
        if uid in [3535955754, 2993240173, 2854202507, 3528183142, 3506606538, 51684994, 2854199949, 2375927591, 1178876832, 1511262282]: # 狗叫黑名单
            return 0
        # if time.time() // 60 > time_change // 60:
        logging.critical(f'{uid}/{gid} {message_cq} -> 狗叫')
        flag = False
        if user.get(str(uid)) == None:
            flag = True
            user[str(uid)] = { "gp": 0,"lv": 1,"exp": 0,"last_sign": 0,"day": 1,"jrys": {},"hidden_value": 0,"dogbark": {"dogbark_count": 0,"today_dogbark": 0,"last_dogbark": 0,"top": 0},"daphnis": {"length": 0,"last_time": 0,"maximum": 0,"minimum": 0,"count": 10}}
        else:
            user[str(uid)]["dogbark"]["dogbark_count"] += 1
            user[str(uid)]["dogbark"]["today_dogbark"] += 1
            user[str(uid)]["dogbark"]["last_dogbark"] = time.time()
        if flag:
            print(user[str(uid)])
        json_content_str = json.dumps(user)
        open("./data/user.json", "w").write(json_content_str) # 保存 应该狗叫就够
        json_content_str = json.dumps(nickname)
        open("./data/nickname.json", "w").write(json_content_str)
    if ( time.time() + (8 * 3600) ) // 86400 > ( init["check_dogbark"] + (8 * 3600) ) // 86400:
        user_uidList = list(user.keys())
        random.shuffle(user_uidList)
        dogbark = []
        for id in user_uidList:
            dogbark.append((id, user[id]["dogbark"]["today_dogbark"]))
            dogbark = sorted(dogbark, key=lambda x: (x[1]), reverse=True)
        for id in user_uidList:
            user[id]["hidden_value"] = user[id]["hidden_value"] + int(user[id]["dogbark"]["today_dogbark"] * ((user[id]["lv"] * 6 + 10) // 10))
            user[id]["dogbark"]["today_dogbark"] = 0
            user[id]["daphnis"]["change"] = 0
            user[id]["daphnis"]["count"] = 20
        init["check_dogbark"] = time.time()
        json_content_str = json.dumps(init)
        open("./data/init.json", "w").write(json_content_str)
        json_content_str = json.dumps(user)
        open("./data/user.json", "w").write(json_content_str) # 保存 应该狗叫就够
        user[str(dogbark[0][0])]["dogbark"]["top"] += 1

bot.run(host='127.0.0.1', port=8080)