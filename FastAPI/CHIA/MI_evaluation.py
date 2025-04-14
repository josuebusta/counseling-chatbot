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
    Evaluate the response based on the following criteria, rating each as true/false:
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
