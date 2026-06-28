import os
import json
import re
from dotenv import load_dotenv
# import tkinter as tk
from datetime import datetime
import argparse
import random
import time
import getpass

from selenium import webdriver
from selenium_stealth import stealth

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC\

# Convert a date/time string from 'Jan 30' or 'Jan 30, 2024' format to '2024-01-30 00:00' format.
def convert_datetime(input_string):
    current_year = datetime.now().year
    date_format = '%b %d, %Y'
    if ',' not in input_string:
        input_string += f", {current_year}"  # Add the current year
    input_datetime = datetime.strptime(input_string, date_format)
    # input_datetime = datetime.strptime(input_string, '%b %d, %Y, %I:%M %p') // For old format that includes time
    output_string = input_datetime.strftime('%Y-%m-%d %H:%M')
    return output_string

# Return true if the second date (of format '2024-01-30 18:23') is greater than the first one (of format '2024-01-30-18-23').
def is_web_date_greater(date_str_from_arg, date_str_from_web):
    format_a = '%Y-%m-%d %H:%M'
    format_b = '%Y-%m-%d %H:%M'
    date_a = datetime.strptime(date_str_from_arg, format_a)
    date_b = datetime.strptime(date_str_from_web, format_b)
    if date_b > date_a:
        return True
    else:
        return False

def login(driver: webdriver.Chrome, family=False):
    target_url = "https://www.instacart.com/store/account/family_orders" if family else "https://www.instacart.com/store/account/orders"
    driver.get(target_url)
    print("Waiting for user to log in manually...")
    WebDriverWait(driver, 3600).until(
        lambda d: "store/account/family_orders" in d.current_url or "store/account/orders" in d.current_url or "store/account" in d.current_url
    )
    print("Login successful! Proceeding...")

def get_orders_list(driver: webdriver.Chrome, after_str=None, family=False):
    target_url = "https://www.instacart.com/store/account/family_orders" if family else "https://www.instacart.com/store/account/orders"
    target_path = "store/account/family_orders" if family else "store/account/orders"
    # Already on the orders page from login, but reload just to be sure
    if target_path not in driver.current_url:
        driver.get(target_url)
    
    # Wait for the orders page to actually load order cards
    print("Waiting for order history to load...")
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.XPATH, "//div[@data-testid='order-card']"))
    )
    
    # Keep clicking "load more orders" until no more can be loaded (with counts-change and safety checks)
    last_card_count = 0
    click_count = 0
    max_clicks = 100 # Safety limit
    
    while click_count < max_clicks:
        cards = driver.find_elements(By.XPATH, "//div[@data-testid='order-card']")
        card_count = len(cards)
        print(f"Loaded {card_count} order cards...")
        
        if card_count == last_card_count:
            # Let's wait 3 seconds and check again to make sure it's not just a loading delay
            time.sleep(3)
            cards = driver.find_elements(By.XPATH, "//div[@data-testid='order-card']")
            if len(cards) == last_card_count:
                print("No new orders loaded. Stopping expansion.")
                break
                
        last_card_count = card_count
        
        # Try to click "load more"
        if not click_load_more():
            print("No more 'Load more orders' button found.")
            break
            
        click_count += 1
        time.sleep(2) # Give it a brief sleep to load
        
        if after_str is not None:
            cards = driver.find_elements(By.XPATH, "//div[@data-testid='order-card']")
            if cards:
                last_item_date = order_info_div_to_dict(cards[-1])["dateTime"]
                if not is_web_date_greater(after_str, last_item_date):
                    print("Reached order older than --after. Stopping scroll.")
                    break
                    
    # Find all order card elements
    cards = driver.find_elements(By.XPATH, "//div[@data-testid='order-card']")
    print(f"Scraping a total of {len(cards)} orders...")
    items = list(map(order_info_div_to_dict, cards))
    if after_str is not None:
        items = list(filter(lambda x: is_web_date_greater(after_str, x["dateTime"]), items))
    items.reverse() # Oldest first
    return items

# Function to find and click the "load more orders" button
def click_load_more():
    try:
        load_more_button = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//button/span[text()='Load more orders']"))
        )
        load_more_button.click()
        return True
    except:
        return False

def order_info_div_to_dict(order_info_div):
    order_url_p = order_info_div.find_element(By.XPATH, ".//a[contains(text(), 'View order detail')]")
    order_url = order_url_p.get_attribute("href")
    
    order_date_el = order_info_div.find_element(By.XPATH, ".//h3[contains(text(), 'Order placed')]/../p")
    date_match = re.search(r'([A-Za-z]{3,9}\s+\d{1,2}(?:,\s+\d{4})?)', order_date_el.text)
    date_str = date_match.group(1) if date_match else order_date_el.text
    order_date_text = convert_datetime(date_str)
    
    order_item_count_el = order_info_div.find_element(By.XPATH, ".//h3[contains(text(), 'Items')]/../p")
    order_item_count_text = order_item_count_el.text
    
    order_total_el = order_info_div.find_element(By.XPATH, ".//h3[contains(text(), 'Total')]/../p")
    order_total_text = order_total_el.text.replace('$', '').strip()
    
    cancelled = "cancelled" in order_date_el.text.lower() or "cancelled" in order_info_div.text.lower()
    
    return {
        "dateTime": order_date_text,
        "itemCount": order_item_count_text,
        "total": order_total_text,
        "url": order_url,
        "cancelled": cancelled
    }

def get_order_details(driver: webdriver.Chrome, order_url: str):
    driver.get(order_url)
    show_items_button = WebDriverWait(driver, 3600).until( # A very long wait to allow CloudFlare bot detection time to finish
        EC.element_to_be_clickable((By.ID, "order-status-items-card"))
    )
    show_items_button.click()
    delivery_photo_url = None
    try:
        delivery_photo_url = driver.find_element(By.XPATH, "//img[contains(@src, 'orderdeliveryphoto')]").get_attribute("src")
    except:
        pass
    
    # Wait for the expanded items list to load
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//div[@id='items-card-expanded']//ul/li/ul/li/div"))
    )
    
    return {
        "delivery_photo_url": delivery_photo_url,
        "items": list(map(item_info_div_to_dict, driver.find_elements(By.XPATH, "//div[@id='items-card-expanded']//ul/li/ul/li/div")))
    }

def item_info_div_to_dict(item_info_div):
    # Thumbnail
    try:
        item_thumbnail_url = item_info_div.find_element(By.XPATH, ".//img").get_attribute("src")
    except:
        item_thumbnail_url = None
        
    # Name
    item_name = item_info_div.find_element(By.XPATH, ".//h3").text.strip()
    
    # Unit Info
    unit_p = item_info_div.find_element(By.XPATH, ".//p[contains(text(), '•')]")
    item_unit_info = [s.strip() for s in unit_p.text.split("•")]
    item_unit_price = item_unit_info[0].replace('$', '').strip()
    item_unit_description = item_unit_info[1]
    
    # Quantity
    qty_p = item_info_div.find_element(By.XPATH, ".//p[not(contains(text(), '•'))]")
    qty_text = qty_p.text.replace("Quantity:", "").replace("Qty:", "").strip()
    
    return {
        "name": item_name,
        "unitPrice": item_unit_price,
        "unitDescription": item_unit_description,
        "quantity": qty_text,
        "thumbnailUrl": item_thumbnail_url
    }

# Main function
if __name__ == "__main__":
    # Validate arguments
    output_path=""
    after_str=None
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', help='Where to save the output (can be an existing file for incremental scraping)')
    parser.add_argument('--after', help='A \'Y-m-d H:M\' string to filter out orders older than a certain date/time')
    parser.add_argument('--family', action='store_true', help='Scrape family orders instead of personal orders')
    args = parser.parse_args()
    if args.file:
        output_path = args.file
    if args.after:
        after_str = args.after

    # Grab existing data if any and ensure you don't repeat orders
    existing_orders=[]
    if (output_path):
        if os.path.exists(output_path):
            with open(output_path, 'r') as file:
                json_array = json.load(file)
                existing_orders += json_array
    if (len(existing_orders) > 0):
        if after_str is not None:
            raise "You cant use the '--after' argment with an existing orders list!"
        after_str = existing_orders[len(existing_orders) - 1]["dateTime"]
        print("You have pointed to an existing orders list. Only orders after " + after_str + " will be scraped.")

    # Setup Webdriver and load env. vars.
    load_dotenv()
    options = webdriver.ChromeOptions()
    # Support macOS Chrome profile directory to persist login session
    dataDir = f"/Users/{getpass.getuser()}/Library/Application Support/Google/Chrome/SeleniumInstacart"
    os.makedirs(os.path.dirname(dataDir), exist_ok=True)
    options.add_argument(f"--user-data-dir={dataDir}")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(options=options)
    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
        )

    # Scrape data
    login(driver=driver, family=args.family)
    time.sleep(random.randint(5, 15))
    orders = get_orders_list(driver=driver, after_str=after_str, family=args.family)
    for order in orders:
        time.sleep(random.randint(5, 15)) # Helps with bot detection
        order_details = get_order_details(driver=driver, order_url=order["url"])
        order["items"] = order_details["items"]
        order["deliveryPhotoUrl"] = order_details["delivery_photo_url"]
    driver.quit()
    orders = existing_orders + orders

    # Output
    report = json.dumps(orders, indent=4)
    print(report)
    if output_path:
        with open(output_path, 'w') as f:
            f.write(report)