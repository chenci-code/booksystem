/**
 * 书籍列表页面特有功能
 */

// 页面加载完成后初始化书籍列表功能
document.addEventListener('DOMContentLoaded', function() {
    initializeBookList();
});

/**
 * 初始化书籍列表功能
 */
function initializeBookList() {
    // 初始化筛选功能
    initializeFilters();
    
    // 初始化排序功能
    initializeSorting();
    
    // 初始化书籍卡片交互
    initializeBookCards();
    
    // 初始化分页功能
    initializePagination();
    
    // 初始化搜索功能
    initializeSearchEnhancements();
}

/**
 * 初始化筛选功能
 */
function initializeFilters() {
    // 为筛选选项添加点击效果
    const filterOptions = document.querySelectorAll('.filter-option');
    filterOptions.forEach(option => {
        option.addEventListener('click', function(e) {
            // 添加点击动画效果
            this.style.transform = 'scale(0.95)';
            setTimeout(() => {
                this.style.transform = '';
            }, 150);
        });
    });
    
    // 添加筛选选项的悬停效果
    filterOptions.forEach(option => {
        option.addEventListener('mouseenter', function() {
            if (!this.classList.contains('active')) {
                this.style.transform = 'translateY(-2px)';
            }
        });
        
        option.addEventListener('mouseleave', function() {
            if (!this.classList.contains('active')) {
                this.style.transform = '';
            }
        });
    });
}

/**
 * 初始化排序功能
 */
function initializeSorting() {
    const sortSelect = document.querySelector('select[name="sort"]');
    if (sortSelect) {
        sortSelect.addEventListener('change', function() {
            // 显示加载状态
            NovelSystem.showLoading();
            
            // 构建新的URL
            const currentUrl = new URL(window.location);
            currentUrl.searchParams.set('sort', this.value);
            
            // 跳转到新的URL
            window.location.href = currentUrl.toString();
        });
    }
}

/**
 * 初始化书籍卡片交互
 */
function initializeBookCards() {
    const bookCards = document.querySelectorAll('.book-card');
    
    bookCards.forEach(card => {
        // 添加卡片悬停效果
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-6px)';
            this.style.boxShadow = '0 25px 50px -12px rgba(0, 0, 0, 0.15), 0 10px 20px -5px rgba(0, 0, 0, 0.1)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = '';
            this.style.boxShadow = '';
        });
        
        // 添加点击效果
        card.addEventListener('click', function(e) {
            // 如果点击的是按钮，不处理卡片点击
            if (e.target.closest('.btn')) {
                return;
            }
            
            // 添加点击动画
            this.style.transform = 'scale(0.98)';
            setTimeout(() => {
                this.style.transform = '';
            }, 150);
        });
    });
}

/**
 * 初始化分页功能
 */
function initializePagination() {
    const pageLinks = document.querySelectorAll('.page-link');
    
    pageLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            // 显示加载状态
            NovelSystem.showLoading();
            
            // 添加点击效果
            this.style.transform = 'scale(0.9)';
            setTimeout(() => {
                this.style.transform = '';
            }, 150);
        });
    });
}

/**
 * 初始化搜索增强功能
 */
function initializeSearchEnhancements() {
    const searchInput = document.querySelector('input[name="search"]');
    if (searchInput) {
        // 添加搜索建议功能
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value.trim();
            
            if (query.length > 2) {
                searchTimeout = setTimeout(() => {
                    showSearchSuggestions(query);
                }, 300);
            } else {
                hideSearchSuggestions();
            }
        });
        
        // 添加搜索历史功能
        loadSearchHistory();
    }
}

/**
 * 显示搜索建议
 */
function showSearchSuggestions(query) {
    // 这里应该调用API获取搜索建议
    // 暂时使用模拟数据
    const suggestions = [
        '玄幻小说',
        '都市言情',
        '历史军事',
        '科幻未来',
        '悬疑推理'
    ].filter(item => item.includes(query));
    
    if (suggestions.length > 0) {
        createSearchSuggestionsDropdown(suggestions);
    }
}

/**
 * 创建搜索建议下拉框
 */
function createSearchSuggestionsDropdown(suggestions) {
    // 移除现有的建议框
    hideSearchSuggestions();
    
    const searchInput = document.querySelector('input[name="search"]');
    if (!searchInput) return;
    
    const dropdown = document.createElement('div');
    dropdown.className = 'search-suggestions';
    dropdown.style.cssText = `
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        box-shadow: 0 10px 25px -3px rgba(0, 0, 0, 0.1);
        z-index: 1000;
        max-height: 200px;
        overflow-y: auto;
    `;
    
    suggestions.forEach(suggestion => {
        const item = document.createElement('div');
        item.className = 'suggestion-item';
        item.textContent = suggestion;
        item.style.cssText = `
            padding: 0.75rem 1rem;
            cursor: pointer;
            transition: background-color 0.2s ease;
        `;
        
        item.addEventListener('mouseenter', function() {
            this.style.backgroundColor = '#f9fafb';
        });
        
        item.addEventListener('mouseleave', function() {
            this.style.backgroundColor = '';
        });
        
        item.addEventListener('click', function() {
            searchInput.value = suggestion;
            hideSearchSuggestions();
            // 触发搜索
            const form = searchInput.closest('form');
            if (form) {
                form.submit();
            }
        });
        
        dropdown.appendChild(item);
    });
    
    // 定位搜索输入框的父容器
    const searchContainer = searchInput.closest('.relative') || searchInput.parentElement;
    searchContainer.style.position = 'relative';
    searchContainer.appendChild(dropdown);
}

/**
 * 隐藏搜索建议
 */
function hideSearchSuggestions() {
    const existingDropdown = document.querySelector('.search-suggestions');
    if (existingDropdown) {
        existingDropdown.remove();
    }
}

/**
 * 加载搜索历史
 */
function loadSearchHistory() {
    const searchHistory = JSON.parse(localStorage.getItem('searchHistory') || '[]');
    if (searchHistory.length > 0) {
        // 可以在这里显示搜索历史
    }
}

/**
 * 保存搜索历史
 */
function saveSearchHistory(query) {
    if (!query.trim()) return;
    
    let searchHistory = JSON.parse(localStorage.getItem('searchHistory') || '[]');
    
    // 移除重复项
    searchHistory = searchHistory.filter(item => item !== query);
    
    // 添加到开头
    searchHistory.unshift(query);
    
    // 限制历史记录数量
    if (searchHistory.length > 10) {
        searchHistory = searchHistory.slice(0, 10);
    }
    
    localStorage.setItem('searchHistory', JSON.stringify(searchHistory));
}

/**
 * 初始化书籍图片懒加载
 */
function initializeLazyLoading() {
    const bookImages = document.querySelectorAll('.book-cover img');
    
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src || img.src;
                    img.classList.add('loaded');
                    observer.unobserve(img);
                }
            });
        });
        
        bookImages.forEach(img => {
            imageObserver.observe(img);
        });
    }
}

/**
 * 初始化无限滚动（如果适用）
 */
function initializeInfiniteScroll() {
    let isLoading = false;
    
    window.addEventListener('scroll', NovelSystem.throttle(() => {
        if (isLoading) return;
        
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const windowHeight = window.innerHeight;
        const documentHeight = document.documentElement.scrollHeight;
        
        // 当滚动到距离底部100px时加载更多
        if (scrollTop + windowHeight >= documentHeight - 100) {
            loadMoreBooks();
        }
    }, 200));
}

/**
 * 加载更多书籍
 */
function loadMoreBooks() {
    const nextPageLink = document.querySelector('.pagination .page-link[rel="next"]');
    if (!nextPageLink) return;
    
    isLoading = true;
    NovelSystem.showLoading();
    
    // 这里应该调用API加载更多书籍
    // 暂时使用模拟延迟
    setTimeout(() => {
        NovelSystem.hideLoading();
        isLoading = false;
        // 实际实现中应该加载新内容并更新页面
    }, 1000);
}

/**
 * 验证图片URL是否有效
 */
function isValidImageUrl(url) {
    if (!url || url.trim() === '' || url === 'None' || url === 'null' || url === 'undefined') {
        return false;
    }
    
    // 检查URL长度
    if (url.length < 10) {
        return false;
    }
    
    // 检查是否是有效的URL格式
    try {
        new URL(url);
        return true;
    } catch (e) {
        return false;
    }
}

/**
 * 处理封面图片加载
 */
function handleCoverImageLoad() {
    const coverImages = document.querySelectorAll('.book-cover-img');
    coverImages.forEach(img => {
        const src = img.src;
        
        // 验证URL
        if (!isValidImageUrl(src)) {
            img.style.display = 'none';
            const noCover = img.nextElementSibling;
            if (noCover && noCover.classList.contains('no-cover')) {
                noCover.style.display = 'flex';
            }
            return;
        }
        
        // 如果图片已经加载完成
        if (img.complete && img.naturalHeight !== 0) {
            img.classList.add('loaded');
            img.style.display = 'block';
            const noCover = img.nextElementSibling;
            if (noCover && noCover.classList.contains('no-cover')) {
                noCover.style.display = 'none';
            }
        } else if (img.complete && img.naturalHeight === 0) {
            // 图片加载失败
            img.style.display = 'none';
            const noCover = img.nextElementSibling;
            if (noCover && noCover.classList.contains('no-cover')) {
                noCover.style.display = 'flex';
            }
        }
    });
}

/**
 * 初始化图片加载处理
 */
function initializeImageLoading() {
    // 立即处理封面图片
    handleCoverImageLoad();
    
    // 页面加载完成后再次处理封面
    window.addEventListener('load', handleCoverImageLoad);
    
    // 监听图片加载事件
    document.addEventListener('load', handleCoverImageLoad, true);
    
    // 添加超时处理，防止图片加载时间过长
    setTimeout(() => {
        const coverImages = document.querySelectorAll('.book-cover-img');
        coverImages.forEach(img => {
            if (!img.classList.contains('loaded') && img.style.display !== 'none') {
                // 如果图片在3秒内没有加载完成，显示占位符
                img.style.display = 'none';
                const noCover = img.nextElementSibling;
                if (noCover && noCover.classList.contains('no-cover')) {
                    noCover.style.display = 'flex';
                }
            }
        });
    }, 3000);
}

// 页面加载完成后初始化所有功能
document.addEventListener('DOMContentLoaded', function() {
    initializeLazyLoading();
    initializeInfiniteScroll();
    initializeImageLoading();
});
