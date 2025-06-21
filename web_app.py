import os
import sys
import uuid
import logging
import json
from pathlib import Path
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
from src.agents.router_agent import RouterAgent
from src.config import config

# 添加项目根目录到系统路径
project_root = Path(__file__).parent.absolute()
sys.path.append(str(project_root))

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'

# 初始化路由代理，用于分发查询到适当的代理
router_agent = None

@app.route('/')
def index():
    """渲染主页"""
    return render_template('index.html')

@app.route('/score')
def score_page():
    """Render the scoring page"""
    return render_template('score.html')

@app.route('/upload_documents', methods=['POST'])
def upload_documents():
    """处理用户上传的文档作为需求和问题规格"""
    global router_agent
    
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
        
        # 初始化路由代理
        router_agent = RouterAgent()
        
        # 加载系统中已有的文档
        reference_dir = os.path.join(project_root, 'data', 'documents', 'reference')
        # report_dir = os.path.join(project_root, 'data', 'documents', 'report')
        
        # 获取系统文档路径
        system_paths = []
        for directory in [reference_dir]:
            if os.path.exists(directory):
                for root, _, files in os.walk(directory):
                    for file in files:
                        if file.lower().endswith(('.pdf', '.txt', '.json')):
                            system_paths.append(os.path.join(root, file))
        
        # 结合用户上传的文档和系统参考文档
        all_paths = system_paths + user_req_paths
        
        # Log what documents we're processing
        logger.info(f"Processing {len(user_req_paths)} user uploaded documents and {len(system_paths)} reference documents")
        for path in user_req_paths:
            logger.info(f"User document: {os.path.basename(path)}")
        for path in system_paths:
            logger.info(f"Reference document: {os.path.basename(path)}")
        
        if not all_paths:
            return jsonify({
                'success': False,
                'message': 'No documents found.'
            })
        
        # 决定是否需要向量化文档 (超过3个文件或总大小>1MB)
        should_vectorize = len(all_paths) > 3 or sum(os.path.getsize(path) for path in all_paths if os.path.exists(path)) > 1000000
        
        # 设置用户需求文档标记
        router_agent.set_user_requirement_files(user_req_paths)
        
        # 加载文档，根据需要决定是否向量化
        # 传递用户文件和所有文件分开，这样scoring_agent只会使用用户上传的文件
        router_agent.load_documents(all_paths, vectorize=should_vectorize, user_files=user_req_paths)
        
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
        logger.error(f"Error processing documents: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error processing documents: {str(e)}'
        })

@app.route('/ask', methods=['POST'])
def ask():
    """处理用户问题并根据模式参数路由到适当的代理"""
    global router_agent
    
    # 检查路由代理是否已初始化
    if router_agent is None:
        return jsonify({
            'success': False,
            'message': 'Router agent not initialized. Please load documents first.'
        })
    
    # 获取用户问题和模式
    data = request.get_json()
    query = data.get('query', '')
    mode = data.get('mode', 'analysis')  # Default to analysis mode
    
    if not query:
        return jsonify({
            'success': False,
            'message': 'Query cannot be empty.'
        })
    
    try:
        # 根据模式决定如何处理查询
        logger.info(f"Processing query in {mode} mode: {query}")
        
        # 路由查询到适当的代理，传递模式参数
        result = router_agent.route_query(query, mode=mode)
        
        # 根据使用的代理类型返回响应
        if result.get('agent') == 'scoring_agent':
            return jsonify({
                'success': True,
                'query': query,
                'agent_type': 'scoring_agent',
                'answer': result.get('response', '')
            })
        else:  # rag_assistant
            return jsonify({
                'success': True,
                'query': query,
                'agent_type': 'rag_assistant',
                'context': result.get('context', ''),
                'answer': result.get('response', '')
            })
    
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
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
    
    # 创建data/scoring目录（如果不存在）
    scoring_dir = os.path.join(project_root, 'data', 'scoring')
    os.makedirs(scoring_dir, exist_ok=True)
    
    print("Starting RAG Web Application...")
    app.run(debug=True, port=5000)
