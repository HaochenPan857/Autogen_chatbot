from typing import List, Optional
from pathlib import Path
import logging
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredMarkdownLoader
)

logger = logging.getLogger(__name__)

class DocumentLoader:
    """Document loader supporting multiple file types"""
    
    SUPPORTED_EXTENSIONS = {
        '.pdf': PyPDFLoader,
        '.txt': TextLoader,
        '.md': UnstructuredMarkdownLoader
    }
    
    @classmethod
    def load_document(cls, file_path: str) -> List[str]:
        """Load a single document and return its content as text"""
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            loader_class = cls.SUPPORTED_EXTENSIONS.get(path.suffix.lower())
            if not loader_class:
                raise ValueError(f"Unsupported file type: {path.suffix}")
            
            logger.info(f"Loading document: {file_path}")
            loader = loader_class(file_path)
            documents = loader.load()
            
            # Extract text content from documents
            texts = [doc.page_content for doc in documents]
            logger.info(f"Successfully loaded {len(texts)} pages from {file_path}")
            
            return texts
            
        except Exception as e:
            logger.error(f"Error loading document {file_path}: {str(e)}")
            raise
    
    @classmethod
    def load_documents(cls, file_paths: List[str]) -> List[str]:
        """Load multiple documents and return their contents"""
        all_texts = []
        for file_path in file_paths:
            try:
                texts = cls.load_document(file_path)
                all_texts.extend(texts)
            except Exception as e:
                logger.error(f"Skipping file {file_path} due to error: {str(e)}")
                continue
        
        logger.info(f"Successfully loaded {len(all_texts)} total pages from {len(file_paths)} documents")
        return all_texts
