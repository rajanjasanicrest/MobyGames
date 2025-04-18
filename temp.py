import json

with open('mobygames_platforms.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

updated_list = []


for console in data:
    print(console['link'])
    console_code = console['link'].split('/')[-2]
    console['console_code'] = console_code


with open('mobygames_platforms.json', 'w', encoding='utf-8') as f:
    data = json.dump( data, f, indent=4)