# api/app/controllers/api/v1/chat_controller.rb

class Api::V1::ChatController < ApplicationController
  include ActionController::Live

  def stream
    query = params[:query]
    conversation_id = params[:conversation_id]

    if query.blank?
      render json: { error: 'Query parameter is missing' }, status: :bad_request
      return
    end

    conversation = conversation_id.present? ? Conversation.find_by(id: conversation_id) : Conversation.create
    conversation.messages.create(sender: 'user', content: query)

    history = conversation.messages.order(created_at: :desc).limit(5).reverse
    context = VectorDbService.get_relevant_context(query)

    response.headers['Content-Type'] = 'text/event-stream'
    ai_response = ""

    begin
      LlmService2.stream_answer(query, context, history) do |chunk|
        # Replace newlines with a unique token before sending
        sanitized_chunk = chunk.gsub("\n", "[NL]")
        ai_response << chunk
        response.stream.write("data: #{sanitized_chunk}\n\n")
      end

      # Save the AI's full response
      conversation.messages.create(sender: 'ai', content: ai_response)

      response.stream.write("data: #{ { done: true, conversation_id: conversation.id }.to_json }\n\n")
    rescue => e
      Rails.logger.error "Streaming error: #{e.message}"
    ensure
      response.stream.close
    end
  end
end
