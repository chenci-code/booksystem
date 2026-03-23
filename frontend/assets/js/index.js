// 首页JavaScript功能

document.addEventListener('DOMContentLoaded', function() {
    initializeHomePage();
});

function initializeHomePage() {
    // 初始化轮换推荐功能
    initRotatingRecommendations();
    
    // 初始化书籍卡片动画
    initBookCardAnimations();
    
    // 初始化懒加载
    initLazyLoading();
}

// 轮换推荐功能
function initRotatingRecommendations() {
    // 自动轮换推荐（每30秒）
    setInterval(function() {
        if (Math.random() < 0.3) { // 30%的概率自动刷新
            refreshRecommendations();
        }
    }, 30000);
}

// 刷新推荐书籍
function refreshRecommendations() {
    const rotatingGrid = document.getElementById('rotating-books-grid');
    if (!rotatingGrid) return;
    
    // 显示加载状态
    showLoadingState(rotatingGrid);
    
    fetch('/api/rotating-recommendations/')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateRotatingBooks(data.books);
                showMessage('推荐已更新！', 'success');
            } else {
                showMessage('更新失败：' + data.message, 'error');
            }
        })
        .catch(error => {
            console.error('刷新推荐失败:', error);
            showMessage('网络错误，请稍后重试', 'error');
        })
        .finally(() => {
            hideLoadingState(rotatingGrid);
        });
}

// 显示加载状态
function showLoadingState(container) {
    container.style.opacity = '0.6';
    container.style.pointerEvents = 'none';
    
    // 添加加载动画
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'loading-overlay';
    loadingDiv.innerHTML = `
        <div class="flex items-center justify-center h-64">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <span class="ml-3 text-gray-600">正在更新推荐...</span>
        </div>
    `;
    container.appendChild(loadingDiv);
}

// 隐藏加载状态
function hideLoadingState(container) {
    container.style.opacity = '1';
    container.style.pointerEvents = 'auto';
    
    const loadingOverlay = container.querySelector('.loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.remove();
    }
}

// 更新轮换书籍
function updateRotatingBooks(books) {
    const rotatingGrid = document.getElementById('rotating-books-grid');
    if (!rotatingGrid) return;
    
    // 淡出动画
    rotatingGrid.style.transition = 'opacity 0.3s ease';
    rotatingGrid.style.opacity = '0';
    
    setTimeout(() => {
        // 清空现有内容
        rotatingGrid.innerHTML = '';
        
        // 添加新书籍
        books.forEach(book => {
            const bookCard = createBookCard(book);
            rotatingGrid.appendChild(bookCard);
        });
        
        // 淡入动画
        rotatingGrid.style.opacity = '1';
        
        // 重新初始化懒加载
        initLazyLoading();
    }, 300);
}

// 创建书籍卡片
function createBookCard(book) {
    const cardElement = document.createElement('a');
    cardElement.href = `/book/${book.book_id}/`;
    cardElement.className = 'card book-card group block';
    
    const coverHtml = book.cover_url && book.cover_url.trim() && 
                     book.cover_url !== 'None' && book.cover_url !== 'null' && 
                     book.cover_url !== 'undefined' && book.cover_url.length > 10 ? `
        <img src="${book.cover_url}" 
             class="w-full h-full book-cover-img" 
             alt="${book.title}" 
             loading="lazy"
             onload="this.classList.add('loaded'); this.style.display='block'; this.nextElementSibling.style.display='none';"
             onerror="this.style.display='none'; this.nextElementSibling.style.display='flex'; this.classList.remove('loaded');">
        <div class="no-cover" style="display: none;">
            <i class="fas fa-book"></i>
        </div>
    ` : `
        <div class="no-cover">
            <i class="fas fa-book"></i>
        </div>
    `;
    
    cardElement.innerHTML = `
        <div class="book-cover">
            ${coverHtml}
        </div>
        <div class="card-body">
            <h3 class="font-semibold text-gray-900 mb-2 line-clamp-2">${book.title}</h3>
            <p class="text-gray-600 text-sm mb-2">${book.author}</p>
            <p class="text-gray-500 text-xs mb-3 line-clamp-2">${truncateText(book.description || '', 100)}</p>
            
            <div class="book-meta mb-3">
                <span class="badge bg-secondary">${book.category}</span>
                <span class="badge bg-info">${book.status}</span>
                <span class="badge bg-success">${book.chapter_count}章</span>
            </div>
            
            <div class="book-stats grid grid-cols-3 gap-2 text-center mb-3">
                <div class="text-xs text-gray-500">
                    <i class="fas fa-star text-yellow-400 block mb-1"></i>
                    ${book.rating.toFixed(1)}
                </div>
                <div class="text-xs text-gray-500">
                    <i class="fas fa-heart text-red-400 block mb-1"></i>
                    ${book.collection_count}
                </div>
                <div class="text-xs text-gray-500">
                    <i class="fas fa-book text-blue-600 block mb-1"></i>
                    ${book.word_count || '未知'}
                </div>
            </div>
            
            ${book.update_time ? `
                <div class="text-xs text-gray-500 mb-3">
                    <i class="fas fa-calendar mr-1"></i> 更新于 ${book.update_time}
                </div>
            ` : ''}
        </div>
    `;
    
    return cardElement;
}

// 初始化书籍卡片动画
function initBookCardAnimations() {
    const bookCards = document.querySelectorAll('.book-card');
    
    // 添加悬停效果
    bookCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-4px)';
            this.style.boxShadow = '0 8px 25px rgba(0, 0, 0, 0.15)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '';
        });
    });
    
    // 添加进入视口动画
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, {
        threshold: 0.1
    });
    
    bookCards.forEach(card => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(card);
    });
}

// 初始化懒加载
function initLazyLoading() {
    const images = document.querySelectorAll('img[loading="lazy"]');
    
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.src; // 触发加载
                    img.classList.remove('lazy');
                    imageObserver.unobserve(img);
                }
            });
        });
        
        images.forEach(img => imageObserver.observe(img));
    }
}

// 工具函数：截断文本
function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// 显示消息提示
function showMessage(message, type = 'info') {
    const alertClass = type === 'success' ? 'bg-green-100 border-green-400 text-green-700' : 
                      type === 'error' ? 'bg-red-100 border-red-400 text-red-700' :
                      'bg-blue-100 border-blue-400 text-blue-700';
    
    const iconClass = type === 'success' ? 'fa-check-circle text-green-400' : 
                     type === 'error' ? 'fa-exclamation-circle text-red-400' :
                     'fa-info-circle text-blue-400';
    
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

// 平滑滚动到指定区域
function scrollToSection(sectionId) {
    const section = document.getElementById(sectionId);
    if (section) {
        section.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });
    }
}

// 添加键盘快捷键支持
document.addEventListener('keydown', function(e) {
    // Ctrl + R 刷新推荐
    if (e.ctrlKey && e.key === 'r') {
        e.preventDefault();
        refreshRecommendations();
    }
    
    // 数字键快速跳转到对应区域
    if (e.key >= '1' && e.key <= '4') {
        const sections = ['rotating-books-section', 'collaborative-books-section', 'popular-books-section', 'latest-books-section'];
        const sectionIndex = parseInt(e.key) - 1;
        if (sections[sectionIndex]) {
            scrollToSection(sections[sectionIndex]);
        }
    }
});

// 添加页面可见性API支持，页面重新可见时刷新推荐
document.addEventListener('visibilitychange', function() {
    if (!document.hidden && Math.random() < 0.2) { // 20%的概率刷新
        setTimeout(() => {
            refreshRecommendations();
        }, 1000);
    }
});