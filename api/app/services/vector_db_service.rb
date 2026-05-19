require 'httparty'

class VectorDbService
  include HTTParty

  # --- Configuration for Local Ollama ---
  OLLAMA_API_URL = ENV['OLLAMA_API_URL'] + '/embeddings'
  # This MUST match the model used in your Python script
  EMBEDDING_MODEL = 'nomic-embed-text'

  PINECONE_API_URL = ENV['PINECONE_API_URL']
  PINECONE_API_KEY = ENV['PINECONE_API_KEY']
  TOP_K = 10

  def self.get_relevant_context(query)
    # 1. Convert the user's query into an embedding using local Ollama
    query_embedding = generate_embedding(query)
    return [] unless query_embedding

    # 2. Query Pinecone to find the most similar text chunks
    headers = {
      'Api-Key' => PINECONE_API_KEY,
      'Content-Type' => 'application/json'
    }
    body = {
      'vector' => query_embedding,
      'topK' => TOP_K,
      'includeMetadata' => true
    }.to_json

    begin
      response = HTTParty.post("#{PINECONE_API_URL}/query", headers: headers, body: body)
      if response.success?
        matches = response.parsed_response['matches'] || []
        matches.filter_map { |match| build_context_item(match) }
      else
        puts "Error querying Pinecone: #{response.body}"
        []
      end
    rescue => e
      puts "Exception querying Pinecone: #{e.message}"
      []
    end
  end

  def self.source_links(context, max: 2)
    sources = {}

    context.each do |item|
      url = item[:url].to_s
      next if url.empty?

      key = item[:story_id] || url
      sources[key] ||= {
        title: item[:title].to_s.empty? ? url : item[:title].to_s,
        url: url
      }
    end

    links = sources.values.first(max).map do |source|
      "[#{escape_markdown_link_text(source[:title])}](<#{source[:url]}>)"
    end

    links.empty? ? "" : "Sources: #{links.join(', ')}"
  end

  private

  def self.build_context_item(match)
    metadata = match['metadata'] || {}
    text = metadata['text'].to_s
    return nil if text.empty?

    {
      story_id: metadata['story_id'],
      title: metadata['title'],
      url: metadata['url'],
      hn_url: metadata['hn_url'],
      text: text,
      score: match['score']
    }
  end

  def self.escape_markdown_link_text(text)
    text.to_s.gsub('[', '\\[').gsub(']', '\\]')
  end

  def self.generate_embedding(text)
    headers = { 'Content-Type' => 'application/json' }
    # Ollama's embedding endpoint requires a different body structure
    body = {
      model: EMBEDDING_MODEL,
      prompt: text
    }.to_json

    begin
      response = HTTParty.post(OLLAMA_API_URL, headers: headers, body: body)
      if response.success?
        response.parsed_response['embedding']
      else
        puts "Error generating embedding with Ollama: #{response.body}"
        nil
      end
    rescue => e
      puts "Exception generating embedding with Ollama: #{e.message}"
      nil
    end
  end
end
