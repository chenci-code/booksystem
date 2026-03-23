"""
书籍管理服务类
"""
import logging
from typing import Dict, List, Optional, Any
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.db import transaction
from django.utils import timezone

from ..models import BookName, BookChapter, BookEvaluate, UserBookOwnership
from .exceptions import (
    BookManagementException, BookNotFoundError, BatchOperationError, ValidationError, 
    DuplicateBookError
)

logger = logging.getLogger(__name__)


class BookManagementService:
    """书籍管理服务类"""
    
    def __init__(self):
        self.cache = cache
        self.logger = logger
    
    def search_books(self, query: str = '', filters: Dict = None, pagination: Dict = None) -> Dict:
        """
        搜索和筛选书籍
        
        Args:
            query: 搜索关键词
            filters: 筛选条件 {'category': '', 'status': '', 'author': ''}
            pagination: 分页参数 {'page': 1, 'size': 20}
        
        Returns:
            Dict: 包含书籍列表和分页信息的字典
        """
        try:
            # 构建查询
            books = BookName.objects.all()
            
            # 搜索关键词
            if query:
                books = books.filter(
                    Q(title__icontains=query) | 
                    Q(author__icontains=query) |
                    Q(description__icontains=query)
                )
            
            # 应用筛选条件
            if filters:
                if filters.get('category'):
                    books = books.filter(category=filters['category'])
                if filters.get('status'):
                    books = books.filter(status=filters['status'])
                if filters.get('author'):
                    books = books.filter(author__icontains=filters['author'])
                if filters.get('rating_min'):
                    books = books.filter(rating__gte=filters['rating_min'])
                if filters.get('rating_max'):
                    books = books.filter(rating__lte=filters['rating_max'])
            
            # 排序
            sort_by = filters.get('sort_by', 'create_time') if filters else 'create_time'
            if sort_by == 'popularity':
                books = books.order_by('-collection_count', '-view_count')
            elif sort_by == 'rating':
                books = books.order_by('-rating', '-collection_count')
            elif sort_by == 'update_time':
                books = books.order_by('-update_time')
            else:
                books = books.order_by('-create_time')
            
            # 分页
            if pagination:
                page = pagination.get('page', 1)
                size = pagination.get('size', 20)
                paginator = Paginator(books, size)
                page_obj = paginator.get_page(page)
                
                return {
                    'books': list(page_obj),
                    'total_count': paginator.count,
                    'page_count': paginator.num_pages,
                    'current_page': page,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous(),
                }
            else:
                return {
                    'books': list(books),
                    'total_count': books.count(),
                }
                
        except Exception as e:
            self.logger.error(f"搜索书籍失败: {str(e)}")
            raise BookManagementException(f"搜索失败: {str(e)}")
    
    def get_book_by_id(self, book_id: int) -> BookName:
        """
        根据ID获取书籍
        
        Args:
            book_id: 书籍ID
            
        Returns:
            BookName: 书籍对象
        """
        try:
            return BookName.objects.get(book_id=book_id)
        except BookName.DoesNotExist:
            raise BookNotFoundError(f"书籍ID {book_id} 不存在")
    
    def create_book(self, book_data: Dict) -> BookName:
        """
        创建新书籍
        
        Args:
            book_data: 书籍数据字典
            
        Returns:
            BookName: 创建的书籍对象
        """
        try:
            # 验证必填字段
            required_fields = ['title', 'author', 'category']
            for field in required_fields:
                if not book_data.get(field):
                    raise ValidationError(f"字段 {field} 不能为空")
            
            # 检查书籍是否已存在
            if BookName.objects.filter(
                title=book_data['title'], 
                author=book_data['author']
            ).exists():
                raise DuplicateBookError(f"书籍《{book_data['title']}》已存在")
            
            # 创建书籍
            book = BookName.objects.create(
                title=book_data['title'],
                author=book_data['author'],
                category=book_data['category'],
                status=book_data.get('status', '连载中'),
                description=book_data.get('description', ''),
                word_count=book_data.get('word_count', ''),
                cover_url=book_data.get('cover_url', ''),
                rating=book_data.get('rating', 0.0),
                collection_count=book_data.get('collection_count', 0),
                chapter_count=book_data.get('chapter_count', 0),
            )
            
            self.logger.info(f"创建书籍成功: {book.title} (ID: {book.book_id})")
            return book
            
        except (ValidationError, DuplicateBookError):
            raise
        except Exception as e:
            self.logger.error(f"创建书籍失败: {str(e)}")
            raise BookManagementException(f"创建失败: {str(e)}")
    
    def update_book(self, book_id: int, update_data: Dict) -> BookName:
        """
        更新书籍信息
        
        Args:
            book_id: 书籍ID
            update_data: 更新数据字典
            
        Returns:
            BookName: 更新后的书籍对象
        """
        try:
            book = self.get_book_by_id(book_id)
            
            # 更新字段
            allowed_fields = [
                'title', 'author', 'category', 'status', 'description',
                'word_count', 'cover_url', 'rating', 'collection_count',
                'chapter_count', 'update_time'
            ]
            
            for field, value in update_data.items():
                if field in allowed_fields and hasattr(book, field):
                    setattr(book, field, value)
            
            book.save()
            
            self.logger.info(f"更新书籍成功: {book.title} (ID: {book.book_id})")
            return book
            
        except BookNotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"更新书籍失败: {str(e)}")
            raise BookManagementException(f"更新失败: {str(e)}")
    
    def delete_book(self, book_id: int) -> bool:
        """
        删除书籍
        
        Args:
            book_id: 书籍ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            book = self.get_book_by_id(book_id)
            book_title = book.title
            
            with transaction.atomic():
                # 删除相关章节
                BookChapter.objects.filter(book_title=book.title).delete()
                
                # 删除相关评价
                BookEvaluate.objects.filter(book_title=book.title).delete()
                
                # 删除用户拥有权记录
                UserBookOwnership.objects.filter(book_id=book_id).delete()
                
                # 删除书籍
                book.delete()
            
            self.logger.info(f"删除书籍成功: {book_title} (ID: {book_id})")
            return True
            
        except BookNotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"删除书籍失败: {str(e)}")
            raise BookManagementException(f"删除失败: {str(e)}")
    
    def batch_update_books(self, book_ids: List[int], update_data: Dict) -> Dict:
        """
        批量更新书籍
        
        Args:
            book_ids: 书籍ID列表
            update_data: 更新数据字典
            
        Returns:
            Dict: 操作结果
        """
        try:
            if not book_ids:
                raise ValidationError("书籍ID列表不能为空")
            
            success_count = 0
            failed_books = []
            
            with transaction.atomic():
                for book_id in book_ids:
                    try:
                        self.update_book(book_id, update_data)
                        success_count += 1
                    except Exception as e:
                        failed_books.append({
                            'book_id': book_id,
                            'error': str(e)
                        })
            
            result = {
                'success_count': success_count,
                'failed_count': len(failed_books),
                'failed_books': failed_books,
                'total_count': len(book_ids)
            }
            
            self.logger.info(f"批量更新完成: 成功 {success_count}, 失败 {len(failed_books)}")
            return result
            
        except Exception as e:
            self.logger.error(f"批量更新失败: {str(e)}")
            raise BatchOperationError(f"批量更新失败: {str(e)}")
    
    def batch_delete_books(self, book_ids: List[int]) -> Dict:
        """
        批量删除书籍
        
        Args:
            book_ids: 书籍ID列表
            
        Returns:
            Dict: 操作结果
        """
        try:
            if not book_ids:
                raise ValidationError("书籍ID列表不能为空")
            
            success_count = 0
            failed_books = []
            
            for book_id in book_ids:
                try:
                    self.delete_book(book_id)
                    success_count += 1
                except Exception as e:
                    failed_books.append({
                        'book_id': book_id,
                        'error': str(e)
                    })
            
            result = {
                'success_count': success_count,
                'failed_count': len(failed_books),
                'failed_books': failed_books,
                'total_count': len(book_ids)
            }
            
            self.logger.info(f"批量删除完成: 成功 {success_count}, 失败 {len(failed_books)}")
            return result
            
        except Exception as e:
            self.logger.error(f"批量删除失败: {str(e)}")
            raise BatchOperationError(f"批量删除失败: {str(e)}")
    
    def get_book_statistics(self, book_id: int) -> Dict:
        """
        获取书籍统计信息
        
        Args:
            book_id: 书籍ID
            
        Returns:
            Dict: 统计信息
        """
        try:
            book = self.get_book_by_id(book_id)
            
            # 获取章节统计
            chapter_count = BookChapter.objects.filter(book_title=book.title).count()
            
            # 获取评价统计
            evaluations = BookEvaluate.objects.filter(book_title=book.title)
            evaluation_count = evaluations.count()
            avg_rating = evaluations.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0
            
            # 获取购买统计
            ownership_count = UserBookOwnership.objects.filter(book_id=book_id).count()
            
            # 评分分布
            rating_distribution = {}
            for i in range(1, 6):
                rating_distribution[str(i)] = evaluations.filter(rating=i).count()
            
            stats = {
                'book_id': book_id,
                'title': book.title,
                'author': book.author,
                'chapter_count': chapter_count,
                'evaluation_count': evaluation_count,
                'average_rating': round(avg_rating, 2),
                'ownership_count': ownership_count,
                'collection_count': book.collection_count,
                'view_count': getattr(book, 'view_count', 0),
                'rating_distribution': rating_distribution,
                'create_time': book.create_time,
                'update_time': book.update_time,
            }
            
            return stats
            
        except BookNotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"获取书籍统计失败: {str(e)}")
            raise BookManagementException(f"获取统计失败: {str(e)}")
    
    def get_categories(self) -> List[str]:
        """
        获取所有书籍分类
        
        Returns:
            List[str]: 分类列表
        """
        try:
            categories = BookName.objects.values_list('category', flat=True).distinct()
            return list(categories)
        except Exception as e:
            self.logger.error(f"获取分类列表失败: {str(e)}")
            return []
    
    def get_authors(self) -> List[str]:
        """
        获取所有作者
        
        Returns:
            List[str]: 作者列表
        """
        try:
            authors = BookName.objects.values_list('author', flat=True).distinct()
            return list(authors)
        except Exception as e:
            self.logger.error(f"获取作者列表失败: {str(e)}")
            return []