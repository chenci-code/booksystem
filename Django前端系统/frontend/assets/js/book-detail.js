/**
 * 书籍详情页面特有功能
 */

// 页面加载完成后初始化书籍详情功能
document.addEventListener('DOMContentLoaded', function() {
    initializeBookDetail();
});

/**
 * 初始化书籍详情功能
 */
function initializeBookDetail() {
    // 初始化章节列表
    initializeChapterList();
    
    // 初始化阅读进度
    initializeReadingProgress();
    
    // 初始化评价功能
    initializeReviewSystem();
    
    // 初始化书籍操作按钮
    initializeBookActions();
    
    // 初始化相关推荐
    initializeRelatedBooks();
    
    // 初始化书籍图片
    initializeBookImage();
}

/**
 * 初始化章节列表
 */
function initializeChapterList() {
    const chapterList = document.querySelector('.chapter-list');
    if (!chapterList) return;
    
    // 为章节项添加点击效果
    const chapterItems = document.querySelectorAll('.chapter-item');
    chapterItems.forEach(item => {
        item.addEventListener('click', function() {
            // 添加点击动画
            this.style.transform = 'scale(0.98)';
            setTimeout(() => {
                this.style.transform = '';
            }, 150);
        });
    });
    
    // 实现章节搜索功能
    const searchInput = document.querySelector('#chapter-search');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            filterChapters(this.value);
        });
    }
}

/**
 * 筛选章节
 */
function filterChapters(query) {
    const chapterItems = document.querySelectorAll('.chapter-item');
    const searchTerm = query.toLowerCase();
    
    chapterItems.forEach(item => {
        const chapterTitle = item.querySelector('.chapter-title');
        if (chapterTitle) {
            const title = chapterTitle.textContent.toLowerCase();
            if (title.includes(searchTerm)) {
                item.style.display = '';
            } else {
                item.style.display = 'none';
            }
        }
    });
}

/**
 * 初始化阅读进度
 */
function initializeReadingProgress() {
    const progressBar = document.querySelector('.progress-bar');
    if (!progressBar) return;
    
    // 从localStorage读取阅读进度
    const bookId = document.body.dataset.bookId;
    if (bookId) {
        const progress = localStorage.getItem(`reading_progress_${bookId}`);
        if (progress) {
            progressBar.style.width = progress + '%';
        }
    }
}

/**
 * 更新阅读进度
 */
function updateReadingProgress(progress) {
    const progressBar = document.querySelector('.progress-bar');
    if (progressBar) {
        progressBar.style.width = progress + '%';
        
        // 保存到localStorage
        const bookId = document.body.dataset.bookId;
        if (bookId) {
            localStorage.setItem(`reading_progress_${bookId}`, progress);
        }
    }
}

/**
 * 初始化评价系统
 */
function initializeReviewSystem() {
    // 初始化星级评分
    initializeStarRating();
    
    // 初始化评价表单
    const reviewForm = document.querySelector('#reviewForm');
    if (reviewForm) {
        reviewForm.addEventListener('submit', function(e) {
            e.preventDefault();
            submitReview();
        });
    }
}

/**
 * 初始化星星评分交互
 */
function initializeStarRating() {
    // 初始化评价表单的星星评分
    const ratingInput = document.querySelector('.rating-input');
    if (ratingInput) {
        const stars = ratingInput.querySelectorAll('label');
        stars.forEach((star, index) => {
            star.addEventListener('click', function() {
                const rating = index + 1;
                updateStarDisplay(ratingInput, rating);
                // 选中对应的radio按钮
                const radio = ratingInput.querySelector(`input[value="${rating}"]`);
                if (radio) {
                    radio.checked = true;
                }
            });
            
            // 添加鼠标悬停效果
            star.addEventListener('mouseenter', function() {
                const hoverRating = index + 1;
                updateStarDisplay(ratingInput, hoverRating);
            });
        });
        
        // 鼠标离开时恢复选中状态
        ratingInput.addEventListener('mouseleave', function() {
            const checkedRadio = ratingInput.querySelector('input[name="rating"]:checked');
            if (checkedRadio) {
                const rating = parseInt(checkedRadio.value);
                updateStarDisplay(ratingInput, rating);
            } else {
                updateStarDisplay(ratingInput, 0);
            }
        });
    }
    
    // 初始化编辑评价模态框的星星评分
    const editRatingInput = document.querySelector('#editReviewModal .rating-input');
    if (editRatingInput) {
        const editStars = editRatingInput.querySelectorAll('label');
        editStars.forEach((star, index) => {
            star.addEventListener('click', function() {
                const rating = index + 1;
                updateStarDisplay(editRatingInput, rating);
                // 选中对应的radio按钮
                const radio = editRatingInput.querySelector(`input[value="${rating}"]`);
                if (radio) {
                    radio.checked = true;
                }
            });
            
            // 添加鼠标悬停效果
            star.addEventListener('mouseenter', function() {
                const hoverRating = index + 1;
                updateStarDisplay(editRatingInput, hoverRating);
            });
        });
        
        // 鼠标离开时恢复选中状态
        editRatingInput.addEventListener('mouseleave', function() {
            const checkedRadio = editRatingInput.querySelector('input[name="edit_rating"]:checked');
            if (checkedRadio) {
                const rating = parseInt(checkedRadio.value);
                updateStarDisplay(editRatingInput, rating);
            } else {
                updateStarDisplay(editRatingInput, 0);
            }
        });
    }
}

/**
 * 更新星星显示
 */
function updateStarDisplay(container, rating) {
    const stars = container.querySelectorAll('label');
    stars.forEach((star, index) => {
        if (index < rating) {
            star.classList.add('active');
        } else {
            star.classList.remove('active');
        }
    });
}

/**
 * 提交评分
 */
function submitRating(rating) {
    const bookId = document.body.dataset.bookId;
    if (!bookId) return;
    
    NovelSystem.showLoading();
    
    fetch('/api/submit-rating/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': NovelSystem.getCookie('csrftoken')
        },
        body: JSON.stringify({
            book_id: bookId,
            rating: rating
        })
    })
    .then(response => response.json())
    .then(data => {
        NovelSystem.hideLoading();
        if (data.success) {
            NovelSystem.showMessage(data.message, 'success');
            // 更新评分显示
            updateRatingDisplay(rating);
        } else {
            NovelSystem.showMessage(data.message, 'error');
        }
    })
    .catch(error => {
        NovelSystem.hideLoading();
        NovelSystem.showMessage('评分提交失败，请重试', 'error');
    });
}

/**
 * 提交评价
 */
function submitReview() {
    const bookId = document.body.dataset.bookId;
    const reviewContent = document.querySelector('#reviewContent').value.trim();
    const rating = document.querySelector('input[name="rating"]:checked')?.value;
    
    if (!reviewContent) {
        NovelSystem.showMessage('请输入评价内容', 'warning');
        return;
    }
    
    if (!rating) {
        NovelSystem.showMessage('请选择评分', 'warning');
        return;
    }
    
    NovelSystem.showLoading();
    
    fetch('/api/submit-review/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': NovelSystem.getCookie('csrftoken')
        },
        body: JSON.stringify({
            book_id: bookId,
            rating: rating,
            content: reviewContent
        })
    })
    .then(response => response.json())
    .then(data => {
        NovelSystem.hideLoading();
        if (data.success) {
            NovelSystem.showMessage(data.message, 'success');
            // 更新评分显示
            if (data.rating !== undefined) {
                updateBookRating(data.rating);
            }
            // 清空表单
            const reviewForm = document.querySelector('#reviewForm');
            if (reviewForm) {
                reviewForm.reset();
                // 重置星星显示
                const ratingInput = reviewForm.querySelector('.rating-input');
                if (ratingInput) {
                    updateStarDisplay(ratingInput, 0);
                }
            }
            // 刷新评价列表（延迟刷新，让用户看到更新）
            setTimeout(() => {
                location.reload();
            }, 1000);
        } else {
            NovelSystem.showMessage(data.message, 'error');
        }
    })
    .catch(error => {
        NovelSystem.hideLoading();
        NovelSystem.showMessage('评价提交失败，请重试', 'error');
    });
}

/**
 * 更新评分显示
 */
function updateRatingDisplay(rating) {
    const ratingDisplay = document.querySelector('.rating-display');
    if (ratingDisplay) {
        const stars = ratingDisplay.querySelectorAll('.fa-star');
        stars.forEach((star, index) => {
            if (index < rating) {
                star.classList.remove('far');
                star.classList.add('fas');
            } else {
                star.classList.remove('fas');
                star.classList.add('far');
            }
        });
    }
}

/**
 * 更新书籍评分显示（更新页面上的平均评分）
 */
function updateBookRating(rating) {
    // 更新统计区域的评分
    const statItems = document.querySelectorAll('.stat-item');
    for (let item of statItems) {
        const label = item.querySelector('.stat-label');
        if (label && label.textContent.includes('评分')) {
            const valueElement = item.querySelector('.stat-value');
            if (valueElement) {
                valueElement.textContent = parseFloat(rating).toFixed(1);
            }
        }
    }
    
    // 更新书籍信息区域的评分
    const infoLabels = document.querySelectorAll('.info-label');
    for (let label of infoLabels) {
        if (label.textContent.includes('评分')) {
            const valueElement = label.nextElementSibling;
            if (valueElement && valueElement.classList.contains('info-value')) {
                valueElement.textContent = parseFloat(rating).toFixed(1) + '分';
            }
        }
    }
}

/**
 * 更新书籍收藏数显示
 */
function updateBookCollectionCount(count) {
    // 更新统计区域的收藏数
    const statItems = document.querySelectorAll('.stat-item');
    for (let item of statItems) {
        const label = item.querySelector('.stat-label');
        if (label && label.textContent.includes('收藏')) {
            const valueElement = item.querySelector('.stat-value');
            if (valueElement) {
                valueElement.textContent = count;
            }
        }
    }
}

/**
 * 初始化书籍操作按钮
 */
function initializeBookActions() {
    // 开始阅读按钮
    const startReadingBtn = document.querySelector('.start-reading-btn');
    if (startReadingBtn) {
        startReadingBtn.addEventListener('click', function() {
            startReading();
        });
    }
    
    // 加入书架按钮
    const addToBookshelfBtn = document.querySelector('.add-to-bookshelf-btn');
    if (addToBookshelfBtn) {
        addToBookshelfBtn.addEventListener('click', function() {
            const bookTitle = this.dataset.bookTitle;
            toggleBookshelf(bookTitle);
        });
    }
    
    // 收藏按钮
    const collectBtn = document.querySelector('.collect-btn');
    if (collectBtn) {
        collectBtn.addEventListener('click', function() {
            const bookTitle = this.dataset.bookTitle;
            toggleCollection(bookTitle);
        });
    }
    
    // 购买按钮
    const buyBtn = document.querySelector('.buy-btn');
    if (buyBtn) {
        buyBtn.addEventListener('click', function() {
            const bookTitle = this.dataset.bookTitle;
            const price = parseFloat(this.dataset.price);
            addToCart(bookTitle, price);
        });
    }
}


/**
 * 初始化相关推荐
 */
function initializeRelatedBooks() {
    const relatedBooks = document.querySelectorAll('.related-book');
    
    relatedBooks.forEach(book => {
        book.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-4px)';
            this.style.boxShadow = '0 10px 25px -3px rgba(0, 0, 0, 0.1)';
        });
        
        book.addEventListener('mouseleave', function() {
            this.style.transform = '';
            this.style.boxShadow = '';
        });
    });
}

/**
 * 初始化书籍图片
 */
function initializeBookImage() {
    const bookImage = document.querySelector('.book-cover-large img');
    if (!bookImage) return;
    
    // 图片加载完成后的处理
    bookImage.addEventListener('load', function() {
        this.classList.add('loaded');
        this.style.opacity = '1';
    });
    
    // 图片加载失败的处理
    bookImage.addEventListener('error', function() {
        this.style.display = 'none';
        const noCover = this.nextElementSibling;
        if (noCover && noCover.classList.contains('no-cover-large')) {
            noCover.style.display = 'flex';
        }
    });
}

/**
 * 初始化章节导航
 */
function initializeChapterNavigation() {
    const chapterNav = document.querySelector('.chapter-navigation');
    if (!chapterNav) return;
    
    const prevBtn = chapterNav.querySelector('.prev-chapter');
    const nextBtn = chapterNav.querySelector('.next-chapter');
    
    if (prevBtn) {
        prevBtn.addEventListener('click', function() {
            navigateToChapter('prev');
        });
    }
    
    if (nextBtn) {
        nextBtn.addEventListener('click', function() {
            navigateToChapter('next');
        });
    }
}

/**
 * 导航到章节
 */
function navigateToChapter(direction) {
    const currentChapter = document.querySelector('.current-chapter');
    if (!currentChapter) return;
    
    let targetChapter;
    if (direction === 'prev') {
        targetChapter = currentChapter.previousElementSibling;
    } else {
        targetChapter = currentChapter.nextElementSibling;
    }
    
    if (targetChapter) {
        const link = targetChapter.querySelector('.chapter-link');
        if (link) {
            window.location.href = link.href;
        }
    } else {
        NovelSystem.showMessage(`没有${direction === 'prev' ? '上一' : '下一'}章了`, 'info');
    }
}

/**
 * 初始化书籍统计信息动画
 */
function initializeBookStatsAnimation() {
    const statItems = document.querySelectorAll('.stat-item');
    
    statItems.forEach((item, index) => {
        item.style.opacity = '0';
        item.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            item.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            item.style.opacity = '1';
            item.style.transform = 'translateY(0)';
        }, index * 100);
    });
}

/**
 * 开始阅读（跳转到第一章）
 */
function startReading() {
    const bookId = document.body.dataset.bookId;
    if (bookId) {
        window.location.href = `/book/${bookId}/chapter/1/`;
    }
}

/**
 * 添加到书架
 */
function addToBookshelf() {
    if (!isUserLoggedIn()) return;
    
    const bookTitle = document.body.dataset.bookTitle;
    
    fetch('/api/add-to-bookshelf/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            book_title: bookTitle
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage(data.message, 'success');
            const bookshelfText = document.getElementById('bookshelfText');
            const bookshelfBtn = document.getElementById('bookshelfBtn');
            if (bookshelfText) bookshelfText.textContent = '已加入';
            if (bookshelfBtn) {
                bookshelfBtn.classList.add('btn-success');
                bookshelfBtn.classList.remove('btn-outline-success');
                bookshelfBtn.onclick = function() { removeFromBookshelf(); };
            }
        } else {
            showMessage(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage('添加到书架失败，请重试', 'error');
    });
}

/**
 * 从书架移除
 */
function removeFromBookshelf() {
    if (!isUserLoggedIn()) return;
    
    const bookTitle = document.body.dataset.bookTitle;
    
    if (confirm(`确定要从书架中移除《${bookTitle}》吗？`)) {
        fetch('/api/remove-from-bookshelf/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                book_title: bookTitle
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showMessage(data.message, 'success');
                const bookshelfText = document.getElementById('bookshelfText');
                const bookshelfBtn = document.getElementById('bookshelfBtn');
                if (bookshelfText) bookshelfText.textContent = '加入书架';
                if (bookshelfBtn) {
                    bookshelfBtn.classList.remove('btn-success');
                    bookshelfBtn.classList.add('btn-outline-success');
                    bookshelfBtn.onclick = function() { addToBookshelf(); };
                }
            } else {
                showMessage(data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showMessage('移除失败，请重试', 'error');
        });
    }
}

/**
 * 收藏书籍
 */
function collectBook() {
    if (!isUserLoggedIn()) return;
    
    const bookTitle = document.body.dataset.bookTitle;
    
    fetch('/api/collect-book/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            book_title: bookTitle
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage(data.message, 'success');
            const collectText = document.getElementById('collectText');
            const collectBtn = document.getElementById('collectBtn');
            if (collectText) collectText.textContent = '已收藏';
            if (collectBtn) {
                collectBtn.classList.add('btn-danger');
                collectBtn.classList.remove('btn-outline-danger');
            }
            // 更新收藏数显示
            if (data.collection_count !== undefined) {
                updateBookCollectionCount(data.collection_count);
            }
        } else {
            showMessage(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage('收藏失败，请重试', 'error');
    });
}

/**
 * VIP用户支持作者购买
 */
function supportAuthor(bookId, price) {
    if (!isUserLoggedIn()) return;
    
    if (!confirm(`确定要购买支持作者吗？价格：¥${price}`)) {
        return;
    }
    
    showMessage('正在处理购买...', 'info');
    
    fetch('/api/support-author/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            book_id: bookId,
            price: price
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage(data.message, 'success');
            // 刷新页面以更新购买状态
            setTimeout(() => location.reload(), 1500);
        } else {
            showMessage(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage('购买失败，请重试', 'error');
    });
}

/**
 * 添加整本书到购物车
 */
function addBookToCart(bookId, price) {
    if (!isUserLoggedIn()) return;
    
    showMessage('正在添加到购物车...', 'info');
    
    fetch('/api/cart/add/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            book_id: bookId,
            price: price
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage(data.message, 'success');
            // 更新购物车数量显示
            updateCartCount();
        } else {
            showMessage(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage('添加到购物车失败，请重试', 'error');
    });
}

/**
 * 更新购物车数量显示
 */
function updateCartCount() {
    fetch('/api/cart-count/', {
        method: 'GET',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const cartCountElements = document.querySelectorAll('.cart-count');
            cartCountElements.forEach(element => {
                element.textContent = data.count;
                if (data.count > 0) {
                    element.style.display = 'inline';
                } else {
                    element.style.display = 'none';
                }
            });
        }
    })
    .catch(error => {
        console.error('Error updating cart count:', error);
    });
}

/**
 * 检查用户是否已登录
 */
function isUserLoggedIn() {
    // 检查页面中是否有用户信息
    const userMenu = document.querySelector('.group button span');
    const isLoggedIn = userMenu && userMenu.textContent.trim() !== '';
    
    if (!isLoggedIn) {
        showMessage('请先登录', 'warning');
        setTimeout(() => {
            window.location.href = '/login/';
        }, 1500);
        return false;
    }
    return true;
}

/**
 * 初始化评价表单
 */
function initializeReviewForm() {
    const reviewForm = document.getElementById('reviewForm');
    if (reviewForm) {
        reviewForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const rating = document.querySelector('input[name="rating"]:checked');
            const content = document.getElementById('reviewContent').value;
            const bookTitle = document.body.dataset.bookTitle;
            
            if (!rating) {
                NovelSystem.showMessage('请选择评分', 'error');
                return;
            }
            
            fetch('/api/submit-review/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': NovelSystem.getCookie('csrftoken')
                },
                body: JSON.stringify({
                    book_title: bookTitle,
                    rating: rating.value,
                    review_content: content
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    NovelSystem.showMessage(data.message, 'success');
                    reviewForm.reset();
                    // 刷新页面以显示新评价
                    setTimeout(() => location.reload(), 1000);
                } else {
                    NovelSystem.showMessage(data.message, 'error');
                }
            });
        });
    }
}

/**
 * 显示消息提示
 */
function showMessage(message, type = 'info', duration = 3000) {
    // 如果common.js中的showMessage存在，使用它
    if (typeof window.showMessage === 'function') {
        window.showMessage(message, type, duration);
        return;
    }
    
    // 否则使用简单的alert
    alert(message);
}

/**
 * 获取CSRF Token
 */
function getCookie(name) {
    // 如果common.js中的getCookie存在，使用它
    if (typeof window.getCookie === 'function') {
        return window.getCookie(name);
    }
    
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// 页面加载完成后初始化所有功能
document.addEventListener('DOMContentLoaded', function() {
    initializeChapterNavigation();
    initializeBookStatsAnimation();
    initializeReviewForm();
});
