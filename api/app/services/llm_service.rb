require 'net/http'
require 'json'

class LlmService
  include HTTParty

  OLLAMA_API_URL = ENV['OLLAMA_API_URL'] + '/generate'
  CHAT_MODEL = 'llama3.2'

  def self.stream_answer(query, context, history)
    prompt = build_prompt(query, context, history)

    uri = URI(OLLAMA_API_URL)
    request = Net::HTTP::Post.new(uri, { 'Content-Type' => 'application/json' })
    request.body = {
      model: CHAT_MODEL,
      prompt: prompt,
      stream: true
    }.to_json

    Net::HTTP.start(uri.host, uri.port) do |http|
      http.request(request) do |response|
        response.read_body do |chunk|
          Rails.logger.info "✅ #{chunk}"
          begin
            json = JSON.parse(chunk)
            yield json["response"] if json["response"]
            break if json["done"]
          rescue JSON::ParserError
            # skip incomplete JSON chunks
          end
        end
      end
    end
  end

  def self.build_prompt(query, context, history)
    <<-PROMPT
      You are an intelligent assistant for Hacker News.
      Answer the following question based *only* on the provided context.
      If the context does not contain the answer, say "I could not find an answer in the provided articles."

      Here is the relevant context from new articles:
      ---
      #{context.join("\n---\n")}
      ---

      Here is the recent conversation history:
      ---
      #{history.map { |m| "#{m.sender}: #{m.content}" }.join("\n")}
      ---

      Latest Question: #{query}

      Answer:
    PROMPT
  end
end
