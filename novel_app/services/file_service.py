"""
文件管理服务类
"""
import os
import logging
from typing import Dict, List, Optional, Tuple
from PIL import Image
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone
import uuid

from .exceptions import FileUploadError, ValidationError

logger = logging.getLogger(__name__)


class FileManagementService:
    """文件管理服务类"""
    
    # 允许的图片格式
    ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
    ALLOWED_MIME_TYPES = {
        'image/jpeg', 'image/png', 'image/webp', 'image/gif'
    }
    
    # 文件大小限制 (5MB)
    MAX_FILE_SIZE = 5 * 1024 * 1024
    
    # 缩略图尺寸
    THUMBNAIL_SIZES = {
        'small': (150, 200),    # 小缩略图
        'medium': (300, 400),   # 中等缩略图
        'large': (600, 800),    # 大缩略图
    }
    
    def __init__(self):
        self.logger = logger
        self.storage = default_storage
        
        # 确保上传目录存在
        self.upload_dir = 'book_covers'
        self.thumbnail_dir = 'book_thumbnails'
        
    def validate_image_file(self, file) -> bool:
        """
        验证图片文件
        
        Args:
            file: 上传的文件对象
            
        Returns:
            bool: 验证是否通过
        """
        try:
            # 检查文件大小
            if file.size > self.MAX_FILE_SIZE:
                raise ValidationError(f"文件大小超过限制 ({self.MAX_FILE_SIZE / 1024 / 1024:.1f}MB)")
            
            # 检查文件扩展名
            file_ext = os.path.splitext(file.name)[1].lower()
            if file_ext not in self.ALLOWED_IMAGE_EXTENSIONS:
                raise ValidationError(f"不支持的文件格式: {file_ext}")
            
            # 检查MIME类型
            if hasattr(file, 'content_type') and file.content_type:
                if file.content_type not in self.ALLOWED_MIME_TYPES:
                    raise ValidationError(f"不支持的文件类型: {file.content_type}")
            
            # 尝试打开图片验证格式
            try:
                image = Image.open(file)
                image.verify()
                file.seek(0)  # 重置文件指针
                return True
            except Exception:
                raise ValidationError("文件不是有效的图片格式")
                
        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"文件验证失败: {str(e)}")
            raise FileUploadError(f"文件验证失败: {str(e)}")
    
    def generate_unique_filename(self, original_filename: str) -> str:
        """
        生成唯一的文件名
        
        Args:
            original_filename: 原始文件名
            
        Returns:
            str: 唯一文件名
        """
        file_ext = os.path.splitext(original_filename)[1].lower()
        unique_id = str(uuid.uuid4())
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        return f"{timestamp}_{unique_id}{file_ext}"
    
    def upload_cover_image(self, file, book_id: int) -> Dict:
        """
        上传书籍封面图片
        
        Args:
            file: 上传的文件对象
            book_id: 书籍ID
            
        Returns:
            Dict: 上传结果信息
        """
        try:
            # 验证文件
            self.validate_image_file(file)
            
            # 生成文件名
            filename = self.generate_unique_filename(file.name)
            file_path = f"{self.upload_dir}/{filename}"
            
            # 保存原图
            saved_path = self.storage.save(file_path, file)
            
            # 获取文件信息
            file_info = {
                'original_name': file.name,
                'saved_name': filename,
                'file_path': saved_path,
                'file_size': file.size,
                'mime_type': getattr(file, 'content_type', 'image/jpeg'),
                'book_id': book_id,
                'upload_time': timezone.now(),
            }
            
            # 生成缩略图
            thumbnails = self.generate_thumbnails(saved_path, filename)
            file_info['thumbnails'] = thumbnails
            
            self.logger.info(f"封面上传成功: {filename} for book {book_id}")
            return file_info
            
        except (ValidationError, FileUploadError):
            raise
        except Exception as e:
            self.logger.error(f"封面上传失败: {str(e)}")
            raise FileUploadError(f"上传失败: {str(e)}")
    
    def generate_thumbnails(self, original_path: str, original_filename: str) -> Dict:
        """
        生成缩略图
        
        Args:
            original_path: 原图路径
            original_filename: 原图文件名
            
        Returns:
            Dict: 缩略图信息
        """
        thumbnails = {}
        
        try:
            # 打开原图
            with self.storage.open(original_path, 'rb') as f:
                image = Image.open(f)
                
                # 转换为RGB模式（处理RGBA等格式）
                if image.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', image.size, (255, 255, 255))
                    if image.mode == 'P':
                        image = image.convert('RGBA')
                    background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                    image = background
                
                # 生成各种尺寸的缩略图
                for size_name, (width, height) in self.THUMBNAIL_SIZES.items():
                    try:
                        # 创建缩略图
                        thumbnail = image.copy()
                        thumbnail.thumbnail((width, height), Image.Resampling.LANCZOS)
                        
                        # 生成缩略图文件名
                        name_without_ext = os.path.splitext(original_filename)[0]
                        ext = os.path.splitext(original_filename)[1]
                        thumbnail_filename = f"{name_without_ext}_{size_name}{ext}"
                        thumbnail_path = f"{self.thumbnail_dir}/{thumbnail_filename}"
                        
                        # 保存缩略图
                        from io import BytesIO
                        thumbnail_io = BytesIO()
                        thumbnail.save(thumbnail_io, format='JPEG', quality=85)
                        thumbnail_content = ContentFile(thumbnail_io.getvalue())
                        
                        saved_thumbnail_path = self.storage.save(thumbnail_path, thumbnail_content)
                        
                        thumbnails[size_name] = {
                            'filename': thumbnail_filename,
                            'path': saved_thumbnail_path,
                            'width': thumbnail.width,
                            'height': thumbnail.height,
                            'size': len(thumbnail_io.getvalue())
                        }
                        
                    except Exception as e:
                        self.logger.warning(f"生成 {size_name} 缩略图失败: {str(e)}")
                        continue
                        
        except Exception as e:
            self.logger.error(f"生成缩略图失败: {str(e)}")
            # 缩略图生成失败不影响主流程
            
        return thumbnails
    
    def delete_book_files(self, book_id: int, file_paths: List[str] = None) -> bool:
        """
        删除书籍相关文件
        
        Args:
            book_id: 书籍ID
            file_paths: 要删除的文件路径列表，如果为None则删除所有相关文件
            
        Returns:
            bool: 删除是否成功
        """
        try:
            deleted_count = 0
            
            if file_paths:
                # 删除指定文件
                for file_path in file_paths:
                    try:
                        if self.storage.exists(file_path):
                            self.storage.delete(file_path)
                            deleted_count += 1
                    except Exception as e:
                        self.logger.warning(f"删除文件失败 {file_path}: {str(e)}")
            else:
                # 删除所有相关文件（需要从数据库查询）
                # 这里简化处理，实际应该从BookFile模型查询
                pass
            
            self.logger.info(f"删除书籍 {book_id} 的 {deleted_count} 个文件")
            return True
            
        except Exception as e:
            self.logger.error(f"删除书籍文件失败: {str(e)}")
            return False
    
    def get_file_url(self, file_path: str) -> str:
        """
        获取文件访问URL
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 文件URL
        """
        try:
            return self.storage.url(file_path)
        except Exception as e:
            self.logger.error(f"获取文件URL失败: {str(e)}")
            return ''
    
    def get_file_info(self, file_path: str) -> Dict:
        """
        获取文件信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict: 文件信息
        """
        try:
            if not self.storage.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            file_size = self.storage.size(file_path)
            file_url = self.get_file_url(file_path)
            
            # 尝试获取图片尺寸
            width, height = 0, 0
            try:
                with self.storage.open(file_path, 'rb') as f:
                    image = Image.open(f)
                    width, height = image.size
            except Exception:
                pass
            
            return {
                'path': file_path,
                'url': file_url,
                'size': file_size,
                'width': width,
                'height': height,
                'exists': True
            }
            
        except Exception as e:
            self.logger.error(f"获取文件信息失败: {str(e)}")
            return {
                'path': file_path,
                'url': '',
                'size': 0,
                'width': 0,
                'height': 0,
                'exists': False,
                'error': str(e)
            }