"""
业务逻辑工具模块
提供统一的业务逻辑处理函数
"""
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from .models import (
    BookName, UserProfile, UserBookOwnership, 
    BookOrder, CartItem
)
import logging

logger = logging.getLogger(__name__)


def check_book_access(user, book):
    """
    统一的书籍访问权限检查
    
    Args:
        user: UserProfile对象
        book: BookName对象
        
    Returns:
        dict: 包含访问权限信息的字典
    """
    if not user:
        return {
            'can_read': False,
            'can_purchase': True,
            'has_access': False,
            'is_vip': False,
            'access_type': 'none',
            'message': '请先登录'
        }
    
    # 检查用户状态
    if user.status == '禁用':
        return {
            'can_read': False,
            'can_purchase': False,
            'has_access': False,
            'is_vip': False,
            'access_type': 'none',
            'message': '账户已被禁用'
        }
    
    # 首先检查是否已购买（优先于VIP状态）
    ownership = UserBookOwnership.objects.filter(
        user_id=user.user_id,
        book_id=book.book_id
    ).first()
    
    if ownership:
        # 用户已购买，无论是否是VIP都显示已购买状态
        is_vip = user.is_vip()
        return {
            'can_read': True,
            'can_purchase': False,  # 已购买后不能再购买
            'has_access': True,
            'is_vip': is_vip,
            'access_type': ownership.access_type,
            'message': '已购买'
        }
    
    # VIP用户可以访问所有书籍（但未购买）
    is_vip = user.is_vip()
    if is_vip:
        return {
            'can_read': True,
            'can_purchase': True,  # VIP用户可以选择购买支持作者
            'has_access': True,
            'is_vip': True,
            'access_type': 'vip_free',
            'message': 'VIP用户免费阅读'
        }
    
    # 未购买
    return {
        'can_read': False,
        'can_purchase': True,
        'has_access': False,
        'is_vip': False,
        'access_type': 'none',
        'message': '需要购买'
    }


def check_chapter_access(user, book, chapter_number, free_chapters=2):
    """
    检查章节访问权限
    
    Args:
        user: UserProfile对象或None
        book: BookName对象
        chapter_number: 章节号
        free_chapters: 免费章节数，默认2章
        
    Returns:
        dict: 包含访问权限信息的字典
    """
    is_free_chapter = chapter_number <= free_chapters
    
    # 免费章节所有人都可以阅读
    if is_free_chapter:
        return {
            'can_read': True,
            'is_free': True,
            'message': '免费章节'
        }
    
    # 付费章节需要检查权限
    if not user:
        return {
            'can_read': False,
            'is_free': False,
            'message': '请先登录'
        }
    
    access_info = check_book_access(user, book)
    return {
        'can_read': access_info['has_access'],
        'is_free': False,
        'message': access_info['message']
    }


@transaction.atomic
def purchase_book(user, book, price, access_type='purchased', order_id=None):
    """
    购买书籍（事务安全）
    
    Args:
        user: UserProfile对象
        book: BookName对象
        price: 购买价格
        access_type: 访问类型，默认'purchased'
        order_id: 关联订单ID（可选）
        
    Returns:
        dict: 包含购买结果的字典
    """
    try:
        # 检查用户是否已经拥有该书籍
        existing_ownership = UserBookOwnership.objects.filter(
            user_id=user.user_id,
            book_id=book.book_id
        ).first()
        
        if existing_ownership:
            return {
                'success': False,
                'message': f'您已经购买过《{book.title}》了',
                'action': 'already_owned',
                'ownership_id': existing_ownership.id
            }
        
        # 创建新的拥有权记录
        ownership = UserBookOwnership.objects.create(
            user_id=user.user_id,
            book_id=book.book_id,
            book_title=book.title,
            access_type=access_type,
            purchase_price=Decimal(str(price)),
            purchase_time=timezone.now(),
            order_id=order_id
        )
        
        # 更新书籍购买量
        book.increment_purchase_count()
        
        return {
            'success': True,
            'message': f'成功购买《{book.title}》！',
            'action': 'purchased',
            'ownership_id': ownership.id
        }
        
    except Exception as e:
        logger.error(f"购买书籍失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            'success': False,
            'message': f'购买失败：{str(e)}',
            'action': 'error',
            'ownership_id': None
        }


def calculate_cart_total(user, selected_only=True):
    """
    计算购物车总价
    
    Args:
        user: UserProfile对象
        selected_only: 是否只计算选中的商品
        
    Returns:
        dict: 包含总价信息的字典
    """
    cart_items = CartItem.objects.filter(user=user)
    
    if selected_only:
        cart_items = cart_items.filter(is_selected=True)
    
    total_price = Decimal('0.00')
    book_count = 0
    
    for item in cart_items:
        total_price += item.price
        book_count += 1
    
    return {
        'total_price': total_price,
        'book_count': book_count,
        'items': cart_items
    }


def update_reading_progress(user, book, chapter_number):
    """
    更新阅读进度
    
    Args:
        user: UserProfile对象
        book: BookName对象
        chapter_number: 章节号
        
    Returns:
        bool: 是否更新成功
    """
    try:
        ownership = UserBookOwnership.objects.filter(
            user_id=user.user_id,
            book_id=book.book_id
        ).first()
        
        if ownership and chapter_number > (ownership.reading_progress or 0):
            ownership.reading_progress = chapter_number
            ownership.last_read_time = timezone.now()
            ownership.save(update_fields=['reading_progress', 'last_read_time'])
            return True
        
        return False
    except Exception as e:
        logger.error(f"更新阅读进度失败: {str(e)}")
        return False


def generate_order_number():
    """
    生成唯一订单号
    
    Returns:
        str: 订单号
    """
    import random
    import string
    from datetime import datetime
    
    # 格式：ORD + 年月日时分秒 + 4位随机数
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_str = ''.join(random.choices(string.digits, k=4))
    return f'ORD{timestamp}{random_str}'
