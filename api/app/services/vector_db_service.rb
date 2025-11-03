require 'httparty'

class VectorDbService
  include HTTParty

  # --- Configuration for Local Ollama ---
  OLLAMA_API_URL = ENV['OLLAMA_API_URL'] + '/embeddings'
  # This MUST match the model used in your Python script
  EMBEDDING_MODEL = 'nomic-embed-text'

  PINECONE_API_URL = ENV['PINECONE_API_URL']
  PINECONE_API_KEY = ENV['PINECONE_API_KEY']

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
      'topK' => 3, # Get the top 3 most relevant chunks
      'includeMetadata' => true
    }.to_json

    begin
      response = HTTParty.post("#{PINECONE_API_URL}/query", headers: headers, body: body)
      if response.success?
        # Extract just the text from the metadata of each match
        matches = response.parsed_response['matches'] || []
        matches.map { |match| match.dig('metadata', 'text') }.compact
      else
        puts "Error querying Pinecone: #{response.body}"
        []
      end
    rescue => e
      puts "Exception querying Pinecone: #{e.message}"
      []
    end
  end

  private

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
