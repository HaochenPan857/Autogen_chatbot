import logging
from pathlib import Path
from src.agents.rag_assistant import RAGAssistant
from src.utils.document_loader import DocumentLoader

def load_documents(rag_assistant, doc_dir: str = "data/documents"):
    """Load documents into the RAG system"""
    try:
        doc_path = Path(doc_dir)
        if not doc_path.exists():
            print(f"[Error] Document directory does not exist: {doc_dir}")
            return False
        supported_extensions = tuple(DocumentLoader.SUPPORTED_EXTENSIONS.keys())
        doc_files = [
            str(f) for f in doc_path.glob("**/*")
            if f.is_file() and f.suffix.lower() in supported_extensions
        ]
        if not doc_files:
            print(f"[Error] No supported documents found in directory: {doc_dir}")
            return False
        print(f"[Info] Detected {len(doc_files)} document(s), loading...")
        rag_assistant.load_documents(doc_files)
        print("[Info] Document loading completed. RAG vector store initialized.")
        return True
    except Exception as e:
        print(f"[Error] Exception occurred while loading documents: {str(e)}")
        return False

def main():
    try:
        rag_assistant = RAGAssistant()
        if not load_documents(rag_assistant):
            print("[Terminated] Document loading failed. Cannot enter interactive Q&A mode.")
            return
        print("\nLocal RAG Interactive Q&A Platform is running. Please enter your question (type 'exit' to quit):")
        while True:
            user_query = input("\nPlease enter your question (type 'exit' to quit):\n> ").strip()
            if user_query.lower() in ["exit", "quit", "q"]:
                print("Exited RAG Q&A platform.")
                break
            if not user_query:
                print("Question cannot be empty. Please try again."); continue
            result = rag_assistant.process_query(user_query)
            print("\n========= Retrieved context preview =========")
            print(result["context"])
            print("\n========= RAG LLM Answer =========")
            if result.get("enhanced_prompt"):
                answer = rag_assistant.agent.generate_reply([
                    {"role": "user", "content": result["enhanced_prompt"]}
                ])
                print(answer)
            else:
                print("[Error] Unable to generate answer. Please check your documents and retrieval pipeline.")
    except Exception as e:
        print(f"[Error] Exception in main: {str(e)}")

if __name__ == "__main__":
    main()
