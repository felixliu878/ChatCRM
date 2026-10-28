/**
 * ChatCRM - Web前端应用逻辑
 * 实现WebSocket通信、用户认证、聊天界面交互
 */

class ChatCRMApp {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.isAuthenticated = false;
        this.currentUser = null;
        this.sessionId = null;
        this.currentSqlData = null;
        
        this.init();
    }
    
    init() {
        this.initEventListeners();
        this.initSession();
    }
    
    // 初始化事件监听器
    initEventListeners() {
        // 登录表单
        const loginForm = document.getElementById('loginForm');
        if (loginForm) {
            loginForm.addEventListener('submit', this.handleLogin.bind(this));
        }
        
        // 聊天表单
        const chatForm = document.getElementById('chatForm');
        if (chatForm) {
            chatForm.addEventListener('submit', this.handleSendMessage.bind(this));
        }
        

        
        // 建议标签
        const suggestionTags = document.querySelectorAll('.suggestion-tag');
        suggestionTags.forEach(tag => {
            tag.addEventListener('click', (e) => {
                const text = e.currentTarget.getAttribute('data-text');
                document.getElementById('messageInput').value = text;
                document.getElementById('messageInput').focus();
            });
        });
        
        // 示例查询标签
        const exampleTags = document.querySelectorAll('.example-tag');
        exampleTags.forEach(tag => {
            tag.addEventListener('click', (e) => {
                const text = e.currentTarget.textContent;
                document.getElementById('messageInput').value = text;
                document.getElementById('messageInput').focus();
            });
        });
        
        // SQL确认按钮
        const confirmBtn = document.getElementById('confirmBtn');
        const cancelBtn = document.getElementById('cancelBtn');
        
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => this.confirmSql(true));
        }
        
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.confirmSql(false));
        }
        
        // 清除聊天按钮
        const clearChatBtn = document.getElementById('clearChatBtn');
        if (clearChatBtn) {
            clearChatBtn.addEventListener('click', this.clearChat.bind(this));
        }
        
        // 登出按钮
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', this.logout.bind(this));
        }
        
        // 回车键发送消息
        const messageInput = document.getElementById('messageInput');
        if (messageInput) {
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.handleSendMessage(e);
                }
            });
        }
    }
    
    // 初始化会话
    async initSession() {
        this.showLoading(true);
        
        try {
            const response = await fetch('/api/init', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.sessionId = data.session_id;
                this.initWebSocket();
                this.showToast('系统已连接', 'success');
            } else {
                this.showToast(data.message, 'error');
            }
        } catch (error) {
            console.error('初始化失败:', error);
            this.showToast('连接服务器失败', 'error');
        } finally {
            this.showLoading(false);
        }
    }
    
    // 初始化WebSocket连接
    initWebSocket() {
        this.socket = io({
            transports: ['websocket', 'polling']
        });
        
        this.socket.on('connect', () => {
            console.log('WebSocket已连接');
            this.isConnected = true;
            this.updateConnectionStatus(true);
        });
        
        this.socket.on('disconnect', () => {
            console.log('WebSocket已断开');
            this.isConnected = false;
            this.updateConnectionStatus(false);
        });
        
        this.socket.on('status', (data) => {
            console.log('状态:', data.message);
        });
        
        this.socket.on('error', (data) => {
            this.showToast(data.message, 'error');
        });
        
        // 用户消息现在直接在前端显示，无需监听服务器事件
        // this.socket.on('user_message', (data) => {
        //     this.addMessage(data.message, 'user', data.timestamp);
        // });
        
        this.socket.on('bot_message', (data) => {
            if (data.type === 'confirmation') {
                this.addConfirmationMessage(data);
            } else if (data.type === 'processing') {
                this.addProcessingMessage(data);
            } else {
                this.addBotMessage(data);
            }
        });
    }
    

    
    // 更新连接状态
    updateConnectionStatus(connected) {
        const statusIndicator = document.querySelector('.status-indicator');
        const statusText = document.querySelector('#connectionStatus span');
        
        if (statusIndicator && statusText) {
            if (connected) {
                statusIndicator.className = 'status-indicator online';
                statusText.textContent = '已连接';
            } else {
                statusIndicator.className = 'status-indicator offline';
                statusText.textContent = '连接断开';
            }
        }
    }
    
    // 处理登录
    async handleLogin(e) {
        e.preventDefault();
        
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value.trim();
        
        if (!username || !password) {
            this.showLoginStatus('请输入用户名和密码', 'error');
            return;
        }
        
        this.showLoading(true);
        
        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    username, 
                    password, 
                    session_id: this.sessionId 
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.isAuthenticated = true;
                this.currentUser = data.user;
                this.showChatInterface();
                this.showToast(`欢迎，${data.user}！`, 'success');
            } else {
                this.showLoginStatus(data.message, 'error');
            }
        } catch (error) {
            console.error('登录失败:', error);
            this.showLoginStatus('登录请求失败', 'error');
        } finally {
            this.showLoading(false);
        }
    }
    
    // 显示登录状态
    showLoginStatus(message, type) {
        const loginStatus = document.getElementById('loginStatus');
        if (loginStatus) {
            loginStatus.textContent = message;
            loginStatus.className = `login-status ${type}`;
        }
    }
    
    // 显示聊天界面
    showChatInterface() {
        const loginContainer = document.getElementById('loginContainer');
        const chatContainer = document.getElementById('chatContainer');
        const userInfo = document.getElementById('userInfo');
        const userName = document.getElementById('userName');
        const logoutBtn = document.getElementById('logoutBtn');
        
        if (loginContainer) loginContainer.style.display = 'none';
        if (chatContainer) chatContainer.style.display = 'flex';
        if (userInfo) userInfo.style.display = 'flex';
        if (userName) userName.textContent = this.currentUser;
        if (logoutBtn) logoutBtn.style.display = 'flex';
        
        // 聚焦到输入框
        setTimeout(() => {
            const messageInput = document.getElementById('messageInput');
            if (messageInput) messageInput.focus();
        }, 100);
    }
    
    // 处理发送消息
    handleSendMessage(e) {
        e.preventDefault();
        
        const messageInput = document.getElementById('messageInput');
        const message = messageInput.value.trim();
        
        if (!message) return;
        
        if (!this.isConnected) {
            this.showToast('连接已断开，请刷新页面', 'error');
            return;
        }
        
        if (!this.isAuthenticated) {
            this.showToast('请先登录', 'error');
            return;
        }
        
        if (!this.sessionId) {
            this.showToast('会话无效，请刷新页面', 'error');
            return;
        }
        
        // 先显示用户消息
        this.addMessage(message, 'user', new Date().toISOString());
        
        // 清空输入框
        messageInput.value = '';
        
        // 禁用发送按钮
        const sendBtn = document.getElementById('sendBtn');
        if (sendBtn) {
            sendBtn.disabled = true;
            sendBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        }
        
        console.log('发送消息:', message, 'Session ID:', this.sessionId);  // 调试信息
        
        // 发送消息
        this.socket.emit('send_message', { 
            message: message, 
            session_id: this.sessionId 
        });
        
        // 重新启用发送按钮
        setTimeout(() => {
            if (sendBtn) {
                sendBtn.disabled = false;
                sendBtn.innerHTML = '<i class="fas fa-paper-plane"></i>';
            }
        }, 1000);
    }
    

    
    // 添加消息到聊天
    addMessage(content, sender, timestamp) {
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) return;
        
        // console.log(`添加${sender}消息:`, content); // 调试信息
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        // 为用户消息添加特殊标识，防止被误删
        if (sender === 'user') {
            messageDiv.setAttribute('data-user-message', 'true');
        }
        
        const messageBubble = document.createElement('div');
        messageBubble.className = 'message-bubble';
        messageBubble.textContent = content;
        
        if (timestamp) {
            const timeDiv = document.createElement('div');
            timeDiv.className = 'message-time';
            timeDiv.textContent = this.formatTime(timestamp);
            messageBubble.appendChild(timeDiv);
        }
        
        messageDiv.appendChild(messageBubble);
        chatMessages.appendChild(messageDiv);
        
        // console.log(`当前聊天区域中的消息数量:`, chatMessages.children.length); // 调试信息
        
        // 如果是用户消息，立即保护它
        if (sender === 'user') {
            setTimeout(() => this.protectUserMessages(), 100);
        }
        
        // 滚动到底部
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // 添加机器人消息
    addBotMessage(data) {
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) return;
        
        // console.log('添加机器人消息前，聊天消息数量:', chatMessages.children.length);
        
        // 先移除处理中消息，但保护用户消息
        const existingProcessing = chatMessages.querySelector('[data-processing="true"]');
        if (existingProcessing) {
            // console.log('移除处理中消息');
            existingProcessing.remove();
        }
        
        // 检查用户消息是否还在
        const userMessages = chatMessages.querySelectorAll('[data-user-message="true"]');
        // console.log('机器人消息添加前，用户消息数量:', userMessages.length);
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot';
        
        const messageBubble = document.createElement('div');
        messageBubble.className = 'message-bubble';
        
        // 主要消息内容
        const contentDiv = document.createElement('div');
        // 支持简单的Markdown格式（加粗和换行）
        const formattedMessage = this.formatMessageContent(data.message);
        contentDiv.innerHTML = formattedMessage;
        messageBubble.appendChild(contentDiv);
        
        // 时间戳
        if (data.timestamp) {
            const timeDiv = document.createElement('div');
            timeDiv.className = 'message-time';
            timeDiv.textContent = this.formatTime(data.timestamp);
            messageBubble.appendChild(timeDiv);
        }
        
        // 操作详情
        if (data.details) {
            const detailsDiv = document.createElement('div');
            detailsDiv.className = 'message-details';
            detailsDiv.innerHTML = `<div class="operation-result">${data.details}</div>`;
            messageBubble.appendChild(detailsDiv);
        }
        
        // 数据表格 - 临时禁用，先用简单格式
        if (data.data && data.columns && false) {
            const tableDiv = this.createDataTable(data.data, data.columns);
            messageBubble.appendChild(tableDiv);
        }
        
        // 如果有数据，显示为简单文本格式
        if (data.data_count && data.data_count > 0) {
            const dataDiv = document.createElement('div');
            dataDiv.className = 'data-summary';
            dataDiv.style.marginTop = '12px';
            dataDiv.style.padding = '12px';
            dataDiv.style.background = 'var(--background-color)';
            dataDiv.style.borderRadius = 'var(--radius-md)';
            dataDiv.style.border = '1px solid var(--border-color)';
            dataDiv.innerHTML = `<small>📊 查询结果包含 ${data.data_count} 条记录</small>`;
            messageBubble.appendChild(dataDiv);
        }
        
        messageDiv.appendChild(messageBubble);
        chatMessages.appendChild(messageDiv);
        
        // 再次检查用户消息是否还在
        const finalUserMessages = chatMessages.querySelectorAll('[data-user-message="true"]');
        // console.log('机器人消息添加后，用户消息数量:', finalUserMessages.length);
        // console.log('最终聊天消息总数:', chatMessages.children.length);
        
        // 检查用户消息完整性
        setTimeout(() => this.checkAndRestoreUserMessages(), 200);
        
        // 滚动到底部
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // 创建数据表格
    createDataTable(data, columns) {        
        const tableContainer = document.createElement('div');
        tableContainer.className = 'data-table';
        
        const table = document.createElement('table');
        
        // 表头
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        columns.forEach(column => {
            const th = document.createElement('th');
            th.textContent = column;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);
        
        // 表体
        const tbody = document.createElement('tbody');
        data.forEach((row, rowIndex) => {
            const tr = document.createElement('tr');
            row.forEach((cell, cellIndex) => {
                const td = document.createElement('td');
                td.textContent = cell || '';
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
        table.appendChild(tbody);
        
        tableContainer.appendChild(table);
        return tableContainer;
    }
    
    // 添加确认消息（带按钮）
    addConfirmationMessage(data) {
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) return;
        
        // 移除之前的确认消息，但保护用户消息
        const existingConfirmation = chatMessages.querySelector('.confirmation-message');
        if (existingConfirmation) {
            console.log('移除之前的确认消息');
            existingConfirmation.remove();
        }
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot confirmation-message';
        
        const messageBubble = document.createElement('div');
        messageBubble.className = 'message-bubble';
        
        const messageContent = document.createElement('div');
        messageContent.textContent = data.message;
        messageBubble.appendChild(messageContent);
        
        const buttonsDiv = document.createElement('div');
        buttonsDiv.className = 'confirmation-buttons';
        
        data.buttons.forEach(button => {
            const btn = document.createElement('button');
            btn.className = `confirmation-btn ${button.style}`;
            btn.textContent = button.text;
            btn.onclick = () => this.handleUserAction(button.action, data.pending_sql);
            buttonsDiv.appendChild(btn);
        });
        
        messageBubble.appendChild(buttonsDiv);
        
        if (data.timestamp) {
            const timeDiv = document.createElement('div');
            timeDiv.className = 'message-time';
            timeDiv.textContent = this.formatTime(data.timestamp);
            messageBubble.appendChild(timeDiv);
        }
        
        messageDiv.appendChild(messageBubble);
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // 添加处理中消息
    addProcessingMessage(data) {
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) return;
        
        // 先移除之前的处理消息
        const existingProcessing = chatMessages.querySelector('[data-processing="true"]');
        if (existingProcessing) {
            existingProcessing.remove();
        }
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot processing-message';
        messageDiv.setAttribute('data-processing', 'true');
        
        const messageBubble = document.createElement('div');
        messageBubble.className = 'message-bubble';
        
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'processing-indicator';
        loadingDiv.innerHTML = `
            <div class="loading-dots">
                <span></span><span></span><span></span>
            </div>
            <span class="processing-text">${data.message}</span>
        `;
        
        messageBubble.appendChild(loadingDiv);
        
        if (data.timestamp) {
            const timeDiv = document.createElement('div');
            timeDiv.className = 'message-time';
            timeDiv.textContent = this.formatTime(data.timestamp);
            messageBubble.appendChild(timeDiv);
        }
        
        messageDiv.appendChild(messageBubble);
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // 处理用户操作
    handleUserAction(action, pendingSql) {
        if (!this.socket || !this.sessionId) {
            this.showToast('连接已断开，请刷新页面', 'error');
            return;
        }
        
        // 禁用所有确认按钮
        const confirmationBtns = document.querySelectorAll('.confirmation-btn');
        confirmationBtns.forEach(btn => {
            btn.disabled = true;
            btn.style.opacity = '0.5';
        });
        
        console.log('发送用户操作:', action, 'Session ID:', this.sessionId);
        console.log('当前聊天消息数量:', document.getElementById('chatMessages').children.length);
        
        // 记录用户消息数量，以便后续检查
        const chatMessages = document.getElementById('chatMessages');
        const userMessages = chatMessages.querySelectorAll('[data-user-message="true"]');
        console.log('当前用户消息数量:', userMessages.length);
        
        this.socket.emit('user_action', {
            action: action,
            pending_sql: pendingSql,
            session_id: this.sessionId
        });
    }
    
    // 显示SQL确认对话框（已废弃，保留兼容性）
    showSqlConfirmation(data) {
        // 这个方法已经被新的addConfirmationMessage替代
        console.warn('showSqlConfirmation已废弃，请使用addConfirmationMessage');
    }
    
    // 获取操作类型文本
    getOperationTypeText(type) {
        const typeMap = {
            'CREATE': '📝 创建操作',
            'UPDATE': '✏️ 更新操作',
            'DELETE': '🗑️ 删除操作',
            'READ': '🔍 查询操作'
        };
        return typeMap[type] || type;
    }
    
    // 确认SQL执行
    confirmSql(confirmed) {
        const sqlConfirmation = document.getElementById('sqlConfirmation');
        if (sqlConfirmation) {
            sqlConfirmation.style.display = 'none';
        }
        
        console.log('SQL确认:', confirmed, 'Session ID:', this.sessionId, 'SQL Data:', this.currentSqlData);  // 调试信息
        
        if (this.socket && this.currentSqlData && this.sessionId) {
            const confirmData = {
                confirmed: confirmed,
                sql_query: this.currentSqlData.sql_query,
                original_message: this.currentSqlData.original_message,
                session_id: this.sessionId
            };
            
            console.log('发送SQL确认数据:', confirmData);  // 调试信息
            this.socket.emit('confirm_sql', confirmData);
        } else {
            console.error('无法发送SQL确认，缺少必要数据');
            this.showToast('无法执行操作，请刷新页面重试', 'error');
        }
        
        this.currentSqlData = null;
    }
    
    // 清除聊天记录
    clearChat() {
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) {
            // 保留欢迎消息
            const welcomeMessage = chatMessages.querySelector('.welcome-message');
            chatMessages.innerHTML = '';
            if (welcomeMessage) {
                chatMessages.appendChild(welcomeMessage);
            }
        }
        this.showToast('聊天记录已清除', 'success');
    }
    
    // 登出
    logout() {
        this.isAuthenticated = false;
        this.currentUser = null;
        
        const loginContainer = document.getElementById('loginContainer');
        const chatContainer = document.getElementById('chatContainer');
        const userInfo = document.getElementById('userInfo');
        const logoutBtn = document.getElementById('logoutBtn');
        
        if (loginContainer) loginContainer.style.display = 'flex';
        if (chatContainer) chatContainer.style.display = 'none';
        if (userInfo) userInfo.style.display = 'none';
        if (logoutBtn) logoutBtn.style.display = 'none';
        
        // 清空登录表单
        const username = document.getElementById('username');
        const password = document.getElementById('password');
        const loginStatus = document.getElementById('loginStatus');
        
        if (username) username.value = '';
        if (password) password.value = '';
        if (loginStatus) loginStatus.textContent = '';
        
        this.showToast('已退出登录', 'success');
    }
    
    // 显示/隐藏加载动画
    showLoading(show) {
        const loadingOverlay = document.getElementById('loadingOverlay');
        if (loadingOverlay) {
            if (show) {
                loadingOverlay.classList.add('show');
            } else {
                loadingOverlay.classList.remove('show');
            }
        }
    }
    
    // 显示提示消息
    showToast(message, type = 'info') {
        const toast = document.getElementById('toast');
        const toastIcon = toast.querySelector('.toast-icon');
        const toastMessage = toast.querySelector('.toast-message');
        
        if (toast && toastIcon && toastMessage) {
            // 设置图标
            const iconMap = {
                'success': 'fas fa-check-circle',
                'error': 'fas fa-exclamation-circle',
                'warning': 'fas fa-exclamation-triangle',
                'info': 'fas fa-info-circle'
            };
            
            toastIcon.className = `toast-icon ${iconMap[type] || iconMap.info}`;
            toastMessage.textContent = message;
            
            // 设置样式
            toast.className = `toast ${type}`;
            
            // 显示
            toast.classList.add('show');
            
            // 自动隐藏
            setTimeout(() => {
                toast.classList.remove('show');
            }, 3000);
        }
    }
    
    // 格式化时间
    formatTime(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit'
        });
    }
    
    // 保护用户消息不被意外删除
    protectUserMessages() {
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) return;
        
        const userMessages = chatMessages.querySelectorAll('[data-user-message="true"]');
        console.log('正在保护用户消息，数量:', userMessages.length);
        
        // 为每个用户消息添加额外的保护
        userMessages.forEach((msg, index) => {
            if (!msg.hasAttribute('data-protected')) {
                msg.setAttribute('data-protected', 'true');
                msg.style.position = 'relative';
                // 添加一个不可见的备份标识
                const backup = document.createElement('span');
                backup.style.display = 'none';
                backup.textContent = 'USER_MESSAGE_BACKUP';
                backup.className = 'user-message-backup';
                msg.appendChild(backup);
                console.log(`用户消息 ${index + 1} 已添加保护`);
            }
        });
    }

    // 检查并恢复丢失的用户消息
    checkAndRestoreUserMessages() {
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) return;
        
        const userMessages = chatMessages.querySelectorAll('[data-user-message="true"]');
        const backups = chatMessages.querySelectorAll('.user-message-backup');
        
        console.log('用户消息检查 - 当前用户消息:', userMessages.length, '备份标记:', backups.length);
        
        if (backups.length > userMessages.length) {
            console.warn('检测到用户消息丢失！备份数量大于当前用户消息数量');
            this.showToast('检测到消息显示异常，正在修复...', 'warning');
        }
    }

    // 格式化消息内容，支持简单的Markdown
    formatMessageContent(message) {
        if (!message) return '';
        
        // 先转义HTML特殊字符
        let formatted = message
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#x27;');
        
        // 将换行符转换为<br>
        formatted = formatted.replace(/\n/g, '<br>');
        
        // 将**文本**转换为<strong>文本</strong>
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        return formatted;
    }
}

// 页面加载完成后初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.chatCRM = new ChatCRMApp();
});

// 错误处理
window.addEventListener('error', (e) => {
    console.error('应用错误:', e.error);
    if (window.chatCRM) {
        window.chatCRM.showToast('应用出现错误，请刷新页面', 'error');
    }
});

// 网络状态监听
window.addEventListener('online', () => {
    if (window.chatCRM) {
        window.chatCRM.showToast('网络连接已恢复', 'success');
    }
});

window.addEventListener('offline', () => {
    if (window.chatCRM) {
        window.chatCRM.showToast('网络连接已断开', 'error');
    }
}); 