# This is the main entry point for the AWS Lambda function.
# It orchestrates the data pipeline by importing and calling functions
# from the other two scripts.

import os
from datetime import datetime

# Import the functions from the other scripts
from fetch_hn_data import get_processed_ids, fetch_new_story_details
from embed_and_upsert import process_stories

def handler(event, context):
    """
    AWS Lambda handler function.
    """
    print(f"Pipeline started at: {datetime.utcnow().isoformat()}")

    # --- Step 1: Fetch new story details ---
    print("--- Phase 1: Fetching new stories ---")

    # Get a set of already processed IDs from the database
    processed_ids = get_processed_ids()
    if processed_ids is None:
        # This indicates a database connection failure
        return {"statusCode": 500, "body": "Failed to connect to database."}

    # Fetch details for stories that are not in the processed set
    new_stories = fetch_new_story_details(processed_ids)

    if not new_stories:
        print("No new stories to process. Exiting.")
        return {"statusCode": 200, "body": "No new stories to process."}

    print(f"Found {len(new_stories)} new stories to process.")

    # --- Step 2: Process and upsert the new stories ---
    print("--- Phase 2: Processing and upserting stories ---")
    process_stories(new_stories)

    print(f"Pipeline finished successfully at: {datetime.utcnow().isoformat()}")
    return {"statusCode": 200, "body": "Pipeline completed successfully."}
