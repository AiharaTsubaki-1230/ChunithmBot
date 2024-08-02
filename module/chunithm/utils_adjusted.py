import json
import socket
import struct
from Crypto.Cipher import AES, DES
import sqlite3
from pydantic import BaseModel, validator
from decimal import Decimal, ROUND_DOWN
from typing import Optional, Any, Self
from PIL import Image, ImageDraw, ImageFont
import os
import csv
import requests
import numpy as np
from http.cookiejar import CookiePolicy

path = os.getcwd()

# pre-open the file of music_db
music_db: dict = json.load(
            fp=open(
                file="./module/chunithm/data/music_data.json", 
                mode="r", 
                encoding="utf-8"
            )
        )

music_db_lmn: dict = json.load(
            fp=open(
                file="./module/chunithm/data/music_data_lmn.json", 
                mode="r", 
                encoding="utf-8"
            )
        )

music_db_cn: dict = json.load(
            fp=open(
                file="./module/chunithm/data/music_data_cn.json", 
                mode="r", 
                encoding="utf-8"
            )
        )

class ChuApiError(Exception):
    def __init__(self, message: str):
        self.message = message

class MusicDB():
    def __init__(self, cid: str = 0) -> None:
        self.cid = cid
    
    def match_songname(self, title: str) -> int: # match 曲名 转 int id
        for song_id in music_db.keys():
            if title == music_db[song_id]["title"]:
                return int(song_id[1:])
        return 0
    
    @property
    def song_db(self) -> dict:
        return music_db[self.cid]                

class SegaID:
    @staticmethod
    def set_record(uid: int, **kwargs) -> str:
        """
        主要是for kwargs的说明
        uid -> primary_key / not null
        国服 -> diving_fish | louis | lxns
        私服 -> aqua | rin | na | lin
        国际服 -> en_segaid | en_pswd | en_friendcode
        日服 -> jp_rec | jp_segaid | jp_pswd
        """
        # 预处理kwargs
        kwargs = kwargs.get("kwargs", kwargs)
        try:
            # 建立数据库的连接
            with sqlite3.connect('./module/chunithm/data/sega_id.db') as connect:
                cursor = connect.cursor()
                # 获取所有绑定过的qq号
                result = cursor.execute("SELECT uid FROM segaid_db")
                # 检测查询的qq号在不在绑定的list里面
                if str(uid) in [res[0] for res in result.fetchall()]:
                    # 如果绑定过则使用UPDATE语句
                    # 先把所有kw组合成value统一放一个变量里面
                    value = ','.join([f"{kw}='{kwargs[kw]}'" for kw in kwargs])
                    # 然后写好sql语句
                    query = f"UPDATE segaid_db SET {value} WHERE uid='{uid}'"
                else:
                    # 没有绑定过则使用INSERT语句
                    # 这两段字符串写的比较史，能跑就行... 大体逻辑就是把所有什么kwargs缝合到一起去
                    key = f"(uid,{','.join(list(kwargs.keys()))})"
                    value = f"('{uid}'," + ",".join([f"'{kwargs[kw]}'" for kw in kwargs]) + ")"
                    # 然后写好sql语句
                    query = f"INSERT INTO segaid_db {key} VALUES {value}"
                # 最后放到一起做更新
                cursor.execute(query)
                cursor.close()
            return "绑定完成！"
        except Exception as e:
            return f"发生未知错误\nError: {e}"

    @staticmethod
    def get_record(uid: int, server: str) -> tuple | str | None:
        """
        tuple -> record exists
        None -> record does not exists
        str -> unknown error occured
        """
        # 给server转义成对应的key
        match server:
            case "cn":
                query = "diving_fish"
            case "jp":
                query = "jp_rec"
            case "en":
                query = "en_friendcode"
            case "" | "en2":
                query = "en_segaid,en_pswd"
            case _: # aqua | rin | na | lin | louis | lxns
                query = server
        try:
            # 建立数据库的连接
            with sqlite3.connect('./module/chunithm/data/sega_id.db') as connect:
                cursor = connect.cursor()
                # 把sql语句凑出来做一下execute
                sql = f"SELECT {query} FROM segaid_db WHERE uid='{uid}'"
                result = cursor.execute(sql)
                return result.fetchone()
        except Exception as e:
            return f"发生错误\nError: {e}"

class ScoreItem(BaseModel):
    score: int
    diff: str
    id: int
    title: Optional[str] | str
    const: Optional[float]
    isAJ: Optional[bool] = False
    isFC: Optional[bool] = False

    @validator("title", always=True, allow_reuse=True)
    def set_default_title(cls, value, values) -> str:
        cid = f"c{values['id']}"
        for song_db in [music_db.get(cid), music_db_lmn.get(cid), music_db_cn.get(cid)]:
            if song_db:
                return value if value else song_db["title"]

    @validator("const", always=True, allow_reuse=True)
    def set_default_const(cls, value, values) -> float:
        cid = f"c{values['id']}"
        diff = values["diff"]
        if value:
            return value
        elif music_db.get(cid):
            return music_db[cid]["data"][diff]["const"]
        elif music_db_lmn.get(cid):
            return music_db_lmn[cid]["data"][diff]["const"]
        elif music_db_cn.get(cid):
            diff_change = {"BAS": "basic", "ADV": "advanced", "EXP": "expert", "MAS": "master", "ULT": "ultima"}
            return float(music_db_cn[cid]["charts"][diff_change[diff]]["constant"])
        else:
            return 0
        
    @property
    def rating_precise(self) -> float:
        match self.score:
            case self.score if self.score >= 1009000:
                rt = self.const + 2.15
            case self.score if 1009000 > self.score >= 1007500:
                rt = self.const + 2 + (self.score - 1007500) / (1009000 - 1007500) * 0.15
            case self.score if 1007500 > self.score >= 1005000:
                rt = self.const + 1.5 + (self.score - 1005000) / (1007500 - 1005000) * 0.5
            case self.score if 1005000 > self.score >= 1000000:
                rt = self.const + 1 + (self.score - 1000000) / (1005000 - 1000000) * 0.5
            case self.score if 1000000 > self.score >= 975000:
                rt = self.const + 0 + (self.score - 975000) / (1000000 - 975000) * 1
            case self.score if 975000 > self.score >= 925000:
                rt = self.const + -3 + (self.score - 925000) / (975000 - 925000) * 3
            case self.score if 925000 > self.score >= 900000:
                rt = self.const + -5 + (self.score - 900000) / (925000 - 900000) * 2
            case self.score if 900000 > self.score >= 800000:
                rt = (self.const - 5) / 2 + (self.score - 800000) / (900000 - 800000) * ((self.const + -5) - (self.const - 5) / 2)
            case self.score if 800000 > self.score >= 500000:
                rt = 0 + (self.score - 500000) / (800000 - 500000) * (self.const - 5) / 2
            case _:
                rt = 0
        return max(rt + 2 * 10 ** -8, 0)

    @property
    def rating_2dp(self) -> Decimal:
        rt = self.rating_precise 
        return Decimal(rt).quantize(Decimal("0.00"), rounding=ROUND_DOWN)
    
    @property
    def rating_4dp(self) -> Decimal:
        rt = self.rating_precise
        return Decimal(rt).quantize(Decimal("0.0000"), rounding=ROUND_DOWN)
    
    @property
    def cid(self) -> str:
        return "c" + str(self.id)
    
    @property
    def op_current(self) -> Decimal:
        """
        OVER POWERの計算値は以下の通り。
        ランク	     スコア	             OVER POWER値
        SSS以上	   1,007,501～	    (譜面定数+2)×5+補正1+補正2
        S～SSS	975,000～1,007,500	レーティング値×5＋補正1
        Copy from https://gamerch.com/chunithm/entry/489232
        """

        # 補正1 => FCで+0.5、AJで更に+0.5、AJCで更に+0.25
        complete1 = 1.25 if self.score == 1010000 else (1 if self.isAJ else (0.5 if self.isFC else 0))

        # 補正2 => (スコア-1,007,500) × 0.0015
        complete2 = max((self.score - 1007500) * 0.0015, 0)
        
        op_current = (min(Decimal(self.const + 2), self.rating_2dp) * 5 + Decimal(complete1) + Decimal(complete2)) if self.score >= 975000 else 0

        return Decimal(op_current).quantize(Decimal("0.0000"))
    
    @property
    def op_max(self) -> Decimal:
        return Decimal(self.const * 5 + 15).quantize(Decimal("0.0"))


class Record(BaseModel):
    name: str = ""
    best: list[ScoreItem] = []
    recent: list[ScoreItem] = []
    playCount: Optional[int] = "--"
    rating_max: float | Decimal | str = "--"
    enable_recent: Optional[bool] = True

    # 筛选特定的难度范围 => 分数列表
    def filter_record_by_level(self, level: float) -> list[ScoreItem]:
        return sorted(list(filter(lambda x: level <= x.const <= level + 0.4, self.best)), key=lambda x: x.score, reverse=True)
    
    # 筛选特定的定数范围
    def filter_record_by_const(self, level: float) -> list[ScoreItem]:
        return sorted(list(filter(lambda x: x.const == level, self.best)), key=lambda x: x.score, reverse=True)

    # sort by rating
    def sort(self) -> Self:
        self.best = sorted(self.best, reverse=True, key=lambda x: (x.rating_precise, x.score))[:30]
        self.recent = sorted(self.recent, reverse=True, key=lambda x: (x.rating_precise, x.score))[:10]
        return self
    
    # sort by rating + not cut first 30
    def sort_all_entries(self) -> Self:
        self.best = sorted(self.best, reverse=True, key=lambda x: (x.rating_precise, x.score))
        self.recent = sorted(self.recent, reverse=True, key=lambda x: (x.rating_precise, x.score))
        return self

    # 筛选掉分数为0的记录
    def filter_not_played_record(self) -> Self:
        self.best = list(filter(lambda x: x.score != 0, self.best))
        return self
    
    # 切换难度范围
    def change_const_by_version(self, ver: str) -> Self:
        """
        可选项:
        - jp | lmnp | lmnplus: 日服最新定数
        - lmn | luminous: lmn版本定数
        - cn: 国服定数
        """
        # change best const
        best_temp_storage = []
        for best in self.best:
            try:
                match ver:
                    case "jp" | "lmnp" | "lmnplus":
                        best.const = music_db[best.cid]["data"][best.diff]["const"]
                    case "lmn" | "luminous":
                        best.const = music_db_lmn[best.cid]["data"][best.diff]["const"]
                    case "cn":
                        diff_change_format = {"BAS": "basic", "ADV": "advance", "EXP": "expert", "MAS": "master", "ULT": "ultima"}
                        diff_format = diff_change_format[best.diff]
                        best.const = float(music_db_cn[best.cid]["charts"][diff_format]["constant"])
            except KeyError: # 大概率就是数据库没这歌了，直接走掉就可以
                pass
            best_temp_storage.append(best)
        self.best = best_temp_storage

        # change recent const
        recent_temp_storage = []
        for best in self.recent:
            try:
                match ver:
                    case "jp" | "lmnp" | "lmnplus":
                        best.const = music_db[best.cid]["data"][best.diff]["const"]
                    case "lmn" | "luminous":
                        best.const = music_db_lmn[best.cid]["data"][best.diff]["const"]
                    case "cn":
                        diff_change_format = {"BAS": "basic", "ADV": "advance", "EXP": "expert", "MAS": "master", "ULT": "ultima"}
                        diff_format = diff_change_format[best.diff]
                        best.const = float(music_db_cn[best.cid]["charts"][diff_format]["constant"])
            except KeyError: # 大概率就是数据库没这歌了，直接走掉就可以
                recent_temp_storage.append(best)
            recent_temp_storage.append(best)
        self.recent = recent_temp_storage

        return self
    
    # 填补数据
    def fill_zero_record(self, ver: str, score: int = 0) -> Self:
        songID_played = [(x.cid, x.diff) for x in self.best]
        diff_change_format = {"basic": "BAS", "advanced": "ADV", "expert": "EXP", "master": "MAS", "ultima": "ULT", "worldsend": "WE"}
        match ver:
            case "jp":
                standard = []
                for songID in music_db:
                    diff_list = ["BAS", "ADV", "EXP", "MAS"] + (["ULT"] if music_db[songID]["data"]["ULT"]["const"] else [])
                    standard.extend([(songID, diff) for diff in diff_list])
            case "cn":
                standard = []
                for songID in music_db_cn:
                    standard.extend([(songID, diff_change_format[diff]) for diff in music_db_cn[songID]["charts"] if music_db_cn[songID]["charts"][diff]["enabled"]])
        set_standard = set(standard)
        set_difference = set_standard.difference(set(songID_played))
        for songID, diff in list(set_difference):
            if music_db.get(songID):
                self.best.append(
                    ScoreItem(
                        score=score,
                        id=int(songID[1:]),
                        diff=diff
                    )
                )
        return self
    
    # fill recent10 in maximum
    def fill_recent_record(self) -> Self:
        self.recent = [self.best[0]] * 10
        return self
    
    # 寻找特定ID的数据
    def search_best_record_by_id(self, cid: str) -> list[ScoreItem]:
        best_record: list[ScoreItem] = list(filter(lambda x: x.cid == cid and x.diff in ["EXP", "MAS", "ULT"], self.best))
        return sorted(best_record, key=lambda x: ["EXP", "MAS", "ULT"].index(x.diff))
    
    @property
    def b30_precise(self) -> Decimal:
        rt = sum([record.rating_precise for record in self.best]) / 30
        return Decimal(rt).quantize(Decimal("0.0000"), rounding=ROUND_DOWN)
    
    @property
    def r10_precise(self) -> Decimal:
        rt = sum([record.rating_precise for record in self.recent]) / 10
        return Decimal(rt).quantize(Decimal("0.000"), rounding=ROUND_DOWN)
    
    @property
    def b30_2dp(self) -> Decimal:
        rt = sum([record.rating_2dp for record in self.best]) / 30
        return Decimal(rt).quantize(Decimal("0.0000"), rounding=ROUND_DOWN)
    
    @property
    def r10_2dp(self) -> Decimal:
        rt = sum([record.rating_2dp for record in self.recent]) / 10
        return Decimal(rt).quantize(Decimal("0.000"), rounding=ROUND_DOWN)

    # 计算rating 不取单曲2dp
    @property
    def rating_precise(self) -> Decimal:
        rt = sum([record.rating_precise for record in self.best + self.recent]) / 40
        return Decimal(rt).quantize(Decimal("0.00"), rounding=ROUND_DOWN)
    
    # 计算rating 取2dp
    @property
    def rating_2dp(self) -> Decimal:
        rt = sum([record.rating_2dp for record in self.best + self.recent]) / 40
        return Decimal(rt).quantize(Decimal("0.00"), rounding=ROUND_DOWN)
    
    @property
    def rating_4dp(self) -> Decimal:
        rt = sum([record.rating_2dp for record in self.best + self.recent]) / 40
        return Decimal(rt).quantize(Decimal("0.0000"), rounding=ROUND_DOWN)

    @property
    def rating_reachable_2dp(self) -> Decimal:
        rt = sum([record.rating_2dp for record in self.best + [self.best[0]] * 10]) / 40 if self.best else 0
        return Decimal(rt).quantize(Decimal("0.00"), rounding=ROUND_DOWN)
    
    @property
    def rating_reachable_4dp(self) -> Decimal:
        rt = sum([record.rating_2dp for record in self.best + [self.best[0]] * 10]) / 40 if self.best else 0
        return Decimal(rt).quantize(Decimal("0.0000"), rounding=ROUND_DOWN)
    
    @property
    def standard_deviation(self) -> Decimal:
        sd = np.std([record.rating_2dp for record in self.best])
        return Decimal(sd).quantize(Decimal("0.0000"), rounding=ROUND_DOWN)
    
    @property
    def distance_to_next_rating(self) -> Decimal:
        distance = Decimal(0.3) - self.b30_2dp * Decimal(30) % Decimal(0.3) + Decimal(2 * 10 ** -8)
        return Decimal(distance).quantize(Decimal("0.0000"), rounding=ROUND_DOWN)
    
    @property
    def overpower_total(self) -> Decimal:
        record = list(filter(lambda x: x.diff in ["MAS", "ULT"], self.best))
        return sum([score.op_current for score in record]) / sum([score.op_max for score in record])
    
    # for developer
    def convert_to_csv_format(self):
        for record in self.best:
            print(record.cid, record.title.replace(",", ""), record.score, record.diff, ("AJ" if record.isAJ else "FC" if record.isFC else ""), sep=",")

    @staticmethod
    def overpower_ratio(record: list[ScoreItem] = None) -> Decimal:
        record = list(filter(lambda x: x.diff in ["MAS", "ULT"], record))
        return sum([score.op_current for score in record]) / sum([score.op_max for score in record])

    @property
    def std_mean(self) -> Decimal | str:
        mean = 1.0006405721 * float(self.b30_2dp) ** 4 - 66.2054373962 * float(self.b30_2dp) ** 3 + 1642.4363958556 * float(self.b30_2dp) ** 2 - 18107.2465845080 * float(self.b30_2dp) + 74851.9419440918
        return round(mean, 4) if float(self.b30_2dp) > 16.00 else "N/A"


class ExcelUpsert:
    def __init__(self, uid: int, isrecent: bool = False):
        self.uid: int = uid
        self.recent: str = "_recent" if isrecent else ""
    
    @property
    def file_name(self) -> str:
        # Fixed: 不明原因 self.uid -> tuple, need to fix 
        return f"./module/chunithm/user/{self.uid}{self.recent}.csv"
    
    # 读取数据
    def read_excel(self) -> list:
        if os.path.isfile(self.file_name):
            with open(self.file_name, "r", encoding="utf-8") as f:
                return [row for row in csv.reader(f)]
        # maybe file does not exist
        elif self.file_name.endswith("_recent.csv"):
            return []
        else:
            raise ChuApiError("Not registered yet")
        
    # create .csv file if file does not exist
    # otherwise just change the name of csv
    def register_excel(self, name: str) -> int:
        if os.path.isfile(self.file_name):
            data = self.read_excel()
            with open(self.file_name, "w") as f:
                data[0][0] = name # change name 
                csv.writer(f).writerows(data)
                return "User name is updated."
        else:
            with open(self.file_name, "w") as f:
                csv.writer(f).writerow([name, 0])
                return ".csv file is created."
    
    def update_score(self, cid: str, score: str, diff: str, status: str = "") -> str:
        # get all record in .csv file
        entries = self.read_excel()
        # create a flag to check insert or update
        flag_update = False

        if diff.upper() not in ["EXP", "MAS", "ULT"] or not score.isdigit():
            raise ChuApiError("Input was invalid.")

        for index, entry in enumerate(entries[1:]):
            # Format: c428,Aleph-0,1008738,EXP,FC
            if cid == entry[0] and diff.upper() == entry[3]: # if record exists
                entry[2] = score
                entry[4] = status.upper()
                entries[index+1] = entry
                flag_update = True
                break
        
        if not music_db.get(cid):
            raise ChuApiError("No such song in database.")
        
        if not flag_update: # if flag_update == True -> insert new record
            entries.append([cid, music_db[cid]['title'].replace(",", ""), score, diff.upper(), status.upper()])
        
        with open(self.file_name, "w") as f:
            csv.writer(f).writerows(entries)
            return f"Updated\n{music_db[cid]['title']}\n{score} {diff.upper()} {status.upper()}".strip()

class B30Image_v2:
    def __init__(self, b30_record: Record, uid: int) -> None:
        self.b30_record: Record = b30_record
        self.uid = uid
    
    @staticmethod
    def char_full_to_half(s):
        s1 = ""
        for uchar in s:
            inside_code = ord(uchar)
            if inside_code == 0x3000:
                inside_code = 0x0020
            else:
                inside_code -= 0xfee0
            if inside_code < 0x0020 or inside_code > 0x7e: #转完之后不是半角字符返回原来的字符
                inside_code = uchar
            else:
                inside_code = chr(inside_code)
            s1 += inside_code
        return s1
        
    def generate_b30_image_with_recent(self):
        base = Image.open("./src/chunithm/blue.PNG").resize((1800, 2085))

        ico = Image.open("./src/chunithm/ico.png").convert("RGBA")
        ico = ico.resize((180, 180))
        base.paste(ico, (40, 40), mask=ico)

        ico_sp = Image.open("./src/chunithm/logo_sp.png").convert("RGBA")
        ico_sp = ico_sp.resize((240, 120))
        base.paste(ico_sp, (1540, 80), mask=ico_sp)

        draw = ImageDraw.Draw(base)

        font = ImageFont.truetype("./src/chunithm/font/BAHNSCHRIFT.ttf", 80)
        font_2 = ImageFont.truetype("./src/chunithm/font/BAHNSCHRIFT.ttf", 40)
        font_4 = ImageFont.truetype("./src/chunithm/font/XiaolaiSC-Regular.ttf", 60)

        draw.polygon([(325, 40), (240, 220), (1500, 220), (1560, 40)], fill=(255, 255, 255))

        max_index = 0

        self.b30_record.name = self.char_full_to_half(self.b30_record.name)
        size = font_4.getlength(self.b30_record.name)
        while size > 345:
            max_index -= 1
            size = font_4.getlength(self.b30_record.name[:max_index] + "..")

        draw.text((350, 60), "Player name:", (0, 0, 0), font_2)
        draw.text((350, 110), self.b30_record.name[:max_index].strip() + ".." if max_index else self.b30_record.name, (0, 0, 0), font_4)

        draw.text((730, 60), f"Rating: {self.b30_record.rating_2dp}", (0, 0, 0), font)
        draw.text((1190, 90), f"/Max: {self.b30_record.rating_max}", (0, 0, 0), font_2)

        draw.text((730, 160), f"Best30: {self.b30_record.b30_2dp} / Recent10: {self.b30_record.r10_2dp} / PC: {self.b30_record.playCount}", (0, 0, 0), font_2)

        draw.line([(10, 270), (580, 270)], fill=(255, 255, 255), width=10)

        draw.text((590, 251), "Best", (255, 255, 255), font_2)

        draw.line([(680, 270), (1490, 270)], fill=(255, 255, 255), width=10)

        draw.text((1500, 251), "Recent", (255, 255, 255), font_2)

        draw.line([(1630, 270), (1790, 270)], fill=(255, 255, 255), width=10)

        draw.line([(1324, 270), (1324, 1990)], fill=(255, 255, 255), width=10)

        count = 0

        for song in self.b30_record.best:
            pic = self.song_record_image(record=song, count=count+1)
            base.paste(pic, (20 + count % 3 * 430, 310 + count // 3 * 168))
            count += 1

        count = 0

        for song in self.b30_record.recent:
            pic = self.song_record_image(record=song, count=count+1)
            base.paste(pic, (1350, 310 + count * 168))
            count += 1
        
        base.save(f"./src/temp/res_{self.uid}.jpg")

        return f"[CQ:image,file=file:///{path}/src/temp/res_{self.uid}.jpg]"
    
    def generate_b30_image_without_recent(self):
        base = Image.open("./src/chunithm/blue.PNG").resize((1315, 2085))

        ico = Image.open("./src/chunithm/ico.png").convert("RGBA")
        ico_sp = Image.open("./src/chunithm/logo_sp.png").convert("RGBA")

        ico = ico.resize((180, 180))
        ico_sp = ico_sp.resize((240, 120))

        base.paste(ico, (60, 40), mask=ico)

        draw = ImageDraw.Draw(base)

        font_4 = ImageFont.truetype("./src/chunithm/font/XiaolaiSC-Regular.ttf", 60)
        font_2 = ImageFont.truetype("./src/chunithm/font/BAHNSCHRIFT.ttf", 40)

        max_index = 0

        self.b30_record.name = self.char_full_to_half(self.b30_record.name)
        size = font_4.getlength(self.b30_record.name)
        while size > 450:
            max_index -= 1
            size = font_4.getlength(self.b30_record.name[:max_index] + "..")

        draw.polygon([(340, 40), (280, 220), (1240, 220), (1290, 40)], fill=(255, 255, 255))
        draw.text((380, 60), "Player name:", (0, 0, 0), font_2)
        draw.text((380, 110), self.b30_record.name[:max_index].strip() + ".." if max_index else self.b30_record.name, (0, 0, 0), font_4)

        draw.text((900, 160), f"Best30: {self.b30_record.b30_2dp}", (0, 0, 0), font_2)

        draw.line([(10, 270), (580, 270)], fill=(255, 255, 255), width=10)

        draw.text((590, 251), "Best", (255, 255, 255), font_2)

        draw.line([(680, 270), (1300, 270)], fill=(255, 255, 255), width=10)

        count = 0

        for song in self.b30_record.best:
            pic = self.song_record_image(record=song, count=count+1)
            base.paste(pic, (20 + count % 3 * 430, 310 + count // 3 * 168))
            count += 1
        
        base.save(f"./src/temp/res_{self.uid}.jpg")

        return f"[CQ:image,file=file:///{path}/src/temp/res_{self.uid}.jpg]"
    
    def generate_level_image(self, level: float, page: int = 1):
        base = Image.open("./src/chunithm/blue.PNG").resize((1800, 2085))

        ico_sp = Image.open("./src/chunithm/logo_sp.png").convert("RGBA")
        ico_sp = ico_sp.resize((420, 240))

        base.paste(ico_sp, (20, 50), mask=ico_sp)

        draw = ImageDraw.Draw(base)

        font = ImageFont.truetype("./src/chunithm/font/BAHNSCHRIFT.ttf", 80)
        font_4 = ImageFont.truetype("./src/chunithm/font/XiaolaiSC-Regular.ttf", 60)
        font_2 = ImageFont.truetype("./src/chunithm/font/BAHNSCHRIFT.ttf", 60)

        draw.line([(10, 370), (1790, 370)], fill=(255, 255, 255), width=10)

        draw.text((540, 80), f"CHUNITHM Lv.{int(level)}{'' if level % 1 == 0 else '+'} Score List", "#000000", font)
        draw.text((540, 250), f"User: {self.char_full_to_half(self.b30_record.name)}", "#000000", font_4)        

        entries = self.b30_record.filter_record_by_level(level=level)

        sssp_count = len(list(filter(lambda x: x.score >= 1009000,entries)))
        sss_count = len(list(filter(lambda x: x.score >= 1007500,entries)))
        fc_count = len(list(filter(lambda x: x.isFC,entries)))
        aj_count = len(list(filter(lambda x: x.isAJ,entries)))

        draw.text((540, 180), f"SSS+: {sssp_count} / SSS: {sss_count} / AJ&FC: {aj_count}/{fc_count}", "#000000", font_2)

        data_count = len(entries)
        
        draw.text((40, 2000), f"Page: {page}/{int(data_count//36)+1}", "#000000", ImageFont.truetype("./src/chunithm/font/BAHNSCHRIFT.ttf", 40))

        count = 0

        for song in entries[36*(page-1):36*page]:
            pic = self.song_record_image(record=song, count=36*(page-1)+count+1)
            base.paste(pic, (24 + count % 4 * 445, 410 + count // 4 * 168))
            count += 1
        
        base.save(f"src/temp/res_{self.uid}.jpg")

        return f"[CQ:image,file=file:///{path}/src/temp/res_{self.uid}.jpg]"

        
    @staticmethod
    def song_record_image(record: ScoreItem, count: int):
        color = {
            'Master': (187, 51, 238),
            'MAS': (187, 51, 238),
            'Expert': (238, 67, 102),
            'EXP': (238, 67, 102),
            'Advanced': (254, 170, 0),
            'ADV': (254, 170, 0),
            'Ultima': (0, 0, 0),
            'ULT': (0, 0, 0),
            'Basic': (102, 221, 17),
            'BAS': (102, 221, 17)
        }

        base = Image.new("RGBA", (620, 240), (255, 255, 255, 175))

        try:
            jacket = Image.open(f'./src/chunithm/image/{record.cid}.jpg').resize((186, 186))
        except FileNotFoundError:
            jacket = Image.new("RGB", (186, 186), (255, 255, 255))
        finally:
            base.paste(jacket, (32, 28))

        draw = ImageDraw.Draw(base)
        font = ImageFont.truetype('./src/chunithm/font/NotoSansHans-Regular-2.ttf', 37)

        max_index = 0

        size = font.getlength(record.title)
        while size > 345:
            max_index -= 1
            size = font.getlength(record.title[:max_index] + "..")

        draw.text((270, 38), record.title[:max_index].strip() + ".." if max_index else record.title, '#000000', font)

        font_2 = ImageFont.truetype('./src/chunithm/font/BAHNSCHRIFT.TTF', 58)
        draw.text((240, 107), str(record.score), '#000000', font_2)

        font_4 = ImageFont.truetype('./src/chunithm/font/BAHNSCHRIFT.TTF', 29)
        length = font_4.getlength(f"(#{count})")
        draw.text((610-length, 135), f"(#{count})", '#000000', font_4)

        font_3 = ImageFont.truetype('./src/chunithm/font/BAHNSCHRIFT.TTF', 42)
        if record.isAJ:
            draw.text((570-length, 135), "AJ", '#000000', font_4)
        elif record.isFC:
            draw.text((570-length, 135), "FC", '#000000', font_4)

        draw.rectangle((240, 27, 255, 87), fill=color[record.diff])

        draw.text((240, 177), "Rating: " + str(record.const) + '  >  ' + str(record.rating_2dp), (0, 0, 0), font_3)

        base = base.resize((420, 158))
        return base



class SongInfoImage:
    def __init__(self, b30_record: Record, uid: int, cid: str) -> None:
        self.b30_record = b30_record
        self.uid = uid
        self.cid = cid
    
    def generate_song_info_image(self):

        # 创建一个底图对象
        base = Image.open("./src/chunithm/blue.PNG").resize((2700, 1830))

        # 创建一个画图对象
        draw = ImageDraw.Draw(base)

        # 留50px的margin, 上面500px留着放歌的数据

        # 先创建一个白底 alpha=128的背景
        background_songinfo = Image.new("RGBA", (2400, 720), (255, 255, 255, 128))
        base.paste(background_songinfo, box=(150, 150), mask=background_songinfo)

        # 曲绘上下左右留20px的margin, size=200
        song_jacket = Image.open(f'./src/chunithm/image/{self.cid}.jpg').resize((600, 600))
        base.paste(song_jacket, box=(210, 210))

        # 然后右边540px开始填曲目数据, 再留20px的margin

        # 创建字体对象
        font_1 = ImageFont.truetype('./src/chunithm/font/BAHNSCHRIFT.TTF', 87)
        font_2 = ImageFont.truetype('./src/chunithm/font/BAHNSCHRIFT.TTF', 42)
        font_3 = ImageFont.truetype('./src/chunithm/font/NotoSansHans-Regular-2.ttf', 87)
        font_4 = ImageFont.truetype('./src/chunithm/font/NotoSansHans-Regular-2.ttf', 42)

        # 获取数据
        songinfo_db = music_db[self.cid]

        # 填入数据
        draw.text((870, 210), "TITLE", (0, 0, 0), font_2)
        max_index = 0
        size = font_3.getlength(songinfo_db["title"])
        while size > 1661:
            max_index -= 1
            size = font_3.getlength(songinfo_db["title"][:max_index] + "..")
        draw.text((870, 261), songinfo_db["title"][:max_index].strip() + ".." if max_index else songinfo_db["title"], (0, 0, 0), font_1 if songinfo_db["title"].isascii() else font_3)
        
        draw.text((870, 360), "ARTIST", (0, 0, 0), font_2)
        size = font_3.getlength(songinfo_db["artist"])
        max_index = 0
        while size > 1661:
            max_index -= 1
            size = font_3.getlength(songinfo_db["artist"][:max_index] + "..")
        draw.text((870, 411), songinfo_db["artist"][:max_index].strip() + ".." if max_index else songinfo_db["artist"], (0, 0, 0), font_1 if songinfo_db["artist"].isascii() else font_3)

        length = 0 # 存放总长度

        draw.text((870, 510), "GENRE", (0, 0, 0), font_2)
        draw.text((870, 561), songinfo_db["genre"], (0, 0, 0), font_1 if songinfo_db["genre"].isascii() else font_3)
        length += max(font_2.getlength("GENRE"), font_1.getlength(songinfo_db["genre"]) if songinfo_db["genre"].isascii() else font_3.getlength(songinfo_db["genre"])) + 45

        draw.text((870 + length, 510), "RELEASE DATE", (0, 0, 0), font_2)
        draw.text((870 + length, 561), songinfo_db["updatedAt"].replace("-", "/"), (0, 0, 0), font_1)
        length += max(font_2.getlength("RELEASE DATE"), font_1.getlength(songinfo_db["updatedAt"].replace("-", "/"))) + 45

        draw.text((870 + length, 510), "BPM", (0, 0, 0), font_2)
        draw.text((870 + length, 561), songinfo_db["bpm"], (0, 0, 0), font_1)
        length += max(font_2.getlength("BPM"), font_1.getlength(songinfo_db["bpm"])) + 45

        draw.text((870 + length, 510), "Version", (0, 0, 0), font_2)
        draw.text((870 + length, 561), songinfo_db["version"], (0, 0, 0), font_1 if songinfo_db["version"].isascii() else font_3)

        draw.text((870, 660), "Charter", (0, 0, 0), font_2)

        length = 0 # 存放总共的长度
        for diff in ["EXPERT", "MASTER", "ULTIMA"]:
            if designer := songinfo_db["data"][diff[:3]]["designer"]:
                draw.text((870 + length, 711), diff, (0, 0, 0), font_2)
                draw.text((870 + length, 762), designer, (0, 0, 0), font_4)
                length += max(font_4.getlength(designer), font_2.getlength(diff)) + 45

        # 获取单曲分数

        filtered_songinfo: list[ScoreItem] = self.b30_record.search_best_record_by_id(cid=self.cid)

        # 画图 + 填入数据

        # color常数
        color = {
                'MASTER': (187, 51, 238),
                'EXPERT': (238, 67, 102),
                'ULTIMA': (0, 0, 0)
            }

        for index, diff in enumerate(["EXPERT", "MASTER", "ULTIMA"]):
            if len(filtered_songinfo) >= index + 1:
                draw.rounded_rectangle(xy=(150, 900 + index * 300, 2550, 1170 + index * 300), radius=45, fill=(255, 255, 255), outline=color[diff], width=6)
                draw.rectangle(xy=(210, 975 + index * 300, 240, 1095 + index * 300), fill=color[diff])
                draw.text((285, 993 + index * 300), diff, (0, 0, 0), font_1)

                if filtered_songinfo[index].score:
                    # 填入数据
                    draw.text((660, 942 + index * 300), "SCORE", (0, 0, 0), font_2)
                    draw.text((660, 993 + index * 300), str(format(filtered_songinfo[index].score, ",")), (0, 0, 0), font_1)
                    
                    draw.text((1050, 942 + index * 300), "RATING", (0, 0, 0), font_2)
                    draw.text((1050, 993 + index * 300), f"{filtered_songinfo[index].const} > {filtered_songinfo[index].rating_2dp}", (0, 0, 0), font_1)
                    length_rating = font_1.getlength(f"{filtered_songinfo[index].const} > {filtered_songinfo[index].rating_2dp}")
                    draw.text((1050 + length_rating, 1032 + index * 300), str(filtered_songinfo[index].rating_4dp)[-2:], (0, 0, 0), font_2)

                    draw.text((1590, 942 + index * 300), "OVERPOWER", (0, 0, 0), font_2)
                    draw.text((1590, 993 + index * 300), f"{filtered_songinfo[index].op_current}", (0, 0, 0), font_1)
                    length_overpower = font_1.getlength(f"{filtered_songinfo[index].op_current}")
                    draw.text((1596 + length_overpower, 1032 + index * 300), f"/ {filtered_songinfo[index].op_max}", (0, 0, 0), font_2)

                    draw.text((2106, 942 + index * 300), "STATUS", (0, 0, 0), font_2)
                    if filtered_songinfo[index].isAJ:
                        draw.text((2106, 993 + index * 300), "AJ", (0, 0, 0), font_1)
                    elif filtered_songinfo[index].isFC:
                        draw.text((2106, 993 + index * 300), "FC", (0, 0, 0), font_1)

                else:
                    draw.text((1200, 993 + index * 300), "NOT PLAYED YET", (156, 156, 156), font_1)


        base.save(f"./src/temp/res_{self.uid}.jpg")

        return f"[CQ:image,file=file:///{path}/src/temp/res_{self.uid}.jpg]"

class B30Image_v3:
    def __init__(self, b30_record: Record, uid: int) -> None:
        self.b30_record: Record = b30_record
        self.uid = uid

    @staticmethod
    def char_full_to_half(s):
        s1 = ""
        for uchar in s:
            inside_code = ord(uchar)
            if inside_code == 0x3000:
                inside_code = 0x0020
            else:
                inside_code -= 0xfee0
            if inside_code < 0x0020 or inside_code > 0x7e: #转完之后不是半角字符返回原来的字符
                inside_code = uchar
            else:
                inside_code = chr(inside_code)
            s1 += inside_code
        return s1
    
    def generate_b30_image(self):
        
        base = Image.open("./src/chunithm/background.png").resize((6000, 4600))

        mask = Image.new("RGBA", (6000, 5500), (255, 255, 255, 64))

        base.paste(mask, mask=mask)

        chara = Image.open("./src/chunithm/chara.png").convert("RGBA")
        base.paste(chara, box=(3876, 910), mask=chara)

        chara_dim = Image.open("./src/chunithm/chara_diminished.png").convert("RGBA").resize((220, 220))

        # paste icon on base
        icon = Image.open("./src/chunithm/version_ico.png").convert("RGBA").resize((842, 602))
        base.paste(icon, box=(4958, 200), mask=icon)

        draw = ImageDraw.Draw(base)

        draw.polygon([(250, 325), (50, 925), (4700, 925), (4900, 325)], fill=(255, 255, 255))

        best30_frame = Image.open("./src/chunithm/rating_frame.png").convert("RGBA").resize((1340, 1268))
        base.paste(best30_frame, box=(3500, 0), mask=best30_frame)

        draw.line([(50, 3390), (4200, 3390)], fill=(255, 255, 255), width=18)

        font_icon = ImageFont.truetype("./src/chunithm/font/AvenirNextCyr-Regular.ttf", 150)

        draw.rounded_rectangle((50, 975, 907, 1205), radius=50, fill=(233, 247, 255), outline=(255, 255, 255), width=15)
        base.paste(chara_dim, box=(100, 995), mask=chara_dim)
        draw.text(xy=(350, 1000), text="Best 30", fill="#77507f", font=font_icon)

        draw.rounded_rectangle((50, 3440, 1082, 3670), radius=50, fill=(233, 247, 255), outline=(255, 255, 255), width=15)
        base.paste(chara_dim, box=(100, 3460), mask=chara_dim)
        draw.text(xy=(350, 3460), text="Recent 10", fill="#77507f", font=font_icon)

        # draw.rounded_rectangle((1840, 3440, 2834, 3670), radius=50, fill=(233, 247, 255), outline=(255, 255, 255), width=15)
        # base.paste(chara_dim, box=(1890, 3460), mask=chara_dim)
        # draw.text(xy=(2140, 3460), text="Bar Chart", fill="#77507f", font=font_icon)

        # max 用到 width 3900
        font_name = ImageFont.truetype("./src/chunithm/font/XiaolaiSC-Regular.ttf", 150)
        font_title_half = ImageFont.truetype("./src/chunithm/font/AvenirNextCyr-Regular.ttf", 75)
        font_content_half = ImageFont.truetype("./src/chunithm/font/AvenirNextCyr-Regular.ttf", 150)


        draw.text(xy=(325, 375), text="Player name", fill="#77507f", font=font_title_half)
        draw.text(xy=(325, 470), text=self.char_full_to_half(self.b30_record.name), fill="#77507f", font=font_name)

        length = max(font_name.getlength(self.char_full_to_half(self.b30_record.name)), font_title_half.getlength("Player name"))

        draw.text(xy=(550 + length, 375), text="Distance To Next 0.01", fill="#77507f", font=font_title_half)
        draw.text(xy=(550 + length, 455), text=f"+{self.b30_record.distance_to_next_rating}", fill="#77507f", font=font_content_half)

        draw.text(xy=(1465 + length, 375), text="Best30 (Precise)", fill="#77507f", font=font_title_half)
        draw.text(xy=(1465 + length, 455), text=str(self.b30_record.b30_precise), fill="#77507f", font=font_content_half)

        draw.text(xy=(325, 650), text="Rating", fill="#77507f", font=font_title_half)
        draw.text(xy=(325, 720), text=str(self.b30_record.rating_2dp), fill="#77507f", font=font_content_half)
        length = font_content_half.getlength(str(self.b30_record.rating_2dp))
        draw.text(xy=(325 + length, 797), text=str(self.b30_record.rating_4dp)[-2:], fill="#77507f", font=font_title_half)

        draw.text(xy=(1000, 650), text="Reachable Rating", fill="#77507f", font=font_title_half)
        draw.text(xy=(1000, 720), text=str(self.b30_record.rating_reachable_2dp), fill="#77507f", font=font_content_half)
        length = font_content_half.getlength(str(self.b30_record.rating_reachable_2dp))
        draw.text(xy=(1000 + length, 797), text=str(self.b30_record.rating_reachable_4dp)[-2:], fill="#77507f", font=font_title_half)

        draw.text(xy=(1750, 650), text="Max Rating", fill="#77507f", font=font_title_half)
        draw.text(xy=(1750, 720), text=str(self.b30_record.rating_max), fill="#77507f", font=font_content_half)

        draw.text(xy=(2275, 650), text="Standard Deviation", fill="#77507f", font=font_title_half)
        draw.text(xy=(2275, 720), text=str(self.b30_record.standard_deviation)[:-2], fill="#77507f", font=font_content_half)
        length = font_content_half.getlength(str(self.b30_record.standard_deviation)[:-2])
        draw.text(xy=(2275 + length, 797), text=str(self.b30_record.standard_deviation)[-2:], fill="#77507f", font=font_title_half)

        draw.text(xy=(3000, 650), text="Play Count", fill="#77507f", font=font_title_half)
        draw.text(xy=(3000, 720), text=str(self.b30_record.playCount), fill="#77507f", font=font_content_half)

        font_title = ImageFont.truetype("./src/chunithm/font/BAHNSCHRIFT.ttf", 105)
        font_content = ImageFont.truetype("./src/chunithm/font/BAHNSCHRIFT.ttf", 220)

        length = font_title.getlength("Best30")
        draw.text(xy=(4179 - length / 2, 361), text="Best30", fill="#77507f", font=font_title)
        length = font_content.getlength(str(self.b30_record.b30_2dp))
        draw.text(xy=(4179 - length / 2, 514), text=str(self.b30_record.b30_2dp), fill="#77507f", font=font_content)
        length = int(font_title.getlength(f"Recent10: {self.b30_record.r10_2dp}"))
        draw.text(xy=(4179 - length / 2, 765), text=f"Recent10: {self.b30_record.r10_2dp}", fill="#77507f", font=font_title)


        count = 0

        for song in self.b30_record.best:
            pic = self.song_record_image(record=song, count=count+1)
            base.paste(pic, (50 + count % 5 * 878, 1255 + count // 5 * 352), mask=pic)
            count += 1

        count = 0
        
        for song in self.b30_record.recent:
            pic = self.song_record_image(record=song, count=count+1) if self.b30_record.enable_recent else self.song_record_not_avaliable()
            base.paste(pic, (50 + count % 5 * 878, 3720 + count // 5 * 352), mask=pic)
            count += 1
        
        # bar_chart = self.bar_chart()

        # base.paste(bar_chart, (1840, 3720), bar_chart)

        base.save(f"./src/temp/res_{self.uid}.jpg")

        return f"[CQ:image,file=file:///{path}/src/temp/res_{self.uid}.jpg]"
    
    def generate_b30_image_with_bar(self):
        
        base = Image.open("./src/chunithm/background.png").resize((6000, 5530))

        mask = Image.new("RGBA", (6000, 5530), (255, 255, 255, 64))

        base.paste(mask, mask=mask)

        chara = Image.open("./src/chunithm/chara.png").convert("RGBA")
        base.paste(chara, box=(3876, 910), mask=chara)

        chara_dim = Image.open("./src/chunithm/chara_diminished.png").convert("RGBA").resize((220, 220))

        # paste icon on base
        icon = Image.open("./src/chunithm/version_ico.png").convert("RGBA").resize((842, 602))
        base.paste(icon, box=(4958, 200), mask=icon)

        draw = ImageDraw.Draw(base)

        draw.polygon([(250, 325), (50, 925), (4700, 925), (4900, 325)], fill=(255, 255, 255))

        best30_frame = Image.open("./src/chunithm/rating_frame.png").convert("RGBA").resize((1340, 1268))
        base.paste(best30_frame, box=(3500, 0), mask=best30_frame)

        draw.line([(50, 3390), (4200, 3390)], fill=(255, 255, 255), width=18)

        draw.line([(1821, 3390), (1821, 5480)], fill=(255, 255, 255), width=18)

        font_icon = ImageFont.truetype("./src/chunithm/font/AvenirNextCyr-Regular.ttf", 150)

        draw.rounded_rectangle((50, 975, 907, 1205), radius=50, fill=(233, 247, 255), outline=(255, 255, 255), width=15)
        base.paste(chara_dim, box=(100, 995), mask=chara_dim)
        draw.text(xy=(350, 1000), text="Best 30", fill="#77507f", font=font_icon)

        draw.rounded_rectangle((50, 3440, 1082, 3670), radius=50, fill=(233, 247, 255), outline=(255, 255, 255), width=15)
        base.paste(chara_dim, box=(100, 3460), mask=chara_dim)
        draw.text(xy=(350, 3460), text="Recent 10", fill="#77507f", font=font_icon)

        draw.rounded_rectangle((1860, 3440, 2854, 3670), radius=50, fill=(233, 247, 255), outline=(255, 255, 255), width=15)
        base.paste(chara_dim, box=(1910, 3460), mask=chara_dim)
        draw.text(xy=(2160, 3460), text="Bar Chart", fill="#77507f", font=font_icon)

        # max 用到 width 3900
        font_name = ImageFont.truetype("./src/chunithm/font/XiaolaiSC-Regular.ttf", 150)
        font_title_half = ImageFont.truetype("./src/chunithm/font/AvenirNextCyr-Regular.ttf", 75)
        font_content_half = ImageFont.truetype("./src/chunithm/font/AvenirNextCyr-Regular.ttf", 150)

        draw.text(xy=(325, 375), text="Player name", fill="#77507f", font=font_title_half)
        draw.text(xy=(325, 470), text=self.char_full_to_half(self.b30_record.name), fill="#77507f", font=font_name)

        length = max(font_name.getlength(self.char_full_to_half(self.b30_record.name)), font_title_half.getlength("Player name"))

        draw.text(xy=(550 + length, 375), text="Distance To Next 0.01", fill="#77507f", font=font_title_half)
        draw.text(xy=(550 + length, 455), text=f"+{self.b30_record.distance_to_next_rating}", fill="#77507f", font=font_content_half)

        draw.text(xy=(1465 + length, 375), text="Best30 (Precise)", fill="#77507f", font=font_title_half)
        draw.text(xy=(1465 + length, 455), text=str(self.b30_record.b30_precise), fill="#77507f", font=font_content_half)

        draw.text(xy=(325, 650), text="Rating", fill="#77507f", font=font_title_half)
        draw.text(xy=(325, 720), text=str(self.b30_record.rating_2dp), fill="#77507f", font=font_content_half)
        length = font_content_half.getlength(str(self.b30_record.rating_2dp))
        draw.text(xy=(325 + length, 797), text=str(self.b30_record.rating_4dp)[-2:], fill="#77507f", font=font_title_half)

        draw.text(xy=(1000, 650), text="Reachable Rating", fill="#77507f", font=font_title_half)
        draw.text(xy=(1000, 720), text=str(self.b30_record.rating_reachable_2dp), fill="#77507f", font=font_content_half)
        length = font_content_half.getlength(str(self.b30_record.rating_reachable_2dp))
        draw.text(xy=(1000 + length, 797), text=str(self.b30_record.rating_reachable_4dp)[-2:], fill="#77507f", font=font_title_half)


        draw.text(xy=(1750, 650), text="Max Rating", fill="#77507f", font=font_title_half)
        draw.text(xy=(1750, 720), text=str(self.b30_record.rating_max), fill="#77507f", font=font_content_half)

        draw.text(xy=(2275, 650), text="Standard Deviation", fill="#77507f", font=font_title_half)
        draw.text(xy=(2275, 720), text=str(self.b30_record.standard_deviation)[:-2], fill="#77507f", font=font_content_half)
        length = font_content_half.getlength(str(self.b30_record.standard_deviation)[:-2])
        draw.text(xy=(2275 + length, 797), text=str(self.b30_record.standard_deviation)[-2:], fill="#77507f", font=font_title_half)

        draw.text(xy=(3000, 650), text="Play Count", fill="#77507f", font=font_title_half)
        draw.text(xy=(3000, 720), text=str(self.b30_record.playCount), fill="#77507f", font=font_content_half)

        font_title = ImageFont.truetype("./src/chunithm/font/BAHNSCHRIFT.ttf", 105)
        font_content = ImageFont.truetype("./src/chunithm/font/BAHNSCHRIFT.ttf", 220)

        length = font_title.getlength("Best30")
        draw.text(xy=(4179 - length / 2, 361), text="Best30", fill="#77507f", font=font_title)
        length = font_content.getlength(str(self.b30_record.b30_2dp))
        draw.text(xy=(4179 - length / 2, 514), text=str(self.b30_record.b30_2dp), fill="#77507f", font=font_content)
        length = int(font_title.getlength(f"Recent10: {self.b30_record.r10_2dp}"))
        draw.text(xy=(4179 - length / 2, 765), text=f"Recent10: {self.b30_record.r10_2dp}", fill="#77507f", font=font_title)


        count = 0

        for song in self.b30_record.best:
            pic = self.song_record_image(record=song, count=count+1)
            base.paste(pic, (50 + count % 5 * 878, 1255 + count // 5 * 352), mask=pic)
            count += 1

        count = 0
        
        for song in self.b30_record.recent:
            pic = self.song_record_image(record=song, count=count+1) if self.b30_record.enable_recent else self.song_record_not_avaliable()
            base.paste(pic, (50 + count % 2 * 878, 3720 + count // 2 * 352), mask=pic)
            count += 1
        
        bar_chart = self.bar_chart()

        base.paste(bar_chart, (1860, 3770), bar_chart)

        base.save(f"./src/temp/res_{self.uid}.jpg")

        return f"[CQ:image,file=file:///{path}/src/temp/res_{self.uid}.jpg]"

    @staticmethod
    def song_record_image(record: ScoreItem, count: int) -> Image:
        color = {
            'Master': (187, 51, 238),
            'MAS': (187, 51, 238),
            'Expert': (238, 67, 102),
            'EXP': (238, 67, 102),
            'Advanced': (254, 170, 0),
            'ADV': (254, 170, 0),
            'Ultima': (0, 0, 0),
            'ULT': (0, 0, 0),
            'Basic': (102, 221, 17),
            'BAS': (102, 221, 17)
        }

        base = Image.new("RGBA", (620, 240), (255, 255, 255, 240))

        try:
            jacket = Image.open(f'./src/chunithm/image/{record.cid}.jpg').resize((186, 186))
        except FileNotFoundError:
            jacket = Image.new("RGB", (186, 186), (255, 255, 255))
        finally:
            base.paste(jacket, (32, 28))

        draw = ImageDraw.Draw(base)
        font = ImageFont.truetype('./src/chunithm/font/NotoSansHans-Regular-2.ttf', 37)

        max_index = 0

        size = font.getlength(record.title)
        while size > 345:
            max_index -= 1
            size = font.getlength(record.title[:max_index] + "..")

        draw.text((270, 38), record.title[:max_index].strip() + ".." if max_index else record.title, '#000000', font)

        font_2 = ImageFont.truetype('./src/chunithm/font/BAHNSCHRIFT.TTF', 58)
        draw.text((240, 107), str(record.score), '#000000', font_2)

        font_4 = ImageFont.truetype('./src/chunithm/font/BAHNSCHRIFT.TTF', 29)
        length = font_4.getlength(f"(#{count})")
        draw.text((610-length, 135), f"(#{count})", '#000000', font_4)

        font_3 = ImageFont.truetype('./src/chunithm/font/BAHNSCHRIFT.TTF', 42)
        if record.isAJ:
            draw.text((570-length, 135), "AJ", '#000000', font_4)
        elif record.isFC:
            draw.text((570-length, 135), "FC", '#000000', font_4)

        draw.rectangle((240, 27, 255, 87), fill=color[record.diff])

        draw.text((240, 181), f"Rating: {record.const} > {record.rating_2dp}", (0, 0, 0), font_3)
        length = font_3.getlength(f"Rating: {record.const} > {record.rating_2dp}")
        draw.text((242 + length, 190), str(record.rating_4dp)[-2:], (0, 0, 0), font_4)

        return base.resize((858, 332))
    
    @staticmethod
    def song_record_not_avaliable() -> Image:

        base = Image.new("RGBA", (620, 240), (255, 255, 255, 240))

        font_2 = ImageFont.truetype('./src/chunithm/font/BAHNSCHRIFT.TTF', 60)

        length = font_2.getlength("NOT AVALIABLE")

        draw = ImageDraw.Draw(base)

        draw.text(xy=(310 - length / 2, 90), text="NOT AVALIABLE", fill=(150, 150, 150), font=font_2)

        return base.resize((858, 332))
    
    def bar_chart(self) -> Image:

        base = Image.new("RGBA", (3800, 2400), (255, 255, 255, 240))

        font = ImageFont.truetype('./src/chunithm/font/BAHNSCHRIFT.TTF', 100)
        font_avg = ImageFont.truetype('./src/chunithm/font/BAHNSCHRIFT.TTF', 80)

        draw = ImageDraw.Draw(base)

        # 75% height
        # range = Decimal(max([x.const for x in self.b30_record.best]) + 2.15) - self.b30_record.best[-1].rating_2dp

        _range = self.b30_record.best[0].rating_2dp - self.b30_record.best[-1].rating_2dp

        draw.line([(300, 50), (300, 2250)], fill=(0, 0, 0), width=8)

        draw.line([(296, 2250), (3700, 2250)], fill=(0, 0, 0), width=8)

        # 0.05 intervals

        gap = (float(_range) // 0.4 + 1) * 0.05
        
        intervals = [float(x.rating_precise + 2 * 10 ** -8) // gap * gap for x in self.b30_record.best]

        for i in range(10):
            intervals += [intervals[0] + gap * i, intervals[0] - gap * i]


        for i in list(set(intervals)):
            i = Decimal(i).quantize(Decimal("0.00"))
            distance_from_b30 = i - self.b30_record.best[-1].rating_2dp
            height = 1850 - distance_from_b30 / _range * 1300
            if height < 100 or height > 2100:
                continue
            length = font.getlength(str(i))
            draw.text((270 - length, height - 50), text=str(i), fill="#000000", font=font)
            draw.line([(310, height), (3700, height)], fill=(180, 180, 180), width=4)
        
        # average line

        distance_from_b30 = self.b30_record.b30_2dp - self.b30_record.best[-1].rating_2dp
        height_avg = 1850 - distance_from_b30 / _range * 1300
        length = font_avg.getlength(f"AVG:{self.b30_record.b30_2dp}")
        draw.text((3700 - length, height_avg - 80), text=f"AVG:{self.b30_record.b30_2dp}", fill="#ee2200", font=font_avg)
        draw.line([(310, height_avg), (3700, height_avg)], fill="#ee2200", width=4)

        for index, best in enumerate(self.b30_record.best):
            distance_from_b30 = best.rating_2dp - self.b30_record.best[-1].rating_2dp
            height = 1850 - distance_from_b30 / _range * 1300

            # if height_avg > height:
            #     draw.rectangle(((360 + 111 * index, height), (428 + 111 * index, height_avg - 3)), fill=(150, 235, 202)) # height_avg - 3 -> 2238
            # else:
            #     draw.rectangle(((360 + 111 * index, height_avg + 3), (428 + 111 * index, height)), fill=(235, 174, 150))

            draw.rectangle(((360 + 111 * index, height), (428 + 111 * index, 2246)), fill="#ebc780")

            length = font_avg.getlength(str(index + 1))

            draw.text((394 + 111 * index - length / 2, 2265), text=str(index + 1), font=font_avg, fill="#000000")
        
        return base.resize((2600, 1670))

class B30Image_v1:
    def __init__(self, b30_record: Record, uid: int) -> None:
        self.b30_record: Record = b30_record
        self.uid = uid

    @staticmethod
    def char_full_to_half(s):
        s1 = ""
        for uchar in s:
            inside_code = ord(uchar)
            if inside_code == 0x3000:
                inside_code = 0x0020
            else:
                inside_code -= 0xfee0
            if inside_code < 0x0020 or inside_code > 0x7e: #转完之后不是半角字符返回原来的字符
                inside_code = uchar
            else:
                inside_code = chr(inside_code)
            s1 += inside_code
        return s1
    
    def generate_b30_image(self):

        base = Image.new("RGB", size=(3200, 2380), color=(255, 255, 255))

        draw = ImageDraw.Draw(base)

        self.b30_record.name = self.char_full_to_half(self.b30_record.name)
        font_name = ImageFont.truetype("./src/chunithm/font/XiaolaiSC-Regular.ttf", 90)
        font_content = ImageFont.truetype("./src/chunithm/font/AvenirNextCyr-Regular.ttf", 65)


        draw.text(xy=(50, 50), text=self.b30_record.name, fill="#000000", font=font_name)

        length = font_name.getlength(self.b30_record.name)

        draw.text((50+length, 75), text=f"/ Rating: {self.b30_record.rating_2dp}", font=font_content, fill="#000000")

        draw.text((50, 150), text=f"Best30: {self.b30_record.b30_2dp} / Recent10: {self.b30_record.r10_2dp}", font=font_content, fill="#000000")
        draw.text((50, 230), text=f"Max Rating: {self.b30_record.rating_max} / Reachable Rating: {self.b30_record.rating_reachable_4dp}", font=font_content, fill="#000000")
        draw.text((50, 310), text=f"Play Count: {self.b30_record.playCount} / Standard Deviation: {self.b30_record.standard_deviation} (Mean: {self.b30_record.std_mean})", font=font_content, fill="#000000")

        draw.line(((50, 400), (3150, 400)), fill="#000000", width=3)
        draw.line(((50, 1855), (3150, 1855)), fill="#000000", width=3)

        for count, song in enumerate(self.b30_record.best):
            pic = self.song_record_image(record=song, count=count+1)
            base.paste(pic, (50 + count % 5 * 620, 410 + count // 5 * 240))
        

        for count, song in enumerate(self.b30_record.recent):
            pic = self.song_record_image(record=song, count=count+1) if self.b30_record.enable_recent else self.song_record_not_avaliable()
            base.paste(pic, (50 + count % 5 * 620, 1860 + count // 5 * 240))

        draw.line(((50, 2103), (3150, 2103)), fill="#000000", width=3)

        for i in range(5):
            draw.line(((50, 653 + i * 240), (3150, 653 + i * 240)), fill="#cccccc", width=3)
        
        for i in range(4):
            draw.line(((673 + i * 620, 400), (673 + i * 620, 2340)), fill="#cccccc", width=3)
            draw.line(((673 + i * 620, 400), (673 + i * 620, 2340)), fill="#cccccc", width=3)

        base.save(f"./src/temp/res_{self.uid}.jpg")

        return f"[CQ:image,file=file:///{path}/src/temp/res_{self.uid}.jpg]"
        
    @staticmethod
    def song_record_image(record: ScoreItem, count: int) -> Image:
        color = {
            'Master': (187, 51, 238),
            'MAS': (187, 51, 238),
            'Expert': (238, 67, 102),
            'EXP': (238, 67, 102),
            'Advanced': (254, 170, 0),
            'ADV': (254, 170, 0),
            'Ultima': (0, 0, 0),
            'ULT': (0, 0, 0),
            'Basic': (102, 221, 17),
            'BAS': (102, 221, 17)
        }

        base = Image.new("RGBA", (620, 240), (255, 255, 255, 240))

        try:
            jacket = Image.open(f'./src/chunithm/image/{record.cid}.jpg').resize((186, 186))
        except FileNotFoundError:
            jacket = Image.new("RGB", (186, 186), (255, 255, 255))
        finally:
            base.paste(jacket, (32, 28))

        draw = ImageDraw.Draw(base)
        font = ImageFont.truetype('./src/chunithm/font/NotoSansHans-Regular-2.ttf', 37)

        max_index = 0

        size = font.getlength(record.title)
        while size > 345:
            max_index -= 1
            size = font.getlength(record.title[:max_index] + "..")

        draw.text((270, 38), record.title[:max_index].strip() + ".." if max_index else record.title, '#000000', font)

        font_2 = ImageFont.truetype('./src/chunithm/font/BAHNSCHRIFT.TTF', 58)
        draw.text((240, 107), str(record.score), '#000000', font_2)

        font_4 = ImageFont.truetype('./src/chunithm/font/BAHNSCHRIFT.TTF', 29)
        length = font_4.getlength(f"(#{count})")
        draw.text((610-length, 135), f"(#{count})", '#000000', font_4)

        font_3 = ImageFont.truetype('./src/chunithm/font/BAHNSCHRIFT.TTF', 42)
        if record.isAJ:
            draw.text((570-length, 135), "AJ", '#000000', font_4)
        elif record.isFC:
            draw.text((570-length, 135), "FC", '#000000', font_4)

        draw.rectangle((240, 27, 255, 87), fill=color[record.diff])

        draw.text((240, 181), f"Rating: {record.const} > {record.rating_2dp}", (0, 0, 0), font_3)
        length = font_3.getlength(f"Rating: {record.const} > {record.rating_2dp}")
        draw.text((242 + length, 190), str(record.rating_4dp)[-2:], (0, 0, 0), font_4)

        return base
    
    @staticmethod
    def song_record_not_avaliable() -> Image:

        base = Image.new("RGBA", (620, 240), (255, 255, 255, 240))

        font_2 = ImageFont.truetype('./src/chunithm/font/BAHNSCHRIFT.TTF', 60)

        length = font_2.getlength("NOT AVALIABLE")

        draw = ImageDraw.Draw(base)

        draw.text(xy=(310 - length / 2, 90), text="NOT AVALIABLE", fill=(150, 150, 150), font=font_2)

        return base