// 用户管理JavaScript

// 全局变量
let currentUserId = null;
let currentView = 'list';

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeUserManagement();
});

// 初始化用户管理
function initializeUserManagement() {
    // 设置默认视图
    switchView('list');
    
    // 绑定事件监听器
    bindEventListeners();
    
    // 初始化批量操作
    initBatchOperations();
}

// 绑定事件监听器
function bindEventListeners() {
    // 模态框外部点击关闭
    document.getElementById('userModal').addEventListener('click', function(e) {
        if (e.target === this) {
            closeUserModal();
        }
    });
    
    document.getElementById('userDetailModal').addEventListener('click', function(e) {
        if (e.target === this) {
            closeUserDetailModal();
        }
    });
    
    // ESC键关闭模态框
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeUserModal();
            closeUserDetailModal();
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
        if (gridView) gridView.style.display = 'grid';
        if (listView) listView.style.display = 'none';
        if (gridBtn) gridBtn.classList.add('active');
        if (listBtn) listBtn.classList.remove('active');
    } else {
        if (gridView) gridView.style.display = 'none';
        if (listView) listView.style.display = 'block';
        if (gridBtn) gridBtn.classList.remove('active');
        if (listBtn) listBtn.classList.add('active');
    }
}

// 显示添加用户模态框
function showAddUserModal() {
    currentUserId = null;
    document.getElementById('modalTitle').textContent = '添加用户';
    document.getElementById('userForm').reset();
    document.getElementById('userModal').classList.add('show');
    document.getElementById('userModal').style.display = 'flex';
}

// 显示编辑用户模态框
function editUser(userId) {
    currentUserId = userId;
    document.getElementById('modalTitle').textContent = '编辑用户';
    
    // 获取用户信息
    fetch(`/api/admin/get-user/${userId}/`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const user = data.user;
                document.getElementById('userName').value = user.name || '';
                document.getElementById('userUsername').value = user.username || '';
                document.getElementById('userPassword').value = ''; // 不显示原密码
                document.getElementById('userBalance').value = user.balance || 0;
                document.getElementById('userStatus').value = user.status || '正常';
                
                // 编辑时密码不是必填的
                document.getElementById('userPassword').required = false;
                
                document.getElementById('userModal').classList.add('show');
                document.getElementById('userModal').style.display = 'flex';
            } else {
                showMessage('获取用户信息失败: ' + data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showMessage('获取用户信息失败', 'error');
        });
}

// 关闭用户模态框
function closeUserModal() {
    document.getElementById('userModal').classList.remove('show');
    document.getElementById('userModal').style.display = 'none';
    currentUserId = null;
    // 重置密码必填状态
    document.getElementById('userPassword').required = true;
}

// 保存用户
function saveUser() {
    const form = document.getElementById('userForm');
    const formData = new FormData(form);
    
    // 验证必填字段
    const name = formData.get('name');
    const username = formData.get('username');
    const password = formData.get('password');
    
    if (!name || !username) {
        showMessage('请填写姓名和用户名', 'error');
        return;
    }
    
    if (!currentUserId && !password) {
        showMessage('新用户必须设置密码', 'error');
        return;
    }
    
    // 构建请求数据
    const userData = {
        name: name,
        username: username,
        balance: parseFloat(formData.get('balance')) || 0,
        status: formData.get('status') || '正常'
    };
    
    if (password) {
        userData.password = password;
    }
    
    if (currentUserId) {
        userData.user_id = currentUserId;
    }
    
    // 发送请求
    const url = currentUserId ? '/api/admin/update-user/' : '/api/admin/add-user/';
    
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify(userData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage(data.message, 'success');
            closeUserModal();
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

// 查看用户详情
function viewUser(userId) {
    fetch(`/api/admin/get-user-detail/${userId}/`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const user = data.user;
                const orders = data.orders || [];
                const reviews = data.reviews || [];
                const collections = data.collections || [];
                
                const detailHtml = `
                    <div class="user-detail-grid">
                        <div class="user-basic-info">
                            <h4>基本信息</h4>
                            <div class="info-grid">
                                <div class="info-item">
                                    <label>姓名:</label>
                                    <span>${user.name}</span>
                                </div>
                                <div class="info-item">
                                    <label>用户名:</label>
                                    <span>${user.username}</span>
                                </div>
                                <div class="info-item">
                                    <label>余额:</label>
                                    <span class="balance">¥${user.balance}</span>
                                </div>
                                <div class="info-item">
                                    <label>状态:</label>
                                    <span class="status-badge status-${user.status.replace(/\s+/g, '-').toLowerCase()}">${user.status}</span>
                                </div>
                                <div class="info-item">
                                    <label>注册时间:</label>
                                    <span>${new Date(user.register_time).toLocaleString()}</span>
                                </div>
                                <div class="info-item">
                                    <label>最后登录:</label>
                                    <span>${user.last_login_time ? new Date(user.last_login_time).toLocaleString() : '从未登录'}</span>
                                </div>
                            </div>
                        </div>
                        
                        <div class="user-stats">
                            <h4>统计信息</h4>
                            <div class="stats-grid">
                                <div class="stat-card">
                                    <div class="stat-number">${orders.length}</div>
                                    <div class="stat-label">订单数</div>
                                </div>
                                <div class="stat-card">
                                    <div class="stat-number">${reviews.length}</div>
                                    <div class="stat-label">评价数</div>
                                </div>
                                <div class="stat-card">
                                    <div class="stat-number">${collections.length}</div>
                                    <div class="stat-label">收藏数</div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="user-orders">
                            <h4>最近订单</h4>
                            <div class="orders-list">
                                ${orders.slice(0, 5).map(order => `
                                    <div class="order-item">
                                        <div class="order-info">
                                            <span class="order-number">${order.order_number}</span>
                                            <span class="order-amount">¥${order.order_amount}</span>
                                        </div>
                                        <div class="order-meta">
                                            <span class="order-status status-${order.order_status.replace(/\s+/g, '-').toLowerCase()}">${order.order_status}</span>
                                            <span class="order-time">${new Date(order.create_time).toLocaleDateString()}</span>
                                        </div>
                                    </div>
                                `).join('') || '<p class="no-data">暂无订单</p>'}
                            </div>
                        </div>
                        
                        <div class="user-collections">
                            <h4>收藏书籍</h4>
                            <div class="collections-list">
                                ${collections.slice(0, 10).map(book => `
                                    <div class="collection-item">
                                        <span class="book-title">${typeof book === 'string' ? book : book.book_title || book}</span>
                                        ${typeof book === 'object' && book.collect_time ? `<span class="collect-time">收藏于 ${new Date(book.collect_time).toLocaleDateString()}</span>` : ''}
                                    </div>
                                `).join('') || '<p class="no-data">暂无收藏</p>'}
                            </div>
                        </div>
                    </div>
                `;
                
                document.getElementById('userDetailContent').innerHTML = detailHtml;
                document.getElementById('userDetailModal').classList.add('show');
                document.getElementById('userDetailModal').style.display = 'flex';
            } else {
                showMessage('获取用户详情失败: ' + data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showMessage('获取用户详情失败', 'error');
        });
}

// 关闭用户详情模态框
function closeUserDetailModal() {
    document.getElementById('userDetailModal').classList.remove('show');
    document.getElementById('userDetailModal').style.display = 'none';
}

// 切换用户状态
function toggleUserStatus(userId, currentStatus) {
    const newStatus = currentStatus === '正常' ? '禁用' : '正常';
    const action = newStatus === '禁用' ? '禁用' : '启用';
    
    if (!confirm(`确定要${action}该用户吗？`)) {
        return;
    }
    
    fetch('/api/admin/toggle-user-status/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            user_id: userId,
            status: newStatus
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage(data.message, 'success');
            // 更新页面上的状态显示
            setTimeout(() => {
                location.reload();
            }, 1000);
        } else {
            showMessage(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage('操作失败，请重试', 'error');
    });
}

// 删除用户
function deleteUser(userId) {
    if (!confirm('确定要删除该用户吗？此操作不可恢复！')) {
        return;
    }
    
    fetch('/api/admin/delete-user/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            user_id: userId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage(data.message, 'success');
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

// 导出用户数据
function exportUsers() {
    const currentUrl = new URL(window.location);
    const params = new URLSearchParams(currentUrl.search);
    params.set('export', 'true');
    
    const exportUrl = '/api/admin/export-users/?' + params.toString();
    
    // 创建下载链接
    const link = document.createElement('a');
    link.href = exportUrl;
    link.download = `users_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    showMessage('导出任务已开始', 'success');
}

// 批量操作
function batchOperation() {
    const checkedBoxes = document.querySelectorAll('.user-checkbox:checked');
    const userIds = Array.from(checkedBoxes).map(cb => cb.value);
    
    if (userIds.length === 0) {
        showMessage('请选择要操作的用户', 'error');
        return;
    }
    
    // 显示批量操作菜单
    const menu = `
        <div class="batch-menu">
            <button onclick="batchToggleStatus('正常')">批量启用</button>
            <button onclick="batchToggleStatus('禁用')">批量禁用</button>
            <button onclick="batchDelete()" class="danger">批量删除</button>
        </div>
    `;
    
    // 这里可以实现一个下拉菜单或模态框
}

// 批量切换状态
function batchToggleStatus(status) {
    const checkedBoxes = document.querySelectorAll('.user-checkbox:checked');
    const userIds = Array.from(checkedBoxes).map(cb => cb.value);
    
    if (userIds.length === 0) {
        showMessage('请选择要操作的用户', 'error');
        return;
    }
    
    const action = status === '禁用' ? '禁用' : '启用';
    if (!confirm(`确定要${action}选中的 ${userIds.length} 个用户吗？`)) {
        return;
    }
    
    fetch('/api/admin/batch-toggle-user-status/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            user_ids: userIds,
            status: status
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage(`成功${action} ${data.updated_count} 个用户`, 'success');
            setTimeout(() => {
                location.reload();
            }, 1000);
        } else {
            showMessage(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage('批量操作失败，请重试', 'error');
    });
}

// 初始化批量操作
function initBatchOperations() {
    const selectAllCheckbox = document.getElementById('selectAll');
    const userCheckboxes = document.querySelectorAll('.user-checkbox');
    
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            userCheckboxes.forEach(checkbox => {
                checkbox.checked = this.checked;
            });
            updateBatchButtons();
        });
    }
    
    userCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updateBatchButtons);
    });
}

// 全选切换
function toggleSelectAll() {
    const selectAllCheckbox = document.getElementById('selectAll') || document.getElementById('selectAllTable');
    const userCheckboxes = document.querySelectorAll('.user-checkbox');
    
    if (selectAllCheckbox) {
        userCheckboxes.forEach(checkbox => {
            checkbox.checked = selectAllCheckbox.checked;
        });
        updateBatchButtons();
    }
}

// 更新批量操作按钮状态
function updateBatchButtons() {
    const checkedBoxes = document.querySelectorAll('.user-checkbox:checked');
    const batchButtons = document.querySelectorAll('.batch-btn');
    
    batchButtons.forEach(btn => {
        btn.disabled = checkedBoxes.length === 0;
    });
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

// 添加用户详情样式
const userDetailStyles = `
<style>
.user-detail-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 2rem;
}

.user-basic-info, .user-stats, .user-orders, .user-collections {
    background: #f9fafb;
    padding: 1.5rem;
    border-radius: 8px;
}

.user-basic-info h4, .user-stats h4, .user-orders h4, .user-collections h4 {
    margin: 0 0 1rem 0;
    color: #1f2937;
    font-weight: 600;
}

.info-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
}

.info-item {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.info-item label {
    font-weight: 500;
    color: #6b7280;
    font-size: 0.875rem;
}

.info-item span {
    color: #1f2937;
}

.balance {
    font-weight: 600;
    color: #059669;
}

.stats-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
}

.stat-card {
    text-align: center;
    padding: 1rem;
    background: white;
    border-radius: 6px;
}

.stat-number {
    font-size: 1.5rem;
    font-weight: 700;
    color: #1f2937;
}

.stat-label {
    font-size: 0.875rem;
    color: #6b7280;
    margin-top: 0.25rem;
}

.orders-list, .collections-list {
    max-height: 200px;
    overflow-y: auto;
}

.order-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem;
    background: white;
    border-radius: 6px;
    margin-bottom: 0.5rem;
}

.order-info {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.order-number {
    font-weight: 500;
    color: #1f2937;
}

.order-amount {
    font-weight: 600;
    color: #059669;
}

.order-meta {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 0.25rem;
}

.order-status {
    font-size: 0.75rem;
    padding: 0.125rem 0.5rem;
    border-radius: 4px;
}

.order-time {
    font-size: 0.75rem;
    color: #6b7280;
}

.collection-item {
    padding: 0.5rem;
    background: white;
    border-radius: 4px;
    margin-bottom: 0.25rem;
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.book-title {
    font-size: 0.875rem;
    color: #1f2937;
    font-weight: 500;
}

.collect-time {
    font-size: 0.75rem;
    color: #9ca3af;
}

.no-data {
    text-align: center;
    color: #9ca3af;
    font-style: italic;
    padding: 2rem;
}

@media (max-width: 768px) {
    .user-detail-grid {
        grid-template-columns: 1fr;
        gap: 1rem;
    }
    
    .info-grid {
        grid-template-columns: 1fr;
    }
    
    .stats-grid {
        grid-template-columns: 1fr;
    }
}
</style>
`;

// 添加样式到页面
document.head.insertAdjacentHTML('beforeend', userDetailStyles);