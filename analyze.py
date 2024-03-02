import json
import sys
import re
import argparse
from collections import defaultdict
from datetime import datetime
from statistics import mean
from fuzzywuzzy import fuzz
from functools import cmp_to_key

def trim_common_prefix_word(string1, string2):
    words1 = string1.split()
    words2 = string2.split()
    prefix_length = 0
    for word1, word2 in zip(words1, words2):
        if word1 == word2:
            prefix_length += 1
        else:
            break
    common_prefix = ' '.join(words1[:prefix_length])
    trimmed_string1 = ' '.join(words1[prefix_length:])
    trimmed_string2 = ' '.join(words2[prefix_length:])
    return common_prefix, trimmed_string1, trimmed_string2

if __name__ == "__main__":
    # Validate arguments
    selection_mode=False
    after_date=None
    after_date_message=''
    parser = argparse.ArgumentParser()
    parser.add_argument('file_path', metavar='file_path', type=str, nargs='?', help='Input file path')
    parser.add_argument('--select', action='store_true', help='If defined, show a single-product selection menu and print the results instead of saving to CSV')
    parser.add_argument('--after', help='A \'Y-m-d H:M\' string to filter out orders older than a certain date/time')
    args = parser.parse_args()
    if args.select:
        selection_mode = args.select
    if args.file_path:
        file_path = args.file_path
    if args.after:
        after_date = datetime.strptime(args.after, '%Y-%m-%d %H:%M')
        after_date_message = f" (after {args.after})"

    # Read the JSON file
    with open(file_path, 'r') as file:
        original_orders = json.load(file)

    # Extract item information from orders
    item_info = defaultdict(list)
    item_prices = defaultdict(list)
    orders = []
    for order in original_orders:
        if order["cancelled"] is True:
            continue
        if after_date is not None:
            if datetime.strptime(order['dateTime'], '%Y-%m-%d %H:%M') <= after_date:
                continue
        orders.append(order)
    for order in orders:
        for item in order['items']:
            item_identifier = (item['name'], item['unitDescription'])
            item_info[item_identifier].append(float(re.sub(r'[^0-9.]', '', item['quantity'])))
            item_prices[item_identifier].append((order['dateTime'], float(re.sub(r'[^0-9.]', '', item['unitPrice']))))

    # Create a list of unique items and order them based on string similarity (trying to ignore common prefixes as they are typically brand names)
    unique_items = sorted(list(item_info.keys()), key=lambda x: x[0])
    temp = []
    num_items = len(unique_items)
    if num_items > 1:
        for i in range(0, num_items - 1):
            if len(temp) > 0 and temp[len(temp) - 1][0] + temp[len(temp) - 1][1] == unique_items[i][0] + unique_items[i][1]:
                continue
            trimmed_prefix, trimmed_item, trimmed_next_item = trim_common_prefix_word(unique_items[i][0], unique_items[i+1][0])
            if (len(trimmed_prefix) > 0):
                temp.append((unique_items[i][0], unique_items[i][1], trimmed_item))
                temp.append((unique_items[i+1][0], unique_items[i+1][1], trimmed_next_item))
            else:
                temp.append((unique_items[i][0], unique_items[i][1], unique_items[i][0]))
    unique_items = sorted(
        sorted(temp, key=lambda x: x[2]),
        key=cmp_to_key(lambda item1, item2: fuzz.partial_ratio(item1[2], item2[2]))
    )

    def analyze_item(selected_item):
        # Calculate total units ordered
        total_units_ordered = sum(item_info[selected_item])

        # Calculate average units per month
        order_dates = [datetime.strptime(order['dateTime'], '%Y-%m-%d %H:%M') for order in orders]
        months_diff = (max(order_dates).year - min(order_dates).year) * 12 + max(order_dates).month - min(order_dates).month
        average_units_per_month = total_units_ordered / months_diff

        # Calculate average units per order
        average_units_per_order = total_units_ordered / len(orders)

        # Calculate price fluctuations
        prices = item_prices[selected_item]
        price_changes = [(prices[i][0], prices[i][1] - prices[i - 1][1]) for i in range(1, len(prices)) if prices[i][1] != prices[i - 1][1]]
        return total_units_ordered, average_units_per_month, average_units_per_order, price_changes

    if (selection_mode):
        # Display the ordered list of unique items
        print("List of unique items (ordered by similarity):")
        for index, item in enumerate(unique_items, start=1):
            print(f"{index}. {item[0]} - {item[1]}")

        # Choose an item
        item_choice = int(input("Select an item by entering its number: ")) - 1
        selected_item = (unique_items[item_choice][0], unique_items[item_choice][1])

        total_units_ordered, average_units_per_month, average_units_per_order, price_changes = analyze_item(selected_item=selected_item)

        # Print results
        print(f"\n{selected_item[0]} - {selected_item[1]}:")
        print(f"    Total units ordered: {total_units_ordered}")
        print(f"    Average units per month: {average_units_per_month:.2f}")
        print(f"    Average units per order: {average_units_per_order:.2f}")
        if price_changes:
            print("    Price fluctuations:")
            for change in price_changes:
                if change[1] > 0:
                    print(f"        +${change[1]:.2f} on {change[0]}")
                else:
                    print(f"        -${-change[1]:.2f} on {change[0]}")
        else:
            print("No price fluctuation data available.")
    else:
        report_csv=f"\"Product Name{after_date_message}\",\"Unit Description\",\"Total Units Ordered\",\"Average Units Per Month\",\"Average Units Per Order\",\"Price Fluctuations\""
        results = []
        for item in unique_items:
            total_units_ordered, average_units_per_month, average_units_per_order, price_changes = analyze_item((item[0], item[1]))
            results.append((item[0], item[1], total_units_ordered, average_units_per_month, average_units_per_order, price_changes))
        results = sorted(
            results,
            key=cmp_to_key(lambda r1, r2: r2[3] - r1[3]) # For the report, sort by units per month descending
        )
        for result in results:
            item_name = result[0].replace('"', '')
            item_unit_description = result[1].replace('"', '')
            total_units_ordered = result[2]
            average_units_per_month = result[3]
            average_units_per_order = result[4]
            price_changes = result[5]
            price_change_string = ""
            if price_changes:
                for change in price_changes:
                    if len(price_change_string) > 0:
                        price_change_string += ", "
                    if change[1] > 0:
                        price_change_string += f"+${change[1]:.2f} on {change[0]}"
                    else:
                        price_change_string += f"-${-change[1]:.2f} on {change[0]}"
            report_csv += f"\n\"{item_name}\", \"{item_unit_description}\", \"{total_units_ordered}\", \"{average_units_per_month}\", \"{average_units_per_order}\", \"{price_change_string}\""
        output_file = f"{file_path}.analysis.csv"
        with open(output_file, 'w') as f:
            f.write(report_csv)
        print(f"Report saved: {output_file}")
