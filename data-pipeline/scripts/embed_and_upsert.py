import os
import json
import time
import requests
import psycopg2
import random
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path='../.env')

# --- CONFIGURATION ---
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "YOUR_PINECONE_API_KEY")
PINECONE_INDEX_NAME = "hn-rag-v0"
EMBEDDING_MODEL = 'nomic-ai/nomic-embed-text-v1.5'
MODEL_DIMENSION = 768

USER_AGENT_LIST = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
]

# --- HELPER FUNCTIONS ---
def get_db_connection():
    # ... (Same as in fetch_hn_data.py) ...
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

def mark_story_as_processed(story_id):
    """Inserts a story ID into the processed_stories table."""
    conn = get_db_connection()
    if not conn:
        print(f"Cannot mark story {story_id}: No DB connection.")
        return

    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO processed_stories (story_id, created_at, updated_at) VALUES (%s, NOW(), NOW()) ON CONFLICT (story_id) DO NOTHING", (story_id,))
            conn.commit()
            print(f"-> Successfully marked story {story_id} as processed.")
    except psycopg2.Error as e:
        print(f"Error marking story {story_id} as processed: {e}")
        conn.rollback()
    finally:
        conn.close()

def scrape_article_text(url):
    """Scrapes the main text content from a given URL."""
    try:
        headers = {'User-Agent': random.choice(USER_AGENT_LIST)}
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()
        text = ' '.join(t.strip() for t in soup.stripped_strings)
        return text if text else None
    except requests.RequestException as e:
        print(f"-> Failed to scrape {url}: {e}")
        return None

def chunk_text(text, chunk_size=512, overlap=50):
    """Splits text into overlapping chunks."""
    if not text: return []
    words = text.split()
    return [' '.join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size - overlap)]

# --- MAIN PROCESSING FUNCTION ---
def process_stories(stories_list):
    """Takes a list of stories, scrapes, embeds, and upserts them."""
    if not stories_list:
        print("No stories provided to process.")
        return

    print("Loading embedding model...")
    model = SentenceTransformer(EMBEDDING_MODEL, trust_remote_code=True)
    print("Embedding model loaded.")

    pc = Pinecone(api_key=PINECONE_API_KEY)
    if PINECONE_INDEX_NAME not in pc.list_indexes().names():
        pc.create_index(name=PINECONE_INDEX_NAME, dimension=MODEL_DIMENSION, metric="cosine", spec=ServerlessSpec(cloud='aws', region='us-west-2'))

    index = pc.Index(PINECONE_INDEX_NAME)

    for i, story in enumerate(stories_list, 1):
        print(f"\n--- Processing story {i}/{len(stories_list)} (ID: {story['id']}) ---")

        article_text = scrape_article_text(story['url'])
        if not article_text:
            print("-> Skipping due to scraping failure.")
            continue

        text_chunks = chunk_text(article_text)
        if not text_chunks:
            print("-> Skipping, no text chunks generated.")
            continue

        print(f"-> Generated {len(text_chunks)} chunks. Embedding...")
        try:
            embeddings = model.encode(text_chunks, show_progress_bar=False).tolist()
        except Exception as e:
            print(f"-> Error generating embeddings: {e}")
            continue

        vectors_to_upsert = [
            {"id": f"{story['id']}-{j}", "values": emb, "metadata": {"text": chunk, "story_id": story['id'], "title": story['title'], "url": story['url']}}
            for j, (chunk, emb) in enumerate(zip(text_chunks, embeddings))
        ]

        if not vectors_to_upsert:
            print("-> Skipping, no vectors to upsert.")
            continue

        print(f"-> Upserting {len(vectors_to_upsert)} vectors to Pinecone...")
        try:
            index.upsert(vectors=vectors_to_upsert, batch_size=100)
            mark_story_as_processed(story['id'])
        except Exception as e:
            print(f"-> Error during Pinecone upsert: {e}")

# This block allows the script to be run directly for local testing.
# It simulates the old behavior of reading from a JSON file.
if __name__ == "__main__":
    print("Running embed and upsert script directly for local testing...")
    try:
        with open("hn_stories.json", 'r', encoding='utf-8') as f:
            stories_to_process = json.load(f)
        process_stories(stories_to_process)
    except FileNotFoundError:
        print("hn_stories.json not found. Run fetch_hn_data.py first.")
