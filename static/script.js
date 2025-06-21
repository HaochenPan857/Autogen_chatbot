document.addEventListener('DOMContentLoaded', function() {
    // DOM元素
    const fileUploadInput = document.getElementById('file-upload');
    const fileSelectedSpan = document.getElementById('file-selected');
    const statusDiv = document.getElementById('status');
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const contextContent = document.getElementById('context-content');
    const toggleContextBtn = document.getElementById('toggle-context');
    const loadingOverlay = document.getElementById('loading-overlay');
    const loadingText = document.getElementById('loading-text');
    const analysisModeBtn = document.getElementById('analysis-mode-btn');
    const scoringModeBtn = document.getElementById('scoring-mode-btn');
    const exploreModeBtn = document.getElementById('explore-mode-btn');
    const currentModeSpan = document.getElementById('current-mode');
    const analysisDescription = document.getElementById('analysis-description');
    const scoringDescription = document.getElementById('scoring-description');
    const exploreDescription = document.getElementById('explore-description');

    // 标记文档是否已加载
    let documentsLoaded = false;
    
    // 当前模式: 'analysis' 或 'scoring'
    let currentMode = 'analysis';
    
    // 配置marked库以正确渲染markdown
    marked.setOptions({
        renderer: new marked.Renderer(),
        highlight: function(code, language) {
            const validLanguage = hljs.getLanguage(language) ? language : 'plaintext';
            return hljs.highlight(validLanguage, code).value;
        },
        pedantic: false,
        gfm: true,
        breaks: true,
        sanitize: false,
        smartypants: false,
        xhtml: false
    });

    // 文件选择更新
    fileUploadInput.addEventListener('change', function() {
        if (fileUploadInput.files.length > 0) {
            fileSelectedSpan.textContent = `${fileUploadInput.files.length} file(s) selected`;
            uploadFiles();
        } else {
            fileSelectedSpan.textContent = 'No files selected';
        }
    });

    // 上传文档
    function uploadFiles() {
        if (fileUploadInput.files.length === 0) {
            addMessage('system', 'Please select files to upload first.');
            return;
        }

        showLoading('Uploading documents...');
        
        const formData = new FormData();
        for (let i = 0; i < fileUploadInput.files.length; i++) {
            formData.append('files', fileUploadInput.files[i]);
        }
        
        fetch('/upload_documents', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            hideLoading();
            
            if (data.success) {
                documentsLoaded = true;
                statusDiv.textContent = data.message;
                statusDiv.className = 'status success';
                
                // 启用输入
                userInput.disabled = false;
                sendButton.disabled = false;
                
                // 添加系统消息
                let systemMsg = `User requirements uploaded and processed successfully! ${data.files.length} files were processed: ${data.files.join(', ')}.`;
                
                // 如果有系统文档被加载
                if (data.system_files && data.system_files.length > 0) {
                    systemMsg += ` Combined with ${data.system_files.length} system reference documents.`;
                }
                
                systemMsg += ' You can now ask questions about your requirements in relation to the reference documents.';
                
                addMessage('system', systemMsg);
            } else {
                statusDiv.textContent = data.message;
                statusDiv.className = 'status error';
                addMessage('system', `Error processing requirements documents: ${data.message}`);
            }
        })
        .catch(error => {
            hideLoading();
            statusDiv.textContent = 'Error connecting to server';
            statusDiv.className = 'status error';
            addMessage('system', 'Error connecting to server. Please try again later.');
            console.error('Error:', error);
        });
    }

    // Mode switching handlers
    analysisModeBtn.addEventListener('click', function() {
        if (currentMode !== 'analysis') {
            // Update mode
            currentMode = 'analysis';
            currentModeSpan.textContent = 'Analysis';
            
            // Update button styles
            analysisModeBtn.classList.add('active', 'btn-primary');
            analysisModeBtn.classList.remove('btn-secondary');
            scoringModeBtn.classList.remove('active', 'btn-primary');
            scoringModeBtn.classList.add('btn-secondary');
            exploreModeBtn.classList.remove('active', 'btn-primary');
            exploreModeBtn.classList.add('btn-secondary');
            
            // Update descriptions
            analysisDescription.style.display = 'block';
            scoringDescription.style.display = 'none';
            exploreDescription.style.display = 'none';
            
            // Update placeholder
            userInput.placeholder = 'Ask a question about your documents...';
        }
    });
    
    scoringModeBtn.addEventListener('click', function() {
        if (currentMode !== 'scoring') {
            // Update mode
            currentMode = 'scoring';
            currentModeSpan.textContent = 'Scoring';
            
            // Update button styles
            scoringModeBtn.classList.add('active', 'btn-primary');
            scoringModeBtn.classList.remove('btn-secondary');
            analysisModeBtn.classList.remove('active', 'btn-primary');
            analysisModeBtn.classList.add('btn-secondary');
            exploreModeBtn.classList.remove('active', 'btn-primary');
            exploreModeBtn.classList.add('btn-secondary');
            
            // Update descriptions
            scoringDescription.style.display = 'block';
            analysisDescription.style.display = 'none';
            exploreDescription.style.display = 'none';
            
            // Update placeholder
            userInput.placeholder = 'Ask to score or rate your sustainability report...';
        }
    });
    
    exploreModeBtn.addEventListener('click', function() {
        if (currentMode !== 'explore') {
            // Update mode
            currentMode = 'explore';
            currentModeSpan.textContent = 'Explore';
            
            // Update button styles
            exploreModeBtn.classList.add('active', 'btn-primary');
            exploreModeBtn.classList.remove('btn-secondary');
            analysisModeBtn.classList.remove('active', 'btn-primary');
            analysisModeBtn.classList.add('btn-secondary');
            scoringModeBtn.classList.remove('active', 'btn-primary');
            scoringModeBtn.classList.add('btn-secondary');
            
            // Update descriptions
            exploreDescription.style.display = 'block';
            analysisDescription.style.display = 'none';
            scoringDescription.style.display = 'none';
            
            // Update placeholder
            userInput.placeholder = 'Ask a question about your uploaded documents only...';
        }
    });

    // 发送问题
    function sendQuestion() {
        const query = userInput.value.trim();
        
        if (!query) return;
        
        // Prepare the actual query based on the current mode
        let processedQuery = query;
        if (currentMode === 'scoring' && !query.toLowerCase().includes('score') && 
            !query.toLowerCase().includes('rate') && !query.toLowerCase().includes('evaluate')) {
            // If in scoring mode but query doesn't contain scoring keywords, add them
            processedQuery = `Score and rate this sustainability report: ${query}`;
        }
        
        // 添加用户消息
        addMessage('user', query);
        
        // 清空输入框
        userInput.value = '';
        
        // 显示加载中
        showLoading('Processing your question...');
        
        // 发送请求
        fetch('/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query: processedQuery, mode: currentMode })
        })
        .then(response => response.json())
        .then(data => {
            hideLoading();
            
            if (data.success) {
                // 添加助手回答
                addMessage('assistant', data.answer);
                
                // 更新上下文面板
                if (data.context) {
                    updateContextPanel(data.context);
                } else {
                    updateContextPanel('');
                }
            } else {
                addMessage('system', `Error: ${data.message}`);
            }
        })
        .catch(error => {
            hideLoading();
            addMessage('system', 'Error connecting to server. Please try again later.');
            console.error('Error:', error);
        });
    }

    // 发送按钮点击事件
    sendButton.addEventListener('click', sendQuestion);

    // 输入框回车事件
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!sendButton.disabled) {
                sendQuestion();
            }
        }
    });

    // 切换上下文面板
    toggleContextBtn.addEventListener('click', function() {
        const icon = toggleContextBtn.querySelector('i');
        if (contextContent.style.display === 'none') {
            contextContent.style.display = 'block';
            icon.className = 'fas fa-chevron-up';
        } else {
            contextContent.style.display = 'none';
            icon.className = 'fas fa-chevron-down';
        }
    });

    // 添加消息到聊天窗口
    function addMessage(type, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // 使用marked渲染markdown
        contentDiv.innerHTML = marked.parse(content);
        
        messageDiv.appendChild(contentDiv);
        chatMessages.appendChild(messageDiv);
        
        // 滚动到底部
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // 更新上下文面板
    function updateContextPanel(context) {
        if (context) {
            contextContent.innerHTML = `<pre>${context}</pre>`;
        } else {
            contextContent.innerHTML = '<p class="placeholder">No context available for this query.</p>';
        }
    }

    // 显示加载中
    function showLoading(text) {
        loadingText.textContent = text || 'Processing...';
        loadingOverlay.style.display = 'flex';
    }

    // 隐藏加载中
    function hideLoading() {
        loadingOverlay.style.display = 'none';
    }

    // 初始化
    addMessage('system', 'Welcome to RAG Assistant! Click "Upload Documents" to start, then ask questions about your documents.');
});
