import autogen
import logging
from typing import Dict, Any, Optional
from ..config import config

logger = logging.getLogger(__name__)

class EnhancedUserProxy(autogen.UserProxyAgent):
    """Enhanced user proxy with RAG support"""
    
    def __init__(self, name="user_proxy", **kwargs):
        super().__init__(
            name=name,
            system_message="""You are an enhanced user proxy that manages RAG-enabled conversations.
            Your responsibilities:
            1. Forward user questions to the RAG assistant
            2. Evaluate response quality and relevance
            3. Request clarification when needed
            4. Maintain conversation context
            5. Handle document loading requests""",
            human_input_mode="NEVER",  # Change to "TERMINATE" or "ALWAYS" as needed
            llm_config=config.llm_config,
            code_execution_config={"use_docker": False},  # Disable Docker requirement
            **kwargs
        )
        self._conversation_context = []
    
    def _update_context(self, message: Dict[str, Any]) -> None:
        """Update conversation context"""
        self._conversation_context.append(message)
        if len(self._conversation_context) > 5:  # Keep last 5 messages
            self._conversation_context.pop(0)
    
    def _evaluate_response(self, response: str) -> bool:
        """Evaluate if the response is satisfactory"""
        # Add your evaluation logic here
        return True
    
    def process_received_message(self, message: Dict[str, Any], sender: Any) -> None:
        """Process received messages with enhanced handling"""
        try:
            logger.info(f"Received message from {sender.name}")
            
            # Update conversation context
            self._update_context(message)
            
            # Evaluate response if it's from the RAG assistant
            if sender.name == "rag_assistant":
                if not self._evaluate_response(message.get("content", "")):
                    logger.info("Response quality check failed")
                    return self.generate_reply(sender, "Please provide more specific information.")
            
            return super().process_received_message(message, sender)
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return self.generate_reply(sender, f"Error: {str(e)}")
    
    def generate_reply(self, messages=None, sender=None, config=None):
        """Generate reply with enhanced context awareness"""
        try:
            # Add any custom reply generation logic here
            return super().generate_reply(messages=messages, sender=sender, config=config)
        except Exception as e:
            logger.error(f"Error generating reply: {str(e)}")
            return f"Error generating reply: {str(e)}"
