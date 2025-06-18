# menu_crawler.py
import requests
import json
import datetime
import time
import os
from collections import defaultdict

API_URL = "https://api.dailypace.de/api/foodfinder/list"
API_KEY = os.environ.get('PACE_API_KEY') # Read API key from environment variable

if not API_KEY:
    print("Error: PACE_API_KEY environment variable not set.")
    exit(1)

HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    # ... (include all other headers from your previous example)
    "apiKey": API_KEY,
}

# --- Directory Setup ---
RAW_DATA_DIR = "raw_data"
DB_FILE = "menu_database.json"

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def fetch_menu_data():
    """Fetches the raw menu data from the API."""
    timestamp = int(time.time() * 1000)
    params = {"_": timestamp}
    try:
        response = requests.get(API_URL, headers=HEADERS, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def save_raw_data(data):
    """Saves the full raw JSON response, timestamped."""
    ensure_dir(RAW_DATA_DIR)
    now = datetime.datetime.now()
    filename = os.path.join(RAW_DATA_DIR, f"{now.strftime('%Y-%m-%d_%H-%M-%S')}_raw_menu.json")
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Raw data saved to {filename}")
    except IOError as e:
        print(f"Error saving raw data to {filename}: {e}")

def create_clean_db(raw_data, outlets_of_interest):
    """Creates a clean JSON structure for specified outlets."""
    if not raw_data or "data" not in raw_data:
        return {}

    # { "outlet_name": { "date": { "mealtime": [items] } } }
    clean_db_structure = {outlet: defaultdict(lambda: defaultdict(list)) for outlet in outlets_of_interest}

    for item in raw_data["data"]:
        outlet = item.get("outlet")
        if outlet in outlets_of_interest:
            date_str = item.get("date")
            mealtime = item.get("mealtime", "N/A")
            
            # Extract only desired fields for the clean DB
            menu_item_details = {
                "id": item.get("id"),
                "item_id": item.get("itemId"), # For potential future linking
                "recipe_id": item.get("RecipeID"),
                "description_de": item.get("GastDesc_de"),
                "description_en": item.get("GastDesc_en"),
                "category": item.get("MenuName"),
                "price": item.get("ProductPrice"),
                "price_2": item.get("ProductPrice_2"), # If applicable
                "allergens": item.get("allergene"),
                "attributes": item.get("merkmale"), # e.g., vegan, vegetarian
                "nutrition": item.get("naehrstoffe"),
                "additives": item.get("zusatzstoffe"),
                "co2_value": item.get("CO2Value"),
                "co2_rating": item.get("CO2Rating"),
                "print_order": item.get("PrintOrder")
            }
            clean_db_structure[outlet][date_str][mealtime].append(menu_item_details)

    # Sort items within each mealtime by PrintOrder (if it exists and is numeric)
    for outlet_data in clean_db_structure.values():
        for date_data in outlet_data.values():
            for mealtime_items in date_data.values():
                mealtime_items.sort(key=lambda x: int(x.get("print_order", 0)) if str(x.get("print_order", 0)).isdigit() else 0)
                
    return clean_db_structure

def save_clean_db(data):
    """Saves the clean database to a JSON file."""
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Clean database saved to {DB_FILE}")
    except IOError as e:
        print(f"Error saving clean DB to {DB_FILE}: {e}")

# --- Main Execution ---
if __name__ == "__main__":
    outlets_to_crawl = ["canteen", "journalistenclub"]
    
    print(f"[{datetime.datetime.now()}] Starting menu crawl...")
    raw_menu_data = fetch_menu_data()

    if raw_menu_data:
        print("Saving raw data...")
        save_raw_data(raw_menu_data) # Save the complete raw response

        print("Creating and saving clean database...")
        clean_database = create_clean_db(raw_menu_data, outlets_to_crawl)
        save_clean_db(clean_database)
        
        print(f"[{datetime.datetime.now()}] Process completed successfully.")
    else:
        print(f"[{datetime.datetime.now()}] Failed to fetch or process data.")