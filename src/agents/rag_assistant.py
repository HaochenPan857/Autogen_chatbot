import autogen
import logging
from typing import List, Optional, Dict, Any
from ..utils.vector_store import VectorStore
from ..utils.document_loader import DocumentLoader
from ..config import config

logger = logging.getLogger(__name__)

class RAGAssistant:
    """Assistant agent with RAG capabilities"""
    
    def __init__(self):
        self.vector_store = VectorStore()
        self.vector_store.create_or_load()
        
        # Create the assistant agent with RAG capabilities
        self.agent = autogen.AssistantAgent(
            name="rag_assistant",
            system_message="""You are an expert assistant for sustainability report analysis. You will always answer ONLY based on the provided extracted text context below. Do not mention PDF files, and do not ask for more data. If the context contains relevant information, answer as fully as possible using and quoting the context. If not, say that the context does not contain enough information.""",
            llm_config=config.llm_config
        )
    
    def load_documents(self, file_paths: List[str]) -> None:
        """Load documents into the vector store"""
        try:
            logger.info(f"Loading {len(file_paths)} documents...")
            texts = DocumentLoader.load_documents(file_paths)
            self.vector_store.add_texts(texts)
            logger.info("Documents successfully loaded into vector store")
        except Exception as e:
            logger.error(f"Error loading documents: {str(e)}")
            raise
    
    def get_relevant_context(self, query: str, k: Optional[int] = None) -> str:
        """Get relevant context for the query"""
        try:
            chunks = self.vector_store.get_relevant_chunks(query, k)
            context = "\n\nRelevant Context:\n" + "\n---\n".join(chunks)
            logger.info(f"Retrieved {len(chunks)} relevant chunks for query")
            return context
        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            return "Error: Unable to retrieve relevant context"
    
    def enhance_prompt(self, query: str, context: str) -> str:
        """为LLM拼接简明prompt，强调context已是已提取文本，鼓励直接引用内容作答"""
        return f"""
Below is the extracted text context from sustainability reports and/or benchmark documents. This is NOT a PDF, but already extracted text for your analysis.

Extracted Context:
{context}

User Question:
{query}

Please answer ONLY based on the extracted context above. Quote relevant sections where possible. If the context is insufficient, state so clearly."""
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """Process a query using RAG"""
        try:
            # Get relevant context
            context = self.get_relevant_context(query)
            print("\n========= 检索到的 context 预览 =========\n", context, "\n====================================\n")
            # Enhance prompt with context
            enhanced_prompt = self.enhance_prompt(query, context)
            
            return {
                "query": query,
                "context": context,
                "enhanced_prompt": enhanced_prompt
            }
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return {
                "error": str(e),
                "query": query,
                "context": None,
                "enhanced_prompt": None
            }
