from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from typing import List, Optional, Dict, Any
import os
import logging
from ..config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorStore:
    """Enhanced vector store with improved error handling and logging"""
    
    def __init__(self):
        """Initialize vector store with configuration"""
        self.embeddings = HuggingFaceEmbeddings(
            model_name=config.rag.embedding_model
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.rag.chunk_size,
            chunk_overlap=config.rag.chunk_overlap
        )
        self.vector_store = None
        self._ensure_vector_store_dir()
    
    def _ensure_vector_store_dir(self) -> None:
        """Ensure vector store directory exists"""
        os.makedirs(os.path.dirname(config.rag.vector_store_path), exist_ok=True)
    
    def create_or_load(self) -> bool:
        """Create a new vector store or load existing one"""
        try:
            if os.path.exists(config.rag.vector_store_path):
                logger.info("Loading existing vector store...")
                self.vector_store = FAISS.load_local(
                    config.rag.vector_store_path, 
                    self.embeddings
                )
                return True
            logger.info("No existing vector store found.")
            return False
        except Exception as e:
            logger.error(f"Error loading vector store: {str(e)}")
            return False
    
    def add_texts(self, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None) -> None:
        """Add texts to vector store with improved error handling"""
        try:
            logger.info(f"Processing {len(texts)} texts...")
            chunks = self.text_splitter.split_text("\n".join(texts))
            
            if self.vector_store is None:
                logger.info("Creating new vector store...")
                self.vector_store = FAISS.from_texts(
                    chunks, 
                    self.embeddings, 
                    metadatas=metadatas
                )
                self.vector_store.save_local(config.rag.vector_store_path)
            else:
                logger.info("Adding to existing vector store...")
                self.vector_store.add_texts(chunks, metadatas=metadatas)
                self.vector_store.save_local(config.rag.vector_store_path)
            
            logger.info(f"Successfully processed {len(chunks)} chunks.")
        except Exception as e:
            logger.error(f"Error adding texts to vector store: {str(e)}")
            raise
    
    def similarity_search(self, query: str, k: Optional[int] = None) -> List[Document]:
        """Search for similar texts with configurable k"""
        if self.vector_store is None:
            raise ValueError("Vector store not initialized. Call create_or_load() first.")
        
        try:
            k = k or config.rag.retrieval_k
            logger.info(f"Performing similarity search with k={k}")
            results = self.vector_store.similarity_search(query, k=k)
            logger.info(f"Found {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Error during similarity search: {str(e)}")
            raise
    
    def get_relevant_chunks(self, query: str, k: Optional[int] = None) -> List[str]:
        """Get relevant text chunks for a query"""
        documents = self.similarity_search(query, k)
        return [doc.page_content for doc in documents]
