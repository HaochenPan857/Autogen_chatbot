import logging
from pathlib import Path
from src.agents.rag_assistant import RAGAssistant
from src.agents.user_proxy import EnhancedUserProxy
from src.utils.document_loader import DocumentLoader
import autogen

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_agents():
    """Initialize and setup the agents"""
    try:
        # Initialize agents
        rag_assistant = RAGAssistant()
        user_proxy = EnhancedUserProxy()
        
        # Create chat group
        groupchat = autogen.GroupChat(
            agents=[user_proxy, rag_assistant.agent],
            messages=[],
            max_round=12,
            speaker_selection_method="round_robin"
        )
        
        manager = autogen.GroupChatManager(
            groupchat=groupchat,
            llm_config=rag_assistant.agent.llm_config
        )
        
        return user_proxy, rag_assistant, manager
    except Exception as e:
        logger.error(f"Error setting up agents: {str(e)}")
        raise

def load_documents(rag_assistant, doc_dir: str = "data/documents"):
    """Load documents into the RAG system"""
    try:
        doc_path = Path(doc_dir)
        if not doc_path.exists():
            logger.warning(f"Document directory not found: {doc_dir}")
            return
        
        # Get all supported document files
        supported_extensions = tuple(DocumentLoader.SUPPORTED_EXTENSIONS.keys())
        doc_files = [
            str(f) for f in doc_path.glob("**/*") 
            if f.is_file() and f.suffix.lower() in supported_extensions
        ]
        
        if not doc_files:
            logger.warning(f"No supported documents found in {doc_dir}")
            return
        
        logger.info(f"Loading {len(doc_files)} documents...")
        rag_assistant.load_documents(doc_files)
        
    except Exception as e:
        logger.error(f"Error loading documents: {str(e)}")
        raise

def main():
    """Main entry point"""
    try:
        # 单 agent RAG 问答流程
        rag_assistant = RAGAssistant()
        
        # 检查文档目录和内容
        doc_dir = "data/documents"
        doc_path = Path(doc_dir)
        if not doc_path.exists():
            print(f"[错误] 文档目录不存在: {doc_dir}")
            return
        # 支持所有子目录下的pdf和txt文件
        supported_exts = (".pdf", ".txt")
        doc_files = [str(f) for f in doc_path.glob("**/*") if f.is_file() and f.suffix.lower() in supported_exts]
        if not doc_files:
            print(f"[错误] 文档目录及其子目录中未找到任何pdf或txt文件: {doc_dir}")
            return
        print(f"[信息] 检测到 {len(doc_files)} 个pdf/txt文档，开始加载...")
        load_documents(rag_assistant)
        print("[信息] 文档加载完毕，准备进行RAG分析。")
        
        # 原始query已备份，如需回滚可恢复
        query = (
            "Please provide a comprehensive, in-depth summary and analysis of all key points regarding climate risk management and benchmark requirements "
            "based solely on the provided documents. Your response should be approximately 2000 words, written in well-structured paragraphs, not in bullet points or highlights. "
            "The summary should be free-flowing, analytical, and as detailed as possible, integrating and synthesizing information from the context. Do not mention specific file names."
        )
        print("[信息] 开始RAG检索与分析...")
        result = rag_assistant.process_query(query)
        print("\n=========检索到的 context 预览=========")
        print(result["context"])
        print("\n=========RAG LLM Answer=========")
        # 直接调用 LLM 并输出最终答案
        answer = rag_assistant.agent.generate_reply([
            {"role": "user", "content": result["enhanced_prompt"]}
        ])
        print(answer)
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise

if __name__ == "__main__":
    main()
