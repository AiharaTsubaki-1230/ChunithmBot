import module.user.dogbark as dogbark
import module.user.sign as sign
import module.user.work as work
import random
import module.user.daphnis as daphnis

async def handle_command(uid, gid, message, user, sender, nickname, bot, message_id):
    try:
        split = message.split(" ")
        msg = split[1]
        if msg in ["狗叫", "我的狗叫", "dogbark", "db"]:
            message_return = dogbark.get_dogbark_info(uid, user, sender["nickname"], message, nickname)
        elif msg in ["stat"]:
            message_return = dogbark.get_stat(user)
        elif msg in ["狗叫排行", "rank"]:
            if len(split) == 3:
                n = int(split[2])
            else:
                n = 1
            message_return = dogbark.get_dogbark_rank(user, uid, sender, nickname, n)
        elif msg in ["今日狗叫排行", "dlrank"]:
            if len(split) == 3:
                n = int(split[2])
            else:
                n = 1
            message_return = dogbark.get_daily_dogbark_rank(user, uid, sender, nickname, n)
        elif msg in ["签到", "s", "sign"]:
            message_return = sign.sign(user, uid, sender)
        elif msg in ["个人信息", "info"]:
            message_return = sign.info(user, uid, sender)
        # elif msg in ["gprank", "forbes", "fhb", "GPrank", "GPRANK", "富豪榜", "福布斯排行榜"]:
        #     message_return = sign.rank_forbes(user, uid, sender, nickname)
        elif msg in ["添加关键词", "word"]:
            message_return = dogbark.append_wordings(message)
        elif msg in ["狗王排行"]:
            message_return = dogbark.get_dogbark_king_rank(user, uid, sender, nickname)
        # elif msg in ["114514"]:
        #     message_return = dogbark.hdvrank(user, uid, sender, nickname)
        elif msg in ["ws", "开始打工"]:
            message_return = work.work_start(user, uid)
        elif msg in ["we", "结束打工"]:
            message_return = work.work_end(user, uid)
        elif "还是" in msg:
            msg = msg.split("还是")
            arr = [0] * len(msg)
            for i in range(10000):
                seed = random.randint(0, len(msg)-1)
                arr[seed] += 1
            arr = sorted(zip(arr, msg), key=lambda x: x[0], reverse=True)
            message_return = "随机结果：\n" +"\n".join([f"{x[1]}: {x[0]}次" for x in arr])
        elif msg in ["贴贴"] and uid == 1804956961:
            message_return = random.choice(["贴贴", "贴贴捏", "贴贴可爱", "可爱", "喜欢你", "好き"])

        # elif msg in ["scjb", "生成几把"]:
        #     message_return = daphnis.generate_penis(user, uid)
        # elif msg in ["rd", "random", "随机"]:
        #     message_return = daphnis.change_penis(user, uid)
        # elif msg in ["rdp", "randompremium", "保底随机"]:
        #     message_return = daphnis.change_penis_premium(user, uid)
        # elif msg in ["jbrank"]:
        #     message_return = daphnis.penis_rank(user, uid, sender, nickname)
        elif msg in ["口球"]:
            if (sender["role"] in ["admin", "member"] and gid in [298626210, 947987790, 741053852]) or (sender["role"] in ["member"] and gid in [924684205]):
                message_return = "晚安捏"
                await bot.set_group_ban(group_id=gid, user_id=uid, duration=random.randint(0,43200))
            else:
                message_return = "没有权限捏"
        # elif msg in ["美食分享者", "制裁", "10"]:
        #     if sender["role"] in ["member"] and gid in [924684205, 741053852]:
        #         message_return = "晚安捏"
        #         await bot.set_group_ban(group_id=gid, user_id=uid, duration=600)
        #     else:
        #         message_return = "没有权限捏"
        elif msg.isdigit() == True:
            jikan = int(msg) * 60
            if sender["role"] in ["member"] and gid in [924684205, 947987790, 741053852]:
                message_return = "晚安捏"
                if jikan > 86400:
                    return "时间太长了，禁言不了捏"
                await bot.set_group_ban(group_id=gid, user_id=uid, duration=jikan)
            else:
                message_return = "没有权限捏"
        else:
            message_return = "暂不支持相关指令 / 没有相关的指令"
    except Exception as e:
        message_return = repr(e)
    # print(message_return)
    return f"[CQ:reply,id={message_id}]" + message_return

"""
{"message_type":"group","sub_type":"normal","message_id":0,"group_id":142830249,"user_id":1258719565,"anonymous":null,"message":[{"type":"text","data":{"text":"\u554A\uFF1F"}}],"raw_message":"","font":0,"sender":{"user_id":1258719565,"nickname":"\u96EA\u72FC","card":"\u300A\u5927\u4E71\u300B \u30E1\u30EA\u30E0 marry me","sex":"unknown","age":0,"area":"","level":"24","role":"member","title":""},"time":1705597646,"self_id":2676306539,"post_type":"message"}
"""
    