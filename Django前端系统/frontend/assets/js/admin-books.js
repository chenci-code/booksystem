// 书籍管理JavaScript

// 全局变量
let currentBookId = null;
let currentView = 'grid';

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeBookManagement();
});

// 初始化书籍管理
function initializeBookManagement() {
    // 设置默认视图
    switchView('grid');
    
    // 绑定事件监听器
    bindEventListeners();
}

// 绑定事件监听器
function bindEventListeners() {
    // 模态框外部点击关闭
    document.getElementById('bookModal').addEventListener('click', function(e) {
        if (e.target === this) {
            closeBookModal();
        }
    });
    
    // ESC键关闭模态框
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeBookModal();
        }
    });
}

// 切换视图
function switchView(view) {
    currentView = view;
    
    const gridView = document.getElementById('gridView');
    const listView = document.getElementById('listView');
    const gridBtn = document.querySelector('[data-view="grid"]');
    const listBtn = document.querySelector('[data-view="list"]');
    
    if (view === 'grid') {
        gridView.style.display = 'grid';
        listView.style.display = 'none';
        gridBtn.classList.add('active');
        listBtn.classList.remove('active');
    } else {
        gridView.style.display = 'none';
        listView.style.display = 'block';
        gridBtn.classList.remove('active');
        listBtn.classList.add('active');
    }
}

// 显示添加书籍模态框
function showAddBookModal() {
    currentBookId = null;
    document.getElementById('modalTitle').textContent = '添加书籍';
    document.getElementById('bookForm').reset();
    document.getElementById('bookModal').classList.add('show');
    document.getElementById('bookModal').style.display = 'flex';
}

// 显示编辑书籍模态框
function editBook(bookId) {
    currentBookId = bookId;
    document.getElementById('modalTitle').textContent = '编辑书籍';
    
    // 获取书籍信息
    fetch(`/api/admin/get-book/${bookId}/`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const book = data.book;
                document.getElementById('bookTitle').value = book.title || '';
                document.getElementById('bookAuthor').value = book.author || '';
                document.getElementById('bookCategory').value = book.category || '';
                document.getElementById('bookStatus').value = book.status || '';
                document.getElementById('bookWordCount').value = book.word_count || '';
                document.getElementById('bookCoverUrl').value = book.cover_url || '';
                document.getElementById('bookDescription').value = book.description || '';
                
                document.getElementById('bookModal').classList.add('show');
                document.getElementById('bookModal').style.display = 'flex';
            } else {
                showMessage('获取书籍信息失败: ' + data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showMessage('获取书籍信息失败', 'error');
        });
}

// 关闭书籍模态框
function closeBookModal() {
    document.getElementById('bookModal').classList.remove('show');
    document.getElementById('bookModal').style.display = 'none';
    currentBookId = null;
}

// 保存书籍
function saveBook() {
    const form = document.getElementById('bookForm');
    const formData = new FormData(form);
    
    // 验证必填字段
    const title = formData.get('title');
    const author = formData.get('author');
    const category = formData.get('category');
    
    if (!title || !author || !category) {
        showMessage('请填写所有必填字段', 'error');
        return;
    }
    
    // 构建请求数据
    const bookData = {
        title: title,
        author: author,
        category: category,
        status: formData.get('status') || '连载中',
        word_count: formData.get('word_count') || '',
        cover_url: formData.get('cover_url') || '',
        description: formData.get('description') || ''
    };
    
    if (currentBookId) {
        bookData.book_id = currentBookId;
    }
    
    // 发送请求
    const url = currentBookId ? '/api/admin/update-book/' : '/api/admin/add-book/';
    
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify(bookData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage(data.message, 'success');
            closeBookModal();
            // 刷新页面或更新列表
            setTimeout(() => {
                location.reload();
            }, 1000);
        } else {
            showMessage(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage('保存失败，请重试', 'error');
    });
}

// 查看书籍详情
function viewBook(bookId) {
    window.open(`/book/${bookId}/`, '_blank');
}

// 删除书籍
function deleteBook(bookId) {
    if (!confirm('确定要删除这本书籍吗？此操作不可恢复！')) {
        return;
    }
    
    fetch('/api/admin/delete-book/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            book_id: bookId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage(data.message, 'success');
            // 移除对应的书籍卡片或行
            const bookCard = document.querySelector(`[data-book-id="${bookId}"]`);
            if (bookCard) {
                bookCard.remove();
            }
            // 或者刷新页面
            setTimeout(() => {
                location.reload();
            }, 1000);
        } else {
            showMessage(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage('删除失败，请重试', 'error');
    });
}

// 导出书籍数据
function exportBooks() {
    const currentUrl = new URL(window.location);
    const params = new URLSearchParams(currentUrl.search);
    params.set('export', 'true');
    
    const exportUrl = '/api/admin/export-books/?' + params.toString();
    
    // 创建下载链接
    const link = document.createElement('a');
    link.href = exportUrl;
    link.download = `books_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    showMessage('导出任务已开始', 'success');
}

// 获取CSRF令牌
function getCsrfToken() {
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
function showMessage(message, type) {
    const alertClass = type === 'success' ? 'bg-green-100 border-green-400 text-green-700' : 'bg-red-100 border-red-400 text-red-700';
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

// 搜索功能增强
function enhanceSearch() {
    const searchInput = document.querySelector('input[name="search"]');
    if (searchInput) {
        let searchTimeout;
        
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                if (this.value.length >= 2 || this.value.length === 0) {
                    // 可以在这里添加实时搜索功能
                }
            }, 300);
        });
    }
}

// 批量操作功能
function initBatchOperations() {
    const selectAllCheckbox = document.getElementById('selectAll');
    const bookCheckboxes = document.querySelectorAll('.book-checkbox');
    
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            bookCheckboxes.forEach(checkbox => {
                checkbox.checked = this.checked;
            });
            updateBatchButtons();
        });
    }
    
    bookCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updateBatchButtons);
    });
}

// 更新批量操作按钮状态
function updateBatchButtons() {
    const checkedBoxes = document.querySelectorAll('.book-checkbox:checked');
    const batchButtons = document.querySelectorAll('.batch-btn');
    
    batchButtons.forEach(btn => {
        btn.disabled = checkedBoxes.length === 0;
    });
}

// 批量删除
function batchDelete() {
    const checkedBoxes = document.querySelectorAll('.book-checkbox:checked');
    const bookIds = Array.from(checkedBoxes).map(cb => cb.value);
    
    if (bookIds.length === 0) {
        showMessage('请选择要删除的书籍', 'error');
        return;
    }
    
    if (!confirm(`确定要删除选中的 ${bookIds.length} 本书籍吗？此操作不可恢复！`)) {
        return;
    }
    
    fetch('/api/admin/batch-delete-books/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            book_ids: bookIds
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage(`成功删除 ${data.deleted_count} 本书籍`, 'success');
            setTimeout(() => {
                location.reload();
            }, 1000);
        } else {
            showMessage(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage('批量删除失败，请重试', 'error');
    });
}

// 图片预览功能
function previewCover() {
    const coverUrlInput = document.getElementById('bookCoverUrl');
    const coverUrl = coverUrlInput.value.trim();
    
    if (coverUrl) {
        // 创建预览窗口
        const previewWindow = window.open('', '_blank', 'width=400,height=600');
        previewWindow.document.write(`
            <html>
                <head><title>封面预览</title></head>
                <body style="margin:0;padding:20px;text-align:center;">
                    <h3>封面预览</h3>
                    <img src="${coverUrl}" style="max-width:100%;max-height:80vh;" 
                         onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjNmNGY2Ii8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzZiNzI4MCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPuaXoOazleWKoOi9veWbvueJhzwvdGV4dD48L3N2Zz4='; this.alt='图片加载失败';">
                    <br><br>
                    <button onclick="window.close()">关闭</button>
                </body>
            </html>
        `);
    } else {
        showMessage('请先输入封面URL', 'error');
    }
}

// 添加封面预览按钮
document.addEventListener('DOMContentLoaded', function() {
    const coverUrlInput = document.getElementById('bookCoverUrl');
    if (coverUrlInput) {
        const previewBtn = document.createElement('button');
        previewBtn.type = 'button';
        previewBtn.className = 'btn btn-secondary';
        previewBtn.innerHTML = '<i class="fas fa-eye mr-1"></i>预览';
        previewBtn.onclick = previewCover;
        
        coverUrlInput.parentNode.appendChild(previewBtn);
    }
});