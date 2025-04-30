import json, re, os, time
from get_agents import get_agent
from playwright.sync_api import sync_playwright

# if games are more than 10000

def handle_pagination_and_get_games_list(url, games_dedup, console, genre=None, alphabet=None):

    i = 0
    is_valid_page = True
    games_dedup
    games_list = []
    while is_valid_page and i < 21 :

        if 'title:' in url:
            alphabet = url.split('title:')[-1].split('/')[0]
            print(f"Scraping page {i} for {platform['console_code']}, genre {genre}..., for alphabet {alphabet}")
        else:
            print(f"Scraping page {i} for {platform['console_code']}, genre {genre}...")
        page.goto(f'{url}/page:{i}/', wait_until='domcontentloaded', timeout=60000)
        
        games = page.query_selector_all("tbody tr")
        
        next_link = page.query_selector('a:has-text("Next")')
        if not next_link:
            is_valid_page = False
        if games:
            for game in games:
                game_name = game.query_selector('td a').inner_text()
                game_link = game.query_selector('td a').get_attribute('href')
                if game_link not in games_dedup:
                    games_list.append(
                        {
                            'game': game_name,
                            'link': game_link,
                            'game_code': game_link.strip('/').split('/')[-1]
                        }
                    )
                    games_dedup.append(game_link)

        i += 1

    return games_list, games_dedup



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
            },
            {
                "name": "showIcons",
                "value": "false",
                "domain": ".mobygames.com",
                "path": "/",
                "max_age": 30 * 24 * 60 * 60
            },
            {
                "name": "perPage",
                "value": "50",
                "domain": ".mobygames.com",
                "path": "/",
                "max_age": 30 * 24 * 60 * 60
            }
        ])

        with open('genres.json', 'r', encoding='utf-8') as file:
            genres_list = json.load(file)

        page = context.new_page()
        for platform in platforms:
            # if platform['console_code'] in ['nes', '3ds', 'nintendo-ds', 'msx']:
            if platform['console_code'] in ["pc98"]:
                games_dedup=[]
                games_list = []

                try:
                    with open(f'games_list/{platform['console_code']}.json', 'r', encoding='utf-8') as file:
                        games_list = json.load(file)
                        games_dedup = [game['link'] for game in games_list]
                except Exception as e:
                    print(e)

                print(f'getting list of years for platform {platform['platform']}')
                page.goto(f"https://www.mobygames.com{platform['link']}", wait_until='domcontentloaded', timeout=210000)
                year_links = []
                year_links = page.query_selector_all("a[href*='year']")

                year_data = [
                    year_link.get_attribute("href").split("year:")[-1].split("/")[0]
                    for year_link in year_links
                ]
                print('got year list', year_data)
                page.goto(f"https://www.mobygames.com/game/platform:{platform['console_code']}/", wait_until='domcontentloaded', timeout=120000)

                results_element = page.query_selector('p.no-select.text-muted')
                if not results_element:
                    games_fetched, duped_fetch = handle_pagination_and_get_games_list(f"https://www.mobygames.com/game/platform:{platform['console_code']}/", games_dedup, platform['console_code'], genre_code)
                    games_list.extend(games_fetched)
                    games_dedup = duped_fetch
                    with open(f"games_list/{platform['console_code']}.json", "w", encoding="utf-8") as file:
                        json.dump(games_list, file, indent=4)
                else:
                    results_text = results_element.inner_text()                        
                    results_count = int(results_text.split('results')[0].strip().replace(',', '').split()[-1])
                    
                    # if less than 1000 get list and move on
                    if results_count <= 1000:
                        games_fetched, duped_fetch = handle_pagination_and_get_games_list(f"https://www.mobygames.com/game/platform:{platform['console_code']}/sort:title/", games_dedup, platform['console_code'], genre_code)
                        games_list.extend(games_fetched)
                        games_dedup = duped_fetch
                        with open(f"games_list/{platform['console_code']}.json", "w", encoding="utf-8") as file:
                            json.dump(games_list, file, indent=4)

                    elif results_count <= 2000:
                        games_fetched, duped_fetch = handle_pagination_and_get_games_list(f"https://www.mobygames.com/game/platform:{platform['console_code']}/sort:title", games_dedup, platform['console_code'])
                        games_list.extend(games_fetched)
                        games_dedup = duped_fetch
                        games_fetched, duped_fetch = handle_pagination_and_get_games_list(f"https://www.mobygames.com/game/platform:{platform['console_code']}/sort:-title", games_dedup, platform['console_code'])
                        games_list.extend(games_fetched)
                        games_dedup = duped_fetch
                        with open(f"games_list/{platform['console_code']}.json", "w", encoding="utf-8") as file:
                            json.dump(games_list, file, indent=4)

                    elif results_count <= 10000:
                        for year in year_data:
                            print(f'scrapping for year {year}')
                            page.goto(f"https://www.mobygames.com/game/from:{year}/platform:{platform['console_code']}/until:{year}/sort:title/", wait_until='domcontentloaded', timeout=60000)
                            results_element = page.query_selector('p.no-select.text-muted')
                            if results_element:
                                results_text = results_element.inner_text()                        
                                results_count = int(results_text.split('results')[0].strip().replace(',', '').split()[-1])
                                print(f'result count is {results_count} for year {year}')
                                # if less than 1000 get list and move on
                                if results_count <= 1000:
                                    games_fetched, duped_fetch = handle_pagination_and_get_games_list(f"https://www.mobygames.com/game/from:{year}/platform:{platform['console_code']}/until:{year}/sort:title", games_dedup, platform['console_code'])
                                    games_list.extend(games_fetched)
                                    games_dedup = duped_fetch
                                    with open(f"games_list/{platform['console_code']}.json", "w", encoding="utf-8") as file:
                                        json.dump(games_list, file, indent=4)
                                elif results_count <= 2000:
                                    games_fetched, duped_fetch = handle_pagination_and_get_games_list(f"https://www.mobygames.com/game/from:{year}/platform:{platform['console_code']}/until:{year}/sort:title", games_dedup, platform['console_code'])
                                    games_list.extend(games_fetched)
                                    games_dedup = duped_fetch
                                    games_fetched, duped_fetch = handle_pagination_and_get_games_list(f"https://www.mobygames.com/game/from:{year}/platform:{platform['console_code']}/until:{year}/sort:-title", games_dedup, platform['console_code'])
                                    games_list.extend(games_fetched)
                                    games_dedup = duped_fetch
                                    with open(f"games_list/{platform['console_code']}.json", "w", encoding="utf-8") as file:
                                        json.dump(games_list, file, indent=4)
                    else:
                        # genres_list = []
                        for genre in genres_list:
                            # genre_name = genre['genre_name']
                            genre_code = genre['genre_link'].split('/')[-2]

                            # if genre_code in ['action', 'adventure', 'educational', 'idle', 'puzzle', 'racing-driving', 'role-playing-rpg', 'simulation', 'special_edition', 'sports', 'strategy']:
                            #     continue
                            if genre_code not in ['action', 'adventure','eductational']:
                                continue

                            page.goto(f"https://www.mobygames.com/game/genre:{genre_code}/platform:{platform['console_code']}/sort:title/", wait_until='domcontentloaded', timeout=120000)
                            

                            results_element = page.query_selector('p.no-select.text-muted')
                            if not results_element:
                                games_fetched, duped_fetch = handle_pagination_and_get_games_list(f"https://www.mobygames.com/game/genre:{genre_code}/platform:{platform['console_code']}/sort:title/", games_dedup, platform['console_code'], genre_code)
                                games_list.extend(games_fetched)
                                games_dedup = duped_fetch
                                with open(f"games_list/{platform['console_code']}.json", "w", encoding="utf-8") as file:
                                    json.dump(games_list, file, indent=4)
                            else:
                                results_text = results_element.inner_text()                        
                                results_count = int(results_text.split('results')[0].strip().replace(',', '').split()[-1])
                                print(f'result count for genre {genre} is {results_count}')
                                # if less than 1000 get list and move on
                                if results_count <= 1000:
                                    games_fetched, duped_fetch = handle_pagination_and_get_games_list(f"https://www.mobygames.com/game/genre:{genre_code}/platform:{platform['console_code']}/sort:title/", games_dedup, platform['console_code'], genre_code)
                                    games_list.extend(games_fetched)
                                    games_dedup = duped_fetch
                                    with open(f"games_list/{platform['console_code']}.json", "w", encoding="utf-8") as file:
                                        json.dump(games_list, file, indent=4)

                                # check if games are more than 1000
                                else:
                                    print(f'results count is greater than 1000 for genre {genre} splitting by years')
                                    # if greater than 1000 break by years and get the data.
                                    for year in year_data:
                                        print(f'scrapping for year {year}')
                                        page.goto(f"https://www.mobygames.com/game/from:{year}/genre:{genre_code}/platform:{platform['console_code']}/until:{year}/sort:title/", wait_until='domcontentloaded', timeout=60000)
                                        results_element = page.query_selector('p.no-select.text-muted')
                                        if results_element:
                                            results_text = results_element.inner_text()                        
                                            results_count = int(results_text.split('results')[0].strip().replace(',', '').split()[-1])
                                            print(f'result count for genre {genre} is {results_count} for year {year}')
                                            # if less than 1000 get list and move on
                                            if results_count <= 1000:
                                                games_fetched, duped_fetch = handle_pagination_and_get_games_list(f"https://www.mobygames.com/game/from:{year}/genre:{genre_code}/platform:{platform['console_code']}/until:{year}/sort:title", games_dedup, platform['console_code'], genre_code)
                                                games_list.extend(games_fetched)
                                                games_dedup = duped_fetch
                                                with open(f"games_list/{platform['console_code']}.json", "w", encoding="utf-8") as file:
                                                    json.dump(games_list, file, indent=4)
                                            elif results_count <= 2000:
                                                games_fetched, duped_fetch = handle_pagination_and_get_games_list(f"https://www.mobygames.com/game/from:{year}/genre:{genre_code}/platform:{platform['console_code']}/until:{year}/sort:title", games_dedup, platform['console_code'], genre_code)
                                                games_list.extend(games_fetched)
                                                games_dedup = duped_fetch
                                                games_fetched, duped_fetch = handle_pagination_and_get_games_list(f"https://www.mobygames.com/game/from:{year}/genre:{genre_code}/platform:{platform['console_code']}/until:{year}/sort:-title", games_dedup, platform['console_code'], genre_code)
                                                games_list.extend(games_fetched)
                                                games_dedup = duped_fetch
                                                with open(f"games_list/{platform['console_code']}.json", "w", encoding="utf-8") as file:
                                                    json.dump(games_list, file, indent=4)
                                                
                                            else:
                                                print(f'Result count for genre {genre} is greater than 1000 so splitting based on title.')
                                                # first 20ish iteration for non alphabets
                                                games_fetched, duped_fetch = handle_pagination_and_get_games_list(f"https://www.mobygames.com/game/from:{year}/genre:{genre_code}/platform:{platform['console_code']}/until:{year}/sort:title", games_dedup, platform['console_code'], genre_code)
                                                with open(f"games_list/{platform['console_code']}.json", "w", encoding="utf-8") as file:
                                                    json.dump(games_list, file, indent=4)
                                                games_list.extend(games_fetched)
                                                games_dedup = duped_fetch
                                                # else split by title and get the data, but first 20 iterations for getting titles with characters and numbers
                                                alphabets = '1234567890abcdefghijklmnopqrstuvwxyz'
                                                for alphabet in alphabets:
                                                    page.goto(f"https://www.mobygames.com/game/from:{year}/genre:{genre_code}/platform:{platform['console_code']}/title:{alphabet}/until:{year}/sort:title", wait_until='domcontentloaded', timeout=60000)
                                                    results_element = page.query_selector('p.no-select.text-muted')
                                                    if results_element:
                                                        results_text = results_element.inner_text()                        
                                                        results_count = int(results_text.split('results')[0].strip().replace(',', '').split()[-1])
                                                        print(f'result count for genre {genre} is {results_count}')
                                                        if results_count <= 1000:
                                                            games_fetched, duped_fetch = handle_pagination_and_get_games_list(f"https://www.mobygames.com/game/from:{year}/genre:{genre_code}/platform:{platform['console_code']}/title:{alphabet}/until:{year}/sort:title", games_dedup, platform['console_code'], genre_code)
                                                            games_list.extend(games_fetched)
                                                            games_dedup = duped_fetch
                                                            with open(f"games_list/{platform['console_code']}.json", "w", encoding="utf-8") as file:
                                                                json.dump(games_list, file, indent=4)
                                                        else:
                                                            print(f'results count is greater than 1000 for genre {genre} splitting by alphabets for year {year} for alphabet {alphabet}')
                                                            games_fetched, duped_fetch = handle_pagination_and_get_games_list(f"https://www.mobygames.com/game/from:{year}/genre:{genre_code}/platform:{platform['console_code']}/title:{alphabet}/until:{year}/sort:title", games_dedup, platform['console_code'], genre_code)
                                                            games_list.extend(games_fetched)
                                                            games_dedup = duped_fetch
                                                            games_fetched, duped_fetch = handle_pagination_and_get_games_list(f"https://www.mobygames.com/game/from:{year}/genre:{genre_code}/platform:{platform['console_code']}/title:{alphabet}/until:{year}/sort:-title", games_dedup, platform['console_code'], genre_code)
                                                            games_list.extend(games_fetched)
                                                            games_dedup = duped_fetch
                                                            with open(f"games_list/{platform['console_code']}.json", "w", encoding="utf-8") as file:
                                                                json.dump(games_list, file, indent=4)
             
                with open(f"games_list/{platform['console_code']}.json", "w", encoding="utf-8") as file:
                    json.dump(games_list, file, indent=4)