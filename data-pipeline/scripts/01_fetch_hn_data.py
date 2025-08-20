import requests
import json
import time

# --- Configuration ---
# The Hacker News API endpoint for top story IDs.
TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
# The base URL for fetching individual item details.
ITEM_URL_TEMPLATE = "https://hacker-news.firebaseio.com/v0/item/{}.json"
# The number of top stories to fetch for our v0.
STORIES_LIMIT = 30
# The name of the output file where we'll save our data.
OUTPUT_FILENAME = "hn_stories.json"

def fetch_top_story_ids():
    """
    Fetches a list of top story IDs from the Hacker News API.
    """
    print("Fetching top story IDs...")
    try:
        response = requests.get(TOP_STORIES_URL)
        # Raise an exception if the request was unsuccessful (e.g., 404, 500).
        response.raise_for_status()
        story_ids = response.json()
        print(f"Successfully fetched {len(story_ids)} story IDs.")
        return story_ids
    except requests.exceptions.RequestException as e:
        print(f"Error fetching story IDs: {e}")
        return []

def fetch_story_details(story_id):
    """
    Fetches the details of a single story given its ID.
    Returns a dictionary with title and url, or None if it's not a story with a URL.
    """
    item_url = ITEM_URL_TEMPLATE.format(story_id)
    try:
        response = requests.get(item_url)
        response.raise_for_status()
        story_data = response.json()

        # We only want to process items that are actual stories and have a URL.
        # This filters out "Ask HN", "Show HN" without URLs, jobs, etc.
        if story_data and story_data.get("type") == "story" and story_data.get("url"):
            return {
                "id": story_data.get("id"),
                "title": story_data.get("title"),
                "url": story_data.get("url")
            }
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching details for story ID {story_id}: {e}")
        return None

def main():
    """
    Main function to orchestrate fetching and saving story data.
    """
    story_ids = fetch_top_story_ids()

    if not story_ids:
        print("No story IDs fetched. Exiting.")
        return

    # Limit the number of stories for our v0 prototype.
    limited_story_ids = story_ids[:STORIES_LIMIT]
    print(f"\nProcessing the top {len(limited_story_ids)} stories...")

    stories_with_details = []
    for i, story_id in enumerate(limited_story_ids):
        print(f"  ({i+1}/{len(limited_story_ids)}) Fetching details for story ID: {story_id}")
        details = fetch_story_details(story_id)
        if details:
            stories_with_details.append(details)
        # A small delay to be polite to the API.
        time.sleep(0.1)

    print(f"\nSuccessfully fetched details for {len(stories_with_details)} valid stories.")

    # Save the collected data to a JSON file.
    try:
        with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
            json.dump(stories_with_details, f, indent=4, ensure_ascii=False)
        print(f"Data successfully saved to {OUTPUT_FILENAME}")
    except IOError as e:
        print(f"Error saving data to file: {e}")

# This ensures the main function is called when the script is executed.
if __name__ == "__main__":
    main()
