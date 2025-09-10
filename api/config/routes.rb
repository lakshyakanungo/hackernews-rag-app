Rails.application.routes.draw do
  # Define your API routes under a namespace to version them.
  # This creates the URL: /api/v1/chat
  namespace :api do
    namespace :v1 do
      get "chat/stream", to: "chat#stream"
    end
  end
end
