/**
 * 书架调试功能
 * 用于调试书架相关的功能
 */

// 调试模式开关
const DEBUG_MODE = true;

/**
 * 调试日志函数
 */
function debugLog(message, data = null) {
    if (DEBUG_MODE) {
        console.log(`[书架调试] ${message}`, data || '');
    }
}

/**
 * 调试书架状态
 */
function debugBookshelfStatus() {
    debugLog('开始调试书架状态');
    
    // 检查页面数据
    const bookId = document.body.dataset.bookId;
    const bookTitle = document.body.dataset.bookTitle;
    const isInBookshelf = document.body.dataset.isInBookshelf === 'true';
    const isCollected = document.body.dataset.isCollected === 'true';
    const username = document.body.dataset.username;
    
    debugLog('页面数据', {
        bookId,
        bookTitle,
        isInBookshelf,
        isCollected,
        username
    });
    
    // 检查按钮状态
    const bookshelfBtn = document.querySelector('.bookshelf-btn');
    const collectBtn = document.querySelector('.collect-btn');
    
    debugLog('按钮状态', {
        bookshelfBtn: bookshelfBtn ? bookshelfBtn.className : '未找到',
        collectBtn: collectBtn ? collectBtn.className : '未找到'
    });
    
    // 检查用户会话
    debugLog('用户会话', {
        username: username || '未登录',
        sessionData: {
            username: document.body.dataset.username || 'None',
            name: document.body.dataset.name || 'None',
            is_admin: document.body.dataset.isAdmin || 'None'
        }
    });
}

/**
 * 调试书架操作
 */
function debugBookshelfAction(action, bookTitle) {
    debugLog(`执行书架操作: ${action}`, { bookTitle });
    
    // 记录操作时间
    const timestamp = new Date().toISOString();
    debugLog('操作时间', timestamp);
    
    // 检查操作前的状态
    const beforeState = {
        isInBookshelf: document.body.dataset.isInBookshelf === 'true',
        isCollected: document.body.dataset.isCollected === 'true'
    };
    
    debugLog('操作前状态', beforeState);
}

/**
 * 调试API响应
 */
function debugApiResponse(url, response, error = null) {
    if (error) {
        debugLog(`API错误: ${url}`, error);
    } else {
        debugLog(`API成功: ${url}`, response);
    }
}

/**
 * 调试书架数据加载
 */
function debugBookshelfDataLoad(data) {
    debugLog('书架数据加载', {
        bookCount: data.books ? data.books.length : 0,
        hasBooks: !!data.books,
        dataKeys: Object.keys(data)
    });
}

/**
 * 初始化调试功能
 */
function initBookshelfDebug() {
    if (DEBUG_MODE) {
        debugLog('书架调试功能已初始化');
        
        // 监听页面加载完成
        document.addEventListener('DOMContentLoaded', function() {
            debugBookshelfStatus();
        });
        
        // 监听书架按钮点击
        document.addEventListener('click', function(e) {
            if (e.target.classList.contains('bookshelf-btn')) {
                const bookTitle = e.target.dataset.bookTitle || '未知';
                debugBookshelfAction('书架操作', bookTitle);
            }
        });
    }
}

// 页面加载时初始化调试功能
initBookshelfDebug();

// 导出调试函数供其他脚本使用
window.bookshelfDebug = {
    debugLog,
    debugBookshelfStatus,
    debugBookshelfAction,
    debugApiResponse,
    debugBookshelfDataLoad
};

