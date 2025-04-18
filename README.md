# counselling-chatbot
Chatbot for HIV/PREP counselling

Installation guide:
- Go to current file 'counselling-chatbot' directory
- Run 'python3.11 -m venv counselling-env' to create virtual env
- Run 'source counselling-env/bin/activate' to activate virtual env 
- Run 'pip install -r requirements.txt' to install necessary libraries


- To run backend: 
    - cd FastAPI, uvicorn main:app --reload
    - backend changes will be reflected immediately

- To run frontend: 
    - cd chatbot-ui-shadcn, npm run build then npm run start 
    - this needs to be ran each time you want to see changes to the frontend


Notes: There is a gitignore file with venv and .env (contains API key) files 

