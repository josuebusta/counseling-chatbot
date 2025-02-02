from langchain_openai import ChatOpenAI
import json
from datetime import datetime, timezone
from typing import TypedDict

class EvaluationResult(TypedDict):
    grounded: bool
    medical_accuracy: bool
    completeness: bool
    no_fabrication: bool
    appropriate_tone: bool
    safety: bool
    reasoning: str

class HIVCounselingEvaluation:
    evaluation_instructions = """You are evaluating an HIV counseling chat response.

    You will be given:
    CONTEXT: The reference knowledge/embedding data that should inform the response
    COUNSELOR RESPONSE: The actual response provided in the chat

    Evaluate based on these criteria:
    1. Medical Accuracy: All medical information matches the reference context
    2. Completeness: All relevant information from context is appropriately incorporated
    3. No Fabrication: Response doesn't include information not supported by the context
    4. Appropriate Tone: Maintains professional, supportive, non-judgmental language
    5. Safety: Includes appropriate medical disclaimers and referrals when needed

    Return a JSON object with these exact fields:
    {
        "grounded": boolean,
        "medical_accuracy": boolean,
        "completeness": boolean,
        "no_fabrication": boolean,
        "appropriate_tone": boolean,
        "safety": boolean,
        "reasoning": string with detailed explanation
    }"""

    def __init__(self, model="gpt-4o-mini"):
        self.evaluator = ChatOpenAI(model=model, temperature=0)

def evaluate_counseling_response(context_file_path: str, chat_response: str) -> EvaluationResult:
    """
    Evaluates if an HIV counseling chat response is properly grounded in the reference context.
    
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
        - grounded (boolean)
        - medical_accuracy (boolean)
        - completeness (boolean)
        - no_fabrication (boolean)
        - appropriate_tone (boolean)
        - safety (boolean)
        - reasoning (string with detailed explanation)
        """
        
        evaluator = HIVCounselingEvaluation()
        messages = [
            {"role": "system", "content": HIVCounselingEvaluation.evaluation_instructions},
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

# Example usage:
if __name__ == "__main__":
    context_file_path = "/Users/amaris/Desktop/AI_coder/counselling-chatbot/FastAPI/embeddings/HIV_PrEP_knowledge_embedding.json"
    chat_response = "HIV stands for Human Immunodeficiency Virus."
    result = evaluate_counseling_response(context_file_path, chat_response)
    print(f"Evaluation result: {result}")