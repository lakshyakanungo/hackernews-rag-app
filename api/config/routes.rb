Rails.application.routes.draw do
  # Define your API routes under a namespace to version them.
  # This creates the URL: /api/v1/chat
  namespace :api do
    namespace :v1 do
      # A POST request to /api/v1/chat will be handled by the 'create' action
      # in the ChatController.
      post 'chat', to: 'chat#create'
    end
  end
end
