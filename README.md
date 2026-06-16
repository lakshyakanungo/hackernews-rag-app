# HN RAG Chat

HN RAG Chat is a retrieval-augmented generation app for asking questions about the latest Hacker News articles.

The system fetches current Hacker News stories, scrapes the linked articles, chunks and embeds the article text, stores vectors in Pinecone, tracks processed story IDs and conversations in Supabase Postgres, and streams grounded answers back through a React chat UI.

## What this app does

- Pulls the latest Hacker News top stories from the official Hacker News Firebase API.
- Skips articles that have already been processed by checking `processed_stories` in Postgres.
- Scrapes article pages, removes noisy tags, chunks the text, and embeds each chunk.
- Stores article embeddings and metadata in Pinecone for semantic search.
- Stores processed article IDs, conversations, and messages in Supabase Postgres.
- Retrieves the most relevant chunks for a user query.
- Streams a Gemini answer to the frontend with source links appended by the backend.
- Routes embedding requests for live queries through a local Ollama instance exposed through ngrok.

## Architecture

```text
                         Daily ingestion, every 24 hours
                         via Codex automation / script
                                      |
                                      v
  Hacker News API -> Python pipeline -> Article scraper -> Chunker
                                      |
                                      v
                         nomic-embed-text embeddings
                                      |
                                      v
               +----------------------+----------------------+
               |                                             |
               v                                             v
        Pinecone vector DB                         Supabase Postgres
        article chunks + metadata                  processed_stories
                                                   conversations
                                                   messages


  User -> React/Vite frontend on Vercel -> Rails API on Render
                                      |
                                      v
                       /api/v1/chat/stream SSE endpoint
                                      |
                 +--------------------+--------------------+
                 |                                         |
                 v                                         v
       ngrok -> local laptop -> Ollama          Pinecone similarity search
       query embedding using                    top relevant article chunks
       nomic-embed-text
                 |                                         |
                 +--------------------+--------------------+
                                      |
                                      v
                         Gemini 3.5 Flash streaming answer
                                      |
                                      v
                         React chat receives chunks over SSE
```

## Tech stack

| Layer | Technology |
| --- | --- |
| Frontend | React 19, Vite, Tailwind CSS, `EventSource` for SSE streaming |
| Backend | Ruby on Rails 7.1 API, Puma, Rack CORS |
| LLM | Gemini `gemini-3.5-flash` through `gemini-ai` |
| Local model runtime | Ollama, exposed to the deployed backend through ngrok |
| Embeddings | Nomic `nomic-embed-text` for query embeddings; pipeline uses `nomic-ai/nomic-embed-text-v1.5` through Sentence Transformers |
| Vector database | Pinecone |
| Relational database | Supabase Postgres |
| Data pipeline | Python, Requests, BeautifulSoup, Sentence Transformers, Pinecone client, psycopg2 |
| Hosting | Backend on Render, frontend on Vercel |

## Repository layout

```text
.
├── api/                         # Rails API
│   ├── app/controllers/api/v1/   # Streaming chat endpoint
│   ├── app/services/             # Pinecone retrieval, Ollama embeddings, Gemini streaming
│   ├── app/models/               # Conversation, Message, ProcessedStory
│   └── db/migrate/               # Supabase/Postgres schema
├── client/                      # React + Vite frontend
│   └── src/
│       ├── App.jsx              # Chat UI and EventSource client
│       └── components/          # Message rendering and markdown link handling
└── data-pipeline/               # HN ingestion, scraping, embedding, and upsert scripts
    ├── scripts/fetch_hn_data.py
    └── scripts/embed_and_upsert.py
```

## Data ingestion flow

The ingestion job runs every 24 hours via Codex automation/script.

1. `data-pipeline/scripts/fetch_hn_data.py` calls the Hacker News API:
   - `https://hacker-news.firebaseio.com/v0/topstories.json`
   - `https://hacker-news.firebaseio.com/v0/item/{id}.json`

2. It connects to Supabase Postgres and reads `processed_stories` so the pipeline only processes new articles.

3. It fetches up to 30 new HN stories per run and keeps stories that have an external article URL.

4. `data-pipeline/scripts/embed_and_upsert.py` scrapes the article body with Requests and BeautifulSoup.

5. The article text is split into overlapping chunks of roughly 512 words with a 50-word overlap.

6. Chunks are embedded with Nomic embeddings:
   - Pipeline model: `nomic-ai/nomic-embed-text-v1.5`
   - Vector dimension: `768`
   - Pinecone metric: cosine similarity

7. Each chunk is upserted into the Pinecone index `hn-rag-v0` with metadata:
   - `text`
   - `story_id`
   - `title`
   - `url`
   - `hn_url`
   - `chunk_index`
   - `total_chunks`

8. Once Pinecone upsert succeeds, the story ID is inserted into `processed_stories`.

## Query and response flow

1. The React app sends a query to:

   ```text
   GET /api/v1/chat/stream?query=...
   ```

2. The Rails controller creates or reuses a conversation and stores the user message.

3. `VectorDbService` embeds the user query using local Ollama:

   ```text
   OLLAMA_API_URL + /embeddings
   model: nomic-embed-text
   ```

4. The Rails API queries Pinecone for the top 10 semantically similar chunks.

5. `LlmService2` builds a grounded prompt with:
   - retrieved article context
   - article titles and URLs
   - relevance scores
   - recent conversation history
   - the latest user question

6. Gemini `gemini-3.5-flash` streams the answer back to Rails.

7. Rails streams chunks to the frontend using server-sent events.

8. The backend appends verified article links from Pinecone metadata after the model response.

## Why this architecture?

This app intentionally separates ingestion, retrieval, generation, and presentation.

- Pinecone is used for vector search because the app needs low-latency semantic retrieval over article chunks, not just keyword search.
- Supabase Postgres is used for relational state: processed story IDs, conversations, and messages. This keeps operational state queryable and easy to inspect.
- Ollama runs locally for embeddings so query embedding cost stays low and the embedding model can be swapped without redeploying the backend.
- ngrok bridges the hosted Rails API to the local laptop running Ollama. This is useful for demos and development because the model runtime can stay local while the app remains publicly reachable.
- Gemini `gemini-3.5-flash` is used for streaming answer generation because the chat experience benefits from low-latency token streaming and strong summarization over retrieved context.
- React uses `EventSource` because server-sent events are a simple fit for one-way streaming responses from the backend to the browser.
- The ingestion job runs every 24 hours because Hacker News changes frequently, but the app does not need expensive continuous ingestion for a portfolio/demo workload.

## FAQs

### Why Nomic embeddings?

Nomic embeddings are a good fit for a local-first setup: they are strong general-purpose text embeddings, easy to run with Ollama for query-time embedding, and available through Sentence Transformers for batch ingestion. That keeps ingestion and retrieval aligned around the same embedding family.

### Why Gemini 3.5 Flash?

The user-facing workload is conversational summarization over retrieved chunks. A Flash model is appropriate because it optimizes for fast responses and streaming UX while still handling article-level reasoning and explanation.

### Why stream responses?

Streaming improves perceived latency. The user starts reading while the model is still generating, which makes the app feel responsive even when retrieval and generation take a few seconds.

### Why process only new Hacker News stories?

The `processed_stories` table makes the pipeline idempotent. Re-running the job does not repeatedly scrape and embed the same articles, which saves compute, avoids duplicate vectors, and makes failures easier to recover from.

### What are the tradeoffs?

- Scraping external article pages can fail due to paywalls, bot protection, or unusual markup.
- ngrok plus a local Ollama runtime is excellent for demos, but production would usually move embedding generation to a managed service or private hosted model endpoint.
- The current chunking strategy is simple word-based chunking. A more advanced version could use semantic chunking or document structure.
- The system appends source links from metadata, but deeper citation support could map individual answer claims to specific chunks.

## Example prompts

These prompts work well with articles already embedded in the current dataset:

- `Explain "How memory safety CVEs differ between Rust and C/C++" in simple terms.`
- `Summarize the article about Firefox 152 and JPEG-XL support.`
- `What is "Show HN: Fata" and what problem does it solve?`
- `Tell me about the Micro Radar project.`
- `Compare the articles about AI coding tools and AI capacity constraints.`
- `What are the main arguments in "Can Europe train a frontier AI model on the compute it owns?"`
- `Explain the article about factoring short-sleeve RSA keys with polynomials.`
- `What does the Typst 0.15.0 article announce?`
- `Give me a concise summary of the copper transport Alzheimer's drug article.`
- `Which embedded articles are related to AI infrastructure or model development?`

You can also paste an article title directly, for example:

```text
How memory safety CVEs differ between Rust and C/C++
```

## Local development

### Prerequisites

- Ruby `3.3.0`
- Bundler
- Node.js and Yarn
- Python `3.11+`
- Supabase Postgres database
- Pinecone account and index
- Ollama running locally with `nomic-embed-text`
- Gemini API key
- ngrok for exposing local Ollama to the hosted backend when needed

Pull the embedding model locally:

```bash
ollama pull nomic-embed-text
```

### Backend setup

```bash
cd api
bundle install
bin/rails db:migrate
bin/rails server -p 3005
```

Required backend environment variables:

```bash
DATABASE_URL=postgres://...
GOOGLE_API_KEY=...
PINECONE_API_KEY=...
PINECONE_API_URL=https://your-index-host.svc.region.pinecone.io
OLLAMA_API_URL=http://localhost:11434/api
ALLOWED_ORIGINS=http://localhost:5173
```

For Render, `OLLAMA_API_URL` should point to the ngrok URL that forwards to your local Ollama API, with `/api` included if your tunnel exposes Ollama’s root host.

### Frontend setup

```bash
cd client
yarn install
yarn dev
```

The current frontend points at:

```text
http://localhost:3005/api/v1/chat/stream
```

For production on Vercel, configure the API URL to point at the Render backend.

### Data pipeline setup

```bash
cd data-pipeline
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd scripts
python fetch_hn_data.py
python embed_and_upsert.py
```

Required pipeline environment variables:

```bash
PINECONE_API_KEY=...
DB_NAME=...
DB_USER=...
DB_PASSWORD=...
DB_HOST=...
DB_PORT=5432
```

The pipeline scripts load environment variables from `data-pipeline/.env`.

## Database schema

The Rails app uses three application tables:

- `processed_stories`: stores unique Hacker News story IDs that have already been embedded.
- `conversations`: stores chat sessions.
- `messages`: stores user and AI messages for each conversation.

Supabase also adds its own platform schemas and extensions, which appear in `api/db/schema.rb`.

## API

### Stream chat response

```http
GET /api/v1/chat/stream?query=<question>&conversation_id=<optional>
```

Response format: `text/event-stream`

The stream emits text chunks as SSE `data:` messages. When complete, it emits:

```json
{ "done": true, "conversation_id": 1 }
```

### Health check

```http
GET /ping
```

## Deployment notes

- Backend is hosted on Render.
- Frontend is hosted on Vercel.
- Supabase provides managed Postgres.
- Pinecone hosts the vector index.
- Ollama runs on a local laptop.
- ngrok forwards the hosted backend’s embedding requests to the local Ollama API.
- Codex runs the Hacker News parsing and ingestion workflow every 24 hours.

For a more production-hardened setup, the local Ollama/ngrok dependency could be replaced with a private model service, a managed embedding API, or a small GPU/CPU instance inside the same network as the Rails API.

## Current implementation notes

- The Rails chat endpoint is implemented in `api/app/controllers/api/v1/chat_controller.rb`.
- Pinecone retrieval and query embeddings are handled by `api/app/services/vector_db_service.rb`.
- Gemini streaming is handled by `api/app/services/llm_service2.rb`.
- The Python ingestion entry points are `data-pipeline/scripts/fetch_hn_data.py` and `data-pipeline/scripts/embed_and_upsert.py`.
