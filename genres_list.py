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

        page.goto("https://www.mobygames.com/genre/", wait_until='domcontentloaded', timeout=60000)

        genres = page.query_selector_all("section ul li")

        genre_object = []

        for genre in genres:

            genre_name = genre.query_selector('a').inner_text()   
            genre_link = genre.query_selector('a').get_attribute('href')   

            genre_object.append({
                'genre_name': genre_name,
                'genre_link': genre_link
            })

            
        
        context.close()
        browser.close()
        with open("genres.json", "w", encoding="utf-8") as file:
            json.dump(genre_object, file, indent=4, ensure_ascii=False)


if __name__ == '__main__':
    visit_mobygames()
    print("✅ Data exported successfully to genres.json")