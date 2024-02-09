# import requests
# import bs4
# import json
# import sys

# bs = bs4.BeautifulSoup(requests.get('https://wiki.vg/index.php?title=Protocol&oldid=16681').text, 'html.parser')

# def chek(bsc: list):
#     if 'Packet ID' in bsc[0].text and 'State' in bsc[1].text and 'Bound To' in bsc[2].text: return True
#     else: False

# def form(value: str):
#     while True:
#         if value[0] == ' ' or value[0] == '\n': value = value[1:]
#         else: break
#     while True:
#         if value[-1] == ' ' or value[-1] == '\n': value = value[:-1]
#         else: break
#     return value


# # for bs2 in bs.find('div', class_='mw-parser-output'):
# #     print(bs2)

# names = iter(bs.find_all('h4'))
# save = [[], []]
# state_save = {}

# state = -1

# for table in bs.find_all('table', class_="wikitable"):
#     table: bs4.BeautifulSoup
#     heads = table.tbody.find_all('th')
#     values = table.tbody.find_all('td')
#     if chek(heads):
#         name = next(names)
#         p_id = 0
#         bound = 0

#         for i, v in enumerate(values):
#             if i == 0:
#                 p_id = int(form(v.text), 16)
#             elif i == 1:
#                 v = form(v.text)
#                 if state_save.get(v) is None:
#                     state_save[v] = True
#                     state += 1
#                     save[0].append({})
#                     save[1].append({})
#             elif i == 2:
#                 v = form(v.text)
#                 if v == 'Server':
#                     bound = 1
#                 elif v == 'Client':
#                     bound = 0
#                 else:
#                     raise Exception(f'{v}')

#                 break
#         n = form(name.text)
#         save[bound][state][n] = p_id
#         save[bound][state][p_id] = n
        
        
# print(save)
# with open('{}\\versions\\{}'.format(sys.__dict__['path'][0], '754.json'), 'w', encoding='utf-8') as file:
#     file.write(json.dumps(save))

class T:
    state = 0

class Data_packs(dict):
    def __init__(self, self2: T, dict_packs):
        self.dict_packs = dict_packs
        self.self2 = self2
        dict.__init__(self, dict_packs[self2.state])

    def state_apdate(self):
        self.clear()
        dict.__init__(self, self.dict_packs[self.self2.state])

d = Data_packs(T, [{1: 1}, {2: 2}, {3: 3}])
print(d)
T.state = 1
d.state_apdate()
print(d)

