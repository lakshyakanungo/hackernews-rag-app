# api/app/services/llm_service.rb

require 'httparty'

class LlmService
  include HTTParty

  OLLAMA_API_URL = 'http://localhost:11434/api/generate'
  CHAT_MODEL = 'llama3.2'

  def self.generate_answer(query, context, history)
    headers = { 'Content-Type' => 'application/json' }

    # Build a formatted history string
    formatted_history = history.map do |msg|
      "#{msg.sender.capitalize}: #{msg.content}"
    end.join("\n")

    prompt = <<-PROMPT
      You are an intelligent assistant for Hacker News.
      Answer the following question based *only* on the provided context.
      If the context does not contain the answer, say "I could not find an answer in the provided articles."

      Here is the recent conversation history:
      ---
      #{formatted_history}
      ---

      Here is the relevant context from new articles:
      ---
      #{context.join("\n---\n")}
      ---

      Latest Question: #{query}

      Answer:
    PROMPT

    body = {
      model: CHAT_MODEL,
      prompt: prompt,
      stream: false
    }.to_json

    begin
      response = HTTParty.post(OLLAMA_API_URL, headers: headers, body: body)
      if response.success?
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
