import os
from dotenv import load_dotenv
import json
from langchain_community.document_loaders import DirectoryLoader, JSONLoader, WebBaseLoader
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain import hub
import autogen
from langchain.tools import BaseTool, StructuredTool, Tool, tool
from autogen.agentchat.contrib.retrieve_user_proxy_agent import RetrieveUserProxyAgent
from functions import assess_hiv_risk, search_provider

# CONFIGURATION 
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Load environment variables from .env file
load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')


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

# Initialize RetrievalQA
retriever = vectorstore.as_retriever()
qa_chain = RetrievalQA.from_chain_type(
    llm, retriever=retriever, chain_type_kwargs={"prompt": prompt}
)

