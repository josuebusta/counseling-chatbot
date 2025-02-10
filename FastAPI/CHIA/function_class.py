from semantic_kernel.functions import kernel_function
from .functions import *

class HIVHelperFunctions:
    def __init__(self, websocket, chat_id):
        self.websocket = websocket
        self.chat_id = chat_id

    def register_functions(self):
        """Register native functions with the kernel"""

        # Use the ffunction decorator to define and register the function
        @kernel_function(name="answer_question", description="Get accurate HIV/PrEP information for any question")
        async def answer_question(question: str) -> str:
            """Get accurate HIV/PrEP information for any question"""
            return self.qa_chain.invoke({"query": question}).get("result", 
                "I'm sorry, I couldn't find an answer to that question.")
        
        @kernel_function(name="assess_risk", description="Assess HIV risk factors and provide recommendations")
        async def assess_risk() -> str:
            """Assess HIV risk factors and provide recommendations"""
            return await assess_hiv_risk(self.websocket)

        @kernel_function(name="search_providers", description="Find nearby HIV/PrEP healthcare providers")
        def search_providers(zip_code: str) -> str:
            """Find nearby HIV/PrEP healthcare providers"""
            return search_provider(zip_code)

        @kernel_function(name="assess_status", description="Assess patient's status of change regarding PrEP")
        async def assess_status() -> str:
            """Assess patient's readiness for change regarding PrEP"""
            return await assess_ttm_stage_single_question(self.websocket)

        @kernel_function(name="record_support", description="Record when patient needs additional support")
        async def record_support() -> str:
            """Record when patient needs additional support"""
            return await record_support_request(self.websocket, self.chat_id)
