"""
爬虫监控系统测试脚本
用于测试爬虫监控的各项功能
"""
import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'novel_system.settings')
django.setup()

from novel_app.crawler_monitor import CrawlerMonitor, CrawlerTask
from novel_app.models import BookName
import time


def test_create_task():
    """测试创建任务"""
    print("\n=== 测试1: 创建爬虫任务 ===")
    
    # 获取一本书
    book = BookName.objects.first()
    if not book:
        print("❌ 数据库中没有书籍,无法测试")
        return False
    
    monitor = CrawlerMonitor()
    task_id = monitor.start_crawl_task(
        book_id=book.book_id,
        book_title=book.title,
        max_chapters=5
    )
    
    print(f"✓ 成功创建任务: {task_id}")
    print(f"  书籍: {book.title}")
    print(f"  书籍ID: {book.book_id}")
    
    # 等待任务开始
    time.sleep(2)
    
    # 检查任务状态
    task = CrawlerTask.objects.get(task_id=task_id)
    print(f"  任务状态: {task.status}")
    print(f"  总章节数: {task.total_chapters}")
    
    return task_id


def test_get_statistics():
    """测试获取统计信息"""
    print("\n=== 测试2: 获取统计信息 ===")
    
    monitor = CrawlerMonitor()
    stats = monitor.get_statistics()
    
    print(f"✓ 统计信息:")
    print(f"  总任务数: {stats['total_tasks']}")
    print(f"  已完成: {stats['completed_tasks']}")
    print(f"  失败: {stats['failed_tasks']}")
    print(f"  运行中: {stats['running_tasks']}")
    print(f"  等待中: {stats['pending_tasks']}")
    print(f"  成功率: {stats['success_rate']}%")
    print(f"  总爬取章节: {stats['total_chapters_crawled']}")
    
    return True


def test_get_task_detail(task_id):
    """测试获取任务详情"""
    print(f"\n=== 测试3: 获取任务详情 ===")
    
    monitor = CrawlerMonitor()
    detail = monitor.get_task_detail(task_id)
    
    if detail:
        print(f"✓ 任务详情:")
        print(f"  任务ID: {detail['task_id']}")
        print(f"  书籍: {detail['book_title']}")
        print(f"  状态: {detail['status']}")
        print(f"  进度: {detail['progress_percentage']}%")
        print(f"  已完成章节: {detail['completed_chapters']}/{detail['total_chapters']}")
        print(f"  失败章节: {detail['failed_chapters']}")
        print(f"  创建时间: {detail['created_at']}")
        print(f"  耗时: {detail['duration'] or '未开始'}")
        return True
    else:
        print(f"❌ 任务不存在: {task_id}")
        return False


def test_retry_task(task_id):
    """测试重试任务"""
    print(f"\n=== 测试4: 重试任务 ===")
    
    # 先将任务标记为失败
    try:
        task = CrawlerTask.objects.get(task_id=task_id)
        task.status = 'failed'
        task.error_message = '测试错误'
        task.save()
        print(f"✓ 已将任务标记为失败")
    except CrawlerTask.DoesNotExist:
        print(f"❌ 任务不存在: {task_id}")
        return False
    
    # 重试任务
    monitor = CrawlerMonitor()
    result = monitor.retry_task(task_id)
    
    if result['success']:
        print(f"✓ 重试成功: {result['message']}")
        
        # 检查任务状态
        task = CrawlerTask.objects.get(task_id=task_id)
        print(f"  新状态: {task.status}")
        print(f"  重试次数: {task.retry_count}")
        return True
    else:
        print(f"❌ 重试失败: {result['message']}")
        return False


def test_clear_old_tasks():
    """测试清理旧任务"""
    print(f"\n=== 测试5: 清理旧任务 ===")
    
    monitor = CrawlerMonitor()
    
    # 获取清理前的任务数
    before_count = CrawlerTask.objects.count()
    print(f"  清理前任务数: {before_count}")
    
    # 清理30天前的任务
    deleted_count = monitor.clear_old_tasks(days=30)
    
    # 获取清理后的任务数
    after_count = CrawlerTask.objects.count()
    print(f"  清理后任务数: {after_count}")
    print(f"✓ 清理了 {deleted_count} 个旧任务")
    
    return True


def main():
    """主测试函数"""
    print("=" * 60)
    print("爬虫监控系统测试")
    print("=" * 60)
    
    try:
        # 测试1: 创建任务
        task_id = test_create_task()
        if not task_id:
            print("\n❌ 测试失败: 无法创建任务")
            return
        
        # 测试2: 获取统计信息
        test_get_statistics()
        
        # 等待任务执行一段时间
        print("\n⏳ 等待任务执行...")
        time.sleep(5)
        
        # 测试3: 获取任务详情
        test_get_task_detail(task_id)
        
        # 测试4: 重试任务
        test_retry_task(task_id)
        
        # 测试5: 清理旧任务
        test_clear_old_tasks()
        
        print("\n" + "=" * 60)
        print("✓ 所有测试完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
