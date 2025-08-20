class Api::V1::ChatController < ApplicationController
  # This action will handle POST requests to /api/v1/chat
  def create
    # 1. Get the user's query from the request parameters
    query = params[:query]

    # Simple validation
    if query.blank?
      render json: { error: 'Query parameter is missing' }, status: :bad_request
      return
    end

    # 2. Use the VectorDbService to get relevant context from Pinecone
    context = VectorDbService.get_relevant_context(query)

    # 3. Use the LlmService to generate a final answer
    answer = LlmService.generate_answer(query, context)

    # 4. Send the answer back to the frontend as JSON
    render json: { answer: answer }
  end
end
