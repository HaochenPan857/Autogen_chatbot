import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union

# Load environment variables
load_dotenv()

class RAGConfig(BaseModel):
    """RAG specific configuration"""
    chunk_size: int = Field(default=1000, description="Size of text chunks for splitting documents")
    chunk_overlap: int = Field(default=200, description="Overlap between text chunks")
    embedding_model: str = Field(
        default="sentence-transformers/all-mpnet-base-v2",
        description="Model to use for embeddings"
    )
    retrieval_k: int = Field(default=4, description="Number of documents to retrieve")
    vector_store_path: str = Field(
        default=os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "vector_store"),
        description="Path to vector store"
    )

class LLMConfig(BaseModel):
    """LLM configuration"""
    provider: str = Field(default="google", description="Provider for LLM (openai or google)")
    model: str = Field(default="models/gemini-1.5-pro", description="Model to use for LLM")
    temperature: float = Field(default=0.7, description="Temperature for LLM")
    openai_api_key: str = Field(default=os.getenv("OPENAI_API_KEY"), description="API key for OpenAI")
    google_api_key: str = Field(default=os.getenv("GOOGLE_API_KEY"), description="API key for Google Gemini")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to AutoGen format"""
        if self.provider == "openai":
            return {
                "config_list": [{
                    "model": self.model,
                    "api_key": self.openai_api_key,
                }],
                "temperature": self.temperature
            }
        elif self.provider == "google":
            return {
                "config_list": [{
                    "model": self.model,
                    "api_key": self.google_api_key,
                }],
                "temperature": self.temperature
            }

class Config:
    """Main configuration class"""
    def __init__(self):
        self.rag = RAGConfig()
        self.llm = LLMConfig()
        
    @property
    def llm_config(self) -> Dict[str, Any]:
        return self.llm.to_dict()

# Create global config instance
config = Config()
