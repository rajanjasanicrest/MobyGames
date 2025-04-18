import json, re, os, time
from get_agents import get_agent
from playwright.sync_api import sync_playwright

def visit_mobygames():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False
        )  # Set headless=True for background execution
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent=get_agent(),
        )

        page = context.new_page()

        page.goto("https://www.mobygames.com/platform/", wait_until='domcontentloaded')

        platforms = page.query_selector_all("tbody tr")

        platforms_object = []

        for platform in platforms:

            platform_name = platform.query_selector('td a').inner_text()   
            platform_link = platform.query_selector('td a').get_attribute('href')
            game_count_td = platform.query_selector_all('td')
            games = game_count_td[1].inner_text().strip() if len(game_count_td) > 1 else "0"


            platforms_object.append(
                {
                    'platform': platform_name,
                    'link': platform_link,
                    'games': games,
                    'console_code': platform_link.split('/')[-2]
                }
            )
        
        context.close()
        browser.close()
        with open("mobygames_platforms.json", "w", encoding="utf-8") as file:
            json.dump(platforms_object, file, indent=4, ensure_ascii=False)


if __name__ == '__main__':
    visit_mobygames()
    print("✅ Data exported successfully to mobygames_platforms.json")