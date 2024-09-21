import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode, urljoin
import re
import csv
import json

# Base URL for the bike listings
base_url = 'https://www.olx.pt/carros-motos-e-barcos/motociclos-scooters/'
# Base URL for the ad details
ad_base_url = 'https://www.olx.pt'

def get_user_inputs():
    bike_brand = input("Enter the bike brand you want to search for: ").lower().strip()
    bike_model = input("Enter the bike model (or press Enter to skip): ").strip()
    year_from = input("Enter the starting year (or press Enter to skip): ").strip()
    year_to = input("Enter the ending year (or press Enter to skip): ").strip()
    requested_pages = int(input("Enter the number of pages to scrape: ").strip())
    output_formats = input("Enter the desired output formats (csv, json, or both): ").strip().lower()
    return bike_brand, bike_model, year_from, year_to, requested_pages, output_formats

def price_to_number(price_str):
    price_str = re.sub(r'[^\d,]', '', price_str)
    price_str = price_str.replace(',', '.')
    try:
        return float(price_str)
    except ValueError:
        return float('inf')

def format_location(location_str):
    location_str = location_str.strip()
    dash_index = location_str.find('-')
    if dash_index != -1:
        location_part = location_str[:dash_index].strip()
    else:
        location_part = location_str
    location_part = re.sub(r'\s*\(.*\)', '', location_part).strip()
    return location_part

def extract_description(soup):
    description_div = soup.find('div', {'data-cy': 'ad_description'})
    if description_div:
        description = description_div.get_text(separator='\n', strip=True)
        return description
    return 'No description available'

def scrape_page(url, ad_base_url, seen_urls):
    all_valid_listings = []
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        ad_containers = soup.find_all('div', {'data-cy': 'l-card'})
        if not ad_containers:
            return []
        
        for ad in ad_containers:
            link_tag = ad.find('a', class_='css-z3gu2d', href=True)
            if link_tag:
                relative_href = link_tag['href']
                href = urljoin(ad_base_url, relative_href)
                
                # Skip duplicates by checking if the link has been seen before
                if href in seen_urls:
                    continue
                seen_urls.add(href)

                price_tag = ad.find('p', {'data-testid': 'ad-price'})
                price = price_tag.get_text(strip=True) if price_tag else 'Price not found'
                price_number = price_to_number(price)
                location_tag = ad.find('p', {'data-testid': 'location-date'})
                location = format_location(location_tag.get_text(strip=True)) if location_tag else 'Location not found'
                
                ad_response = requests.get(href)
                description = extract_description(BeautifulSoup(ad_response.text, 'html.parser')) if ad_response.status_code == 200 else 'No description available'
                all_valid_listings.append((price_number, price, href, location, description))
    else:
        print(f"Failed to retrieve page {url}. Status code: {response.status_code}")
        return []  # Stop on error pages
    return all_valid_listings

def write_to_csv(listings):
    csv_file = 'bike_listings.csv'
    try:
        with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Index', 'Link', 'Price', 'Location', 'Description'])
            for index, price, link, location, description in listings:
                writer.writerow([index, link, price, location, description])
        print(f"\nResults have been written to {csv_file}")
    except IOError as e:
        print(f"Failed to write CSV file. Error: {e}")

def write_to_json(listings):
    json_file = 'bike_listings.json'
    try:
        with open(json_file, mode='w', encoding='utf-8') as file:
            listings_dict = [{'Index': index, 'Link': link, 'Price': price, 'Location': location, 'Description': description} for index, price, link, location, description in listings]
            json.dump(listings_dict, file, ensure_ascii=False, indent=4)
        print(f"Results have also been written to {json_file}")
    except IOError as e:
        print(f"Failed to write JSON file. Error: {e}")

def main():
    bike_brand, bike_model, year_from, year_to, requested_pages, output_formats = get_user_inputs()
    
    # Initial URL setup
    base_params = {
        'search[order]': 'filter_float_price:asc',
        'search[filter_enum_modelo][0]': bike_model if bike_model else '',
        'search[filter_float_year:from]': year_from if year_from else '',
        'search[filter_float_year:to]': year_to if year_to else ''
    }
    
    all_valid_listings = []
    seen_urls = set()  # To track URLs we've already seen
    
    for page in range(1, requested_pages + 1):
        params = base_params.copy()
        params['page'] = page
        page_url = f"{base_url}{bike_brand}/?" + urlencode(params)
        print(f"Scraping page {page}: {page_url}")
        
        listings_on_page = scrape_page(page_url, ad_base_url, seen_urls)
        
        if not listings_on_page:
            print(f"No new listings found on page {page}. Ending scraping.")
            break  # If no new listings are found, stop scraping
        
        all_valid_listings.extend(listings_on_page)
    
    # Sort listings and write to CSV/JSON
    all_valid_listings.sort()
    index_listings = [(index + 1, price, link, location, description) for index, (_, price, link, location, description) in enumerate(all_valid_listings)]
    
    if 'csv' in output_formats:
        write_to_csv(index_listings)
    
    if 'json' in output_formats:
        write_to_json(index_listings)

    if 'both' in output_formats:
        write_to_json(index_listings)
        write_to_csv(index_listings)
    
    if output_formats not in ['csv', 'json', 'both']:
        print("Invalid format selected. Please choose 'csv', 'json', or 'both'.")
    
    if index_listings:
        print(f"\nTotal number of valid listings found: {len(index_listings)}")
    else:
        print(f"\nNo valid listings found for {bike_brand}.")

if __name__ == "__main__":
    main()