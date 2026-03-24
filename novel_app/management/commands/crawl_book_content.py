from django.core.management.base import BaseCommand, CommandError

from novel_app.crawler_service import DjangoBookCrawlerService
from novel_app.models import BookChapter, BookName


class Command(BaseCommand):
    help = '爬取并保存指定书籍的章节正文内容'

    def add_arguments(self, parser):
        parser.add_argument('book_id', type=int, help='Django 书籍 ID')
        parser.add_argument(
            '--max-chapters',
            type=int,
            default=10,
            help='最多爬取多少个未爬取章节，默认 10'
        )
        parser.add_argument(
            '--chapters',
            type=str,
            help='指定章节号，使用英文逗号分隔，例如 3,5,8'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='爬取当前书籍全部未爬取章节'
        )

    def handle(self, *args, **options):
        book_id = options['book_id']
        max_chapters = options['max_chapters']
        chapters_raw = options.get('chapters')
        crawl_all = options.get('all', False)

        try:
            book = BookName.objects.get(book_id=book_id)
        except BookName.DoesNotExist as exc:
            raise CommandError(f'书籍不存在: {book_id}') from exc

        chapter_numbers = None
        if chapters_raw:
            try:
                chapter_numbers = [
                    int(item.strip())
                    for item in chapters_raw.split(',')
                    if item.strip()
                ]
            except ValueError as exc:
                raise CommandError('--chapters 参数格式错误，请使用英文逗号分隔的数字') from exc

            if not chapter_numbers:
                raise CommandError('--chapters 不能为空')

        if crawl_all and not chapter_numbers:
            max_chapters = BookChapter.objects.filter(
                book_title=book.title,
                is_crawled=False
            ).count() or max_chapters

        self.stdout.write(f'开始爬取《{book.title}》正文内容')
        self.stdout.write(f'书籍ID: {book.book_id}')
        self.stdout.write(f'奇猫ID: {book.qimao_book_id or "未配置"}')

        if chapter_numbers:
            self.stdout.write(f'指定章节: {chapter_numbers}')
        else:
            self.stdout.write(f'最多爬取章节数: {max_chapters}')

        crawler = DjangoBookCrawlerService()
        result = crawler.crawl_book_chapters(
            book_id=book.book_id,
            max_chapters=max_chapters,
            async_crawl=False,
            chapter_numbers=chapter_numbers
        )

        if not result.get('success'):
            raise CommandError(result.get('message') or '爬取失败')

        self.stdout.write(self.style.SUCCESS(result.get('message') or '爬取完成'))
        self.stdout.write(f"本次爬取: {result.get('chapters_crawled', 0)} 章")
        self.stdout.write(f"总章节数: {result.get('total_chapters', 0)}")
        self.stdout.write(f"已爬取章节数: {result.get('crawled_chapters', 0)}")
        self.stdout.write(f"是否全部完成: {'是' if result.get('all_crawled') else '否'}")
