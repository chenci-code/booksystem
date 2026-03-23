from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Q
from django.contrib.auth.hashers import make_password, check_password
import json


class BookName(models.Model):
    """书籍信息表"""
    STATUS_CHOICES = [
        ('连载中', '连载中'),
        ('完结', '完结'),
        ('暂停', '暂停'),
    ]
    
    LANGUAGE_CHOICES = [
        ('zh-CN', '简体中文'),
        ('zh-TW', '繁体中文'),
        ('en', '英语'),
        ('ja', '日语'),
        ('ko', '韩语'),
    ]
    
    AGE_RATING_CHOICES = [
        ('G', '全年龄'),
        ('PG', '建议家长指导'),
        ('PG-13', '13岁以上'),
        ('R', '17岁以上'),
        ('NC-17', '18岁以上'),
    ]
    
    book_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200, verbose_name='书名')
    author = models.CharField(max_length=100, verbose_name='作者名')
    category = models.CharField(max_length=50, verbose_name='类别')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='连载中', verbose_name='状态')
    word_count = models.CharField(max_length=20, blank=True, null=True, verbose_name='字数')
    description = models.TextField(blank=True, null=True, verbose_name='简介')
    update_time = models.DateTimeField(blank=True, null=True, verbose_name='更新时间')
    book_url = models.URLField(blank=True, null=True, verbose_name='书籍URL')
    cover_url = models.URLField(blank=True, null=True, verbose_name='封面图片URL')
    qimao_book_id = models.CharField(max_length=50, blank=True, null=True, verbose_name='书籍ID（奇猫网）')
    chapter_count = models.IntegerField(default=0, verbose_name='章节数')
    chapter_list_api = models.URLField(blank=True, null=True, verbose_name='章节列表API')
    collection_count = models.IntegerField(default=0, verbose_name='收藏量')
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00, verbose_name='评分')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    # 新增扩展字段
    tags = models.JSONField(default=list, verbose_name='标签', help_text='书籍标签列表，JSON格式')
    isbn = models.CharField(max_length=20, blank=True, null=True, verbose_name='ISBN', help_text='国际标准书号')
    publisher = models.CharField(max_length=100, blank=True, null=True, verbose_name='出版社')
    publish_date = models.DateField(blank=True, null=True, verbose_name='出版日期')
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='zh-CN', verbose_name='语言')
    age_rating = models.CharField(max_length=10, choices=AGE_RATING_CHOICES, blank=True, null=True, verbose_name='年龄分级')
    
    # 统计字段
    view_count = models.IntegerField(default=0, verbose_name='浏览量', help_text='书籍页面浏览次数')
    download_count = models.IntegerField(default=0, verbose_name='下载量', help_text='书籍下载次数')
    purchase_count = models.IntegerField(default=0, verbose_name='购买量', help_text='书籍购买次数')
    
    # 管理字段
    is_featured = models.BooleanField(default=False, verbose_name='是否推荐', help_text='是否在首页推荐')
    is_hot = models.BooleanField(default=False, verbose_name='是否热门', help_text='是否标记为热门书籍')
    is_new = models.BooleanField(default=False, verbose_name='是否新书', help_text='是否标记为新书')
    sort_order = models.IntegerField(default=0, verbose_name='排序权重', help_text='数值越大排序越靠前')
    
    # 价格字段
    price = models.DecimalField(max_digits=8, decimal_places=2, default=9.99, verbose_name='价格')
    original_price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, verbose_name='原价')
    discount_rate = models.DecimalField(max_digits=3, decimal_places=2, default=0.00, verbose_name='折扣率', help_text='0.00-1.00之间')
    
    class Meta:
        db_table = 'book_name'
        verbose_name = '书籍信息'
        verbose_name_plural = '书籍信息'
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['author']),
            models.Index(fields=['status']),
            models.Index(fields=['rating']),
            models.Index(fields=['collection_count']),
            # 新增索引
            models.Index(fields=['view_count']),
            models.Index(fields=['purchase_count']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['is_hot']),
            models.Index(fields=['is_new']),
            models.Index(fields=['sort_order']),
            models.Index(fields=['price']),
            models.Index(fields=['language']),
            models.Index(fields=['age_rating']),
            models.Index(fields=['publisher']),
            # 复合索引
            models.Index(fields=['is_featured', 'sort_order']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['rating', 'collection_count']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['title', 'author'], name='unique_book_title_author')
        ]
    
    def __str__(self):
        return self.title
    
    def get_tags(self):
        """获取标签列表"""
        if isinstance(self.tags, list):
            return self.tags
        return []
    
    def set_tags(self, tags_list):
        """设置标签列表"""
        self.tags = tags_list if isinstance(tags_list, list) else []
    
    def add_tag(self, tag):
        """添加标签"""
        tags = self.get_tags()
        if tag not in tags:
            tags.append(tag)
            self.set_tags(tags)
    
    def remove_tag(self, tag):
        """移除标签"""
        tags = self.get_tags()
        if tag in tags:
            tags.remove(tag)
            self.set_tags(tags)
    
    def get_current_price(self):
        """获取当前价格（考虑折扣）"""
        if self.discount_rate > 0:
            return float(self.price) * (1 - float(self.discount_rate))
        return float(self.price)
    
    def is_on_sale(self):
        """是否在打折"""
        return self.discount_rate > 0
    
    def get_discount_percentage(self):
        """获取折扣百分比"""
        if self.discount_rate > 0:
            return int(float(self.discount_rate) * 100)
        return 0
    
    def increment_view_count(self):
        """增加浏览量"""
        self.view_count += 1
        self.save(update_fields=['view_count'])
    
    def increment_purchase_count(self):
        """增加购买量"""
        self.purchase_count += 1
        self.save(update_fields=['purchase_count'])
    
    @property
    def is_completed(self):
        """是否完结"""
        return self.status == '完结'
    
    @property
    def is_ongoing(self):
        """是否连载中"""
        return self.status == '连载中'
    
    @property
    def popularity_score(self):
        """人气分数（综合评分）"""
        # 简单的人气计算公式
        score = (
            float(self.rating) * 0.3 +
            min(self.collection_count / 1000, 10) * 0.2 +
            min(self.view_count / 10000, 10) * 0.2 +
            min(self.purchase_count / 100, 10) * 0.3
        )
        return round(score, 2)


class BookChapter(models.Model):
    """书籍章节表"""
    chapter_id = models.AutoField(primary_key=True)
    book_title = models.CharField(max_length=200, verbose_name='书名')
    chapter_number = models.IntegerField(verbose_name='第几章')
    chapter_title = models.CharField(max_length=200, verbose_name='章节名')
    chapter_content = models.TextField(blank=True, null=True, verbose_name='章节内容')
    content_file_path = models.CharField(max_length=500, blank=True, null=True, verbose_name='内容文件路径')
    word_count = models.IntegerField(default=0, verbose_name='章节字数')
    is_crawled = models.BooleanField(default=False, verbose_name='是否已爬取')
    crawl_time = models.DateTimeField(blank=True, null=True, verbose_name='爬取时间')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        db_table = 'book_chapter'
        verbose_name = '书籍章节'
        verbose_name_plural = '书籍章节'
        indexes = [
            models.Index(fields=['book_title']),
            models.Index(fields=['chapter_number']),
            models.Index(fields=['is_crawled']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['book_title', 'chapter_number'], name='unique_book_chapter')
        ]
    
    def __str__(self):
        return f"{self.book_title} - 第{self.chapter_number}章 {self.chapter_title}"



class UserProfile(models.Model):
    """用户信息表"""
    STATUS_CHOICES = [
        ('正常', '正常'),
        ('禁用', '禁用'),
    ]
    
    VIP_LEVEL_CHOICES = [
        ('普通', '普通用户'),
        ('VIP', 'VIP用户'),
    ]
    
    user_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, verbose_name='姓名')
    username = models.CharField(max_length=50, unique=True, verbose_name='账号')
    password = models.CharField(max_length=255, verbose_name='密码')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='头像')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='余额')
    book_evaluations = models.TextField(blank=True, null=True, verbose_name='书籍评价（JSON格式）')
    collected_books = models.TextField(blank=True, null=True, verbose_name='收藏书籍（JSON格式）')
    bookshelf_books = models.TextField(blank=True, null=True, verbose_name='书架书籍（JSON格式）')
    deleted_books = models.TextField(blank=True, null=True, verbose_name='已删除书籍（JSON格式）')
    order_numbers = models.TextField(blank=True, null=True, verbose_name='订单号（JSON格式）')
    shopping_cart_id = models.CharField(max_length=100, blank=True, null=True, verbose_name='购物车编号')
    vip_level = models.CharField(max_length=10, choices=VIP_LEVEL_CHOICES, default='普通', verbose_name='VIP等级')
    vip_expire_time = models.DateTimeField(blank=True, null=True, verbose_name='VIP到期时间')
    register_time = models.DateTimeField(auto_now_add=True, verbose_name='注册时间')
    last_login_time = models.DateTimeField(blank=True, null=True, verbose_name='最后登录时间')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='正常', verbose_name='状态')
    
    class Meta:
        db_table = 'user'
        verbose_name = '用户信息'
        verbose_name_plural = '用户信息'
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['name']),
            models.Index(fields=['vip_level']),
        ]
    
    def __str__(self):
        return self.name
    
    def get_collected_books(self):
        """获取收藏的书籍列表"""
        if self.collected_books:
            try:
                return json.loads(self.collected_books)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_collected_books(self, books_list):
        """设置收藏的书籍列表"""
        self.collected_books = json.dumps(books_list, ensure_ascii=False)
    
    def get_bookshelf_books(self):
        """获取书架书籍列表"""
        if self.bookshelf_books:
            try:
                return json.loads(self.bookshelf_books)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_bookshelf_books(self, books_list):
        """设置书架书籍列表"""
        self.bookshelf_books = json.dumps(books_list, ensure_ascii=False)
    
    def get_deleted_books(self):
        """获取已删除的书籍列表"""
        if self.deleted_books:
            try:
                return json.loads(self.deleted_books)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_deleted_books(self, books_list):
        """设置已删除的书籍列表"""
        self.deleted_books = json.dumps(books_list, ensure_ascii=False)
    
    def set_password(self, raw_password):
        """设置密码（使用Django哈希加密）"""
        self.password = make_password(raw_password)
    
    def check_password(self, raw_password):
        """验证密码（使用Django哈希验证）"""
        return check_password(raw_password, self.password)
    
    def is_vip(self):
        """检查用户是否是VIP（检查VIP等级和到期时间）"""
        if self.vip_level != 'VIP':
            return False
        # 如果vip_expire_time为NULL，表示永久VIP
        if not self.vip_expire_time:
            return True
        from django.utils import timezone
        return timezone.now() < self.vip_expire_time
    
    def get_vip_status_display(self):
        """获取VIP状态显示文本"""
        if self.is_vip():
            from django.utils import timezone
            from django.utils.dateformat import format
            return f"VIP会员（到期时间：{format(self.vip_expire_time, 'Y-m-d H:i')}）"
        else:
            return "不是VIP"


class UserBookOwnership(models.Model):
    """用户书籍拥有权表 - 整本购买模式核心表"""
    ACCESS_TYPE_CHOICES = [
        ('purchased', '购买'),
        ('vip_free', 'VIP免费'),
        ('vip_support', 'VIP支持作者'),
    ]
    
    id = models.AutoField(primary_key=True)
    user_id = models.IntegerField(verbose_name='用户ID')
    book_id = models.IntegerField(verbose_name='书籍ID')
    book_title = models.CharField(max_length=200, verbose_name='书名')
    purchase_time = models.DateTimeField(auto_now_add=True, verbose_name='购买时间')
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='购买价格')
    order_id = models.IntegerField(blank=True, null=True, verbose_name='关联订单ID')
    access_type = models.CharField(
        max_length=20, 
        choices=ACCESS_TYPE_CHOICES, 
        default='purchased', 
        verbose_name='访问类型'
    )
    last_read_time = models.DateTimeField(blank=True, null=True, verbose_name='最后阅读时间')
    reading_progress = models.IntegerField(default=0, verbose_name='阅读进度（章节数）')
    
    class Meta:
        db_table = 'user_book_ownership'
        verbose_name = '用户书籍拥有权'
        verbose_name_plural = '用户书籍拥有权'
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['book_id']),
            models.Index(fields=['user_id', 'book_id']),
            models.Index(fields=['access_type']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['user_id', 'book_id'], name='unique_user_book_ownership')
        ]
    
    def __str__(self):
        return f"用户{self.user_id} - {self.book_title} - {self.get_access_type_display()}"
    
    @property
    def user(self):
        """获取关联的用户对象"""
        try:
            return UserProfile.objects.get(user_id=self.user_id)
        except UserProfile.DoesNotExist:
            return None
    
    @property
    def book(self):
        """获取关联的书籍对象"""
        try:
            return BookName.objects.get(book_id=self.book_id)
        except BookName.DoesNotExist:
            return None


class BookOrderManager(models.Manager):
    """BookOrder自定义管理器"""
    
    def by_status(self, status):
        """按状态筛选订单"""
        return self.filter(order_status=status)
    
    def recent(self, limit=10):
        """获取最近的订单"""
        return self.order_by('-create_time')[:limit]
    
    def search(self, query):
        """搜索订单"""
        return self.filter(
            Q(customer_name__icontains=query) | 
            Q(order_number__icontains=query)
        )


class BookOrder(models.Model):
    """数字内容订单表 - 整本书籍购买模式"""
    STATUS_CHOICES = [
        ('待支付', '待支付'),
        ('已支付', '已支付'),
        ('已取消', '已取消'),
    ]
    
    order_id = models.AutoField(primary_key=True)
    customer_name = models.CharField(max_length=100, verbose_name='用户名')
    order_number = models.CharField(max_length=50, unique=True, verbose_name='订单号')
    order_content = models.TextField(blank=True, null=True, verbose_name='订单内容（书籍信息JSON）')
    book_count = models.IntegerField(default=0, verbose_name='书籍数量', db_column='chapter_count')  # 字段名已修正，但数据库列名保持不变以兼容现有数据
    order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='实际支付金额')
    payment_method = models.CharField(max_length=20, default='余额', verbose_name='支付方式')
    order_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='待支付', verbose_name='订单状态')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    payment_time = models.DateTimeField(blank=True, null=True, verbose_name='支付时间')
    complete_time = models.DateTimeField(blank=True, null=True, verbose_name='完成时间')
    
    # 使用自定义管理器
    objects = BookOrderManager()
    
    class Meta:
        db_table = 'book_order'
        verbose_name = '数字内容订单'
        verbose_name_plural = '数字内容订单'
        indexes = [
            models.Index(fields=['customer_name']),
            models.Index(fields=['order_number']),
            models.Index(fields=['order_status']),
            models.Index(fields=['create_time']),
        ]
    
    def __str__(self):
        return f"{self.customer_name} - {self.order_number}"
    
    def get_order_content(self):
        """获取订单内容"""
        if self.order_content:
            try:
                return json.loads(self.order_content)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_order_content(self, content_list):
        """设置订单内容"""
        self.order_content = json.dumps(content_list, ensure_ascii=False)
    
    def get_book_titles(self):
        """获取订单中的所有书籍标题"""
        content = self.get_order_content()
        if content:
            return [item.get('book_title', '未知书籍') for item in content]
        return []


class BookShoppingCart(models.Model):
    """数字内容购物车表 - 整本书籍购买模式"""
    cart_id = models.AutoField(primary_key=True)
    customer_name = models.CharField(max_length=100, verbose_name='用户名')
    cart_number = models.CharField(max_length=100, unique=True, verbose_name='购物车编号')
    cart_content = models.TextField(blank=True, null=True, verbose_name='购物车内容（书籍信息JSON）')
    book_count = models.IntegerField(default=0, verbose_name='书籍数量')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='总金额')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'book_shoppingcart'
        verbose_name = '数字内容购物车'
        verbose_name_plural = '数字内容购物车'
        indexes = [
            models.Index(fields=['customer_name']),
            models.Index(fields=['cart_number']),
        ]
    
    def __str__(self):
        return f"{self.customer_name} - {self.cart_number}"
    
    def get_cart_content(self):
        """获取购物车内容"""
        if self.cart_content:
            try:
                return json.loads(self.cart_content)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_cart_content(self, content_list):
        """设置购物车内容"""
        self.cart_content = json.dumps(content_list, ensure_ascii=False)


class CartItem(models.Model):
    """购物车项目表 - 用于管理购物车中的具体书籍（单本书籍，每本书仅存1份）"""
    item_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name='用户')
    book = models.ForeignKey(BookName, on_delete=models.CASCADE, verbose_name='书籍')
    price = models.DecimalField(max_digits=8, decimal_places=2, default=9.99, verbose_name='书籍价格')
    is_selected = models.BooleanField(default=True, verbose_name='是否选中')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='添加时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'cart_item'
        verbose_name = '购物车项目'
        verbose_name_plural = '购物车项目'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['book']),
        ]
        constraints = [
            # 确保每个用户每本书在购物车中仅存1份（唯一存在）
            models.UniqueConstraint(fields=['user', 'book'], name='unique_cart_item')
        ]

    def __str__(self):
        return f"{self.user.username} - {self.book.title}"

    def get_total_price(self):
        """获取该项目总价（整本书价格，不支持数量拆分）"""
        return self.price


class BookEvaluate(models.Model):
    """书籍评价表"""
    evaluate_id = models.AutoField(primary_key=True)
    customer_name = models.CharField(max_length=100, verbose_name='姓名')
    book_title = models.CharField(max_length=200, verbose_name='书名')
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='对应评分'
    )
    review_content = models.TextField(blank=True, null=True, verbose_name='评价内容')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        db_table = 'book_evaluate'
        verbose_name = '书籍评价'
        verbose_name_plural = '书籍评价'
        indexes = [
            models.Index(fields=['customer_name']),
            models.Index(fields=['book_title']),
            models.Index(fields=['rating']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['customer_name', 'book_title'], name='unique_user_book_evaluate')
        ]
    
    def __str__(self):
        return f"{self.customer_name} - {self.book_title} - {self.rating}星"


class Admin(models.Model):
    """管理员表 - 统一管理员类型"""
    STATUS_CHOICES = [
        ('正常', '正常'),
        ('禁用', '禁用'),
    ]
    
    admin_id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=50, unique=True, verbose_name='用户名')
    password = models.CharField(max_length=255, verbose_name='密码')
    email = models.EmailField(unique=True, verbose_name='邮箱')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    last_login_time = models.DateTimeField(blank=True, null=True, verbose_name='最后登录时间')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='正常', verbose_name='状态')
    
    class Meta:
        db_table = 'admins'
        verbose_name = '管理员'
        verbose_name_plural = '管理员'
    
    def __str__(self):
        return self.username
    
    def set_password(self, raw_password):
        """设置密码（使用Django哈希加密）"""
        self.password = make_password(raw_password)
    
    def check_password(self, raw_password):
        """验证密码（使用Django哈希验证）"""
        return check_password(raw_password, self.password)


class SystemConfig(models.Model):
    """系统配置表"""
    config_id = models.AutoField(primary_key=True)
    config_key = models.CharField(max_length=100, unique=True, verbose_name='配置键')
    config_value = models.TextField(blank=True, null=True, verbose_name='配置值')
    description = models.CharField(max_length=255, blank=True, null=True, verbose_name='描述')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'system_config'
        verbose_name = '系统配置'
        verbose_name_plural = '系统配置'
    
    def __str__(self):
        return self.config_key


class AdminOperationLog(models.Model):
    """管理员操作日志表"""
    OPERATION_CHOICES = [
        ('create', '创建'),
        ('update', '更新'),
        ('delete', '删除'),
        ('batch_update', '批量更新'),
        ('batch_delete', '批量删除'),
        ('import', '导入'),
        ('export', '导出'),
        ('upload', '上传'),
        ('login', '登录'),
        ('logout', '退出'),
    ]
    
    TARGET_TYPE_CHOICES = [
        ('book', '书籍'),
        ('user', '用户'),
        ('order', '订单'),
        ('file', '文件'),
        ('system', '系统'),
    ]
    
    log_id = models.AutoField(primary_key=True)
    admin_id = models.IntegerField(verbose_name='管理员ID')
    admin_username = models.CharField(max_length=50, verbose_name='管理员用户名')
    operation_type = models.CharField(max_length=20, choices=OPERATION_CHOICES, verbose_name='操作类型')
    target_type = models.CharField(max_length=20, choices=TARGET_TYPE_CHOICES, verbose_name='目标类型')
    target_id = models.IntegerField(blank=True, null=True, verbose_name='目标ID')
    target_title = models.CharField(max_length=200, blank=True, null=True, verbose_name='目标标题')
    operation_details = models.JSONField(default=dict, verbose_name='操作详情')
    ip_address = models.GenericIPAddressField(verbose_name='IP地址')
    user_agent = models.TextField(blank=True, null=True, verbose_name='用户代理')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='操作时间')
    
    class Meta:
        db_table = 'admin_operation_log'
        verbose_name = '管理员操作日志'
        verbose_name_plural = '管理员操作日志'
        indexes = [
            models.Index(fields=['admin_id']),
            models.Index(fields=['admin_username']),
            models.Index(fields=['operation_type']),
            models.Index(fields=['target_type']),
            models.Index(fields=['target_type', 'target_id']),
            models.Index(fields=['create_time']),
            models.Index(fields=['admin_id', 'create_time']),
            models.Index(fields=['operation_type', 'create_time']),
        ]
        ordering = ['-create_time']
    
    def __str__(self):
        return f"{self.admin_username} - {self.get_operation_type_display()} - {self.create_time.strftime('%Y-%m-%d %H:%M:%S')}"
    
    def get_operation_details(self):
        """获取操作详情"""
        if isinstance(self.operation_details, dict):
            return self.operation_details
        return {}
    
    def set_operation_details(self, details_dict):
        """设置操作详情"""
        self.operation_details = details_dict if isinstance(details_dict, dict) else {}
    
    @property
    def operation_summary(self):
        """操作摘要"""
        target_info = f"{self.get_target_type_display()}"
        if self.target_title:
            target_info += f"《{self.target_title}》"
        elif self.target_id:
            target_info += f"(ID: {self.target_id})"
        
        return f"{self.get_operation_type_display()}{target_info}"
    
    @classmethod
    def log_book_operation(cls, admin_id, admin_username, operation_type, 
                          book_id=None, book_title='', old_data=None, 
                          new_data=None, ip_address='', user_agent=''):
        """记录书籍操作日志的便捷方法"""
        details = {
            'old_data': old_data or {},
            'new_data': new_data or {},
        }
        
        return cls.objects.create(
            admin_id=admin_id,
            admin_username=admin_username,
            operation_type=operation_type,
            target_type='book',
            target_id=book_id,
            target_title=book_title,
            operation_details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @classmethod
    def log_batch_operation(cls, admin_id, admin_username, operation_type, 
                           target_type, target_ids, operation_result, 
                           ip_address='', user_agent=''):
        """记录批量操作日志的便捷方法"""
        details = {
            'target_ids': target_ids,
            'target_count': len(target_ids),
            'operation_result': operation_result,
        }
        
        return cls.objects.create(
            admin_id=admin_id,
            admin_username=admin_username,
            operation_type=operation_type,
            target_type=target_type,
            operation_details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )


class BookFile(models.Model):
    """书籍文件管理表"""
    FILE_TYPE_CHOICES = [
        ('cover', '封面图片'),
        ('thumbnail_small', '小缩略图'),
        ('thumbnail_medium', '中等缩略图'),
        ('thumbnail_large', '大缩略图'),
        ('content', '内容文件'),
        ('attachment', '附件'),
    ]
    
    file_id = models.AutoField(primary_key=True)
    book = models.ForeignKey(BookName, on_delete=models.CASCADE, verbose_name='关联书籍')
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES, verbose_name='文件类型')
    file_name = models.CharField(max_length=255, verbose_name='文件名')
    original_name = models.CharField(max_length=255, verbose_name='原始文件名')
    file_path = models.CharField(max_length=500, verbose_name='文件路径')
    file_url = models.URLField(blank=True, null=True, verbose_name='文件访问URL')
    file_size = models.IntegerField(verbose_name='文件大小（字节）')
    mime_type = models.CharField(max_length=100, verbose_name='MIME类型')
    
    # 图片特有字段
    image_width = models.IntegerField(blank=True, null=True, verbose_name='图片宽度')
    image_height = models.IntegerField(blank=True, null=True, verbose_name='图片高度')
    
    # 管理字段
    upload_admin_id = models.IntegerField(verbose_name='上传管理员ID')
    upload_admin_username = models.CharField(max_length=50, verbose_name='上传管理员用户名')
    upload_time = models.DateTimeField(auto_now_add=True, verbose_name='上传时间')
    is_active = models.BooleanField(default=True, verbose_name='是否有效')
    
    class Meta:
        db_table = 'book_file'
        verbose_name = '书籍文件'
        verbose_name_plural = '书籍文件'
        indexes = [
            models.Index(fields=['book']),
            models.Index(fields=['file_type']),
            models.Index(fields=['upload_time']),
            models.Index(fields=['is_active']),
            models.Index(fields=['book', 'file_type']),
            models.Index(fields=['upload_admin_id']),
        ]
        ordering = ['-upload_time']
    
    def __str__(self):
        return f"{self.book.title} - {self.get_file_type_display()} - {self.file_name}"
    
    @property
    def file_size_human(self):
        """人类可读的文件大小"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    @property
    def is_image(self):
        """是否是图片文件"""
        return self.mime_type.startswith('image/')
    
    @property
    def image_dimensions(self):
        """图片尺寸"""
        if self.is_image and self.image_width and self.image_height:
            return f"{self.image_width}x{self.image_height}"
        return ""
    
    def get_absolute_url(self):
        """获取文件的绝对URL"""
        if self.file_url:
            return self.file_url
        # 如果没有URL，可以根据file_path生成
        from django.conf import settings
        return f"{settings.MEDIA_URL}{self.file_path}"
    
    @classmethod
    def create_from_upload(cls, book, file_type, file_info, admin_id, admin_username):
        """从上传信息创建文件记录的便捷方法"""
        return cls.objects.create(
            book=book,
            file_type=file_type,
            file_name=file_info.get('saved_name', ''),
            original_name=file_info.get('original_name', ''),
            file_path=file_info.get('file_path', ''),
            file_url=file_info.get('file_url', ''),
            file_size=file_info.get('file_size', 0),
            mime_type=file_info.get('mime_type', ''),
            image_width=file_info.get('width', None),
            image_height=file_info.get('height', None),
            upload_admin_id=admin_id,
            upload_admin_username=admin_username,
        )
    
    def soft_delete(self):
        """软删除文件记录"""
        self.is_active = False
        self.save(update_fields=['is_active'])
    
    def restore(self):
        """恢复文件记录"""
        self.is_active = True
        self.save(update_fields=['is_active'])