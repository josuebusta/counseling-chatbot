from openai import OpenAI
import os
import openai
from dotenv import load_dotenv



# Load dotenv file 
load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

# Retrieve API key
client = OpenAI(api_key=api_key)



# Chat creation request
def get_chat_responses(messages):
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    return completion.choices[0].message


get_chat_responses(['I would like to assess my HIV risk'])
conversation = { }


high_risk = False
responses = {}


 


