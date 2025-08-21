# data-pipeline/scripts/01_fetch_hn_data.py

import requests
import json
import time
import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path='../.env')

# --- Configuration ---
TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
ITEM_URL_TEMPLATE = "https://hacker-news.firebaseio.com/v0/item/{}.json"
STORIES_LIMIT = 30
OUTPUT_FILENAME = "hn_stories.json"

# --- Database Connection ---
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

def fetch_processed_ids_from_db(conn):
    """Fetches all story_ids from the processed_stories table."""
    print("Fetching already processed story IDs from the database...")
    processed_ids = set()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT story_id FROM processed_stories")
            rows = cur.fetchall()
            for row in rows:
                processed_ids.add(row[0])
        print(f"Found {len(processed_ids)} processed IDs in the database.")
    except psycopg2.Error as e:
        print(f"Database error fetching processed IDs: {e}")
    return processed_ids

# --- Main Logic (largely the same, but uses DB) ---
def fetch_top_story_ids():
    """Fetches a list of top story IDs from the Hacker News API."""
    print("Fetching top story IDs from Hacker News API...")
    try:
        response = requests.get(TOP_STORIES_URL)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching story IDs: {e}")
        return []

def fetch_story_details(story_id):
    """Fetches the details of a single story given its ID."""
    item_url = ITEM_URL_TEMPLATE.format(story_id)
    try:
        response = requests.get(item_url)
        response.raise_for_status()
        story_data = response.json()
        if story_data and story_data.get("type") == "story" and story_data.get("url"):
            return {"id": story_data.get("id"), "title": story_data.get("title"), "url": story_data.get("url")}
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching details for story ID {story_id}: {e}")
        return None

def main():
    """Main function to fetch and save ONLY new story data."""
    conn = get_db_connection()
    if not conn:
        return

    processed_ids = fetch_processed_ids_from_db(conn)
    all_top_ids = fetch_top_story_ids()

    if not all_top_ids:
        print("No story IDs fetched from HN API. Exiting.")
        conn.close()
        return

    # Filter out already processed stories
    new_story_ids = [id for id in all_top_ids if id not in processed_ids]

    if not new_story_ids:
        print("No new stories to process. Exiting.")
        conn.close()
        return

    limited_new_ids = new_story_ids[:STORIES_LIMIT]
    print(f"\nFound {len(new_story_ids)} new stories. Processing up to {len(limited_new_ids)}...")

    new_stories_details = []
    for i, story_id in enumerate(limited_new_ids):
        print(f"  ({i+1}/{len(limited_new_ids)}) Fetching details for new story ID: {story_id}")
        details = fetch_story_details(story_id)
        if details:
            new_stories_details.append(details)
        time.sleep(0.1)

    print(f"\nSuccessfully fetched details for {len(new_stories_details)} new valid stories.")

    if new_stories_details:
        try:
            with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
                json.dump(new_stories_details, f, indent=4, ensure_ascii=False)
            print(f"Data for new stories successfully saved to {OUTPUT_FILENAME}")
        except IOError as e:
            print(f"Error saving data to file: {e}")

    conn.close()

if __name__ == "__main__":
    main()
