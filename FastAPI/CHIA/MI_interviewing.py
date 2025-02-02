from openai import OpenAI
import json

client = OpenAI()


input_file = "/Users/amaris/Desktop/AI_coder/counselling-chatbot/FastAPI/embeddings/HIV_PrEP_knowledge_embedding.json"
output_file = "/Users/amaris/Desktop/AI_coder/counselling-chatbot/FastAPI/embeddings/HIV_PrEP_knowledge_embedding.jsonl"


with open(output_file, "rb") as file:
    response = client.files.create(file=file, purpose="fine-tune")


file_id = response.id
print(f"File uploaded with ID: {file_id}")

job = client.fine_tuning.jobs.create(
    training_file=file_id,
    model="gpt-4o-2024-08-06",
)

print(f"Fine-tuning job created: {job}")

