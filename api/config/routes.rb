Rails.application.routes.draw do
  # This creates the URL: /api/v1/chat
  namespace :api do
    namespace :v1 do
      get "chat/stream", to: "chat#stream"
    end
  end
  get :ping, to: "ping#show"
end
