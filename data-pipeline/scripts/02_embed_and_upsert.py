# data-pipeline/scripts/02_embed_and_upsert.py

import os
import json
import time
import requests
import psycopg2
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path='../.env')

# --- Configuration ---
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "YOUR_PINECONE_API_KEY")
PINECONE_INDEX_NAME = "hn-rag-v0"
EMBEDDING_MODEL = 'nomic-ai/nomic-embed-text-v1.5'
MODEL_DIMENSION = 768
INPUT_FILENAME = "hn_stories.json"

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

def mark_story_as_processed_in_db(conn, story_id):
    """Inserts a story_id into the processed_stories table."""
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO processed_stories (story_id, created_at, updated_at) VALUES (%s, NOW(), NOW()) ON CONFLICT (story_id) DO NOTHING", (story_id,))
        conn.commit()
    except psycopg2.Error as e:
        print(f"Database error marking story {story_id} as processed: {e}")
        conn.rollback() # Rollback the transaction on error

# --- Service Initialization (same as before) ---
def initialize_pinecone():
    """Initializes and returns a Pinecone client and index object."""
    print("Initializing Pinecone...")
    pc = Pinecone(api_key=PINECONE_API_KEY)
    if PINECONE_INDEX_NAME not in pc.list_indexes().names():
        print(f"Creating new Pinecone index '{PINECONE_INDEX_NAME}'...")
        pc.create_index(name=PINECONE_INDEX_NAME, dimension=MODEL_DIMENSION, metric="cosine", spec=ServerlessSpec(cloud='aws', region='us-east-1'))
        while not pc.describe_index(PINECONE_INDEX_NAME).status['ready']: time.sleep(1)
    index = pc.Index(PINECONE_INDEX_NAME)
    time.sleep(1)
    print("Pinecone initialized.")
    return index

def initialize_embedding_model():
    """Initializes and returns the sentence-transformer model."""
    print(f"Loading embedding model: {EMBEDDING_MODEL}...")
    model = SentenceTransformer(EMBEDDING_MODEL, trust_remote_code=True)
    print("Embedding model loaded.")
    return model

# --- Data Processing (same as before) ---
def load_stories():
    """Loads the story data from the JSON file."""
    try:
        with open(INPUT_FILENAME, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Note: {INPUT_FILENAME} not found. This is expected if there were no new stories.")
        return []

def scrape_article_text(url):
    """Scrapes the main textual content from a given article URL."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        main_content_tags = soup.find_all(['article', 'main', 'p'])
        if not main_content_tags: return ' '.join(soup.get_text().split())
        text_parts = [tag.get_text(separator=' ', strip=True) for tag in main_content_tags]
        return ' '.join(' '.join(text_parts).split())
    except requests.exceptions.RequestException as e:
        print(f"  -> Failed to scrape {url}: {e}")
        return None

def chunk_text(text, chunk_size=512, overlap=50):
    """Splits a long text into smaller, overlapping chunks."""
    if not text: return []
    words = text.split()
    return [' '.join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size - overlap)]

# --- Main Execution Logic ---
def main():
    """Main function to run the embedding and upserting pipeline."""
    stories = load_stories()
    if not stories:
        print("No new stories to process. Exiting.")
        return

    conn = get_db_connection()
    if not conn: return

    pinecone_index = initialize_pinecone()
    model = initialize_embedding_model()

    print("\n--- Starting to process and embed new stories ---")
    total_chunks_upserted = 0

    for i, story in enumerate(stories):
        story_id, story_title, story_url = story['id'], story['title'], story['url']
        print(f"\n({i+1}/{len(stories)}) Processing: {story_title}")
        print(f"  -> URL: {story_url}")

        article_text = scrape_article_text(story_url)
        if not article_text:
            print("  -> Skipping due to scraping failure.")
            continue

        text_chunks = chunk_text(article_text)
        if not text_chunks:
            print("  -> Skipping as no text chunks were generated.")
            continue

        print(f"  -> Generated {len(text_chunks)} text chunks. Generating embeddings...")
        try:
            embeddings = model.encode(text_chunks, show_progress_bar=False).tolist()
        except Exception as e:
            print(f"  -> Error encoding text chunks: {e}")
            continue

        # Prepare vectors for Pinecone upsert
        vectors_to_upsert = []
        for j, chunk in enumerate(text_chunks):
            vector_id = f"{story_id}-{j}"
            metadata = {
                "story_id": story_id,
                "story_title": story_title,
                "story_url": story_url,
                "chunk_index": j,
                "text": chunk
            }
            vectors_to_upsert.append({
                "id": vector_id,
                "values": embeddings[j],
                "metadata": metadata
            })

        # Upsert the vectors in batches to Pinecone
        if vectors_to_upsert:
            print(f"  -> Upserting {len(vectors_to_upsert)} vectors to Pinecone...")
            try:
                pinecone_index.upsert(vectors=vectors_to_upsert)
                total_chunks_upserted += len(vectors_to_upsert)
                # If upsert is successful, mark this story as processed in our database
                mark_story_as_processed_in_db(conn, story_id)
                print(f"  -> Successfully marked story {story_id} as processed.")
            except Exception as e:
                print(f"  -> Error upserting to Pinecone: {e}")

    print(f"\n--- Pipeline Finished ---")
    print(f"Total new chunks upserted to Pinecone: {total_chunks_upserted}")

    conn.close()

if __name__ == "__main__":
    main()
