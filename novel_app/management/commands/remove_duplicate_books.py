from django.core.management.base import BaseCommand
from django.db.models import Count
from novel_app.models import BookName


class Command(BaseCommand):
    help = '删除重复的书籍记录，保留最新的一条'

    def handle(self, *args, **options):
        self.stdout.write('开始查找重复的书籍...')
        
        # 查找重复的书名
        duplicates = BookName.objects.values('title').annotate(
            count=Count('title')
        ).filter(count__gt=1)
        
        total_duplicates = duplicates.count()
        total_removed = 0
        
        if total_duplicates == 0:
            self.stdout.write(
                self.style.SUCCESS('没有发现重复的书籍记录')
            )
            return
        
        self.stdout.write(f'发现 {total_duplicates} 个重复的书名')
        
        for duplicate in duplicates:
            title = duplicate['title']
            count = duplicate['count']
            
            # 获取所有同名书籍，按创建时间排序
            books = BookName.objects.filter(title=title).order_by('-create_time')
            
            # 保留最新的一本，删除其他的
            books_to_delete = books[1:]  # 跳过第一本（最新的）
            
            self.stdout.write(f'书名: "{title}" 有 {count} 条记录')
            self.stdout.write(f'  保留: ID={books[0].book_id}, 创建时间={books[0].create_time}')
            
            for book in books_to_delete:
                self.stdout.write(f'  删除: ID={book.book_id}, 创建时间={book.create_time}')
                book.delete()
                total_removed += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'清理完成！共删除了 {total_removed} 条重复记录')
        )