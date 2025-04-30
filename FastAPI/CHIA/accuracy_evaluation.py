from langchain_openai import ChatOpenAI
import json
from datetime import datetime, timezone
from typing import TypedDict
from supabase import create_client
import supabase
import os
import uuid
import requests

class EvaluationResult(TypedDict):
    accuracy: int
    conciseness: int
    up_to_dateness: int
    trustworthiness: int
    empathy: int
    evocation: int
    reasoning: str

class HIVCounselingEvaluation:
    evaluation_instructions = """CONTEXT: 

        Evaluate this response and return a JSON object with the following fields:
        - grounded (boolean)
        - medical_accuracy (boolean)
        - completeness (boolean)
        - no_fabrication (boolean)
        - appropriate_tone (boolean)
        - safety (boolean)
        - reasoning (string with detailed explanation)

        You are evaluating an HIV counseling chat response.

    You will be given:
    CONTEXT: The reference knowledge/embedding data that should inform the response
    COUNSELOR RESPONSE: The actual response provided in the chat

    Evaluate based on these criteria using a scale of 1-5 (1 being lowest, 5 being highest):
    1. Accuracy (1-5): Is the response factually correct and relevant with respect to the context?
    2. Conciseness (1-5): Is the response clear, direct, and appropriately worded?
    3. Up-to-dateness (1-5): Is the response based on current and relevant information?
    4. Trustworthiness (1-5): Is the response free from bias, misinformation, and harmful content?
    5. Empathy (1-5): Does the response show appropriate understanding and emotional support?
    6. Evocation (1-5): Does the chatbot encourage the user to express their motivations for change?

    Rating Scale:
    1 = Poor/Inadequate
    2 = Below Average
    3 = Average/Adequate
    4 = Good
    5 = Excellent

    Return a JSON object with these exact fields:
    {
        "accuracy": number (1-5),
        "conciseness": number (1-5),
        "up_to_dateness": number (1-5),
        "trustworthiness": number (1-5),
        "empathy": number (1-5),
        "evocation": number (1-5),
        "reasoning": string with detailed explanation for each rating
    }
    }"""

    def __init__(self, model="ft:gpt-4o-2024-08-06:brown-university::B4YXCCUH"):
        self.evaluator = ChatOpenAI(model=model, temperature=0)

supabase = create_client(
    os.environ.get("NEXT_PUBLIC_SUPABASE_URL"),
    os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
)

# accuracy evaluation
def evaluate_counseling_response(chat_id: str, chat_response: str, context_file_path: str = "https://raw.githubusercontent.com/amarisg25/embedding-data-chatbot/main/HIV_PrEP_knowledge_embedding.json") -> EvaluationResult:
    """
    Evaluates if an HIV counseling chat response is properly grounded in the reference context.
    
    Args:
        chat_id: Unique identifier for the chat session
        chat_response: The counselor's response to evaluate
        context_file_path: URL to the JSON file containing context data
        
    Returns:
        EvaluationResult: Structured evaluation results
    """
    print("Running accuracy evaluation")
    try:
        response = requests.get(context_file_path)
        context_data = response.json()
        context_string = json.dumps(context_data, indent=2)
        
        evaluation_prompt = f"""CONTEXT: {context_string}
        
COUNSELOR RESPONSE: {chat_response}

Evaluate this response and return a JSON object with these exact fields:
{{
    "accuracy": number (1-5),
    "conciseness": number (1-5),
    "up_to_dateness": number (1-5),
    "trustworthiness": number (1-5),
    "empathy": number (1-5),
    "evocation": number (1-5),
    "reasoning": string with detailed explanation for each rating
}}

Rating Scale:
1 = Poor/Inadequate
2 = Below Average
3 = Average/Adequate
4 = Good
5 = Excellent

Evaluation Criteria:
1. Accuracy: Is the response factually correct and relevant with respect to the context?
2. Conciseness: Is the response clear, direct, and appropriately worded?
3. Up-to-dateness: Is the response based on current and relevant information?
4. Trustworthiness: Is the response free from bias, misinformation, and harmful content?
5. Empathy: Does the response show appropriate understanding and emotional support?
6. Evocation: Does the chatbot encourage the user to express their motivations for change?
"""
        
        evaluator = HIVCounselingEvaluation()
        messages = [
            {"role": "system", "content": HIVCounselingEvaluation.evaluation_instructions},
            {"role": "user", "content": evaluation_prompt}
        ]
        
        response = evaluator.evaluator.invoke(messages)
        try:
            # Handle markdown-formatted JSON response
            content = response.content
            if isinstance(content, str):
                # Remove markdown code block if present
                if content.startswith('```json'):
                    content = content[7:]  # Remove ```json
                if content.startswith('```'):
                    content = content[3:]  # Remove ```
                if content.endswith('```'):
                    content = content[:-3]  # Remove ```
                content = content.strip()
                
                result = json.loads(content)
            else:
                result = content
            
            required_fields = ["accuracy", "conciseness", "up_to_dateness", 
                             "trustworthiness", "empathy", "evocation", "reasoning"]
            
            for field in required_fields:
                if field not in result:
                    print(f"Missing required field: {field}")
                    result[field] = 1 if field != "reasoning" else "Evaluation failed to produce complete results"

            # Convert datetime to ISO format string
            current_time = datetime.now(timezone.utc).isoformat()

            insert_result = supabase.table("evaluations").insert({
                "chat_id": chat_id,
                "chat_response": chat_response,
                "evaluation_result": result, 
                "created_at": current_time
            }).execute()

            if insert_result:
                print("Accuracy evaluation saved to database.")
            else:
                print("Error inserting evaluation result")

            return result
            
        except json.JSONDecodeError as e:
            print(f"Error parsing evaluation response: {e}")
            print(f"Raw response: {response}")
            return EvaluationResult(
                accuracy=1,
                conciseness=1,
                up_to_dateness=1,
                trustworthiness=1,
                empathy=1,
                evocation=1,
                reasoning="Failed to parse evaluation response"
            )
        
    except requests.RequestException as e:
        print(f"Error fetching context from URL: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None


