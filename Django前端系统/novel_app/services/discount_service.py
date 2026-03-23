"""
折扣策略服务模块
实现批量购买折扣、VIP折扣等策略
"""
from decimal import Decimal
from typing import List, Dict, Tuple
from django.core.cache import cache
from ..models import SystemConfig, BookName
import logging

logger = logging.getLogger(__name__)


class DiscountStrategy:
    """折扣策略基类"""
    
    def calculate(self, books: List[BookName], user_vip_level: str) -> Tuple[Decimal, Decimal, str]:
        """
        计算折扣
        :param books: 书籍列表
        :param user_vip_level: 用户VIP等级
        :return: (原价, 折扣后价格, 折扣说明)
        """
        raise NotImplementedError


class BulkPurchaseDiscount(DiscountStrategy):
    """批量购买折扣策略"""
    
    # 默认折扣配置
    DEFAULT_DISCOUNTS = {
        1: 0.00,   # 1本书：无折扣
        2: 0.05,   # 2本书：95折
        3: 0.10,   # 3本书：9折
        5: 0.15,   # 5本书及以上：85折
        10: 0.20,  # 10本书及以上：8折
    }
    
    def __init__(self):
        self.discounts = self._load_discount_config()
    
    def _load_discount_config(self) -> Dict[int, float]:
        """从系统配置加载折扣策略"""
        cache_key = 'bulk_discount_config'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        try:
            config = SystemConfig.objects.filter(
                config_key__startswith='bulk_discount_'
            ).values_list('config_key', 'config_value')
            
            discounts = {}
            for key, value in config:
                # 解析配置键：bulk_discount_3 -> 3本书的折扣
                count = int(key.replace('bulk_discount_', ''))
                discounts[count] = float(value)
            
            if not discounts:
                discounts = self.DEFAULT_DISCOUNTS
            
            # 缓存5分钟
            cache.set(cache_key, discounts, 300)
            return discounts
            
        except Exception as e:
            logger.warning(f"加载折扣配置失败，使用默认配置: {e}")
            return self.DEFAULT_DISCOUNTS
    
    def calculate(self, books: List[BookName], user_vip_level: str) -> Tuple[Decimal, Decimal, str]:
        """计算批量购买折扣"""
        if not books:
            return Decimal('0.00'), Decimal('0.00'), '无商品'
        
        # 计算原价
        original_price = sum(Decimal(str(book.price)) for book in books)
        book_count = len(books)
        
        # 获取适用的折扣率
        discount_rate = self._get_discount_rate(book_count)
        
        # 计算折扣后价格
        final_price = original_price * (Decimal('1.00') - Decimal(str(discount_rate)))
        
        # 生成折扣说明
        if discount_rate > 0:
            discount_percent = int(discount_rate * 100)
            description = f"批量购买{book_count}本，享受{100-discount_percent}折优惠"
        else:
            description = f"购买{book_count}本书"
        
        return original_price, final_price, description
    
    def _get_discount_rate(self, book_count: int) -> float:
        """根据书籍数量获取折扣率"""
        # 找到适用的最大折扣
        applicable_discount = 0.0
        for count_threshold, discount in sorted(self.discounts.items()):
            if book_count >= count_threshold:
                applicable_discount = discount
        
        return applicable_discount


class VIPDiscount(DiscountStrategy):
    """VIP折扣策略"""
    
    VIP_DISCOUNT_RATE = 0.10  # VIP额外享受9折
    
    def calculate(self, books: List[BookName], user_vip_level: str) -> Tuple[Decimal, Decimal, str]:
        """VIP用户额外折扣"""
        if not books:
            return Decimal('0.00'), Decimal('0.00'), '无商品'
        
        original_price = sum(Decimal(str(book.price)) for book in books)
        
        if user_vip_level == 'VIP':
            final_price = original_price * Decimal('0.90')
            description = f"VIP会员专享9折优惠"
        else:
            final_price = original_price
            description = "普通用户价格"
        
        return original_price, final_price, description


class CombinedDiscountStrategy(DiscountStrategy):
    """组合折扣策略：批量购买 + VIP折扣"""
    
    def __init__(self):
        self.bulk_discount = BulkPurchaseDiscount()
    
    def calculate(self, books: List[BookName], user_vip_level: str) -> Tuple[Decimal, Decimal, str]:
        """计算组合折扣"""
        if not books:
            return Decimal('0.00'), Decimal('0.00'), '无商品'
        
        # 1. 先计算批量购买折扣
        original_price, bulk_price, bulk_desc = self.bulk_discount.calculate(books, user_vip_level)
        
        # 2. VIP用户在批量折扣基础上再享受额外折扣
        if user_vip_level == 'VIP':
            # VIP额外享受5%折扣
            vip_discount_rate = Decimal('0.05')
            final_price = bulk_price * (Decimal('1.00') - vip_discount_rate)
            
            # 计算总折扣率
            total_discount = ((original_price - final_price) / original_price * 100).quantize(Decimal('0.1'))
            description = f"{bulk_desc}，VIP会员再享95折，总计{total_discount}%优惠"
        else:
            final_price = bulk_price
            description = bulk_desc
        
        return original_price, final_price, description


class DiscountService:
    """折扣服务统一入口"""
    
    def __init__(self):
        self.strategy = CombinedDiscountStrategy()
    
    def calculate_discount(self, books: List[BookName], user_vip_level: str = '普通') -> Dict:
        """
        计算折扣
        :param books: 书籍列表
        :param user_vip_level: 用户VIP等级
        :return: 折扣信息字典
        """
        original_price, final_price, description = self.strategy.calculate(books, user_vip_level)
        
        discount_amount = original_price - final_price
        discount_rate = (discount_amount / original_price * 100) if original_price > 0 else Decimal('0.00')
        
        return {
            'original_price': float(original_price),
            'final_price': float(final_price),
            'discount_amount': float(discount_amount),
            'discount_rate': float(discount_rate.quantize(Decimal('0.01'))),
            'description': description,
            'book_count': len(books),
            'is_vip': user_vip_level == 'VIP'
        }
    
    @staticmethod
    def init_default_config():
        """初始化默认折扣配置到数据库"""
        default_configs = [
            ('bulk_discount_1', '0.00', '购买1本书的折扣率'),
            ('bulk_discount_2', '0.05', '购买2本书的折扣率（95折）'),
            ('bulk_discount_3', '0.10', '购买3本书的折扣率（9折）'),
            ('bulk_discount_5', '0.15', '购买5本书的折扣率（85折）'),
            ('bulk_discount_10', '0.20', '购买10本书及以上的折扣率（8折）'),
            ('vip_extra_discount', '0.05', 'VIP用户额外折扣率（95折）'),
        ]
        
        for key, value, desc in default_configs:
            SystemConfig.objects.get_or_create(
                config_key=key,
                defaults={'config_value': value, 'description': desc}
            )
        
        logger.info("折扣配置初始化完成")


# 全局折扣服务实例
discount_service = DiscountService()
