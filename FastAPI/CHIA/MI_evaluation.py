from langchain_openai import ChatOpenAI
import json
from datetime import datetime, timezone
from typing import TypedDict
from supabase import create_client
import supabase
import os
import uuid

class EvaluationResult(TypedDict):
    open_ended_question: bool
    affirmation: bool
    information_sharing: bool
    exploration_of_ambivalence: bool
    eliciting_change_talk: bool
    reflective_listening: bool
    reasoning: str

class MotivationalInterviewEvaluation:
    evaluation_instructions = """
    Take this conversation between a chatbot counselor and a client.
    Give it a rating from 1-10 based on whether the chatbot aligns with the 
    motivational interviewing found in the text file I've attached here.


    Return a JSON object with these exact fields:
    {
        "open_ended_question": string,
        "affirmation": string,
        "information_sharing": string,
        "exploration_of_ambivalence": string,
        "eliciting_change_talk": string,
        "reflective_listening": string,
        "reasoning": string with detailed explanation
    }"""

    def __init__(self, model="ft:gpt-4o-2024-08-06:brown-university::B4YXCCUH"):
        self.evaluator = ChatOpenAI(model=model, temperature=0)

supabase = create_client(
    os.environ.get("NEXT_PUBLIC_SUPABASE_URL"),
    os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
)

# accuracy evaluation
def evaluate_counseling_response(chat_id: str, chat_response: str, context_file_path: str = "FastAPI/embeddings/HIV_PrEP_knowledge_embedding.json") -> EvaluationResult:
    """
    Evaluates if an HIV counseling chat response follows motivational interviewing guidelines.
    
    Args:
        context_file_path: Path to the JSON file containing context data
        chat_response: The counselor's response to evaluate
        
    Returns:
        EvaluationResult: Structured evaluation results
    """
    try:
        with open(context_file_path, 'r') as file:
            context_data = json.load(file)

        context_string = json.dumps(context_data, indent=2)
        
        evaluation_prompt = f"""
        CONTEXT: {context_string}
        
        COUNSELOR RESPONSE: {chat_response}

        Evaluate this response and return a JSON object with the following fields:
        "open_ended_question": string,
        "affirmation": string,
        "information_sharing": string,
        "exploration_of_ambivalence": string,
        "eliciting_change_talk": string,
        "reflective_listening": string,
        "reasoning": string with detailed explanation
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
            
            required_fields = ["grounded", "medical_accuracy", "completeness", 
                             "no_fabrication", "appropriate_tone", "safety", "reasoning"]
            
            for field in required_fields:
                if field not in result:
                    print(f"Missing required field: {field}")
                    result[field] = False if field != "reasoning" else "Evaluation failed to produce complete results"

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
                grounded=False,
                medical_accuracy=False,
                completeness=False,
                no_fabrication=False,
                appropriate_tone=False,
                safety=False,
                reasoning="Failed to parse evaluation response"
            )
        
    except json.JSONDecodeError as e:
        print(f"Error parsing context JSON file: {e}")
        return None
    except FileNotFoundError:
        print(f"Context file not found at: {context_file_path}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None


# motivational interview evaluation
def evaluate_motivational_interview(chat_id: str, chat_response: str, context_file_path: str = "FastAPI/CHIA/motivational_interviewing_dataset.jsonl") -> EvaluationResult:
    """
    Evaluates if a counseling response follows motivational interviewing principles.
    
    Args:
        chat_id: Unique identifier for the chat session
        chat_response: The counselor's response to evaluate
        context_file_path: Path to the JSON file containing context data
        
    Returns:
        EvaluationResult: Structured evaluation of motivational interviewing techniques
    """
    try:
        with open(context_file_path, 'r') as file:
            context_data = json.load(file)

        context_string = json.dumps(context_data, indent=2)
        
        evaluation_prompt = f"""
        CONTEXT: {context_string}
        
        COUNSELOR RESPONSE: {chat_response}

        Evaluate this response based on motivational interviewing principles. For each category, 
        return true if the technique is present and effectively used, false otherwise.
        Return a JSON object with these exact fields:
        {{
            "open_ended_question": boolean,
            "affirmation": boolean,
            "information_sharing": boolean,
            "exploration_of_ambivalence": boolean,
            "eliciting_change_talk": boolean,
            "reflective_listening": boolean,
            "reasoning": string with detailed explanation of the evaluation
        }}
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
            
            # Verify all required MI fields are present
            required_fields = ["open_ended_question", "affirmation", "information_sharing", 
                             "exploration_of_ambivalence", "eliciting_change_talk", 
                             "reflective_listening", "reasoning"]
            
            for field in required_fields:
                if field not in result:
                    print(f"Missing required field: {field}")
                    result[field] = False if field != "reasoning" else "Evaluation failed to produce complete results"

            # Store evaluation result in database
            insert_result = supabase.table("evaluations").insert({
                "chat_id": chat_id,
                "chat_response": chat_response,
                "evaluation_result": result,
                "evaluation_type": "motivational_interviewing",
                "created_at": datetime.now(timezone.utc)
            }).execute()

            if insert_result:
                print("Motivational interviewing evaluation saved to database.")
            else:
                print("Error inserting evaluation result")

            return result
            
        except json.JSONDecodeError as e:
            print(f"Error parsing evaluation response: {e}")
            print(f"Raw response: {response}")
            return EvaluationResult(
                open_ended_question=False,
                affirmation=False,
                information_sharing=False,
                exploration_of_ambivalence=False,
                eliciting_change_talk=False,
                reflective_listening=False,
                reasoning="Failed to parse evaluation response"
            )
        
    except json.JSONDecodeError as e:
        print(f"Error parsing context JSON file: {e}")
        return None
    except FileNotFoundError:
        print(f"Context file not found at: {context_file_path}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None