# import os
# import openai
# from dotenv import load_dotenv
# from openai import OpenAI


# load_dotenv()
# api_key = os.getenv('OPENAI_API_KEY')


# client = OpenAI(api_key=api_key)

# def get_chat_responses(messages):
#     completion = client.chat.completions.create(
#         model="gpt-4",  
#         messages=messages
#     )
#     return completion.choices[0].message.content

# messages = [
#     # {"role": "system", "content": "You are an HIV risk counselor chatbot."},
#     {"role": "user", "content": "I would like to assess my HIV risk."}
# ]

# response = get_chat_responses(messages)
# print(response)


# conversation = []

# conversation.append({"role": "user", "content": "I would like to assess my HIV risk"})
# conversation.append({"role": "assistant", "content": response})


import os
import openai
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

client = OpenAI(api_key=api_key)

# get responses
def get_chat_responses(messages):
    completion = client.chat.completions.create(
        model="gpt-4",  
        messages=messages
    )
    return completion.choices[0].message.content

conversation = [
    # {"role": "system", "content": "You are an HIV risk counselor chatbot."}
]

# conversate with chatbot in terminal
while True:
    user_input = input("Patient: ")
    conversation.append({"role": "user", "content": user_input})
    response = get_chat_responses(conversation)
    print(f"Counselor: {response}")
    conversation.append({"role": "assistant", "content": response})

