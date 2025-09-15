"""
Utility functions for the counseling chatbot tools.
"""
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv("../.env")

# Initialize OpenAI API
OpenAI.api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI()


def classify_response(response, language):
    """Classifies response as affirmative, negative, uncooperative, or unsure."""
    prompt = (f"In {language}, classify this response as 'affirmative', "
              f"'negative', 'stop' (if the user wants to stop or exit out of "
              f"the assessment), 'clarification', or 'unsure': '{response}'. "
              f"Do not add extra words, just return the classification.")
    completion = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": prompt}]
    )
    return completion.choices[0].message.content.strip().lower()


def translate_question(question, language_code):
    """Translates a question into the user's detected language."""
    prompt = f"Translate the following sentence to {language_code}: {question}"
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "You are a translation assistant. "
                                                "Only return the translated question, "
                                                "no other text."},
                  {"role": "user", "content": prompt}]
    )
    return completion.choices[0].message.content