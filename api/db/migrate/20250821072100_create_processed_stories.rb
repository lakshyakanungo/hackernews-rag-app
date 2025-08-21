class CreateProcessedStories < ActiveRecord::Migration[7.1]
  def change
    create_table :processed_stories do |t|
      t.integer :story_id

      t.timestamps
    end

    add_index :processed_stories, :story_id, unique: true
  end
end
