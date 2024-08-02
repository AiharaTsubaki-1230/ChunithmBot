import requests
from typing import List, Tuple, Dict, Union, Optional
import time
import json
from PIL import Image, ImageDraw, ImageFont
import os
import ast

# 可能需要写好几个函数 再封装到一起
# 比较麻烦
# 定数表这一部分, 日服需要修改 而国服可以直接原封不动

# 2024.4.29　終わりました

class Update():
    def __init__(self) -> None:
        self.chunirec_token = "0c332b89f58298883d4a60d0c8704f5fa4126a0ec88c9bad76afa411eec4b8c2b9508641e9cdea73964b12bcb8b742fe46d1a72f0074354aa4708d4bcb7679c7" # chunirec的token, 可能动的时候先动这个
        self.music_chunirec = f"https://api.chunirec.net/2.0/music/showall.json?region=jp2&token={self.chunirec_token}" # chunirec全曲数据
        self.music_chunijp = "https://chunithm.sega.jp/storage/json/music.json" # 中二jp官网数据
        self.music_chuniintl = "https://raw.githubusercontent.com/zvuc/otoge-db/master/chunithm/data/music-intl.json" # 中二intl官网数据 - from otogedb
        self.music_chuniex = "https://raw.githubusercontent.com/zvuc/otoge-db/master/chunithm/data/music-ex.json" # 和其他数据merge一起的数据 - from otogedb
        self.music_chuniex_deleted = "https://raw.githubusercontent.com/zvuc/otoge-db/master/chunithm/data/music-ex-deleted.json" # deleted song - from otogedb
        self.music_chunicn = "https://43.139.107.206:8083/api/chunithm/music_data" # 国行数据 - from Diving-Fish
        self.music_db: dict = json.load(
            fp=open(
                file="./module/chunithm/data/music_data.json", 
                mode="r", 
                encoding="utf-8"
            )
        )
    
    def merging_music_data(self) -> int: # 把所有我能收到数据的地方缝合起来

        # 0. 新建一个变量 -> dict, 用于储存一整个数据, 最后再dump成一个json文件存放在本地
        
        music_db = {} # 为什么要用music_db呢？可能是帅（
        count = 0 # 后续新增变量 -> 用于判断有多少数据没有在otogedb里面

        # 1. 先直接拿到otogedb的music_data

        response_ex = requests.get(url=self.music_chuniex, timeout=15)

        response_deleted = requests.get(url=self.music_chuniex_deleted, timeout=15)

        response: list = response_ex.json() + response_deleted.json() # 将获取到的music_data变成json格式 (反正肯定是json

        for song_db in response: # 用song_db取代key，更清晰一点（可能, response是list格式

            # 首先筛掉一些WE谱面
            if int(song_db["id"]) >= 8000:
                continue
            # TODO: 补丁
            # elif song_db["title"] == "HECATONCHEIR":
            #     song_db["id"] = "2598"

            id = "c" + song_db["id"] # songid

            # 先初步把基本的meta information处理了
            # TODO: 缺少updatedAt, 在第3步的chunirec会处理
            music_db[id] = {
                "title": song_db["title"],
                "artist": song_db["artist"],
                "genre": song_db["catname"],
                "image": song_db["image"],
                "bpm": song_db["bpm"],
                "version": song_db["version"],
                "chart": song_db["lev_mas_chart_link"][:-3], # 大概率是09/09001之类的东西 放心用就可以 (不用去sdvxin一个一个爬真好)
                "updatedAt": ""
            }

            # 再去慢慢做更深一层的chart data

            song_data = {}

            for diff in ["bas", "adv", "exp", "mas", "ult"]:
                prefix = f"lev_{diff}_" # 写好prefix先

                # 按照规范定义一下song_data先
                song_data[diff.upper()] = {
                    "level": song_db[prefix[:-1]],
                    # 我草你妈otogedb.longtool
                    "const": float(song_db[prefix + "i"].replace("⑨", "9")) if song_db[prefix + "i"] else 0.0, # 如果只是一个单纯的空字符串的话就等待后续chunirec的时候再搞, 一般我更信任chunirec多一点点
                    "designer": song_db[prefix + "designer"],
                    "note": {
                        "total": song_db[prefix + "notes"], # TODO: 目前还是str类型
                        "tap": song_db[prefix + "notes_tap"],
                        "hold": song_db[prefix + "notes_hold"],
                        "slide": song_db[prefix + "notes_slide"],
                        "flick": song_db[prefix + "notes_flick"],
                        "air": song_db[prefix + "notes_air"]
                    }
                }


                music_db[id]["data"] = song_data

        
        # 2. 对着官服再筛一遍有没有多的, 一般还是以otogedb为准吧, 这一块就暂时不塞什么半完成品了

        for url in [self.music_chunijp, self.music_chuniintl]: # 因为不想复制一遍贴下去所以做了个for, 好文明

            response = requests.get(url=url, timeout=15)

            response: list = response.json() # 大家都知道这是什么的

            for song_db in response: # 目的只是为了筛一遍而已

                if int(song_db["id"]) >= 8000: # 又是经典filter掉WE谱面
                    continue

                flag = music_db.get("c" + song_db["id"]) == None # 定义一个flag判断有没有东西返回

                # 如果没有相关数据
                if flag:
                    print(song_db["title"]) # 在本地命令行print他的曲名
                    count += 1 # 其实想写count++的, 大概展示一下otogedb还差多少歌

        # 3. 从chunirec再拿一遍数据 (好累歇会)

        response = requests.get(url=self.music_chunirec, timeout=15)

        response: list = response.json()

        # time_start_looping = time.time() # 留一个时间戳记录开始的时候, 后续: 貌似0.24秒, 那不需要了

        for song_db in response:

            for music_key in music_db: # 没办法了只能一个一个用for循环，肯定是要浪费不少时间的

                if music_db[music_key]["title"] == song_db["meta"]["title"] and song_db["data"].get("WE") == None: # 匹配title是不是相似 / 非WE谱面

                    music_db[music_key]["updatedAt"] = song_db["meta"]["release"] # 更新release time

                    for diff in ["bas", "adv", "exp", "mas", "ult"]:
                        if not song_db["data"].get(diff.upper()) == None: # 确保没有ultima难度不会报错

                            temp = music_db[music_key]["data"][diff.upper()] # 加个temp先, 要不然疯狂嵌套实属难受

                            temp["const"] = max(float(song_db["data"][diff.upper()]["level"]), float(temp["const"]), float(song_db["data"][diff.upper()]["const"])) # 比大小环节, 确保没有定数=0的情况 / PS: 一行过真的很恶心
                            # temp["const"] = max(float(song_db["data"][diff.upper()]["level"]), float(temp["const"]), float(song_db["data"][diff.upper()]["const"]))

                            temp["const"] = temp["const"] if temp["const"] else 0.0

                            if (note := temp["note"]["total"]).isdigit() == True: # 确保物量不是str类型, 用海象运算符省一行 + 判断是不是数字
                                temp["note"]["total"] = int(note) # 直接转成int塞进去
                            else:
                                temp["note"]["total"] = 0
                            
                            music_db[music_key]["data"][diff.upper()] = temp # 再塞回去

                            # WARN: 一坨狮山真的难受

        json.dump(
            obj=music_db, 
            ensure_ascii=False, 
            indent=4, 
            fp=open(
                file="./module/chunithm/data/music_data.json", 
                mode="w", 
                encoding="utf-8"
            )
        )

        return count
    
    def draw_dsb(self) -> int: # TODO: 没有注释
        for target in ["12", "12+", "13", "13+", "14", "14+", "15"]:

            tg = target # 借存一个target先

            new_keys = []
            for diff in ["ULT", "MAS", "EXP"]:
                for key in self.music_db:
                    if int(key[1:]) >= 8000:
                        continue
                    if self.music_db[key].get("data") != None:
                        if self.music_db[key]["data"].get(diff) != None:
                            if self.music_db[key]["data"][diff]["level"] == target:
                                new_keys.append((key, diff))
            

            l = len(new_keys) // 15 * 210 + 1200
            base = Image.open("./src/chunithm/blue.PNG").resize((3500, l)).convert("RGB")

            ico_sp = Image.open("./src/chunithm/logo_sp.png").convert("RGBA")
            ico_sp = ico_sp.resize((480, 240))

            base.paste(ico_sp, (80, 80), mask=ico_sp)

            draw = ImageDraw.Draw(base)

            font = ImageFont.truetype("./src/chunithm/font/NotoSansHans-Regular-2.ttf", 100)
            

            draw.text((1320, 140), f"CHUNITHM 定数表 Lv.{target}", (0, 0, 0), font)

            font = ImageFont.truetype("./src/chunithm/font/BAHNSCHRIFT.ttf", 100)

            c = 0

            if target.isdigit():
                target = int(target)
            else:
                target = int(target[:-1]) + 0.5

        

            for i in [target+0.4, target+0.3, target+0.2, target+0.1, target+0.0]:
                draw.text((50, 400 + c * 210), str(i), (0, 0, 0), font)

                count = 0

                for key in new_keys:
                    try:
                        if self.music_db[key[0]]["data"][key[1]]["const"] == i:
                            if key[1] == "ULT":
                                bg = Image.new("RGB", (204, 204), (0, 0, 0))
                                base.paste(bg, ((265 + count % 15 * 210 - 2, 335 + count // 15 * 210 + c * 210 - 2)))
                            if key[1] == "EXP":
                                bg = Image.new("RGB", (204, 204), (238, 67, 102))
                                base.paste(bg, ((265 + count % 15 * 210 - 2, 335 + count // 15 * 210 + c * 210 - 2)))
                            pic = Image.open(f'./src/chunithm/image/{key[0]}.jpg')
                            base.paste(pic, (270 + count %
                                    15 * 210, 340 + count // 15 * 210 + c * 210))
                            count += 1
                    except Exception as e:
                        print(e)

                c += 1 + (count-1) // 15

            base.resize((1000, l // 2))

            base.save(f"./src/chunithm/const/{tg}.jpg")

        with open("./module/chunithm/data/music_data_cn.json", "w") as f:
            req = requests.get(
                url="http://43.139.107.206:8083/api/chunithm/music_data"
            )
            alldata = {f'c{x["musicID"]}': x for x in req.json()}
            json.dump(
                obj=alldata,
                fp=f,
                indent=4
            )

        # alldata = requests.get(url=self.music_chunicn, timeout=15).json() # 获取国行数据 + 转成json

        for target in ["12", "12+", "13", "13+", "14", "14+", "15"]:

            tg = target # 借存一个target先

            new_keys = []
            for diff in ["ultima", "master", "expert"]:
                for key in alldata:
                    if int(key[1:]) >= 8000:
                        continue
                    if alldata[key].get("charts") != None:
                        if alldata[key]["charts"].get(diff) != None:
                            if alldata[key]["charts"][diff]["level"] == target:
                                new_keys.append((key, diff))
            

            l = len(new_keys) // 15 * 210 + 1200
            base = Image.open("./src/chunithm/blue.PNG").resize((3500, l)).convert("RGB")

            ico_sp = Image.open("./src/chunithm/logo_sp.png").convert("RGBA")
            ico_sp = ico_sp.resize((480, 240))

            base.paste(ico_sp, (80, 80), mask=ico_sp)

            draw = ImageDraw.Draw(base)

            font = ImageFont.truetype("./src/chunithm/font/NotoSansHans-Regular-2.ttf", 100)
            

            draw.text((1320, 140), f"中二节奏 国服定数表 Lv.{target}", (0, 0, 0), font)

            font = ImageFont.truetype("./src/chunithm/font/BAHNSCHRIFT.ttf", 100)

            c = 0

            if target.isdigit():
                target = int(target)
            else:
                target = int(target[:-1]) + 0.5

        

            for i in [target+0.4, target+0.3, target+0.2, target+0.1, target+0.0]:
                draw.text((50, 400 + c * 210), str(i), (0, 0, 0), font)

                count = 0

                for key in new_keys:
                    try:
                        if alldata[key[0]]["charts"][key[1]]["constant"] == i:
                            if key[1] == "ultima":
                                bg = Image.new("RGB", (204, 204), (0, 0, 0))
                                base.paste(bg, ((265 + count % 15 * 210 - 2, 335 + count // 15 * 210 + c * 210 - 2)))
                            if key[1] == "expert":
                                bg = Image.new("RGB", (204, 204), (238, 67, 102))
                                base.paste(bg, ((265 + count % 15 * 210 - 2, 335 + count // 15 * 210 + c * 210 - 2)))
                            pic = Image.open(f'./src/chunithm/image/{key[0]}.jpg')
                            base.paste(pic, (270 + count %
                                    15 * 210, 340 + count // 15 * 210 + c * 210))
                            count += 1
                    except Exception as e:
                        print(e)

                c += 1 + (count-1) // 15

            base.resize((1000, l // 2))

            base.save(f"./src/chunithm/const/{tg}_cn.jpg")
        
        return 0
        
    def check_download_image(self) -> int:
        
        count = 0 # 下载的曲绘数量

        for key in self.music_db:
            flag = os.path.exists(f"./src/chunithm/image/{key}.jpg") # 检查是否下载
            if flag == False: # 如果没下载
                url = "https://new.chunithm-net.com/chuni-mobile/html/mobile/img/" + self.music_db[key]["image"] # merge url
                request = requests.get(url, timeout=15) # 获取数据
                print(key)
                open(f"./src/chunithm/image/{key}.jpg", "wb").write(request.content) # 写入数据
                count += 1 # count + 1

        return count

    def handle(self) -> int: # 简单做一行把三个弄一起

        count = self.merging_music_data() + self.check_download_image() + self.draw_dsb()

        return f"Updated.\ncount={count}"