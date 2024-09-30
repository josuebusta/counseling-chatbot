# agents_initialization.py

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

# RAG prompt
# Load the latest version of the prompt
prompt = hub.pull("rlm/rag-prompt", api_url="https://api.hub.langchain.com")

# Load documents from a URL
# loader = JSONLoader('embeddings/HIV_PrEP_knowledge_embedding.json', jq_schema='.quiz', text_content=False)
loader = WebBaseLoader("https://github.com/amarisg25/counselling-chatbot/blob/main/CHIA/HIV_PrEP_knowledge_embedding.json")
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

# Initialize RetrievalQA
qa_chain = RetrievalQA.from_chain_type(
    llm, retriever=vectorstore.as_retriever(), chain_type_kwargs={"prompt": prompt}
)

# Example question for testing
question = "How do I tell my family that I’m on PrEP?"
result = qa_chain.invoke({"query": question})

# Print the result
print(result["result"])
