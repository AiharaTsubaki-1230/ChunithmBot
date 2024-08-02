import requests
from module.chunithm.utils import Record, ScoreItem, CustomCookiePolicy, ChuApiError, AimeDB, FetchData, ExcelUpsert, music_db, music_db_lmn
from bs4 import BeautifulSoup
from lxml import html
from decimal import Decimal
import os


path = os.getcwd()

def parse_b30_record(
    segaid: str | tuple, 
    server: str, 
    uid: int) -> Record | None:
        match server:
            case "" | "lmnp":
                if not isinstance(segaid, tuple):
                    raise ChuApiError("发生错误，可能是绑定有问题 / bot自己的问题")
                
                # check const version
                ver = "lmnp" if server else "lmn"

                # login
                account, password = segaid
                login_url = 'https://lng-tgk-aime-gw.am-all.net/common_auth/login?site_id=chuniex&redirect_url=https://chunithm-net-eng.com/mobile/&back_url=https://chunithm.sega.com/'
                response_login = requests.get(url=login_url, timeout=15)
                cookies_login = response_login.headers['Set-Cookie']

                # 尝试登录 + 重新定向到chunithm-net网站
                login_page = 'https://lng-tgk-aime-gw.am-all.net/common_auth/login/sid/'
                response_redirect = requests.post(login_page, headers={'cookie': cookies_login}, data={
                    'retention': 1, 'sid': account, 'password': password}, allow_redirects=False, timeout=15)
                redirect_page = response_redirect.headers['location']
                cookies_redirect = response_redirect.cookies

                response = requests.get(redirect_page, cookies=cookies_redirect, allow_redirects=False, timeout=15) # 获取cookies
                # 如果"_t"不在cookies内 -> 登录失败，或许是账号/密码错误
                cookies = response.cookies
                if '_t' not in cookies:
                    raise ChuApiError("Account or Password is invalid. Please Try Again.")

                # 登录的Home界面 => 获取userinfo相关
                response = requests.get("https://chunithm-net-eng.com/mobile/home/playerData/", cookies=cookies, timeout=15)
                player_data = response.text

                soup_all = BeautifulSoup(player_data, 'html.parser')
                soup = soup_all.find(id="inner").find("div", {"class": "player_data_right"})

                # 创建record对象, 直接存放数据
                # 获取player_name, max_rating, play_count, 统一直接放在里面
                b30_record = Record(
                    name=soup.find("div", {"class": "player_name"}).find_all("div")[1].string,
                    playCount=int(soup_all.find(id="inner").find("div", {"class": "user_data_play_count"}).div.string.replace(",", ""))
                )

                b30_record.rating_max = Decimal(soup.find("div", {"class": "player_rating_max"}).string).quantize(Decimal("0.00"))

                # 进入获取player_b30
                response = requests.get("https://chunithm-net-eng.com/mobile/record/musicGenre", cookies=cookies, timeout=15)

                session = requests.Session()

                for diff in ["Basic", "Advanced", "Expert", "Master", "Ultima"]:
                    response = session.post(
                            url="https://chunithm-net-eng.com/mobile/record/musicGenre/send" + diff,
                            data={
                                "genre": "99",
                                "token": cookies["_t"]
                            },
                            cookies=cookies, 
                            timeout=15
                        )
                        
                    # parsing b30 html
                    soup = BeautifulSoup(response.text, "html.parser")

                    soup = soup.find(id="inner").find("div", {"class": "frame01 w460"}).find("div", {"class": "frame01_inside"}).find_all("div", {"class": "box01 w420"})

                    # b30部分
                    # TODO: 注释呢！！！！我急了！！！！
                    for genre in soup:
                        songs = genre.find_all("form")
                        for song in songs:
                            inputs = song.div.find_all("input")
                            song_score = song.div.find("div", {"class": "play_musicdata_highscore"})
                            song_clearfix = song.div.find("div", {"class": "play_musicdata_icon clearfix"})
                            b30_record.best.append(
                                ScoreItem(
                                    score=int(song_score.span.string.replace(",", "")) if song_score else 0,
                                    diff={"0": "BAS", "1": "ADV", "2": "EXP", "3": "MAS", "4": "ULT"}[inputs[2]["value"]],
                                    id=int(inputs[0]["value"]),
                                    isFC=song_clearfix.find("img", {"src": "https://chunithm-net-eng.com/mobile/images/icon_fullcombo.png"}) != None if song_clearfix else False,
                                    isAJ=song_clearfix.find("img", {"src": "https://chunithm-net-eng.com/mobile/images/icon_alljustice.png"}) != None if song_clearfix else False
                                )
                            )


                # r10部分
                response_recent = requests.get(
                    url="https://chunithm-net-eng.com/mobile/home/playerData/ratingDetailRecent/", 
                    cookies=cookies, 
                    timeout=15
                )

                content = response_recent.text
                soup = BeautifulSoup(content, 'html.parser')
                soup_form = soup.find(id="inner").find("div", {"class": "box05 w400"}).find_all("form")

                for soup_best in soup_form:
                    data_div = soup_best.div.find_all("div")
                    data_input = soup_best.div.find_all("input")
                    b30_record.recent.append(
                            ScoreItem(
                                score=int(data_div[1].span.string.replace(",","")),
                                diff={"0": "BAS", "1": "ADV", "2": "EXP", "3": "MAS", "4": "ULT"}[data_input[0]["value"]],
                                id=int(data_input[2]["value"])
                            )
                        )
                
                return b30_record.change_const_by_version(ver=ver)
            case "en" | "enlmnp" | "en lmnp":
                # check const version
                ver = "lmn" if server == "en" else "lmnp"

                # login
                login_url = 'https://lng-tgk-aime-gw.am-all.net/common_auth/login?site_id=chuniex&redirect_url=https://chunithm-net-eng.com/mobile/&back_url=https://chunithm.sega.com/'
                response_login = requests.get(login_url, timeout=15)
                cookies_login = response_login.headers['Set-Cookie']

                # 尝试登录 + 重新定向到chunithm-net网站
                login_page = 'https://lng-tgk-aime-gw.am-all.net/common_auth/login/sid/'
                response_redirect = requests.post(login_page, headers={'cookie': cookies_login}, data={
                    'retention': 1, 'sid': "acekuro0219", 'password': "gzycTaffyxxm0915"}, allow_redirects=False, timeout=15)
                redirect_page = response_redirect.headers['location']
                cookies_redirect = response_redirect.cookies


                response = requests.get(redirect_page, cookies=cookies_redirect, allow_redirects=False, timeout=15) # 获取cookies
                    
                # 如果"_t"不在cookies内 -> 登录失败，或许是账号/密码错误
                cookies = response.cookies
                if '_t' not in cookies:
                    return "Error: Account or Password is invalid. Please Try Again."
                
                # 设置session & session的cookies
                session = requests.Session()
                session.cookies.update({"userId": cookies["userId"], "_t": cookies["_t"]})
                session.cookies.set_policy(CustomCookiePolicy())

                # Step 1: 获取好友列表
                response = session.get(
                    url="https://chunithm-net-eng.com/mobile/friend/", 
                    timeout=15
                )

                friend_list = html.fromstring(response.content).xpath(
                    '//div[@class="friend_block"]//div[@class="player_name"]//input[@name="idx"]/@value'
                )

                # Step 2: 检测在不在好友列表, 否则添加好友
                segaid = segaid[0]
                if segaid not in friend_list:
                    response = session.post(
                        url="https://chunithm-net-eng.com/mobile/friend/search/sendInvite/", 
                        data={
                            "idx": segaid, 
                            "token": session.cookies["_t"]
                            }, 
                        timeout=15
                    )
                    if error_msg := html.fromstring(response.content).xpath('//div[@class="block text_l"]/p[2]/text()') and error_msg[0] == "Invalid access.":
                        raise ChuApiError("Invalid Friend Code")
                    raise ChuApiError("Not a friend, friend request is sent")

                
                # Step 3: Register favourite friend
                session.post(
                    url="https://chunithm-net-eng.com/mobile/friend/favoriteOn/", 
                    data={
                        "idx": segaid, 
                        "token": session.cookies["_t"]
                        }, 
                    timeout=15
                )

                # Step 4: Get player best from battle

                # 先创建一个曲名转id的临时字典
                # TODO: Change to music_db from music_db_lmn after lmn+ in intl ver
                db_for_title_to_id = {music_db_lmn[key]["title"]: int(key[1:]) for key in music_db_lmn}

                b30_record = Record(enable_recent=False)

                for i in range(5):
                    response = session.post(
                        url="https://chunithm-net-eng.com/mobile/friend/genreVs/sendBattleStart/",
                        data={
                            "genre": "99",
                            "friend": segaid,
                            "radio_diff": str(i),
                            "token": cookies["_t"],
                        },
                    )

                    tree = html.fromstring(response.text)

                    b30_record.name = tree.xpath('//*[@id="inner"]/div[3]/div[2]/div[3]/form/div[1]/select[2]/option/text()')[0]

                    music_boxes = tree.xpath('//div[contains(@class, "music_box")]')

                    if not music_boxes:
                        raise ChuApiError("No songs available.")
                    
                    for music_box in music_boxes:
                        score = music_box.xpath(
                            './/div[@class="vs_list_infoblock"][2]/div[1]/text()'
                        )[0]
                        title = music_box.xpath(
                            './/div[@class="block_underline text_b text_c"]/div[1]/text()'
                        )[0]
                        fcaj_img = music_box.xpath(
                            './/div[@class="vs_list_infoblock"][2]/div[2]/img/@src'
                        )
                        fcaj_img = fcaj_img[0] if fcaj_img else ""
                        isAJ = "icon_alljustice" in fcaj_img
                        isFC = "icon_fullcombo" in fcaj_img or isAJ

                        score = int(score.replace(",", ""))

                        b30_record.best.append(
                            ScoreItem(
                                score=score,
                                diff=["BAS", "ADV", "EXP", "MAS", "ULT"][i], 
                                id=db_for_title_to_id[title],
                                title=title,
                                isAJ=isAJ, 
                                isFC=isFC
                            )
                        )
                
                # Add Recent to b30_record (but score=0)
                b30_record.recent = [ScoreItem(id=999, score=0, diff="MAS")] * 10
                
                # Step 5: Cancel registering favourite friend
                session.post(
                    url="https://chunithm-net-eng.com/mobile/friend/favoriteOff/", 
                    data={"idx": segaid, "token": session.cookies["_t"]}, 
                    timeout=15
                )

                return b30_record.change_const_by_version(ver=ver)
            case "cn":
                # 检测segaid的变量类型是不是正确（虽然没什么必要（后续：事实上确实没有必要
                # assert isinstance(segaid, (str, None)), "发生错误，可能是bot自己的问题"

                # 如果segaid = None -> 没绑定，则使用QQ号查询B30
                segaid = segaid[0] if isinstance(segaid, tuple) else segaid

                post_json: dict = {"username": segaid} if segaid else {"qq": str(uid)}

                # 发送请求去水鱼进行查分
                response: dict = requests.post(
                                url="https://www.diving-fish.com/api/chunithmprober/query/player", 
                                json=post_json, 
                                timeout=15
                            ).json()
                
                # 如果返回了错误message则直接返回报错message
                if error := response.get("message"):
                    raise ChuApiError(error)
                    

                # 创建Record物件
                b30_record = Record(
                    name=response["nickname"],
                )

                # 填入Best30数据
                for record in response["records"]["b30"]:
                    b30_record.best.append(
                        ScoreItem(
                                id=record["mid"], 
                                score=record["score"],
                                diff=["BAS", "ADV", "EXP", "MAS", "ULT"][record["level_index"]],
                                isAJ=record["fc"] == "alljustice", 
                                isFC=record["fc"] == "fullcombo",
                            )
                    )
                
                # 填入Recent10数据
                for record in response["records"]["r10"]:
                    b30_record.recent.append(
                        ScoreItem(
                                id=record["mid"], 
                                score=record["score"],
                                diff=["BAS", "ADV", "EXP", "MAS", "ULT"][record["level_index"]],
                                isAJ=record["fc"] == "alljustice", 
                                isFC=record["fc"] == "fullcombo",
                            )
                    )
                
                return b30_record.change_const_by_version(ver="cn")
            case "louis" | "louis lmnp" | "louislmnp":

                # 检查定数版本
                ver = "lmnp" if server != "louis" else "cn"

                # 如果segaid = None -> 没绑定，则使用QQ号查询B30

                segaid = segaid[0] if isinstance(segaid, tuple) else segaid

                post_json: dict = {"username": segaid} if segaid else {"qq": str(uid)}

                # User Info: 发送请求
                response: dict = requests.post(
                                    url="http://43.139.107.206:8083/api/chunithm/user_info", 
                                    json=post_json, 
                                    timeout=15
                                ).json()
                
                # 如果返回了错误message则直接返回报错message
                if error := response.get("message"):
                    raise ChuApiError(error)

    

                # 创建Record物件
                b30_record = Record(
                    name=response["nickname"],
                    playCount=response["playCount"]
                )

                b30_record.rating_max = Decimal(response["maxRating"]).quantize(Decimal("0.00"))

                # Best: 发送请求
                response: dict = requests.post(
                                    url="http://43.139.107.206:8083/api/chunithm/filtered_info", 
                                    json=post_json, 
                                    timeout=15
                                ).json()

                # 填入Best30数据
                for record in response:
                    b30_record.best.append(
                        ScoreItem(
                                id=int(record["idx"]), 
                                score=record["highscore"],
                                diff=["BAS", "ADV", "EXP", "MAS", "ULT"][record["level_index"]],
                                isAJ=record["full_combo"] == "alljustice", 
                                isFC=record["full_combo"] == "fullcombo",
                            )
                    )
                
                # Recent10: 发送请求 
                response: dict = requests.post(
                                    url="http://43.139.107.206:8083/api/chunithm/basic_info", 
                                    json=post_json, 
                                    timeout=15
                                ).json()

                # 填入Recent10数据
                for record in response["records"]["r10"]:
                    b30_record.recent.append(
                        ScoreItem(
                                id=record["mid"], 
                                score=record["score"],
                                diff=["BAS", "ADV", "EXP", "MAS", "ULT"][record["level_index"]],
                                isAJ=record["fc"] == "alljustice", 
                                isFC=record["fc"] == "fullcombo",
                            )
                    )
                
                return b30_record.change_const_by_version(ver=ver)
                
            case "jp":
                token = "0c332b89f58298883d4a60d0c8704f5fa4126a0ec88c9bad76afa411eec4b8c2b9508641e9cdea73964b12bcb8b742fe46d1a72f0074354aa4708d4bcb7679c7"

                segaid = segaid[0]
                
                # 对chunirec数据做请求
                response_profile = requests.get(
                                        url=f"https://api.chunirec.net/2.0/records/profile.json?user_name={segaid}&region=jp2&token={token}", 
                                        timeout=15
                                    )
                response_record = requests.get(
                                        url=f"https://api.chunirec.net/2.0/records/rating_data.json?user_name={segaid}&region=jp2&token={token}", 
                                        timeout=15
                                    )
                response_best_entries = requests.get(
                                            url=f"https://api.chunirec.net/2.0/records/showall.json?user_name={segaid}&region=jp2&token={token}",
                                            timeout=15
                                        ) 
                
                # 如果status code = 200, 就返回报错
                if (response_profile.status_code, response_record.status_code, response_best_entries.status_code) != (200, 200, 200):
                    raise ChuApiError(f"Status Code is not = 200")
                
                # 把获取到的数据转成json
                profile = response_profile.json()
                record = response_record.json()
                best_entries = response_best_entries.json()

                # 创建Record对象
                b30_record = Record(
                    name=profile["player_name"]
                )

                # 填入rating_max
                b30_record.rating_max = Decimal(profile["rating_max"]).quantize(Decimal("0.00"))

                # 先创建一个曲名转id的临时字典
                db_for_title_to_id = {music_db[key]["title"]: int(key[1:]) for key in music_db}

                # fill in b30
                for entry in list(filter(None, best_entries["records"])):
                    b30_record.best.append(
                        ScoreItem(
                            score=entry["score"],
                            id=db_for_title_to_id[entry["title"]],
                            diff=entry["diff"],
                            isFC=entry["is_fullcombo"],
                            isAJ=entry["is_alljustice"]
                        )
                    )

                # fill in r10
                for entry in list(filter(None, record["recent"]["entries"])):
                    b30_record.recent.append(
                        ScoreItem(
                            score=entry["score"],
                            id=db_for_title_to_id[entry["title"]],
                            diff=entry["diff"]
                        )
                    )

                return b30_record
            case "aqua" | "rin" | "na" | "aqua lmnp" | "rin lmnp" | "na lmnp" | "aqualmnp" | "rinlmnp" | "nalmnp":
                # 定数版本检测
                ver = "jp" if server.endswith("lmnp") else "lmn"
                server = server.replace("lmnp", "").strip()

                # 获取user_id
                user_id = AimeDB(access_code=segaid[0], server=server).user_id

                # 获取user info
                user_info = FetchData(server=server).requests_to_url(user_id=user_id, root="GetUserDataApi/")

                # create Record object
                b30_record = Record(
                    name=user_info["userData"]["userName"],
                    playCount=user_info["userData"]["playCount"]
                )
                
                # fill best30
                best_entries = FetchData(server=server).requests_to_url(user_id=user_id, root="GetUserMusicApi/")
                for entries in best_entries["userMusicList"]:
                    for diff in entries["userMusicDetailList"]:
                        try:
                            if 0 <= int(diff["level"]) <= 4 and int(diff["musicId"]) < 3000:
                                b30_record.best.append(
                                    ScoreItem(
                                        score=int(diff["scoreMax"]),
                                        diff=["BAS", "ADV", "EXP", "MAS", "ULT"][int(diff["level"])],
                                        id=diff["musicId"],
                                        isAJ=diff["isAllJustice"] == "true",
                                        isFC=diff["isFullCombo"] == "true"
                                    )
                                )
                        except KeyError:
                            pass
                
                # fill recent10
                for entries in FetchData(server=server).requests_to_url(user_id=user_id, root="GetUserRecentRatingApi/")["userRecentRatingList"]:
                    try:
                        if not 0 >= int(diff["level"]) >= 4:
                            b30_record.recent.append(
                                    ScoreItem(
                                        score=int(entries["score"]),
                                        diff=["BAS", "ADV", "EXP", "MAS", "ULT"][int(entries["difficultId"])],
                                        id=entries["musicId"]
                                    )
                                )
                    except KeyError:
                        pass
                
                return b30_record.change_const_by_version(ver=ver)

            case "csv" | "csvlmnp" | "csv lmnp":
                # check const version
                ver = "lmn" if server == "csv" else "jp"

                # get entries from .csv file
                entries = ExcelUpsert(uid=uid, isrecent=False).read_excel()

                # create Record object
                b30_record = Record(name=entries[0][0], playCount=int(entries[0][1]))

                # insert best entries into b30_record
                for entry in entries[1:]:
                    b30_record.best.append(
                        ScoreItem(
                            id=int(entry[0][1:]),
                            score=int(entry[2]),
                            diff=entry[3],
                            isFC=entry[4] == "FC",
                            isAJ=entry[4] == "AJ"
                        )
                    )
                
                
                # get entries from .csv file, recent
                entries = ExcelUpsert(uid=uid, isrecent=True).read_excel()

                b30_record = b30_record.sort_all_entries()

                if entries: # if return recent from .csv file
                    for entry in entries:
                        b30_record.recent.append(
                            ScoreItem(
                                id=int(entry[0][1:]),
                                score=int(entry[2]),
                                diff=entry[3],
                                isFC=entry[4] == "FC",
                                isAJ=entry[4] == "AJ"
                            )
                        )
                else: # no entry from .csv file
                    b30_record.recent = [b30_record.best[0]] * 10
                    b30_record.enable_recent = False
                
                return b30_record.change_const_by_version(ver=ver)
            
            case "max" | "maxcn" | "max cn":

                return Record(name="MaxScore").change_const_by_version(ver="jp" if server == "max" else "cn").fill_zero_record(ver="jp" if server == "max" else "cn", score=1010000).sort().fill_recent_record()

            case _:
                return ""