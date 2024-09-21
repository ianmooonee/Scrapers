import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode, urljoin
import re
import csv
import json

# Base URL for the car listings
base_url = 'https://www.olx.pt/carros-motos-e-barcos/carros/'
# Base URL for the ad details
ad_base_url = 'https://www.olx.pt'

def get_user_inputs():
    car_brand = input("Enter the car brand you want to search for: ").lower().strip()
    car_model = input("Enter the car model (or press Enter to skip): ").strip()
    year_from = input("Enter the starting year (or press Enter to skip): ").strip()
    year_to = input("Enter the ending year (or press Enter to skip): ").strip()
    requested_pages = int(input("Enter the number of pages to scrape (max 25): ").strip())
    output_formats = input("Enter the desired output formats (csv, json, or both): ").strip().lower()
    return car_brand, car_model, year_from, year_to, requested_pages, output_formats

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

def get_total_pages(soup):
    pagination = soup.find('ul', class_='pagination-list')
    if pagination:
        page_links = pagination.find_all('a')
        if page_links:
            last_page_link = page_links[-1]
            try:
                return int(last_page_link.get_text())
            except ValueError:
                return 1
    # Check for next page link as an alternative
    next_page_link = soup.find('a', {'data-cy': 'pagination-forward'})
    if next_page_link:
        href = next_page_link.get('href', '')
        match = re.search(r'page=(\d+)', href)
        if match:
            return int(match.group(1)) + 1
    return 1

def scrape_page(url, ad_base_url):
    all_valid_listings = []
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        ad_containers = soup.find_all('div', {'data-cy': 'l-card'})
        for ad in ad_containers:
            link_tag = ad.find('a', class_='css-z3gu2d', href=True)
            if link_tag:
                relative_href = link_tag['href']
                href = urljoin(ad_base_url, relative_href)
                price_tag = ad.find('p', {'data-testid': 'ad-price'})
                price = price_tag.get_text(strip=True) if price_tag else 'Price not found'
                price_number = price_to_number(price)
                location_tag = ad.find('p', {'data-testid': 'location-date'})
                location = format_location(location_tag.get_text(strip=True)) if location_tag else 'Location not found'
                ad_response = requests.get(href)
                description = extract_description(BeautifulSoup(ad_response.text, 'html.parser')) if ad_response.status_code == 200 else 'No description available'
                all_valid_listings.append((price_number, price, href, location, description))
    else:
        print(f"Failed to retrieve page. Status code: {response.status_code}")
    return all_valid_listings

def write_to_csv(listings):
    csv_file = 'car_listings.csv'
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
    json_file = 'car_listings.json'
    try:
        with open(json_file, mode='w', encoding='utf-8') as file:
            listings_dict = [{'Index': index, 'Link': link, 'Price': price, 'Location': location, 'Description': description} for index, price, link, location, description in listings]
            json.dump(listings_dict, file, ensure_ascii=False, indent=4)
        print(f"Results have also been written to {json_file}")
    except IOError as e:
        print(f"Failed to write JSON file. Error: {e}")

def main():
    car_brand, car_model, year_from, year_to, requested_pages, output_formats = get_user_inputs()
    initial_url = f"{base_url}{car_brand}/?" + urlencode({
        'search[order]': 'filter_float_price:asc',
        'search[filter_enum_modelo][0]': car_model if car_model else '',
        'search[filter_float_year:from]': year_from if year_from else '',
        'search[filter_float_year:to]': year_to if year_to else ''
    })
    
    response = requests.get(initial_url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        total_pages = get_total_pages(soup)
        total_pages = min(requested_pages, total_pages)
        
        all_valid_listings = []
        for page in range(1, total_pages + 1):
            params = {
                'page': page,
                'search[order]': 'filter_float_price:asc'
            }
            if car_model:
                params['search[filter_enum_modelo][0]'] = car_model
            if year_from:
                params['search[filter_float_year:from]'] = year_from
            if year_to:
                params['search[filter_float_year:to]'] = year_to
            url = f"{base_url}{car_brand}/?" + urlencode(params)
            print(f"Scraping page {page}: {url}")
            all_valid_listings.extend(scrape_page(url, ad_base_url))
        
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
            print(f"\nValid listings found across {total_pages} pages for {car_brand} listings:\n")
            print(f"\nTotal number of valid listings found across {total_pages} pages: {len(index_listings)}")
        else:
            print(f"\nNo valid listings found for {car_brand} across {total_pages} pages.")
    else:
        print(f"Failed to retrieve the initial page. Status code: {response.status_code}")

if __name__ == "__main__":
    main()