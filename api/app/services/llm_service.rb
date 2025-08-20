# api/app/services/llm_service.rb

require 'httparty'

class LlmService
  include HTTParty

  # --- Configuration for Local Ollama ---
  OLLAMA_API_URL = 'http://localhost:11434/api/generate'
  # Use the local model you have downloaded (e.g., llama3)
  CHAT_MODEL = 'llama3.2'

  def self.generate_answer(query, context)
    headers = { 'Content-Type' => 'application/json' }

    # Construct a clear prompt for the LLM
    prompt = <<-PROMPT
      You are an intelligent assistant for Hacker News.
      Answer the following question based *only* on the provided context.
      If the context does not contain the answer, say "I could not find an answer in the provided articles."

      Context:
      ---
      #{context.join("\n---\n")}
      ---

      Question: #{query}

      Answer:
    PROMPT

    # Ollama's generate endpoint has a simpler body structure
    body = {
      model: CHAT_MODEL,
      prompt: prompt,
      stream: false # We want the full response at once for v0
    }.to_json

    begin
      response = HTTParty.post(OLLAMA_API_URL, headers: headers, body: body)
      if response.success?
        # The response from Ollama is a stream of JSON objects, even with stream:false.
        # We parse the full response body and then extract the 'response' key from the final JSON object.
        parsed_response = JSON.parse(response.body)
        parsed_response['response']
      else
        puts "Error from Ollama LLM API: #{response.body}"
        "Sorry, there was an error processing your request."
      end
    rescue => e
      puts "Exception calling Ollama LLM API: #{e.message}"
      "Sorry, there was an error connecting to the AI service."
    end
  end
end
