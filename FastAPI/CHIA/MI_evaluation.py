from langchain_openai import ChatOpenAI
import json
from datetime import datetime, timezone
from typing import TypedDict
from supabase import create_client
import supabase
import os
import uuid

class EvaluationResult(TypedDict):
    accuracy: bool
    conciseness: bool
    up_to_dateness: bool
    trustworthiness: bool
    empathy: bool
    evocation: bool
    collaboration: bool
    autonomy_support: bool
    affirmation: bool
    reasoning: str

class MotivationalInterviewEvaluation:
    evaluation_instructions = """
    Take this conversation between a chatbot counselor and a client.
    Evaluate the response based on the following criteria, rating each in scale of 1-10:
    - Accuracy: Is the information provided accurate?
    - Conciseness: Is the response clear and to the point?
    - Up-to-dateness: Is the information current and relevant?
    - Trustworthiness: Does the response build trust and credibility?
    - Empathy: Does the response show understanding of the client's feelings?
    - Evocation: Does it draw out the client's own motivations?
    - Collaboration: Does it promote a partnership approach?
    - Autonomy Support: Does it respect client's independence in decision-making?
    - Affirmation: Does it recognize client's strengths and efforts?

    Return a JSON object with these exact fields:
    {
        "accuracy": boolean,
        "conciseness": boolean,
        "up_to_dateness": boolean,
        "trustworthiness": boolean,
        "empathy": boolean,
        "evocation": boolean,
        "collaboration": boolean,
        "autonomy_support": boolean,
        "affirmation": boolean,
        "reasoning": string with detailed explanation
    }"""

    def __init__(self):
        self.evaluator = ChatOpenAI(
            model="ft:gpt-4o-2024-08-06:brown-university::B4YXCCUH",
            temperature=0.7,
            max_tokens=1000
        )

# motivational interview evaluation
def evaluate_motivational_interview(chat_id: str, chat_response: str, context_file_path: str = "https://raw.githubusercontent.com/anuradha1992/Motivational-Interviewing-Dataset/refs/heads/main/MI%20Dataset.csv") -> EvaluationResult:
    """
    Evaluates if a counseling response follows motivational interviewing principles.
    
    Args:
        chat_id: Unique identifier for the chat session
        chat_response: The counselor's response to evaluate
        context_file_path: URL to the CSV file containing motivational interviewing data
        
    Returns:
        EvaluationResult: Structured evaluation of motivational interviewing techniques
    """
    try:
        import requests
        import pandas as pd
        from io import StringIO
        
        # Fetch and parse the CSV data
        response = requests.get(context_file_path)
        df = pd.read_csv(StringIO(response.text))
        
        # Convert relevant columns to context string
        context_string = df[['text', 'final agreed label']].to_string()
        
        evaluation_prompt = f"""
        CONTEXT: {context_string}
        
        COUNSELOR RESPONSE: {chat_response}

        Evaluate this response and return a JSON object with the following fields:
        - grounded (boolean)
        - medical_accuracy (boolean)
        - completeness (boolean)
        - no_fabrication (boolean)
        - appropriate_tone (boolean)
        - safety (boolean)
        - reasoning (string with detailed explanation)
        """
        
        evaluator = MotivationalInterviewEvaluation()
        messages = [
            {"role": "system", "content": MotivationalInterviewEvaluation.evaluation_instructions},
            {"role": "user", "content": evaluation_prompt}
        ]
        
        response = evaluator.evaluator.invoke(messages)
        try:
            if isinstance(response.content, str):
                result = json.loads(response.content)
            else:
                result = response.content
            
            required_fields = ["accuracy", "conciseness", "up_to_dateness", 
                             "trustworthiness", "empathy", "evocation", "reasoning"]
            
            for field in required_fields:
                if field not in result:
                    print(f"Missing required field: {field}")
                    result[field] = 0 if field != "reasoning" else "Evaluation failed to produce complete results"

            insert_result = supabase.table("evaluations").insert({
                "chat_id": chat_id,
                "chat_response": chat_response,
                "evaluation_result": result
            }).execute()

            if insert_result:
                print("Evaluation result successfully saved to the database.")
            else:
                print("Error inserting evaluation result")

            
            return result
            
        except json.JSONDecodeError as e:
            print(f"Error parsing evaluation response: {e}")
            print(f"Raw response: {response}")
            return EvaluationResult(
                accuracy=0,
                conciseness=0,
                up_to_dateness=0,
                trustworthiness=0,
                empathy=0,
                evocation=0,
                reasoning="Failed to parse evaluation response"
            )
        
    except json.JSONDecodeError as e:
        print(f"Error parsing context JSON file: {e}")
        return None
    except requests.RequestException as e:
        print(f"Error fetching context from URL: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None
