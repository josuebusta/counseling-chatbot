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
import pandas as pd


# CONFIGURATION 
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Load environment variables from .env file
load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

if not api_key:
    raise ValueError("API key not found. Please set OPENAI_API_KEY in your .env file.")



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
 
# Initialize RetrievalQA
retriever = vectorstore.as_retriever()
qa_chain = RetrievalQA.from_chain_type(
    llm, retriever=retriever, chain_type_kwargs={"prompt": prompt}
)

from ragas import evaluate

from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_recall,
    context_precision,
    answer_correctness
)
from datasets import Dataset

# Testing the evaluation metrics of exact questions from dataset
data_questions = ["What is HIV?", 
             "How does HIV attack the human immune system",
             "How is HIV transmitted?",
             "What are the stages of HIV infection?",
             "What is PrEP?",
             "Is PrEP suitable for MSM with different sexual behaviors?",
             "What do I do if family members find out I’m on PrEP?",
             "What is the schedule for injectable PrEP doses?"
            ]


answers_dataset = []
contexts_dataset = []

# Testing the evaluation metrics of questions from the dataset, but not asked in the same way as in the dataset
data_questions_variation = [
    "Can you explain what HIV is?",
    "In what way does HIV impact the human immune system?",
    "What are the modes of transmission for HIV?",
    "What phases are involved in HIV infection?",
    "What does PrEP stand for?",
    "Is PrEP appropriate for MSM with various sexual practices?",
    "How should I handle it if my family discovers I'm on PrEP?",
    "How often should I get the injectable PrEP shot?"
]

answers_dataset_variation = []
contexts_dataset_variation = []


# Ground truths for the questions in the dataset
ground_truths = [["HIV stands for Human Immunodeficiency Virus. It attacks the body's immune system, making it harder to fight off infections and diseases. If not treated, it can lead to AIDS (Acquired Immunodeficiency Syndrome)"],
                ["HIV attacks the immune system by targeting CD4 cells, also known as T cells. These cells help the body fight infections. HIV enters these cells, uses them to make more copies of itself, and then destroys them. Over time, the number of CD4 cells drops, making it harder for the body to fight off infections and diseases."],
                ["HIV can spread through certain body fluids like blood, semen, vaginal fluids, rectal fluids, and breast milk. Common ways it transmits include unprotected sex, sharing needles, and from mother to baby during birth or breastfeeding."],
                ["There are three stages of HIV infection: \n Acute HIV Infection: This happens 2-4 weeks after getting the virus. Symptoms can feel like the flu, such as fever, sore throat, and swollen glands.\nChronic HIV Infection: Also called clinical latency. The virus is still active but reproduces at low levels. People might not have symptoms or only mild ones.\nAIDS: This is the final stage. The immune system is badly damaged, and people get severe illnesses or infections. Symptoms can include rapid weight loss, extreme tiredness, and prolonged swelling of the lymph glands."],
                [ "PrEP, or Pre-Exposure Prophylaxis, is a preventive treatment for people who do not have HIV but are more likely to have HIV exposure. PrEP involves taking a medication that helps prevent the virus from establishing an infection if you are exposed to it."],
                ["Yes, PrEP is suitable for MSM with different sexual behaviors. It is important to discuss your sexual practices with your healthcare provider to determine the best PrEP regimen for you."],
                ["If your family finds out you're on PrEP and you're worried about their reaction, try these steps:\n1. Stay Calm: Keep calm and approach the situation with a clear mind.\n2. Explain PrEP: Tell them PrEP is a medication that helps prevent HIV and that it’s a smart choice for your health.\n3. Address Concerns: Be ready to answer questions and provide information, and seek support from a trusted friend, healthcare provider, or counselor if needed.\nRemember, taking care of your health is important, and you deserve to make choices that are right for you."],
                ["First Injection: You'll receive a 600mg (3mL) shot of cabotegravir in your gluteal muscle. Second Injection: You'll get another 600mg shot one month after the first. Ongoing Dosing Schedule: After the initial two shots, receive a 600mg injection every 8 weeks (2 months), with a +/- 7-day window considered on time."]]

# Questions that are not in the dataset
new_data_questions = [
    "How can I tell if I have HIV?",
    "I slept with someone who tested positive for HIV. Should I start taking PrEP now?",
    "How to start PrEP without using insurance?",
    "Do doctors need parent permission to prescribe PrEP for underage patients?",
    "I can’t go to a doctor’s office. Can I be prescribed PrEP virtually?",
    "How much does PrEP cost?",
    "Are there any cures for HIV?",
    "How can I convince someone to start PrEP if they think they don’t need to?",
    "I’m scared to tell a partner that I have HIV. How can I do it?",
    "Can I stop taking PrEP when my partner and I are exclusive?"
]

answers_new_dataset = []
contexts_new_dataset = []



# Testing the evaluation metrics of questions that are not in the dataset

retriever = vectorstore.as_retriever()
qa_chain = RetrievalQA.from_chain_type(
    llm, retriever=retriever, chain_type_kwargs={"prompt": prompt}
)


# Inference
for query in data_questions:
  answers_dataset.append(qa_chain.invoke(query))
  contexts_dataset.append([docs.page_content for docs in retriever.invoke(query)])

for query in data_questions_variation:
  answers_dataset_variation.append(qa_chain.invoke(query))
  contexts_dataset_variation.append([docs.page_content for docs in retriever.invoke(query)])

for query in new_data_questions:
    answer = qa_chain.invoke(query)
    answers_new_dataset.append(answer)
    context = retriever.invoke(query)
    contexts_new_dataset.append([docs.page_content for docs in context] if context else ["No context found"])

# To dict
dataframe_dataset = {
    "question": data_questions,
    "answer": answers_dataset,
    "contexts": contexts_dataset,
    "reference": ground_truths
}

dataframe_dataset_variation = {
    "question": data_questions_variation,
    "answer": answers_dataset_variation,
    "contexts": contexts_dataset_variation,
    "reference": ground_truths
}

dataframe_new_dataset = {
    "question": new_data_questions,
    "answer": answers_new_dataset,
    "contexts": contexts_new_dataset,
}

print("LENGTH questions", len(new_data_questions))
print("LENGTH answers", len(answers_new_dataset))
print("LENGTH contexts", len(contexts_new_dataset))



# Convert dict to dataset
dataset = Dataset.from_dict(dataframe_dataset)
dataset_variation = Dataset.from_dict(dataframe_dataset_variation)
dataset_new = Dataset.from_dict(dataframe_new_dataset)

def convert_to_string_dataset(example):
    example['answer'] = str(example['answer'])
    example['reference'] = str(example['reference'])
    return example

def convert_to_string_not_in_dataset(example):
    example['answer'] = str(example['answer'])
    return example

# Apply the conversion to each field in the dataset
dataset = dataset.map(convert_to_string_dataset)
dataset_variation = dataset_variation.map(convert_to_string_dataset)
dataset_new = dataset_new.map(convert_to_string_not_in_dataset)

result = evaluate(
    dataset = dataset, 
    metrics=[
        context_precision,
        context_recall,
        faithfulness,
        answer_relevancy,
        answer_correctness
    ],
)

result_variation = evaluate(
    dataset = dataset_variation, 
    metrics=[
        context_precision,
        context_recall,
        faithfulness,
        answer_relevancy,
        answer_correctness
    ],
)

result_new = evaluate(
    dataset = dataset_new, 
    metrics=[
        faithfulness,
        answer_relevancy,
    ],
)

print("Evaluation complete")

df = result.to_pandas()
df.to_excel('evaluation_results.xlsx', index=False)
df_loaded = pd.read_excel('evaluation_results.xlsx')

df_variation = result_variation.to_pandas()
df_variation.to_excel('evaluation_results_variation.xlsx', index=False)
df_variation_loaded = pd.read_excel('evaluation_results_variation.xlsx')

df_new = result_new.to_pandas()
df_new.to_excel('evaluation_results_new.xlsx', index=False)
df_new_loaded = pd.read_excel('evaluation_results_new.xlsx')
