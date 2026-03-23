#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Django管理命令：系统性能优化
"""

from django.core.management.base import BaseCommand
from django.db import connection
from novel_app.models import (
    BookName, UserProfile, UserBookOwnership, BookOrder, CartItem
)


class Command(BaseCommand):
    help = '系统性能优化'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-indexes',
            action='store_true',
            help='创建性能优化索引'
        )
        parser.add_argument(
            '--analyze-queries',
            action='store_true',
            help='分析查询性能'
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='清理冗余数据'
        )

    def handle(self, *args, **options):
        self.stdout.write("开始系统性能优化")
        self.stdout.write("=" * 60)
        
        try:
            if options['create_indexes']:
                self.stdout.write("1. 创建性能优化索引...")
                self.create_performance_indexes()
            
            if options['analyze_queries']:
                self.stdout.write("\n2. 分析查询性能...")
                self.analyze_query_performance()
            
            if options['cleanup']:
                self.stdout.write("\n3. 清理冗余数据...")
                self.cleanup_redundant_data()
            
            if not any([options['create_indexes'], options['analyze_queries'], options['cleanup']]):
                self.stdout.write("请指定要执行的操作:")
                self.stdout.write("  --create-indexes: 创建性能优化索引")
                self.stdout.write("  --analyze-queries: 分析查询性能")
                self.stdout.write("  --cleanup: 清理冗余数据")
            
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write(self.style.SUCCESS("性能优化完成！"))
            self.stdout.write("=" * 60)
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"性能优化过程中出错: {e}"))
            import traceback
            self.stdout.write(traceback.format_exc())

    def create_performance_indexes(self):
        """创建性能优化索引"""
        with connection.cursor() as cursor:
            # 为常用查询创建复合索引
            indexes = [
                # 用户书籍拥有权表的复合索引
                "CREATE INDEX IF NOT EXISTS idx_ownership_user_access ON user_book_ownership (user_id, access_type)",
                "CREATE INDEX IF NOT EXISTS idx_ownership_book_access ON user_book_ownership (book_id, access_type)",
                "CREATE INDEX IF NOT EXISTS idx_ownership_read_time ON user_book_ownership (last_read_time DESC)",
                
                # 书籍表的复合索引
                "CREATE INDEX IF NOT EXISTS idx_book_category_rating ON book_name (category, rating DESC)",
                "CREATE INDEX IF NOT EXISTS idx_book_author_status ON book_name (author, status)",
                "CREATE INDEX IF NOT EXISTS idx_book_update_rating ON book_name (update_time DESC, rating DESC)",
                
                # 订单表的复合索引
                "CREATE INDEX IF NOT EXISTS idx_order_customer_status ON book_order (customer_name, order_status)",
                "CREATE INDEX IF NOT EXISTS idx_order_status_time ON book_order (order_status, create_time DESC)",
                
                # 购物车项目表的复合索引
                "CREATE INDEX IF NOT EXISTS idx_cart_user_selected ON cart_item (user_id, is_selected)",
                
                # 用户表的复合索引
                "CREATE INDEX IF NOT EXISTS idx_user_vip_status ON user (vip_level, status)",
            ]
            
            created_count = 0
            for index_sql in indexes:
                try:
                    cursor.execute(index_sql)
                    created_count += 1
                    index_name = index_sql.split('idx_')[1].split(' ')[0]
                    self.stdout.write(f"  ✓ 创建索引: idx_{index_name}")
                except Exception as e:
                    self.stdout.write(f"  ✗ 索引创建失败: {e}")
            
            self.stdout.write(f"  总计创建 {created_count} 个索引")

    def analyze_query_performance(self):
        """分析查询性能"""
        # 分析常用查询的性能
        queries = [
            {
                'name': '用户书籍访问权限查询',
                'query': 'SELECT COUNT(*) FROM user_book_ownership WHERE user_id = %s AND book_id = %s',
                'params': [1, 1]
            },
            {
                'name': 'VIP用户书籍列表查询',
                'query': '''
                    SELECT b.* FROM book_name b 
                    JOIN user_book_ownership o ON b.book_id = o.book_id 
                    WHERE o.user_id = %s AND o.access_type = 'vip_free'
                    ORDER BY o.last_read_time DESC LIMIT 10
                ''',
                'params': [1]
            },
            {
                'name': '用户订单历史查询',
                'query': '''
                    SELECT * FROM book_order 
                    WHERE customer_name = %s 
                    ORDER BY create_time DESC LIMIT 10
                ''',
                'params': ['测试用户']
            },
            {
                'name': '热门书籍查询',
                'query': '''
                    SELECT * FROM book_name 
                    WHERE rating >= 4.0 
                    ORDER BY collection_count DESC, rating DESC LIMIT 20
                ''',
                'params': []
            }
        ]
        
        with connection.cursor() as cursor:
            for query_info in queries:
                try:
                    # 执行EXPLAIN分析查询计划
                    explain_query = f"EXPLAIN {query_info['query']}"
                    cursor.execute(explain_query, query_info['params'])
                    result = cursor.fetchall()
                    
                    self.stdout.write(f"  查询: {query_info['name']}")
                    for row in result:
                        self.stdout.write(f"    {row}")
                    self.stdout.write("")
                    
                except Exception as e:
                    self.stdout.write(f"  查询分析失败 ({query_info['name']}): {e}")

    def cleanup_redundant_data(self):
        """清理冗余数据"""
        cleanup_count = 0
        
        # 1. 清理重复的用户书籍拥有权记录
        self.stdout.write("  清理重复的拥有权记录...")
        duplicate_ownership = UserBookOwnership.objects.values('user_id', 'book_id').annotate(
            count=models.Count('id')
        ).filter(count__gt=1)
        
        for dup in duplicate_ownership:
            # 保留最新的记录，删除其他的
            records = UserBookOwnership.objects.filter(
                user_id=dup['user_id'],
                book_id=dup['book_id']
            ).order_by('-purchase_time')
            
            for record in records[1:]:
                record.delete()
                cleanup_count += 1
        
        # 2. 清理孤立的购物车项目
        self.stdout.write("  清理孤立的购物车项目...")
        for item in CartItem.objects.all():
            try:
                # 检查用户和书籍是否存在
                user = item.user
                book = item.book
            except:
                item.delete()
                cleanup_count += 1
        
        # 3. 清理无效的JSON字段
        self.stdout.write("  清理无效的JSON字段...")
        for user in UserProfile.objects.all():
            json_fields = ['book_evaluations', 'collected_books', 'bookshelf_books', 'order_numbers']
            updated = False
            
            for field_name in json_fields:
                field_value = getattr(user, field_name)
                if field_value:
                    try:
                        json.loads(field_value)
                    except json.JSONDecodeError:
                        setattr(user, field_name, '[]')
                        updated = True
            
            if updated:
                user.save()
                cleanup_count += 1
        
        # 4. 清理负余额用户
        self.stdout.write("  修复负余额用户...")
        negative_balance_users = UserProfile.objects.filter(balance__lt=0)
        for user in negative_balance_users:
            user.balance = 0
            user.save()
            cleanup_count += 1
        
        # 5. 清理无效订单内容
        self.stdout.write("  清理无效订单内容...")
        for order in BookOrder.objects.all():
            if order.order_content:
                try:
                    content = json.loads(order.order_content)
                    if not isinstance(content, list):
                        order.order_content = '[]'
                        order.save()
                        cleanup_count += 1
                except json.JSONDecodeError:
                    order.order_content = '[]'
                    order.save()
                    cleanup_count += 1
        
        self.stdout.write(f"  总计清理 {cleanup_count} 条记录")

    def get_system_stats(self):
        """获取系统统计信息"""
        stats = {
            'users': UserProfile.objects.count(),
            'vip_users': UserProfile.objects.filter(vip_level='VIP').count(),
            'books': BookName.objects.count(),
            'ownership_records': UserBookOwnership.objects.count(),
            'orders': BookOrder.objects.count(),
            'cart_items': CartItem.objects.count(),
        }
        
        self.stdout.write("系统统计信息:")
        for key, value in stats.items():
            self.stdout.write(f"  {key}: {value}")
        
        return stats