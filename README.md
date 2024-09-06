# counselling-chatbot
Chatbot for HIV/PREP counselling

Installation guide:
- Go to file 'counselling-chatbot' directory
- Run 'python3.11 -m venv chatbot-env' to create virtual env
- Run 'source chatbot-env/bin/activate' to activate virtual env
- Run 'pip install -r requirements.txt' to install necessary libraries

Notes: There is a gitignore file with venv and .env (contains API key) files 

# Results
- Baseline Autogen (No function calling) - Example Chat

user_proxy (to assistant):

I would like to assess my HIV risk

--------------------------------------------------------------------------------
assistant (to user_proxy):

Sure, I can help you with that. However, please note that this assessment is not a substitute for professional medical advice. It's always best to consult with a healthcare provider for an accurate understanding of your risk.

Here's a simple risk assessment based on some general factors. Please answer the following questions:

1. Have you had unprotected sex (sex without a condom) in the last year?
2. Have you had multiple sexual partners in the last year?
3. Have you shared needles for drug use in the last year?
4. Have you received a blood transfusion in a country where blood is not tested for HIV in the last year?
5. Have you been diagnosed with or sought treatment for another sexually transmitted infection in the last year?
6. Have you been diagnosed with or sought treatment for hepatitis or tuberculosis in the last year?

Please answer these questions with either 'yes' or 'no'.

--------------------------------------------------------------------------------
Replying as user_proxy. Provide feedback to assistant. Press enter to skip and use auto-reply, or type 'exit' to end the conversation: yes
user_proxy (to assistant):

yes

--------------------------------------------------------------------------------
assistant (to user_proxy):

I'm sorry for the confusion, but I need you to answer each question individually. Let's try again. Please answer 'yes' or 'no' for each question:

1. Have you had unprotected sex (sex without a condom) in the last year?
2. Have you had multiple sexual partners in the last year?
3. Have you shared needles for drug use in the last year?
4. Have you received a blood transfusion in a country where blood is not tested for HIV in the last year?
5. Have you been diagnosed with or sought treatment for another sexually transmitted infection in the last year?
6. Have you been diagnosed with or sought treatment for hepatitis or tuberculosis in the last year?

--------------------------------------------------------------------------------
Replying as user_proxy. Provide feedback to assistant. Press enter to skip and use auto-reply, or type 'exit' to end the conversation: 1.yes/2.yes/3.no/4.yes/5.no/6.yes
user_proxy (to assistant):

1.yes/2.yes/3.no/4.yes/5.no/6.yes

--------------------------------------------------------------------------------
assistant (to user_proxy):

Based on your responses, you have several risk factors for HIV. These include unprotected sex, multiple sexual partners, receiving a blood transfusion in a country where blood is not tested for HIV, and having been diagnosed with or sought treatment for hepatitis or tuberculosis.

However, this is a very basic assessment and does not cover all possible risk factors. It's important to get tested for HIV regularly if you're sexually active or have other risk factors. The only way to know for sure if you have HIV is to get tested.

Please consult with a healthcare provider for a more accurate understanding of your risk and to discuss testing options. Remember, early detection and treatment of HIV can significantly improve health outcomes.

TERMINATE

- 