"""
API URL配置
组织所有API端点的路由
"""
from django.urls import path
from . import api_views, book_views, user_views

# API端点URL模式
api_urlpatterns = [
    # ========== 书籍相关API ==========
    path('api/books/search/', book_views.book_search_api, name='api_book_search'),
    path('api/books/categories/', book_views.book_categories_api, name='api_book_categories'),
    path('api/books/recommendations/', book_views.book_recommendations_api, name='api_book_recommendations'),
    
    # ========== 访问权限API ==========
    path('api/access/book/', api_views.check_book_access_api, name='api_check_book_access'),
    path('api/access/chapter/', api_views.check_chapter_access_api, name='api_check_chapter_access'),
    
    # ========== 购物车API ==========
    path('api/cart/summary/', api_views.get_cart_summary_api, name='api_cart_summary'),
    path('api/cart/batch-add/', api_views.batch_add_to_cart_api, name='api_batch_add_to_cart'),
    
    # ========== 订单API ==========
    path('api/order/create/', api_views.create_order_api, name='api_create_order'),
    
    # ========== 爬虫API ==========
    path('api/crawler/chapter/', api_views.crawl_single_chapter_api, name='api_crawl_chapter'),
    
    # ========== 用户相关API ==========
    path('api/user/profile/update/', user_views.update_user_profile_api, name='api_update_profile'),
    path('api/user/password/change/', user_views.change_password_api, name='api_change_password'),
    path('api/user/collection/add/', user_views.add_to_collection_api, name='api_add_collection'),
    path('api/user/collection/remove/', user_views.remove_from_collection_api, name='api_remove_collection'),
    path('api/user/stats/', user_views.get_user_stats_api, name='api_user_stats'),
]
