from django.urls import path
from . import views

urlpatterns = [
    # 首页和书籍相关
    path('', views.index, name='index'),
    path('books/', views.book_list, name='book_list'),
    path('book/<int:book_id>/', views.book_detail, name='book_detail'),
    path('book/<int:book_id>/chapter/<int:chapter_number>/', views.chapter_detail, name='chapter_detail'),
    
    # 用户相关
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.user_register, name='register'),
    path('profile/', views.user_profile, name='user_profile'),
    path('update-profile/', views.update_profile, name='update_profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('vip-recharge/', views.vip_recharge, name='vip_recharge'),
    
    # 书架和购物车
    path('bookshelf/', views.bookshelf, name='bookshelf'),
    path('cart/', views.shopping_cart, name='shopping_cart'),
    path('orders/', views.user_orders, name='user_orders'),
    
    # AJAX接口
    path('api/add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('api/remove-from-cart/', views.remove_from_cart, name='remove_from_cart'),
    path('api/clear-cart/', views.clear_cart, name='clear_cart'),
    path('api/cart-count/', views.get_cart_count, name='get_cart_count'),
    
    # 新的购物车管理API
    path('api/cart/add/', views.add_to_cart_new, name='add_to_cart_new'),
    path('api/cart/remove/', views.remove_from_cart_new, name='remove_from_cart_new'),
    path('api/cart/update/', views.update_cart_item, name='update_cart_item'),
    path('api/cart/clear/', views.clear_cart_new, name='clear_cart_new'),
    path('api/cart/remove-book/', views.remove_book_from_cart_new, name='remove_book_from_cart_new'),
    path('api/cart/checkout/', views.cart_checkout, name='cart_checkout'),
    path('api/bulk-add-to-cart/', views.bulk_add_to_cart, name='bulk_add_to_cart'),
    path('api/remove-book-from-cart/', views.remove_from_cart, name='remove_book_from_cart'),
    path('api/book-info/<int:book_id>/', views.get_book_info, name='get_book_info'),
    path('api/add-to-bookshelf/', views.add_to_bookshelf, name='add_to_bookshelf'),
    path('api/remove-from-bookshelf/', views.remove_from_bookshelf, name='remove_from_bookshelf'),
    path('api/collect-book/', views.collect_book, name='collect_book'),
    path('api/remove-from-collection/', views.remove_from_collection, name='remove_from_collection'),
    path('api/submit-review/', views.submit_review, name='submit_review'),
    path('api/edit-review/', views.edit_review, name='edit_review'),
    path('api/delete-review/', views.delete_review, name='delete_review'),
    path('api/create-order/', views.create_order, name='create_order'),
    path('api/user/get-order-detail/<int:order_id>/', views.user_get_order_detail, name='user_get_order_detail'),
    path('api/user/get-order-detail-by-number/<str:order_number>/', views.user_get_order_detail_by_number, name='user_get_order_detail_by_number'),
    path('api/user/upload-avatar/', views.user_upload_avatar, name='user_upload_avatar'),
    path('api/user/update-profile/', views.user_update_profile, name='user_update_profile'),
    
    # 爬虫相关API
    path('api/crawl-chapters/', views.crawl_book_chapters, name='crawl_chapters'),
    path('api/crawl-status/', views.get_crawl_status, name='crawl_status'),
    path('api/check-crawl-status/<int:book_id>/', views.get_crawl_status, name='check_crawl_status'),
    path('api/book/<int:book_id>/chapters/', views.get_chapter_list, name='get_chapter_list'),
    # 新的爬虫API - 使用 AdvancedCrawler
    path('api/qimao/book/<int:book_id>/chapters/', views.get_qimao_chapter_list, name='get_qimao_chapter_list'),
    path('api/qimao/book/<int:book_id>/info/', views.get_qimao_book_info, name='get_qimao_book_info'),
    path('api/crawl-single-chapter/', views.crawl_single_chapter_api, name='crawl_single_chapter'),
    
    # 爬虫监控相关
    path('admin/crawler-monitor/', views.crawler_monitor_view, name='crawler_monitor'),
    path('api/crawler/statistics/', views.api_crawler_statistics, name='api_crawler_statistics'),
    path('api/crawler/tasks/', views.api_crawler_tasks, name='api_crawler_tasks'),
    path('api/crawler/task/<str:task_id>/', views.api_crawler_task_detail, name='api_crawler_task_detail'),
    path('api/crawler/retry/', views.api_crawler_retry_task, name='api_crawler_retry_task'),
    path('api/crawler/start/', views.api_crawler_start_task, name='api_crawler_start_task'),
    
    # 管理员相关
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/books/', views.admin_books, name='admin_books'),
    path('admin/users/', views.admin_users, name='admin_users'),
    path('admin/orders/', views.admin_orders, name='admin_orders'),
    
    # 管理员API - 用户
    path('api/admin/add-user/', views.admin_add_user, name='admin_add_user'),
    path('api/admin/get-user/<int:user_id>/', views.admin_get_user, name='admin_get_user'),
    path('api/admin/get-user-detail/<int:user_id>/', views.admin_get_user_detail, name='admin_get_user_detail'),
    path('api/admin/update-user/', views.admin_update_user, name='admin_update_user'),
    path('api/admin/toggle-user-status/', views.admin_toggle_user_status, name='admin_toggle_user_status'),
    path('api/admin/delete-user/', views.admin_delete_user, name='admin_delete_user'),
    
    # 管理员API - 订单
    path('api/admin/get-order-detail/<int:order_id>/', views.admin_get_order_detail, name='admin_get_order_detail'),
    path('api/admin/update-order-status/', views.admin_update_order_status, name='admin_update_order_status'),
    path('api/admin/batch-update-order-status/', views.admin_batch_update_order_status, name='admin_batch_update_order_status'),
    
    # 优化版管理员书籍管理API
    path('api/admin/books/search/', views.api_admin_search_books, name='api_admin_search_books'),
    path('api/admin/books/<int:book_id>/', views.api_admin_get_book_detail, name='api_admin_get_book_detail'),
    path('api/admin/books/', views.api_admin_create_book, name='api_admin_create_book'),
    path('api/admin/books/<int:book_id>/update/', views.api_admin_update_book, name='api_admin_update_book'),
    path('api/admin/books/<int:book_id>/delete/', views.api_admin_delete_book, name='api_admin_delete_book'),
    path('api/admin/books/categories/', views.api_admin_get_categories, name='api_admin_get_categories'),
    path('api/admin/books/authors/', views.api_admin_get_authors, name='api_admin_get_authors'),
    
    # 购买相关
        path('api/purchase-from-cart/', views.purchase_books_from_cart, name='purchase_books_from_cart'),
    path('api/cart/purchase/', views.purchase_books_from_cart, name='cart_purchase'),
    path('api/book/purchase/', views.purchase_book_directly, name='book_purchase'),
    path('api/purchase-book-directly/', views.purchase_book_directly, name='purchase_book_directly'),
    path('api/support-author/', views.support_author, name='support_author'),
    path('api/cart/add/', views.add_to_cart, name='cart_add'),
    
    # 推荐相关
    path('api/rotating-recommendations/', views.get_rotating_recommendations, name='rotating_recommendations'),
    
    # 书架书籍API
    path('api/bookshelf/books/<str:book_type>/', views.get_bookshelf_books_api, name='get_bookshelf_books_api'),
    path('api/update-read-time/', views.update_read_time, name='update_read_time'),
    
    # 订单管理API
    path('api/orders/all/', views.get_all_orders, name='get_all_orders'),
    path('api/orders/by-status/', views.get_orders_by_status, name='get_orders_by_status'),
    path('api/orders/by-book/', views.get_order_by_book, name='get_order_by_book'),
]

# ========== 新增API端点 (重构后) ==========
# 导入新的API视图服务
from .services import api_views, book_views, user_views

# 添加新的API路由
urlpatterns += [
    # 书籍相关API
    path('api/v2/books/search/', book_views.book_search_api, name='api_v2_book_search'),
    path('api/v2/books/categories/', book_views.book_categories_api, name='api_v2_book_categories'),
    path('api/v2/books/recommendations/', book_views.book_recommendations_api, name='api_v2_book_recommendations'),
    
    # 访问权限API
    path('api/v2/access/book/', api_views.check_book_access_api, name='api_v2_check_book_access'),
    path('api/v2/access/chapter/', api_views.check_chapter_access_api, name='api_v2_check_chapter_access'),
    
    # 购物车API
    path('api/v2/cart/summary/', api_views.get_cart_summary_api, name='api_v2_cart_summary'),
    path('api/v2/cart/batch-add/', api_views.batch_add_to_cart_api, name='api_v2_batch_add_to_cart'),
    
    # 订单API
    path('api/v2/order/create/', api_views.create_order_api, name='api_v2_create_order'),
    
    # 爬虫API
    path('api/v2/crawler/chapter/', api_views.crawl_single_chapter_api, name='api_v2_crawl_chapter'),
    
    # 用户相关API
    path('api/v2/user/profile/update/', user_views.update_user_profile_api, name='api_v2_update_profile'),
    path('api/v2/user/password/change/', user_views.change_password_api, name='api_v2_change_password'),
    path('api/v2/user/collection/add/', user_views.add_to_collection_api, name='api_v2_add_collection'),
    path('api/v2/user/collection/remove/', user_views.remove_from_collection_api, name='api_v2_remove_collection'),
    path('api/v2/user/stats/', user_views.get_user_stats_api, name='api_v2_user_stats'),
]


