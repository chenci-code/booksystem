from django.core.management.base import BaseCommand
from django.utils import timezone
from novel_app.models import UserProfile, BookName, UserBookOwnership
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '迁移到整本书籍购买模式，为VIP用户创建书籍拥有权记录'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只显示将要执行的操作，不实际执行',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('这是一次试运行，不会实际修改数据'))
        
        # 获取所有VIP用户
        vip_users = UserProfile.objects.filter(vip_level='VIP')
        self.stdout.write(f'找到 {vip_users.count()} 个VIP用户')
        
        # 获取所有书籍
        all_books = BookName.objects.all()
        self.stdout.write(f'找到 {all_books.count()} 本书籍')
        
        total_created = 0
        
        for user in vip_users:
            self.stdout.write(f'处理VIP用户: {user.username} ({user.name})')
            
            # 获取用户已有的书籍拥有权记录
            existing_books = UserBookOwnership.objects.filter(user=user).values_list('book_id', flat=True)
            
            # 为用户创建缺失的书籍拥有权记录
            books_to_create = all_books.exclude(book_id__in=existing_books)
            
            if not dry_run:
                ownership_records = []
                for book in books_to_create:
                    ownership_records.append(UserBookOwnership(
                        user=user,
                        book=book,
                        purchase_time=timezone.now(),
                        purchase_price=0.00,
                        access_type='vip_free'
                    ))
                
                if ownership_records:
                    UserBookOwnership.objects.bulk_create(ownership_records, ignore_conflicts=True)
                    created_count = len(ownership_records)
                    total_created += created_count
                    self.stdout.write(f'  为用户 {user.username} 创建了 {created_count} 条书籍拥有权记录')
                else:
                    self.stdout.write(f'  用户 {user.username} 已拥有所有书籍的访问权限')
            else:
                self.stdout.write(f'  将为用户 {user.username} 创建 {books_to_create.count()} 条书籍拥有权记录')
        
        if dry_run:
            self.stdout.write(self.style.SUCCESS('试运行完成'))
        else:
            self.stdout.write(self.style.SUCCESS(f'迁移完成，总共创建了 {total_created} 条VIP用户书籍拥有权记录'))