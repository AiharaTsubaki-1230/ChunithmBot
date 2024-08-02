import csv
import json

def update():
    count = 0
    chuni_alias = json.loads(open("./module/chunithm/data/chuni_alias.json").read())
    with open("./test/中二节奏别名添加收集表格-Sheet1.csv", "r") as f:
        for row in list(csv.reader(f))[1:]:
            isNewAlias = False
            id = "c" + row[0]
            alias = []
            for col in row[2:]:
                if col != "":
                    isNewAlias = True
                    alias.append(col)
            if isNewAlias:
                if chuni_alias.get(id) == None: 
                    chuni_alias[id] = []
                for a in alias:
                    if a not in chuni_alias[id]:
                        chuni_alias[id].append(a)
                        count += 1

    open("./module/chunithm/data/chuni_alias.json", "w").write(json.dumps(chuni_alias))
    return f"一共更新了{count}个别名"