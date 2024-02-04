import os
import json
from dotenv import load_dotenv
import tkinter as tk
from datetime import datetime
import argparse
import random
import time

from selenium import webdriver
from selenium_stealth import stealth

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC\

# Parse an output file argument if any
output_path=""
parser = argparse.ArgumentParser()
parser.add_argument('--output', help='Where to save the output JSON')
args = parser.parse_args()
if args.output:
    output_path = args.output

# Function to get the screen width and height
def get_screen_dimensions():
    root = tk.Tk()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    root.destroy()
    return screen_width, screen_height

# Convert a date/time string from 'Jan 30, 2024, 6:23 PM' format to '2024-01-30 18:23' format.
def convert_datetime(input_string):
    input_datetime = datetime.strptime(input_string, '%b %d, %Y, %I:%M %p')
    output_string = input_datetime.strftime('%Y-%m-%d %H:%M')
    return output_string

def login(driver: webdriver.Chrome):
    driver.get("https://www.instacart.ca/store/account")
    email = os.getenv("INSTACART_EMAIL")
    password = os.getenv("INSTACART_PASSWORD")
    if (email and password): # If not defined, you can login manually
        email_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Email']")))
        password_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Password']")))
        login_button = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//button/span[text()='Log in']")))
        email_input.send_keys(email)
        password_input.send_keys(password)
        login_button.click()
    WebDriverWait(driver, 3600).until(EC.url_changes(driver.current_url)) # Long timeout needed for manual login or occasional CAPTCHA

def get_orders_list(driver: webdriver.Chrome):
    driver.get("https://www.instacart.ca/store/account/orders")
    # Keep clicking "load more orders" until no more can be loaded
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    while click_load_more():
        pass
    # Find all 'li' elements with 'data-radium' attribute equal to 'true' and save their inner HTML to an array
    return list(map(order_info_div_to_dict, driver.find_elements(By.XPATH, "//li[@data-radium='true']/div[1]")))

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
    order_url = order_info_div.find_element(By.XPATH, "./a").get_attribute("href")
    order_date_text = convert_datetime(order_info_div.find_element(By.XPATH, "./div/div[1]/p[2]").text)
    order_item_count_text = order_info_div.find_element(By.XPATH, "./div/div[2]/p[2]").text
    cancelled = False
    try:
        order_info_div.find_element(By.XPATH, "./div/div[1]/p[3]").text
        cancelled = True
    except:
        pass
    order_total_text = order_info_div.find_element(By.XPATH, "./div/div[3]/p[2]").text[1:]
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
    return {
        "delivery_photo_url": delivery_photo_url,
        "items": list(map(item_info_div_to_dict, driver.find_elements(By.XPATH, "//div[@id='items-card-expanded']/ul/li/div")))
    }

def item_info_div_to_dict(item_info_div):
    item_thumbnail_url = item_info_div.find_element(By.XPATH, "./div[1]/button/span/img").get_attribute("src")
    item_name = item_info_div.find_element(By.XPATH, "./div[1]/div/button/span").text
    item_unit_info = [s.strip() for s in item_info_div.find_element(By.XPATH, "./div[1]/div/p").text.split("•")]
    item_quantity = item_info_div.find_element(By.XPATH, "./div[2]/p").text
    item_unit_price = item_unit_info[0][1:]
    item_unit_description = item_unit_info[1]
    return {
        "name": item_name,
        "unitPrice": item_unit_price,
        "unitDescription": item_unit_description,
        "quantity": item_quantity,
        "thumbail_url": item_thumbnail_url
    }

# Main function
if __name__ == "__main__":
    # Setup
    load_dotenv()
    screen_width, screen_height = get_screen_dimensions()
    window_width = screen_width // 2
    window_height = screen_height
    options = webdriver.ChromeOptions()
    options.add_argument(f"window-size={window_width},{window_height}")
    options.add_argument(f"window-position={screen_width},0")
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
    login(driver=driver)
    time.sleep(random.randint(5, 15))
    orders = get_orders_list(driver=driver)
    for order in orders:
        time.sleep(random.randint(5, 15)) # Helps with bot detection
        order_details = get_order_details(driver=driver, order_url=order["url"])
        order["items"] = order_details["items"]
        order["delivery_photo_url"] = order_details["delivery_photo_url"]
    driver.quit()
    
    # Output
    report = json.dumps(orders, indent=4)
    print(report)
    if output_path:
        with open(output_path, 'w') as f:
            f.write(report)