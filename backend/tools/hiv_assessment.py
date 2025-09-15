"""
HIV risk assessment and TTM stage assessment tools.
"""
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
from datetime import datetime
from .utils import classify_response, translate_question

load_dotenv("../.env")

# Initialize OpenAI API
OpenAI.api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI()

# List of HIV risk assessment questions
QUESTIONS = [
    ("I'll help assess your HIV risk factors. This will involve a few questions "
     "about your sexual health and activities. Everything you share is completely "
     "confidential, and I'm here to help without judgment. Let's go through this "
     "step by step.\nFirst question: Have you had sex without condoms in the "
     "past 3 months?"),
    "Have you had multiple sexual partners in the past 12 months?",
    "Have you used intravenous drugs or shared needles?",
    ("Do you have a sexual partner who is HIV positive or whose status you "
     "don't know?"),
    "Have you been diagnosed with an STI in the past 12 months?"
]


async def handle_clarification(patient_agent, question, user_response, language):
    """Recursive function to handle clarification requests."""
    # Generate clarification response
    clarification_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "You are here to clarify the question "
                                                "asked by the user. Please provide a "
                                                "clear answer of the information is "
                                                "being asked for."},
                  {"role": "user", "content": f"Question: {question}\nUser response: "
                                              f"{user_response}\n\nPlease provide a "
                                              f"clear answer of the information is "
                                              f"being asked for. Also, re-ask the "
                                              f"question initially asked at the end."}]
    )
    
    # Send the clarification response via patient agent
    clarification_text = clarification_response.choices[0].message.content
    new_response = await patient_agent.get_human_input(clarification_text)
    classification = classify_response(new_response, language)
    
    # If the user is still asking for clarification, recursively handle it
    if classification == "clarification":
        return await handle_clarification(patient_agent, question, new_response, language)
    
    # Otherwise, return the classification for further processing
    return classification, new_response


async def assess_hiv_risk(patient_agent, language_param):
    """Main function for administering questionnaire using patient agent communication."""
    try:
        language = language_param
        print(f"[{language}]")
        
        # Track responses and questions for memo
        assessment_log = []
        affirmative_count = 0
        
        for question in QUESTIONS:
            if language != "English":
                question = translate_question(question, language)

            # Use patient agent's get_human_input instead of direct websocket
            user_response = await patient_agent.get_human_input(question)
            classification = classify_response(user_response, language)
            
            # Log each Q&A
            assessment_log.append(f"Q: {question}\nA: {user_response}")

            if classification == "negative":
                # No need to send status messages - just process
                pass
            elif classification == "affirmative":
                affirmative_count += 1
            elif classification == "stop":
                return translate_question("I understand you want to stop this assessment. "
                                          "Please let me know if you have any other questions.",
                                          language)
            elif classification == "clarification":
                # Use the recursive function to handle clarification
                classification, user_response = await handle_clarification(
                    patient_agent, question, user_response, language)
                
                # Process the response after clarification
                if classification == "negative":
                    pass  # No status message needed
                elif classification == "affirmative":
                    affirmative_count += 1
                elif classification == "stop":
                    return ("I understand you want to stop this assessment. "
                            "Please let me know if you have any other questions.")
                else:
                    pass  # No status message needed
            else:
                # Unclear response - continue to next question
                pass
        
        # Create recommendation
        if affirmative_count > 0:
            risk_level = "elevated"
            recommendation = (
                "Based on your responses, you might benefit from PrEP "
                "(pre-exposure prophylaxis). This is just an initial assessment, "
                "and I recommend discussing this further with a healthcare provider. "
                "Would you like information about PrEP or help finding a provider "
                "in your area?"
            )
        else:
            risk_level = "lower"
            recommendation = (
                "Based on your responses, you're currently at lower risk for HIV. "
                "It's great that you're being proactive about your health! "
                "Continue your safer practices, and remember to get tested regularly. "
                "Would you like to know more about HIV prevention or testing options?"
            )

        # Store complete assessment in teachability
        return translate_question(recommendation, language)

    except Exception as e:
        error_msg = f"Error in assess_hiv_risk: {e}"
        print(error_msg)
        # Store error memo if teachability is available
        if hasattr(patient_agent, 'teachability') and patient_agent.teachability:
            error_memo = (
                "=== HIV Risk Assessment Error ===\n"
                f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Error: {error_msg}\n"
                "Partial Results:\n" + "\n\n".join(
                    assessment_log if 'assessment_log' in locals()
                    else ["No responses recorded"])
            )
            patient_agent.teachability._consider_memo_storage(error_memo)
        return "Sorry, there was an error processing your responses."


async def assess_ttm_stage_single_question(patient_agent, language: str) -> str:
    """Assess the user's stage of change regarding PrEP uptake using TTM."""
    question = """Of course, I will ask you a single question to assess your status of change. 
    Are you currently engaging in Prep uptake on a regular basis? Please respond with the number corresponding to your answer: 
    1. No, and I do not intend to start in the next 6 months.
    2. No, but I intend to start in the next 6 months.
    3. No, but I intend to start in the next 30 days.
    4. Yes, I have been for less than 6 months.
    5. Yes, I have been for more than 6 months."""

    # Use patient agent's get_human_input instead of direct websocket
    response = await patient_agent.get_human_input(translate_question(question, language))
    
    try:
        print(f"Received response: {response}")
        
        # Parse JSON response
        try:
            response_json = json.loads(response)
            # Extract content from JSON
            response_number = response_json.get("content", "")
        except json.JSONDecodeError:
            response_number = response

        # Map response to stage
        stage_map = {
            "1": "Precontemplation",
            "2": "Contemplation",
            "3": "Preparation",
            "4": "Action",
            "5": "Maintenance"
        }
        
        stage = stage_map.get(response_number, "Unclassified")
        
        if stage != "Unclassified":
            return translate_question(f"Based on your response, you are in the "
                                      f"'{stage}' stage of change regarding PrEP "
                                      f"uptake. Let me explain what this means and "
                                      f"discuss possible next steps.", language)
        else:
            return translate_question("I didn't catch your response. Please respond "
                                      "with a number from 1 to 5 corresponding to "
                                      "your situation.", language)
            
    except Exception as e:
        print(f"Error processing response: {e}")
        return translate_question("I'm having trouble processing your response. "
                                  "Please try again with a number from 1 to 5.",
                                  language)
