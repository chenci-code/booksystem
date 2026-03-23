from django.core.management.base import BaseCommand
from django.db.models import Count
from novel_app.models import UserProfile, BookName, UserBookOwnership, BookOrder
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '验证书籍拥有权数据的完整性'

    def handle(self, *args, **options):
        self.stdout.write('开始验证书籍拥有权数据完整性...')
        
        # 统计基础数据
        total_users = UserProfile.objects.count()
        vip_users_count = UserProfile.objects.filter(vip_level='VIP').count()
        regular_users_count = total_users - vip_users_count
        total_books = BookName.objects.count()
        total_ownership = UserBookOwnership.objects.count()
        
        self.stdout.write(f'用户统计: 总计 {total_users} 个用户 (VIP: {vip_users_count}, 普通: {regular_users_count})')
        self.stdout.write(f'书籍统计: 总计 {total_books} 本书籍')
        self.stdout.write(f'拥有权记录: 总计 {total_ownership} 条记录')
        
        # 检查VIP用户的书籍拥有权
        vip_users = UserProfile.objects.filter(vip_level='VIP')
        incomplete_vip_users = []
        
        for user in vip_users:
            owned_books_count = UserBookOwnership.objects.filter(user=user).count()
            if owned_books_count < total_books:
                incomplete_vip_users.append({
                    'user': user,
                    'owned_count': owned_books_count,
                    'missing_count': total_books - owned_books_count
                })
        
        if incomplete_vip_users:
            self.stdout.write(self.style.WARNING(f'发现 {len(incomplete_vip_users)} 个VIP用户的书籍拥有权不完整:'))
            for item in incomplete_vip_users:
                self.stdout.write(f'  - {item["user"].username}: 拥有 {item["owned_count"]} 本，缺少 {item["missing_count"]} 本')
        else:
            self.stdout.write(self.style.SUCCESS('所有VIP用户的书籍拥有权都是完整的'))
        
        # 检查访问类型统计
        access_type_stats = UserBookOwnership.objects.values('access_type').annotate(count=Count('id'))
        self.stdout.write('访问类型统计:')
        for stat in access_type_stats:
            self.stdout.write(f'  - {stat["access_type"]}: {stat["count"]} 条记录')
        
        # 检查重复记录
        duplicate_records = UserBookOwnership.objects.values('user', 'book').annotate(
            count=Count('id')
        ).filter(count__gt=1)
        
        if duplicate_records.exists():
            self.stdout.write(self.style.ERROR(f'发现 {duplicate_records.count()} 组重复的用户-书籍拥有权记录'))
            for record in duplicate_records[:10]:  # 只显示前10个
                user = UserProfile.objects.get(id=record['user'])
                book = BookName.objects.get(id=record['book'])
                self.stdout.write(f'  - 用户 {user.username} 对书籍 {book.title} 有 {record["count"]} 条记录')
        else:
            self.stdout.write(self.style.SUCCESS('没有发现重复的拥有权记录'))
        
        # 检查订单关联
        orders_with_ownership = BookOrder.objects.filter(
            order_status__in=['已支付', '已完成']
        ).count()
        
        ownership_with_orders = UserBookOwnership.objects.filter(
            access_type='purchased',
            order__isnull=False
        ).count()
        
        self.stdout.write(f'已支付/已完成订单: {orders_with_ownership} 个')
        self.stdout.write(f'有订单关联的拥有权记录: {ownership_with_orders} 条')
        
        # 检查孤立的拥有权记录（付费购买但没有订单关联）
        orphaned_ownership = UserBookOwnership.objects.filter(
            access_type='purchased',
            order__isnull=True
        ).count()
        
        if orphaned_ownership > 0:
            self.stdout.write(self.style.WARNING(f'发现 {orphaned_ownership} 条孤立的付费拥有权记录（没有订单关联）'))
        else:
            self.stdout.write(self.style.SUCCESS('所有付费拥有权记录都有正确的订单关联'))
        
        self.stdout.write(self.style.SUCCESS('数据完整性验证完成'))