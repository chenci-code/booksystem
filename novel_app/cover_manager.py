"""
书籍封面管理模块
负责下载、存储和管理书籍封面图片
"""

import os
import requests
import hashlib
import logging
from pathlib import Path
from urllib.parse import urlparse

# 处理Django环境
try:
    from django.conf import settings
except:
    # 如果不在Django环境中，使用默认设置
    class Settings:
        MEDIA_ROOT = os.path.join(os.path.dirname(__file__), '..', '..', 'media')
    settings = Settings()

try:
    from .models import BookName
except:
    BookName = None

logger = logging.getLogger(__name__)


class CoverManager:
    """书籍封面管理器"""
    
    # 封面存储目录
    COVER_DIR = 'book_covers'
    
    # 支持的图片格式
    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.webp'}
    
    # 最大文件大小 (5MB)
    MAX_FILE_SIZE = 5 * 1024 * 1024
    
    # 请求超时时间
    REQUEST_TIMEOUT = 10
    
    # 默认封面
    DEFAULT_COVER = 'book_covers/default-cover.png'
    
    @classmethod
    def download_cover(cls, book_id: int, cover_url: str) -> str:
        """
        下载书籍封面到本地
        
        Args:
            book_id: 书籍ID
            cover_url: 封面URL
            
        Returns:
            本地封面路径（相对于MEDIA_ROOT）
        """
        if not cover_url or not cover_url.strip():
            return cls.DEFAULT_COVER
        
        try:
            # 验证URL
            if not cls._is_valid_url(cover_url):
                logger.warning(f"无效的封面URL: {cover_url}")
                return cls.DEFAULT_COVER
            
            # 下载图片
            response = requests.get(
                cover_url,
                timeout=cls.REQUEST_TIMEOUT,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                },
                verify=False  # 忽略SSL证书验证
            )
            response.raise_for_status()
            
            # 检查文件大小
            if len(response.content) > cls.MAX_FILE_SIZE:
                logger.warning(f"封面文件过大: {cover_url}")
                return cls.DEFAULT_COVER
            
            # 获取文件扩展名
            ext = cls._get_file_extension(cover_url, response)
            if ext not in cls.SUPPORTED_FORMATS:
                logger.warning(f"不支持的图片格式: {ext}")
                return cls.DEFAULT_COVER
            
            # 生成本地文件名
            filename = cls._generate_filename(book_id, ext)
            
            # 保存文件
            local_path = cls._save_cover_file(filename, response.content)
            
            logger.info(f"成功下载封面: {book_id} -> {local_path}")
            return local_path
            
        except requests.RequestException as e:
            logger.error(f"下载封面失败 ({cover_url}): {e}")
            return cls.DEFAULT_COVER
        except Exception as e:
            logger.error(f"处理封面时出错 ({cover_url}): {e}")
            return cls.DEFAULT_COVER
    
    @classmethod
    def _is_valid_url(cls, url: str) -> bool:
        """验证URL是否有效"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    @classmethod
    def _get_file_extension(cls, url: str, response) -> str:
        """获取文件扩展名"""
        # 从URL获取扩展名
        parsed_url = urlparse(url)
        path = parsed_url.path
        if '.' in path:
            ext = '.' + path.split('.')[-1].lower()
            if ext in cls.SUPPORTED_FORMATS:
                return ext
        
        # 从Content-Type获取扩展名
        content_type = response.headers.get('content-type', '').lower()
        type_map = {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/webp': '.webp',
        }
        
        for mime_type, ext in type_map.items():
            if mime_type in content_type:
                return ext
        
        # 默认为jpg
        return '.jpg'
    
    @classmethod
    def _generate_filename(cls, book_id: int, ext: str) -> str:
        """生成本地文件名"""
        return f"book_{book_id}{ext}"
    
    @classmethod
    def _save_cover_file(cls, filename: str, content: bytes) -> str:
        """保存封面文件到本地"""
        # 创建目录
        cover_dir = os.path.join(settings.MEDIA_ROOT, cls.COVER_DIR)
        os.makedirs(cover_dir, exist_ok=True)
        
        # 保存文件
        filepath = os.path.join(cover_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(content)
        
        # 返回相对于MEDIA_ROOT的路径
        return os.path.join(cls.COVER_DIR, filename)
    
    @classmethod
    def update_book_cover(cls, book_id: int, cover_url: str) -> bool:
        """
        更新书籍封面

        Args:
            book_id: 书籍ID
            cover_url: 新的封面URL

        Returns:
            是否更新成功
        """
        if BookName is None:
            logger.error("BookName模型不可用")
            return False

        try:
            book = BookName.objects.get(book_id=book_id)

            # 下载新封面
            local_path = cls.download_cover(book_id, cover_url)

            # 更新数据库
            book.cover_url = local_path
            book.save()

            logger.info(f"成功更新书籍 {book_id} 的封面")
            return True

        except BookName.DoesNotExist:
            logger.error(f"书籍不存在: {book_id}")
            return False
        except Exception as e:
            logger.error(f"更新书籍封面失败: {e}")
            return False
    
    @classmethod
    def batch_download_covers(cls, books_data: list) -> dict:
        """
        批量下载书籍封面
        
        Args:
            books_data: 书籍数据列表，每项包含 book_id 和 cover_url
            
        Returns:
            下载结果统计
        """
        stats = {
            'total': len(books_data),
            'success': 0,
            'failed': 0,
            'skipped': 0,
        }
        
        for book_data in books_data:
            book_id = book_data.get('book_id')
            cover_url = book_data.get('cover_url')
            
            if not book_id or not cover_url:
                stats['skipped'] += 1
                continue
            
            try:
                local_path = cls.download_cover(book_id, cover_url)
                if local_path != cls.DEFAULT_COVER:
                    stats['success'] += 1
                else:
                    stats['failed'] += 1
            except Exception as e:
                logger.error(f"下载书籍 {book_id} 的封面失败: {e}")
                stats['failed'] += 1
        
        return stats

