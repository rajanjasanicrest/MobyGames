import re
import json
import requests, boto3, os
from urllib.parse import urlparse
from io import BytesIO
from playwright.sync_api import sync_playwright

def normalize_text(text):
    """Remove special characters, convert to lowercase, and replace multiple spaces with a single space."""
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)  # Replace special characters with space
    text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with a single space
    return text.lower().strip()

def unordered_match(str1, str2):
    return sorted(str1.split()) == sorted(str2.split())

def upload_image_to_s3(image_url, bucket_name, folder="covers/"):
    """
    Downloads an image from the given URL and uploads it to an S3 bucket.

    :param image_url: URL of the image to upload.
    :param bucket_name: Name of the S3 bucket.
    :param folder: Folder path inside the bucket (default: "covers/").
    :return: The full S3 path of the uploaded image.
    """
    try:
        # Get image content
        response = requests.get(image_url, stream=True)
        response.raise_for_status()

        # Extract filename from URL
        parsed_url = urlparse(image_url)
        filename = os.path.basename(parsed_url.path)

        print(response.content)

        # Ensure filename is valid
        if not filename:
            raise ValueError("Invalid image URL, no filename found")

        # Define S3 key (folder + filename)
        s3_key = f"{folder}{filename}"

        # Upload to S3
        s3_client = boto3.client("s3")
        s3_client.upload_fileobj(
            BytesIO(response.content), 
            bucket_name, 
            s3_key, 
            ExtraArgs={"ContentType": response.headers["Content-Type"]}
        )

        # Construct and return the S3 URL
        s3_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"
        return s3_url

    except Exception as e:
        print(f"Error uploading image to S3: {e}")
        return None


class MobyGamesScraper:
    def __init__(self, headless=True):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=headless)
        self.context = self.browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent=self.get_agent()
        )
        self.context.add_cookies([
            {
                "name": "remember-www",
                "value": "login-v2-1114323-1100295|ce4be64d911bef101abeedc6ee2b1b0bef83b8c30ea51ceecb325c9bcc3e21a78bd85f68ad2f804e88890f10d2ab2ed18884dbee93139e7dac02af086c673227",
                "domain": ".mobygames.com",
                "path": "/",
                "max_age": 30 * 24 * 60 * 60
            }
        ])
        self.page = self.context.new_page()
    
    def get_agent(self):
        """ Return a valid user-agent string. You can rotate this for better anti-bot evasion. """
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def login(self, username, password):
        """ Logs into MobyGames """
        self.page.goto('https://www.mobygames.com/user/login/')
        self.page.fill('input[name="login"]', username)
        self.page.fill('input[name="password"]', password)
        self.page.click('button.btn.btn-primary')
        self.page.wait_for_load_state("networkidle")  # Ensure login completes
        print("Logged in successfully!")

    def get_overview_details(self, url):
        """ Scrape overview details """
        print('Processing Overview')
        try:
            self.page.goto(f'{url}', wait_until='domcontentloaded', timeout=2000000)
        except Exception as e:
            return None
        gameInfoBlock = self.page.query_selector('#infoBlock')


        title = self.page.query_selector('h1').inner_text()
        mobyid = [text.text_content().split('Moby ID: ')[1].split(' ')[0].strip() 
          for text in self.page.query_selector_all('.text-sm.text-muted')  
          if 'Moby ID' in text.text_content()][0]

        # genres related stuff
        rating = gameInfoBlock.query_selector('.info-score dl dt:text("Players") + dd span')
        if rating:
            rating = rating.get_attribute('data-tooltip').split(' ')[0]
        else:
            rating = None

        game_details = gameInfoBlock.query_selector_all('.info-genres dl.metadata dt')
        game_details_values = gameInfoBlock.query_selector_all('.info-genres dl.metadata dd')

        overview = {}
        for index, key in enumerate(game_details):
            key = key.text_content().strip()
            values = ','.join( [ a_tag.inner_text() for a_tag in game_details_values[index].query_selector_all('a')])
            overview[key] = values

        if self.page.query_selector('#gameOfficialDescription summary'):
            self.page.click('#gameOfficialDescription summary')
            self.page.wait_for_timeout(500)
            
        description = self.page.query_selector('#description-text')
        if description: description = description.inner_text()
        elif self.page.query_selector('#gameOfficialDescription'):
            description = self.page.locator('#gameOfficialDescription').inner_text()

        return {
            "title": title,
            "mobyid": mobyid,
            "rating": rating if rating else '',
            "description": description,
            **overview
        }

    def get_covers(self, url):
        """ Scrape game cover screenshots, packaging, and video standard info """
        print('Processing Covers')
        try:
            self.page.goto(url, wait_until="domcontentloaded")
        except Exception as e:
            print(e)
            return None
        
        cover_data = self.page.evaluate('''() => {
            const result = {};
            
            // Find all console sections
            const sections = document.querySelectorAll('section');
            
            for (const section of sections) {
                // Get console name from the h2 element
                const consoleHeader = section.querySelector('h2 a');
                if (!consoleHeader) continue;
                
                const consoleName = consoleHeader.textContent.trim();
                
                // Check for variant name (in small tag)
                let variantName = "";
                const variantElement = section.querySelector('h2 small');
                if (variantElement) {
                    variantName = variantElement.textContent.trim();
                    // Remove parentheses if present
                    variantName = variantName.replace(/^\(|\)$/g, '').trim();
                }
                            
                // Create a unique console key combining console name and variant
                const consoleKey = consoleName;
                
                if (!(consoleKey in result)) {
                    result[consoleKey] = [];
                }
                
                // Get packaging info
                const packagingRow = Array.from(section.querySelectorAll('tr td.text-nowrap')).find(td => td.textContent.includes("Packaging:"));

                let packaging = "";
                if (packagingRow) {
                    const packagingItems = packagingRow.nextElementSibling.querySelectorAll('ul.commaList li');
                    packaging = Array.from(packagingItems).map(item => item.textContent.trim()).join(", ");
                }
                
                // Skip if packaging includes "Electronic" (as per your original code)
                if (packaging.includes("Electronic")) continue;

                // Get video standard info
                const videoRow = Array.from(section.querySelectorAll('tr td.text-nowrap')).find(td => td.textContent.includes("Video Standard:"));

                let videoStandard = "";
                if (videoRow) {
                    const videoItems = videoRow.nextElementSibling.querySelectorAll('ul.commaList li');
                    videoStandard = Array.from(videoItems).map(item => item.textContent.trim()).join(", ");
                }
                
                // Get countries and create entries for each
                const countryRow = Array.from(section.querySelectorAll('tr td.text-nowrap')).find(td => td.textContent.includes("Country:"));

                if (countryRow) {
                    const countryItems = countryRow.nextElementSibling.querySelectorAll('ul.commaList li');
                    
                    for (const countryItem of countryItems) {
                        // Extract the country name (text before the flag image)
                        const countryName = countryItem.childNodes[0].textContent.trim();
                        
                        // Get all cover links (instead of images)
                        const coverLinks = [];
                        const imgFigures = section.querySelectorAll('div.img-holder figure');

                        for (const figure of imgFigures) {
                            const link = figure.querySelector('a');
                            
                            if (link) {
                                // Extract the href (URL leading to the full-size image page)
                                const imagePageUrl = link.getAttribute('href');
                                if (imagePageUrl) {
                                    coverLinks.push(imagePageUrl);
                                }
                            }
                        }
                        
                        // Create an entry for this country
                        result[consoleKey].push({
                            packaging: packaging,
                            comments: variantName || "",  // Add variant name as comments
                            video_standard: videoStandard,
                            country: countryName,
                            cover_links: coverLinks  // Store the URLs of cover pages
                        });
                    }
                }
            }
            
            return result;
        }''')

        if not cover_data or not isinstance(cover_data, dict):
            print("No Covers found.")
            return {}

        # Visit each cover page and extract the full-size image URL
        cover_cache = {}
        bucket_name = os.getenv('BUCKET_NAME')

        # Visit each cover page only once and extract full-size images
        for console, entries in cover_data.items():
            for entry in entries:
                sr_url_list = []
                for cover_link in entry["cover_links"]:
                    if cover_link in cover_cache:
                        # Reuse the stored full-size image URL
                        sr_url_list.append(cover_cache[cover_link])
                    else:
                        # Visit the cover link and extract the full-size image
                        self.page.goto(cover_link, wait_until="domcontentloaded")
                        full_size_image = self.page.evaluate('''() => {
                            const imgElement = document.querySelector('figure img');
                            return imgElement ? imgElement.getAttribute('src') : null;
                        }''')
                        
                        if full_size_image:
                            
                            s3_url = upload_image_to_s3(full_size_image, bucket_name, 'covers/')
                            if s3_url is None:
                                return None
                            sr_url_list.append(s3_url)
                            cover_cache[cover_link] = s3_url  # Store for reuse
                
                # Replace cover_links with full-size images
                entry["cover_images"] = sr_url_list
                del entry["cover_links"]

        return cover_data

    def get_screenshots(self, url):
        """Scrape full-size screenshots for each console."""
        print('Processing Screenshots')
        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(e)
            return None
        # Execute JavaScript to extract screenshot links by console
        screenshot_links = self.page.evaluate('''() => {
            const result = {};
            
            // Find all screenshot sections by console
            const sections = document.querySelectorAll('div[id^="screenshots-platform-"]');

            for (const section of sections) {
                // Get console name from the h2 element
                const consoleHeader = section.querySelector('h2');
                if (!consoleHeader) continue;
                
                const consoleName = consoleHeader.textContent.trim().replace(/\s+screenshots$/, '');
                result[consoleName] = [];

                // Extract all screenshot page links
                const figures = section.querySelectorAll('div.img-holder figure');

                for (const figure of figures) {
                    const link = figure.querySelector('a');
                    if (link && link.href) {
                        result[consoleName].push(link.href);
                    }
                }
            }
            return result;
        }''')

        if not screenshot_links or not isinstance(screenshot_links, dict):
            print("No screenshots found.")
            return {}

        full_screenshots = {}
        bucket_name = os.getenv('BUCKET_NAME')

        # Visit each screenshot page and extract the full-size image
        for console, links in screenshot_links.items():
            full_screenshots[console] = []
            for link in links:
                try:
                    self.page.goto(link, wait_until="domcontentloaded", timeout=60000)
                except Exception as e:
                    return None
                # Extract the full-size image URL from the visited page
                full_size_image = self.page.evaluate('''() => {
                    const img = document.querySelector('figure img'); // Adjust selector if needed
                    return img ? img.src : null;
                }''')

                if full_size_image:
                    
                    s3_url = upload_image_to_s3(full_size_image, bucket_name, 'screenshots/')
                    if s3_url is None: return  None
                    full_screenshots[console].append(s3_url)

        return full_screenshots

    def get_specs(self, url):
        """ Scrape game specifications """
        print('Processing Specs')
        try:
            self.page.goto(url, wait_until='domcontentloaded', timeout=60000)
        except Exception as e:
            print(e)
            return None

        specs_data = self.page.evaluate('''() => {
            const result = {};
                                            
            const tables = document.querySelectorAll('table.table-nowrap');
            // If no tables exist, return an empty object
            if (tables.length === 0) {
                return result;
            }
        
            // for Specs
            const specsTable = tables[0]; // Get the first table
            
            let currentConsole = null;
            
            // Process each row
            for (const row of specsTable.querySelectorAll('tbody tr')) {
                // Check if this is a console header row
                const headerElement = row.querySelector('td h4');
                
                if (headerElement) {
                    // Extract console name (remove the "+" part)
                    const consoleText = headerElement.textContent.trim();
                    currentConsole = consoleText.replace(/\s*\+\s*$/, '').trim();
                    if (!(currentConsole in result)) {
                        result[currentConsole] = {};
                    }
                } 
                // If we have a current console and this is a data row
                else if (currentConsole && row.querySelectorAll('td').length >= 2) {
                    const specType = row.querySelector('td').textContent.replace(':', '').replaceAll(' ', '_').toLowerCase().trim();
                    const specValues = [];
                    
                    // Extract all spec values
                    let specLinks = row.querySelectorAll('td:nth-child(2) ul.commaList li a');
                    console.log(specLinks)
                    for (const link of specLinks) {
                        specValues.push(link.textContent.trim());
                    }
                    if( specLinks.length == 0){
                        specLinks = row.querySelector('td:nth-child(2)');
                        if (specLinks) {
                            specValues.push(specLinks.textContent.trim());
                        }
                    }
                    
                    if (specValues.length === 1) {
                        result[currentConsole][specType] = specValues[0];
                    } else if (specValues.length > 1) {
                        result[currentConsole][specType] = specValues.join(',');
                    }
                                        
                }
            }
            
            return result ? result : {};
        }''')
        
        return specs_data

    def get_ratings(self, url):
        """ Scrape game ratings """
        print('Processing Ratings')
        try:
            self.page.goto(url, wait_until='domcontentloaded', timeout=60000)
        except Exception as e:
            print(e)
            return None

        # Evaluate the entire table extraction in JavaScript for better control
        ratings_data = self.page.evaluate('''() => {
            const result = {};
                                        
            const tables = document.querySelectorAll('table.table-nowrap');
            // If no tables exist, return an empty object
            if (tables.length === 0) {
                return result;
            }
        
           
            // for ratings
            const ratingsTable = tables[tables.length - 1]; // Get the last table
            
            let currentConsole = null;
            
            // Process each row
            for (const row of ratingsTable.querySelectorAll('tbody tr')) {
                // Check if this is a console header row
                const headerElement = row.querySelector('th h4');
                
                if (headerElement) {
                    // Extract console name (remove the "+" part)
                    const consoleText = headerElement.textContent.trim();
                    currentConsole = consoleText.replace(/\s*\+\s*$/, '').trim();
                    if (!(currentConsole in result)) {
                        result[currentConsole] = {};
                    }
                } 
                // If we have a current console and this is a data row
                else if (currentConsole && row.querySelectorAll('td').length >= 2) {
                    const ratingType = row.querySelector('td').textContent.replace(':', '').replaceAll(' ', '_').toLowerCase().trim();
                    const ratingValues = [];
                    
                    // Extract all rating values
                    const ratingLinks = row.querySelectorAll('td:nth-child(2) ul.commaList li a');
                    for (const link of ratingLinks) {
                        ratingValues.push(link.textContent.trim());
                    }
                    
                    if (ratingValues.length === 1) {
                        result[currentConsole][ratingType] = ratingValues[0];
                    } else if (ratingValues.length > 1) {
                        result[currentConsole][ratingType] = ratingValues;
                    }
                }
            }
            
            return result;
        }''')
        
        return ratings_data

    def get_releases(self, url):
        """ Scrape game releases information """
        print('Processing releases')
        try:
            self.page.goto(url, wait_until='domcontentloaded', timeout=60000)
        except Exception as e:
            print(e)
            return None

        releases = {}
        consoles = self.page.query_selector_all('#main h4')

        for i, console in enumerate(consoles):
            console_name = console.inner_text().strip()
            releases[console_name] = []

            console_indices = self.page.evaluate("""() => {
                const h4s = Array.from(document.querySelectorAll('#main h4'));
                return h4s.map(el => ({
                    text: el.innerText.trim(),
                    index: Array.from(document.querySelectorAll('*')).indexOf(el)
                }));
            }""")

            current_index, next_index = None, None
            for idx, c in enumerate(console_indices):
                if c['text'] == console_name:
                    current_index = c['index']
                    if idx < len(console_indices) - 1:
                        next_index = console_indices[idx + 1]['index']
                    break

            if current_index is None:
                continue

            table_selectors = self.page.evaluate("""(args) => {
                const allElements = Array.from(document.querySelectorAll('*'));
                const { currentIndex, nextIndex } = args;
                const endIndex = nextIndex || allElements.length;
                const tablePaths = [];

                for (let i = currentIndex + 1; i < endIndex; i++) {
                    const element = allElements[i];
                    if (element.tagName === 'TABLE' && element.classList.contains('releaseTable')) {
                        let selector = 'table.releaseTable';
                        const tableIndex = Array.from(document.querySelectorAll(selector)).indexOf(element);
                        tablePaths.push(`${selector}:nth-of-type(${tableIndex + 1})`);
                    }
                }
                return tablePaths;
            }""", {'currentIndex': current_index, 'nextIndex': next_index})

            for table_selector in table_selectors:
                table = self.page.query_selector(table_selector)
                if not table:
                    continue

                common_info = {}
                country_groups = []
                current_country_group = []
                in_country_section = False

                rows = table.query_selector_all('tbody tr')

                if rows:
                    date_cell = rows[0].query_selector('td')
                    if date_cell:
                        release_date = date_cell.inner_text().strip().replace(" Release", "")
                        common_info['release_date'] = release_date

                for row in rows[1:]:
                    cells = row.query_selector_all('td')
                    if len(cells) == 2:
                        key, value_text = cells[0].inner_text().strip().replace(':', ''), cells[1].inner_text().strip()
                        key = key.lower().replace(' ', '_')

                        if key == 'countries':
                            in_country_section = True
                            countries_html = cells[1].inner_html()
                            clean_html = self.page.evaluate("(html) => html.replace(/<img[^>]*>/g, '').trim();", countries_html)
                            countries = [c.strip() for c in clean_html.split(',')]

                            # Create a new group for each country
                            new_country_groups = []
                            for country in countries:
                                new_group = common_info.copy()
                                new_group['country'] = country
                                new_country_groups.append(new_group)
                            country_groups.extend(new_country_groups)
                            current_country_group = new_country_groups  # Update the current group

                        elif in_country_section and current_country_group:
                            # Handle duplicate keys
                            new_country_group = []
                            for group in current_country_group:
                                if key in group:
                                    # Split entry
                                    new_group1 = group.copy()
                                    new_group2 = group.copy()
                                    new_group2[key] = value_text
                                    new_country_group.extend([new_group1, new_group2])
                                else:
                                    # Update existing entry
                                    group[key] = value_text
                                    new_country_group.append(group)  # Keep track of updated groups
                            
                            # Update all country groups
                            country_groups = [g for g in country_groups if g not in current_country_group] + new_country_group
                            current_country_group = new_country_group

                        else:
                            # Gather common information
                            common_info[key] = value_text

                    else:
                        # Reset the flags when not a key-value row
                        in_country_section = False
                        current_country_group = []

                releases[console_name].extend(country_groups)

        return releases

    def close(self):
        """ Clean up resources """
        self.browser.close()
        self.playwright.stop()

def merge_covers_releases_data(covers, releases):
    # Initialize merged result
    merged_data = {}

    # Iterate over consoles in covers_data
    considered_release = []
    for console, cover_entries in covers.items():
        if console not in merged_data:
            merged_data[console] = []

        release_entries = releases.get(console, [])

        # Iterate over cover entries
        for cover_entry in cover_entries:
            country = cover_entry['country']
            comments = cover_entry.get('comments', '')
            
            # Find matching release entry
            matching_release_entries = [
                entry for entry in release_entries
                if entry.get('country') == country and (normalize_text(entry.get('comments', '')) == normalize_text(comments) or unordered_match(normalize_text(entry.get('comments', '')), normalize_text(comments)))
            ]

            if matching_release_entries:
                # Merge entries
                for matching_release_entry in matching_release_entries:
                    merged_entry = {**cover_entry, **matching_release_entry}
                    merged_entry['console'] = console
                    merged_data[console].append(merged_entry)

                considered_release.extend(matching_release_entries)
            else:
                # No matching release entry, add cover entry as is
                cover_entry['console'] = console
                merged_data[console].append(cover_entry)

    # Add remaining release entries that have no matching cover entry
    release_entries = []
    for key,value in releases.items():
        for entry in value:
            entry['console'] = key
        release_entries.extend(value)

    for release_entry in release_entries:
        if release_entry not in considered_release:
            if release_entry['console'] not in merged_data:
                merged_data[release_entry['console']] = [release_entry]
            else:
                merged_data[release_entry['console']].append(release_entry)

    print('Covers and releases data merged successfully.')

    return merged_data

def parse_data(overview, screenshots, ratings, specs, merged_cover_releases):
    # Add overview details to each JSON object in merged_cover_releases
    for console, entries in merged_cover_releases.items():
        for entry in entries:
            # Add overview details
            entry.update(**overview)

    # Add screenshots based on consoles to each JSON object in merged_cover_releases
    for console, entries in merged_cover_releases.items():
        for entry in entries:
            # Add screenshots
            entry['screenshots'] = screenshots.get(console, [])

    # Add ratings based on consoles to each JSON object in merged_cover_releases
    for console, entries in merged_cover_releases.items():
        for entry in entries:
            # Add specs
            entry.update( **(ratings.get(console, {})) )

    # Add specs based on consoles to each JSON object in merged_cover_releases
    for console, entries in merged_cover_releases.items():
        for entry in entries:
            # Add specs
            entry['specs'] = ' | '.join(f"{k}: {v}" for k, v in specs.get(console, {}).items())

    return merged_cover_releases


if __name__ == '__main__':

    url = 'https://www.mobygames.com/game/193484/atari-mania/'
    # Usage
    scraper = MobyGamesScraper(headless=False)  # Change to True for background execution
    # scraper.login('rajan.j@crestskillserve.com', 'mobygames01')

    overview = scraper.get_overview_details(url)
    print(overview)
    # screenshots = scraper.get_screenshots(f'{url}screenshots/')
    # covers = scraper.get_covers(f'{url}covers/')
    # ratings = scraper.get_ratings(f'{url}specs/')
    # specs = scraper.get_specs(f'{url}specs/')
    # releases = scraper.get_releases(f'{url}releases/')

#     merged_cover_releases = merge_covers_releases_data(covers, releases)

#     parse_data_result = parse_data(overview, screenshots, ratings, specs, merged_cover_releases)

#     # lineraise the json
#     # Collect all unique keys dynamically
#     json_data = []
#     for key, value in parse_data_result.items():
#         json_data.extend(value)


#     final_list = []
#     # remove virtual entries
#     for entry in json_data:
#         if any(word in entry.get('comments', '') for word in ['virtual', 'online', 'download']):
#             continue
#         final_list.append(entry)


#     with open('RiverRaidd.json', 'w', encoding='utf-8') as f:
#         json.dump(final_list, f, indent=4)
#     print("River Raid Scrapped Successfully")
#     scraper.close()    