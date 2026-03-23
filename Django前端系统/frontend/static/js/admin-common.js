/**
 * 管理界面通用JavaScript功能
 * 版本: 1.0
 */

// 管理界面通用类
class AdminCommon {
    constructor() {
        this.init();
    }

    init() {
        this.bindEvents();
    }

    // 获取CSRF令牌
    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        if (token) {
            return token.value;
        }
        // 如果找不到CSRF令牌，尝试从cookie获取
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        return '';
    }

    // 显示消息提示
    showMessage(message, type = 'success') {
        const iconClass = type === 'success' ? 'fa-check-circle text-green-400' : 'fa-exclamation-circle text-red-400';
        
        const alertHtml = `
        <div class="fixed top-4 right-4 z-50 max-w-sm w-full bg-white shadow-lg rounded-lg pointer-events-auto ring-1 ring-black ring-opacity-5 overflow-hidden">
            <div class="p-4">
                <div class="flex items-start">
                    <div class="flex-shrink-0">
                        <i class="fas ${iconClass}"></i>
                    </div>
                    <div class="ml-3 w-0 flex-1 pt-0.5">
                        <p class="text-sm font-medium text-gray-900">${message}</p>
                    </div>
                    <div class="ml-4 flex-shrink-0 flex">
                        <button class="bg-white rounded-md inline-flex text-gray-400 hover:text-gray-500 focus:outline-none" onclick="this.parentElement.parentElement.parentElement.parentElement.remove()">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>
        `;

        document.body.insertAdjacentHTML('beforeend', alertHtml);

        // 3秒后自动消失
        setTimeout(() => {
            const alert = document.querySelector('.fixed.top-4.right-4');
            if (alert) {
                alert.remove();
            }
        }, 3000);
    }

    // 显示确认对话框
    showConfirm(message, onConfirm, onCancel = null) {
        const confirmHtml = `
        <div id="confirmModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center">
            <div class="relative p-5 border w-96 shadow-lg rounded-md bg-white">
                <div class="mt-3 text-center">
                    <div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-yellow-100 mb-4">
                        <i class="fas fa-exclamation-triangle text-yellow-600"></i>
                    </div>
                    <h3 class="text-lg font-medium text-gray-900 mb-4">确认操作</h3>
                    <p class="text-sm text-gray-500 mb-6">${message}</p>
                    <div class="flex justify-center space-x-3">
                        <button id="confirmCancel" class="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-500">
                            取消
                        </button>
                        <button id="confirmOk" class="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500">
                            确认
                        </button>
                    </div>
                </div>
            </div>
        </div>
        `;

        document.body.insertAdjacentHTML('beforeend', confirmHtml);

        const modal = document.getElementById('confirmModal');
        const confirmBtn = document.getElementById('confirmOk');
        const cancelBtn = document.getElementById('confirmCancel');

        confirmBtn.onclick = () => {
            modal.remove();
            if (onConfirm) onConfirm();
        };

        cancelBtn.onclick = () => {
            modal.remove();
            if (onCancel) onCancel();
        };

        // 点击背景关闭
        modal.onclick = (e) => {
            if (e.target === modal) {
                modal.remove();
                if (onCancel) onCancel();
            }
        };
    }

    // API请求封装
    async apiRequest(url, options = {}) {
        try {
            const response = await fetch(url, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken(),
                    ...options.headers
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API请求失败 (${url}):`, error);
            this.showMessage('网络请求失败，请稍后重试', 'error');
            throw error;
        }
    }

    // 防抖函数
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
    }

    // 节流函数
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    // 绑定通用事件
    bindEvents() {
        // 表格行悬停效果
        document.addEventListener('DOMContentLoaded', () => {
            const tableRows = document.querySelectorAll('tbody tr');
            tableRows.forEach(row => {
                row.addEventListener('mouseenter', () => {
                    row.classList.add('bg-gray-50');
                });
                row.addEventListener('mouseleave', () => {
                    row.classList.remove('bg-gray-50');
                });
            });
        });
    }

    // 格式化日期
    formatDate(date, format = 'YYYY-MM-DD HH:mm') {
        if (!date) return '';
        
        const d = new Date(date);
        const year = d.getFullYear();
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        const hours = String(d.getHours()).padStart(2, '0');
        const minutes = String(d.getMinutes()).padStart(2, '0');
        const seconds = String(d.getSeconds()).padStart(2, '0');

        return format
            .replace('YYYY', year)
            .replace('MM', month)
            .replace('DD', day)
            .replace('HH', hours)
            .replace('mm', minutes)
            .replace('ss', seconds);
    }

    // 格式化数字
    formatNumber(num, decimals = 2) {
        if (num === null || num === undefined) return '0';
        return parseFloat(num).toFixed(decimals);
    }

    // 格式化文件大小
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // 复制到剪贴板
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            this.showMessage('已复制到剪贴板');
        } catch (err) {
            console.error('复制失败:', err);
            this.showMessage('复制失败', 'error');
        }
    }

    // 下载文件
    downloadFile(url, filename) {
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    // 验证表单
    validateForm(form) {
        const requiredFields = form.querySelectorAll('[required]');
        let isValid = true;

        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                field.classList.add('border-red-500');
                isValid = false;
            } else {
                field.classList.remove('border-red-500');
            }
        });

        return isValid;
    }

    // 重置表单
    resetForm(form) {
        form.reset();
        const errorFields = form.querySelectorAll('.border-red-500');
        errorFields.forEach(field => {
            field.classList.remove('border-red-500');
        });
    }

    // 设置加载状态
    setLoading(element, loading = true) {
        if (loading) {
            element.disabled = true;
            const originalText = element.textContent;
            element.dataset.originalText = originalText;
            element.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>处理中...';
        } else {
            element.disabled = false;
            element.textContent = element.dataset.originalText || '确定';
        }
    }

    // 图片懒加载
    initLazyLoading() {
        const images = document.querySelectorAll('img[data-src]');
        const imageObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    imageObserver.unobserve(img);
                }
            });
        });

        images.forEach(img => imageObserver.observe(img));
    }

    // 初始化工具提示
    initTooltips() {
        const tooltipElements = document.querySelectorAll('[data-tooltip]');
        tooltipElements.forEach(element => {
            element.addEventListener('mouseenter', (e) => {
                const tooltip = document.createElement('div');
                tooltip.className = 'absolute z-50 px-2 py-1 text-sm text-white bg-gray-900 rounded shadow-lg';
                tooltip.textContent = e.target.dataset.tooltip;
                tooltip.style.top = e.target.offsetTop - 30 + 'px';
                tooltip.style.left = e.target.offsetLeft + 'px';
                document.body.appendChild(tooltip);
                e.target.tooltipElement = tooltip;
            });

            element.addEventListener('mouseleave', (e) => {
                if (e.target.tooltipElement) {
                    e.target.tooltipElement.remove();
                    delete e.target.tooltipElement;
                }
            });
        });
    }
}

// 创建全局实例
window.adminCommon = new AdminCommon();

// 导出类供其他模块使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AdminCommon;
}