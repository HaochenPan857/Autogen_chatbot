import autogen
import logging
import sys
import os
from typing import List, Optional, Dict, Any

# 添加项目根目录到系统路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.utils.vector_store import VectorStore
from src.utils.document_loader import DocumentLoader
from src.utils.metrics_loader import MetricsLoader
from src.config import config

# Import Google Gemini API if available
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

logger = logging.getLogger(__name__)

class RAGAssistant:
    """Assistant agent with RAG capabilities"""
    
    def __init__(self):
        self.vector_store = VectorStore()
        self.vector_store.create_or_load()
        # Initialize document storage
        self.texts = []
        self.file_paths = []
        self.user_req_file_paths = []
        self.vectorized = False
        self.metrics_data = None
        
        # Load sustainability metrics reference data if available
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        metrics_file_path = os.path.join(project_root, 'data', 'documents', 'reference', 'metrics_reference.json')
        
        # Try to load from the project path
        if os.path.exists(metrics_file_path):
            self.metrics_data = MetricsLoader.load_metrics_from_json(metrics_file_path)
            logger.info(f"Loaded metrics reference data from {metrics_file_path}")
        else:
            # Try to load from the original path if project path doesn't exist
            original_path = r"C:\Users\panha\CascadeProjects\autogen-rag-test\data\documents\reference\test reference.json"
            if os.path.exists(original_path):
                self.metrics_data = MetricsLoader.load_metrics_from_json(original_path)
                logger.info(f"Loaded metrics reference data from {original_path}")
            else:
                logger.warning("No metrics reference data found")
        
        # Set up the appropriate LLM based on provider
        if config.llm.provider == "google" and GEMINI_AVAILABLE:
            # Configure Gemini
            if config.llm.google_api_key:
                genai.configure(api_key=config.llm.google_api_key)
                logger.info(f"Configured Google Gemini with model: {config.llm.model}")
                self.gemini_model = genai.GenerativeModel(config.llm.model)
            else:
                logger.error("Google API key not found. Please set GOOGLE_API_KEY in your environment variables.")
                # Fall back to OpenAI
                # config.llm.provider = "openai"
                # logger.info("Falling back to OpenAI provider.")
        
        # Create the assistant agent with RAG capabilities
        # Use the to_dict method to get the correct config format
        llm_config = config.llm.to_dict()
        
        self.agent = autogen.AssistantAgent(
            name="rag_assistant",
            system_message="""You are an expert assistant for sustainability report analysis. You will always answer ONLY based on the provided extracted text context below. Do not mention PDF files, and do not ask for more data. If the context contains relevant information, answer as fully as possible using and quoting the context. If not, say that the context does not contain enough information.""",
            llm_config=llm_config
        )
    
    def load_documents(self, file_paths: List[str], vectorize: bool = True) -> None:
        """Load documents into the vector store
        
        Args:
            file_paths: List of paths to documents
            vectorize: Whether to vectorize documents for retrieval (True) or just load them for direct use (False)
        """
        try:
            logger.info(f"Loading {len(file_paths)} documents...")
            self.texts = DocumentLoader.load_documents(file_paths)
            
            # Store the file paths for reference
            self.file_paths = file_paths
            
            # Only add to vector store if vectorization is requested
            if vectorize:
                logger.info("Vectorizing documents for efficient retrieval...")
                self.vector_store.add_texts(self.texts)
                self.vectorized = True
                logger.info("Documents successfully vectorized and loaded into vector store")
            else:
                logger.info("Documents loaded without vectorization for direct LLM processing")
                self.vectorized = False
        except Exception as e:
            logger.error(f"Error loading documents: {str(e)}")
            raise
    
    def set_user_requirement_files(self, file_paths: List[str]) -> None:
        """Set the user requirement files to give them higher priority during retrieval
        
        Args:
            file_paths: List of paths to user requirement files
        """
        self.user_req_file_paths = file_paths
        logger.info(f"Set {len(file_paths)} user requirement files")
    
    def get_relevant_context(self, query: str, k: Optional[int] = None) -> str:
        """Get relevant context for the query with priority given to user requirement documents"""
        try:
            # Get chunks from vector store for semantic search
            chunks = self.vector_store.get_relevant_chunks(query, k)
            logger.info(f"Retrieved {len(chunks)} relevant chunks from vector store")
            
            # Initialize collections for different document types
            user_req_texts = []
            reference_texts = []
            
            # Process reference documents from the reference directory
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
            ref_dir = os.path.join(project_root, 'data', 'documents', 'reference')
            
            if os.path.exists(ref_dir):
                # Get all reference documents
                ref_files = []
                for root, _, files in os.walk(ref_dir):
                    for file in files:
                        if file.lower().endswith(('.pdf', '.txt')):
                            ref_files.append(os.path.join(root, file))
                
                # Load content from reference documents
                for ref_file in ref_files:
                    try:
                        texts = DocumentLoader.load_document(ref_file)
                        reference_texts.extend(texts)
                        logger.info(f"Loaded reference document: {ref_file}")
                    except Exception as e:
                        logger.error(f"Error loading reference document {ref_file}: {str(e)}")
            
            # Process user uploaded documents
            for file_path in self.user_req_file_paths:
                try:
                    texts = DocumentLoader.load_document(file_path)
                    user_req_texts.extend(texts)
                    logger.info(f"Loaded user requirement file: {file_path}")
                except Exception as e:
                    logger.error(f"Error loading user requirement file {file_path}: {str(e)}")
            
            # Log document statistics
            logger.info(f"Loaded {len(user_req_texts)} text chunks from user documents")
            logger.info(f"Loaded {len(reference_texts)} text chunks from reference documents")
            
            # Limit texts to avoid token limits
            max_user_chunks = 250
            max_ref_chunks = 250
            
            if len(user_req_texts) > max_user_chunks:
                logger.info(f"Limiting user document chunks from {len(user_req_texts)} to {max_user_chunks}")
                user_req_texts = user_req_texts[:max_user_chunks]
                
            if len(reference_texts) > max_ref_chunks:
                logger.info(f"Limiting reference document chunks from {len(reference_texts)} to {max_ref_chunks}")
                reference_texts = reference_texts[:max_ref_chunks]
            
            # Build the context with clear sections
            context_parts = []
            
            # Add user requirements if available
            if user_req_texts:
                user_context = "\n\n=== USER UPLOADED DOCUMENTS ===\n" + "\n---\n".join(user_req_texts)
                context_parts.append(user_context)
            
            # Add reference documents if available
            if reference_texts:
                ref_context = "\n\n=== REFERENCE DOCUMENTS ===\n" + "\n---\n".join(reference_texts)
                context_parts.append(ref_context)
            
            # Add vector search results
            if chunks:
                chunks_context = "\n\n=== RELEVANT CHUNKS FROM VECTOR SEARCH ===\n" + "\n---\n".join(chunks)
                context_parts.append(chunks_context)
            
            # Combine all context parts
            context = "\n\n".join(context_parts)
            
            # Log context statistics
            logger.info(f"Created context with {len(context)} characters from {len(user_req_texts)} user chunks, "
                       f"{len(reference_texts)} reference chunks, and {len(chunks)} vector search chunks")
            
            return context
        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            return "Error: Unable to retrieve relevant context"
    
    def enhance_prompt(self, query: str, context: str) -> str:
        """为LLM拼接简明prompt，处理用户需求和系统文档的组合"""
        
        # Format metrics data for inclusion in the prompt if available
        metrics_section = ""
        if self.metrics_data:
            metrics_section = MetricsLoader.format_metrics_for_prompt(self.metrics_data)
            logger.info("Added metrics reference data to prompt")
        
        # Check if the context contains user uploaded documents
        has_user_documents = "=== USER UPLOADED DOCUMENTS ===" in context
        
        # Build a more structured prompt that includes metrics for analysis
        prompt = f"""
# SUSTAINABILITY REPORT ANALYSIS

## EXTRACTED TEXT CONTEXT
The following text has been extracted from sustainability reports and/or benchmark documents for analysis:

{context}

## USER QUESTION
{query}
"""

        # Add metrics section if available
        if metrics_section:
            prompt += f"""

## REFERENCE METRICS AND DEFINITIONS
{metrics_section}
"""

        # Add analysis instructions
        if has_user_documents:
            prompt += f"""

## ANALYSIS INSTRUCTIONS
Please analyze the uploaded sustainability report using the reference metrics and definitions provided. Follow these guidelines:

1. Structure your analysis according to the key sustainability metrics and frameworks mentioned in the reference section.
2. For each relevant metric or framework found in the report, provide:
   - How the organization is performing against this metric
   - Any targets, commitments, or strategies mentioned
   - Areas of strength and potential improvement
   - Compliance with relevant standards (IFRS, GRI, SASB, etc.)

3. Include direct quotes or evidence from the report to support your analysis.
4. If certain metrics are not addressed in the report, note these gaps.
5. Conclude with an overall assessment of the organization's sustainability reporting quality and completeness.

Present your analysis in a clear, structured format with appropriate headings and sections.
"""
        else:
            prompt += f"""

## ANALYSIS INSTRUCTIONS
Please analyze the context thoroughly and provide a detailed answer. Follow these guidelines:

1. Carefully examine all parts of the context, even if information appears fragmented or scattered across different sections.
2. Look for both direct and indirect references to the query topic.
3. If you find relevant information, synthesize it into a coherent answer, quoting specific sections.
4. For governance or board-related queries, look for mentions of directors, board members, committees, governance structure, etc.
5. If after thorough examination you determine the context truly lacks information about the query, state so clearly.

Your goal is to extract as much relevant information as possible from the provided context, even if it requires connecting details from different parts of the text.
"""
        
        return prompt
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """处理用户查询，根据是否向量化决定检索方式"""
        try:
            # Handle differently based on whether documents were vectorized
            if self.vectorized:
                # Get relevant context using vector search
                context = self.get_relevant_context(query, k=500)  # 增加检索数量到500个chunk

            else:
                # If not vectorized, use all document texts as context
                context = "\n\nRelevant Context:\n" + "\n---\n".join(self.texts[:15])
                # print("\n========= 未向量化，使用前15个文档作为context =========\n")
            
            # Enhance the prompt with context
            enhanced_prompt = self.enhance_prompt(query, context)
            print("================enhanced_prompt================",enhanced_prompt[:100])
            print("================context================",context[:100])
            # Use the appropriate model based on provider
            if config.llm.provider == "google" and GEMINI_AVAILABLE and hasattr(self, 'gemini_model'):
                try:
                    # Use Google Gemini API directly
                    logger.info("Using Google Gemini for response generation")
                    gemini_response = self.gemini_model.generate_content(enhanced_prompt)
                    
                    # Check if the response is valid
                    if gemini_response and hasattr(gemini_response, 'text'):
                        response = gemini_response.text
                        logger.info("Successfully generated response with Gemini")
                    else:
                        logger.warning("Gemini returned an empty or invalid response, falling back to OpenAI")
                        response = self.agent.generate_reply([
                            {"role": "user", "content": enhanced_prompt}
                        ])
                except Exception as gemini_error:
                    logger.error(f"Error with Gemini API: {str(gemini_error)}")
                    # Fallback to OpenAI with a compatible model
                    logger.info("Falling back to OpenAI with gpt-3.5-turbo model")
                    # Use the OpenAI agent that's already configured correctly
                    response = self.agent.generate_reply([
                        {"role": "user", "content": enhanced_prompt}
                    ])
            else:
                # Send the enhanced prompt to the LLM using generate_reply
                response = self.agent.generate_reply([
                    {"role": "user", "content": enhanced_prompt}
                ])
            
            return {
                'response': response,
                'context': context,
                'enhanced_prompt': enhanced_prompt
            }
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return {
                'response': f"Error: {str(e)}",
                'context': "",
                'enhanced_prompt': ""
            }
if __name__ == "__main__":
    # 示例用法：初始化、加载文档、提问
    assistant = RAGAssistant()
    
    # 假设你有一些文件路径
    file_paths = [r"C:\Users\panha\CascadeProjects\autogen-rag-test\data\documents\reference\effects-analysis.pdf"]
    assistant.load_documents(file_paths)
    
    # 使用process_query方法，这样可以打印enhanced prompt
    query = "What are the key sustainability goals mentioned?"
    result = assistant.process_query(query)
    
    # print("\n========= RAG LLM Answer =========\n")
    if result.get("enhanced_prompt"):
        answer = assistant.agent.generate_reply([
            {"role": "user", "content": result["enhanced_prompt"]}
        ])
        print(answer)
    else:
        print("[Error] Unable to generate answer. Please check your documents and retrieval pipeline.")
