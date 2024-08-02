import requests
import json
from aiocqhttp.message import MessageSegment
import os
import Levenshtein as lev
from module.chunithm.utils import MusicDB, ChuApiError

path = os.getcwd()


class SearchSong():
    def __init__(self, keyword: str = ""):
        self.chunirec_token = "0c332b89f58298883d4a60d0c8704f5fa4126a0ec88c9bad76afa411eec4b8c2b9508641e9cdea73964b12bcb8b742fe46d1a72f0074354aa4708d4bcb7679c7"
        self.chunirec_search = f"https://api.chunirec.net/2.0/music/search.json?q={keyword}&region=jp2&token={self.chunirec_token}"
        self.keyword = keyword
        self.music_db: dict = json.load(
            fp=open(
                file="./module/chunithm/data/music_data.json",
                mode="r",
                encoding="utf-8"
            )
        )

    # 将匹配到的曲目转成消息类型发送, query例子: ["c982", "c2440"]
    def merge_match_to_message(self, query: list[str]) -> str:

        # 预处理query, 去掉所有匹配到是c0的歌
        query = [q for q in query if q != "c0"]


        match len(query):
            case 0:
                return "没有找到符合的曲目捏"
            # 当长度=1 (有一说一id也可以往这里传) / 其实有一说一还是很丑...
            case 1:
                # list[song_id] -> song_id
                query = query[0]
                # 获取当前曲目的信息 -> dict | None (None -> error)
                music_data = self.music_db.get(query)
                if not isinstance(music_data, dict):
                    raise ChuApiError("没有找到对应ID的曲目捏")
                # 定义一个空的字符串作为return的消息
                message = ""
                for line in [
                    f'{query}. {music_data["title"]}',
                    f'分类: {music_data["genre"]}',
                    f'曲师: {music_data["artist"]}',
                    f'更新版本: {music_data["version"]}',
                    f'更新日期: {music_data["updatedAt"]}',
                    f'BPM: {music_data["bpm"]}',
                    f'等级: {music_data["data"]["BAS"]["level"]}/{music_data["data"]["ADV"]["level"]}/{music_data["data"]["EXP"]["level"]}/{music_data["data"]["MAS"]["level"]}/{music_data["data"]["ULT"]["level"]}',
                    f'定数: {music_data["data"]["BAS"]["const"]}/{music_data["data"]["ADV"]["const"]}/{music_data["data"]["EXP"]["const"]}/{music_data["data"]["MAS"]["const"]}/{music_data["data"]["ULT"]["const"]}',
                    f'物量: {music_data["data"]["BAS"]["note"]["total"]}/{music_data["data"]["ADV"]["note"]["total"]}/{music_data["data"]["EXP"]["note"]["total"]}/{music_data["data"]["MAS"]["note"]["total"]}/{music_data["data"]["ULT"]["note"]["total"]}'
                ]:
                    # 主要针对最后两行, 如果没有ULTIMA难度的数据就把最后面的/去掉
                    message += line.rstrip("0.0").rstrip("/") + "\n"
                return message + MessageSegment.image(file=f"file:///{path}/src/chunithm/image/{query}.jpg")
            case _:
                message = ""
                for song_id in query:
                    message += f"{song_id}. {self.music_db[song_id]['title']}\n"
                return message[:-1]

    def search_by_keywords(self) -> list[str] | str:
        """
        从指令中获取需要查询的keyword -> 返回一个全是id的列表 | 报错提醒

        调用方式:
        query = SearchSong(keyword="江江").search_by_keywords()
        if isinstance(query, str):
            return query
        return SearchSong().merge_match_to_message(query=query)

        (or)

        return SearchSong().merge_match_to_message(query=query) if not isinstance(query, str) else query
        """

        music_alias: dict = json.load(
            fp=open(
                file="./module/chunithm/data/alias.json",
                mode="r",
                encoding="utf-8"
            )
        )

        def calc_similar(s1, s2) -> float:  # 封装一个calc_similar 计算匹配度
            return 1 - (lev.distance(s1, s2) / max(len(s1), len(s2)))

        def local_match(cutoff: tuple[float]) -> list[str]:
            # 1. 直接匹配曲名, cutoff=0.6 / 0.3
            result = []

            # for循环一遍 分别获取每一首歌的song_id和title
            for song_id, title in [(song_id, self.music_db[song_id]["title"]) for song_id in self.music_db]:
                # 先储存similar -> 匹配度, 然后判断是不是大于cutoff (1 / 0.6 / 0.3) True -> 加进去result里面
                if (similar := calc_similar(self.keyword.lower(), title.lower())) >= cutoff[0]:
                    result.append((song_id, similar))

            # sorting list by similar
            result = sorted(result, key=lambda x: x[1], reverse=True)

            if result:
                result = [x[0] for x in result]
                return result if cutoff[0] == 1 else result[:5]

            # 2. 匹配别名, cutoff=0.75 / 0.3

            # for循环一遍 分别获取每一首歌的song_id和所有别名
            for song_id, song_alias in [(song_id, music_alias[song_id]) for song_id in music_alias if music_alias[song_id]]:
                # 储存similar -> 匹配度, 然后对每一个别名做比较 + 取所有匹配度的最大值放进similar里面 / 判断是不是大于cutoff (1 / 0.75 / 0.3) True -> 加进去result里面
                if (similar := max([calc_similar(self.keyword.lower(), alias.lower()) for alias in song_alias])) >= cutoff[1]:
                    result.append((song_id, similar))

            # 无论有没有都加进去
            result = [x[0] for x in sorted(result, key=lambda x: x[1], reverse=True)]
            return result if cutoff[1] == 1 else result[:5]

        result = local_match((1, 1))

        if result:
            return result
    

        # 3. 字首匹配
        # 创建query = [] 作为临时存放准备
        query: list[tuple] = []

        # 分别获取每一个song_id
        for song_id in self.music_db:
            # for x in self.music_db[song_id]["title"].split(" ") -> 按空格split开
            # x[0] for x 取每个空格的字首 -> join => title_abbr
            title_abbr = "".join(
                [x[0] for x in self.music_db[song_id]["title"].split(" ")])
            # append到query里面等待一个一个查询
            query.append((song_id, title_abbr))

        # 分别获取query中的每一个元素 -> unpack成song_id和title_abbr
        for song_id, title_abbr in query:
            # 判断是不是相等
            if self.keyword.lower() == title_abbr.lower():
                result.append(song_id)

        if result:
            return result

        # 4. 丢去chunirec匹配, 进行一次try, 如果爆了返回TimeoutError
        try:
            response = requests.get(self.chunirec_search, timeout=15)
        except TimeoutError as e:
            return f"[ERROR] {e}"

        response = response.json()  # 将chunirec返回的数据转为dict

        # 可读性一坨, 总体就是将所有在chunirec匹配上的歌, 找到返回的title转回id -> cid (str)
        result.extend(
            [f'c{MusicDB().match_songname(song["title"])}' for song in response]
        )

        if result:
            return result
        
        result.extend(local_match((0.6, 0.65)))

        if result:
            return result

        result.extend(local_match((0.3, 2)))

        return result

    def search_alias(self, keyword: str):
        song_id: list = [keyword] if (keyword[1:].isdigit() and keyword[0] == "c") else SearchSong(keyword=keyword).search_by_keywords()

        music_alias: dict = json.load(
            fp=open(
                file="./module/chunithm/data/alias.json",
                mode="r",
                encoding="utf-8"
            )
        )

        match len(song_id):
            case 0:
                return "没有找到符合关键词的曲目捏"
            case 1:
                # list[song_id] -> song_id
                song_id: str = song_id[0]
                return f"{song_id}. {self.music_db[song_id]['title']}的别名:\n" + ", ".join(music_alias[song_id]) if music_alias.get(song_id, []) else "此曲目没有别名捏"
            case _:
                # More than one song is matched -> Further search
                return "匹配到了多个曲目\n请使用/chu alias [你需要的曲目ID]进行查询\n" + self.merge_match_to_message(song_id)

class UpdateAlias:
    def __init__(self) -> None:
        self.music_alias_fp = open(
            file="./module/chunithm/data/alias.json",
            mode="r",
            encoding="utf-8"
        )
    
    # update song alias
    def update(self, new_alias: str, target_song: str) -> str:
        # remove spaces at the end / start of string
        new_alias, target_song = new_alias.strip(), target_song.strip()
        # get target_list first
        target_list = [target_song] if target_song[0] == "c" and target_song[1:].isdigit() else SearchSong(keyword=target_song).search_by_keywords()

        # if len(new_alias) > 13:
        #     return "别名长度过大, 故无法添加"

        match len(target_list):
            case 0:
                return "没有找到有目标别名的曲目, 故无法添加新的别名捏"
            case 1:
                if target_list[0] in (music_alias := json.load(self.music_alias_fp)):
                    if new_alias in music_alias[target_list[0]]:
                        return "该别名已经被添加过了捏"
                    else:
                        music_alias[target_list[0]].append(new_alias)
                else:
                    music_alias[target_list[0]] = [new_alias]
                with open(file="./module/chunithm/data/alias.json", mode="w", encoding="utf-8") as fp:
                    json.dump(obj=music_alias, fp=fp, indent=4, ensure_ascii=False)
                    return f"添加成功!\n{new_alias} -> {target_list[0]}"
            case _:
                return "匹配到了多个曲目\n请使用/chu add [新添加的别名] into [需要的id] 进行添加捏\n" + SearchSong().merge_match_to_message(query=target_list)
    
    # delete song alias
    def delete(self, del_alias: str, target_song: str) -> str:
        # remove spaces at the end / start of string
        del_alias, target_song = del_alias.strip(), target_song.strip()

        target_list = [target_song] if target_song[0] == "c" and target_song[1:].isdigit() else SearchSong(keyword=target_song).search_by_keywords()

        match len(target_list):
            case 0:
                return "没有找到有目标别名的曲目, 故无法添加新的别名捏"
            case 1:
                if target_list[0] in (music_alias := json.load(self.music_alias_fp)):
                    if del_alias in music_alias[target_list[0]]:
                        music_alias[target_list[0]].remove(del_alias)
                        with open(file="./module/chunithm/data/alias.json", mode="w", encoding="utf-8") as fp:
                            json.dump(obj=music_alias, fp=fp, indent=4, ensure_ascii=False)
                            return f"删除别名成功!\n'{del_alias}' is deleted from {target_list[0]}"
                return "没有对应的别名可删除哦"
            case _:
                return "匹配到了多个曲目\n请使用/chu delete [需要删除的别名] from [需要的id] 进行添加捏\n" + SearchSong().merge_match_to_message(query=target_list)