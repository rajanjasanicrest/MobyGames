import json, re, os, time
from get_agents import get_agent
from playwright.sync_api import sync_playwright
from mobygames import MobyGamesScraper, parse_data, merge_covers_releases_data
from json_to_excel import export_json_to_excel


def scrapeGamesByConsole():

    with open('mobygames_platforms.json', 'r', encoding='utf-8') as file:
        platforms = json.load(file)

    scrapper = MobyGamesScraper(headless=True)
    for platform in platforms:
        console_code = platform['console_code']

        console_games = []

        # if console_code in [
        #     'matsushitapanasonic-jr', 'mattel-aquarius', 'memotech-mtx', 'meritum', 'microbee', 'microtan-65', 'microvision', 'multi8', 'motorola-6800', 'mre', 'msx', 'ngage', 'nascom', 'neo-geo-cd', 'neo-geo-pocket', 'neo-geo-pocket-color', 'neo-geo-x', 'newbrain', 'new-nintendo-3ds', 'n64', 'nintendo-dsi', 'northstar', 'novel-760', 'nuon', 'odyssey', 'odyssey-2', 'ohio-scientific', 'orao', 'oric', 'os2', 'os2', ]:
        if console_code in [
            'amiga',
            'cpc',
            'apple-i',
            'apple2',
            'apple2gs',
            'arcade',
            'atari-8-bit',
            'atari-st',
            'bbc-micro',
            'vic-20',
        ]:

            with open(f'games_list/{console_code}.json', 'r', encoding='utf-8') as file:
                games_list = json.load(file)

            scrapped_games = []
            safe_platform_name = platform['platform'].replace("/", "").replace("\\", "").replace("?", "").replace("*", "").replace(':','')
            if os.path.exists(f'excels/{safe_platform_name}.xlsx'):
                continue
            if os.path.exists(f'data/{safe_platform_name}.json'):
                with open(f'data/{safe_platform_name}.json', 'r', encoding='utf-8') as file:
                    scrapped_games = json.load(file)

            if scrapped_games:
                console_games.extend(scrapped_games)
            
            scrapped_games = [x['game_url'] for x in scrapped_games]
            total_games = len(games_list)
            for index, game in enumerate(games_list):
                if game['link'] not in scrapped_games:
                    print(f"Scraping {game['game']}, {index+1} of {total_games} for {platform['platform']}...")
                    
                    game_code = game['game_code']
                    # if game_code == 'galaga':
                    print(game["link"])
                    overview_url = game["link"]
                    release_url = f'{game["link"]}/releases/{console_code}'
                    specs_ratings_url = f'{game["link"]}/specs/{console_code}'
                    covers_url = f'{game["link"]}/covers/{console_code}'
                    screenshots_url = f'{game["link"]}/screenshots/{console_code}'

                    game_overview = scrapper.get_overview_details(overview_url)
                    if game_overview is None:
                        scrapper.close()
                        return 'restart'
                    game_releases = scrapper.get_releases(release_url)
                    if game_releases is None: 
                        scrapper.close()
                        return 'restart'
                    game_specs = scrapper.get_specs(specs_ratings_url)
                    if game_specs is None: 
                        scrapper.close()
                        return 'restart'
                    game_ratings = scrapper.get_ratings(specs_ratings_url)
                    if game_ratings is None: 
                        scrapper.close()
                        return 'restart'
                    game_covers = scrapper.get_covers(covers_url)
                    if game_covers is None: 
                        scrapper.close()
                        return 'restart'
                    if game_covers or game_releases:
                        game_screenshots = scrapper.get_screenshots(screenshots_url)
                        if game_screenshots is None: 
                            scrapper.close()
                            return 'restart'

                        merged_cover_releases = merge_covers_releases_data(game_covers, game_releases)
                        parse_data_result = parse_data(game_overview, game_screenshots, game_ratings, game_specs, merged_cover_releases)

                        # Collect all unique keys dynamically
                        json_data = []
                        for key, value in parse_data_result.items():
                            json_data.extend(value)

                        final_list = []
                        # remove virtual entries
                        for entry in json_data:
                            comments = entry.get('comments', '')  # Ensure it's a string
                            if isinstance(comments, str) and any(word in comments.lower() for word in ['virtual release', 'online', 'download', 'eshop']):
                                final_list.append({'game_url': game['link']})
                            entry['game_url'] = game['link']
                            final_list.append(entry)

                        console_games.extend(final_list)

                    with open(f'data/{safe_platform_name}.json', 'w', encoding='utf-8') as f:
                        json.dump(console_games, f, indent=4)


            with open(f'data/{safe_platform_name}.json', 'w', encoding='utf-8') as f:
                json.dump(console_games, f, indent=4)

            priority_columns = ["console", "title", "comments", "mobyid", "country", "Genre", 'rating', 'description', 'published_by', 'developed_by'] 
            export_json_to_excel(console_games, f'excels/{safe_platform_name}.xlsx', priority_columns)
            print(f"{platform['platform']} Scrapped Successfully")

    scrapper.close()
    return 'exit'

if __name__ == '__main__':

    status = 'start'
    while status != 'exit':
        print("Waking up...")
        status = scrapeGamesByConsole()