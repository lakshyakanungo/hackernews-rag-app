# api/app/services/llm_service2.rb

require 'gemini-ai'

class LlmService2
  include HTTParty

  def self.client
    Gemini.new(
      credentials: {
        service: 'generative-language-api',
        api_key: ENV['GOOGLE_API_KEY']
      },
      options: { model: 'gemini-2.5-flash', server_sent_events: true }
    )
  end

  def self.stream_answer(query, context, history)
    prompt = build_prompt(query, context, history)

    client.stream_generate_content(
      { contents: { role: 'user', parts: { text: prompt } } }
    ) do |event, parsed, raw|
      yield event["candidates"]&.first["content"]["parts"]&.first["text"] || ""
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
