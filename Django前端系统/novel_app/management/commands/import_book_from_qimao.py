#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Django管理命令：从奇猫网导入书籍信息到数据库
只导入书籍信息和章节列表，不爬取章节内容
"""

import asyncio
import sys
import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from novel_app.models import BookName, BookChapter
from novel_app.crawler_service import DjangoBookCrawlerService

class Command(BaseCommand):
    help = '从奇猫网导入书籍信息到数据库（不爬取内容）'

    def add_arguments(self, parser):
        parser.add_argument(
            'qimao_book_id',
            type=str,
            help='奇猫网书籍ID'
        )
        parser.add_argument(
            '--category',
            type=str,
            default='其他',
            help='书籍类别（默认：其他）'
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='如果书籍已存在，更新书籍信息'
        )

    def handle(self, *args, **options):
        qimao_book_id = options['qimao_book_id']
        category = options['category']
        update = options['update']
        
        self.stdout.write(f"开始导入书籍，奇猫网ID: {qimao_book_id}")
        self.stdout.write("=" * 60)
        
        try:
            # 检查书籍是否已存在
            existing_book = BookName.objects.filter(qimao_book_id=qimao_book_id).first()
            
            if existing_book and not update:
                self.stdout.write(
                    self.style.WARNING(
                        f"书籍已存在: {existing_book.title} (Django ID: {existing_book.book_id})"
                    )
                )
                self.stdout.write("使用 --update 参数可以更新书籍信息")
                return
            
            # 初始化爬虫服务
            crawler_service = DjangoBookCrawlerService()
            
            # 1. 获取书籍信息
            self.stdout.write("步骤1: 获取书籍信息...")
            
            # 创建临时书籍对象用于获取信息
            temp_book = None
            if existing_book:
                temp_book = existing_book
            else:
                # 创建临时书籍对象
                temp_book = BookName.objects.create(
                    title=f"临时书籍_{qimao_book_id}",
                    author="未知",
                    category=category,
                    qimao_book_id=qimao_book_id
                )
            
            # 获取书籍详细信息
            book_info_result = crawler_service.get_book_info_from_qimao(temp_book.book_id)
            
            if not book_info_result.get('success'):
                if not existing_book:
                    temp_book.delete()
                self.stdout.write(
                    self.style.ERROR(f"获取书籍信息失败: {book_info_result.get('message')}")
                )
                return
            
            book_info = book_info_result.get('book_info')
            if not book_info:
                if not existing_book:
                    temp_book.delete()
                self.stdout.write(self.style.ERROR("未能获取到书籍信息"))
                return
            
            # 更新或创建书籍
            if existing_book:
                book = existing_book
                self.stdout.write(f"更新现有书籍: {book.title}")
            else:
                # 检查是否已存在相同标题和作者的书籍
                book = BookName.objects.filter(
                    title=book_info.get('title', ''),
                    author=book_info.get('author', '')
                ).first()
                
                if book:
                    # 更新现有书籍的qimao_book_id
                    book.qimao_book_id = qimao_book_id
                    book.save()
                    temp_book.delete()
                    self.stdout.write(f"找到同名书籍，更新奇猫网ID: {book.title}")
                else:
                    # 使用获取到的信息更新临时书籍
                    book = temp_book
                    book.title = book_info.get('title', f'书籍_{qimao_book_id}')
                    book.author = book_info.get('author', '未知')
                    book.category = category
                    book.description = book_info.get('description', '')
                    book.word_count = book_info.get('word_count', '')
                    book.status = book_info.get('status', '连载中')
                    book.book_url = book_info.get('url', f'https://www.qimao.com/shuku/{qimao_book_id}/')
                    if book_info.get('rating'):
                        try:
                            book.rating = float(book_info['rating'])
                        except (ValueError, TypeError):
                            pass
                    book.save()
                    self.stdout.write(f"创建新书籍: {book.title}")
            
            # 2. 获取章节列表
            self.stdout.write("步骤2: 获取章节列表...")
            chapters_result = crawler_service.get_chapter_list(book.book_id)
            
            if not chapters_result.get('success'):
                self.stdout.write(
                    self.style.WARNING(f"获取章节列表失败: {chapters_result.get('message')}")
                )
                self.stdout.write("书籍信息已保存，但章节列表获取失败")
                return
            
            chapters = chapters_result.get('chapters', [])
            self.stdout.write(f"获取到 {len(chapters)} 个章节")
            
            # 3. 保存章节列表到数据库（不爬取内容）
            self.stdout.write("步骤3: 保存章节列表到数据库...")
            saved_count = 0
            updated_count = 0
            
            for i, chapter_info in enumerate(chapters, 1):
                try:
                    chapter_title = chapter_info.get('title', f'第{i}章')
                    chapter_id = chapter_info.get('id', str(i))
                    
                    # 创建或更新章节记录（不爬取内容）
                    chapter, created = BookChapter.objects.update_or_create(
                        book_title=book.title,
                        chapter_number=i,
                        defaults={
                            'chapter_title': chapter_title,
                            'is_crawled': False,  # 标记为未爬取
                            'word_count': 0,  # 内容未爬取，字数为0
                        }
                    )
                    
                    if created:
                        saved_count += 1
                    else:
                        updated_count += 1
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f"保存章节 {i} 失败: {e}")
                    )
                    continue
            
            # 更新书籍的章节数
            book.chapter_count = len(chapters)
            book.save()
            
            # 输出结果
            self.stdout.write("=" * 60)
            self.stdout.write(self.style.SUCCESS("导入完成！"))
            self.stdout.write(f"书籍ID (Django): {book.book_id}")
            self.stdout.write(f"书籍标题: {book.title}")
            self.stdout.write(f"作者: {book.author}")
            self.stdout.write(f"章节总数: {book.chapter_count}")
            self.stdout.write(f"新建章节: {saved_count}")
            self.stdout.write(f"更新章节: {updated_count}")
            self.stdout.write("=" * 60)
            self.stdout.write("注意：章节内容未爬取，可以在系统中使用爬取功能获取内容")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"导入过程中出错: {e}"))
            import traceback
            self.stdout.write(traceback.format_exc())
            return







