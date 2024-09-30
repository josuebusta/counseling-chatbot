import os
from dotenv import load_dotenv
import json
from langchain_community.document_loaders import DirectoryLoader, JSONLoader, WebBaseLoader
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain import hub
import autogen
from langchain.tools import BaseTool, StructuredTool, Tool, tool
from autogen.agentchat.contrib.retrieve_user_proxy_agent import RetrieveUserProxyAgent


# CONFIGURATION 
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Load environment variables from .env file
load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

if not api_key:
    raise ValueError("API key not found. Please set OPENAI_API_KEY in your .env file.")

config_list = {
    "model": "gpt-4o-mini", 
    "api_key": api_key  # Directly use the api_key variable
}

# Function description
llm_config_counselor = {
    "temperature": 0,
    "timeout": 300,
    "cache_seed": 43,
    "config_list": config_list,
}


# FUNCTION TO CHECK TERMINATION
# Search provider user proxy agent (Debugging purposes)
def check_termination(x):
    """
    Checks if the message content ends with "TERMINATE" to determine if the conversation should end.

    Parameters:
    x (dict): A dictionary containing the message content

    Returns:
    bool: True if the message ends with "TERMINATE", False otherwise
    """

    print(f"Message content: {x}")
    return x.get("content", "").rstrip().endswith("TERMINATE")



# RAG prompt
# Load the latest version of the prompt
prompt = hub.pull("rlm/rag-prompt", api_url="https://api.hub.langchain.com")

# Load documents from a URL
# loader = JSONLoader('embeddings/HIV_PrEP_knowledge_embedding.json', jq_schema='.quiz', text_content=False)
loader = WebBaseLoader("https://github.com/amarisg25/counselling-chatbot/blob/main/embeddings/HIV_PrEP_knowledge_embedding.json")
data = loader.load()

# Split documents into manageable chunks
text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
all_splits = text_splitter.split_documents(data)
print(f"Number of splits: {len(all_splits)}")
# Check the contents of all_splits
# for i, split in enumerate(all_splits):
#     print(f"Split Document {i}: {split}")

# Store splits in the vector store
vectorstore = Chroma.from_documents(documents=all_splits, embedding=OpenAIEmbeddings(openai_api_key=api_key))

# Initialize the LLM with the correct model
llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)

# Patient (Chatbot-user)
patient = autogen.UserProxyAgent(
    name="patient",
    human_input_mode="ALWAYS",
    max_consecutive_auto_reply=10,
    code_execution_config={"work_dir": "coding", "use_docker": False},
    llm_config=config_list
)
# Initialize RetrievalQA
qa_chain = RetrievalQA.from_chain_type(
    llm, retriever=vectorstore.as_retriever(), chain_type_kwargs={"prompt": prompt}
)

def answer_question(question: str) -> str:
    """
    Answer a question based on HIV PrEP knowledge base.

    :param question: The question to answer.
    :return: The answer as a string.
    """
    result = qa_chain.invoke({"query": question})
    return result.get("result", "I'm sorry, I couldn't find an answer to that question.")


answer = answer_question("What is the schedule for injectable PrEP doses?")
# Print the result
print(answer)

# AGENTS INITALIZATION
# Patient (Chatbot-user)
patient = autogen.UserProxyAgent(
    name="patient",
    human_input_mode="ALWAYS",
    max_consecutive_auto_reply=10,
    code_execution_config={"work_dir": "coding", "use_docker": False},
    llm_config=config_list
)


# Main counselor - answers general questions 
counselor = autogen.UserProxyAgent(
    name="counselor",
    system_message="You are an HIV PrEP counselor. Call the function provided to answer user's questions. ",
    is_termination_msg=lambda x: check_termination(x),
    human_input_mode="NEVER",
    code_execution_config={"work_dir":"coding", "use_docker":False},
    llm_config=config_list
)

# counselor_aid - gives the counselor some context
FAQ_agent = autogen.AssistantAgent(
    name="suggests_retrieve_function",
    is_termination_msg=lambda x: check_termination(x),
    system_message="Suggests function to use to answer HIV/PrEPcounselling questions",
    human_input_mode="NEVER",
    code_execution_config={"work_dir":"coding", "use_docker":False},
    llm_config=config_list
)

autogen.agentchat.register_function(
    answer_question,
    caller=FAQ_agent,
    executor=counselor,
    name="answer_question",
    description="Retrieves embedding data content to answer user's question.",
)

#INITIALIZE THE GROUP CHAT

group_chat = autogen.GroupChat(
    agents=[counselor, FAQ_agent, patient], 
    messages=[], 
    )

manager = autogen.GroupChatManager(groupchat=group_chat, llm_config=config_list, system_message="When asked a question about HIV/PREP, always call the FAQ agent before to help the counselor answer")

manager.initiate_chat(
    patient,
    message="How can I help you?",
)
