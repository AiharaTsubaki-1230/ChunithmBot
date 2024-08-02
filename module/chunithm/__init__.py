from module.chunithm.search import SearchSong, UpdateAlias
from module.chunithm.utils import SegaID, Record, B30Image_v2, ChuApiError, ExcelUpsert, SongInfoImage, B30Image_v3, B30Image_v1, music_db
import module.chunithm.b30 as b30
from module.chunithm.update import Update
from typing import Any
import re
import os

path = os.getcwd()


def handle(message: str, uid: int) -> Any:

    message = message[4:].strip()

    uid = 2154319688 if uid in [3407299613, 3865046719] else uid
    
    if message.startswith("search"):

        # 去掉字首的search, 如果有空格继续去掉
        keyword = message[6:].strip()
        if not (keyword.startswith("c") and keyword[1:].isdigit()):
            # 直接对keyword做查询 -> match(查询的结果)
            match = SearchSong(keyword=keyword).search_by_keywords()
        else:
            # 主要是应对炒饭
            match = [keyword]
        
        # 返回消息 | 报错提醒
        return SearchSong().merge_match_to_message(query=match)
    
    elif message.startswith("id"):

        # 去掉字首的id
        song_id = message[2:].strip()

        # [match] -> str to list
        try:
            return SearchSong().merge_match_to_message(query=[song_id]) if song_id.startswith("c") else ""
        except ChuApiError as e:
            return f"Error: {repr(e)}"

    elif message.startswith("alias"):

        # 去掉字首的id
        song_id = message[5:].strip()
        return SearchSong().search_alias(keyword=song_id)
    
    elif message == "update":

        return Update().handle() if uid in [2154319688, 3407299613] else "No authority to update."

    elif message.startswith("b30"):
        # 去掉字首的b30和空格
        message = message[3:].strip()

        if message == "temp":
            return f"[CQ:image,file=file:///{path}/src/temp/res_{uid}.jpg]"
        
        ver = "sunp" if message.endswith("sunp")  else "lmn"
        server = message[:-4].strip() if ver == "sunp" else message

        temp = server

        server = server.replace("lmnp", "").replace("lmn", "").strip()

        segaid: str | tuple = SegaID.get_record(uid=uid, server=server)

        b30_version: str | tuple | None = SegaID.get_record(uid=uid, server="b30_version")

        # 处理一下b30_version, 默认v3
        b30_version = (b30_version[0] if b30_version[0] else "v3") if b30_version else "v3"
        
        # 返回None的情况 & 查分是要查国行的情况
        if not (segaid or server in ["lxns", "cn", "louis"]):
            return "你还没有绑定过呢！"

        # 检查segaid里面是不是None & 查分不是查国行的情况
        if server in ["lxns", "cn", "louis", "csv"] or (segaid[0] and server not in ["lxns", "cn", "louis", "csv"]):
            try:
                b30_record: Record | str | None = b30.parse_b30_record(segaid=segaid, server=temp, uid=uid)
                if b30_record: 
                    b30_record = b30_record.filter_not_played_record().sort()
                else: 
                    return ""
                match b30_version:
                    case "v3a":
                        return B30Image_v3(b30_record=b30_record, uid=uid).generate_b30_image_with_bar()
                    case "v3":
                        return B30Image_v3(b30_record=b30_record, uid=uid).generate_b30_image()
                    case "v2":
                        if server == "en":
                            return B30Image_v2(b30_record=b30_record, uid=uid).generate_b30_image_without_recent()
                        else:
                            return B30Image_v2(b30_record=b30_record, uid=uid).generate_b30_image_with_recent()
                    case "v1":
                        return B30Image_v1(b30_record=b30_record, uid=uid).generate_b30_image()
                    case _:
                        print("version out of v3 and v2")
                        return ""
            except TimeoutError:
                return f"发生错误\nError: TimeoutError"
            except ChuApiError as e:
                return f"发生错误\nError: {repr(e)}"
            except Exception as e:
                return f"发生未知错误\nError: {e}"
        else:
            return "你还没有绑定过呢！"
    

    elif message.startswith("calc"):
        # 去掉字首的b30和空格
        message: str = message[4:].strip()

        # 检测要查的分数
        for n in range(114514):
            if not message[:n+1].isdigit():
                break
        
        # 获取分数 & 要查的歌 (with 难度)
        score = int(message[:n])
        songinfo = message[n:].strip()

        # 检测要查的难度 -> 默认 MAS
        diff = "mas"
        for temp in ["exp", "mas", "ult"]:
            if songinfo.endswith(temp):
                diff = temp
                songinfo = songinfo.replace(temp, "").strip()
                break
        
        # songinfo最后应该会剩下 c[数字] 或者 曲名

        # 如果是id为格式 -> 直接变成id; 否则丢去searchsong object查到对应的歌
        query = [songinfo] if songinfo[0] == "c" and songinfo[1:].isdigit() else SearchSong(keyword=songinfo).search_by_keywords()
        
        match len(query):
            case 0:
                return "没有找到符合的曲目捏"
            case 1:
                songinfo_db = music_db[query[0]]

                note = songinfo_db["data"][diff.upper()]["note"]["total"]
                
                justice_reduce = 10000 / note
                fault = 1010000 - score

                return f"[{diff.upper()}]{query[0]}. {songinfo_db['title']}\n目标分数: {score}\n允许最多JUSTICE数量: {round(fault / justice_reduce, 2)} (每个-{round(justice_reduce, 2)})\n允许最多ATTACK数量: {round(fault / justice_reduce / 51, 2)} (每个-{round(justice_reduce * 51, 2)})\n允许最多MISS数量: {round(fault / justice_reduce / 101, 2)} (每个-{round(justice_reduce * 101, 2)})"
            case _:
                return "匹配到了多个曲目\n请使用/chu calc [目标分数] [你需要的曲目ID] [exp/ult]进行查询\n" + SearchSong().merge_match_to_message(query=query)
    
    elif message.startswith("add"):

        message: str = message[3:].strip()

        try:
            return UpdateAlias().update(*message.split(sep="into"))
        except TypeError:
            return "Error: 输入格式错误, 请输入正确的格式后重试捏"
    
    elif message.startswith("delete"):

        message: str = message[6:].strip()

        try:
            return UpdateAlias().delete(*message.split(sep="from"))
        except TypeError:
            return "Error: 输入格式错误, 请输入正确的格式后重试捏"
        
    elif message.startswith("update"):
        # split message by space
        update_record = message[6:].strip().split()

        try:
            return ExcelUpsert(uid=uid).update_score(score=update_record[0], diff=update_record[1], cid="c"+update_record[2], status="" if len(update_record) == 3 else update_record[3])
        except ChuApiError as e:
            return f"Error: {repr(e)}"
    
    elif message.startswith("std"):
        # 去掉字首的level和空格
        message = message[3:].strip()

        rating = float(message)



        std = 1.0006405721 * rating ** 4 - 66.2054373962 * rating ** 3 + 1642.4363958556 * rating ** 2 - 18107.2465845080 * rating + 74851.9419440918

        return f"STDEV: {std}" if 16 <= rating <= 17.15 else ""

    
    elif message.startswith("level"):
        # 去掉字首的level和空格
        message = message[5:].strip()

        # Example: /chu level 14+ en 3 -> 14+ en 3
        page = 0
        index = 0

        # page of required level
        while message[-1].isdigit():
            page += int(message[-1]) * 10 ** index
            index += 1
            message = message[:-1].strip()
        
        page = page if page else 1

        # required level
        # if matched -> match level
        if match := re.search("\d+\+?", message):
            match: str = match.group(0)
        else:
            return "Error: Invalid input."

        # change level to float
        level = int(match) if match.isdigit() else int(match[:-1]) + 0.5

        # server -> replace "level" to ""
        server = message.replace(match, "").replace("en", "").strip()

        # get segaid
        segaid: str | tuple = SegaID.get_record(uid=uid, server=server)

        # 不对水鱼国服做支持先
        if server == "cn":
            return 

        # 返回None的情况 & 查分是要查国行的情况
        if not (segaid or server in ["lxns", "cn", "louis"]):
            return "你还没有绑定过呢！"

        # 检查segaid里面是不是None & 查分不是查国行的情况
        if server in ["lxns", "cn", "louis", "csv"] or (segaid[0] and server not in ["lxns", "cn", "louis", "csv"]):
            try:
                b30_record: Record | str | None = b30.parse_b30_record(segaid=segaid, server=server, uid=uid)
                return B30Image_v2(b30_record=b30_record.filter_not_played_record(), uid=uid).generate_level_image(level=level, page=page) if b30_record else ""
            except TimeoutError:
                return f"发生错误\nError: TimeoutError"
            except ChuApiError as e:
                return f"发生错误\nError: {repr(e)}"
            except Exception as e:
                return f"发生未知错误\nError: {e}"
        else:
            return "你还没有绑定过呢！"
    
    elif message.startswith("info"):

        # 去掉字首的b30和空格
        message = message[4:].strip()

        # check server
        server = ""

        for temp in ["aqua", "rin", "na", "en", "jp", "louis", "cn", "csv"]:
            if temp in message:
                message = message.replace(temp, "").strip()
                server = temp
                break
        
        query = [message] if message[0] == "c" and message[1:].isdigit() else SearchSong(keyword=message).search_by_keywords()

        query = list(filter(lambda x: x != "c0", query))

        match len(query):
            case 0:
                return "没有找到符合的曲目捏"
            case 1:
                # 获取绑定数据
                segaid: str | tuple = SegaID.get_record(uid=uid, server=server)

                # 返回None的情况 & 查分是要查国行的情况
                if not (segaid or server in ["lxns", "cn", "louis"]):
                    return "你还没有绑定过呢！"

                # 检查segaid里面是不是None & 查分不是查国行的情况
                if server in ["lxns", "cn", "louis", "csv"] or (segaid[0] and server not in ["lxns", "cn", "louis", "csv"]):
                    try:
                        b30_record: Record | str | None = b30.parse_b30_record(segaid=segaid, server=server, uid=uid).fill_zero_record(ver="cn" if server in ["lxns", "cn", "louis"] else "jp")
                        return SongInfoImage(b30_record=b30_record, uid=uid, cid=query[0]).generate_song_info_image() if b30_record else ""
                    except TimeoutError:
                        return f"发生错误\nError: TimeoutError"
                    except ChuApiError as e:
                        return f"发生错误\nError: {repr(e)}"
                    except Exception as e:
                        return f"发生未知错误\nError: {e}"
                else:
                    return "你还没有绑定过呢！"
            case _:
                return f"匹配到了多个曲目\n请使用/chu info [你需要的曲目ID] {server}进行查询\n" + SearchSong().merge_match_to_message(query=query)
            
    elif message.startswith("set"):

        message = message[3:].strip()

        match message:
            case "v1" | "v2" | "v3" | "v3a":
                return SegaID.set_record(uid=uid, b30_version=message)
            case _:
                return "没有这项设置捏"

    elif message.startswith("bind"):

        message = message[4:].strip()

        bind_info = message.split(" ") # 应该len=2没跑了

        match bind_info[1]:
            case "aqua" | "rin" | "na":
                if bind_info[0].isdigit() and len(bind_info[0]) == 20:
                    return SegaID.set_record(uid=uid, kwargs={bind_info[1]: bind_info[0]})
                else:
                    return "Error: 卡号应为20位数字"
            case "en" | "fc":
                if bind_info[0].isdigit():
                    return SegaID.set_record(uid=uid, en_friendcode=bind_info[0])
            case "csv":
                return ExcelUpsert(uid=uid).register_excel(bind_info[0])
            case "jp":
                return SegaID.set_record(uid=uid, jp_rec=bind_info[0])
            case _:
                return SegaID.set_record(uid=uid, en_segaid=bind_info[0], en_pswd=bind_info[1]) if bind_info[0] and bind_info[1] else "Error: 绑定格式错误"
    
    elif message.startswith("dsb"):
            
            message = message[3:].strip()

            cn = message.endswith("cn")
            message = message[:-2].strip() if cn else message

            if not os.path.exists(f"./src/chunithm/const/{message}.jpg"):
                return "没有对应难度的定数表"
            
            return f"[CQ:image,file=file:///{os.getcwd()}/src/chunithm/const/{message}{'_cn' if cn else ''}.jpg]"
    else:
        return ""