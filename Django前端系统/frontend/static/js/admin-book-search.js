/**
 * 管理员书籍搜索组件
 */
class AdminBookSearch {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            apiUrl: '/api/admin/books/search/',
            pageSize: 20,
            debounceDelay: 300,
            ...options
        };
        
        // 搜索状态
        this.currentQuery = '';
        this.currentFilters = {};
        this.currentPage = 1;
        this.isLoading = false;
        this.debounceTimer = null;
        
        // DOM元素
        this.searchInput = null;
        this.categoryFilter = null;
        this.statusFilter = null;
        this.authorFilter = null;
        this.sortSelect = null;
        this.resultsContainer = null;
        this.paginationContainer = null;
        this.loadingIndicator = null;
        
        this.init();
    }
    
    init() {
        this.createSearchInterface();
        this.bindEvents();
        this.loadInitialData();
    }
    
    createSearchInterface() {
        const searchHTML = `
            <div class="admin-book-search">
                <!-- 搜索栏 -->
                <div class="search-bar bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
                    <div class="flex flex-col lg:flex-row gap-4">
                        <!-- 搜索输入框 -->
                        <div class="flex-1">
                            <div class="relative">
                                <input type="text" 
                                       id="bookSearchInput" 
                                       class="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                       placeholder="搜索书名、作者或简介...">
                                <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                    <i class="fas fa-search text-gray-400"></i>
                                </div>
                                <div id="searchSpinner" class="absolute inset-y-0 right-0 pr-3 flex items-center hidden">
                                    <i class="fas fa-spinner fa-spin text-gray-400"></i>
                                </div>
                            </div>
                        </div>
                        
                        <!-- 筛选器 -->
                        <div class="flex flex-col sm:flex-row gap-2">
                            <select id="categoryFilter" class="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                                <option value="">所有分类</option>
                            </select>
                            
                            <select id="statusFilter" class="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                                <option value="">所有状态</option>
                                <option value="连载中">连载中</option>
                                <option value="完结">完结</option>
                                <option value="暂停">暂停</option>
                            </select>
                            
                            <select id="sortSelect" class="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                                <option value="create_time">创建时间</option>
                                <option value="update_time">更新时间</option>
                                <option value="popularity">人气排序</option>
                                <option value="rating">评分排序</option>
                            </select>
                        </div>
                        
                        <!-- 清除按钮 -->
                        <button id="clearFilters" class="px-4 py-2 text-gray-600 hover:text-gray-800 border border-gray-300 rounded-md hover:bg-gray-50">
                            <i class="fas fa-times mr-1"></i>清除
                        </button>
                    </div>
                    
                    <!-- 搜索建议 -->
                    <div id="searchSuggestions" class="mt-2 hidden">
                        <div class="text-sm text-gray-600 mb-2">搜索建议：</div>
                        <div class="flex flex-wrap gap-2" id="suggestionTags"></div>
                    </div>
                </div>
                
                <!-- 搜索结果统计 -->
                <div class="search-stats bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-4">
                    <div class="flex justify-between items-center">
                        <div id="searchResultStats" class="text-sm text-gray-600">
                            正在搜索...
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="text-sm text-gray-500">每页显示：</span>
                            <select id="pageSizeSelect" class="text-sm border border-gray-300 rounded px-2 py-1">
                                <option value="10">10</option>
                                <option value="20" selected>20</option>
                                <option value="50">50</option>
                                <option value="100">100</option>
                            </select>
                        </div>
                    </div>
                </div>
                
                <!-- 搜索结果 -->
                <div id="searchResults" class="search-results">
                    <!-- 结果将在这里显示 -->
                </div>
                
                <!-- 分页 -->
                <div id="searchPagination" class="pagination-container mt-6">
                    <!-- 分页将在这里显示 -->
                </div>
            </div>
        `;
        
        this.container.innerHTML = searchHTML;
        
        // 获取DOM元素引用
        this.searchInput = document.getElementById('bookSearchInput');
        this.categoryFilter = document.getElementById('categoryFilter');
        this.statusFilter = document.getElementById('statusFilter');
        this.sortSelect = document.getElementById('sortSelect');
        this.resultsContainer = document.getElementById('searchResults');
        this.paginationContainer = document.getElementById('searchPagination');
        this.loadingIndicator = document.getElementById('searchSpinner');
        this.clearFiltersBtn = document.getElementById('clearFilters');
        this.pageSizeSelect = document.getElementById('pageSizeSelect');
        this.searchResultStats = document.getElementById('searchResultStats');
    }
    
    bindEvents() {
        // 搜索输入框事件
        this.searchInput.addEventListener('input', (e) => {
            this.handleSearchInput(e.target.value);
        });
        
        // 筛选器事件
        this.categoryFilter.addEventListener('change', () => {
            this.handleFilterChange();
        });
        
        this.statusFilter.addEventListener('change', () => {
            this.handleFilterChange();
        });
        
        this.sortSelect.addEventListener('change', () => {
            this.handleFilterChange();
        });
        
        // 清除筛选器
        this.clearFiltersBtn.addEventListener('click', () => {
            this.clearFilters();
        });
        
        // 每页显示数量变化
        this.pageSizeSelect.addEventListener('change', () => {
            this.options.pageSize = parseInt(this.pageSizeSelect.value);
            this.currentPage = 1;
            this.performSearch();
        });
        
        // 键盘快捷键
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'f') {
                e.preventDefault();
                this.searchInput.focus();
            }
        });
    }
    
    handleSearchInput(query) {
        this.currentQuery = query.trim();
        
        // 清除之前的定时器
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }
        
        // 设置防抖
        this.debounceTimer = setTimeout(() => {
            this.currentPage = 1;
            this.performSearch();
        }, this.options.debounceDelay);
        
        // 显示加载指示器
        if (this.currentQuery) {
            this.showLoading();
        }
    }
    
    handleFilterChange() {
        this.currentFilters = {
            category: this.categoryFilter.value,
            status: this.statusFilter.value,
            sort_by: this.sortSelect.value
        };
        
        this.currentPage = 1;
        this.performSearch();
    }
    
    clearFilters() {
        this.searchInput.value = '';
        this.categoryFilter.value = '';
        this.statusFilter.value = '';
        this.sortSelect.value = 'create_time';
        
        this.currentQuery = '';
        this.currentFilters = {};
        this.currentPage = 1;
        
        this.performSearch();
    }
    
    async loadInitialData() {
        try {
            // 加载分类列表
            await this.loadCategories();
            
            // 执行初始搜索
            this.performSearch();
        } catch (error) {
            console.error('加载初始数据失败:', error);
            this.showError('加载数据失败，请刷新页面重试');
        }
    }
    
    async loadCategories() {
        try {
            const response = await fetch('/api/admin/books/categories/', {
                method: 'GET',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            const data = await response.json();
            
            if (data.success && data.data) {
                // 清空现有选项（保留"所有分类"）
                this.categoryFilter.innerHTML = '<option value="">所有分类</option>';
                
                // 添加分类选项
                data.data.forEach(category => {
                    const option = document.createElement('option');
                    option.value = category;
                    option.textContent = category;
                    this.categoryFilter.appendChild(option);
                });
            }
        } catch (error) {
            console.error('加载分类失败:', error);
        }
    }
    
    async performSearch() {
        if (this.isLoading) return;
        
        this.isLoading = true;
        this.showLoading();
        
        try {
            const searchData = {
                query: this.currentQuery,
                filters: this.currentFilters,
                pagination: {
                    page: this.currentPage,
                    size: this.options.pageSize
                }
            };
            
            const response = await fetch(this.options.apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(searchData)
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.displayResults(data.data);
                this.updateStats(data.data.pagination);
            } else {
                this.showError(data.message || '搜索失败');
            }
        } catch (error) {
            console.error('搜索请求失败:', error);
            this.showError('搜索请求失败，请稍后重试');
        } finally {
            this.isLoading = false;
            this.hideLoading();
        }
    }
    
    displayResults(data) {
        const { books, pagination } = data;
        
        if (!books || books.length === 0) {
            this.showEmptyState();
            return;
        }
        
        let resultsHTML = '<div class="book-results-grid">';
        
        books.forEach(book => {
            resultsHTML += this.createBookCard(book);
        });
        
        resultsHTML += '</div>';
        
        this.resultsContainer.innerHTML = resultsHTML;
        this.createPagination(pagination);
        
        // 绑定结果中的事件
        this.bindResultEvents();
    }
    
    createBookCard(book) {
        const statusClass = book.status === '连载中' ? 'bg-green-100 text-green-800' : 
                           book.status === '完结' ? 'bg-blue-100 text-blue-800' : 
                           'bg-yellow-100 text-yellow-800';
        
        const coverImage = book.cover_url ? 
            `<img src="${book.cover_url}" alt="${book.title}" class="w-16 h-20 object-cover rounded">` :
            `<div class="w-16 h-20 bg-gray-200 rounded flex items-center justify-center">
                <i class="fas fa-book text-gray-400"></i>
            </div>`;
        
        return `
            <div class="book-card bg-white rounded-lg shadow-sm border border-gray-200 p-4 hover:shadow-md transition-shadow">
                <div class="flex items-start space-x-4">
                    <!-- 封面 -->
                    <div class="flex-shrink-0">
                        ${coverImage}
                    </div>
                    
                    <!-- 书籍信息 -->
                    <div class="flex-1 min-w-0">
                        <div class="flex items-start justify-between">
                            <div class="flex-1">
                                <h3 class="text-lg font-medium text-gray-900 truncate">${book.title}</h3>
                                <p class="text-sm text-gray-600 mt-1">作者：${book.author}</p>
                                <p class="text-sm text-gray-600">分类：${book.category}</p>
                                
                                <div class="flex items-center space-x-4 mt-2">
                                    <span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full ${statusClass}">
                                        ${book.status}
                                    </span>
                                    <span class="text-xs text-gray-500">章节: ${book.chapter_count}</span>
                                    <span class="text-xs text-gray-500">收藏: ${book.collection_count}</span>
                                    <span class="text-xs text-gray-500">评分: ${book.rating.toFixed(1)}</span>
                                </div>
                                
                                ${book.description ? `<p class="text-sm text-gray-600 mt-2 line-clamp-2">${book.description}</p>` : ''}
                            </div>
                            
                            <!-- 操作按钮 -->
                            <div class="flex flex-col space-y-2 ml-4">
                                <button class="edit-book-btn px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700" 
                                        data-book-id="${book.book_id}">
                                    <i class="fas fa-edit mr-1"></i>编辑
                                </button>
                                <button class="delete-book-btn px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700" 
                                        data-book-id="${book.book_id}" data-book-title="${book.title}">
                                    <i class="fas fa-trash mr-1"></i>删除
                                </button>
                                <button class="view-stats-btn px-3 py-1 text-sm bg-gray-600 text-white rounded hover:bg-gray-700" 
                                        data-book-id="${book.book_id}">
                                    <i class="fas fa-chart-bar mr-1"></i>统计
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    createPagination(pagination) {
        if (pagination.page_count <= 1) {
            this.paginationContainer.innerHTML = '';
            return;
        }
        
        let paginationHTML = '<div class="flex items-center justify-between">';
        
        // 页面信息
        paginationHTML += `
            <div class="text-sm text-gray-700">
                显示第 ${((pagination.current_page - 1) * this.options.pageSize) + 1} - 
                ${Math.min(pagination.current_page * this.options.pageSize, pagination.total_count)} 条，
                共 ${pagination.total_count} 条记录
            </div>
        `;
        
        // 分页按钮
        paginationHTML += '<div class="flex space-x-1">';
        
        // 上一页
        if (pagination.has_previous) {
            paginationHTML += `
                <button class="pagination-btn px-3 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50" 
                        data-page="${pagination.current_page - 1}">
                    <i class="fas fa-chevron-left"></i>
                </button>
            `;
        }
        
        // 页码按钮
        const startPage = Math.max(1, pagination.current_page - 2);
        const endPage = Math.min(pagination.page_count, pagination.current_page + 2);
        
        if (startPage > 1) {
            paginationHTML += `
                <button class="pagination-btn px-3 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50" data-page="1">1</button>
            `;
            if (startPage > 2) {
                paginationHTML += '<span class="px-3 py-2 text-sm text-gray-500">...</span>';
            }
        }
        
        for (let i = startPage; i <= endPage; i++) {
            const isActive = i === pagination.current_page;
            paginationHTML += `
                <button class="pagination-btn px-3 py-2 text-sm border rounded-md ${
                    isActive ? 'bg-blue-600 text-white border-blue-600' : 'border-gray-300 hover:bg-gray-50'
                }" data-page="${i}">${i}</button>
            `;
        }
        
        if (endPage < pagination.page_count) {
            if (endPage < pagination.page_count - 1) {
                paginationHTML += '<span class="px-3 py-2 text-sm text-gray-500">...</span>';
            }
            paginationHTML += `
                <button class="pagination-btn px-3 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50" 
                        data-page="${pagination.page_count}">${pagination.page_count}</button>
            `;
        }
        
        // 下一页
        if (pagination.has_next) {
            paginationHTML += `
                <button class="pagination-btn px-3 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50" 
                        data-page="${pagination.current_page + 1}">
                    <i class="fas fa-chevron-right"></i>
                </button>
            `;
        }
        
        paginationHTML += '</div></div>';
        
        this.paginationContainer.innerHTML = paginationHTML;
        
        // 绑定分页事件
        this.paginationContainer.querySelectorAll('.pagination-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const page = parseInt(e.target.dataset.page);
                if (page && page !== this.currentPage) {
                    this.currentPage = page;
                    this.performSearch();
                }
            });
        });
    }
    
    bindResultEvents() {
        // 编辑按钮
        this.resultsContainer.querySelectorAll('.edit-book-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const bookId = e.target.dataset.bookId;
                this.handleEditBook(bookId);
            });
        });
        
        // 删除按钮
        this.resultsContainer.querySelectorAll('.delete-book-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const bookId = e.target.dataset.bookId;
                const bookTitle = e.target.dataset.bookTitle;
                this.handleDeleteBook(bookId, bookTitle);
            });
        });
        
        // 统计按钮
        this.resultsContainer.querySelectorAll('.view-stats-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const bookId = e.target.dataset.bookId;
                this.handleViewStats(bookId);
            });
        });
    }
    
    handleEditBook(bookId) {
        // 触发自定义事件，让外部处理
        this.container.dispatchEvent(new CustomEvent('editBook', {
            detail: { bookId }
        }));
    }
    
    handleDeleteBook(bookId, bookTitle) {
        // 触发自定义事件，让外部处理
        this.container.dispatchEvent(new CustomEvent('deleteBook', {
            detail: { bookId, bookTitle }
        }));
    }
    
    handleViewStats(bookId) {
        // 触发自定义事件，让外部处理
        this.container.dispatchEvent(new CustomEvent('viewStats', {
            detail: { bookId }
        }));
    }
    
    updateStats(pagination) {
        const statsText = `找到 ${pagination.total_count} 本书籍，当前第 ${pagination.current_page} / ${pagination.page_count} 页`;
        this.searchResultStats.textContent = statsText;
    }
    
    showEmptyState() {
        this.resultsContainer.innerHTML = `
            <div class="empty-state text-center py-12">
                <div class="text-gray-400 mb-4">
                    <i class="fas fa-search text-6xl"></i>
                </div>
                <h3 class="text-lg font-medium text-gray-900 mb-2">没有找到匹配的书籍</h3>
                <p class="text-gray-600 mb-4">尝试调整搜索条件或清除筛选器</p>
                <button class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700" 
                        onclick="document.getElementById('clearFilters').click()">
                    清除筛选器
                </button>
            </div>
        `;
        this.paginationContainer.innerHTML = '';
        this.searchResultStats.textContent = '没有找到匹配的书籍';
    }
    
    showLoading() {
        if (this.loadingIndicator) {
            this.loadingIndicator.classList.remove('hidden');
        }
    }
    
    hideLoading() {
        if (this.loadingIndicator) {
            this.loadingIndicator.classList.add('hidden');
        }
    }
    
    showError(message) {
        this.resultsContainer.innerHTML = `
            <div class="error-state text-center py-12">
                <div class="text-red-400 mb-4">
                    <i class="fas fa-exclamation-triangle text-6xl"></i>
                </div>
                <h3 class="text-lg font-medium text-gray-900 mb-2">搜索出错</h3>
                <p class="text-gray-600 mb-4">${message}</p>
                <button class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700" 
                        onclick="location.reload()">
                    刷新页面
                </button>
            </div>
        `;
        this.paginationContainer.innerHTML = '';
        this.searchResultStats.textContent = '搜索出错';
    }
    
    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        if (token) {
            return token.value;
        }
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        return '';
    }
    
    // 公共方法
    refresh() {
        this.performSearch();
    }
    
    setQuery(query) {
        this.searchInput.value = query;
        this.currentQuery = query;
        this.currentPage = 1;
        this.performSearch();
    }
    
    setFilters(filters) {
        if (filters.category !== undefined) {
            this.categoryFilter.value = filters.category;
        }
        if (filters.status !== undefined) {
            this.statusFilter.value = filters.status;
        }
        if (filters.sort_by !== undefined) {
            this.sortSelect.value = filters.sort_by;
        }
        
        this.handleFilterChange();
    }
}

// 导出类
window.AdminBookSearch = AdminBookSearch;