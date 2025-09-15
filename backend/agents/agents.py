"""
Agent factory for the HIV PrEP counseling system.
"""
import autogen
from typing import List
from .counselor_agent import CounselorAgent
from .assistant_agent import AssistantAgent


class AgentFactory:
    """Factory for creating different types of agents."""

    @staticmethod
    def create_counselor_agent(
            llm_config: dict, teachability_flag: bool = True
    ) -> CounselorAgent:
        """Create the primary counselor agent."""
        return CounselorAgent(llm_config, teachability_flag)

    @staticmethod
    def create_counselor_assistant_agent(
            llm_config: dict, teachability_flag: bool = True
    ) -> AssistantAgent:
        """Create the counselor assistant agent."""
        return AssistantAgent(llm_config, teachability_flag)

    @staticmethod
    def create_patient_agent(llm_config: dict,
                             websocket=None) -> autogen.UserProxyAgent:
        """Create the patient proxy agent."""
        agent = autogen.UserProxyAgent(
            name="patient",
            human_input_mode="ALWAYS",  # Need human input for function calls
            max_consecutive_auto_reply=10,
            code_execution_config={"work_dir": "coding", "use_docker": False},
            llm_config=llm_config
        )
        # Store the websocket in the agent for use in get_human_input
        if websocket:
            agent.websocket = websocket

            # Override the get_human_input method to use WebSocket
            async def get_human_input_websocket(prompt: str) -> str:
                """Get human input via WebSocket instead of console."""
                try:
                    if (not hasattr(agent, 'websocket') or
                            agent.websocket is None):
                        print("WebSocket is None, returning empty string")
                        return ""

                    # Send the prompt to the user via websocket
                    await agent.websocket.send_text(prompt)

                    # Wait for user response
                    user_response = await agent.websocket.receive_text()
                    print(f"Received user input: {user_response}")
                    return user_response
                except Exception as e:
                    print(f"Error getting human input: {e}")
                    return ""

            # Override the get_human_input method
            agent.get_human_input = get_human_input_websocket

        return agent

    @staticmethod
    def create_all_agents(
            llm_config: dict, teachability_flag: bool = True, websocket=None
    ) -> List[autogen.Agent]:
        """Create all agents for the counseling system."""
        counselor = AgentFactory.create_counselor_agent(llm_config,
                                                        teachability_flag)
        counselor_assistant = AgentFactory.create_counselor_assistant_agent(
            llm_config, teachability_flag)
        patient = AgentFactory.create_patient_agent(llm_config, websocket)

        # Return the underlying autogen agents
        return [
            counselor.get_agent(), patient, counselor_assistant.get_agent()
        ]

    @staticmethod
    def create_agent_wrappers(
            llm_config: dict, teachability_flag: bool = True, websocket=None
    ) -> tuple:
        """Create agent wrapper objects for the counseling system."""
        counselor = AgentFactory.create_counselor_agent(llm_config,
                                                        teachability_flag)
        counselor_assistant = AgentFactory.create_counselor_assistant_agent(
            llm_config, teachability_flag)
        patient = AgentFactory.create_patient_agent(llm_config, websocket)

        return counselor, counselor_assistant, patient
