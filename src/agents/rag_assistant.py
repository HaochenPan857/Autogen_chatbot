import autogen
import logging
import sys
import os
from typing import List, Optional, Dict, Any

# 添加项目根目录到系统路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.utils.vector_store import VectorStore
from src.utils.document_loader import DocumentLoader
from src.config import config

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
        
        # Create the assistant agent with RAG capabilities
        self.agent = autogen.AssistantAgent(
            name="rag_assistant",
            system_message="""You are an expert assistant for sustainability report analysis. You will always answer ONLY based on the provided extracted text context below. Do not mention PDF files, and do not ask for more data. If the context contains relevant information, answer as fully as possible using and quoting the context. If not, say that the context does not contain enough information.""",
            llm_config=config.llm_config
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
            # Get chunks from vector store
            chunks = self.vector_store.get_relevant_chunks(query, k)
            print("================query=================",query)
            print("================relevant 500 chunks=================",chunks)
            
            # If we have user requirement files and we're using vectorization
            if self.vectorized and self.user_req_file_paths:
                # Get the text content from user requirement files to ensure they're included
                user_req_texts = []
                
                # 使用特定的系统参考文档
                specific_ref_doc = r"C:\Users\panha\CascadeProjects\autogen-rag-test\data\documents\reference\effects-analysis.pdf"
                try:
                    texts = DocumentLoader.load_document(specific_ref_doc)
                    user_req_texts.extend(texts)
                    logger.info(f"Loaded specific reference document: {specific_ref_doc}")
                except Exception as e:
                    logger.error(f"Error loading specific reference document: {str(e)}")
                
                # 如果还需要加载用户上传的文档，可以取消下面的注释
                # for file_path in self.user_req_file_paths:
                #     try:
                #         texts = DocumentLoader.load_document(file_path)
                #         user_req_texts.extend(texts)
                #     except Exception as e:
                #         logger.error(f"Error loading user requirement file {file_path}: {str(e)}")
                
                # Limit user requirement texts to avoid token limits
                user_req_texts = user_req_texts[:500]  
                print("================user_req_texts=================",user_req_texts)
                
                # Prepend user requirement texts to ensure they're included in the context
                if user_req_texts:
                    user_req_context = "\n\nUser Requirements:\n" + "\n---\n".join(user_req_texts)
                    context = user_req_context + "\n\nRelevant Context:\n" + "\n---\n".join(chunks)
                    print("================context=================",context)
                else:
                    context = "\n\nRelevant Context:\n" + "\n---\n".join(chunks)
            else:
                context = "\n\nRelevant Context:\n" + "\n---\n".join(chunks)
                
            logger.info(f"Retrieved {len(chunks)} relevant chunks for query")
            return context
        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            return "Error: Unable to retrieve relevant context"
    
    def enhance_prompt(self, query: str, context: str) -> str:
        """为LLM拼接简明prompt，处理用户需求和系统文档的组合"""
        
        # 检查上下文中是否包含用户需求部分
        #context:就是用户的上传的文件加上相关的chunks
        has_user_requirements = "User Requirements:" in context
        
        if has_user_requirements:
            return f"""
Below is the extracted text context from sustainability reports and/or benchmark documents. This is NOT a PDF, but already extracted text for your analysis.

Extracted Context:
{context}

User Question:
{query}

Please analyze the context thoroughly and provide a detailed answer. Follow these guidelines:
1. Carefully examine all parts of the context, even if information appears fragmented or scattered across different sections.
2. Look for both direct and indirect references to the query topic.
3. If you find relevant information, synthesize it into a coherent answer, quoting specific sections.
4. For governance or board-related queries, look for mentions of directors, board members, committees, governance structure, etc.
5. If after thorough examination you determine the context truly lacks information about the query, state so clearly.

Your goal is to extract as much relevant information as possible from the provided context, even if it requires connecting details from different parts of the text."""
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """处理用户查询，根据是否向量化决定检索方式"""
        try:
            # Handle differently based on whether documents were vectorized
            if self.vectorized:
                # Get relevant context using vector search
                context = self.get_relevant_context(query, k=500)  # 增加检索数量到500个chunk
                print("\n========= 检索到的 context 预览 =========\n", context, "\n====================================\n")
            else:
                # If not vectorized, use all document texts as context
                context = "\n\nRelevant Context:\n" + "\n---\n".join(self.texts[:15])
                print("\n========= 未向量化，使用前15个文档作为context =========\n")
            
            # Enhance the prompt with context
            enhanced_prompt = self.enhance_prompt(query, context)
            
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
    
    # 打印GPT的回答
    print("\n========= RAG LLM Answer =========\n")
    if result.get("enhanced_prompt"):
        answer = assistant.agent.generate_reply([
            {"role": "user", "content": result["enhanced_prompt"]}
        ])
        print(answer)
    else:
        print("[Error] Unable to generate answer. Please check your documents and retrieval pipeline.")
