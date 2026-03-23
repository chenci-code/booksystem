/**
 * 小说阅读系统 - 主要JavaScript功能
 * 使用统一的工具函数和配置
 */

// 确保依赖已加载
if (typeof NovelSystemConfig === 'undefined' || typeof NovelSystemUtils === 'undefined') {
    console.error('Required dependencies not loaded. Please include config.js and utils.js before main.js');
}

// 应用状态
const AppState = {
    currentUser: null,
    cartItems: [],
    bookshelfItems: [],
};

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    try {
        initializeApp();
        setupEventListeners();
        loadUserData();
    } catch (error) {
        console.error('Error initializing app:', error);
    }
});

/**
 * 初始化应用
 */
function initializeApp() {
    // 检查用户登录状态
    checkLoginStatus();
    
    // 初始化工具提示
    initializeTooltips();
    
    // 初始化搜索功能
    initializeSearch();
    
    // 初始化购物车
    initializeCart();
    
    // 添加页面加载动画
    addPageAnimations();
}

/**
 * 设置事件监听器
 */
function setupEventListeners() {
    // 搜索框事件
    const searchInput = document.querySelector('input[name="search"]');
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                performSearch(this.value);
            }
        });
    }
    
    // 收藏按钮事件
    document.addEventListener('click', function(e) {
        if (e.target.closest('.collect-btn')) {
            e.preventDefault();
            const bookTitle = e.target.closest('.collect-btn').dataset.bookTitle;
            toggleCollection(bookTitle);
        }
    });
    
    // 书架按钮事件
    document.addEventListener('click', function(e) {
        if (e.target.closest('.bookshelf-btn')) {
            e.preventDefault();
            const bookTitle = e.target.closest('.bookshelf-btn').dataset.bookTitle;
            toggleBookshelf(bookTitle);
        }
    });
    
    // 购物车按钮事件
    document.addEventListener('click', function(e) {
        if (e.target.closest('.cart-btn')) {
            e.preventDefault();
            const bookTitle = e.target.closest('.cart-btn').dataset.bookTitle;
            const price = parseFloat(e.target.closest('.cart-btn').dataset.price);
            addToCart(bookTitle, price);
        }
    });
}

/**
 * 检查登录状态
 */
function checkLoginStatus() {
    const isLoggedIn = NovelSystemUtils.isUserLoggedIn();
    if (isLoggedIn) {
        AppState.currentUser = {
            username: document.body.dataset.username || '',
            name: document.body.dataset.name || '',
        };
    }
}

/**
 * 初始化工具提示
 */
function initializeTooltips() {
    // 创建简单的工具提示功能
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    tooltipElements.forEach(element => {
        element.addEventListener('mouseenter', showTooltip);
        element.addEventListener('mouseleave', hideTooltip);
    });
}

function showTooltip(event) {
    const element = event.target;
    const text = element.getAttribute('data-tooltip');
    
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = text;
    tooltip.style.position = 'absolute';
    tooltip.style.background = '#1f2937';
    tooltip.style.color = 'white';
    tooltip.style.padding = '0.5rem';
    tooltip.style.borderRadius = '0.375rem';
    tooltip.style.fontSize = '0.875rem';
    tooltip.style.zIndex = '1000';
    tooltip.style.pointerEvents = 'none';
    
    document.body.appendChild(tooltip);
    
    const rect = element.getBoundingClientRect();
    tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
    tooltip.style.top = rect.top - tooltip.offsetHeight - 8 + 'px';
    
    element._tooltip = tooltip;
}

function hideTooltip(event) {
    const element = event.target;
    if (element._tooltip) {
        element._tooltip.remove();
        delete element._tooltip;
    }
}

/**
 * 初始化搜索功能
 */
function initializeSearch() {
    const searchForm = document.querySelector('form[action*="book_list"]');
    if (!searchForm) return;
    
    searchForm.addEventListener('submit', function(e) {
        const searchInput = this.querySelector('input[name="search"]');
        if (searchInput) {
            const query = searchInput.value.trim();
            const minLength = NovelSystemConfig?.SEARCH?.MIN_QUERY_LENGTH || 2;
            
            if (query.length > 0 && query.length < minLength) {
                e.preventDefault();
                NovelSystem.showMessage(
                    NovelSystemConfig?.MESSAGES?.WARNING?.EMPTY_SEARCH || '请输入搜索关键词',
                    'warning'
                );
                return;
            }
        }
    });
}

/**
 * 初始化购物车
 */
function initializeCart() {
    try {
        const savedCart = NovelSystemUtils.getLocalStorage(
            NovelSystemConfig?.STORAGE?.CART_ITEMS || 'cartItems',
            []
        );
        AppState.cartItems = savedCart;
        updateCartDisplay();
    } catch (error) {
        console.error('Error initializing cart:', error);
        AppState.cartItems = [];
    }
}

/**
 * 加载用户数据
 */
function loadUserData() {
    if (!AppState.currentUser) return;
    
    try {
        // 加载用户收藏
        loadUserCollections();
        
        // 加载用户书架
        loadUserBookshelf();
        
        // 更新用户界面
        updateUserInterface();
    } catch (error) {
        console.error('Error loading user data:', error);
    }
}

/**
 * 执行搜索
 */
function performSearch(query) {
    const trimmedQuery = query.trim();
    const minLength = NovelSystemConfig?.SEARCH?.MIN_QUERY_LENGTH || 2;
    
    if (!trimmedQuery) {
        NovelSystem.showMessage(
            NovelSystemConfig?.MESSAGES?.WARNING?.EMPTY_SEARCH || '请输入搜索关键词',
            'warning'
        );
        return;
    }
    
    if (trimmedQuery.length < minLength) {
        NovelSystem.showMessage(
            `搜索关键词至少需要${minLength}个字符`,
            'warning'
        );
        return;
    }
    
    // 跳转到搜索结果页面
    window.location.href = `/books/?search=${encodeURIComponent(trimmedQuery)}`;
}

/**
 * 切换收藏状态
 */
async function toggleCollection(bookTitle) {
    if (!NovelSystemUtils.isUserLoggedIn()) {
        NovelSystem.showMessage(
            NovelSystemConfig?.MESSAGES?.ERROR?.NOT_LOGGED_IN || '请先登录',
            'warning'
        );
        return;
    }
    
    try {
        const isCollected = await isBookCollected(bookTitle);
        
        if (isCollected) {
            await removeFromCollection(bookTitle);
        } else {
            await addToCollection(bookTitle);
        }
    } catch (error) {
        console.error('Error toggling collection:', error);
        NovelSystem.showMessage(
            NovelSystemConfig?.MESSAGES?.ERROR?.OPERATION_FAILED || '操作失败，请重试',
            'error'
        );
    }
}

/**
 * 添加到收藏
 */
async function addToCollection(bookTitle) {
    try {
        const data = await NovelSystemUtils.fetchApi(
            NovelSystemConfig?.API?.COLLECT_BOOK || '/api/collect-book/',
            {
                method: 'POST',
                body: JSON.stringify({ book_title: bookTitle }),
            }
        );
        
        if (data.success) {
            NovelSystem.showMessage(
                data.message || NovelSystemConfig?.MESSAGES?.SUCCESS?.COLLECTED || '收藏成功',
                'success'
            );
            updateCollectionButton(bookTitle, true);
        } else {
            NovelSystem.showMessage(
                data.message || NovelSystemConfig?.MESSAGES?.ERROR?.OPERATION_FAILED || '操作失败',
                'error'
            );
        }
    } catch (error) {
        console.error('Error adding to collection:', error);
        NovelSystem.showMessage(
            NovelSystemConfig?.MESSAGES?.ERROR?.OPERATION_FAILED || '操作失败，请重试',
            'error'
        );
    }
}

/**
 * 从收藏中移除
 */
async function removeFromCollection(bookTitle) {
    try {
        const data = await NovelSystemUtils.fetchApi(
            NovelSystemConfig?.API?.REMOVE_FROM_COLLECTION || '/api/remove-from-collection/',
            {
                method: 'POST',
                body: JSON.stringify({ book_title: bookTitle }),
            }
        );
        
        if (data.success) {
            NovelSystem.showMessage(data.message || '已取消收藏', 'success');
            updateCollectionButton(bookTitle, false);
        } else {
            NovelSystem.showMessage(
                data.message || NovelSystemConfig?.MESSAGES?.ERROR?.OPERATION_FAILED || '操作失败',
                'error'
            );
        }
    } catch (error) {
        console.error('Error removing from collection:', error);
        NovelSystem.showMessage(
            NovelSystemConfig?.MESSAGES?.ERROR?.OPERATION_FAILED || '操作失败，请重试',
            'error'
        );
    }
}

/**
 * 切换书架状态
 */
async function toggleBookshelf(bookTitle) {
    if (!NovelSystemUtils.isUserLoggedIn()) {
        NovelSystem.showMessage(
            NovelSystemConfig?.MESSAGES?.ERROR?.NOT_LOGGED_IN || '请先登录',
            'warning'
        );
        return;
    }
    
    try {
        const isInBookshelf = await isBookInBookshelf(bookTitle);
        
        if (isInBookshelf) {
            await removeFromBookshelf(bookTitle);
        } else {
            await addToBookshelf(bookTitle);
        }
    } catch (error) {
        console.error('Error toggling bookshelf:', error);
        NovelSystem.showMessage(
            NovelSystemConfig?.MESSAGES?.ERROR?.OPERATION_FAILED || '操作失败，请重试',
            'error'
        );
    }
}

/**
 * 添加到书架
 */
async function addToBookshelf(bookTitle) {
    try {
        const data = await NovelSystemUtils.fetchApi(
            NovelSystemConfig?.API?.ADD_TO_BOOKSHELF || '/api/add-to-bookshelf/',
            {
                method: 'POST',
                body: JSON.stringify({ book_title: bookTitle }),
            }
        );
        
        if (data.success) {
            NovelSystem.showMessage(
                data.message || NovelSystemConfig?.MESSAGES?.SUCCESS?.ADDED_TO_BOOKSHELF || '已加入书架',
                'success'
            );
            updateBookshelfButton(bookTitle, true);
        } else {
            NovelSystem.showMessage(
                data.message || NovelSystemConfig?.MESSAGES?.ERROR?.OPERATION_FAILED || '操作失败',
                'error'
            );
        }
    } catch (error) {
        console.error('Error adding to bookshelf:', error);
        NovelSystem.showMessage(
            NovelSystemConfig?.MESSAGES?.ERROR?.OPERATION_FAILED || '操作失败，请重试',
            'error'
        );
    }
}

/**
 * 从书架中移除
 */
async function removeFromBookshelf(bookTitle) {
    try {
        const data = await NovelSystemUtils.fetchApi(
            NovelSystemConfig?.API?.REMOVE_FROM_BOOKSHELF || '/api/remove-from-bookshelf/',
            {
                method: 'POST',
                body: JSON.stringify({ book_title: bookTitle }),
            }
        );
        
        if (data.success) {
            NovelSystem.showMessage(data.message || '已从书架移除', 'success');
            updateBookshelfButton(bookTitle, false);
        } else {
            NovelSystem.showMessage(
                data.message || NovelSystemConfig?.MESSAGES?.ERROR?.OPERATION_FAILED || '操作失败',
                'error'
            );
        }
    } catch (error) {
        console.error('Error removing from bookshelf:', error);
        NovelSystem.showMessage(
            NovelSystemConfig?.MESSAGES?.ERROR?.OPERATION_FAILED || '操作失败，请重试',
            'error'
        );
    }
}

/**
 * 添加到购物车
 */
async function addToCart(bookTitle, price, chapterNumber = null) {
    if (!NovelSystemUtils.isUserLoggedIn()) {
        NovelSystem.showMessage(
            NovelSystemConfig?.MESSAGES?.ERROR?.NOT_LOGGED_IN || '请先登录',
            'warning'
        );
        return;
    }
    
    // 检查是否已在购物车中
    const existingItem = AppState.cartItems.find(item => 
        item.bookTitle === bookTitle && 
        (!chapterNumber || item.chapterNumber === chapterNumber)
    );
    
    if (existingItem) {
        NovelSystem.showMessage(
            NovelSystemConfig?.MESSAGES?.WARNING?.ALREADY_IN_CART || '该商品已在购物车中',
            'warning'
        );
        return;
    }
    
    try {
        // 添加到本地状态
        AppState.cartItems.push({
            bookTitle: bookTitle,
            price: price,
            chapterNumber: chapterNumber,
            quantity: 1,
            addedAt: new Date().toISOString()
        });
        
        // 保存到localStorage
        NovelSystemUtils.setLocalStorage(
            NovelSystemConfig?.STORAGE?.CART_ITEMS || 'cartItems',
            AppState.cartItems
        );
        
        // 更新显示
        updateCartDisplay();
        
        // 显示成功消息
        NovelSystem.showMessage(
            NovelSystemConfig?.MESSAGES?.SUCCESS?.ADDED_TO_CART || '已添加到购物车',
            'success'
        );
        
        // 调用服务器API
        const data = await NovelSystemUtils.fetchApi(
            NovelSystemConfig?.API?.CART_ADD || '/api/cart/add/',
            {
                method: 'POST',
                body: JSON.stringify({
                    book_title: bookTitle,
                    price: price,
                    chapter_number: chapterNumber
                }),
            }
        );
        
        if (!data.success) {
            NovelSystem.showMessage(
                data.message || NovelSystemConfig?.MESSAGES?.ERROR?.OPERATION_FAILED || '操作失败',
                'error'
            );
        }
        
        // 更新购物车计数
        if (typeof window.updateCartCount === 'function') {
            window.updateCartCount();
        }
    } catch (error) {
        console.error('Error adding to cart:', error);
        NovelSystem.showMessage(
            NovelSystemConfig?.MESSAGES?.ERROR?.OPERATION_FAILED || '操作失败，请重试',
            'error'
        );
    }
}

/**
 * 更新收藏按钮状态
 */
function updateCollectionButton(bookTitle, isCollected) {
    const button = document.querySelector(`[data-book-title="${bookTitle}"].collect-btn`);
    if (button) {
        const icon = button.querySelector('i');
        const text = button.querySelector('span');
        
        if (isCollected) {
            icon.className = 'fas fa-heart';
            button.classList.add('btn-danger');
            button.classList.remove('btn-outline-danger');
            if (text) text.textContent = '已收藏';
        } else {
            icon.className = 'far fa-heart';
            button.classList.add('btn-outline-danger');
            button.classList.remove('btn-danger');
            if (text) text.textContent = '收藏';
        }
    }
}

/**
 * 更新书架按钮状态
 */
function updateBookshelfButton(bookTitle, isInBookshelf) {
    const button = document.querySelector(`[data-book-title="${bookTitle}"].bookshelf-btn`);
    if (button) {
        const icon = button.querySelector('i');
        const text = button.querySelector('span');
        
        if (isInBookshelf) {
            icon.className = 'fas fa-bookmark';
            button.classList.add('btn-success');
            button.classList.remove('btn-outline-success');
            if (text) text.textContent = '已收藏';
        } else {
            icon.className = 'far fa-bookmark';
            button.classList.add('btn-outline-success');
            button.classList.remove('btn-success');
            if (text) text.textContent = '加入书架';
        }
    }
}

/**
 * 更新购物车显示
 */
function updateCartDisplay() {
    const cartRedDot = document.querySelector('#cart-red-dot');
    if (cartRedDot) {
        cartRedDot.style.display = AppState.cartItems.length > 0 ? 'block' : 'none';
    }
}

/**
 * 检查书籍是否已收藏
 * @param {string} bookTitle - 书籍标题
 * @returns {Promise<boolean>} 是否已收藏
 */
async function isBookCollected(bookTitle) {
    // 首先检查按钮状态（快速检查）
    const button = document.querySelector(`[data-book-title="${bookTitle}"].collect-btn`);
    if (button && button.classList.contains('btn-danger')) {
        return true;
    }
    
    // 可以在这里添加API调用来验证服务器状态
    // 暂时返回按钮状态
    return false;
}

/**
 * 检查书籍是否在书架中
 * @param {string} bookTitle - 书籍标题
 * @returns {Promise<boolean>} 是否在书架中
 */
async function isBookInBookshelf(bookTitle) {
    // 首先检查按钮状态（快速检查）
    const button = document.querySelector(`[data-book-title="${bookTitle}"].bookshelf-btn`);
    if (button && button.classList.contains('btn-success')) {
        return true;
    }
    
    // 可以在这里添加API调用来验证服务器状态
    // 暂时返回按钮状态
    return false;
}

// showMessage、showLoading、hideLoading 已在 common.js 中实现，这里不再重复定义

/**
 * 添加页面动画
 */
function addPageAnimations() {
    // 为卡片添加淡入动画
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });
}

// 工具函数已在 utils.js 和 common.js 中实现
// 这里保持向后兼容性，将函数暴露到全局
if (typeof window.NovelSystem === 'undefined') {
    window.NovelSystem = {};
}

// 添加main.js特有的功能
window.NovelSystem = {
    ...window.NovelSystem,
    addToCart,
    toggleCollection,
    toggleBookshelf,
};

