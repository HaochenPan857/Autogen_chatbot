import logging
import os
import re
import autogen
from typing import Dict, Any, List

from src.agents.rag_assistant import RAGAssistant
from src.agents.scoring_agent import ScoringAgent

logger = logging.getLogger(__name__)

class RouterAgent:
    """
    Router agent that directs user queries to the appropriate specialized agent
    based on the content of the query.
    """
    
    def __init__(self):
        """Initialize the router agent and its specialized agents"""
        self.rag_assistant = None
        self.scoring_agent = None
        self.file_paths = []
        
    def initialize_agents(self):
        """Initialize all specialized agents if they haven't been initialized yet"""
        if self.rag_assistant is None:
            self.rag_assistant = RAGAssistant()
            logger.info("Initialized RAG assistant")
            
        if self.scoring_agent is None:
            self.scoring_agent = ScoringAgent()
            logger.info("Initialized scoring agent")
    
    def load_documents(self, file_paths: List[str], vectorize: bool = False, user_files: List[str] = None) -> bool:
        """
        Load documents into all agents
        
        Args:
            file_paths: List of file paths to load
            vectorize: Whether to vectorize the documents for RAG
            user_files: List of user uploaded file paths (if separate from system files)
            
        Returns:
            True if documents were loaded successfully, False otherwise
        """
        try:
            self.file_paths = file_paths
            
            # Store user files separately if provided
            if user_files:
                self.user_files = user_files
            else:
                self.user_files = file_paths
            
            # Initialize agents if needed
            self.initialize_agents()
            
            # Load documents into RAG assistant (all files including system references)
            rag_success = self.rag_assistant.load_documents(file_paths, vectorize=vectorize)
            
            # Load documents into scoring agent (it doesn't need vectorization)
            # For scoring agent, we only use user uploaded files, not system reference files
            scoring_success = True
            
            return rag_success and scoring_success
        except Exception as e:
            logger.error(f"Error loading documents into agents: {str(e)}")
            return False
    
    def set_user_requirement_files(self, file_paths: List[str]):
        """
        Set user requirement files for the RAG assistant
        
        Args:
            file_paths: List of file paths containing user requirements
        """
        if self.rag_assistant:
            self.rag_assistant.set_user_requirement_files(file_paths)
    
    def route_query(self, query: str, mode: str = None) -> Dict[str, Any]:
        """
        Route the query to the appropriate agent based on its content and mode
        
        Args:
            query: User query string
            mode: Optional mode parameter ('analysis', 'scoring', or 'explore')
            
        Returns:
            Dictionary containing the response and metadata
        """
        # Initialize agents if needed
        self.initialize_agents()
        
        # Check if this is a scoring/rating request based on keywords or explicit mode
        scoring_keywords = ['score', 'scoring', 'rate', 'rating', 'evaluate', 'assessment', 
                           'grade', 'rank', 'benchmark', 'measure']
        
        # Create regex pattern to match any of the scoring keywords
        pattern = r'\b(' + '|'.join(scoring_keywords) + r')\b'
        
        # Determine if we should use scoring agent
        use_scoring = False
        if mode == 'scoring':
            use_scoring = True
        elif mode is None and re.search(pattern, query.lower()):
            use_scoring = True
            
        if use_scoring:
            logger.info("Routing query to scoring agent")
            
            # First, make sure the scoring agent has the documents loaded
            self.scoring_agent.load_documents(self.user_files)
            
            # Process each user document with the scoring agent (not system files)
            results = []
            for file_path in self.user_files:
                # Only process PDF and TXT files for scoring
                if file_path.lower().endswith(('.pdf', '.txt')):
                    logger.info(f"Scoring document: {os.path.basename(file_path)}")
                    try:
                        result = self.scoring_agent.score_document(file_path)
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Error scoring document {os.path.basename(file_path)}: {str(e)}")
                        results.append({
                            "file_path": file_path,
                            "file_name": os.path.basename(file_path),
                            "error": f"Error scoring document: {str(e)}"
                        })
            
            # If no results were generated, provide a fallback response
            if not results:
                return {
                    "agent": "scoring_agent",
                    "query": query,
                    "results": [],
                    "response": "No documents could be scored. Please make sure you've uploaded valid PDF or TXT files."
                }
            
            return {
                "agent": "scoring_agent",
                "query": query,
                "results": results,
                "response": self._format_scoring_results(results)
            }
        elif mode == 'explore':
            # Explore mode: Free conversation based on user uploaded files and chat history
            logger.info("Routing query to explore mode (free conversation with user files only)")
            
            # If we don't have an explore agent yet, create one
            if not hasattr(self, 'explore_agent') or not self.explore_agent:
                from src.agents.rag_assistant import RAGAssistant
                self.explore_agent = RAGAssistant()
                
                # Clear any default metrics data that might have been loaded
                self.explore_agent.metrics_data = None
                
                # Set a special system message for explore mode
                self.explore_agent.agent = autogen.AssistantAgent(
                    name="explore_agent",
                    system_message="""You are an expert sustainability report analyst focused on helping users understand their own documents. 
                    Your task is to have a free-flowing conversation with the user about their uploaded documents.
                    You should ONLY reference information from the user's uploaded documents and your conversation history.
                    DO NOT reference any external metrics, frameworks, or reference documents.
                    Be conversational, helpful, and focus on what the user wants to know about their own documents.
                    If asked about something not in the user's documents, clearly state that the information is not in the uploaded documents.""",
                    llm_config=self.rag_assistant.agent.llm_config
                )
                
                # Reset file paths to ensure no system documents are included
                self.explore_agent.file_paths = []
                self.explore_agent.texts = []
                self.explore_agent.user_req_file_paths = []
                
                # Load only user documents into the explore agent
                if self.user_files:
                    self.explore_agent.load_documents(self.user_files, vectorize=True)
                    logger.info(f"Initialized explore agent with {len(self.user_files)} user documents")
                else:
                    logger.warning("No user files available for explore mode")
                    return {
                        "agent": "explore_agent",
                        "query": query,
                        "response": "No user documents have been uploaded. Please upload documents first to use Explore mode."
                    }
            
            # Process query with the explore agent
            result = self.explore_agent.process_query(query)
            
            return {
                "agent": "explore_agent",
                "query": query,
                "context": result.get("context", ""),
                "enhanced_prompt": result.get("enhanced_prompt", ""),
                "response": result.get("response", "")
            }
        else:
            # Default to RAG assistant for analysis and other queries
            logger.info("Routing query to RAG assistant")
            result = self.rag_assistant.process_query(query)
            
            return {
                "agent": "rag_assistant",
                "query": query,
                "context": result.get("context", ""),
                "enhanced_prompt": result.get("enhanced_prompt", ""),
                "response": result.get("response", "")
            }
    
    def _format_scoring_results(self, results: List[Dict[str, Any]]) -> str:
        """
        Format scoring results into a readable string
        
        Args:
            results: List of scoring results from the scoring agent
            
        Returns:
            Formatted string with scoring results
        """
        if not results:
            return "No scoring results available."
        
        formatted_output = []
        
        for result in results:
            if "error" in result:
                formatted_output.append(f"Error scoring {result.get('file_name', 'document')}: {result['error']}")
            else:
                formatted_output.append(f"## Scoring Results for {result.get('file_name', 'document')}")
                formatted_output.append(f"Timestamp: {result.get('timestamp', 'N/A')}")
                formatted_output.append("")
                formatted_output.append(result.get('scoring_result', 'No detailed scoring available.'))
        
        return "\n".join(formatted_output)
