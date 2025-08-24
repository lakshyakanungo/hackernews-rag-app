# api/app/controllers/api/v1/chat_controller.rb

class Api::V1::ChatController < ApplicationController
  def create
    query = params[:query]
    conversation_id = params[:conversation_id]

    if query.blank?
      render json: { error: 'Query parameter is missing' }, status: :bad_request
      return
    end

    # Find an existing conversation or create a new one
    conversation = conversation_id.present? ? Conversation.find_by(id: conversation_id) : Conversation.create

    # Save the user's message
    conversation.messages.create(sender: 'user', content: query)

    # Get the last 5 messages as history (to keep the prompt concise)
    history = conversation.messages.order(created_at: :desc).limit(5).reverse

    # Perform the RAG logic
    context = VectorDbService.get_relevant_context(query)
    answer = LlmService.generate_answer(query, context, history)

    # Save the AI's response
    conversation.messages.create(sender: 'ai', content: answer)

    # Send the answer and the conversation_id back to the frontend
    render json: { answer: answer, conversation_id: conversation.id }
  end
end
