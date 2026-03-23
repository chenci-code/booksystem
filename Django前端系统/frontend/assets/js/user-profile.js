/**
 * 最简化的用户中心页面功能
 */

// 页面加载完成后初始化用户中心功能
document.addEventListener('DOMContentLoaded', function() {
    // 设置默认显示个人信息
    showSection('profile');
});

/**
 * 显示指定内容区域
 */
function showSection(sectionName) {
    // 隐藏所有内容区域
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.add('hidden');
    });
    
    // 显示选中的内容区域
    const targetSection = document.getElementById(sectionName + '-section');
    if (targetSection) {
        targetSection.classList.remove('hidden');
    }
    
    // 更新导航菜单状态
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // 找到对应的导航项并激活
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        if (item.getAttribute('onclick') && item.getAttribute('onclick').includes(sectionName)) {
            item.classList.add('active');
        }
    });
}

/**
 * 显示编辑个人信息模态框
 */
function showEditModal() {
    const modal = document.getElementById('editProfileModal');
    if (modal) {
        modal.classList.remove('hidden');
    }
}

/**
 * 隐藏编辑个人信息模态框
 */
function hideEditModal() {
    const modal = document.getElementById('editProfileModal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

/**
 * 简化的订单详情查看
 */
function testViewOrderDetail(orderNumber) {
    alert('订单号: ' + orderNumber + '\n功能开发中...');
}

/**
 * 简化的评价删除
 */
function deleteUserReview(reviewId) {
    if (confirm('确定要删除这条评价吗？')) {
        alert('删除功能开发中...');
    }
}