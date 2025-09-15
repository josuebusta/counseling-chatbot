"""
RAG (Retrieval-Augmented Generation) system for HIV PrEP counseling.
"""
from langchain.prompts import PromptTemplate
from langchain_community.document_loaders import WebBaseLoader
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from .config import DEFAULT_CONFIG
from .database_config import get_database_path


class RAGSystem:
    """Handles document retrieval and question answering for HIV PrEP counseling."""
    
    def __init__(self, api_key: str, embedding_model: str = None):
        self.api_key = api_key
        self.embedding_model = embedding_model or DEFAULT_CONFIG["embedding_model"]
        self._vectorstore = None
        self._qa_chain = None
        self._setup_rag()
    
    def _setup_rag(self):
        """Initialize the RAG system with vector store and QA chain."""
        if self._vectorstore is None:
            prompt = PromptTemplate(
                template="""You are a knowledgeable HIV prevention counselor.
                - The priority is to use the context to answer the question. 
                - If the answer is in the context, make sure to only use all the information available in the context related to the question to answer the question. Do not make up any additional information.

                Context: {context}

                Question: {question}

                - Use "sex without condoms" instead of "unprotected sex"
                - Use "STI" instead of "STD"

                If the answer is not in the context, do not say "I don't know." Instead, provide helpful guidance based on what you do know but do not mention the answer is not in the context.
                If the answer is in the context, do not add information to the answer. You should use motivational interviewing techniques to answer the question.

                Answer: """,
                input_variables=["context", "question"]
            )

            # Load data from URL instead of local file
            loader = WebBaseLoader("https://raw.githubusercontent.com/amarisg25/embedding-data-chatbot/main/HIV_PrEP_knowledge_embedding.json")
            data = loader.load()
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=DEFAULT_CONFIG["chunk_size"], 
                chunk_overlap=DEFAULT_CONFIG["chunk_overlap"]
            )
            all_splits = text_splitter.split_documents(data)
            print(f"Split into {len(all_splits)} documents")

            # Use centralized database path configuration
            persist_dir = get_database_path("rag_chroma_db")
            
            try:
                self._vectorstore = Chroma(
                    persist_directory=persist_dir, 
                    embedding_function=OpenAIEmbeddings(
                        model=self.embedding_model,
                        openai_api_key=self.api_key
                    )
                )
                print(f"Loaded existing vectorstore from disk: {persist_dir}")
            except Exception as e:
                print(f"Creating new vectorstore: {e}")
                self._vectorstore = Chroma.from_documents(
                    documents=all_splits, 
                    embedding_function=OpenAIEmbeddings(
                        model=self.embedding_model,
                        openai_api_key=self.api_key
                    ),
                    persist_directory=persist_dir
                )
                print(f"Created and stored new vectorstore: {persist_dir}")

            # QA Chain
            llm = ChatOpenAI(model_name="gpt-4o", temperature=0)
            retriever = self._vectorstore.as_retriever(
                search_kwargs={"k": DEFAULT_CONFIG["retrieval_k"]} 
            )
            
            self._qa_chain = RetrievalQA.from_chain_type(
                llm, retriever=retriever, chain_type_kwargs={"prompt": prompt}
            )

    def answer_question(self, question: str) -> str:
        """Answer a question using the RAG system."""
        if not self._vectorstore:
            print("Warning: Vectorstore not initialized!")
            return "I'm sorry, my knowledge base is not properly initialized."
        
        print(f"Searching for answer to: {question}")
        try:
            result = self._qa_chain.invoke({"query": question})
            print(f"Retrieved context: {result}")
            answer = result.get("result", "I'm sorry, I couldn't find an answer to that question.")
            return answer
        except Exception as e:
            print(f"Error retrieving answer: {e}")
            return "I'm sorry, I encountered an error retrieving the answer."
