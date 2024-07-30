import requests
from datetime import datetime, date, timedelta
import json
from weds import webflow_bearer_token

def get_electricity_api_url(date_str, zone):
    return f"https://www.hvakosterstrommen.no/api/v1/prices/{date_str}_{zone}.json"

webflow_url = "https://api.webflow.com/v2/collections/66a893a3183d43c3d13be876/items/66a893d8f13ec38e2f6f853f/live"

def get_electricity_prices(date_str, zone):
    url = get_electricity_api_url(date_str, zone)
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        # Add VAT to all prices except for NO4
        for item in data:
            if zone != "NO4":
                item['NOK_per_kWh'] *= 1.25  # Add 25% VAT
        return data
    else:
        print(f"Failed to retrieve electricity data for {zone} on {date_str}. Status code: {response.status_code}")
        return None

def calculate_average_price(prices):
    if not prices:
        return None
    return sum(item['NOK_per_kWh'] for item in prices) / len(prices)

def update_webflow_item(field_data):
    payload = {
        "isArchived": False,
        "isDraft": False,
        "fieldData": field_data
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {webflow_bearer_token}"
    }
    response = requests.patch(webflow_url, json=payload, headers=headers)
    if response.status_code == 200:
        print("Webflow item updated successfully")
    else:
        print(f"Failed to update Webflow item. Status code: {response.status_code}")
        print(response.text)

def main():
    today = date.today()
    yesterday = today - timedelta(days=1)
    today_str = today.strftime("%Y/%m-%d")
    yesterday_str = yesterday.strftime("%Y/%m-%d")

    zones = ["NO1", "NO2", "NO3", "NO4", "NO5"]
    field_data = {
        "name": "Zone",
        "slug": "zone"
    }

    for zone in zones:
        today_prices = get_electricity_prices(today_str, zone)
        yesterday_prices = get_electricity_prices(yesterday_str, zone)

        if not today_prices or not yesterday_prices:
            continue

        today_avg = calculate_average_price(today_prices)
        yesterday_avg = calculate_average_price(yesterday_prices)

        if today_avg is None or yesterday_avg is None:
            continue

        percent_change = ((today_avg - yesterday_avg) / yesterday_avg) * 100
        zone_number = zone[2]

        field_data[f"sone{zone_number}"] = f"{today_avg:.2f}"
        
        # Adjust the sign and color based on price change
        if percent_change > 0:
            change_sign = "+"
            color = "#ff5722"  # Red for price increase
        else:
            change_sign = "-"
            color = "#4caf50"  # Green for price decrease or no change
        
        field_data[f"sone{zone_number}-prosentendring-yesterday"] = f"{change_sign}{abs(percent_change):.2f}%"
        
        # Use the correct field name for each zone
        if zone_number == "1":
            field_data[f"sone{zone_number}-yesterday-color"] = color
        else:
            field_data[f"sone{zone_number}-yesterday-colo"] = color

    # Update Webflow item
    update_webflow_item(field_data)

    # Print the updated data
    print("Updated Webflow item with the following data:")
    print(json.dumps(field_data, indent=2))

if __name__ == "__main__":
    main()