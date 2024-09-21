import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode, urljoin
import csv
import json

# Base URL for bike listings
base_url = 'https://www.olx.pt/desporto-e-lazer/bicicletas/?'
# Base URL for the ad details
ad_base_url = 'https://www.olx.pt'

def get_user_inputs():
    requested_pages = int(input("Enter the number of pages to scrape: ").strip())
    min_price = input("Enter the minimum price threshold (leave blank for no minimum): ").strip()
    max_price = input("Enter the maximum price threshold (leave blank for no maximum): ").strip()
    output_formats = input("Enter the desired output formats (csv, json, or both): ").strip().lower()
    return requested_pages, min_price, max_price, output_formats

def format_location(location_str):
    location_str = location_str.strip()
    dash_index = location_str.find('-')
    if dash_index != -1:
        location_part = location_str[:dash_index].strip()
    else:
        location_part = location_str
    location_part = location_part.strip()
    return location_part

def extract_description(soup):
    description_div = soup.find('div', {'data-cy': 'ad_description'})
    if description_div:
        description = description_div.get_text(separator='\n', strip=True)
        return description
    return 'No description available'

def scrape_page(url, ad_base_url, processed_urls):
    all_valid_listings = []
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error if the URL is not valid
        soup = BeautifulSoup(response.text, 'html.parser')
        ad_containers = soup.find_all('div', {'data-cy': 'l-card'})
        
        if not ad_containers:
            print(f"No ads found on page: {url}")
            return all_valid_listings, True  # Indicate no new content

        found_duplicate = False
        for ad in ad_containers:
            link_tag = ad.find('a', class_='css-z3gu2d', href=True)
            if link_tag:
                relative_href = link_tag['href']
                href = urljoin(ad_base_url, relative_href)

                if href in processed_urls:
                    print(f"Duplicate found: {href}")
                    found_duplicate = True
                    continue  # Skip if this URL has already been processed

                processed_urls.add(href)

                price_tag = ad.find('p', {'data-testid': 'ad-price'})
                price = price_tag.get_text(strip=True) if price_tag else 'Price not found'
                
                location_tag = ad.find('p', {'data-testid': 'location-date'})
                location = format_location(location_tag.get_text(strip=True)) if location_tag else 'Location not found'
                
                ad_response = requests.get(href)
                if ad_response.status_code == 200:
                    soup_ad = BeautifulSoup(ad_response.text, 'html.parser')
                    description = extract_description(soup_ad)
                    
                    # Filter out listings where the description contains "26"
                    if "26" not in description:
                        all_valid_listings.append((price, href, location, description))
                else:
                    print(f"Error accessing ad URL: {href}")
        
        return all_valid_listings, found_duplicate
    except requests.exceptions.RequestException as e:
        print(f"Error accessing {url}: {e}")
        return [], False

def write_to_csv(listings):
    csv_file = 'bike_listings.csv'
    try:
        with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Index', 'Link', 'Price', 'Location', 'Description'])
            for index, (price, link, location, description) in enumerate(listings):
                writer.writerow([index + 1, link, price, location, description])
        print(f"Results have been written to {csv_file}")
    except IOError as e:
        print(f"Failed to write CSV file. Error: {e}")

def write_to_json(listings):
    json_file = 'bike_listings.json'
    try:
        with open(json_file, mode='w', encoding='utf-8') as file:
            listings_dict = [{'Index': index + 1, 'Link': link, 'Price': price, 'Location': location, 'Description': description} 
                             for index, (price, link, location, description) in enumerate(listings)]
            json.dump(listings_dict, file, ensure_ascii=False, indent=4)
        print(f"Results have been written to {json_file}")
    except IOError as e:
        print(f"Failed to write JSON file. Error: {e}")

def build_url(page, min_price, max_price):
    params = {
        'page': page,
        'search[filter_enum_tipo][0]': 'btt',  # Specifying 'btt' as bike type
    }
    
    if min_price:
        params['search[filter_float_price:from]'] = min_price
    if max_price:
        params['search[filter_float_price:to]'] = max_price

    url = base_url + urlencode(params)
    return url

def main():
    requested_pages, min_price, max_price, output_formats = get_user_inputs()

    all_valid_listings = []
    processed_urls = set()  # Track processed URLs to avoid duplicates

    for page in range(1, requested_pages + 1):
        url = build_url(page, min_price, max_price)
        print(f"Scraping page {page}: {url}")
        
        valid_listings, found_duplicate = scrape_page(url, ad_base_url, processed_urls)
        all_valid_listings.extend(valid_listings)
        
        if found_duplicate:
            print(f"Stopping further scraping due to duplicates found on page {page}.")
            break
    
    # Save listings to output formats only once after scraping is complete
    if 'csv' in output_formats:
        write_to_csv(all_valid_listings)
    
    if 'json' in output_formats:
        write_to_json(all_valid_listings)

    if "both" in output_formats:
        write_to_csv(all_valid_listings)
        write_to_json(all_valid_listings)
    
    if not all_valid_listings:
        print(f"No valid listings found.")
    else:
        print(f"Scraping completed with {len(all_valid_listings)} valid listings found.")

if __name__ == "__main__":
    main()