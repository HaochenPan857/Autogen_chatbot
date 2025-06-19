import os
import sys
import uuid
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, jsonify

# 添加项目根目录到系统路径
project_root = Path(__file__).parent.absolute()
sys.path.append(str(project_root))

# 导入RAG助手
from src.agents.rag_assistant import RAGAssistant

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'

# 初始化RAG助手
rag_assistant = None

@app.route('/')
def index():
    """渲染主页"""
    return render_template('index.html')

@app.route('/upload_documents', methods=['POST'])
def upload_documents():
    """处理用户上传的文档作为需求和问题规格"""
    global rag_assistant
    
    try:
        # 检查是否有文件上传
        if 'files' not in request.files:
            return jsonify({
                'success': False,
                'message': 'No files uploaded.'
            })
        
        files = request.files.getlist('files')
        if not files or files[0].filename == '':
            return jsonify({
                'success': False,
                'message': 'No files selected.'
            })
        
        # 创建临时目录来存储用户需求文档
        user_req_dir = os.path.join(project_root, 'data', 'user_requirements', str(uuid.uuid4()))
        os.makedirs(user_req_dir, exist_ok=True)
        
        # 保存上传的文件
        user_req_paths = []
        uploaded_filenames = []
        
        for file in files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                if filename.lower().endswith(('.pdf', '.txt')):
                    file_path = os.path.join(user_req_dir, filename)
                    file.save(file_path)
                    user_req_paths.append(file_path)
                    uploaded_filenames.append(filename)
        
        if not user_req_paths:
            return jsonify({
                'success': False,
                'message': 'No valid PDF or TXT files were uploaded.'
            })
        
        # 初始化RAG助手
        rag_assistant = RAGAssistant()
        
        # 加载系统中已有的文档
        reference_dir = os.path.join(project_root, 'data', 'documents', 'reference')
        # report_dir = os.path.join(project_root, 'data', 'documents', 'report')
        
        # 获取系统文档路径
        system_paths = []
        for directory in [reference_dir]:
            if os.path.exists(directory):
                for root, _, files in os.walk(directory):
                    for file in files:
                        if file.lower().endswith(('.pdf', '.txt')):
                            system_paths.append(os.path.join(root, file))
        
        # 将用户需求文档和系统文档结合起来
        # 添加特定的系统参考文档
        specific_ref_doc = os.path.join(project_root, 'data', 'documents', 'reference', 'effects-analysis.pdf')
        system_paths = [specific_ref_doc] if os.path.exists(specific_ref_doc) else []
        
        # 结合用户上传的文档和系统参考文档
        all_paths = system_paths + user_req_paths
        
        if not all_paths:
            return jsonify({
                'success': False,
                'message': 'No documents found.'
            })
        
        # 决定是否需要向量化文档 (超过3个文件或总大小>1MB)
        should_vectorize = len(all_paths) > 3 or sum(os.path.getsize(path) for path in all_paths if os.path.exists(path)) > 1000000
        
        # 设置用户需求文档标记，以便在检索时给予更高权重
        rag_assistant.set_user_requirement_files(user_req_paths)
        
        # 加载文档，根据需要决定是否向量化
        rag_assistant.load_documents(all_paths, vectorize=should_vectorize)
        
        vectorization_msg = "Documents have been vectorized for efficient retrieval." if should_vectorize else \
                           "Documents are being processed directly by the language model without vectorization."
        
        return jsonify({
            'success': True,
            'message': f'Successfully processed {len(uploaded_filenames)} user requirement documents. {vectorization_msg}',
            'files': uploaded_filenames,
            'system_files': [os.path.basename(path) for path in system_paths] if 'system_paths' in locals() else [],
            'vectorized': should_vectorize
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error processing documents: {str(e)}'
        })

@app.route('/ask', methods=['POST'])
def ask():
    """处理用户问题"""
    global rag_assistant
    
    # 检查RAG助手是否已初始化
    if rag_assistant is None:
        return jsonify({
            'success': False,
            'message': 'RAG assistant not initialized. Please load documents first.'
        })
    
    # 获取用户问题
    data = request.get_json()
    query = data.get('query', '')
    
    if not query:
        return jsonify({
            'success': False,
            'message': 'Query cannot be empty.'
        })
    
    try:
        # 处理查询
        result = rag_assistant.process_query(query)
        
        # 获取LLM回答
        if result.get('enhanced_prompt'):
            # Use the response that was already generated in process_query
            answer = result.get('response')
            
            return jsonify({
                'success': True,
                'query': query,
                'context': result.get('context', ''),
                'answer': answer
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to generate enhanced prompt.'
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error processing query: {str(e)}'
        })

if __name__ == '__main__':
    # 创建templates目录（如果不存在）
    templates_dir = os.path.join(project_root, 'templates')
    os.makedirs(templates_dir, exist_ok=True)
    
    # 创建static目录（如果不存在）
    static_dir = os.path.join(project_root, 'static')
    os.makedirs(static_dir, exist_ok=True)
    
    print("Starting RAG Web Application...")
    app.run(debug=True, port=5000)
