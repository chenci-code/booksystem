"""
书籍相关视图服务
处理书籍浏览、搜索、详情等功能
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Avg
from django.http import JsonResponse
import logging

from ..models import BookName, BookChapter, BookEvaluate, UserBookOwnership
from ..auth_utils import get_current_user
from ..business_utils import check_book_access, check_chapter_access

logger = logging.getLogger(__name__)


def book_list_view(request):
    """
    书籍列表视图
    支持分类筛选、搜索、排序、分页
    """
    # 获取筛选参数
    category = request.GET.get('category', '')
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', 'update_time')  # 默认按更新时间排序
    page_number = request.GET.get('page', 1)
    
    # 基础查询
    books = BookName.objects.all()
    
    # 分类筛选
    if category:
        books = books.filter(category=category)
    
    # 搜索功能
    if search_query:
        books = books.filter(
            Q(title__icontains=search_query) |
            Q(author__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # 排序
    sort_options = {
        'update_time': '-update_time',
        'rating': '-rating',
        'collection': '-collection_count',
        'view': '-view_count',
        'purchase': '-purchase_count',
        'price_asc': 'price',
        'price_desc': '-price'
    }
    books = books.order_by(sort_options.get(sort_by, '-update_time'))
    
    # 分页
    paginator = Paginator(books, 20)  # 每页20本书
    page_obj = paginator.get_page(page_number)
    
    # 获取所有分类
    categories = BookName.objects.values_list('category', flat=True).distinct()
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'current_category': category,
        'search_query': search_query,
        'sort_by': sort_by,
        'total_count': paginator.count
    }
    
    return render(request, 'novel_app/book_list.html', context)


def book_detail_view(request, book_id):
    """
    书籍详情视图
    显示书籍详细信息、章节列表、评价等
    """
    book = get_object_or_404(BookName, book_id=book_id)
    user = get_current_user(request)
    
    # 增加浏览量
    book.increment_view_count()
    
    # 检查访问权限
    access_info = check_book_access(user, book)
    
    # 获取章节列表
    chapters = BookChapter.objects.filter(
        book_title=book.title
    ).order_by('chapter_number')
    
    # 获取评价列表
    evaluations = BookEvaluate.objects.filter(
        book_title=book.title
    ).order_by('-create_time')[:10]
    
    # 计算平均评分
    avg_rating = evaluations.aggregate(Avg('rating'))['rating__avg'] or 0
    
    # 获取用户的评价
    user_evaluation = None
    if user:
        user_evaluation = BookEvaluate.objects.filter(
            customer_name=user.name,
            book_title=book.title
        ).first()
    
    # 获取阅读进度
    reading_progress = 0
    if user and access_info['has_access']:
        ownership = UserBookOwnership.objects.filter(
            user_id=user.user_id,
            book_id=book.book_id
        ).first()
        if ownership:
            reading_progress = ownership.reading_progress or 0
    
    # 推荐相似书籍
    similar_books = BookName.objects.filter(
        category=book.category
    ).exclude(
        book_id=book.book_id
    ).order_by('-rating')[:6]
    
    context = {
        'book': book,
        'access_info': access_info,
        'chapters': chapters,
        'evaluations': evaluations,
        'avg_rating': round(avg_rating, 2),
        'user_evaluation': user_evaluation,
        'reading_progress': reading_progress,
        'similar_books': similar_books,
        'chapter_count': chapters.count()
    }
    
    return render(request, 'novel_app/book_detail.html', context)


def chapter_read_view(request, book_id, chapter_number):
    """
    章节阅读视图
    """
    book = get_object_or_404(BookName, book_id=book_id)
    user = get_current_user(request)
    
    # 检查章节访问权限
    access_info = check_chapter_access(user, book, chapter_number)
    
    if not access_info['can_read']:
        messages.warning(request, access_info['message'])
        return redirect('book_detail', book_id=book_id)
    
    # 获取章节内容
    chapter = get_object_or_404(
        BookChapter,
        book_title=book.title,
        chapter_number=chapter_number
    )
    
    # 读取章节内容
    chapter_content = chapter.chapter_content
    if not chapter_content and chapter.content_file_path:
        try:
            with open(chapter.content_file_path, 'r', encoding='utf-8') as f:
                chapter_content = f.read()
        except Exception as e:
            logger.error(f"读取章节文件失败: {str(e)}")
            chapter_content = "章节内容加载失败"
    
    # 更新阅读进度
    if user and access_info['can_read']:
        from ..business_utils import update_reading_progress
        update_reading_progress(user, book, chapter_number)
    
    # 获取上一章和下一章
    prev_chapter = BookChapter.objects.filter(
        book_title=book.title,
        chapter_number__lt=chapter_number
    ).order_by('-chapter_number').first()
    
    next_chapter = BookChapter.objects.filter(
        book_title=book.title,
        chapter_number__gt=chapter_number
    ).order_by('chapter_number').first()
    
    context = {
        'book': book,
        'chapter': chapter,
        'chapter_content': chapter_content,
        'prev_chapter': prev_chapter,
        'next_chapter': next_chapter,
        'access_info': access_info
    }
    
    return render(request, 'novel_app/chapter_read.html', context)


def book_search_api(request):
    """
    书籍搜索API
    支持模糊搜索书名、作者、描述
    """
    search_query = request.GET.get('q', '')
    limit = int(request.GET.get('limit', 10))
    
    if not search_query:
        return JsonResponse({
            'success': False,
            'message': '请输入搜索关键词'
        }, status=400)
    
    try:
        books = BookName.objects.filter(
            Q(title__icontains=search_query) |
            Q(author__icontains=search_query) |
            Q(description__icontains=search_query)
        )[:limit]
        
        results = []
        for book in books:
            results.append({
                'book_id': book.book_id,
                'title': book.title,
                'author': book.author,
                'category': book.category,
                'cover_url': book.cover_url,
                'rating': float(book.rating),
                'price': float(book.price)
            })
        
        return JsonResponse({
            'success': True,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"搜索失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'搜索失败: {str(e)}'
        }, status=500)


def book_categories_api(request):
    """
    获取所有书籍分类API
    """
    try:
        categories = BookName.objects.values('category').annotate(
            count=Count('book_id')
        ).order_by('-count')
        
        results = []
        for cat in categories:
            results.append({
                'category': cat['category'],
                'count': cat['count']
            })
        
        return JsonResponse({
            'success': True,
            'categories': results
        })
        
    except Exception as e:
        logger.error(f"获取分类失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'获取分类失败: {str(e)}'
        }, status=500)


def book_recommendations_api(request):
    """
    获取推荐书籍API
    基于用户偏好或热门书籍
    """
    user = get_current_user(request)
    limit = int(request.GET.get('limit', 10))
    
    try:
        if user:
            # 基于用户偏好推荐
            collected_books = user.get_collected_books()
            if collected_books:
                book_ids = [b.get('book_id') for b in collected_books if b.get('book_id')]
                categories = BookName.objects.filter(
                    book_id__in=book_ids
                ).values_list('category', flat=True).distinct()
                
                if categories:
                    books = BookName.objects.filter(
                        category__in=categories
                    ).exclude(
                        book_id__in=book_ids
                    ).order_by('-rating', '-collection_count')[:limit]
                else:
                    books = BookName.objects.order_by('-rating')[:limit]
            else:
                books = BookName.objects.order_by('-rating')[:limit]
        else:
            # 未登录用户显示热门书籍
            books = BookName.objects.order_by('-collection_count')[:limit]
        
        results = []
        for book in books:
            results.append({
                'book_id': book.book_id,
                'title': book.title,
                'author': book.author,
                'category': book.category,
                'cover_url': book.cover_url,
                'rating': float(book.rating),
                'price': float(book.price),
                'collection_count': book.collection_count
            })
        
        return JsonResponse({
            'success': True,
            'recommendations': results
        })
        
    except Exception as e:
        logger.error(f"获取推荐失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'获取推荐失败: {str(e)}'
        }, status=500)
