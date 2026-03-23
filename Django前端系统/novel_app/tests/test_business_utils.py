"""
业务逻辑工具函数测试
测试 business_utils.py 中的核心业务逻辑
"""
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from novel_app.models import (
    BookName, UserProfile, UserBookOwnership, 
    BookOrder, CartItem
)
from novel_app.business_utils import (
    check_book_access,
    check_chapter_access,
    purchase_book,
    calculate_cart_total,
    update_reading_progress,
    generate_order_number
)


class CheckBookAccessTestCase(TestCase):
    """测试书籍访问权限检查功能"""
    
    def setUp(self):
        """测试前准备数据"""
        # 创建测试书籍
        self.book = BookName.objects.create(
            title='测试书籍',
            author='测试作者',
            category='玄幻',
            price=Decimal('19.99')
        )
        
        # 创建普通用户
        self.normal_user = UserProfile.objects.create(
            name='普通用户',
            username='normal_user',
            password='password123',
            vip_level='普通'
        )
        
        # 创建VIP用户
        self.vip_user = UserProfile.objects.create(
            name='VIP用户',
            username='vip_user',
            password='password123',
            vip_level='VIP',
            vip_expire_time=timezone.now() + timedelta(days=30)
        )
        
        # 创建禁用用户
        self.disabled_user = UserProfile.objects.create(
            name='禁用用户',
            username='disabled_user',
            password='password123',
            status='禁用'
        )
    
    def test_check_access_without_login(self):
        """测试未登录用户访问权限"""
        result = check_book_access(None, self.book)
        
        self.assertFalse(result['can_read'])
        self.assertTrue(result['can_purchase'])
        self.assertFalse(result['has_access'])
        self.assertEqual(result['message'], '请先登录')
    
    def test_check_access_disabled_user(self):
        """测试禁用用户访问权限"""
        result = check_book_access(self.disabled_user, self.book)
        
        self.assertFalse(result['can_read'])
        self.assertFalse(result['can_purchase'])
        self.assertEqual(result['message'], '账户已被禁用')
    
    def test_check_access_normal_user_without_purchase(self):
        """测试普通用户未购买书籍的访问权限"""
        result = check_book_access(self.normal_user, self.book)
        
        self.assertFalse(result['can_read'])
        self.assertTrue(result['can_purchase'])
        self.assertFalse(result['has_access'])
        self.assertEqual(result['message'], '需要购买')
    
    def test_check_access_normal_user_with_purchase(self):
        """测试普通用户已购买书籍的访问权限"""
        # 创建购买记录
        UserBookOwnership.objects.create(
            user_id=self.normal_user.user_id,
            book_id=self.book.book_id,
            book_title=self.book.title,
            purchase_price=Decimal('19.99'),
            access_type='purchased'
        )
        
        result = check_book_access(self.normal_user, self.book)
        
        self.assertTrue(result['can_read'])
        self.assertFalse(result['can_purchase'])  # 已购买不能再购买
        self.assertTrue(result['has_access'])
        self.assertEqual(result['message'], '已购买')
    
    def test_check_access_vip_user_without_purchase(self):
        """测试VIP用户未购买书籍的访问权限"""
        result = check_book_access(self.vip_user, self.book)
        
        self.assertTrue(result['can_read'])
        self.assertTrue(result['can_purchase'])  # VIP可以选择购买支持作者
        self.assertTrue(result['has_access'])
        self.assertTrue(result['is_vip'])
        self.assertEqual(result['access_type'], 'vip_free')
        self.assertEqual(result['message'], 'VIP用户免费阅读')


class CheckChapterAccessTestCase(TestCase):
    """测试章节访问权限检查功能"""
    
    def setUp(self):
        """测试前准备数据"""
        self.book = BookName.objects.create(
            title='测试书籍',
            author='测试作者',
            category='玄幻',
            price=Decimal('19.99')
        )
        
        self.user = UserProfile.objects.create(
            name='测试用户',
            username='test_user',
            password='password123'
        )
    
    def test_free_chapter_access_without_login(self):
        """测试未登录用户访问免费章节"""
        result = check_chapter_access(None, self.book, chapter_number=1)
        
        self.assertTrue(result['can_read'])
        self.assertTrue(result['is_free'])
        self.assertEqual(result['message'], '免费章节')
    
    def test_paid_chapter_access_without_login(self):
        """测试未登录用户访问付费章节"""
        result = check_chapter_access(None, self.book, chapter_number=3)
        
        self.assertFalse(result['can_read'])
        self.assertFalse(result['is_free'])
        self.assertEqual(result['message'], '请先登录')
    
    def test_paid_chapter_access_without_purchase(self):
        """测试未购买用户访问付费章节"""
        result = check_chapter_access(self.user, self.book, chapter_number=3)
        
        self.assertFalse(result['can_read'])
        self.assertFalse(result['is_free'])
        self.assertEqual(result['message'], '需要购买')


class PurchaseBookTestCase(TestCase):
    """测试书籍购买功能"""
    
    def setUp(self):
        """测试前准备数据"""
        self.book = BookName.objects.create(
            title='测试书籍',
            author='测试作者',
            category='玄幻',
            price=Decimal('19.99'),
            purchase_count=0
        )
        
        self.user = UserProfile.objects.create(
            name='测试用户',
            username='test_user',
            password='password123'
        )
    
    def test_purchase_book_success(self):
        """测试成功购买书籍"""
        result = purchase_book(
            user=self.user,
            book=self.book,
            price=19.99,
            access_type='purchased'
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['action'], 'purchased')
        self.assertIn('成功购买', result['message'])
        
        # 验证购买记录已创建
        ownership = UserBookOwnership.objects.filter(
            user_id=self.user.user_id,
            book_id=self.book.book_id
        ).first()
        self.assertIsNotNone(ownership)
        self.assertEqual(ownership.purchase_price, Decimal('19.99'))
        
        # 验证书籍购买量已增加
        self.book.refresh_from_db()
        self.assertEqual(self.book.purchase_count, 1)
    
    def test_purchase_book_already_owned(self):
        """测试重复购买书籍"""
        # 先购买一次
        purchase_book(self.user, self.book, 19.99)
        
        # 再次购买
        result = purchase_book(self.user, self.book, 19.99)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['action'], 'already_owned')
        self.assertIn('已经购买过', result['message'])


class CalculateCartTotalTestCase(TestCase):
    """测试购物车总价计算功能"""
    
    def setUp(self):
        """测试前准备数据"""
        self.user = UserProfile.objects.create(
            name='测试用户',
            username='test_user',
            password='password123'
        )
        
        self.book1 = BookName.objects.create(
            title='书籍1',
            author='作者1',
            category='玄幻',
            price=Decimal('19.99')
        )
        
        self.book2 = BookName.objects.create(
            title='书籍2',
            author='作者2',
            category='都市',
            price=Decimal('29.99')
        )
    
    def test_calculate_empty_cart(self):
        """测试空购物车"""
        result = calculate_cart_total(self.user)
        
        self.assertEqual(result['total_price'], Decimal('0.00'))
        self.assertEqual(result['book_count'], 0)
    
    def test_calculate_cart_with_selected_items(self):
        """测试计算选中商品总价"""
        CartItem.objects.create(
            user=self.user,
            book=self.book1,
            price=Decimal('19.99'),
            is_selected=True
        )
        CartItem.objects.create(
            user=self.user,
            book=self.book2,
            price=Decimal('29.99'),
            is_selected=True
        )
        
        result = calculate_cart_total(self.user, selected_only=True)
        
        self.assertEqual(result['total_price'], Decimal('49.98'))
        self.assertEqual(result['book_count'], 2)
    
    def test_calculate_cart_with_unselected_items(self):
        """测试只计算选中商品（排除未选中）"""
        CartItem.objects.create(
            user=self.user,
            book=self.book1,
            price=Decimal('19.99'),
            is_selected=True
        )
        CartItem.objects.create(
            user=self.user,
            book=self.book2,
            price=Decimal('29.99'),
            is_selected=False  # 未选中
        )
        
        result = calculate_cart_total(self.user, selected_only=True)
        
        self.assertEqual(result['total_price'], Decimal('19.99'))
        self.assertEqual(result['book_count'], 1)


class UpdateReadingProgressTestCase(TestCase):
    """测试阅读进度更新功能"""
    
    def setUp(self):
        """测试前准备数据"""
        self.user = UserProfile.objects.create(
            name='测试用户',
            username='test_user',
            password='password123'
        )
        
        self.book = BookName.objects.create(
            title='测试书籍',
            author='测试作者',
            category='玄幻',
            price=Decimal('19.99')
        )
        
        # 创建购买记录
        self.ownership = UserBookOwnership.objects.create(
            user_id=self.user.user_id,
            book_id=self.book.book_id,
            book_title=self.book.title,
            purchase_price=Decimal('19.99'),
            reading_progress=0
        )
    
    def test_update_progress_success(self):
        """测试成功更新阅读进度"""
        result = update_reading_progress(self.user, self.book, chapter_number=5)
        
        self.assertTrue(result)
        
        # 验证进度已更新
        self.ownership.refresh_from_db()
        self.assertEqual(self.ownership.reading_progress, 5)
        self.assertIsNotNone(self.ownership.last_read_time)
    
    def test_update_progress_not_increase(self):
        """测试不更新较小的进度值"""
        # 先设置进度为10
        self.ownership.reading_progress = 10
        self.ownership.save()
        
        # 尝试更新为5（较小值）
        result = update_reading_progress(self.user, self.book, chapter_number=5)
        
        self.assertFalse(result)
        
        # 验证进度未改变
        self.ownership.refresh_from_db()
        self.assertEqual(self.ownership.reading_progress, 10)


class GenerateOrderNumberTestCase(TestCase):
    """测试订单号生成功能"""
    
    def test_generate_order_number_format(self):
        """测试订单号格式"""
        order_number = generate_order_number()
        
        # 验证格式：ORD + 14位时间戳 + 4位随机数 = 21位
        self.assertTrue(order_number.startswith('ORD'))
        self.assertEqual(len(order_number), 21)
        self.assertTrue(order_number[3:].isdigit())
    
    def test_generate_order_number_uniqueness(self):
        """测试订单号唯一性"""
        order_numbers = set()
        
        # 生成100个订单号
        for _ in range(100):
            order_number = generate_order_number()
            order_numbers.add(order_number)
        
        # 验证没有重复
        self.assertEqual(len(order_numbers), 100)
