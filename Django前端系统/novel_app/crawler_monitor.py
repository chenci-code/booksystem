"""
爬虫监控服务模块
提供爬虫任务状态监控、进度跟踪、失败重试等功能
"""
from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import logging
import uuid

logger = logging.getLogger(__name__)


class CrawlerTask(models.Model):
    """爬虫任务模型"""
    
    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('running', '运行中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]
    
    task_id = models.CharField(max_length=100, primary_key=True, verbose_name='任务ID')
    book_id = models.IntegerField(verbose_name='书籍ID')
    book_title = models.CharField(max_length=200, verbose_name='书籍标题')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    total_chapters = models.IntegerField(default=0, verbose_name='总章节数')
    completed_chapters = models.IntegerField(default=0, verbose_name='已完成章节数')
    failed_chapters = models.IntegerField(default=0, verbose_name='失败章节数')
    failed_chapter_list = models.TextField(blank=True, null=True, verbose_name='失败章节列表(JSON)')
    error_message = models.TextField(blank=True, null=True, verbose_name='错误信息')
    retry_count = models.IntegerField(default=0, verbose_name='重试次数')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    
    class Meta:
        db_table = 'crawler_task'
        verbose_name = '爬虫任务'
        verbose_name_plural = '爬虫任务'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.task_id} - {self.book_title} ({self.status})"
    
    def get_progress_percentage(self) -> float:
        """获取进度百分比"""
        if self.total_chapters == 0:
            return 0.0
        return round((self.completed_chapters / self.total_chapters) * 100, 2)
    
    def get_duration(self) -> Optional[str]:
        """计算任务耗时"""
        if not self.started_at:
            return None
        
        end = self.completed_at or timezone.now()
        duration = end - self.started_at
        
        hours, remainder = divmod(duration.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}小时{minutes}分{seconds}秒"
        elif minutes > 0:
            return f"{minutes}分{seconds}秒"
        else:
            return f"{seconds}秒"
    
    def get_failed_chapters_list(self) -> List[int]:
        """获取失败章节列表"""
        if not self.failed_chapter_list:
            return []
        try:
            return json.loads(self.failed_chapter_list)
        except:
            return []
    
    def set_failed_chapters_list(self, chapters: List[int]):
        """设置失败章节列表"""
        self.failed_chapter_list = json.dumps(chapters)
        self.failed_chapters = len(chapters)


class CrawlerMonitor:
    """爬虫监控服务"""
    
    def __init__(self):
        pass
    
    def start_crawl_task(self, book_id: int, book_title: str, max_chapters: int = 10, chapter_numbers: List[int] = None) -> str:
        """
        启动爬虫任务
        
        Args:
            book_id: 书籍ID
            book_title: 书籍标题
            max_chapters: 最大爬取章节数
            chapter_numbers: 指定要爬取的章节编号列表
            
        Returns:
            str: 任务ID
        """
        # 生成任务ID
        task_id = f"crawl_{book_id}_{uuid.uuid4().hex[:8]}"
        
        # 创建任务记录
        task = CrawlerTask.objects.create(
            task_id=task_id,
            book_id=book_id,
            book_title=book_title,
            status='pending',
            total_chapters=len(chapter_numbers) if chapter_numbers else max_chapters
        )
        
        logger.info(f"创建爬虫任务: {task_id} - {book_title}")
        
        # 启动异步爬取
        self._start_async_crawl(task_id, book_id, max_chapters, chapter_numbers)
        
        return task_id
    
    def _start_async_crawl(self, task_id: str, book_id: int, max_chapters: int, chapter_numbers: List[int] = None):
        """启动异步爬取任务"""
        import threading
        
        def crawl_task():
            try:
                from .crawler_service import DjangoBookCrawlerService
                
                # 更新任务状态为运行中
                task = CrawlerTask.objects.get(task_id=task_id)
                task.status = 'running'
                task.started_at = timezone.now()
                task.save()
                
                # 执行爬取
                crawler_service = DjangoBookCrawlerService()
                result = crawler_service.crawl_book_chapters(
                    book_id=book_id,
                    max_chapters=max_chapters,
                    async_crawl=False,  # 在线程中同步执行
                    chapter_numbers=chapter_numbers
                )
                
                # 更新任务状态
                task = CrawlerTask.objects.get(task_id=task_id)
                if result['success']:
                    task.status = 'completed'
                    task.completed_chapters = result.get('chapters_crawled', 0)
                    task.completed_at = timezone.now()
                else:
                    task.status = 'failed'
                    task.error_message = result.get('message', '未知错误')
                    task.completed_at = timezone.now()
                
                task.save()
                logger.info(f"爬虫任务完成: {task_id} - {'成功' if result['success'] else '失败'}")
                
            except Exception as e:
                logger.error(f"爬虫任务执行失败: {task_id} - {e}")
                try:
                    task = CrawlerTask.objects.get(task_id=task_id)
                    task.status = 'failed'
                    task.error_message = str(e)
                    task.completed_at = timezone.now()
                    task.save()
                except:
                    pass
        
        # 启动线程
        thread = threading.Thread(target=crawl_task)
        thread.daemon = True
        thread.start()
    
    def get_task_detail(self, task_id: str) -> Optional[Dict]:
        """获取任务详情"""
        try:
            task = CrawlerTask.objects.get(task_id=task_id)
            return {
                'task_id': task.task_id,
                'book_id': task.book_id,
                'book_title': task.book_title,
                'status': task.status,
                'total_chapters': task.total_chapters,
                'completed_chapters': task.completed_chapters,
                'failed_chapters': task.failed_chapters,
                'failed_chapter_list': task.get_failed_chapters_list(),
                'progress_percentage': task.get_progress_percentage(),
                'error_message': task.error_message,
                'retry_count': task.retry_count,
                'created_at': task.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'started_at': task.started_at.strftime('%Y-%m-%d %H:%M:%S') if task.started_at else None,
                'completed_at': task.completed_at.strftime('%Y-%m-%d %H:%M:%S') if task.completed_at else None,
                'duration': task.get_duration(),
            }
        except CrawlerTask.DoesNotExist:
            return None
    
    def get_statistics(self) -> Dict:
        """获取爬虫统计信息"""
        total_tasks = CrawlerTask.objects.count()
        completed_tasks = CrawlerTask.objects.filter(status='completed').count()
        failed_tasks = CrawlerTask.objects.filter(status='failed').count()
        running_tasks = CrawlerTask.objects.filter(status='running').count()
        pending_tasks = CrawlerTask.objects.filter(status='pending').count()
        
        # 计算成功率
        success_rate = 0.0
        if total_tasks > 0:
            success_rate = round((completed_tasks / total_tasks) * 100, 2)
        
        # 计算总爬取章节数
        total_chapters_crawled = CrawlerTask.objects.filter(
            status='completed'
        ).aggregate(
            total=models.Sum('completed_chapters')
        )['total'] or 0
        
        return {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'failed_tasks': failed_tasks,
            'running_tasks': running_tasks,
            'pending_tasks': pending_tasks,
            'success_rate': success_rate,
            'total_chapters_crawled': total_chapters_crawled,
        }
    
    def retry_task(self, task_id: str) -> Dict:
        """重试失败的任务"""
        try:
            task = CrawlerTask.objects.get(task_id=task_id)
            
            if task.status != 'failed':
                return {
                    'success': False,
                    'message': f'任务状态为 {task.status}，只能重试失败的任务'
                }
            
            # 增加重试次数
            task.retry_count += 1
            task.status = 'pending'
            task.error_message = None
            task.started_at = None
            task.completed_at = None
            task.save()
            
            # 重新启动爬取
            self._start_async_crawl(
                task_id=task.task_id,
                book_id=task.book_id,
                max_chapters=task.total_chapters,
                chapter_numbers=task.get_failed_chapters_list() if task.failed_chapters > 0 else None
            )
            
            logger.info(f"重试爬虫任务: {task_id} (第{task.retry_count}次重试)")
            
            return {
                'success': True,
                'message': f'已启动重试 (第{task.retry_count}次)'
            }
            
        except CrawlerTask.DoesNotExist:
            return {
                'success': False,
                'message': f'任务 {task_id} 不存在'
            }
        except Exception as e:
            logger.error(f"重试任务失败: {e}")
            return {
                'success': False,
                'message': f'重试失败: {str(e)}'
            }
    
    def clear_old_tasks(self, days: int = 30):
        """清理旧任务（保留最近N天）"""
        cutoff_time = timezone.now() - timedelta(days=days)
        deleted_count = CrawlerTask.objects.filter(
            created_at__lt=cutoff_time,
            status__in=['completed', 'failed']
        ).delete()[0]
        
        logger.info(f"清理旧任务，删除了 {deleted_count} 个任务")
        return deleted_count


# 全局监控实例
crawler_monitor = CrawlerMonitor()
