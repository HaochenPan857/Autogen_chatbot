import autogen
import logging
import sys
import os
import json
from typing import List, Optional, Dict, Any

# Add project root directory to system path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.utils.document_loader import DocumentLoader
from src.utils.scoring_criteria import ScoringCriteria
from src.config import config

# Import Google Gemini API if available
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

logger = logging.getLogger(__name__)

class ScoringAgent:
    """Agent for scoring sustainability reports based on predefined criteria"""
    
    def __init__(self):
        self.document_loader = DocumentLoader()
        self.texts = []
        self.file_paths = []
        
        # Load scoring criteria
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        self.criteria_file_path = os.path.join(project_root, 'Report_score.json')
        self.scoring_criteria = None
        
        if os.path.exists(self.criteria_file_path):
            self.scoring_criteria = ScoringCriteria.load_criteria(self.criteria_file_path)
            logger.info(f"Loaded scoring criteria from {self.criteria_file_path}")
        else:
            logger.error(f"Scoring criteria file not found at {self.criteria_file_path}")
        
        # Set up the appropriate LLM based on provider
        if config.llm.provider == "google" and GEMINI_AVAILABLE:
            # Configure Gemini
            if config.llm.google_api_key:
                genai.configure(api_key=config.llm.google_api_key)
                logger.info(f"Configured Google Gemini with model: {config.llm.model}")
                self.gemini_model = genai.GenerativeModel(config.llm.model)
            else:
                logger.error("Google API key not found. Please set GOOGLE_API_KEY in your environment variables.")
        
        # Create the assistant agent with scoring capabilities
        llm_config = config.llm.to_dict()
        
        self.agent = autogen.AssistantAgent(
            name="scoring_agent",
            system_message="""You are an expert sustainability report scoring assistant. 
            Your task is to evaluate sustainability reports against specific criteria and provide detailed scores and feedback.""",
            llm_config=llm_config
        )
    
    def load_documents(self, file_paths: List[str]) -> bool:
        """
        Load documents for scoring
        
        Args:
            file_paths: List of file paths to load
            
        Returns:
            True if documents were loaded successfully, False otherwise
        """
        try:
            self.file_paths = file_paths
            self.texts = []
            
            for file_path in file_paths:
                text = self.document_loader.load_document(file_path)
                if text:
                    self.texts.append(text)
                    logger.info(f"Loaded document for scoring: {file_path}")
                else:
                    logger.warning(f"Failed to load document: {file_path}")
            
            return len(self.texts) > 0
        except Exception as e:
            logger.error(f"Error loading documents for scoring: {str(e)}")
            return False
    
    def create_scoring_prompt(self, document_text: str) -> str:
        """
        Create a prompt for scoring a document
        
        Args:
            document_text: Text content of the document to score
            
        Returns:
            Formatted prompt for the LLM
        """
        if not self.scoring_criteria:
            return "Error: Scoring criteria not loaded."
        
        formatted_criteria = ScoringCriteria.format_criteria_for_prompt(self.scoring_criteria)
        
        prompt = f"""# SUSTAINABILITY REPORT SCORING TASK

## DOCUMENT TO SCORE
The following text has been extracted from a sustainability report for scoring:

{document_text[:50000]}  # Limit text to avoid token limits

## SCORING CRITERIA
Please score the sustainability report based on the following criteria:

{formatted_criteria}

## SCORING INSTRUCTIONS
For each category and dimension listed above:

1. Provide a score from 0-5 where:
   - 0: Not addressed at all
   - 1: Minimally addressed with significant gaps
   - 2: Partially addressed with notable gaps
   - 3: Adequately addressed with some gaps
   - 4: Well addressed with minor gaps
   - 5: Comprehensively addressed with no significant gaps

2. For each dimension, provide:
   - Score (0-5)
   - Brief justification (1-2 sentences)
   - Evidence from the report (direct quotes or specific references)
   - Recommendations for improvement

3. For each category, calculate an average score of its dimensions.

4. Provide an overall report score (average of all category scores).

5. Include a summary assessment highlighting key strengths and areas for improvement.

Present your evaluation in a clear, structured format with appropriate headings and sections.
"""
        return prompt
    
    def score_document(self, file_path: str) -> Dict[str, Any]:
        """
        Score a single document based on the scoring criteria
        
        Args:
            file_path: Path to the document to score
            
        Returns:
            Dictionary containing the scoring results
        """
        try:
            # Load the document
            document_text = self.document_loader.load_document(file_path)
            if not document_text:
                logger.error(f"Failed to load document for scoring: {file_path}")
                return {"error": f"Failed to load document: {file_path}"}
            
            # Create the scoring prompt
            scoring_prompt = self.create_scoring_prompt(document_text)
            
            # Process with the appropriate LLM
            if config.llm.provider == "google" and GEMINI_AVAILABLE and hasattr(self, 'gemini_model'):
                logger.info("Using Google Gemini for scoring")
                try:
                    gemini_response = self.gemini_model.generate_content(scoring_prompt)
                    
                    # Check if the response is valid
                    if gemini_response and hasattr(gemini_response, 'text'):
                        response_text = gemini_response.text
                        logger.info("Successfully generated scoring with Gemini")
                    else:
                        logger.warning("Gemini returned an empty or invalid response, falling back to OpenAI")
                        response_text = self.agent.generate_reply([
                            {"role": "user", "content": scoring_prompt}
                        ])
                except Exception as gemini_error:
                    logger.error(f"Error with Gemini API: {str(gemini_error)}")
                    # Fallback to OpenAI
                    logger.info("Falling back to OpenAI for scoring")
                    response_text = self.agent.generate_reply([
                        {"role": "user", "content": scoring_prompt}
                    ])
            else:
                # Use the OpenAI agent
                logger.info("Using OpenAI for scoring")
                response_text = self.agent.generate_reply([
                    {"role": "user", "content": scoring_prompt}
                ])
            
            # Format the response
            result = {
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
                "scoring_result": response_text,
                "timestamp": self._get_timestamp()
            }
            
            return result
        except Exception as e:
            logger.error(f"Error scoring document: {str(e)}")
            return {"error": f"Error scoring document: {str(e)}"}
    
    def _get_timestamp(self) -> str:
        """Get current timestamp string"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
