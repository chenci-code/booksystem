/**
 * 小说阅读系统 - 公共JavaScript文件
 * 提供全局功能和初始化逻辑
 */

// 确保配置和工具函数已加载
if (typeof NovelSystemConfig === 'undefined') {
    console.error('NovelSystemConfig is not loaded. Please include config.js before common.js');
}

if (typeof NovelSystemUtils === 'undefined') {
    console.error('NovelSystemUtils is not loaded. Please include utils.js before common.js');
}

/**
 * 公共功能模块
 */
const NovelSystem = {
    /**
     * 显示提示消息
     * @param {string} message - 消息内容
     * @param {string} type - 消息类型 ('success' | 'error' | 'warning' | 'info')
     * @param {number} duration - 显示时长（毫秒）
     */
    showMessage(message, type = 'info', duration = null) {
        if (!message) return;
        
        const delay = duration || NovelSystemConfig?.MESSAGES?.AUTO_CLOSE_DELAY || 5000;
        const messageContainer = document.createElement('div');
        messageContainer.className = `fixed top-4 right-4 z-50 p-4 rounded-lg border-l-4 max-w-sm transition-all duration-300 transform translate-x-full shadow-lg`;
        
        // 根据类型设置样式和图标
        const typeConfig = {
            success: {
                class: 'bg-green-50 border-green-400 text-green-700',
                icon: 'check-circle'
            },
            error: {
                class: 'bg-red-50 border-red-400 text-red-700',
                icon: 'exclamation-circle'
            },
            warning: {
                class: 'bg-yellow-50 border-yellow-400 text-yellow-700',
                icon: 'exclamation-triangle'
            },
            info: {
                class: 'bg-blue-50 border-blue-400 text-blue-700',
                icon: 'info-circle'
            }
        };
        
        const config = typeConfig[type] || typeConfig.info;
        messageContainer.classList.add(...config.class.split(' '));
        
        messageContainer.innerHTML = `
            <div class="flex items-center justify-between">
                <div class="flex items-center">
                    <i class="fas fa-${config.icon} mr-2"></i>
                    <span>${message}</span>
                </div>
                <button type="button" class="ml-4 text-gray-400 hover:text-gray-600 transition-colors" 
                        onclick="this.closest('.fixed').remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        document.body.appendChild(messageContainer);
        
        // 显示动画
        requestAnimationFrame(() => {
            messageContainer.classList.remove('translate-x-full');
        });
        
        // 自动关闭
        if (delay > 0) {
            setTimeout(() => {
                messageContainer.classList.add('translate-x-full');
                setTimeout(() => {
                    if (messageContainer.parentElement) {
                        messageContainer.remove();
                    }
                }, 300);
            }, delay);
        }
    },
    
    /**
     * 显示加载状态
     * @param {HTMLElement} element - 要显示加载状态的元素
     * @param {string} loadingText - 加载文本
     */
    showLoading(element, loadingText = '加载中...') {
        if (!element) return;
        
        element.disabled = true;
        const originalText = element.innerHTML;
        element.innerHTML = `<i class="fas fa-spinner fa-spin mr-2"></i>${loadingText}`;
        element.dataset.originalText = originalText;
        element.dataset.loading = 'true';
    },
    
    /**
     * 隐藏加载状态
     * @param {HTMLElement} element - 要隐藏加载状态的元素
     */
    hideLoading(element) {
        if (!element || !element.dataset.loading) return;
        
        element.disabled = false;
        if (element.dataset.originalText) {
            element.innerHTML = element.dataset.originalText;
            delete element.dataset.originalText;
        }
        delete element.dataset.loading;
    },
    
    /**
     * 显示全屏加载遮罩
     * @param {string} text - 加载文本
     */
    showLoadingOverlay(text = '加载中...') {
        // 移除已存在的加载遮罩
        this.hideLoadingOverlay();
        
        const overlay = NovelSystemUtils.createLoadingElement(text);
        overlay.id = 'novel-system-loading-overlay';
        document.body.appendChild(overlay);
    },
    
    /**
     * 隐藏全屏加载遮罩
     */
    hideLoadingOverlay() {
        const overlay = document.getElementById('novel-system-loading-overlay');
        if (overlay) {
            overlay.remove();
        }
    },
    
    /**
     * 确认对话框
     * @param {string} message - 确认消息
     * @param {Function} callback - 确认后的回调函数
     * @returns {boolean} 是否确认
     */
    confirmAction(message, callback) {
        if (confirm(message)) {
            if (typeof callback === 'function') {
                callback();
            }
            return true;
        }
        return false;
    },
    
    // 将工具函数暴露为别名，保持向后兼容
    getCookie: (name) => NovelSystemUtils.getCookie(name),
    formatDate: (date, format) => NovelSystemUtils.formatDate(date, format),
    formatPrice: (price) => NovelSystemUtils.formatPrice(price),
    formatNumber: (num) => NovelSystemUtils.formatNumber(num),
    truncateText: (text, maxLength, suffix) => NovelSystemUtils.truncateText(text, maxLength, suffix),
    debounce: (func, wait) => NovelSystemUtils.debounce(func, wait),
    throttle: (func, limit) => NovelSystemUtils.throttle(func, limit),
};

/**
 * 初始化提示消息自动关闭
 */
function initAutoCloseMessages() {
    const messages = document.querySelectorAll('.alert, [class*="bg-red-50"], [class*="bg-yellow-50"], [class*="bg-green-50"], [class*="bg-blue-50"]');
    const delay = NovelSystemConfig?.MESSAGES?.AUTO_CLOSE_DELAY || 5000;
    
    messages.forEach((message) => {
        setTimeout(() => {
            if (message.parentElement) {
                message.style.opacity = '0';
                message.style.transform = 'translateY(-10px)';
                message.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                
                setTimeout(() => {
                    message.remove();
                }, 300);
            }
        }, delay);
    });
}

/**
 * 初始化搜索功能
 */
function initSearchFeatures() {
    const searchInputs = document.querySelectorAll('input[type="search"]');
    
    searchInputs.forEach((input) => {
        // 搜索框回车提交
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const form = input.closest('form');
                if (form) {
                    const searchValue = input.value.trim();
                    const minLength = NovelSystemConfig?.SEARCH?.MIN_QUERY_LENGTH || 2;
                    
                    if (searchValue.length < minLength && searchValue.length > 0) {
                        e.preventDefault();
                        NovelSystem.showMessage(
                            `搜索关键词至少需要${minLength}个字符`,
                            'warning'
                        );
                        return;
                    }
                    
                    form.submit();
                }
            }
        });
        
        // 搜索框焦点效果
        input.addEventListener('focus', () => {
            const parent = input.parentElement;
            if (parent) {
                parent.classList.add('ring-2', 'ring-blue-500');
            }
        });
        
        input.addEventListener('blur', () => {
            const parent = input.parentElement;
            if (parent) {
                parent.classList.remove('ring-2', 'ring-blue-500');
            }
        });
    });
}

/**
 * 初始化用户交互功能
 */
function initUserInteractions() {
    // 添加按钮点击波纹效果
    const buttons = document.querySelectorAll('button.btn, .btn');
    
    buttons.forEach((button) => {
        // 避免重复绑定
        if (button.dataset.rippleInitialized) return;
        button.dataset.rippleInitialized = 'true';
        
        button.addEventListener('click', function(e) {
            // 创建波纹效果
            const ripple = document.createElement('span');
            ripple.classList.add('ripple');
            
            const rect = button.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            
            button.style.position = 'relative';
            button.style.overflow = 'hidden';
            button.appendChild(ripple);
            
            setTimeout(() => {
                if (ripple.parentElement) {
                    ripple.remove();
                }
            }, 600);
        });
    });
}

/**
 * 初始化购物车计数更新
 */
function initCartCount() {
    if (!NovelSystemUtils.isUserLoggedIn()) return;
    
    const updateCartCount = async () => {
        try {
            const data = await NovelSystemUtils.fetchApi(
                NovelSystemConfig?.API?.CART_COUNT || '/api/cart-count/'
            );
            
            const cartRedDot = document.querySelector('#cart-red-dot');
            if (cartRedDot) {
                cartRedDot.style.display = data.count > 0 ? 'block' : 'none';
            }
        } catch (error) {
            console.error('Error fetching cart count:', error);
        }
    };
    
    // 页面加载时更新
    updateCartCount();
    
    // 将更新函数暴露到全局，供其他脚本使用
    window.updateCartCount = updateCartCount;
}

// 页面加载完成后执行初始化
document.addEventListener('DOMContentLoaded', () => {
    try {
        initAutoCloseMessages();
        initSearchFeatures();
        initUserInteractions();
        initCartCount();
    } catch (error) {
        console.error('Error initializing common features:', error);
    }
});

// 将NovelSystem暴露到全局作用域，保持向后兼容
window.NovelSystem = NovelSystem;
window.showMessage = NovelSystem.showMessage.bind(NovelSystem);
window.showLoading = NovelSystem.showLoading.bind(NovelSystem);
window.hideLoading = NovelSystem.hideLoading.bind(NovelSystem);
window.confirmAction = NovelSystem.confirmAction.bind(NovelSystem);
window.getCookie = NovelSystem.getCookie;