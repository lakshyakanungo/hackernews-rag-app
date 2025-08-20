import os
import json
import time
import requests
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec

# --- Configuration ---
# Load environment variables for API keys
# Note: It's best practice to use environment variables for sensitive data.
# You can set them in your terminal before running the script:
# export PINECONE_API_KEY='your_pinecone_api_key'
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "YOUR_PINECONE_API_KEY")

# Pinecone configuration
PINECONE_INDEX_NAME = "hn-rag-v0" # Name your index

# Model for embedding
# Using the high-performance Nomic model with a large context window.
EMBEDDING_MODEL = 'nomic-ai/nomic-embed-text-v1.5'
MODEL_DIMENSION = 768 # Dimension for nomic-embed-text-v1.5

# Data file from the previous step
INPUT_FILENAME = "hn_stories.json"

# --- 1. Initialize Services ---

def initialize_pinecone():
    """Initializes and returns a Pinecone client and index object."""
    print("Initializing Pinecone...")
    if PINECONE_API_KEY == "YOUR_PINECONE_API_KEY":
        raise ValueError("Please set your PINECONE_API_KEY environment variable or update the script.")

    pc = Pinecone(api_key=PINECONE_API_KEY)

    # Check if the index already exists. If not, create it.
    if PINECONE_INDEX_NAME not in pc.list_indexes().names():
        print(f"Index '{PINECONE_INDEX_NAME}' not found. Creating a new one...")
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=MODEL_DIMENSION,
            metric="cosine", # Cosine similarity is common for text embeddings
            spec=ServerlessSpec(
                cloud='aws',
                region='us-east-1'
            )
        )
        # Wait for the index to be ready
        while not pc.describe_index(PINECONE_INDEX_NAME).status['ready']:
            time.sleep(1)
        print("Index created successfully.")
    else:
        print(f"Found existing index '{PINECONE_INDEX_NAME}'.")

    index = pc.Index(PINECONE_INDEX_NAME)
    # Give a moment for the connection to establish
    time.sleep(1)
    print("Pinecone initialized.")
    return index

def initialize_embedding_model():
    """Initializes and returns the sentence-transformer model."""
    print(f"Loading embedding model: {EMBEDDING_MODEL}...")
    # trust_remote_code is required for this Nomic model
    model = SentenceTransformer(EMBEDDING_MODEL, trust_remote_code=True)
    print("Embedding model loaded.")
    return model

# --- 2. Data Processing Functions ---

def load_stories():
    """Loads the story data from the JSON file."""
    try:
        with open(INPUT_FILENAME, 'r', encoding='utf-8') as f:
            stories = json.load(f)
        print(f"Loaded {len(stories)} stories from {INPUT_FILENAME}.")
        return stories
    except FileNotFoundError:
        print(f"Error: {INPUT_FILENAME} not found. Please run 01_fetch_hn_data.py first.")
        return []
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {INPUT_FILENAME}.")
        return []

def scrape_article_text(url):
    """
    Scrapes the main textual content from a given article URL.
    Returns the text as a single string.
    """
    try:
        # Set a user-agent to mimic a browser and avoid being blocked
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # A common strategy: find the main content area of the page.
        # These tags often hold the primary article text.
        main_content_tags = soup.find_all(['article', 'main', 'p'])

        if not main_content_tags:
             # Fallback to just getting all text if specific tags aren't found
            return ' '.join(soup.get_text().split())

        text_parts = [tag.get_text(separator=' ', strip=True) for tag in main_content_tags]
        full_text = ' '.join(text_parts)

        # Clean up excessive whitespace
        return ' '.join(full_text.split())
    except requests.exceptions.RequestException as e:
        print(f"  -> Failed to scrape {url}: {e}")
        return None

def chunk_text(text, chunk_size=512, overlap=50):
    """
    Splits a long text into smaller, overlapping chunks.
    This is crucial for fitting content within the model's context window.
    """
    if not text:
        return []
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = ' '.join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks

# --- 3. Main Execution Logic ---

def main():
    """Main function to run the embedding and upserting pipeline."""
    stories = load_stories()
    if not stories:
        return

    pinecone_index = initialize_pinecone()
    model = initialize_embedding_model()

    print("\n--- Starting to process and embed stories ---")
    total_chunks_upserted = 0

    for i, story in enumerate(stories):
        story_id = story['id']
        story_title = story['title']
        story_url = story['url']

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

        print(f"  -> Generated {len(text_chunks)} text chunks.")

        # Generate embeddings for all chunks of the current article
        print("  -> Generating embeddings...")
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
            except Exception as e:
                print(f"  -> Error upserting to Pinecone: {e}")

    print(f"\n--- Pipeline Finished ---")
    print(f"Total chunks upserted to Pinecone: {total_chunks_upserted}")
    print(f"Index '{PINECONE_INDEX_NAME}' is now populated.")

if __name__ == "__main__":
    main()
