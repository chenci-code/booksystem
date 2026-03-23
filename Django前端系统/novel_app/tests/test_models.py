"""
数据模型测试
测试 models.py 中的模型方法和属性
"""
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from novel_app.models import (
    BookName, BookChapter, UserProfile, UserBookOwnership,
    BookOrder, CartItem, BookEvaluate, Admin
)


class BookNameModelTestCase(TestCase):
    """测试BookName模型"""
    
    def setUp(self):
        """测试前准备数据"""
        self.book = BookName.objects.create(
            title='测试书籍',
            author='测试作者',
            category='玄幻',
            price=Decimal('19.99'),
            original_price=Decimal('29.99'),
            discount_rate=Decimal('0.30'),
            rating=Decimal('4.50'),
            collection_count=1000,
            view_count=10000,
            purchase_count=500
        )
    
    def test_book_str_representation(self):
        """测试书籍字符串表示"""
        self.assertEqual(str(self.book), '测试书籍')
    
    def test_get_current_price_with_discount(self):
        """测试获取折扣后价格"""
        current_price = self.book.get_current_price()
        expected_price = float(self.book.price) * (1 - float(self.book.discount_rate))
        
        self.assertAlmostEqual(current_price, expected_price, places=2)
    
    def test_get_current_price_without_discount(self):
        """测试无折扣时的价格"""
        book = BookName.objects.create(
            title='无折扣书籍',
            author='作者',
            category='都市',
            price=Decimal('19.99'),
            discount_rate=Decimal('0.00')
        )
        
        current_price = book.get_current_price()
        
        self.assertEqual(current_price, float(book.price))
    
    def test_is_on_sale(self):
        """测试是否在打折"""
        self.assertTrue(self.book.is_on_sale())
        
        book_no_discount = BookName.objects.create(
            title='无折扣书籍',
            author='作者',
            category='都市',
            price=Decimal('19.99'),
            discount_rate=Decimal('0.00')
        )
        self.assertFalse(book_no_discount.is_on_sale())
    
    def test_get_discount_percentage(self):
        """测试获取折扣百分比"""
        percentage = self.book.get_discount_percentage()
        
        self.assertEqual(percentage, 30)
    
    def test_increment_view_count(self):
        """测试增加浏览量"""
        initial_count = self.book.view_count
        self.book.increment_view_count()
        
        self.book.refresh_from_db()
        self.assertEqual(self.book.view_count, initial_count + 1)
    
    def test_increment_purchase_count(self):
        """测试增加购买量"""
        initial_count = self.book.purchase_count
        self.book.increment_purchase_count()
        
        self.book.refresh_from_db()
        self.assertEqual(self.book.purchase_count, initial_count + 1)
    
    def test_is_completed_property(self):
        """测试是否完结属性"""
        self.book.status = '完结'
        self.book.save()
        
        self.assertTrue(self.book.is_completed)
        self.assertFalse(self.book.is_ongoing)
    
    def test_is_ongoing_property(self):
        """测试是否连载中属性"""
        self.book.status = '连载中'
        self.book.save()
        
        self.assertTrue(self.book.is_ongoing)
        self.assertFalse(self.book.is_completed)
    
    def test_popularity_score(self):
        """测试人气分数计算"""
        score = self.book.popularity_score
        
        # 验证分数在合理范围内
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 10)
    
    def test_tags_management(self):
        """测试标签管理功能"""
        # 添加标签
        self.book.add_tag('热门')
        self.book.add_tag('推荐')
        
        tags = self.book.get_tags()
        self.assertIn('热门', tags)
        self.assertIn('推荐', tags)
        
        # 移除标签
        self.book.remove_tag('热门')
        tags = self.book.get_tags()
        self.assertNotIn('热门', tags)
        self.assertIn('推荐', tags)


class UserProfileModelTestCase(TestCase):
    """测试UserProfile模型"""
    
    def setUp(self):
        """测试前准备数据"""
        self.user = UserProfile.objects.create(
            name='测试用户',
            username='test_user',
            password='password123'
        )
    
    def test_user_str_representation(self):
        """测试用户字符串表示"""
        self.assertEqual(str(self.user), '测试用户')
    
    def test_set_and_check_password(self):
        """测试密码设置和验证"""
        raw_password = 'new_password123'
        self.user.set_password(raw_password)
        self.user.save()
        
        # 验证正确密码
        self.assertTrue(self.user.check_password(raw_password))
        
        # 验证错误密码
        self.assertFalse(self.user.check_password('wrong_password'))
    
    def test_is_vip_with_valid_vip(self):
        """测试有效VIP用户"""
        self.user.vip_level = 'VIP'
        self.user.vip_expire_time = timezone.now() + timedelta(days=30)
        self.user.save()
        
        self.assertTrue(self.user.is_vip())
    
    def test_is_vip_with_expired_vip(self):
        """测试过期VIP用户"""
        self.user.vip_level = 'VIP'
        self.user.vip_expire_time = timezone.now() - timedelta(days=1)
        self.user.save()
        
        self.assertFalse(self.user.is_vip())
    
    def test_is_vip_with_permanent_vip(self):
        """测试永久VIP用户"""
        self.user.vip_level = 'VIP'
        self.user.vip_expire_time = None  # NULL表示永久VIP
        self.user.save()
        
        self.assertTrue(self.user.is_vip())
    
    def test_is_vip_with_normal_user(self):
        """测试普通用户"""
        self.user.vip_level = '普通'
        self.user.save()
        
        self.assertFalse(self.user.is_vip())
    
    def test_collected_books_management(self):
        """测试收藏书籍管理"""
        books_list = [1, 2, 3, 4, 5]
        self.user.set_collected_books(books_list)
        self.user.save()
        
        retrieved_books = self.user.get_collected_books()
        self.assertEqual(retrieved_books, books_list)
    
    def test_bookshelf_books_management(self):
        """测试书架书籍管理"""
        books_list = [10, 20, 30]
        self.user.set_bookshelf_books(books_list)
        self.user.save()
        
        retrieved_books = self.user.get_bookshelf_books()
        self.assertEqual(retrieved_books, books_list)


class UserBookOwnershipModelTestCase(TestCase):
    """测试UserBookOwnership模型"""
    
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
        
        self.ownership = UserBookOwnership.objects.create(
            user_id=self.user.user_id,
            book_id=self.book.book_id,
            book_title=self.book.title,
            purchase_price=Decimal('19.99'),
            access_type='purchased'
        )
    
    def test_ownership_str_representation(self):
        """测试拥有权字符串表示"""
        expected_str = f"用户{self.user.user_id} - {self.book.title} - 购买"
        self.assertEqual(str(self.ownership), expected_str)
    
    def test_user_property(self):
        """测试用户属性"""
        user = self.ownership.user
        
        self.assertIsNotNone(user)
        self.assertEqual(user.user_id, self.user.user_id)
    
    def test_book_property(self):
        """测试书籍属性"""
        book = self.ownership.book
        
        self.assertIsNotNone(book)
        self.assertEqual(book.book_id, self.book.book_id)


class BookOrderModelTestCase(TestCase):
    """测试BookOrder模型"""
    
    def setUp(self):
        """测试前准备数据"""
        self.order = BookOrder.objects.create(
            customer_name='测试用户',
            order_number='ORD20240101120000001',
            book_count=2,
            order_amount=Decimal('49.98'),
            order_status='待支付'
        )
    
    def test_order_str_representation(self):
        """测试订单字符串表示"""
        expected_str = f"{self.order.customer_name} - {self.order.order_number}"
        self.assertEqual(str(self.order), expected_str)
    
    def test_order_content_management(self):
        """测试订单内容管理"""
        content_list = [
            {'book_id': 1, 'book_title': '书籍1', 'price': 19.99},
            {'book_id': 2, 'book_title': '书籍2', 'price': 29.99}
        ]
        
        self.order.set_order_content(content_list)
        self.order.save()
        
        retrieved_content = self.order.get_order_content()
        self.assertEqual(len(retrieved_content), 2)
        self.assertEqual(retrieved_content[0]['book_title'], '书籍1')
    
    def test_get_book_titles(self):
        """测试获取订单中的书籍标题"""
        content_list = [
            {'book_id': 1, 'book_title': '书籍1', 'price': 19.99},
            {'book_id': 2, 'book_title': '书籍2', 'price': 29.99}
        ]
        
        self.order.set_order_content(content_list)
        self.order.save()
        
        titles = self.order.get_book_titles()
        self.assertEqual(len(titles), 2)
        self.assertIn('书籍1', titles)
        self.assertIn('书籍2', titles)


class CartItemModelTestCase(TestCase):
    """测试CartItem模型"""
    
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
        
        self.cart_item = CartItem.objects.create(
            user=self.user,
            book=self.book,
            price=Decimal('19.99'),
            is_selected=True
        )
    
    def test_cart_item_str_representation(self):
        """测试购物车项目字符串表示"""
        expected_str = f"{self.user.username} - {self.book.title}"
        self.assertEqual(str(self.cart_item), expected_str)
    
    def test_get_total_price(self):
        """测试获取项目总价"""
        total_price = self.cart_item.get_total_price()
        
        self.assertEqual(total_price, self.cart_item.price)
    
    def test_unique_constraint(self):
        """测试唯一约束（每个用户每本书只能有一个购物车项目）"""
        from django.db import IntegrityError
        
        with self.assertRaises(IntegrityError):
            CartItem.objects.create(
                user=self.user,
                book=self.book,
                price=Decimal('19.99')
            )


class BookEvaluateModelTestCase(TestCase):
    """测试BookEvaluate模型"""
    
    def setUp(self):
        """测试前准备数据"""
        self.evaluate = BookEvaluate.objects.create(
            customer_name='测试用户',
            book_title='测试书籍',
            rating=5,
            review_content='非常好看！'
        )
    
    def test_evaluate_str_representation(self):
        """测试评价字符串表示"""
        expected_str = f"{self.evaluate.customer_name} - {self.evaluate.book_title} - {self.evaluate.rating}星"
        self.assertEqual(str(self.evaluate), expected_str)
    
    def test_rating_validation(self):
        """测试评分验证（1-5星）"""
        from django.core.exceptions import ValidationError
        
        # 测试有效评分
        evaluate = BookEvaluate(
            customer_name='用户',
            book_title='书籍',
            rating=3
        )
        evaluate.full_clean()  # 应该不抛出异常
        
        # 测试无效评分（超出范围）
        evaluate_invalid = BookEvaluate(
            customer_name='用户',
            book_title='书籍',
            rating=6
        )
        with self.assertRaises(ValidationError):
            evaluate_invalid.full_clean()


class AdminModelTestCase(TestCase):
    """测试Admin模型"""
    
    def setUp(self):
        """测试前准备数据"""
        self.admin = Admin.objects.create(
            username='admin_user',
            password='admin123',
            email='admin@test.com'
        )
    
    def test_admin_str_representation(self):
        """测试管理员字符串表示"""
        self.assertEqual(str(self.admin), 'admin_user')
    
    def test_set_and_check_password(self):
        """测试管理员密码设置和验证"""
        raw_password = 'new_admin_password'
        self.admin.set_password(raw_password)
        self.admin.save()
        
        # 验证正确密码
        self.assertTrue(self.admin.check_password(raw_password))
        
        # 验证错误密码
        self.assertFalse(self.admin.check_password('wrong_password'))
