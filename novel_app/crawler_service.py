#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Django小说爬虫服务
集成现有的小说内容爬虫到Django系统中
使用 AdvancedCrawler 进行小说内容爬取
"""

import os
import sys
import json
import logging
import asyncio
from typing import List, Dict, Optional
from django.conf import settings
from django.utils import timezone

# 添加爬虫代码路径 - 支持多种路径查找方式
# Django项目在 d:\小说\Django前端系统
# 爬虫代码在 d:\小说\爬虫代码
# 所以需要从Django项目根目录向上一级，然后进入爬虫代码目录

# 获取Django项目根目录
django_project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
# 获取小说目录（Django项目根目录的父目录）
novel_root = os.path.dirname(django_project_root)

crawler_paths = [
    # 方式1: 从小说根目录进入爬虫代码（最可能的位置）
    os.path.join(novel_root, '爬虫代码'),
    # 方式2: 相对于Django项目根目录
    os.path.join(django_project_root, '..', '爬虫代码'),
    # 方式3: 绝对路径（如果爬虫代码在项目根目录）
    os.path.abspath(os.path.join(django_project_root, '爬虫代码')),
    # 方式4: 相对于当前文件
    os.path.join(os.path.dirname(__file__), '..', '..', '..', '爬虫代码'),
]

# 初始化logger（在使用前定义）
logger = logging.getLogger(__name__)

crawler_path = None
for path in crawler_paths:
    abs_path = os.path.abspath(path)
    if os.path.exists(abs_path) and os.path.isdir(abs_path):
        crawler_path = abs_path
        # 将路径添加到sys.path，确保可以导入模块
        if abs_path not in sys.path:
            sys.path.insert(0, abs_path)
        break

if crawler_path:
    logger.info(f"爬虫代码路径: {crawler_path}")
    # 验证关键文件是否存在
    advanced_crawler_file = os.path.join(crawler_path, 'advanced_crawler.py')
    if os.path.exists(advanced_crawler_file):
        logger.info(f"找到爬虫文件: advanced_crawler.py")
    else:
        logger.warning(f"未找到 advanced_crawler.py 文件")
else:
    logger.warning("未找到爬虫代码目录，请检查路径配置")
    logger.warning(f"尝试的路径: {[os.path.abspath(p) for p in crawler_paths]}")

from .models import BookName, BookChapter

# 尝试导入爬虫模块
# 注意：路径是动态添加的，linter无法静态分析，使用 type: ignore 忽略警告
AdvancedCrawler = None
CRAWLER_AVAILABLE = False

if crawler_path:
    try:
        # 确保路径在sys.path中
        if crawler_path not in sys.path:
            sys.path.insert(0, crawler_path)
        
        # 尝试导入
        from advanced_crawler import AdvancedCrawler  # type: ignore
        CRAWLER_AVAILABLE = True
        logger.info("成功导入 AdvancedCrawler 模块")
        logger.info(f"爬虫模块路径: {crawler_path}")
    except ImportError as e:
        logger.error(f"导入爬虫模块失败: {e}")
        logger.error(f"当前使用的爬虫路径: {crawler_path}")
        logger.error(f"路径是否存在: {os.path.exists(crawler_path)}")
        if os.path.exists(crawler_path):
            files = os.listdir(crawler_path)
            logger.error(f"路径中的文件: {files[:10]}")
            if 'advanced_crawler.py' in files:
                logger.error("advanced_crawler.py 文件存在，但导入失败，可能是依赖问题")
            else:
                logger.error("advanced_crawler.py 文件不存在")
        # 打印详细的错误信息
        import traceback
        logger.error(traceback.format_exc())
        AdvancedCrawler = None
        CRAWLER_AVAILABLE = False
else:
    logger.warning("爬虫代码路径未找到，无法导入爬虫模块")

class DjangoBookCrawlerService:
    """Django书籍爬虫服务 - 集成 AdvancedCrawler"""
    
    def __init__(self):
        """初始化爬虫服务"""
        if not CRAWLER_AVAILABLE:
            logger.warning("爬虫模块不可用，部分功能将受限")
        
        # 设置Django项目中的内容存储目录
        self.content_dir = os.path.join(settings.MEDIA_ROOT, 'book_contents')
        if not os.path.exists(self.content_dir):
            os.makedirs(self.content_dir)
            logger.info(f"创建内容存储目录: {self.content_dir}")
        
        # 注意：不在这里创建爬虫实例，而是在使用时通过异步上下文管理器创建
    
    async def _crawl_book_async(self, qimao_book_id: str, book_title: str, max_chapters: int, book: BookName, chapter_numbers: List[int] = None) -> List[Dict]:
        """
        异步爬取书籍章节（内部方法）
        
        Args:
            qimao_book_id: 奇猫网书籍ID
            book_title: 书籍标题
            max_chapters: 最大章节数
            book: 书籍模型对象
            chapter_numbers: 要爬取的章节编号列表（如果指定，则只爬取这些章节）
            
        Returns:
            List[Dict]: 爬取的章节列表
        """
        if not CRAWLER_AVAILABLE:
            raise ImportError("爬虫模块不可用")
        
        # 使用异步上下文管理器确保资源正确释放
        async with AdvancedCrawler() as crawler:
            logger.info(f"开始爬取书籍: {book_title} (奇猫ID: {qimao_book_id})")
            
            if chapter_numbers:
                # 如果指定了章节编号，只爬取这些章节
                # 先获取章节列表
                all_chapters = await crawler.get_chapter_list(str(qimao_book_id))
                if not all_chapters:
                    return []
                
                # 筛选出要爬取的章节
                chapters_to_crawl = []
                for chapter_info in all_chapters:
                    # 从章节标题或ID中提取章节编号
                    chapter_num = None
                    title = chapter_info.get('title', '')
                    # 尝试从标题中提取章节编号
                    import re
                    match = re.search(r'第(\d+)章', title)
                    if match:
                        chapter_num = int(match.group(1))
                    else:
                        # 如果标题中没有，尝试使用ID（假设ID就是章节编号）
                        try:
                            chapter_num = int(chapter_info.get('id', 0))
                        except (ValueError, TypeError):
                            continue
                    
                    if chapter_num and chapter_num in chapter_numbers:
                        chapters_to_crawl.append(chapter_info)
                
                # 爬取选定的章节
                crawled_chapters = []
                for chapter_info in chapters_to_crawl:
                    chapter_id = chapter_info.get('id', '')
                    chapter_title = chapter_info.get('title', '')
                    content = await crawler.crawl_chapter_advanced(
                        book_id=str(qimao_book_id),
                        chapter_id=chapter_id,
                        chapter_title=chapter_title,
                        book_name=book_title
                    )
                    if content:
                        crawled_chapters.append({
                            'id': chapter_id,
                            'title': chapter_title,
                            'content': content
                        })
                
                return crawled_chapters
            else:
                # 使用 AdvancedCrawler 的爬取方法
                crawled_chapters = await crawler.crawl_book_advanced(
                    book_id=str(qimao_book_id),
                    book_title=book_title,
                    max_chapters=max_chapters
                )
                
                return crawled_chapters or []
    
    def crawl_book_chapters(self, book_id: int, max_chapters: int = 10, async_crawl: bool = False, chapter_numbers: List[int] = None) -> Dict:
        """
        爬取书籍章节内容并保存到数据库
        
        Args:
            book_id: 书籍ID（Django数据库中的ID）
            max_chapters: 最大爬取章节数（仅当chapter_numbers为None时有效）
            async_crawl: 是否异步爬取（后台任务）
            chapter_numbers: 要爬取的章节编号列表（如果指定，则只爬取这些章节）
            
        Returns:
            Dict: 爬取结果
        """
        if not CRAWLER_AVAILABLE:
            return {
                'success': False,
                'message': '爬虫模块未正确导入，请检查爬虫代码路径',
                'chapters_crawled': 0
            }
        
        try:
            # 获取书籍信息
            book = BookName.objects.get(book_id=book_id)
            
            # 获取所有章节（包括已爬取和未爬取的）
            all_chapters = BookChapter.objects.filter(book_title=book.title).order_by('chapter_number')
            total_chapters = all_chapters.count()
            crawled_chapters_count = all_chapters.filter(is_crawled=True).count()
            uncrawled_chapters = all_chapters.filter(is_crawled=False).order_by('chapter_number')
            
            # 如果指定了章节编号，只爬取这些章节
            if chapter_numbers:
                # 验证章节编号是否有效
                valid_chapters = uncrawled_chapters.filter(chapter_number__in=chapter_numbers)
                if not valid_chapters.exists():
                    return {
                        'success': False,
                        'message': '指定的章节不存在或已全部爬取',
                        'chapters_crawled': 0,
                        'total_chapters': total_chapters,
                        'crawled_chapters': crawled_chapters_count,
                        'all_crawled': crawled_chapters_count == total_chapters
                    }
            else:
                # 如果没有指定章节编号，只爬取未爬取的章节
                if uncrawled_chapters.count() == 0:
                    return {
                        'success': True,
                        'message': '已全部爬取',
                        'chapters_crawled': crawled_chapters_count,
                        'total_chapters': total_chapters,
                        'crawled_chapters': crawled_chapters_count,
                        'all_crawled': True
                    }
                
                # 获取前max_chapters个未爬取的章节
                chapters_to_crawl = uncrawled_chapters[:max_chapters]
                chapter_numbers = list(chapters_to_crawl.values_list('chapter_number', flat=True))
            
            # 使用书籍的qimao_book_id进行爬取
            qimao_book_id = book.qimao_book_id
            if not qimao_book_id:
                return {
                    'success': False,
                    'message': f'书籍《{book.title}》缺少奇猫网ID，无法爬取',
                    'chapters_crawled': 0
                }
            
            logger.info(f"开始爬取书籍: {book.title} (Django ID: {book_id}, 奇猫ID: {qimao_book_id})")
            
            if async_crawl:
                # 异步爬取 - 启动后台任务
                import threading
                def async_crawl_task():
                    try:
                        # 在新的事件循环中运行异步爬取
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            crawled_chapters = loop.run_until_complete(
                                self._crawl_book_async(
                                    qimao_book_id=str(qimao_book_id),
                                    book_title=book.title,
                                    max_chapters=max_chapters,
                                    book=book,
                                    chapter_numbers=chapter_numbers
                                )
                            )
                            
                            if crawled_chapters:
                                saved_count = self._save_chapters_to_db(book, crawled_chapters, chapter_numbers)
                                book.chapter_count = BookChapter.objects.filter(book_title=book.title).count()
                                book.save()
                                logger.info(f"异步爬取完成: {book.title}, 共保存 {saved_count} 章")
                            else:
                                logger.warning(f"异步爬取失败: {book.title}，未获取到章节内容")
                        finally:
                            loop.close()
                    except Exception as e:
                        logger.error(f"异步爬取出错: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                
                # 启动异步任务
                thread = threading.Thread(target=async_crawl_task)
                thread.daemon = True
                thread.start()
                
                return {
                    'success': True,
                    'message': f'开始异步爬取书籍《{book.title}》，请稍后查看进度',
                    'chapters_crawled': 0,
                    'async': True,
                    'total_chapters': total_chapters,
                    'crawled_chapters': crawled_chapters_count,
                    'all_crawled': False
                }
            else:
                # 同步爬取 - 需要运行异步方法
                try:
                    # 检查是否已有事件循环
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_closed():
                            raise RuntimeError("事件循环已关闭")
                        loop_created = False
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop_created = True
                    
                    try:
                        # 运行异步爬取
                        crawled_chapters = loop.run_until_complete(
                            self._crawl_book_async(
                                qimao_book_id=str(qimao_book_id),
                                book_title=book.title,
                                max_chapters=max_chapters,
                                book=book,
                                chapter_numbers=chapter_numbers
                            )
                        )
                    finally:
                        # 如果创建了新的事件循环，确保关闭它
                        if loop_created:
                            loop.close()
                    
                    if not crawled_chapters:
                        return {
                            'success': False,
                            'message': f'爬取书籍《{book.title}》失败，未获取到章节内容',
                            'chapters_crawled': 0,
                            'total_chapters': total_chapters,
                            'crawled_chapters': crawled_chapters_count,
                            'all_crawled': False
                        }
                    
                    # 保存章节信息到数据库
                    saved_count = self._save_chapters_to_db(book, crawled_chapters, chapter_numbers)
                    
                    # 更新书籍的章节数
                    book.chapter_count = BookChapter.objects.filter(book_title=book.title).count()
                    book.save()
                    
                    # 检查是否全部爬取完成
                    final_crawled = BookChapter.objects.filter(book_title=book.title, is_crawled=True).count()
                    all_crawled = final_crawled == total_chapters
                    
                    return {
                        'success': True,
                        'message': f'成功爬取 {saved_count} 章' if not all_crawled else '已全部爬取',
                        'chapters_crawled': saved_count,
                        'total_chapters': total_chapters,
                        'crawled_chapters': final_crawled,
                        'all_crawled': all_crawled
                    }
                except Exception as e:
                    logger.error(f"同步爬取出错: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    return {
                        'success': False,
                        'message': f'爬取过程中出错: {str(e)}',
                        'chapters_crawled': 0
                    }
            
        except BookName.DoesNotExist:
            return {
                'success': False,
                'message': f'书籍ID {book_id} 不存在',
                'chapters_crawled': 0
            }
        except Exception as e:
            logger.error(f"爬取书籍时出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f'爬取过程中出错: {str(e)}',
                'chapters_crawled': 0
            }
    
    def _save_chapters_to_db(self, book: BookName, crawled_chapters: List[Dict], chapter_numbers: List[int] = None) -> int:
        """
        将爬取的章节保存到数据库
        
        Args:
            book: 书籍对象
            crawled_chapters: 爬取的章节列表
            chapter_numbers: 章节编号列表（如果提供，用于匹配章节）
            
        Returns:
            int: 保存的章节数量
        """
        saved_count = 0
        
        # 获取数据库中已有的章节，用于匹配章节编号
        existing_chapters = {}
        if chapter_numbers:
            db_chapters = BookChapter.objects.filter(
                book_title=book.title,
                chapter_number__in=chapter_numbers
            )
            for db_chapter in db_chapters:
                existing_chapters[db_chapter.chapter_number] = db_chapter
        
        for i, chapter_data in enumerate(crawled_chapters):
            try:
                # 处理不同的数据格式
                # 格式1: {'title': '...', 'content': [...]} (来自crawl_book_advanced)
                # 格式2: {'id': '...', 'title': '...', 'content': [...]} (来自crawl_chapter_advanced的包装)
                # 格式3: List[str] (直接是内容行列表，需要从chapter_numbers获取标题)
                
                if isinstance(chapter_data, list):
                    # 如果直接是内容行列表
                    content_lines = chapter_data
                    if chapter_numbers and i < len(chapter_numbers):
                        chapter_number = chapter_numbers[i]
                        chapter_title = f'第{chapter_number}章'
                    else:
                        chapter_title = f'第{i+1}章'
                elif isinstance(chapter_data, dict):
                    chapter_title = chapter_data.get('title', f'第{i+1}章')
                    content_lines = chapter_data.get('content', [])
                    # 如果content是None，尝试其他字段
                    if not content_lines:
                        content_lines = chapter_data.get('lines', [])
                        if not content_lines and 'text' in chapter_data:
                            content_lines = chapter_data['text'].split('\n') if isinstance(chapter_data['text'], str) else []
                else:
                    logger.warning(f"未知的章节数据格式: {type(chapter_data)}")
                    continue
                
                # 确定章节编号
                if chapter_numbers and i < len(chapter_numbers):
                    chapter_number = chapter_numbers[i]
                else:
                    # 尝试从标题中提取章节编号
                    import re
                    match = re.search(r'第(\d+)章', chapter_title)
                    if match:
                        chapter_number = int(match.group(1))
                    else:
                        # 如果无法提取，使用索引+1
                        chapter_number = i + 1
                
                # 生成内容文件路径
                safe_book_title = self._sanitize_filename(book.title)
                safe_chapter_title = self._sanitize_filename(chapter_title)
                content_filename = f"{safe_book_title}_{safe_chapter_title}.txt"
                content_file_path = os.path.join('book_contents', content_filename)
                
                # 保存内容到文件
                full_content_path = os.path.join(self.content_dir, content_filename)
                with open(full_content_path, 'w', encoding='utf-8') as f:
                    for line in content_lines:
                        f.write(line + '\n')
                
                # 计算字数
                word_count = sum(len(line) for line in content_lines)
                
                # 创建或更新章节记录
                chapter, created = BookChapter.objects.update_or_create(
                    book_title=book.title,
                    chapter_number=chapter_number,
                    defaults={
                        'chapter_title': chapter_title,
                        'content_file_path': content_file_path,
                        'word_count': word_count,
                        'is_crawled': True,
                        'crawl_time': timezone.now(),
                    }
                )
                
                if created:
                    saved_count += 1
                    logger.info(f"保存章节: {chapter_title} (第{chapter_number}章)")
                else:
                    logger.info(f"更新章节: {chapter_title} (第{chapter_number}章)")
                
            except Exception as e:
                logger.error(f"保存章节 {i+1} 时出错: {e}")
                continue
        
        return saved_count
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名中的非法字符"""
        import re
        return re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    def get_chapter_content(self, book_title: str, chapter_number: int) -> Optional[str]:
        """
        从文件读取章节内容
        
        Args:
            book_title: 书名
            chapter_number: 章节号
            
        Returns:
            Optional[str]: 章节内容，如果不存在则返回None
        """
        try:
            chapter = BookChapter.objects.get(
                book_title=book_title,
                chapter_number=chapter_number
            )
            
            if not chapter.content_file_path:
                return None
            
            # 构建完整文件路径
            full_path = os.path.join(settings.MEDIA_ROOT, chapter.content_file_path)
            
            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                logger.warning(f"章节内容文件不存在: {full_path}")
                return None
                
        except BookChapter.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"读取章节内容时出错: {e}")
            return None
    
    def get_chapter_list(self, book_id: int) -> Dict:
        """
        获取书籍的章节列表（从奇猫网）
        
        Args:
            book_id: 书籍ID（Django数据库中的ID）
            
        Returns:
            Dict: 章节列表信息
        """
        if not CRAWLER_AVAILABLE:
            return {
                'success': False,
                'message': '爬虫模块不可用',
                'chapters': []
            }
        
        try:
            book = BookName.objects.get(book_id=book_id)
            qimao_book_id = book.qimao_book_id
            
            if not qimao_book_id:
                return {
                    'success': False,
                    'message': f'书籍《{book.title}》缺少奇猫网ID',
                    'chapters': []
                }
            
            # 运行异步方法获取章节列表
            async def _get_chapters():
                async with AdvancedCrawler() as crawler:
                    chapters = await crawler.get_chapter_list(str(qimao_book_id))
                    return chapters
            
            # 安全地运行异步函数
            loop_created = False
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    raise RuntimeError("事件循环已关闭")
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop_created = True
            
            try:
                chapters = loop.run_until_complete(_get_chapters())
            finally:
                # 如果创建了新的事件循环，确保关闭它
                if loop_created:
                    loop.close()
            
            return {
                'success': True,
                'message': f'成功获取 {len(chapters)} 个章节',
                'chapters': chapters,
                'total_count': len(chapters)
            }
            
        except BookName.DoesNotExist:
            return {
                'success': False,
                'message': f'书籍ID {book_id} 不存在',
                'chapters': []
            }
        except Exception as e:
            logger.error(f"获取章节列表失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f'获取章节列表失败: {str(e)}',
                'chapters': []
            }
    
    def get_book_info_from_qimao(self, book_id: int) -> Dict:
        """
        从奇猫网获取书籍详细信息
        
        Args:
            book_id: 书籍ID（Django数据库中的ID）
            
        Returns:
            Dict: 书籍信息
        """
        if not CRAWLER_AVAILABLE:
            return {
                'success': False,
                'message': '爬虫模块不可用',
                'book_info': None
            }
        
        try:
            book = BookName.objects.get(book_id=book_id)
            qimao_book_id = book.qimao_book_id
            
            if not qimao_book_id:
                return {
                    'success': False,
                    'message': f'书籍《{book.title}》缺少奇猫网ID',
                    'book_info': None
                }
            
            # 运行异步方法获取书籍信息
            async def _get_book_info():
                async with AdvancedCrawler() as crawler:
                    book_info = await crawler.get_book_info(str(qimao_book_id))
                    return book_info
            
            # 安全地运行异步函数
            loop_created = False
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    raise RuntimeError("事件循环已关闭")
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop_created = True
            
            try:
                book_info = loop.run_until_complete(_get_book_info())
            finally:
                # 如果创建了新的事件循环，确保关闭它
                if loop_created:
                    loop.close()
            
            if book_info:
                # 更新数据库中的书籍信息
                if book_info.get('title') and book_info['title'] != book.title:
                    book.title = book_info['title']
                if book_info.get('author'):
                    book.author = book_info['author']
                if book_info.get('description'):
                    book.description = book_info['description']
                if book_info.get('word_count'):
                    book.word_count = book_info['word_count']
                if book_info.get('status'):
                    book.status = book_info['status']
                if book_info.get('rating'):
                    try:
                        book.rating = float(book_info['rating'])
                    except (ValueError, TypeError):
                        pass
                book.save()
                
                return {
                    'success': True,
                    'message': '成功获取书籍信息',
                    'book_info': book_info
                }
            else:
                return {
                    'success': False,
                    'message': '未能获取到书籍信息',
                    'book_info': None
                }
            
        except BookName.DoesNotExist:
            return {
                'success': False,
                'message': f'书籍ID {book_id} 不存在',
                'book_info': None
            }
        except Exception as e:
            logger.error(f"获取书籍信息失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f'获取书籍信息失败: {str(e)}',
                'book_info': None
            }
    
    def crawl_single_chapter(self, book_id: int, chapter_id: str, chapter_title: str = "") -> Dict:
        """
        爬取单个章节内容
        
        Args:
            book_id: 书籍ID（Django数据库中的ID）
            chapter_id: 章节ID（奇猫网的章节ID）
            chapter_title: 章节标题（可选）
            
        Returns:
            Dict: 爬取结果
        """
        if not CRAWLER_AVAILABLE:
            return {
                'success': False,
                'message': '爬虫模块不可用',
                'content': None
            }
        
        try:
            book = BookName.objects.get(book_id=book_id)
            qimao_book_id = book.qimao_book_id
            
            if not qimao_book_id:
                return {
                    'success': False,
                    'message': f'书籍《{book.title}》缺少奇猫网ID',
                    'content': None
                }
            
            # 运行异步方法爬取章节
            async def _crawl_chapter():
                async with AdvancedCrawler() as crawler:
                    content = await crawler.crawl_chapter_advanced(
                        book_id=str(qimao_book_id),
                        chapter_id=chapter_id,
                        chapter_title=chapter_title or f"章节{chapter_id}",
                        book_name=book.title
                    )
                    return content
            
            # 安全地运行异步函数
            loop_created = False
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    raise RuntimeError("事件循环已关闭")
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop_created = True
            
            try:
                content = loop.run_until_complete(_crawl_chapter())
            finally:
                # 如果创建了新的事件循环，确保关闭它
                if loop_created:
                    loop.close()
            
            if content:
                return {
                    'success': True,
                    'message': f'成功爬取章节内容，共 {len(content)} 行',
                    'content': content,
                    'word_count': sum(len(line) for line in content)
                }
            else:
                return {
                    'success': False,
                    'message': '未能获取到章节内容',
                    'content': None
                }
            
        except BookName.DoesNotExist:
            return {
                'success': False,
                'message': f'书籍ID {book_id} 不存在',
                'content': None
            }
        except Exception as e:
            logger.error(f"爬取章节失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f'爬取章节失败: {str(e)}',
                'content': None
            }
    
    def check_crawl_status(self, book_id: int) -> Dict:
        """
        检查书籍爬取状态
        
        Args:
            book_id: 书籍ID
            
        Returns:
            Dict: 爬取状态信息
        """
        try:
            book = BookName.objects.get(book_id=book_id)
            chapters = BookChapter.objects.filter(book_title=book.title)
            
            total_chapters = chapters.count()
            crawled_chapters = chapters.filter(is_crawled=True).count()
            
            return {
                'book_title': book.title,
                'total_chapters': total_chapters,
                'crawled_chapters': crawled_chapters,
                'crawl_progress': (crawled_chapters / total_chapters * 100) if total_chapters > 0 else 0,
                'has_qimao_id': bool(book.qimao_book_id),
                'qimao_book_id': book.qimao_book_id
            }
            
        except BookName.DoesNotExist:
            return {
                'book_title': None,
                'total_chapters': 0,
                'crawled_chapters': 0,
                'crawl_progress': 0,
                'has_qimao_id': False,
                'qimao_book_id': None
            }
