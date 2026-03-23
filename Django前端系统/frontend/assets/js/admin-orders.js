// 订单管理JavaScript

// 全局变量
let currentOrderId = null;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function () {
    initializeOrderManagement();
});

// 初始化订单管理
function initializeOrderManagement() {
    // 绑定事件监听器
    bindEventListeners();

    // 初始化批量操作
    initBatchOperations();

    // 初始化下拉菜单
    initDropdowns();
}

// 绑定事件监听器
function bindEventListeners() {
    // 模态框外部点击关闭
    const orderDetailModal = document.getElementById('orderDetailModal');
    if (orderDetailModal) {
        orderDetailModal.addEventListener('click', function (e) {
            if (e.target === this) {
                closeOrderDetailModal();
            }
        });
    }

    // ESC键关闭模态框
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            closeOrderDetailModal();
        }
    });

    // 点击其他地方关闭下拉菜单
    document.addEventListener('click', function (e) {
        if (!e.target.closest('.dropdown')) {
            closeAllDropdowns();
        }
    });
}

// 初始化下拉菜单
function initDropdowns() {
    const dropdownToggles = document.querySelectorAll('.dropdown-toggle');
    dropdownToggles.forEach(toggle => {
        toggle.addEventListener('click', function (e) {
            e.stopPropagation();
            const dropdown = this.closest('.dropdown');
            const menu = dropdown.querySelector('.dropdown-menu');

            // 关闭其他下拉菜单
            closeAllDropdowns();

            // 切换当前下拉菜单
            menu.classList.toggle('show');
        });
    });
}

// 关闭所有下拉菜单
function closeAllDropdowns() {
    const dropdownMenus = document.querySelectorAll('.dropdown-menu');
    dropdownMenus.forEach(menu => {
        menu.classList.remove('show');
    });
}

// 切换下拉菜单
function toggleDropdown(button) {
    const dropdown = button.closest('.dropdown');
    const menu = dropdown.querySelector('.dropdown-menu');

    // 关闭其他下拉菜单
    closeAllDropdowns();

    // 切换当前下拉菜单
    menu.classList.toggle('show');
}

// 查看订单详情
function viewOrder(orderId) {
    // 显示加载状态
    const loadingHtml = `
        <div class="loading-state">
            <div class="loading-spinner">
                <i class="fas fa-spinner fa-spin"></i>
            </div>
            <p>正在加载订单详情...</p>
        </div>
    `;

    document.getElementById('orderDetailContent').innerHTML = loadingHtml;
    document.getElementById('orderDetailModal').classList.add('show');
    document.getElementById('orderDetailModal').style.display = 'flex';

    // 强制刷新缓存的URL参数
    const cacheBreaker = `_t=${Date.now()}&_v=${Math.random().toString(36).substr(2, 9)}`;

    fetch(`/api/admin/get-order-detail/${orderId}/?${cacheBreaker}`, {
        method: 'GET',
        headers: {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`网络响应错误: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('订单详情完整数据:', JSON.stringify(data, null, 2)); // 详细调试信息
            if (data.success) {
                // 使用整书购买模式处理数据
                const processedData = processBookPurchaseData(data);
                console.log('整书购买模式处理后的数据:', processedData);
                renderOrderDetail(processedData);
            } else {
                // API返回失败，显示友好的错误信息
                const errorHtml = `
                    <div class="error-state">
                        <div class="error-icon">
                            <i class="fas fa-exclamation-triangle"></i>
                        </div>
                        <h3>获取订单详情失败</h3>
                        <p>${data.message || '服务器返回了错误信息，请稍后重试'}</p>
                        <div class="error-actions">
                            <button class="btn btn-primary" onclick="viewOrder(${orderId})">
                                <i class="fas fa-redo mr-2"></i>重新加载
                            </button>
                            <button class="btn btn-secondary" onclick="closeOrderDetailModal()">
                                <i class="fas fa-times mr-2"></i>关闭
                            </button>
                        </div>
                    </div>
                `;
                document.getElementById('orderDetailContent').innerHTML = errorHtml;
                showMessage('获取订单详情失败: ' + (data.message || '未知错误'), 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);

            // 显示友好的错误页面
            const errorHtml = `
                <div class="error-state">
                    <div class="error-icon">
                        <i class="fas fa-wifi"></i>
                    </div>
                    <h3>网络连接异常</h3>
                    <p>无法连接到服务器，请检查网络连接后重试</p>
                    <div class="error-actions">
                        <button class="btn btn-primary" onclick="viewOrder(${orderId})">
                            <i class="fas fa-redo mr-2"></i>重新加载
                        </button>
                        <button class="btn btn-secondary" onclick="closeOrderDetailModal()">
                            <i class="fas fa-times mr-2"></i>关闭
                        </button>
                    </div>
                </div>
            `;
            document.getElementById('orderDetailContent').innerHTML = errorHtml;
            showMessage('网络连接异常，请检查网络后重试', 'error');
        });
}

// 刷新订单详情
function refreshOrderDetail(orderId) {
    // 显示刷新状态
    const refreshingHtml = `
        <div class="loading-state">
            <div class="loading-spinner">
                <i class="fas fa-sync-alt fa-spin"></i>
            </div>
            <p>正在刷新订单详情...</p>
        </div>
    `;

    document.getElementById('orderDetailContent').innerHTML = refreshingHtml;

    // 强制清除所有相关缓存
    const cacheBreaker = `_refresh=${Date.now()}&_v=${Math.random().toString(36).substr(2, 9)}&_force=true`;

    fetch(`/api/admin/get-order-detail/${orderId}/?${cacheBreaker}`, {
        method: 'GET',
        headers: {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`网络响应错误: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('刷新后的订单详情数据:', JSON.stringify(data, null, 2));
            if (data.success) {
                // 使用整书购买模式处理数据
                const processedData = processBookPurchaseData(data);
                console.log('刷新 - 整书购买模式处理后的数据:', processedData);
                // 重新渲染订单详情（复用viewOrder的渲染逻辑）
                renderOrderDetail(processedData);
                showMessage('订单详情已刷新', 'success');
            } else {
                throw new Error(data.message || '刷新失败');
            }
        })
        .catch(error => {
            console.error('刷新订单详情失败:', error);
            const errorHtml = `
                <div class="error-state">
                    <div class="error-icon">
                        <i class="fas fa-exclamation-triangle"></i>
                    </div>
                    <h3>刷新失败</h3>
                    <p>${error.message || '无法刷新订单详情，请稍后重试'}</p>
                    <div class="error-actions">
                        <button class="btn btn-primary" onclick="refreshOrderDetail(${orderId})">
                            <i class="fas fa-redo mr-2"></i>重新刷新
                        </button>
                        <button class="btn btn-secondary" onclick="closeOrderDetailModal()">
                            <i class="fas fa-times mr-2"></i>关闭
                        </button>
                    </div>
                </div>
            `;
            document.getElementById('orderDetailContent').innerHTML = errorHtml;
            showMessage('刷新失败: ' + (error.message || '未知错误'), 'error');
        });
}

// 渲染订单详情（从viewOrder函数中提取的渲染逻辑）
function renderOrderDetail(data) {
    const order = data.order || {};
    const books = Array.isArray(data.books) ? data.books : [];

    // 数据验证
    if (!order.order_id) {
        throw new Error('订单数据不完整');
    }

    console.log('渲染订单对象:', order);
    console.log('渲染订单book_count值:', order.book_count, '类型:', typeof order.book_count);
    console.log('渲染书籍列表:', books);
    console.log('渲染书籍列表长度:', books.length);

    // 整书购买模式 - 计算书籍数量逻辑，确保返回有效数值
    let bookCount = 0;

    // 优先级1: 使用order.book_count（后端已计算好的整书数量）
    if (order.book_count !== undefined && order.book_count !== null) {
        const count = parseInt(order.book_count);
        if (!isNaN(count) && count >= 0) {
            bookCount = count;
            console.log('使用order.book_count（整书数量）:', bookCount);
        }
    }

    // 优先级2: 如果book_count无效，从books数组计算整书总数量
    if (bookCount === 0 && Array.isArray(books) && books.length > 0) {
        bookCount = books.reduce((sum, book) => {
            // 确保book对象存在且有效
            if (!book || typeof book !== 'object') {
                return sum;
            }

            // 整书购买模式：每本书的数量默认为1（整本）
            const qty = parseInt(book.quantity);
            const validQty = (!isNaN(qty) && qty > 0) ? qty : 1; // 整书购买，默认数量为1本
            console.log('整书购买 - 书籍:', book.book_title || '未知书籍', '数量:', validQty, '本');
            return sum + validQty;
        }, 0);
        console.log('从books数组计算整书数量:', bookCount);
    }

    // 移除chapter_count的备用逻辑，因为现在是整书购买模式
    // 如果前两个优先级都无效，则默认为0
    if (bookCount === 0) {
        console.log('整书购买模式：无有效书籍数据，默认为0');
    }

    // 确保bookCount是有效的正整数，最小值为0
    bookCount = Math.max(0, parseInt(bookCount) || 0);
    console.log('最终计算的整书数量:', bookCount, '本');

    const detailHtml = `
        <div class="order-detail-grid">
            <div class="order-basic-info">
                <h4>订单信息</h4>
                <div class="info-grid">
                    <div class="info-item">
                        <label>订单号:</label>
                        <span class="order-number">${order.order_number}</span>
                    </div>
                    <div class="info-item">
                        <label>用户名:</label>
                        <span>${order.customer_name || '未知用户'}</span>
                    </div>
                    <div class="info-item">
                        <label>订单状态:</label>
                        <span class="status-badge status-${(order.order_status || '').toString().replace(/\s+/g, '-').toLowerCase()}">${order.order_status || '未知状态'}</span>
                    </div>
                    <div class="info-item">
                        <label>订单金额:</label>
                        <span class="order-amount">¥${parseFloat(order.order_amount || 0).toFixed(2)}</span>
                    </div>
                    <div class="info-item">
                        <label>书籍数量:</label>
                        <span>${bookCount} 本</span>
                    </div>
                    <div class="info-item">
                        <label>下单时间:</label>
                        <span>${new Date(order.create_time).toLocaleString('zh-CN')}</span>
                    </div>
                    <div class="info-item">
                        <label>支付时间:</label>
                        <span>${order.payment_time ? new Date(order.payment_time).toLocaleString('zh-CN') : '未支付'}</span>
                    </div>
                </div>
            </div>
            
            <div class="order-books">
                <h4>购买书籍</h4>
                <div class="books-list">
                    ${books.length > 0 ? books.map(book => `
                        <div class="book-item">
                            <div class="book-info">
                                <span class="book-title">${book.book_title || '未知书名'}</span>
                                ${book.author ? `<span class="book-author">作者：${book.author}</span>` : ''}
                                ${book.category ? `<span class="book-category">分类：${book.category}</span>` : ''}
                            </div>
                            <div class="book-price">
                                <span>¥${parseFloat(book.book_price || book.price || book.actual_price || book.unit_price || 0).toFixed(2)}</span>
                            </div>
                        </div>
                    `).join('') : '<p class="no-data">暂无书籍信息</p>'}
                </div>
            </div>
            

            <div class="order-actions-detail">
                <h4>订单操作</h4>
                <div class="actions-grid">
                    <button class="btn btn-secondary" onclick="refreshOrderDetail(${order.order_id})">
                        <i class="fas fa-sync-alt mr-2"></i>刷新详情
                    </button>
                    ${order.order_status === '待支付' ? `
                        <button class="btn btn-primary" onclick="updateOrderStatus(${order.order_id}, '已支付')">
                            <i class="fas fa-check mr-2"></i>确认支付
                        </button>
                    ` : ''}
                    ${order.order_status !== '已取消' ? `
                        <button class="btn btn-danger" onclick="updateOrderStatus(${order.order_id}, '已取消')">
                            <i class="fas fa-times mr-2"></i>取消订单
                        </button>
                    ` : ''}
                    <button class="btn btn-secondary" onclick="printOrder(${order.order_id})">
                        <i class="fas fa-print mr-2"></i>打印订单
                    </button>
                </div>
            </div>
            
            <div class="order-timeline">
                <h4>订单时间线</h4>
                <div class="timeline">
                    <div class="timeline-item active">
                        <div class="timeline-marker"></div>
                        <div class="timeline-content">
                            <div class="timeline-title">订单创建</div>
                            <div class="timeline-time">${new Date(order.create_time).toLocaleString()}</div>
                        </div>
                    </div>
                    ${order.payment_time ? `
                        <div class="timeline-item active">
                            <div class="timeline-marker"></div>
                            <div class="timeline-content">
                                <div class="timeline-title">订单支付</div>
                                <div class="timeline-time">${new Date(order.payment_time).toLocaleString()}</div>
                            </div>
                        </div>
                    ` : `
                        <div class="timeline-item">
                            <div class="timeline-marker"></div>
                            <div class="timeline-content">
                                <div class="timeline-title">等待支付</div>
                                <div class="timeline-time">-</div>
                            </div>
                        </div>
                    `}
                </div>
            </div>
        </div>
    `;

    document.getElementById('orderDetailContent').innerHTML = detailHtml;
}

// 关闭订单详情模态框
function closeOrderDetailModal() {
    const modal = document.getElementById('orderDetailModal');
    if (modal) {
        modal.classList.remove('show');
        modal.style.display = 'none';
    }
}

// 更新订单状态
function updateOrderStatus(orderId, newStatus) {
    const statusMap = {
        '待支付': '等待支付',
        '已支付': '确认支付',
        '已取消': '取消'
    };

    const action = statusMap[newStatus] || '更新';

    if (!confirm(`确定要${action}该订单吗？`)) {
        return;
    }

    fetch('/api/admin/update-order-status/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            order_id: orderId,
            status: newStatus
        })
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showMessage(data.message, 'success');
                // 更新页面上的状态显示
                updateOrderRowStatus(orderId, newStatus);
                // 如果在详情模态框中，也更新模态框
                if (document.getElementById('orderDetailModal').style.display === 'flex') {
                    closeOrderDetailModal();
                    setTimeout(() => viewOrder(orderId), 500);
                }
            } else {
                showMessage(data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showMessage('更新失败，请重试', 'error');
        });
}

// 更新订单行状态显示
function updateOrderRowStatus(orderId, newStatus) {
    const orderRow = document.querySelector(`[data-order-id="${orderId}"]`);
    if (orderRow) {
        const statusBadge = orderRow.querySelector('.status-badge');
        if (statusBadge) {
            // 更新状态样式和文本
            statusBadge.className = `status-badge status-${newStatus.replace(/\s+/g, '-').toLowerCase()}`;

            // 更新图标和文本
            let iconClass = 'fas fa-clock';
            if (newStatus === '已支付') iconClass = 'fas fa-check';
            else if (newStatus === '已取消') iconClass = 'fas fa-times-circle';

            statusBadge.innerHTML = `<i class="${iconClass}"></i> ${newStatus}`;
        }

        // 更新操作按钮
        const actionsCell = orderRow.querySelector('.table-actions');
        if (actionsCell) {
            updateActionButtons(actionsCell, orderId, newStatus);
        }
    }
}

// 更新操作按钮
function updateActionButtons(actionsCell, orderId, status) {
    let buttonsHtml = `
        <button class="table-action-btn" onclick="viewOrder(${orderId})" title="查看详情">
            <i class="fas fa-eye"></i>
        </button>
    `;

    if (status === '待支付') {
        buttonsHtml += `
            <button class="table-action-btn confirm" onclick="updateOrderStatus(${orderId}, '已支付')" title="确认支付">
                <i class="fas fa-check"></i>
            </button>
        `;
    }

    if (status !== '已取消') {
        buttonsHtml += `
            <button class="table-action-btn cancel" onclick="updateOrderStatus(${orderId}, '已取消')" title="取消">
                <i class="fas fa-times"></i>
            </button>
        `;
    }

    buttonsHtml += `
        <div class="dropdown">
            <button class="table-action-btn dropdown-toggle" onclick="toggleDropdown(this)">
                <i class="fas fa-ellipsis-v"></i>
            </button>
            <div class="dropdown-menu">
                <a href="#" onclick="updateOrderStatus(${orderId}, '待支付')">设为待支付</a>
                <a href="#" onclick="updateOrderStatus(${orderId}, '已支付')">设为已支付</a>
                <a href="#" onclick="updateOrderStatus(${orderId}, '已取消')">设为已取消</a>
            </div>
        </div>
    `;

    actionsCell.innerHTML = buttonsHtml;
}

// 批量确认支付
function batchConfirmPayment() {
    const checkedBoxes = document.querySelectorAll('.order-checkbox:checked');
    const orderIds = Array.from(checkedBoxes).map(cb => cb.value);

    if (orderIds.length === 0) {
        showMessage('请选择要确认支付的订单', 'error');
        return;
    }

    if (!confirm(`确定要批量确认支付选中的 ${orderIds.length} 个订单吗？`)) {
        return;
    }

    fetch('/api/admin/batch-update-order-status/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            order_ids: orderIds,
            status: '已支付'
        })
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showMessage(`成功确认支付 ${data.updated_count} 个订单`, 'success');
                setTimeout(() => {
                    location.reload();
                }, 1000);
            } else {
                showMessage(data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showMessage('批量确认支付失败，请重试', 'error');
        });
}

// 批量更新状态
function batchUpdateStatus(status) {
    const checkedBoxes = document.querySelectorAll('.order-checkbox:checked');
    const orderIds = Array.from(checkedBoxes).map(cb => cb.value);

    if (orderIds.length === 0) {
        showMessage('请选择要操作的订单', 'error');
        return;
    }

    const action = status === '已支付' ? '确认支付' : '完成';
    if (!confirm(`确定要批量${action}选中的 ${orderIds.length} 个订单吗？`)) {
        return;
    }

    fetch('/api/admin/batch-update-order-status/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            order_ids: orderIds,
            status: status
        })
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showMessage(`成功${action} ${data.updated_count} 个订单`, 'success');
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

// 导出订单数据
function exportOrders() {
    const currentUrl = new URL(window.location);
    const params = new URLSearchParams(currentUrl.search);
    params.set('export', 'true');

    const exportUrl = '/api/admin/export-orders/?' + params.toString();

    // 创建下载链接
    const link = document.createElement('a');
    link.href = exportUrl;
    link.download = `orders_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    showMessage('导出任务已开始', 'success');
}

// 刷新订单
function refreshOrders() {
    showMessage('正在刷新订单数据...', 'success');
    setTimeout(() => {
        location.reload();
    }, 500);
}

// 打印订单
function printOrder(orderId) {
    const printUrl = `/api/admin/print-order/${orderId}/`;
    window.open(printUrl, '_blank', 'width=800,height=600');
}

// 初始化批量操作
function initBatchOperations() {
    const selectAllCheckbox = document.getElementById('selectAll');
    const selectAllTableCheckbox = document.getElementById('selectAllTable');
    const orderCheckboxes = document.querySelectorAll('.order-checkbox');

    // 处理头部的全选
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function () {
            orderCheckboxes.forEach(checkbox => {
                checkbox.checked = this.checked;
            });
            updateBatchButtons();
        });
    }

    // 处理表格头部的全选
    if (selectAllTableCheckbox) {
        selectAllTableCheckbox.addEventListener('change', function () {
            orderCheckboxes.forEach(checkbox => {
                checkbox.checked = this.checked;
            });
            updateBatchButtons();
        });
    }

    // 处理单个复选框
    orderCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updateBatchButtons);
    });
}

// 全选切换
function toggleSelectAll() {
    const selectAllCheckbox = document.getElementById('selectAll') || document.getElementById('selectAllTable');
    const orderCheckboxes = document.querySelectorAll('.order-checkbox');

    if (selectAllCheckbox) {
        orderCheckboxes.forEach(checkbox => {
            checkbox.checked = selectAllCheckbox.checked;
        });
        updateBatchButtons();
    }
}

// 更新批量操作按钮状态
function updateBatchButtons() {
    const checkedBoxes = document.querySelectorAll('.order-checkbox:checked');
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

// 切换购买内容展开/收起 - 统一版本
function togglePurchaseContent(trigger, orderId) {
    const container = trigger.closest('.purchase-content-unified') || trigger.closest('.purchase-content-container');
    const expandedContainer = container.querySelector('.expanded-books-container') || container.querySelector('.expanded-content');
    const icon = trigger.querySelector('i');
    const isExpanded = trigger.classList.contains('expanded');
    
    // 添加加载状态
    trigger.classList.add('loading');
    
    setTimeout(() => {
        if (!isExpanded) {
            // 展开
            expandedContainer.style.display = 'block';
            expandedContainer.classList.remove('hide');
            expandedContainer.classList.add('show', 'animate-in');
            
            icon.classList.remove('fa-chevron-down');
            icon.classList.add('fa-chevron-up');
            trigger.classList.add('expanded');
            
            // 更新按钮文本
            const span = trigger.querySelector('span');
            if (span) {
                span.textContent = '收起';
            }
            
            // 移动端处理
            if (window.innerWidth <= 768) {
                // 添加关闭按钮
                if (!expandedContainer.querySelector('.close-btn')) {
                    const closeBtn = document.createElement('button');
                    closeBtn.className = 'close-btn';
                    closeBtn.innerHTML = '<i class="fas fa-times"></i>';
                    closeBtn.onclick = () => togglePurchaseContent(trigger, orderId);
                    expandedContainer.appendChild(closeBtn);
                }
                
                // 阻止背景滚动
                document.body.style.overflow = 'hidden';
            }
        } else {
            // 收起
            expandedContainer.classList.remove('show', 'animate-in');
            expandedContainer.classList.add('hide', 'animate-out');
            
            icon.classList.remove('fa-chevron-up');
            icon.classList.add('fa-chevron-down');
            trigger.classList.remove('expanded');
            
            // 获取书籍数量来显示正确的计数
            const bookItems = expandedContainer.querySelectorAll('.book-item-unified, .book-item-expanded');
            const span = trigger.querySelector('span');
            if (span) {
                span.textContent = `查看全部(${bookItems.length}本)`;
            }
            
            // 移动端处理
            if (window.innerWidth <= 768) {
                // 恢复背景滚动
                document.body.style.overflow = '';
            }
            
            // 动画结束后隐藏
            setTimeout(() => {
                expandedContainer.style.display = 'none';
                expandedContainer.classList.remove('hide', 'animate-out');
            }, 300);
        }
        
        // 移除加载状态
        trigger.classList.remove('loading');
    }, 100);
}

// 增强的悬停效果处理
function initBookItemHoverEffects() {
    const bookItems = document.querySelectorAll('.book-item-unified, .book-item-summary, .book-item-expanded');
    
    bookItems.forEach(item => {
        item.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
            this.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)';
        });
        
        item.addEventListener('mouseleave', function() {
            this.style.transform = '';
            this.style.boxShadow = '';
        });
    });
}

// 响应式行为控制
function initResponsiveBehavior() {
    let resizeTimer;
    
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function() {
            const expandedContainers = document.querySelectorAll('.expanded-books-container.show, .expanded-content.show');
            
            expandedContainers.forEach(container => {
                if (window.innerWidth <= 768) {
                    // 移动端：转换为模态框
                    container.style.position = 'fixed';
                    container.style.top = '50%';
                    container.style.left = '50%';
                    container.style.transform = 'translate(-50%, -50%)';
                    container.style.width = '90%';
                    container.style.maxWidth = '400px';
                    container.style.zIndex = '9999';
                    
                    // 添加关闭按钮
                    if (!container.querySelector('.close-btn')) {
                        const closeBtn = document.createElement('button');
                        closeBtn.className = 'close-btn';
                        closeBtn.innerHTML = '<i class="fas fa-times"></i>';
                        closeBtn.onclick = () => {
                            const trigger = document.querySelector('.expand-trigger.expanded');
                            if (trigger) {
                                const orderId = trigger.getAttribute('onclick').match(/\d+/)[0];
                                togglePurchaseContent(trigger, orderId);
                            }
                        };
                        container.appendChild(closeBtn);
                    }
                } else {
                    // 桌面端：恢复正常位置
                    container.style.position = 'absolute';
                    container.style.top = '100%';
                    container.style.left = '0';
                    container.style.transform = '';
                    container.style.width = '';
                    container.style.maxWidth = '';
                    container.style.zIndex = '1000';
                    
                    // 移除关闭按钮
                    const closeBtn = container.querySelector('.close-btn');
                    if (closeBtn) {
                        closeBtn.remove();
                    }
                }
            });
        }, 250);
    });
}

// 数据状态检查和处理
function checkBookDataIntegrity() {
    const bookItems = document.querySelectorAll('.book-item-unified');
    
    bookItems.forEach(item => {
        const title = item.querySelector('.book-title');
        const author = item.querySelector('.book-author');
        const category = item.querySelector('.book-category');
        const price = item.querySelector('.book-price');
        
        let missingCount = 0;
        
        // 检查数据完整性
        if (!title || title.textContent.includes('未知书名')) missingCount++;
        if (!author || author.textContent.includes('未知作者')) missingCount++;
        if (!category || category.textContent.includes('未分类')) missingCount++;
        if (!price || price.textContent.includes('¥0.00')) missingCount++;
        
        // 根据缺失程度添加状态类
        if (missingCount === 0) {
            item.classList.add('complete');
        } else if (missingCount <= 2) {
            item.classList.add('incomplete');
        } else {
            item.classList.add('error');
        }
    });
}

// 初始化统一的购买内容功能
function initUnifiedPurchaseContent() {
    // 初始化悬停效果
    initBookItemHoverEffects();
    
    // 初始化响应式行为
    initResponsiveBehavior();
    
    // 检查数据完整性
    checkBookDataIntegrity();
    
    // 为所有展开触发器添加统一的事件处理
    const expandTriggers = document.querySelectorAll('.expand-trigger');
    expandTriggers.forEach(trigger => {
        // 移除旧的onclick属性，使用新的事件监听器
        const onclickAttr = trigger.getAttribute('onclick');
        if (onclickAttr) {
            const orderIdMatch = onclickAttr.match(/\d+/);
            if (orderIdMatch) {
                const orderId = orderIdMatch[0];
                trigger.removeAttribute('onclick');
                trigger.addEventListener('click', () => togglePurchaseContent(trigger, orderId));
            }
        }
    });
}

// 页面加载完成后初始化统一功能
document.addEventListener('DOMContentLoaded', function() {
    // 延迟初始化，确保DOM完全加载
    setTimeout(initUnifiedPurchaseContent, 100);
});

// 添加订单详情样式
const orderDetailStyles = `
<style>
.order-detail-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 2rem;
}

.order-basic-info, .order-books, .order-actions-detail, .order-timeline {
    background: #f9fafb;
    padding: 1.5rem;
    border-radius: 8px;
}

.order-basic-info h4, .order-books h4, .order-actions-detail h4, .order-timeline h4 {
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

.order-number {
    font-family: monospace;
    font-weight: 600;
    color: #1f2937;
}

.order-amount {
    font-weight: 600;
    color: #059669;
}

.books-list {
    max-height: 300px;
    overflow-y: auto;
}

.book-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem;
    background: white;
    border-radius: 6px;
    margin-bottom: 0.5rem;
}

.book-info {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.book-title {
    font-weight: 500;
    color: #1f2937;
}

.book-author {
    font-size: 0.875rem;
    color: #6b7280;
}

.book-price {
    font-weight: 600;
    color: #059669;
}


.actions-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 1rem;
}

.btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.75rem 1rem;
    border: none;
    border-radius: 6px;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    text-decoration: none;
}

.btn-primary {
    background: #3b82f6;
    color: white;
}

.btn-primary:hover {
    background: #1d4ed8;
}

.btn-success {
    background: #10b981;
    color: white;
}

.btn-success:hover {
    background: #059669;
}

.btn-danger {
    background: #ef4444;
    color: white;
}

.btn-danger:hover {
    background: #dc2626;
}

.btn-secondary {
    background: #6b7280;
    color: white;
}

.btn-secondary:hover {
    background: #4b5563;
}

.timeline {
    position: relative;
}

.timeline::before {
    content: '';
    position: absolute;
    left: 10px;
    top: 0;
    bottom: 0;
    width: 2px;
    background: #e5e7eb;
}

.timeline-item {
    position: relative;
    padding-left: 2rem;
    margin-bottom: 1.5rem;
}

.timeline-item:last-child {
    margin-bottom: 0;
}

.timeline-marker {
    position: absolute;
    left: -2rem;
    top: 0.25rem;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: #e5e7eb;
    border: 3px solid white;
    box-shadow: 0 0 0 1px #e5e7eb;
}

.timeline-item.active .timeline-marker {
    background: #3b82f6;
    box-shadow: 0 0 0 1px #3b82f6;
}

.timeline-title {
    font-weight: 500;
    color: #1f2937;
    margin-bottom: 0.25rem;
}

.timeline-time {
    font-size: 0.875rem;
    color: #6b7280;
}

.no-data {
    text-align: center;
    color: #9ca3af;
    font-style: italic;
    padding: 2rem;
}

/* 加载状态样式 */
.loading-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 3rem;
    text-align: center;
}

.loading-spinner {
    font-size: 2rem;
    color: #3b82f6;
    margin-bottom: 1rem;
}

.loading-state p {
    color: #6b7280;
    font-size: 1rem;
}

/* 错误状态样式 */
.error-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 3rem;
    text-align: center;
}

.error-icon {
    font-size: 3rem;
    color: #ef4444;
    margin-bottom: 1rem;
}

.error-state h3 {
    color: #1f2937;
    margin-bottom: 0.5rem;
    font-size: 1.25rem;
    font-weight: 600;
}

.error-state p {
    color: #6b7280;
    margin-bottom: 2rem;
    max-width: 400px;
    line-height: 1.5;
}

.error-actions {
    display: flex;
    gap: 1rem;
    justify-content: center;
}

@media (max-width: 768px) {
    .order-detail-grid {
        grid-template-columns: 1fr;
        gap: 1rem;
    }
    
    .info-grid {
        grid-template-columns: 1fr;
    }
    
    .actions-grid {
        grid-template-columns: 1fr;
    }
    
    .error-actions {
        flex-direction: column;
        width: 100%;
    }
}

/* 购买内容样式 */
.purchase-content {
    max-width: 300px;
    position: relative;
}

.purchase-content-container {
    position: relative;
}

.book-item-summary {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding: 8px 0;
    border-bottom: 1px solid #f0f0f0;
}

.book-item-summary:last-child {
    border-bottom: none;
}

.book-main-info {
    display: flex;
    flex-direction: column;
    flex: 1;
    gap: 4px;
}

.book-title {
    font-weight: 500;
    color: #1f2937;
    font-size: 14px;
    line-height: 1.3;
}

.book-author {
    font-size: 12px;
    color: #6b7280;
}

.book-category {
    font-size: 12px;
    color: #6b7280;
}

.book-price-info {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 2px;
}

.book-price {
    font-weight: 600;
    color: #059669;
    font-size: 13px;
}

.total-price {
    font-weight: 700;
    color: #059669;
    font-size: 18px;
}

.expand-trigger {
    color: #007bff;
    cursor: pointer;
    font-size: 12px;
    margin-top: 8px;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 8px;
    border-radius: 4px;
    transition: all 0.2s ease;
}

.expand-trigger:hover {
    color: #0056b3;
    background-color: #f8f9fa;
}

.expanded-content {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: white;
    border: 1px solid #ddd;
    border-radius: 6px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    z-index: 1000;
    max-height: 300px;
    overflow-y: auto;
    margin-top: 4px;
}

.book-item-expanded {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding: 12px;
    border-bottom: 1px solid #f0f0f0;
}

.book-item-expanded:last-child {
    border-bottom: none;
}

.book-item-expanded:hover {
    background-color: #f8f9fa;
}

.book-info-detail {
    display: flex;
    flex-direction: column;
    flex: 1;
    gap: 4px;
}

.book-price-detail {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 2px;
}

.no-books {
    color: #6b7280;
    font-style: italic;
    font-size: 14px;
}

</style>
`;

// 添加样式到页面
document.head.insertAdjacentHTML('beforeend', orderDetailStyles);
// 切换购买
内容展开 / 收起 - 与订单详情保持一致的交互方式
function togglePurchaseContent(trigger, orderId) {
    const container = trigger.closest('.purchase-content-container');
    const expandedContent = container.querySelector('.expanded-content');
    const icon = trigger.querySelector('i');

    if (expandedContent.style.display === 'none' || !expandedContent.style.display) {
        // 展开内容
        expandedContent.style.display = 'block';
        icon.className = 'fas fa-chevron-up';
        trigger.innerHTML = `<i class="fas fa-chevron-up"></i> 收起`;

        // 添加点击外部关闭功能
        setTimeout(() => {
            document.addEventListener('click', function closeExpandedContent(e) {
                if (!container.contains(e.target)) {
                    expandedContent.style.display = 'none';
                    icon.className = 'fas fa-chevron-down';
                    // 获取书籍数量来显示正确的计数
                    const bookItems = expandedContent.querySelectorAll('.book-item-expanded');
                    trigger.innerHTML = `<i class="fas fa-chevron-down"></i> 查看全部(${bookItems.length})`;
                    document.removeEventListener('click', closeExpandedContent);
                }
            });
        }, 100);
    } else {
        // 收起内容
        expandedContent.style.display = 'none';
        icon.className = 'fas fa-chevron-down';
        // 获取书籍数量来显示正确的计数
        const bookItems = expandedContent.querySelectorAll('.book-item-expanded');
        trigger.innerHTML = `<i class="fas fa-chevron-down"></i> 查看全部(${bookItems.length})`;
    }
}

// 整书购买模式数据处理函数 - 确保所有计算都基于整本书籍
function processBookPurchaseData(orderData) {
    // 确保所有计算都基于整本书籍
    const books = orderData.books || [];

    // 计算书籍总数（整本书籍数量）
    const totalBooks = books.reduce((sum, book) => {
        // 整书购买模式：每本书的数量就是整本书的数量
        const quantity = parseInt(book.quantity) || 1; // 默认1本整书
        console.log('整书购买处理 - 书籍:', book.book_title || '未知书名', '数量:', quantity, '本');
        return sum + quantity;
    }, 0);

    // 计算总价格（基于整书定价）
    const totalPrice = books.reduce((sum, book) => {
        const price = parseFloat(book.price) || 0; // 整书价格
        const quantity = parseInt(book.quantity) || 1; // 整书数量
        return sum + (price * quantity);
    }, 0);

    console.log('整书购买模式处理结果 - 总书籍数:', totalBooks, '本，总价格:', totalPrice);

    return {
        ...orderData,
        book_count: totalBooks, // 整书数量
        books_total_price: totalPrice, // 整书总价格
        purchase_type: 'whole_book' // 标识为整书购买
    };
}

// 生成与订单详情一致的购买内容HTML（用于动态生成）- 完善版本
function generateUnifiedPurchaseContent(books, totalPrice) {
    // 异常处理：检查输入参数
    if (!books || !Array.isArray(books) || books.length === 0) {
        return '<span class="no-books">暂无书籍信息</span>';
    }

    // 过滤掉无效的书籍数据
    const validBooks = books.filter(book => {
        return book && typeof book === 'object' && (book.book_title || book.title);
    });

    if (validBooks.length === 0) {
        return '<span class="no-books">暂无有效书籍信息</span>';
    }

    // 计算总价格（如果没有提供）
    const calculatedTotalPrice = totalPrice || validBooks.reduce((sum, book) => {
        const price = parseFloat(book.price) || 0;
        const quantity = parseInt(book.quantity) || 1;
        return sum + (price * quantity);
    }, 0);

    const headerHtml = `
        <div class="purchase-header">
            <span class="purchase-title">购买内容</span>
            <span class="total-price">¥${calculatedTotalPrice.toFixed(2)}</span>
        </div>
    `;

    // 生成书籍信息HTML的辅助函数
    function generateBookItemHtml(book, isExpanded = false) {
        const bookTitle = book.book_title || book.title || '未知书名';
        const bookAuthor = book.author || '';
        const bookCategory = book.category || book.genre || '';
        const bookPrice = parseFloat(book.price) || 0;
        const bookQuantity = parseInt(book.quantity) || 1;

        const itemClass = isExpanded ? 'book-item-expanded' : 'book-item-summary';
        const infoClass = isExpanded ? 'book-info-detail' : 'book-main-info';
        const priceClass = isExpanded ? 'book-price-detail' : 'book-price-info';

        return `
            <div class="${itemClass}">
                <div class="${infoClass}">
                    <span class="book-title" title="${bookTitle}">${bookTitle}</span>
                    ${bookAuthor ? `<span class="book-author">作者：${bookAuthor}</span>` : '<span class="book-author">作者：未知作者</span>'}
                    ${isExpanded ? (bookCategory ? `<span class="book-category">分类：${bookCategory}</span>` : '<span class="book-category">分类：未分类</span>') : ''}
                </div>
                <div class="${priceClass}">
                    <span class="book-price">¥${bookPrice.toFixed(2)}</span>
                    ${bookQuantity > 1 ? `<span class="book-quantity">x${bookQuantity}</span>` : ''}
                </div>
            </div>
        `;
    }

    if (validBooks.length <= 2) {
        // 1-2本书籍，直接显示所有
        const booksHtml = validBooks.map(book => generateBookItemHtml(book, false)).join('');
        return headerHtml + booksHtml;
    } else {
        // 超过2本书籍，显示前2本+展开功能
        const summaryBooksHtml = validBooks.slice(0, 2).map(book => generateBookItemHtml(book, false)).join('');
        const allBooksHtml = validBooks.map(book => generateBookItemHtml(book, true)).join('');

        return `
            ${headerHtml}
            <div class="purchase-content-container">
                <div class="content-summary">
                    ${summaryBooksHtml}
                </div>
                <span class="expand-trigger" onclick="togglePurchaseContent(this, 'order-${Date.now()}')">
                    <i class="fas fa-chevron-down"></i> 查看全部(${validBooks.length})
                </span>
                <div class="expanded-content" style="display: none;">
                    ${allBooksHtml}
                </div>
            </div>
        `;
    }
}

// 书籍信息验证和处理函数
function validateAndProcessBookInfo(book) {
    if (!book || typeof book !== 'object') {
        return null;
    }

    return {
        book_title: book.book_title || book.title || '未知书名',
        author: book.author || '未知作者',
        category: book.category || book.genre || '未分类',
        price: Math.max(0, parseFloat(book.price) || 0),
        quantity: Math.max(1, parseInt(book.quantity) || 1),
        // 保留原始数据以备后用
        _original: book
    };
}

// 批量处理书籍信息
function processBooksInfo(books) {
    if (!Array.isArray(books)) {
        return [];
    }

    return books
        .map(validateAndProcessBookInfo)
        .filter(book => book !== null);
}
// 切换购买内容展开/收起 - 修复版本
function togglePurchaseContent(trigger, orderId) {
    console.log('togglePurchaseContent called', trigger, orderId);
    
    // 查找正确的容器
    const container = trigger.closest('.purchase-content-unified');
    if (!container) {
        console.error('未找到购买内容容器');
        return;
    }
    
    const expandedContainer = container.querySelector('.expanded-books-container');
    if (!expandedContainer) {
        console.error('未找到展开容器');
        return;
    }
    
    const icon = trigger.querySelector('i');
    const span = trigger.querySelector('span');
    
    // 防止事件冒泡
    if (event) {
        event.stopPropagation();
    }

    if (expandedContainer.style.display === 'none' || !expandedContainer.style.display) {
        // 展开内容
        console.log('展开内容');
        expandedContainer.style.display = 'block';
        
        if (icon) {
            icon.className = 'fas fa-chevron-up';
        }
        if (span) {
            span.textContent = '收起';
        }

        // 添加展开动画效果
        expandedContainer.style.opacity = '0';
        expandedContainer.style.transform = 'translateY(-10px)';

        setTimeout(() => {
            expandedContainer.style.transition = 'all 0.3s ease';
            expandedContainer.style.opacity = '1';
            expandedContainer.style.transform = 'translateY(0)';
        }, 10);

        // 添加点击外部关闭功能
        setTimeout(() => {
            const closeHandler = function (e) {
                if (!container.contains(e.target)) {
                    // 收起内容
                    expandedContainer.style.opacity = '0';
                    expandedContainer.style.transform = 'translateY(-10px)';

                    setTimeout(() => {
                        expandedContainer.style.display = 'none';
                        expandedContainer.style.transition = '';
                        if (icon) {
                            icon.className = 'fas fa-chevron-down';
                        }
                        // 获取书籍数量来显示正确的计数
                        const bookItems = expandedContainer.querySelectorAll('.book-item-unified');
                        if (span) {
                            span.textContent = `查看全部(${bookItems.length}本)`;
                        }
                    }, 300);

                    document.removeEventListener('click', closeHandler);
                }
            };
            document.addEventListener('click', closeHandler);
        }, 100);

    } else {
        // 收起内容
        console.log('收起内容');
        expandedContainer.style.opacity = '0';
        expandedContainer.style.transform = 'translateY(-10px)';

        setTimeout(() => {
            expandedContainer.style.display = 'none';
            expandedContainer.style.transition = '';
            if (icon) {
                icon.className = 'fas fa-chevron-down';
            }
            // 获取书籍数量来显示正确的计数
            const bookItems = expandedContainer.querySelectorAll('.book-item-unified');
            if (span) {
                span.textContent = `查看全部(${bookItems.length}本)`;
            }
        }, 300);
    }
}

// 优化展开内容的定位逻辑
function adjustExpandedContentPosition(expandedContent) {
    const rect = expandedContent.getBoundingClientRect();
    const viewportHeight = window.innerHeight;
    const viewportWidth = window.innerWidth;

    // 检查是否超出视口底部
    if (rect.bottom > viewportHeight) {
        expandedContent.style.top = 'auto';
        expandedContent.style.bottom = '100%';
        expandedContent.style.marginBottom = '0.25rem';
        expandedContent.style.marginTop = '0';
    }

    // 检查是否超出视口右侧
    if (rect.right > viewportWidth) {
        expandedContent.style.left = 'auto';
        expandedContent.style.right = '0';
    }

    // 在小屏幕设备上使用固定定位
    if (viewportWidth <= 768) {
        expandedContent.style.position = 'fixed';
        expandedContent.style.top = '50%';
        expandedContent.style.left = '50%';
        expandedContent.style.transform = 'translate(-50%, -50%)';
        expandedContent.style.width = '90%';
        expandedContent.style.maxWidth = '400px';
        expandedContent.style.maxHeight = '70vh';
        expandedContent.style.zIndex = '9999';
    }
}