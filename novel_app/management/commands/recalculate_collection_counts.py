from django.core.management.base import BaseCommand
from novel_app.models import BookName, UserProfile
import json
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '重新计算所有书籍的收藏数量（基于用户收藏数据）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只显示将要更新的数据，不实际修改',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('运行在干运行模式，不会实际修改数据'))
        
        self.stdout.write('开始重新计算书籍收藏数量...')
        
        # 统计每本书的收藏数量
        book_collection_counts = {}
        total_collections = 0
        
        # 遍历所有用户，统计收藏
        users = UserProfile.objects.all()
        total_users = users.count()
        
        self.stdout.write(f'正在处理 {total_users} 个用户的收藏数据...')
        
        for user in users:
            collected_books = user.get_collected_books()
            if not collected_books:
                continue
            
            for item in collected_books:
                # 处理不同的数据格式
                if isinstance(item, dict):
                    book_title = item.get('book_title')
                elif isinstance(item, str):
                    book_title = item
                else:
                    continue
                
                if book_title:
                    book_collection_counts[book_title] = book_collection_counts.get(book_title, 0) + 1
                    total_collections += 1
        
        self.stdout.write(f'统计完成：共 {total_collections} 条收藏记录，涉及 {len(book_collection_counts)} 本书籍')
        
        # 更新书籍的收藏数量
        updated_count = 0
        not_found_books = []
        
        for book_title, count in book_collection_counts.items():
            try:
                book = BookName.objects.get(title=book_title)
                old_count = book.collection_count or 0
                
                if not dry_run:
                    book.collection_count = count
                    book.save(update_fields=['collection_count'])
                
                if old_count != count:
                    self.stdout.write(
                        f'  {book_title}: {old_count} -> {count}'
                    )
                    updated_count += 1
                else:
                    self.stdout.write(
                        f'  {book_title}: {count} (无需更新)'
                    )
                    
            except BookName.DoesNotExist:
                not_found_books.append(book_title)
                self.stdout.write(
                    self.style.WARNING(f'  警告: 找不到书籍 "{book_title}"')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  错误: 更新书籍 "{book_title}" 失败: {e}')
                )
        
        # 将没有收藏的书籍的收藏数设为 0
        all_books = BookName.objects.all()
        zero_count_books = 0
        for book in all_books:
            if book.title not in book_collection_counts:
                if book.collection_count and book.collection_count > 0:
                    if not dry_run:
                        book.collection_count = 0
                        book.save(update_fields=['collection_count'])
                    self.stdout.write(
                        f'  {book.title}: {book.collection_count} -> 0 (无收藏)'
                    )
                    zero_count_books += 1
        
        # 输出统计信息
        self.stdout.write('')
        self.stdout.write('=' * 60)
        if dry_run:
            self.stdout.write(self.style.WARNING('干运行模式 - 未实际修改数据'))
        else:
            self.stdout.write(self.style.SUCCESS('更新完成！'))
        self.stdout.write(f'  总计更新: {updated_count} 本书籍')
        self.stdout.write(f'  设为0: {zero_count_books} 本书籍')
        if not_found_books:
            self.stdout.write(
                self.style.WARNING(f'  找不到的书籍: {len(not_found_books)} 本')
            )
            for book_title in not_found_books[:10]:  # 只显示前10个
                self.stdout.write(f'    - {book_title}')
            if len(not_found_books) > 10:
                self.stdout.write(f'    ... 还有 {len(not_found_books) - 10} 本')



