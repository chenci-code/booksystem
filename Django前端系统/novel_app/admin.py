from django.contrib import admin
from .models import (
    BookName, BookChapter, UserProfile, UserBookOwnership, BookOrder, 
    BookShoppingCart, CartItem, BookEvaluate, Admin, SystemConfig
)


@admin.register(BookName)
class BookNameAdmin(admin.ModelAdmin):
    list_display = ['book_id', 'title', 'author', 'category', 'status', 'chapter_count', 'rating', 'create_time']
    list_filter = ['category', 'status', 'author']
    search_fields = ['title', 'author', 'qimao_book_id']
    readonly_fields = ['book_id', 'create_time']
    ordering = ['-create_time']
    list_per_page = 25


@admin.register(BookChapter)
class BookChapterAdmin(admin.ModelAdmin):
    list_display = ['chapter_id', 'book_title', 'chapter_number', 'chapter_title', 'word_count', 'is_crawled', 'create_time']
    list_filter = ['is_crawled', 'book_title']
    search_fields = ['book_title', 'chapter_title']
    readonly_fields = ['chapter_id', 'create_time']
    ordering = ['book_title', 'chapter_number']
    list_per_page = 50


@admin.register(UserBookOwnership)
class UserBookOwnershipAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_username', 'book_title', 'access_type', 'purchase_price', 'reading_progress', 'purchase_time']
    list_filter = ['access_type', 'purchase_time']
    search_fields = ['book_title', 'user_id']
    readonly_fields = ['id', 'purchase_time']
    ordering = ['-purchase_time']
    list_per_page = 25
    
    def get_username(self, obj):
        """获取用户名"""
        user = obj.user
        return user.username if user else f'用户ID:{obj.user_id}'
    get_username.short_description = '用户'
    
    fieldsets = (
        ('基本信息', {
            'fields': ('id', 'user_id', 'book_id', 'book_title')
        }),
        ('购买信息', {
            'fields': ('purchase_price', 'access_type', 'order_id', 'purchase_time')
        }),
        ('阅读信息', {
            'fields': ('last_read_time', 'reading_progress')
        })
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'name', 'username', 'balance', 'vip_level', 'status', 'register_time']
    list_filter = ['vip_level', 'status']
    search_fields = ['name', 'username']
    readonly_fields = ['user_id', 'register_time']
    ordering = ['-register_time']
    list_per_page = 25
    
    fieldsets = (
        ('基本信息', {
            'fields': ('user_id', 'name', 'username', 'password', 'avatar')
        }),
        ('账户信息', {
            'fields': ('balance', 'vip_level', 'status')
        }),
        ('扩展信息', {
            'fields': ('book_evaluations', 'collected_books', 'bookshelf_books', 'deleted_books', 'order_numbers', 'shopping_cart_id'),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('register_time', 'last_login_time'),
            'classes': ('collapse',)
        })
    )


@admin.register(BookOrder)
class BookOrderAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'customer_name', 'order_number', 'get_book_titles', 'book_count', 'order_amount', 'order_status', 'create_time']
    list_filter = ['order_status', 'create_time']
    search_fields = ['customer_name', 'order_number']
    readonly_fields = ['order_id', 'create_time']
    ordering = ['-create_time']
    list_per_page = 25
    
    def get_book_titles(self, obj):
        """获取订单中的书籍标题"""
        book_titles = obj.get_book_titles()
        if book_titles:
            return ', '.join(book_titles[:3])  # 最多显示3本书
        return '无书籍'
    get_book_titles.short_description = '书籍'
    
    fieldsets = (
        ('订单基本信息', {
            'fields': ('order_id', 'customer_name', 'order_number')
        }),
        ('订单内容', {
            'fields': ('order_content', 'book_count', 'order_amount')
        }),
        ('订单状态', {
            'fields': ('order_status', 'payment_method', 'create_time', 'payment_time', 'complete_time')
        })
    )


@admin.register(BookShoppingCart)
class BookShoppingCartAdmin(admin.ModelAdmin):
    list_display = ['cart_id', 'customer_name', 'cart_number', 'book_count', 'total_amount', 'create_time']
    list_filter = ['customer_name']
    search_fields = ['customer_name', 'cart_number']
    readonly_fields = ['cart_id', 'create_time', 'update_time']
    ordering = ['-update_time']
    list_per_page = 25


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['item_id', 'get_username', 'get_book_title', 'price', 'is_selected', 'create_time']
    list_filter = ['is_selected', 'create_time']
    search_fields = ['user__username', 'book__title']
    readonly_fields = ['item_id', 'create_time', 'update_time']
    ordering = ['-create_time']
    list_per_page = 25
    
    def get_username(self, obj):
        return obj.user.username if obj.user else '未知用户'
    get_username.short_description = '用户'
    
    def get_book_title(self, obj):
        return obj.book.title if obj.book else '未知书籍'
    get_book_title.short_description = '书籍'


@admin.register(BookEvaluate)
class BookEvaluateAdmin(admin.ModelAdmin):
    list_display = ['evaluate_id', 'customer_name', 'book_title', 'rating', 'create_time']
    list_filter = ['rating', 'book_title']
    search_fields = ['customer_name', 'book_title']
    readonly_fields = ['evaluate_id', 'create_time']
    ordering = ['-create_time']
    list_per_page = 25


@admin.register(Admin)
class AdminAdmin(admin.ModelAdmin):
    list_display = ['admin_id', 'username', 'email', 'status', 'create_time', 'last_login_time']
    list_filter = ['status']
    search_fields = ['username', 'email']
    readonly_fields = ['admin_id', 'create_time']
    ordering = ['-create_time']
    list_per_page = 25


@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = ['config_id', 'config_key', 'config_value', 'description', 'update_time']
    search_fields = ['config_key', 'description']
    readonly_fields = ['config_id', 'update_time']
    ordering = ['config_key']
    list_per_page = 25
    
    fieldsets = (
        ('配置信息', {
            'fields': ('config_id', 'config_key', 'config_value', 'description')
        }),
        ('时间信息', {
            'fields': ('update_time',),
            'classes': ('collapse',)
        })
    )