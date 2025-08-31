import os
import requests
import psycopg2
import time
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path='../.env')

HN_TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL_TEMPLATE = "https://hacker-news.firebaseio.com/v0/item/{}.json"

def get_db_connection():
    """Establishes and returns a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        return conn
    except psycopg2.OperationalError as e:
        print(f"Error connecting to the database: {e}")
        return None

def get_processed_ids():
    """Fetches a set of already processed story IDs from the database."""
    conn = get_db_connection()
    if not conn:
        return None  # Indicate failure

    processed_ids = set()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT story_id FROM processed_stories")
            rows = cur.fetchall()
            for row in rows:
                processed_ids.add(row[0])
        print(f"Found {len(processed_ids)} already processed story IDs.")
    except psycopg2.Error as e:
        print(f"Error fetching processed IDs: {e}")
        return None
    finally:
        conn.close()
    return processed_ids

def fetch_new_story_details(processed_ids):
    """Fetches top story IDs from HN and returns details for new stories."""
    print("Fetching top story IDs from Hacker News API...")
    try:
        response = requests.get(HN_TOP_STORIES_URL)
        response.raise_for_status()
        all_top_ids = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching top story IDs: {e}")
        return []

    new_story_ids = [id for id in all_top_ids if id not in processed_ids]

    if not new_story_ids:
        return []

    stories_to_process = []
    # Limit to 30 new stories per run
    for story_id in new_story_ids[:30]:
        try:
            item_url = HN_ITEM_URL_TEMPLATE.format(story_id)
            item_response = requests.get(item_url)
            item_response.raise_for_status()
            story_data = item_response.json()

            if story_data and story_data.get("type") == "story" and story_data.get("url"):
                stories_to_process.append({
                    "id": story_data["id"],
                    "title": story_data["title"],
                    "url": story_data["url"]
                })
            time.sleep(0.1) # Be polite to the API
        except requests.exceptions.RequestException as e:
            print(f"Error fetching details for story {story_id}: {e}")
            continue

    return stories_to_process

# This block allows the script to be run directly for local testing.
# It simulates the old behavior of writing to a JSON file.
if __name__ == "__main__":
    print("Running data fetching script directly for local testing...")
    processed_ids_set = get_processed_ids()
    if processed_ids_set is not None:
        new_stories_list = fetch_new_story_details(processed_ids_set)
        if new_stories_list:
            print(f"Found {len(new_stories_list)} new stories. Saving to hn_stories.json")
            with open("hn_stories.json", 'w', encoding='utf-8') as f:
                json.dump(new_stories_list, f, indent=4, ensure_ascii=False)
        else:
            print("No new stories found.")
