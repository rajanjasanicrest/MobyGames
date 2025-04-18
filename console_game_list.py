import json, re, os, time
from get_agents import get_agent
from playwright.sync_api import sync_playwright

# If Console has data less then 1000

if __name__ == '__main__':

    with open("mobygames_platforms.json", "r", encoding="utf-8") as file:
        platforms = json.load(file)

    with sync_playwright() as p:
        print('Opening Browser...')
        browser = p.chromium.launch(
            headless=False
        )

        print('Browser opened.')
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent=get_agent(),
        )
        context.add_cookies([
            {
                "name": "remember-www",
                "value": "login-v2-1114323-1100295|ce4be64d911bef101abeedc6ee2b1b0bef83b8c30ea51ceecb325c9bcc3e21a78bd85f68ad2f804e88890f10d2ab2ed18884dbee93139e7dac02af086c673227",
                "domain": ".mobygames.com",
                "path": "/",
                "max_age": 30 * 24 * 60 * 60
            }
        ])

        page = context.new_page()
        for platform in platforms:
            
            if platform['console_code'] in ['atari-2600']:

                games_list = []
                i = 0
                is_valid_page = True
                while is_valid_page:
                    print(f"Scraping page {i} for {platform['console_code']}...")
                    page.goto(f"https://www.mobygames.com{platform['link']}page:{i}/", wait_until='domcontentloaded')
                    games = page.query_selector_all("tbody tr")
                    
                    next_link = page.query_selector('a:has-text("Next")')
                    if not next_link:
                        is_valid_page = False
                    if games:
                        for game in games:
                            game_name = game.query_selector('td a').inner_text()
                            game_link = game.query_selector('td a').get_attribute('href')
                            games_list.append(
                                {
                                    'game': game_name,
                                    'link': game_link,
                                    'game_code': game_link.strip('/').split('/')[-1]
                                }
                            )
                    i += 1

                if not os.path.exists('games_list'):
                    os.makedirs('games_list')
                
                with open(f"games_list/{platform['console_code']}.json", "w", encoding="utf-8") as file:
                    json.dump(games_list, file, indent=4)