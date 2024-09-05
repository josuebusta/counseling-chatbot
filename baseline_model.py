from openai import OpenAI
import os
import openai
from dotenv import load_dotenv



# Load dotenv file 
load_dotenv()
api_key = os.getenv('API_KEY')

# Retrieve API key
client = OpenAI(api_key=api_key)


# Chat creation request
completion = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
       {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Who won the world series in 2020?"},
        {"role": "assistant", "content": "The Los Angeles Dodgers won the World Series in 2020."},
        {"role": "user", "content": "Where was it played?"}
    ]
)

print(completion.choices[0].message)