/**
 * 小说阅读系统 - 工具函数库
 * 提供通用的工具函数，避免代码重复
 */

const NovelSystemUtils = {
    /**
     * 获取Cookie值
     * @param {string} name - Cookie名称
     * @returns {string|null} Cookie值，如果不存在则返回null
     */
    getCookie(name) {
        if (!name || !document.cookie) {
            return null;
        }
        
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                return decodeURIComponent(cookie.substring(name.length + 1));
            }
        }
        return null;
    },
    
    /**
     * 设置Cookie
     * @param {string} name - Cookie名称
     * @param {string} value - Cookie值
     * @param {number} days - 过期天数（可选）
     */
    setCookie(name, value, days = 7) {
        const expires = days ? `; expires=${new Date(Date.now() + days * 86400000).toUTCString()}` : '';
        document.cookie = `${name}=${encodeURIComponent(value)}${expires}; path=/`;
    },
    
    /**
     * 删除Cookie
     * @param {string} name - Cookie名称
     */
    deleteCookie(name) {
        document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
    },
    
    /**
     * 防抖函数
     * @param {Function} func - 要执行的函数
     * @param {number} wait - 等待时间（毫秒）
     * @returns {Function} 防抖后的函数
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    /**
     * 节流函数
     * @param {Function} func - 要执行的函数
     * @param {number} limit - 时间限制（毫秒）
     * @returns {Function} 节流后的函数
     */
    throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },
    
    /**
     * 格式化日期
     * @param {Date|string} date - 日期对象或日期字符串
     * @param {string} format - 格式类型（'short' | 'long' | 'datetime'）
     * @returns {string} 格式化后的日期字符串
     */
    formatDate(date, format = 'short') {
        if (!date) return '';
        
        const dateObj = date instanceof Date ? date : new Date(date);
        if (isNaN(dateObj.getTime())) return '';
        
        const options = {
            short: {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit'
            },
            long: {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            },
            datetime: {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            }
        };
        
        return dateObj.toLocaleDateString('zh-CN', options[format] || options.short);
    },
    
    /**
     * 格式化价格
     * @param {number|string} price - 价格
     * @returns {string} 格式化后的价格字符串
     */
    formatPrice(price) {
        const num = parseFloat(price);
        if (isNaN(num)) return '¥0.00';
        return `¥${num.toFixed(2)}`;
    },
    
    /**
     * 格式化数字（添加千位分隔符）
     * @param {number|string} num - 数字
     * @returns {string} 格式化后的数字字符串
     */
    formatNumber(num) {
        const number = parseFloat(num);
        if (isNaN(number)) return '0';
        return number.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    },
    
    /**
     * 截断文本
     * @param {string} text - 文本
     * @param {number} maxLength - 最大长度
     * @param {string} suffix - 后缀（默认为'...'）
     * @returns {string} 截断后的文本
     */
    truncateText(text, maxLength, suffix = '...') {
        if (!text || text.length <= maxLength) {
            return text;
        }
        return text.substring(0, maxLength) + suffix;
    },
    
    /**
     * 验证URL是否有效
     * @param {string} url - URL字符串
     * @returns {boolean} 是否有效
     */
    isValidUrl(url) {
        if (!url || typeof url !== 'string') return false;
        if (url === 'None' || url === 'null' || url === 'undefined') return false;
        if (url.length < 10) return false;
        
        try {
            new URL(url);
            return true;
        } catch (e) {
            return false;
        }
    },
    
    /**
     * 验证图片URL是否有效
     * @param {string} url - 图片URL
     * @returns {boolean} 是否有效
     */
    isValidImageUrl(url) {
        if (!this.isValidUrl(url)) return false;
        
        const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'];
        const lowerUrl = url.toLowerCase();
        return imageExtensions.some(ext => lowerUrl.includes(ext)) || lowerUrl.includes('image');
    },
    
    /**
     * 获取URL参数
     * @param {string} name - 参数名称
     * @returns {string|null} 参数值
     */
    getUrlParam(name) {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get(name);
    },
    
    /**
     * 设置URL参数
     * @param {string} name - 参数名称
     * @param {string} value - 参数值
     */
    setUrlParam(name, value) {
        const url = new URL(window.location);
        url.searchParams.set(name, value);
        window.history.pushState({}, '', url);
    },
    
    /**
     * 从本地存储获取数据
     * @param {string} key - 存储键名
     * @param {*} defaultValue - 默认值
     * @returns {*} 存储的数据
     */
    getLocalStorage(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (e) {
            console.error(`Error reading localStorage key "${key}":`, e);
            return defaultValue;
        }
    },
    
    /**
     * 设置本地存储数据
     * @param {string} key - 存储键名
     * @param {*} value - 要存储的数据
     */
    setLocalStorage(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (e) {
            console.error(`Error writing localStorage key "${key}":`, e);
        }
    },
    
    /**
     * 移除本地存储数据
     * @param {string} key - 存储键名
     */
    removeLocalStorage(key) {
        try {
            localStorage.removeItem(key);
        } catch (e) {
            console.error(`Error removing localStorage key "${key}":`, e);
        }
    },
    
    /**
     * 创建加载中的元素
     * @param {string} text - 加载文本
     * @returns {HTMLElement} 加载元素
     */
    createLoadingElement(text = '加载中...') {
        const loading = document.createElement('div');
        loading.className = 'loading-overlay';
        loading.innerHTML = `
            <div class="loading-spinner">
                <div class="spinner-border"></div>
                <p class="mt-2">${text}</p>
            </div>
        `;
        return loading;
    },
    
    /**
     * 处理API错误
     * @param {Error} error - 错误对象
     * @param {string} defaultMessage - 默认错误消息
     */
    handleApiError(error, defaultMessage = '操作失败，请重试') {
        console.error('API Error:', error);
        
        let message = defaultMessage;
        if (error.message) {
            message = error.message;
        } else if (error.response && error.response.data && error.response.data.message) {
            message = error.response.data.message;
        }
        
        return message;
    },
    
    /**
     * 发送API请求
     * @param {string} url - API URL
     * @param {object} options - 请求选项
     * @returns {Promise} Promise对象
     */
    async fetchApi(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin',
        };
        
        // 添加CSRF Token
        const csrfToken = this.getCookie('csrftoken');
        if (csrfToken) {
            defaultOptions.headers['X-CSRFToken'] = csrfToken;
        }
        
        // 合并选项
        const finalOptions = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...(options.headers || {}),
            },
        };
        
        try {
            const response = await fetch(url, finalOptions);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || `HTTP error! status: ${response.status}`);
            }
            
            return data;
        } catch (error) {
            throw this.handleApiError(error);
        }
    },
    
    /**
     * 检查用户是否已登录
     * @returns {boolean} 是否已登录
     */
    isUserLoggedIn() {
        // 检查页面中是否有用户信息
        const userMenu = document.querySelector('.group button span');
        const isLoggedIn = userMenu && userMenu.textContent.trim() !== '';
        return isLoggedIn || document.body.classList.contains('logged-in');
    },
    
    /**
     * 滚动到指定元素
     * @param {HTMLElement|string} element - 元素或选择器
     * @param {object} options - 滚动选项
     */
    scrollTo(element, options = {}) {
        const target = typeof element === 'string' 
            ? document.querySelector(element) 
            : element;
        
        if (!target) return;
        
        const defaultOptions = {
            behavior: 'smooth',
            block: 'start',
        };
        
        target.scrollIntoView({ ...defaultOptions, ...options });
    },
    
    /**
     * 复制文本到剪贴板
     * @param {string} text - 要复制的文本
     * @returns {Promise<boolean>} 是否复制成功
     */
    async copyToClipboard(text) {
        try {
            if (navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(text);
                return true;
            } else {
                // 降级方案
                const textArea = document.createElement('textarea');
                textArea.value = text;
                textArea.style.position = 'fixed';
                textArea.style.opacity = '0';
                document.body.appendChild(textArea);
                textArea.select();
                const success = document.execCommand('copy');
                document.body.removeChild(textArea);
                return success;
            }
        } catch (e) {
            console.error('Failed to copy text:', e);
            return false;
        }
    },
};

// 导出工具对象（如果使用模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NovelSystemUtils;
}


