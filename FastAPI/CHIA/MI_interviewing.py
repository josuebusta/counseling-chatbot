from openai import OpenAI
import json

client = OpenAI()

output_file = "/Users/amaris/Desktop/AI_coder/counselling-chatbot/FastAPI/CHIA/motivational_interviewing_dataset.jsonl"

# Upload the file for fine-tuning
with open(output_file, "rb") as file:
    response = client.files.create(file=file, purpose="fine-tune")

file_id = response.id  # Ensure correct access to the file ID
print(f"File uploaded with ID: {file_id}")

# Start fine-tuning job
job = client.fine_tuning.jobs.create(
    training_file=file_id,
    model="gpt-4o-mini-2024-07-18",
)

print(f"Fine-tuning job created with ID: {job.id}")
