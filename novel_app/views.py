from django.shortcuts import render, get_object_or_404, redirect
import os
import logging
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Count, Sum, F, FloatField, Value
from django.db.models.functions import Cast
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings
from functools import wraps
import json
import random
import string
from datetime import datetime

from .models import (
    BookName, BookChapter, UserProfile, UserBookOwnership,
    BookOrder, BookShoppingCart, BookEvaluate, Admin, CartItem
)
from .crawler_service import DjangoBookCrawlerService
from .crawler_monitor import CrawlerTask, CrawlerMonitor
from .auth_utils import (
    get_current_user, get_current_admin, login_required, 
    admin_required, get_client_ip, get_user_agent
)
from .business_utils import (
    check_book_access, check_chapter_access, purchase_book,
    calculate_cart_total, update_reading_progress, generate_order_number
)

# 配置日志
logger = logging.getLogger(__name__)


# 注意：以下旧函数已被 auth_utils 和 business_utils 中的新函数替代
# 保留这些函数是为了向后兼容，但建议使用新的工具函数

def user_has_book_access(user: UserProfile, book: BookName) -> bool:
    """
    统一的书籍访问权限检查（已废弃，请使用 business_utils.check_book_access）
    保留此函数仅为向后兼容
    """
    access_info = check_book_access(user, book)
    return access_info.get('has_access', False)


def get_book_access_info(request, book):
    """
    获取书籍访问信息（已废弃，请使用 business_utils.check_book_access）
    保留此函数仅为向后兼容
    """
    user = get_current_user(request)
    return check_book_access(user, book)


def index(request):
    """首页视图"""
    try:
        import random
        from django.db.models import Q
        
        # 获取每日推荐书籍（随机推荐，每次刷新都不同）
        all_books = list(BookName.objects.all())
        if len(all_books) >= 4:
            rotating_books = random.sample(all_books, min(4, len(all_books)))
        else:
            rotating_books = all_books
        
        # 获取推荐书籍
        featured_books = BookName.objects.filter(status='连载中').order_by('-collection_count')[:6]
        
        # 获取最新更新的书籍
        latest_books = BookName.objects.order_by('-update_time')[:8]
        
        # 获取热门书籍
        popular_books = BookName.objects.order_by('-collection_count')[:8]
        
        # 获取高分书籍（评分4.0+）
        high_rated_books = BookName.objects.filter(rating__gte=4.0).order_by('-rating')[:8]
        
        # 获取协同推荐（如果用户已登录，基于用户偏好；否则显示热门）
        collaborative_books = None
        user = get_current_user(request)
        if user:
            # 基于用户阅读偏好推荐（简化版：推荐用户收藏的书籍的同类书籍）
            try:
                collected_books = user.get_collected_books()
                if collected_books:
                    # 获取用户收藏书籍的分类
                    categories = BookName.objects.filter(
                        book_id__in=[b.get('book_id') for b in collected_books if b.get('book_id')]
                    ).values_list('category', flat=True).distinct()
                    if categories:
                        collaborative_books = BookName.objects.filter(
                            category__in=categories
                        ).exclude(
                            book_id__in=[b.get('book_id') for b in collected_books if b.get('book_id')]
                        ).order_by('-rating', '-collection_count')[:8]
            except Exception as e:
                logger.warning(f"获取协同推荐失败: {e}")
        
        if not collaborative_books:
            collaborative_books = popular_books[:8]
        
        context = {
            'rotating_books': rotating_books,
            'featured_books': featured_books,
            'latest_books': latest_books,
            'popular_books': popular_books,
            'high_rated_books': high_rated_books,
            'collaborative_books': collaborative_books,
        }
        
        return render(request, 'novel_app/index.html', context)
        
    except Exception as e:
        logger.error(f"首页加载失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        messages.error(request, '页面加载失败，请稍后重试')
        return render(request, 'novel_app/index.html', {
            'rotating_books': [],
            'featured_books': [],
            'latest_books': [],
            'popular_books': [],
            'high_rated_books': [],
            'collaborative_books': [],
        })


def book_list(request):
    """书籍列表页面"""
    try:
        from datetime import timedelta
        
        # 获取搜索和筛选参数
        search_query = request.GET.get('search', '')
        channel = request.GET.get('channel', '')
        category = request.GET.get('category', '')
        word_count = request.GET.get('word_count', '')
        update_time = request.GET.get('update_time', '')
        status = request.GET.get('status', '')
        
        # 频道和分类的映射关系
        channel_category_mapping = {
            '女生原创': ['现代言情', '古代言情', '幻想言情', '游戏竞技', '衍生言情', '现实主义'],
            '男生原创': ['历史', '军事', '科幻', '游戏', '玄幻奇幻', '都市', '奇闻异事', '武侠仙侠', '体育', 'N次元', '现实题材'],
            '出版图书': ['文学艺术', '人文社科', '经管励志', '经典文学', '出版小说', '少儿教育']
        }
        
        # 构建查询
        books = BookName.objects.all()
        
        # 搜索
        if search_query:
            books = books.filter(
                Q(title__icontains=search_query) | 
                Q(author__icontains=search_query)
            )
        
        # 频道筛选（通过分类映射）
        if channel and channel in channel_category_mapping:
            allowed_categories = channel_category_mapping[channel]
            books = books.filter(category__in=allowed_categories)
        
        # 分类筛选
        if category:
            books = books.filter(category=category)
        
        # 作品字数筛选
        # 注意：word_count是字符串字段，格式可能不统一（如"92.07万字"、"100万"等）
        # 这里使用简单的字符串匹配，如果需要更精确的筛选，需要解析数字
        if word_count:
            if word_count == '30万以下':
                # 筛选小于30万的书籍（排除包含30、50、100、200等大数字的记录）
                # 使用exclude来排除大数字
                books = books.exclude(
                    Q(word_count__icontains='30') | 
                    Q(word_count__icontains='50') | 
                    Q(word_count__icontains='100') | 
                    Q(word_count__icontains='200')
                )
            elif word_count == '30万-50万':
                books = books.filter(
                    Q(word_count__icontains='30') | 
                    Q(word_count__icontains='40') | 
                    Q(word_count__icontains='50')
                ).exclude(
                    Q(word_count__icontains='100') | 
                    Q(word_count__icontains='200')
                )
            elif word_count == '50万-100万':
                books = books.filter(
                    Q(word_count__icontains='50') | 
                    Q(word_count__icontains='60') | 
                    Q(word_count__icontains='70') | 
                    Q(word_count__icontains='80') | 
                    Q(word_count__icontains='90') | 
                    Q(word_count__icontains='100')
                ).exclude(
                    Q(word_count__icontains='200')
                )
            elif word_count == '100万-200万':
                books = books.filter(
                    Q(word_count__icontains='100') | 
                    Q(word_count__icontains='150') | 
                    Q(word_count__icontains='200')
                ).exclude(
                    Q(word_count__icontains='300') | 
                    Q(word_count__icontains='400') | 
                    Q(word_count__icontains='500')
                )
            elif word_count == '200万以上':
                books = books.filter(
                    Q(word_count__icontains='200') | 
                    Q(word_count__icontains='300') | 
                    Q(word_count__icontains='400') | 
                    Q(word_count__icontains='500') |
                    Q(word_count__icontains='600') |
                    Q(word_count__icontains='700') |
                    Q(word_count__icontains='800') |
                    Q(word_count__icontains='900') |
                    Q(word_count__icontains='1000')
                )
        
        # 更新时间筛选
        if update_time:
            now = timezone.now()
            if update_time == '3天内':
                books = books.filter(update_time__gte=now - timedelta(days=3))
            elif update_time == '7天内':
                books = books.filter(update_time__gte=now - timedelta(days=7))
            elif update_time == '30天内':
                books = books.filter(update_time__gte=now - timedelta(days=30))
        
        # 是否完结筛选
        if status:
            if status == '已完结':
                books = books.filter(status='完结')
            elif status == '连载中':
                books = books.filter(status='连载中')
        
        # 排序
        sort_by = request.GET.get('sort', 'update_time')
        if sort_by == 'popularity':
            books = books.order_by('-collection_count')
        elif sort_by == 'rating':
            books = books.order_by('-rating')
        else:
            books = books.order_by('-update_time')
        
        # 分页
        paginator = Paginator(books, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # 获取分类列表
        categories = BookName.objects.values_list('category', flat=True).distinct()
        
        context = {
            'page_obj': page_obj,
            'search': search_query,
            'current_channel': channel,
            'current_category': category,
            'current_word_count': word_count,
            'current_update_time': update_time,
            'current_status': status,
            'sort': sort_by,
            'categories': categories,
        }
        
        return render(request, 'novel_app/book_list.html', context)
        
    except Exception as e:
        logger.error(f"书籍列表加载失败: {str(e)}")
        messages.error(request, '页面加载失败，请稍后重试')
        return render(request, 'novel_app/book_list.html', {'page_obj': None})


def book_detail(request, book_id):
    """书籍详情页面"""
    try:
        book = get_object_or_404(BookName, book_id=book_id)
        
        # 获取当前用户
        user = get_current_user(request)
        
        # 获取用户访问权限信息
        access_info = check_book_access(user, book)
        
        # 检查是否在书架中
        is_in_bookshelf = False
        is_collected = False
        
        if user:
            bookshelf_books = user.get_bookshelf_books()
            is_in_bookshelf = book.title in bookshelf_books
            
            collected_books = user.get_collected_books()
            is_collected = any(
                (isinstance(item, dict) and item.get('book_title') == book.title) or 
                (isinstance(item, str) and item == book.title)
                for item in collected_books
            )
        
        # 获取章节列表
        chapters = BookChapter.objects.filter(book_title=book.title).order_by('chapter_number')
        total_chapters = chapters.count()
        
        # 获取评价（使用分页）
        reviews_queryset = BookEvaluate.objects.filter(book_title=book.title).order_by('-create_time')
        total_reviews = reviews_queryset.count()
        
        # 对评论进行分页
        review_page = request.GET.get('review_page', 1)
        reviews_paginator = Paginator(reviews_queryset, 10)
        try:
            reviews = reviews_paginator.page(review_page)
        except:
            reviews = reviews_paginator.page(1)
        
        # 检查当前用户是否已发表评价
        user_has_review = False
        user_review = None
        if user:
            user_review = BookEvaluate.objects.filter(
                book_title=book.title,
                customer_name=user.username
            ).first()
            user_has_review = user_review is not None
        
        # 获取用户已购买的章节（如果用户已登录）
        purchased_chapters = []
        if user and access_info.get('has_access'):
            # 如果用户拥有整本书，所有章节都是已购买的
            purchased_chapters = list(chapters.values_list('chapter_number', flat=True))
        
        context = {
            'book': book,
            'chapters': chapters,
            'total_chapters': total_chapters,
            'reviews': reviews,
            'total_reviews': total_reviews,
            'user_has_review': user_has_review,
            'user_review': user_review,
            'access_info': access_info,
            'is_in_bookshelf': is_in_bookshelf,
            'is_collected': is_collected,
            'purchased_chapters': purchased_chapters,
            'user_profile': user,
        }
        
        return render(request, 'novel_app/book_detail.html', context)
        
    except Exception as e:
        logger.error(f"书籍详情加载失败: {str(e)}")
        messages.error(request, '书籍不存在或加载失败')
        return redirect('book_list')


def chapter_detail(request, book_id, chapter_number):
    """章节详情页面"""
    try:
        book = get_object_or_404(BookName, book_id=book_id)
        chapter = get_object_or_404(BookChapter, book_title=book.title, chapter_number=chapter_number)
        
        # 获取当前用户
        user = get_current_user(request)
        
        # 检查章节访问权限
        chapter_access = check_chapter_access(user, book, chapter_number, free_chapters=2)
        
        if not chapter_access['can_read']:
            if not user:
                messages.warning(request, '请先登录')
                return redirect('login')
            else:
                messages.warning(request, '您需要购买此书籍才能阅读此章节')
                return redirect('book_detail', book_id=book_id)
        
        # 更新阅读进度
        if user and not chapter_access['is_free']:
            update_reading_progress(user, book, chapter_number)
        
        # 读取章节内容
        chapter_content = None
        if chapter.chapter_content:
            chapter_content = chapter.chapter_content
        elif chapter.content_file_path:
            # 尝试从文件读取
            try:
                import os
                from django.conf import settings
                full_path = os.path.join(settings.MEDIA_ROOT, chapter.content_file_path)
                if os.path.exists(full_path):
                    with open(full_path, 'r', encoding='utf-8') as f:
                        chapter_content = f.read()
                        # 同时更新数据库中的内容
                        chapter.chapter_content = chapter_content
                        chapter.save(update_fields=['chapter_content'])
            except Exception as e:
                logger.warning(f"从文件读取章节内容失败: {e}")
        
        # 获取上一章和下一章
        prev_chapter = BookChapter.objects.filter(
            book_title=book.title, 
            chapter_number__lt=chapter_number
        ).order_by('-chapter_number').first()
        
        next_chapter = BookChapter.objects.filter(
            book_title=book.title, 
            chapter_number__gt=chapter_number
        ).order_by('chapter_number').first()
        
        # 检查下一章是否已购买
        next_chapter_purchased = False
        if next_chapter and user:
            next_chapter_access = check_chapter_access(user, book, next_chapter.chapter_number, free_chapters=2)
            next_chapter_purchased = next_chapter_access['can_read']
        
        # 获取书籍访问信息（用于显示VIP状态等）
        access_info = check_book_access(user, book)
        
        context = {
            'book': book,
            'chapter': chapter,
            'chapter_content': chapter_content,
            'prev_chapter': prev_chapter,
            'next_chapter': next_chapter,
            'can_read': chapter_access['can_read'],
            'is_free_chapter': chapter_access['is_free'],
            'is_vip_user': access_info.get('is_vip', False),
            'has_purchased': access_info.get('has_access', False),
            'next_chapter_purchased': next_chapter_purchased,
            'access_info': access_info,
        }
        
        return render(request, 'novel_app/chapter_detail.html', context)
        
    except BookChapter.DoesNotExist:
        logger.error(f"章节不存在: book_id={book_id}, chapter_number={chapter_number}")
        messages.error(request, '章节不存在')
        return redirect('book_detail', book_id=book_id)
    except Exception as e:
        logger.error(f"章节详情加载失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        messages.error(request, '章节加载失败，请稍后重试')
        return redirect('book_detail', book_id=book_id)


def login(request):
    """登录页面 - 使用安全的密码验证"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if not username or not password:
            messages.error(request, '用户名和密码不能为空')
            return render(request, 'novel_app/login.html')
        
        try:
            # 检查管理员登录
            try:
                admin = Admin.objects.get(username=username)
                if admin.check_password(password):
                    # 更新最后登录时间
                    admin.last_login_time = timezone.now()
                    admin.save(update_fields=['last_login_time'])
                    
                    request.session['username'] = username
                    request.session['name'] = admin.username
                    request.session['is_admin'] = True
                    request.session['user_id'] = admin.admin_id
                    messages.success(request, f'欢迎管理员 {admin.username}！')
                    return redirect('admin_dashboard')
            except Admin.DoesNotExist:
                pass
            
            # 检查普通用户登录
            try:
                user = UserProfile.objects.get(username=username)
                if user.status == '禁用':
                    messages.error(request, '该账户已被禁用，请联系管理员')
                    return render(request, 'novel_app/login.html')
                
                if user.check_password(password):
                    # 更新最后登录时间
                    user.last_login_time = timezone.now()
                    user.save(update_fields=['last_login_time'])
                    
                    request.session['username'] = username
                    request.session['name'] = user.name
                    request.session['is_admin'] = False
                    request.session['user_id'] = user.user_id
                    messages.success(request, f'欢迎 {user.name}！')
                    return redirect('index')
            except UserProfile.DoesNotExist:
                pass
            
            # 如果到这里说明用户名或密码错误
            messages.error(request, '用户名或密码错误')
                
        except Exception as e:
            logger.error(f"登录失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            messages.error(request, '登录失败，请稍后重试')
    
    return render(request, 'novel_app/login.html')


def register(request):
    """注册页面"""
    if request.method == 'POST':
        name = request.POST.get('name')
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        if not all([name, username, password, confirm_password]):
            messages.error(request, '所有字段都必须填写')
            return render(request, 'novel_app/register.html')
        
        if password != confirm_password:
            messages.error(request, '两次输入的密码不一致')
            return render(request, 'novel_app/register.html')
        
        if len(password) < 6:
            messages.error(request, '密码长度至少6位')
            return render(request, 'novel_app/register.html')
        
        try:
            # 检查用户名是否已存在
            if UserProfile.objects.filter(username=username).exists():
                messages.error(request, '用户名已存在')
                return render(request, 'novel_app/register.html')
            
            # 创建新用户
            user = UserProfile.objects.create(
                name=name,
                username=username,
                balance=0.00,
                vip_level='普通'
            )
            # 使用加密方法设置密码
            user.set_password(password)
            user.save()
            
            messages.success(request, '注册成功！请登录')
            return redirect('login')
            
        except Exception as e:
            logger.error(f"注册失败: {str(e)}")
            messages.error(request, '注册失败，请稍后重试')
    
    return render(request, 'novel_app/register.html')


def logout(request):
    """退出登录"""
    request.session.flush()
    messages.success(request, '已成功退出登录')
    return redirect('index')


@login_required
def user_profile(request):
    """用户个人中心"""
    try:
        user = get_current_user(request)
        if not user:
            messages.warning(request, '请先登录')
            return redirect('login')
        
        # 获取用户统计信息
        owned_books_count = UserBookOwnership.objects.filter(user_id=user.user_id).count()
        orders_count = BookOrder.objects.filter(customer_name=user.username).count()
        
        # 获取订单列表（按创建时间倒序）
        orders_queryset = BookOrder.objects.filter(customer_name=user.username).order_by('-create_time')[:20]
        
        # 处理订单数据，添加书籍标题等信息
        orders = []
        for order in orders_queryset:
            order_data = {
                'order_id': order.order_id,
                'order_number': order.order_number,
                'order_status': order.order_status,
                'order_amount': float(order.order_amount),
                'actual_amount': float(order.order_amount),
                'create_time': order.create_time,
                'payment_time': order.payment_time,
                'book_count': order.book_count,  # 使用正确的字段名
                'book_titles': order.get_book_titles(),
            }
            orders.append(order_data)
        
        # 获取购买的书籍（分页）
        # 只显示真正购买的记录，排除VIP免费访问的记录
        purchased_ownerships = UserBookOwnership.objects.filter(
            user_id=user.user_id
        ).exclude(
            access_type='vip_free'
        ).order_by('-purchase_time')
        
        # 构建购买的书籍数据（在分页之前）
        purchased_books_data = []
        for ownership in purchased_ownerships:
            try:
                book = BookName.objects.get(book_id=ownership.book_id)
                purchased_books_data.append({
                    'book_id': book.book_id,
                    'book_title': ownership.book_title or book.title,
                    'chapter_count': book.chapter_count or 0,
                    'purchase_time': ownership.purchase_time,
                    'last_purchase_time': ownership.purchase_time,
                    'total_price': float(ownership.purchase_price) if ownership.purchase_price else 0.0,
                    'access_type': ownership.access_type,
                })
            except BookName.DoesNotExist:
                # 如果书籍不存在，仍然显示购买记录
                purchased_books_data.append({
                    'book_id': None,
                    'book_title': ownership.book_title or '未知书籍',
                    'chapter_count': 0,
                    'purchase_time': ownership.purchase_time,
                    'last_purchase_time': ownership.purchase_time,
                    'total_price': float(ownership.purchase_price) if ownership.purchase_price else 0.0,
                    'access_type': ownership.access_type,
                })
        
        # 对购买书籍数据进行分页
        purchases_paginator = Paginator(purchased_books_data, 10)
        purchases_page = request.GET.get('purchases_page', 1)
        try:
            purchased_books = purchases_paginator.page(purchases_page)
        except:
            purchased_books = purchases_paginator.page(1)
        
        # 获取收藏的书籍
        collected_books_titles = user_profile.get_collected_books()
        collected_books = []
        for item in collected_books_titles:
            book_title = item.get('book_title') if isinstance(item, dict) else item
            if book_title:
                try:
                    book = BookName.objects.get(title=book_title)
                    collected_books.append(book)
                except BookName.DoesNotExist:
                    continue
        
        # 计算收藏数量（使用原始收藏列表的长度，而不是过滤后的）
        collected_count = len(collected_books_titles)
        
        # 调试信息（如果收藏数为0，记录日志）
        if collected_count == 0:
            logger.debug(f"用户 {user_profile.username} 的收藏列表为空: {collected_books_titles}")
        else:
            logger.debug(f"用户 {user_profile.username} 的收藏数量: {collected_count}, 收藏列表: {collected_books_titles[:5]}")
        
        # 获取评价列表
        from .models import BookEvaluate
        reviews = BookEvaluate.objects.filter(
            customer_name=user_profile.username
        ).order_by('-create_time')[:20]
        
        context = {
            'user_profile': user_profile,
            'owned_books_count': owned_books_count,
            'orders_count': orders_count,
            'total_orders_count': orders_count,  # 模板中使用这个变量名
            'orders': orders,  # 订单列表
            'purchased_books': purchased_books,  # 分页对象
            'collected_books': collected_books,
            'collected_count': collected_count,  # 收藏数量
            'reviews': reviews,
        }
        
        return render(request, 'novel_app/user_profile.html', context)
        
    except UserProfile.DoesNotExist:
        messages.error(request, '用户不存在')
        return redirect('login')
    except Exception as e:
        logger.error(f"个人中心加载失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        messages.error(request, '页面加载失败')
        return redirect('index')



def user_login(request):
    """用户登录"""
    return login(request)


def user_logout(request):
    """用户退出"""
    return logout(request)


def user_register(request):
    """用户注册"""
    return register(request)


def update_profile(request):
    """更新用户资料"""
    if not request.session.get('username'):
        messages.warning(request, '请先登录')
        return redirect('login')
    
    if request.method == 'POST':
        try:
            user_profile = UserProfile.objects.get(username=request.session['username'])
            
            name = request.POST.get('name')
            if name:
                user_profile.name = name
                user_profile.save()
                request.session['name'] = name
                messages.success(request, '资料更新成功')
            
        except UserProfile.DoesNotExist:
            messages.error(request, '用户不存在')
        except Exception as e:
            logger.error(f"更新资料失败: {str(e)}")
            messages.error(request, '更新失败')
    
    return redirect('user_profile')


def change_password(request):
    """修改密码"""
    if not request.session.get('username'):
        messages.warning(request, '请先登录')
        return redirect('login')
    
    if request.method == 'POST':
        try:
            user_profile = UserProfile.objects.get(username=request.session['username'])
            
            old_password = request.POST.get('old_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            if not user_profile.check_password(old_password):
                messages.error(request, '原密码错误')
            elif new_password != confirm_password:
                messages.error(request, '两次输入的新密码不一致')
            elif len(new_password) < 6:
                messages.error(request, '新密码长度至少6位')
            else:
                user_profile.set_password(new_password)
                user_profile.save()
                messages.success(request, '密码修改成功')
            
        except UserProfile.DoesNotExist:
            messages.error(request, '用户不存在')
        except Exception as e:
            logger.error(f"修改密码失败: {str(e)}")
            messages.error(request, '修改失败')
    
    return redirect('user_profile')


def vip_recharge(request):
    """VIP充值"""
    if not request.session.get('username'):
        return JsonResponse({'success': False, 'message': '请先登录'})
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方法错误'})
    
    try:
        user_profile = UserProfile.objects.get(username=request.session['username'])
        
        # 获取充值时长（1个月、3个月、1年）
        duration = request.POST.get('duration')
        
        # 如果没有从POST获取，尝试从JSON获取
        if not duration:
            try:
                data = json.loads(request.body)
                duration = data.get('duration')
            except:
                pass
        
        if not duration:
            return JsonResponse({'success': False, 'message': '请选择充值时长'})
        
        # 定义价格
        prices = {
            '1': {'months': 1, 'price': 20.00, 'discount': 0},
            '3': {'months': 3, 'price': 54.00, 'discount': 0.1},  # 20*3*0.9 = 54
            '12': {'months': 12, 'price': 192.00, 'discount': 0.2},  # 20*12*0.8 = 192
        }
        
        if duration not in prices:
            return JsonResponse({'success': False, 'message': '无效的充值时长'})
        
        price_info = prices[duration]
        price = price_info['price']
        months = price_info['months']
        
        # 检查余额
        if float(user_profile.balance) < price:
            return JsonResponse({'success': False, 'message': f'余额不足，需要¥{price:.2f}，当前余额¥{float(user_profile.balance):.2f}'})
        
        # 扣除余额
        user_profile.balance = float(user_profile.balance) - price
        
        # 更新VIP状态
        from datetime import timedelta
        now = timezone.now()
        
        # 如果已经是VIP且未过期，则延长到期时间
        if user_profile.is_vip() and user_profile.vip_expire_time:
            if user_profile.vip_expire_time > now:
                # 在现有到期时间基础上延长
                user_profile.vip_expire_time = user_profile.vip_expire_time + timedelta(days=30 * months)
            else:
                # 已过期，从当前时间开始计算
                user_profile.vip_expire_time = now + timedelta(days=30 * months)
        else:
            # 不是VIP或已过期，从当前时间开始计算
            user_profile.vip_expire_time = now + timedelta(days=30 * months)
        
        user_profile.vip_level = 'VIP'
        user_profile.save()
        
        return JsonResponse({
            'success': True,
            'message': f'VIP充值成功！已充值{months}个月，到期时间：{user_profile.vip_expire_time.strftime("%Y-%m-%d %H:%M:%S")}',
            'vip_expire_time': user_profile.vip_expire_time.strftime("%Y-%m-%d %H:%M:%S"),
            'balance': float(user_profile.balance)
        })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '用户不存在'})
    except Exception as e:
        logger.error(f"VIP充值失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({'success': False, 'message': f'充值失败：{str(e)}'})


@admin_required
def admin_dashboard(request):
    """管理员仪表板"""
    try:
        from django.utils import timezone
        from datetime import timedelta
        
        # 获取今天的日期
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        
        # 获取基础统计数据
        total_users = UserProfile.objects.count()
        total_books = BookName.objects.count()
        total_orders = BookOrder.objects.count()
        total_chapters = BookChapter.objects.count()
        
        # 获取今日新增数据
        books_today = BookName.objects.filter(create_time__date=today).count()
        users_today = UserProfile.objects.filter(register_time__date=today).count()
        orders_today = BookOrder.objects.filter(create_time__date=today).count()
        chapters_today = BookChapter.objects.filter(create_time__date=today).count()
        
        # 获取最新活动数据
        recent_books = BookName.objects.order_by('-create_time')[:5]
        recent_users = UserProfile.objects.order_by('-register_time')[:5]
        recent_orders = BookOrder.objects.order_by('-create_time')[:5]
        
        # 获取书籍分类统计
        category_stats = BookName.objects.values('category').annotate(
            count=Count('category')
        ).order_by('-count')
        
        # 获取订单状态统计
        order_status_stats = BookOrder.objects.values('order_status').annotate(
            count=Count('order_status')
        ).order_by('-count')
        
        # 转换为JSON格式供前端使用
        category_stats_json = json.dumps(list(category_stats), ensure_ascii=False)
        order_status_stats_json = json.dumps(list(order_status_stats), ensure_ascii=False)
        
        context = {
            'total_users': total_users,
            'total_books': total_books,
            'total_orders': total_orders,
            'total_chapters': total_chapters,
            'books_today': books_today,
            'users_today': users_today,
            'orders_today': orders_today,
            'chapters_today': chapters_today,
            'recent_books': recent_books,
            'recent_users': recent_users,
            'recent_orders': recent_orders,
            'category_stats_json': category_stats_json,
            'order_status_stats_json': order_status_stats_json,
        }
        
        return render(request, 'novel_app/admin_dashboard.html', context)
        
    except Exception as e:
        logger.error(f"管理员仪表板加载失败: {str(e)}")
        messages.error(request, '页面加载失败')
        return redirect('index')



def bookshelf(request):
    """书架页面 - 整本购买模式（不显示VIP购买统计）"""
    # 检查用户是否登录
    if not request.session.get('username'):
        messages.warning(request, '请先登录后再访问书架！')
        return redirect('login')
    
    try:
        user_profile = UserProfile.objects.get(username=request.session.get('username'))
        
        # 获取用户购买的所有书籍
        owned_books = UserBookOwnership.objects.filter(
            user_id=user_profile.user_id
        ).order_by('-last_read_time', '-purchase_time')
        
        # 获取收藏的书籍（原始列表）
        collected_books_titles = user_profile.get_collected_books()
        
        # 获取书架上的书籍
        bookshelf_books = user_profile.get_bookshelf_books()
        
        # 创建购买记录的字典，以book_id为键，方便快速查找
        ownership_dict = {}
        for ownership in owned_books:
            ownership_dict[ownership.book_id] = ownership
        
        # 构建书架书籍列表 - 直接根据书架列表显示书籍
        books = []
        for book_title in bookshelf_books:
            try:
                # 根据书名查找书籍
                book = BookName.objects.get(title=book_title)
                
                # 查找是否有购买记录
                ownership = ownership_dict.get(book.book_id)
                
                if ownership:
                    # 有购买记录，使用购买记录的信息
                    books.append({
                        'book': book,
                        'ownership': ownership,
                        'last_read_chapter': ownership.reading_progress,
                        'start_chapter': max(1, ownership.reading_progress + 1) if ownership.reading_progress > 0 else 1,
                        'last_read_time': ownership.last_read_time,
                        'access_type': ownership.access_type,
                        'purchase_price': float(ownership.purchase_price) if ownership.purchase_price else 0,
                    })
                else:
                    # 没有购买记录，使用默认值
                    books.append({
                        'book': book,
                        'ownership': None,
                        'last_read_chapter': 0,
                        'start_chapter': 1,
                        'last_read_time': None,
                        'access_type': None,
                        'purchase_price': 0,
                    })
            except BookName.DoesNotExist:
                # 如果书籍不存在，跳过
                continue
            except BookName.MultipleObjectsReturned:
                # 如果有多本同名书籍，取第一本
                book = BookName.objects.filter(title=book_title).first()
                if book:
                    ownership = ownership_dict.get(book.book_id)
                    if ownership:
                        books.append({
                            'book': book,
                            'ownership': ownership,
                            'last_read_chapter': ownership.reading_progress,
                            'start_chapter': max(1, ownership.reading_progress + 1) if ownership.reading_progress > 0 else 1,
                            'last_read_time': ownership.last_read_time,
                            'access_type': ownership.access_type,
                            'purchase_price': float(ownership.purchase_price) if ownership.purchase_price else 0,
                        })
                    else:
                        books.append({
                            'book': book,
                            'ownership': None,
                            'last_read_chapter': 0,
                            'start_chapter': 1,
                            'last_read_time': None,
                            'access_type': None,
                            'purchase_price': 0,
                        })
        
        # 按最后阅读时间排序（有购买记录的优先，然后按时间排序）
        # 对于没有购买记录的书籍，保持它们在书架列表中的原始顺序（后添加的在前）
        # Python的sort是稳定的，所以没有购买记录的书籍会保持它们在列表中的原始顺序
        books.sort(key=lambda x: (
            x['last_read_time'] is None,  # None值排在后面
            x['last_read_time'] if x['last_read_time'] else timezone.make_aware(datetime(1970, 1, 1))
        ), reverse=True)
        
        # 计算统计数据
        # 已拥有的书籍总数（包括所有购买类型）
        total_books = UserBookOwnership.objects.filter(user_id=user_profile.user_id).count()
        
        # 已购买的书籍数量（只统计普通购买，不包括VIP免费和支持作者）
        purchased_books = UserBookOwnership.objects.filter(
            user_id=user_profile.user_id, 
            access_type='purchased'
        ).count()
        
        # 收藏数量（使用原始收藏列表的长度）
        collected_count = len(collected_books_titles)
        
        # 阅读中的书籍数量（书架中的书籍）
        reading_count = len(bookshelf_books)
    
    except UserProfile.DoesNotExist:
        books = []
        total_books = 0
        purchased_books = 0
        collected_count = 0
        reading_count = 0
    except Exception as e:
        logger.error(f"书架页面加载失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        books = []
        total_books = 0
        purchased_books = 0
        collected_count = 0
        reading_count = 0
    
    context = {
        'books': books,
        'stats': {
            'total_books': total_books,
            'purchased_books': purchased_books,
            'collected_count': collected_count,
            'reading_count': reading_count,
        }
    }
    return render(request, 'novel_app/bookshelf.html', context)


def shopping_cart(request):
    """购物车页面"""
    if not request.session.get('username'):
        messages.error(request, '请先登录！')
        return redirect('login')
    
    try:
        username = request.session.get('username')
        user = UserProfile.objects.get(username=username)
        
        # 获取购物车中的书籍
        cart_items = CartItem.objects.filter(user=user).select_related('book').order_by('-create_time')
        
        # 构建书籍列表（适配模板）
        books = []
        selected_count = 0
        original_amount = 0
        
        for item in cart_items:
            if item.is_selected:
                selected_count += 1
                original_amount += float(item.price)
            
            books.append({
                'item_id': item.item_id,
                'book': item.book,
                'total_price': float(item.price),
                'price': float(item.price),
                'is_selected': item.is_selected,
            })
        
        # 计算折扣（整本购买模式：5本9折，10本8折，20本7折）
        book_count = selected_count
        discount_rate = 1.0
        if book_count >= 20:
            discount_rate = 0.7
        elif book_count >= 10:
            discount_rate = 0.8
        elif book_count >= 5:
            discount_rate = 0.9
        
        # 计算折扣后的总价
        total_amount = round(original_amount * discount_rate, 2)
        saved_amount = round(original_amount - total_amount, 2)
        
        # 折扣信息
        discount_info = {
            'rate': discount_rate,
            'text': '',
            'saved_amount': saved_amount
        }
        
        if discount_rate < 1.0:
            if book_count >= 20:
                discount_info['text'] = '20本及以上7折'
            elif book_count >= 10:
                discount_info['text'] = '10本及以上8折'
            elif book_count >= 5:
                discount_info['text'] = '5本及以上9折'
        else:
            discount_info['text'] = '无折扣'
        
        context = {
            'user': user,
            'books': books,  # 使用books变量名以匹配模板
            'cart_items': cart_items,  # 保留原变量名以防其他地方使用
            'selected_count': selected_count,
            'total_price': total_amount,
            'total_amount': total_amount,
            'original_amount': original_amount,
            'discount_info': discount_info,
            'cart_count': cart_items.count(),
        }
        
        return render(request, 'novel_app/shopping_cart.html', context)
        
    except UserProfile.DoesNotExist:
        messages.error(request, '用户不存在！')
        return redirect('login')
    except Exception as e:
        logger.error(f"购物车页面加载失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        messages.error(request, '购物车加载失败，请稍后重试')
        return redirect('index')



@csrf_exempt
def add_to_cart(request):
    """添加书籍到购物车"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方法错误'}, status=405)
    
    if not request.session.get('username'):
        return JsonResponse({'success': False, 'message': '请先登录'}, status=401)
    
    try:
        data = json.loads(request.body)
        book_id = data.get('book_id')
        price = data.get('price')  # 从请求中获取价格
        
        username = request.session.get('username')
        user = UserProfile.objects.get(username=username)
        book = BookName.objects.get(book_id=book_id)
        
        # 优先使用传入的价格，如果没有则使用书籍的价格，最后使用默认值
        final_price = float(price) if price is not None else (float(book.price) if book.price else 9.99)
        
        # 检查是否已在购物车中
        cart_item, created = CartItem.objects.get_or_create(
            user=user,
            book=book,
            defaults={
                'price': final_price,
            }
        )
        
        if not created:
            # 如果已存在，更新价格（确保价格一致）
            cart_item.price = final_price
            cart_item.save()
            return JsonResponse({'success': False, 'message': '书籍已在购物车中，价格已更新'})
        
        return JsonResponse({'success': True, 'message': '添加到购物车成功'})
        
    except Exception as e:
        logger.error(f"添加到购物车失败: {e}")
        return JsonResponse({'success': False, 'message': '添加失败'})


@csrf_exempt
def remove_from_cart(request):
    """从购物车移除书籍"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方法错误'})
    
    if not request.session.get('username'):
        return JsonResponse({'success': False, 'message': '请先登录'})
    
    try:
        data = json.loads(request.body)
        book_id = data.get('book_id')
        
        username = request.session.get('username')
        user = UserProfile.objects.get(username=username)
        
        CartItem.objects.filter(
            user=user,
            book__book_id=book_id
        ).delete()
        
        return JsonResponse({'success': True, 'message': '移除成功'})
        
    except Exception as e:
        logger.error(f"移除购物车项目失败: {e}")
        return JsonResponse({'success': False, 'message': '移除失败'})


@csrf_exempt
def clear_cart(request):
    """清空购物车"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方法错误'})
    
    if not request.session.get('username'):
        return JsonResponse({'success': False, 'message': '请先登录'})
    
    try:
        username = request.session.get('username')
        user = UserProfile.objects.get(username=username)
        
        CartItem.objects.filter(user=user).delete()
        
        return JsonResponse({'success': True, 'message': '购物车已清空'})
        
    except Exception as e:
        logger.error(f"清空购物车失败: {e}")
        return JsonResponse({'success': False, 'message': '清空失败'})


def get_cart_count(request):
    """获取购物车商品数量"""
    if not request.session.get('username'):
        return JsonResponse({'count': 0})
    
    try:
        username = request.session.get('username')
        user = UserProfile.objects.get(username=username)
        
        count = CartItem.objects.filter(user=user).count()
        
        return JsonResponse({'count': count})
        
    except Exception as e:
        logger.error(f"获取购物车数量失败: {e}")
        return JsonResponse({'count': 0})


def add_to_bookshelf(request):
    """添加到书架API"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方法错误'}, status=405)
    
    if not request.session.get('username'):
        return JsonResponse({'success': False, 'message': '请先登录'}, status=401)
    
    try:
        data = json.loads(request.body)
        book_title = data.get('book_title')
        
        if not book_title:
            return JsonResponse({'success': False, 'message': '书籍标题不能为空'}, status=400)
        
        user = UserProfile.objects.get(username=request.session['username'])
        bookshelf_books = user.get_bookshelf_books()
        
        # 检查是否已在书架中
        if book_title in bookshelf_books:
            return JsonResponse({'success': False, 'message': '已在书架中'})
        
        # 添加到书架
        bookshelf_books.append(book_title)
        user.set_bookshelf_books(bookshelf_books)
        user.save()
        
        return JsonResponse({'success': True, 'message': '已加入书架'})
        
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '用户不存在'}, status=404)
    except Exception as e:
        logger.error(f"添加到书架失败: {e}")
        return JsonResponse({'success': False, 'message': '添加到书架失败，请稍后重试'}, status=500)

@csrf_exempt
def add_to_cart_new(request):
    """新版添加到购物车API"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方法错误'}, status=405)
    
    if not request.session.get('username'):
        return JsonResponse({'success': False, 'message': '请先登录'}, status=401)
    
    try:
        data = json.loads(request.body)
        book_id = data.get('book_id')
        price = data.get('price')  # 从请求中获取价格
        quantity = data.get('quantity', 1)
        
        username = request.session.get('username')
        user = UserProfile.objects.get(username=username)
        book = BookName.objects.get(book_id=book_id)
        
        # 优先使用传入的价格，如果没有则使用书籍的价格，最后使用默认值
        final_price = float(price) if price is not None else (float(book.price) if book.price else 9.99)
        
        # 检查是否已在购物车中
        cart_item, created = CartItem.objects.get_or_create(
            user=user,
            book=book,
            defaults={
                'price': final_price,
            }
        )
        
        if not created:
            # 如果已存在，更新价格（确保价格一致）
            cart_item.price = final_price
            cart_item.save()
            return JsonResponse({'success': False, 'message': '书籍已在购物车中，价格已更新'})
        
        return JsonResponse({'success': True, 'message': '添加到购物车成功'})
        
    except BookName.DoesNotExist:
        return JsonResponse({'success': False, 'message': '书籍不存在'}, status=404)
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '用户不存在'}, status=404)
    except Exception as e:
        logger.error(f"添加到购物车失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({'success': False, 'message': '添加失败，请稍后重试'}, status=500)

def admin_add_user(request):
    """管理员添加用户API"""
    if not request.session.get('is_admin'):
        return JsonResponse({'success': False, 'message': '权限不足'})
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方法错误'})
    
    try:
        data = json.loads(request.body)
        
        # 验证必填字段
        required_fields = ['name', 'username', 'password']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({'success': False, 'message': f'{field}字段不能为空'})
        
        # 检查用户名是否已存在
        if UserProfile.objects.filter(username=data['username']).exists():
            return JsonResponse({'success': False, 'message': '用户名已存在'})
        
        # 创建用户
        user = UserProfile.objects.create(
            name=data['name'],
            username=data['username'],
            vip_level=data.get('vip_level', '普通'),
            balance=data.get('balance', 0.0),
            status='正常'
        )
        # 使用加密方法设置密码
        user.set_password(data['password'])
        user.save()
        
        return JsonResponse({
            'success': True, 
            'message': '用户添加成功',
            'user_id': user.user_id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': '数据格式错误'})
    except Exception as e:
        logger.error(f"添加用户失败: {e}")
        return JsonResponse({'success': False, 'message': '添加失败，请重试'})

def admin_batch_update_order_status(request):
    """管理员批量更新订单状态API"""
    if not request.session.get('is_admin'):
        return JsonResponse({'success': False, 'message': '权限不足'})
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方法错误'})
    
    try:
        data = json.loads(request.body)
        order_ids = data.get('order_ids', [])
        new_status = data.get('status')
        
        if not order_ids or not new_status:
            return JsonResponse({'success': False, 'message': '参数不完整'})
        
        # 批量更新订单状态
        from django.utils import timezone
        updated_count = 0
        
        for order_id in order_ids:
            try:
                order = BookOrder.objects.get(order_id=order_id)
                old_status = order.order_status
                order.order_status = new_status
                
                # 根据状态更新相应的时间字段
                if new_status == '已支付' and old_status != '已支付':
                    order.payment_time = timezone.now()
                
                order.save()
                updated_count += 1
            except BookOrder.DoesNotExist:
                continue
        
        return JsonResponse({
            'success': True,
            'message': f'成功更新{updated_count}个订单状态',
            'updated_count': updated_count
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': '数据格式错误'})
    except Exception as e:
        logger.error(f"批量更新订单状态失败: {e}")
        return JsonResponse({'success': False, 'message': '批量更新失败'})

def admin_delete_user(request):
    """管理员删除书籍API"""
    if not request.session.get('is_admin'):
        return JsonResponse({'success': False, 'message': '权限不足'})
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方法错误'})
    
    try:
        data = json.loads(request.body)
        book_id = data.get('book_id')
        
        if not book_id:
            return JsonResponse({'success': False, 'message': '书籍ID不能为空'})
        
        book = BookName.objects.get(book_id=book_id)
        book_title = book.title
        
        # 删除相关的章节
        from novel_app.models import BookChapter
        BookChapter.objects.filter(book_title=book_title).delete()
        
        # 删除书籍
        book.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'书籍《{book_title}》删除成功'
        })
        
    except BookName.DoesNotExist:
        return JsonResponse({'success': False, 'message': '书籍不存在'})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': '数据格式错误'})
    except Exception as e:
        logger.error(f"删除书籍失败: {e}")
        return JsonResponse({'success': False, 'message': '删除失败'})

def admin_delete_user(request):
    """管理员删除用户API"""
    if not request.session.get('is_admin'):
        return JsonResponse({'success': False, 'message': '权限不足'})
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方法错误'})
    
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        
        if not user_id:
            return JsonResponse({'success': False, 'message': '用户ID不能为空'})
        
        user = UserProfile.objects.get(user_id=user_id)
        user_name = user.name
        
        # 删除用户相关数据
        UserBookOwnership.objects.filter(user_id=user_id).delete()
        BookOrder.objects.filter(customer_name=user_name).delete()
        CartItem.objects.filter(user=user).delete()
        
        # 删除用户
        user.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'用户"{user_name}"删除成功'
        })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '用户不存在'})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': '数据格式错误'})
    except Exception as e:
        logger.error(f"删除用户失败: {e}")
        return JsonResponse({'success': False, 'message': '删除失败'})

def admin_get_order_detail(request, order_id):
    """管理员获取订单详情API"""
    if not request.session.get('is_admin'):
        return JsonResponse({'success': False, 'message': '权限不足'})
    
    try:
        order = BookOrder.objects.get(order_id=order_id)
        
        # 解析订单内容
        order_content_parsed = None
        if order.order_content:
            try:
                order_content_parsed = json.loads(order.order_content)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"订单 {order_id} 的订单内容JSON解析失败: {order.order_content}")
                order_content_parsed = None
        
        order_data = {
            'order_id': order.order_id,
            'order_number': order.order_number,
            'customer_name': order.customer_name,
            'order_amount': float(order.order_amount),
            'payment_method': order.payment_method,
            'order_status': order.order_status,
            'book_count': order.book_count,  # 使用正确的字段名
            'order_content': order.order_content,
            'order_content_parsed': order_content_parsed,
            'create_time': order.create_time.strftime('%Y-%m-%d %H:%M:%S') if order.create_time else '',
            'payment_time': order.payment_time.strftime('%Y-%m-%d %H:%M:%S') if order.payment_time else '',
            'complete_time': order.complete_time.strftime('%Y-%m-%d %H:%M:%S') if order.complete_time else '',
        }
        
        return JsonResponse({
            'success': True,
            'order': order_data
        })
        
    except BookOrder.DoesNotExist:
        return JsonResponse({'success': False, 'message': '订单不存在'})
    except Exception as e:
        logger.error(f"获取订单详情失败: {e}")
        return JsonResponse({'success': False, 'message': '获取失败'})

def admin_get_user(request, user_id):
    """管理员获取用户信息API"""
    if not request.session.get('is_admin'):
        return JsonResponse({'success': False, 'message': '权限不足'})
    
    try:
        user = UserProfile.objects.get(user_id=user_id)
        
        user_data = {
            'user_id': user.user_id,
            'name': user.name,
            'username': user.username,
            'vip_level': user.vip_level,
            'balance': float(user.balance),
            'status': user.status,
            'register_time': user.register_time.strftime('%Y-%m-%d %H:%M:%S') if user.register_time else '',
            'last_login_time': user.last_login_time.strftime('%Y-%m-%d %H:%M:%S') if user.last_login_time else ''
        }
        
        return JsonResponse({
            'success': True,
            'user': user_data
        })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '用户不存在'})
    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        return JsonResponse({'success': False, 'message': '获取失败'})

def admin_get_user_detail(request, user_id):
    """管理员获取用户详细信息API"""
    if not request.session.get('is_admin'):
        return JsonResponse({'success': False, 'message': '权限不足'})
    
    try:
        user = UserProfile.objects.get(user_id=user_id)
        
        # 获取用户统计信息
        owned_books_count = UserBookOwnership.objects.filter(user_id=user.user_id).count()
        orders_count = BookOrder.objects.filter(customer_name=user.name).count()
        
        user_data = {
            'user_id': user.user_id,
            'name': user.name,
            'username': user.username,
            'vip_level': user.vip_level,
            'status': user.status,
            'balance': float(user.balance),
            'register_time': user.register_time.strftime('%Y-%m-%d %H:%M:%S') if user.register_time else '',
            'last_login_time': user.last_login_time.strftime('%Y-%m-%d %H:%M:%S') if user.last_login_time else '从未登录',
            'owned_books_count': owned_books_count,
            'orders_count': orders_count,
        }
        
        return JsonResponse({
            'success': True,
            'user': user_data
        })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '用户不存在'})
    except Exception as e:
        logger.error(f"获取用户详情失败: {e}")
        return JsonResponse({'success': False, 'message': '获取失败'})

@admin_required
def admin_orders(request):
    """管理员订单管理页面"""
    try:
        # 获取搜索和筛选参数
        search_query = request.GET.get('search', '')
        order_status = request.GET.get('order_status', '')
        create_date = request.GET.get('create_date', '')
        page = request.GET.get('page', 1)
        
        # 构建查询
        orders = BookOrder.objects.all()
        
        if search_query:
            orders = orders.filter(
                Q(customer_name__icontains=search_query) | 
                Q(order_number__icontains=search_query)
            )
        
        if order_status:
            orders = orders.filter(order_status=order_status)
        
        if create_date:
            from datetime import datetime, timedelta
            from django.utils import timezone
            try:
                # 解析日期字符串
                create_date_obj = datetime.strptime(create_date, '%Y-%m-%d').date()
                # 使用时区感知的日期范围查询（考虑时区）
                # 获取当天的开始时间（上海时区 00:00:00）
                start_datetime = timezone.make_aware(
                    datetime.combine(create_date_obj, datetime.min.time())
                )
                # 获取下一天的开始时间（用于范围查询的结束时间）
                next_day = create_date_obj + timedelta(days=1)
                end_datetime = timezone.make_aware(
                    datetime.combine(next_day, datetime.min.time())
                )
                # 使用范围查询，确保包含整个日期（从当天00:00:00到次日00:00:00）
                orders = orders.filter(create_time__gte=start_datetime, create_time__lt=end_datetime)
            except ValueError:
                # 日期格式错误，记录日志但不中断查询
                logger.warning(f"日期格式错误: {create_date}")
        
        # 排序
        orders = orders.order_by('-create_time')
        
        # 分页
        paginator = Paginator(orders, 20)
        page_obj = paginator.get_page(page)
        
        # 获取状态选项
        status_choices = BookOrder.STATUS_CHOICES
        
        context = {
            'page_obj': page_obj,
            'search_query': search_query,
            'order_status': order_status,
            'create_date': create_date,
            'status_choices': status_choices,
            'total_orders': orders.count(),
        }
        
        return render(request, 'novel_app/admin_orders.html', context)
        
    except Exception as e:
        logger.error(f"订单管理页面加载失败: {str(e)}")
        messages.error(request, '页面加载失败')
        return redirect('admin_dashboard')

def admin_toggle_user_status(request):
    """管理员切换用户状态API"""
    if not request.session.get('is_admin'):
        return JsonResponse({'success': False, 'message': '权限不足'})
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方法错误'})
    
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        new_status = data.get('status')
        
        if not user_id or not new_status:
            return JsonResponse({'success': False, 'message': '参数不完整'})
        
        user = UserProfile.objects.get(user_id=user_id)
        user.status = new_status
        user.save()
        
        return JsonResponse({
            'success': True,
            'message': f'用户状态已更新为{new_status}'
        })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '用户不存在'})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': '数据格式错误'})
    except Exception as e:
        logger.error(f"切换用户状态失败: {e}")
        return JsonResponse({'success': False, 'message': '操作失败'})

def admin_update_order_status(request):
    """管理员更新订单状态API"""
    if not request.session.get('is_admin'):
        return JsonResponse({'success': False, 'message': '权限不足'})
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方法错误'})
    
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        new_status = data.get('status')
        
        if not order_id or not new_status:
            return JsonResponse({'success': False, 'message': '参数不完整'})
        
        order = BookOrder.objects.get(order_id=order_id)
        old_status = order.order_status
        order.order_status = new_status
        
        # 根据状态更新相应的时间字段
        from django.utils import timezone
        if new_status == '已支付' and old_status != '已支付':
            order.payment_time = timezone.now()
        
        order.save()
        
        return JsonResponse({
            'success': True,
            'message': f'订单状态已从"{old_status}"更新为"{new_status}"'
        })
        
    except BookOrder.DoesNotExist:
        return JsonResponse({'success': False, 'message': '订单不存在'})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': '数据格式错误'})
    except Exception as e:
        logger.error(f"更新订单状态失败: {e}")
        return JsonResponse({'success': False, 'message': '更新失败'})

def admin_update_user(request):
    """管理员更新用户信息API"""
    if not request.session.get('is_admin'):
        return JsonResponse({'success': False, 'message': '权限不足'})
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方法错误'})
    
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        
        if not user_id:
            return JsonResponse({'success': False, 'message': '用户ID不能为空'})
        
        user = UserProfile.objects.get(user_id=user_id)
        
        # 更新字段
        if 'name' in data:
            user.name = data['name']
        if 'username' in data:
            # 检查用户名唯一性
            if UserProfile.objects.filter(username=data['username']).exclude(user_id=user_id).exists():
                return JsonResponse({'success': False, 'message': '用户名已存在'})
            user.username = data['username']
        if 'vip_level' in data:
            user.vip_level = data['vip_level']
        if 'status' in data:
            user.status = data['status']
        if 'balance' in data:
            user.balance = float(data['balance'])
        if 'password' in data and data['password']:
            user.set_password(data['password'])  # 使用加密方法设置密码
        
        user.save()
        
        return JsonResponse({
            'success': True,
            'message': '用户信息更新成功'
        })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '用户不存在'})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': '数据格式错误'})
    except Exception as e:
        logger.error(f"更新用户信息失败: {e}")
        return JsonResponse({'success': False, 'message': '更新失败'})

@admin_required
def admin_users(request):
    """管理员用户管理页面"""
    try:
        # 获取搜索和筛选参数
        search_query = request.GET.get('search', '')
        vip_level = request.GET.get('vip_level', '')
        status = request.GET.get('status', '')
        page = request.GET.get('page', 1)
        
        # 构建查询
        users = UserProfile.objects.all()
        
        if search_query:
            users = users.filter(
                Q(name__icontains=search_query) | 
                Q(username__icontains=search_query)
            )
        
        if vip_level:
            users = users.filter(vip_level=vip_level)
        
        if status:
            users = users.filter(status=status)
        
        # 排序
        users = users.order_by('-register_time')
        
        # 分页
        paginator = Paginator(users, 20)
        page_obj = paginator.get_page(page)
        
        # 获取VIP等级选项
        vip_level_choices = UserProfile.VIP_LEVEL_CHOICES
        
        # 获取状态选项
        status_choices = UserProfile.STATUS_CHOICES
        
        context = {
            'page_obj': page_obj,
            'search_query': search_query,
            'vip_level': vip_level,
            'status': status,
            'vip_level_choices': vip_level_choices,
            'status_choices': status_choices,
            'total_users': users.count(),
        }
        
        return render(request, 'novel_app/admin_users.html', context)
        
    except Exception as e:
        logger.error(f"用户管理页面加载失败: {str(e)}")
        messages.error(request, '页面加载失败')
        return redirect('admin_dashboard')

@csrf_exempt
def bulk_add_to_cart(request):
    """批量添加到购物车"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方法错误'})
    
    if not request.session.get('username'):
        return JsonResponse({'success': False, 'message': '请先登录'})
    
    try:
        data = json.loads(request.body)
        book_ids = data.get('book_ids', [])
        
        username = request.session.get('username')
        user = UserProfile.objects.get(username=username)
        
        added_count = 0
        for book_id in book_ids:
            try:
                book = BookName.objects.get(book_id=book_id)
                cart_item, created = CartItem.objects.get_or_create(
                    user=user,
                    book=book,
                    defaults={
                        'price': book.price or 9.99,
                    }
                )
                if created:
                    added_count += 1
            except BookName.DoesNotExist:
                continue
        
        return JsonResponse({
            'success': True, 
            'message': f'成功添加 {added_count} 本书到购物车'
        })
        
    except Exception as e:
        logger.error(f"批量添加到购物车失败: {e}")
        return JsonResponse({'success': False, 'message': '批量添加失败'})

@csrf_exempt
def cart_checkout(request):
    """购物车结账"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方法错误'})
    
    if not request.session.get('username'):
        return JsonResponse({'success': False, 'message': '请先登录'})
    
    try:
        username = request.session.get('username')
        user = UserProfile.objects.get(username=username)
        
        # 获取购物车项目
        cart_items = CartItem.objects.filter(user=user)
        
        if not cart_items.exists():
            return JsonResponse({'success': False, 'message': '购物车为空'})
        
        # 计算总价
        total_price = sum(item.price for item in cart_items)
        
        # 检查余额
        if user.balance < total_price:
            return JsonResponse({'success': False, 'message': '余额不足'})
        
        # 创建订单
        order_number = generate_order_number()
        order = BookOrder.objects.create(
            order_number=order_number,
            customer_name=user.username,
            order_amount=total_price,
            order_status='已支付'
        )
        
        # 创建购买记录
        for item in cart_items:
            UserBookOwnership.objects.create(
                user_id=user.user_id,
                book_id=item.book.book_id,
                book_title=item.book.title,
                access_type='purchased',
                purchase_price=item.price
            )
        
        # 扣除余额
        user.balance -= total_price
        user.save()
        
        # 清空购物车
        cart_items.delete()
        
        return JsonResponse({
            'success': True, 
            'message': '购买成功',
            'order_number': order_number
        })
        
    except Exception as e:
        logger.error(f"结账失败: {e}")
        return JsonResponse({'success': False, 'message': '结账失败'})

@csrf_exempt
def clear_cart_new(request):
    """新版清空购物车"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方法错误'})
    
    if not request.session.get('username'):
        return JsonResponse({'success': False, 'message': '请先登录'})
    
    try:
        username = request.session.get('username')
        user = UserProfile.objects.get(username=username)
        
        CartItem.objects.filter(user=user).delete()
        
        return JsonResponse({'success': True, 'message': '购物车已清空'})
        
    except Exception as e:
        logger.error(f"清空购物车失败: {e}")
        return JsonResponse({'success': False, 'message': '清空失败'})

def collect_book(request):
    """收藏书籍API"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方法错误'}, status=405)
    
    if not request.session.get('username'):
        return JsonResponse({'success': False, 'message': '请先登录'}, status=401)
    
    try:
        data = json.loads(request.body)
        book_title = data.get('book_title')
        
        if not book_title:
            return JsonResponse({'success': False, 'message': '书籍标题不能为空'}, status=400)
        
        user = UserProfile.objects.get(username=request.session['username'])
        collected_books = user.get_collected_books()
        
        # 检查是否已收藏
        is_collected = any(
            (isinstance(item, dict) and item.get('book_title') == book_title) or 
            (isinstance(item, str) and item == book_title)
            for item in collected_books
        )
        
        if is_collected:
            return JsonResponse({'success': False, 'message': '已收藏'})
        
        # 添加收藏
        collected_books.append({
            'book_title': book_title,
            'collect_time': timezone.now().isoformat()
        })
        user.set_collected_books(collected_books)
        user.save()
        
        # 更新书籍收藏数
        collection_count = 0
        try:
            book = BookName.objects.get(title=book_title)
            book.collection_count = (book.collection_count or 0) + 1
            book.save()
            collection_count = book.collection_count
        except BookName.DoesNotExist:
            pass
        
        return JsonResponse({
            'success': True,
            'message': '收藏成功',
            'collection_count': collection_count
        })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '用户不存在'}, status=404)
    except Exception as e:
        logger.error(f"收藏书籍失败: {e}")
        return JsonResponse({'success': False, 'message': '收藏失败，请稍后重试'}, status=500)

def crawl_book_chapters(request):
    """爬取书籍章节API"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方法错误'}, status=405)
    
    try:
        data = json.loads(request.body)
        book_id = data.get('book_id')
        max_chapters = data.get('max_chapters', 10)
        chapter_numbers = data.get('chapter_numbers')  # 可选：指定要爬取的章节编号列表
        
        if not book_id:
            return JsonResponse({'success': False, 'message': '书籍ID不能为空'}, status=400)
        
        # 使用爬虫服务
        from .crawler_service import DjangoBookCrawlerService
        crawler_service = DjangoBookCrawlerService()
        
        result = crawler_service.crawl_book_chapters(
            book_id=book_id,
            max_chapters=max_chapters,
            async_crawl=False,  # 同步爬取
            chapter_numbers=chapter_numbers
        )
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': '数据格式错误'}, status=400)
    except Exception as e:
        logger.error(f"爬取章节失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({'success': False, 'message': f'爬取失败: {str(e)}'}, status=500)

# 导入新的API视图
from .services.api_views import (
    crawl_single_chapter_api,
    create_order_api as create_order,
    check_book_access_api,
    check_chapter_access_api,
    get_cart_summary_api,
    batch_add_to_cart_api
)

@csrf_exempt
def delete_review(request):
    """删除评价API"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方法错误'}, status=405)
    
    if not request.session.get('username'):
        return JsonResponse({'success': False, 'message': '请先登录'}, status=401)
    
    try:
        data = json.loads(request.body)
        review_id = data.get('review_id') or data.get('evaluate_id')
        
        if not review_id:
            return JsonResponse({'success': False, 'message': '评价ID不能为空'}, status=400)
        
        username = request.session['username']
        
        # 获取评价记录
        try:
            review = BookEvaluate.objects.get(evaluate_id=review_id)
        except BookEvaluate.DoesNotExist:
            return JsonResponse({'success': False, 'message': '评价不存在'}, status=404)
        
        # 检查是否是用户自己的评价
        if review.customer_name != username:
            return JsonResponse({'success': False, 'message': '只能删除自己的评价'}, status=403)
        
        # 保存书籍标题用于重新计算评分
        book_title = review.book_title
        
        # 删除评价
        review.delete()
        
        # 重新计算书籍的平均评分
        try:
            book = BookName.objects.get(title=book_title)
            evaluations = BookEvaluate.objects.filter(book_title=book.title)
            if evaluations.exists():
                avg_rating = evaluations.aggregate(avg=Avg('rating'))['avg']
                book.rating = round(float(avg_rating), 2) if avg_rating else 0.00
            else:
                book.rating = 0.00
            book.save()
        except BookName.DoesNotExist:
            pass
        
        return JsonResponse({
            'success': True,
            'message': '评价删除成功'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': '请求数据格式错误'}, status=400)
    except Exception as e:
        logger.error(f"删除评价失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({'success': False, 'message': f'删除评价失败：{str(e)}'}, status=500)

@csrf_exempt
def edit_review(request):
    """编辑评价API"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方法错误'}, status=405)
    
    if not request.session.get('username'):
        return JsonResponse({'success': False, 'message': '请先登录'}, status=401)
    
    try:
        data = json.loads(request.body)
        review_id = data.get('review_id')
        rating = data.get('rating')
        review_content = data.get('review_content') or data.get('content', '')
        
        if not review_id:
            return JsonResponse({'success': False, 'message': '评价ID不能为空'}, status=400)
        
        if not rating:
            return JsonResponse({'success': False, 'message': '评分不能为空'}, status=400)
        
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                return JsonResponse({'success': False, 'message': '评分必须在1-5之间'}, status=400)
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'message': '评分格式错误'}, status=400)
        
        if not review_content or not review_content.strip():
            return JsonResponse({'success': False, 'message': '评价内容不能为空'}, status=400)
        
        username = request.session['username']
        
        # 获取评价记录
        try:
            review = BookEvaluate.objects.get(evaluate_id=review_id)
        except BookEvaluate.DoesNotExist:
            return JsonResponse({'success': False, 'message': '评价不存在'}, status=404)
        
        # 检查是否是用户自己的评价
        if review.customer_name != username:
            return JsonResponse({'success': False, 'message': '只能编辑自己的评价'}, status=403)
        
        # 更新评价
        review.rating = rating
        review.review_content = review_content.strip()
        review.save()
        
        # 重新计算书籍的平均评分
        try:
            book = BookName.objects.get(title=review.book_title)
            evaluations = BookEvaluate.objects.filter(book_title=book.title)
            if evaluations.exists():
                avg_rating = evaluations.aggregate(avg=Avg('rating'))['avg']
                book.rating = round(float(avg_rating), 2) if avg_rating else 0.00
            else:
                book.rating = 0.00
            book.save()
        except BookName.DoesNotExist:
            pass
        
        return JsonResponse({
            'success': True,
            'message': '评价更新成功',
            'review': {
                'evaluate_id': review.evaluate_id,
                'rating': review.rating,
                'review_content': review.review_content,
                'customer_name': review.customer_name,
                'create_time': review.create_time.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': '请求数据格式错误'}, status=400)
    except Exception as e:
        logger.error(f"编辑评价失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({'success': False, 'message': f'编辑评价失败：{str(e)}'}, status=500)

def get_all_orders(request):
    """自动生成的函数 - get_all_orders"""
    return JsonResponse({'success': False, 'message': '功能暂未实现'})

def get_book_info(request, book_id):
    """获取书籍信息API"""
    try:
        book = BookName.objects.get(book_id=book_id)
        
        book_info = {
            'book_id': book.book_id,
            'title': book.title,
            'author': book.author,
            'price': float(book.price) if book.price else 9.99,
            'description': book.description or '',
            'cover_image': book.cover_image.url if book.cover_image else '',
        }
        
        return JsonResponse({'success': True, 'book': book_info})
        
    except BookName.DoesNotExist:
        return JsonResponse({'success': False, 'message': '书籍不存在'})
    except Exception as e:
        logger.error(f"获取书籍信息失败: {e}")
        return JsonResponse({'success': False, 'message': '获取书籍信息失败'})

def get_bookshelf_books_api(request, book_type):
    """
    获取书架书籍API
    book_type: 'purchased' (已购买), 'collected' (收藏), 'reading' (阅读中)
    """
    if request.method != 'GET':
        return JsonResponse({'success': False, 'message': '请求方法错误'}, status=405)
    
    if not request.session.get('username'):
        return JsonResponse({'success': False, 'message': '请先登录'}, status=401)
    
    try:
        user_profile = UserProfile.objects.get(username=request.session['username'])
        books_data = []
        
        if book_type == 'purchased':
            # 获取已购买的书籍（排除VIP免费访问的记录）
            owned_books = UserBookOwnership.objects.filter(
                user_id=user_profile.user_id
            ).exclude(
                access_type='vip_free'
            ).order_by('-purchase_time')
            
            for ownership in owned_books:
                try:
                    book = BookName.objects.get(book_id=ownership.book_id)
                    books_data.append({
                        'book_id': book.book_id,
                        'title': book.title,
                        'author': book.author,
                        'category': book.category,
                        'status': book.status,
                        'chapter_count': book.chapter_count or 0,
                        'rating': float(book.rating) if book.rating else 0.0,
                        'cover_url': book.cover_url or '',
                        'start_chapter': max(1, (ownership.reading_progress or 0) + 1),
                        'last_read_chapter': ownership.reading_progress or 0,
                        'last_read_time': ownership.last_read_time.strftime('%Y-%m-%d %H:%M:%S') if ownership.last_read_time else None,
                        'purchase_time': ownership.purchase_time.strftime('%Y-%m-%d %H:%M:%S') if ownership.purchase_time else None,
                        'access_type': ownership.access_type,
                        'purchase_price': float(ownership.purchase_price) if ownership.purchase_price else 0,
                    })
                except BookName.DoesNotExist:
                    continue
                    
        elif book_type == 'collected':
            # 获取收藏的书籍
            collected_books = user_profile.get_collected_books()
            
            for item in collected_books:
                try:
                    if isinstance(item, dict):
                        book_title = item.get('book_title')
                    else:
                        book_title = item
                    
                    if not book_title:
                        continue
                    
                    book = BookName.objects.get(title=book_title)
                    books_data.append({
                        'book_id': book.book_id,
                        'title': book.title,
                        'author': book.author,
                        'category': book.category,
                        'status': book.status,
                        'chapter_count': book.chapter_count or 0,
                        'rating': float(book.rating) if book.rating else 0.0,
                        'cover_url': book.cover_url or '',
                        'collect_time': item.get('collect_time') if isinstance(item, dict) else None,
                    })
                except BookName.DoesNotExist:
                    continue
                    
        elif book_type == 'reading':
            # 获取阅读中的书籍（书架中的书籍）
            bookshelf_books = user_profile.get_bookshelf_books()
            
            # 获取书架中书籍的所有权信息
            for book_title in bookshelf_books:
                try:
                    book = BookName.objects.get(title=book_title)
                    # 获取该书籍的所有权信息
                    ownership = UserBookOwnership.objects.filter(
                        user_id=user_profile.user_id,
                        book_id=book.book_id
                    ).first()
                    
                    books_data.append({
                        'book_id': book.book_id,
                        'title': book.title,
                        'author': book.author,
                        'category': book.category,
                        'status': book.status,
                        'chapter_count': book.chapter_count or 0,
                        'rating': float(book.rating) if book.rating else 0.0,
                        'cover_url': book.cover_url or '',
                        'start_chapter': max(1, (ownership.reading_progress + 1) if ownership and ownership.reading_progress else 1),
                        'last_read_chapter': ownership.reading_progress if ownership else 0,
                        'last_read_time': ownership.last_read_time.strftime('%Y-%m-%d %H:%M:%S') if ownership and ownership.last_read_time else None,
                        'reading_progress': ownership.reading_progress if ownership else 0,
                        'access_type': ownership.access_type if ownership else 'none',
                    })
                except BookName.DoesNotExist:
                    continue
        else:
            return JsonResponse({'success': False, 'message': '无效的书籍类型'}, status=400)
        
        return JsonResponse({
            'success': True,
            'books': books_data,
            'count': len(books_data)
        })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '用户不存在'}, status=404)
    except Exception as e:
        logger.error(f"获取书架书籍失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({'success': False, 'message': '获取书籍列表失败，请稍后重试'}, status=500)

def get_chapter_list(request, book_id):
    """获取书籍章节列表API"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'message': '请求方法错误'}, status=405)
    
    try:
        book = get_object_or_404(BookName, book_id=book_id)
        chapters = BookChapter.objects.filter(book_title=book.title).order_by('chapter_number')
        
        chapters_data = []
        for chapter in chapters:
            chapters_data.append({
                'number': chapter.chapter_number,
                'title': chapter.chapter_title,
                'is_crawled': chapter.is_crawled,
                'word_count': chapter.word_count or 0,
            })
        
        return JsonResponse({
            'success': True,
            'chapters': chapters_data,
            'total': len(chapters_data)
        })
        
    except Exception as e:
        logger.error(f"获取章节列表失败: {e}")
        return JsonResponse({'success': False, 'message': '获取章节列表失败'}, status=500)

def get_crawl_status(request, book_id):
    """获取书籍爬取状态API"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'message': '请求方法错误'}, status=405)
    
    try:
        from .crawler_service import DjangoBookCrawlerService
        crawler_service = DjangoBookCrawlerService()
        
        status = crawler_service.check_crawl_status(book_id)
        
        return JsonResponse({
            'success': True,
            'book_title': status.get('book_title'),
            'total_chapters': status.get('total_chapters', 0),
            'crawled_chapters': status.get('crawled_chapters', 0),
            'crawl_progress': status.get('crawl_progress', 0),
            'has_qimao_id': status.get('has_qimao_id', False),
            'qimao_book_id': status.get('qimao_book_id')
        })
        
    except Exception as e:
        logger.error(f"获取爬取状态失败: {e}")
        return JsonResponse({'success': False, 'message': '获取状态失败'}, status=500)

def get_order_by_book(request):
    """自动生成的函数 - get_order_by_book"""
    return JsonResponse({'success': False, 'message': '功能暂未实现'})

def get_orders_by_status(request):
    """自动生成的函数 - get_orders_by_status"""
    return JsonResponse({'success': False, 'message': '功能暂未实现'})

def get_qimao_book_info(request, book_id):
    """从奇猫网抓取并返回书籍详情信息。"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'message': '请求方法错误'}, status=405)

    try:
        crawler_service = DjangoBookCrawlerService()
        result = crawler_service.get_book_info_from_qimao(book_id)

        status_code = 200 if result.get('success') else 400
        return JsonResponse(result, status=status_code)
    except Exception as e:
        logger.error(f"获取奇猫书籍信息失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({'success': False, 'message': f'获取书籍信息失败: {str(e)}'}, status=500)


def get_qimao_chapter_list(request, book_id):
    """从奇猫网抓取并返回章节目录。"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'message': '请求方法错误'}, status=405)

    try:
        crawler_service = DjangoBookCrawlerService()
        result = crawler_service.get_chapter_list(book_id)

        status_code = 200 if result.get('success') else 400
        return JsonResponse(result, status=status_code)
    except Exception as e:
        logger.error(f"获取奇猫章节列表失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({'success': False, 'message': f'获取章节列表失败: {str(e)}'}, status=500)

def get_rotating_recommendations(request):
    """
    获取轮换推荐书籍API
    每次请求返回随机推荐的书籍，实现"每次刷新都不同"的效果
    """
    try:
        import random
        
        # 获取所有书籍
        all_books = list(BookName.objects.all())
        
        if not all_books:
            return JsonResponse({
                'success': False,
                'message': '暂无书籍数据',
                'books': []
            })
        
        # 随机选择4本书（如果书籍数量不足4本，则全部返回）
        num_books = min(4, len(all_books))
        selected_books = random.sample(all_books, num_books)
        
        # 序列化书籍数据
        books_data = []
        for book in selected_books:
            books_data.append({
                'book_id': book.book_id,
                'title': book.title,
                'author': book.author,
                'category': book.category,
                'status': book.status,
                'description': book.description or '',
                'cover_url': book.cover_url or '',
                'rating': float(book.rating) if book.rating else 0.0,
                'collection_count': book.collection_count or 0,
                'chapter_count': book.chapter_count or 0,
                'word_count': book.word_count or '未知',
                'update_time': book.update_time.strftime('%Y-%m-%d') if book.update_time else None,
            })
        
        return JsonResponse({
            'success': True,
            'message': f'成功获取 {len(books_data)} 本推荐书籍',
            'books': books_data
        })
        
    except Exception as e:
        logger.error(f"获取轮换推荐失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'message': f'获取推荐失败: {str(e)}',
            'books': []
        })

@csrf_exempt
def purchase_book_directly(request):
    """立即购买书籍（整本购买）"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方法错误'}, status=405)
    
    if not request.session.get('username'):
        return JsonResponse({'success': False, 'message': '请先登录'}, status=401)
    
    try:
        # 解析请求数据
        data = json.loads(request.body)
        book_id = data.get('book_id')
        price = float(data.get('price', 0))
        purchase_type = data.get('purchase_type', 'normal')
        
        if not book_id:
            return JsonResponse({'success': False, 'message': '缺少书籍ID'})
        
        if price <= 0:
            return JsonResponse({'success': False, 'message': '价格无效'})
        
        # 获取用户信息
        username = request.session.get('username')
        user = UserProfile.objects.get(username=username)
        
        # 获取书籍信息
        try:
            book = BookName.objects.get(book_id=book_id)
        except BookName.DoesNotExist:
            return JsonResponse({'success': False, 'message': '书籍不存在'}, status=404)
        
        # 检查用户是否已经拥有该书籍
        existing_ownership = UserBookOwnership.objects.filter(
            user_id=user.user_id,
            book_id=book_id
        ).first()
        
        if existing_ownership:
            return JsonResponse({
                'success': False,
                'message': f'您已经购买过《{book.title}》了'
            })
        
        # 检查余额
        if float(user.balance) < price:
            return JsonResponse({
                'success': False,
                'message': f'余额不足，当前余额：¥{float(user.balance):.2f}，需要：¥{price:.2f}'
            })
        
        # 生成订单号
        order_number = generate_order_number()
        
        # 构建订单内容
        order_content = [{
            'book_id': book.book_id,
            'book_title': book.title,
            'author': book.author,
            'price': price,
            'quantity': 1,
            'purchase_type': purchase_type
        }]
        
        # 创建订单
        order = BookOrder.objects.create(
            customer_name=user.username,
            order_number=order_number,
            order_content=json.dumps(order_content, ensure_ascii=False),
            book_count=1,  # 书籍数量（使用正确的字段名）
            order_amount=price,
            payment_method='余额',
            order_status='已支付',
            create_time=timezone.now(),
            payment_time=timezone.now(),
        )
        
        # 创建购买记录
        ownership = UserBookOwnership.objects.create(
            user_id=user.user_id,
            book_id=book.book_id,
            book_title=book.title,
            access_type='purchased',
            purchase_price=price,
            purchase_time=timezone.now(),
            reading_progress=0
        )
        
        # 扣除余额
        user.balance = float(user.balance) - price
        user.save()
        
        return JsonResponse({
            'success': True,
            'message': f'购买成功！《{book.title}》已添加到您的书架',
            'order_number': order_number,
            'book_title': book.title,
            'final_amount': price
        })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '用户不存在'}, status=404)
    except ValueError as e:
        return JsonResponse({'success': False, 'message': f'价格格式错误: {str(e)}'}, status=400)
    except Exception as e:
        logger.error(f"立即购买失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({'success': False, 'message': f'购买失败: {str(e)}'}, status=500)

@csrf_exempt
def support_author(request):
    """支持作者购买功能（VIP用户可用，即使已拥有书籍也可以支持作者）"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方法错误'}, status=405)
    
    if not request.session.get('username'):
        return JsonResponse({'success': False, 'message': '请先登录'}, status=401)
    
    try:
        # 解析请求数据
        data = json.loads(request.body)
        book_id = data.get('book_id')
        price = float(data.get('price', 0))
        
        if not book_id:
            return JsonResponse({'success': False, 'message': '缺少书籍ID'})
        
        if price <= 0:
            return JsonResponse({'success': False, 'message': '价格无效'})
        
        # 获取用户信息
        username = request.session.get('username')
        user = UserProfile.objects.get(username=username)
        
        # 获取书籍信息
        try:
            book = BookName.objects.get(book_id=book_id)
        except BookName.DoesNotExist:
            return JsonResponse({'success': False, 'message': '书籍不存在'}, status=404)
        
        # 检查余额
        if float(user.balance) < price:
            return JsonResponse({
                'success': False,
                'message': f'余额不足，当前余额：¥{float(user.balance):.2f}，需要：¥{price:.2f}'
            })
        
        # 生成订单号
        order_number = generate_order_number()
        
        # 构建订单内容（支持作者类型）
        order_content = [{
            'book_id': book.book_id,
            'book_title': book.title,
            'author': book.author,
            'price': price,
            'quantity': 1,
            'purchase_type': 'vip_support'
        }]
        
        # 创建订单
        order = BookOrder.objects.create(
            customer_name=user.username,
            order_number=order_number,
            order_content=json.dumps(order_content, ensure_ascii=False),
            book_count=1,  # 书籍数量（使用正确的字段名）
            order_amount=price,
            payment_method='余额',
            order_status='已支付',
            create_time=timezone.now(),
            payment_time=timezone.now(),
        )
        
        # 检查用户是否已经拥有该书籍
        existing_ownership = UserBookOwnership.objects.filter(
            user_id=user.user_id,
            book_id=book_id
        ).first()
        
        # 如果用户还没有拥有该书籍，创建购买记录
        if not existing_ownership:
            ownership = UserBookOwnership.objects.create(
                user_id=user.user_id,
                book_id=book.book_id,
                book_title=book.title,
                access_type='purchased',
                purchase_price=price,
                purchase_time=timezone.now(),
                reading_progress=0
            )
        
        # 扣除余额
        user.balance = float(user.balance) - price
        user.save()
        
        return JsonResponse({
            'success': True,
            'message': f'感谢您对《{book.title}》作者的支持！您的支持已记录',
            'order_number': order_number,
            'book_title': book.title,
            'final_amount': price
        })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '用户不存在'}, status=404)
    except ValueError as e:
        return JsonResponse({'success': False, 'message': f'价格格式错误: {str(e)}'}, status=400)
    except Exception as e:
        logger.error(f"支持作者购买失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({'success': False, 'message': f'购买失败: {str(e)}'}, status=500)

@csrf_exempt
def purchase_books_from_cart(request):
    """从购物车购买书籍（整本购买模式）"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方法错误'}, status=405)
    
    if not request.session.get('username'):
        return JsonResponse({'success': False, 'message': '请先登录'}, status=401)
    
    try:
        username = request.session.get('username')
        user = UserProfile.objects.get(username=username)
        
        # 获取购物车中选中的项目（整本购买模式，所有项目都购买）
        cart_items = CartItem.objects.filter(user=user, is_selected=True)
        
        if not cart_items.exists():
            # 如果没有选中的，获取所有项目
            cart_items = CartItem.objects.filter(user=user)
        
        if not cart_items.exists():
            return JsonResponse({'success': False, 'message': '购物车为空'})
        
        # 计算总价和折扣
        book_count = cart_items.count()
        original_amount = sum(float(item.price) for item in cart_items)
        
        # 应用批量购买折扣
        discount_rate = 1.0
        if book_count >= 20:
            discount_rate = 0.7
        elif book_count >= 10:
            discount_rate = 0.8
        elif book_count >= 5:
            discount_rate = 0.9
        
        final_amount = round(original_amount * discount_rate, 2)
        
        # 检查余额
        if float(user.balance) < final_amount:
            return JsonResponse({
                'success': False, 
                'message': f'余额不足，当前余额：¥{float(user.balance):.2f}，需要：¥{final_amount:.2f}'
            })
        
        # 生成订单号
        order_number = generate_order_number()
        
        # 构建订单内容（JSON格式）
        order_content = []
        purchased_books = []
        
        for item in cart_items:
            # 检查是否已购买
            existing_ownership = UserBookOwnership.objects.filter(
                user_id=user.user_id,
                book_id=item.book.book_id
            ).first()
            
            if existing_ownership:
                # 如果已购买，跳过
                continue
            
            # 添加到订单内容
            order_content.append({
                'book_id': item.book.book_id,
                'book_title': item.book.title,
                'author': item.book.author,
                'price': float(item.price),
                'quantity': 1,
                'purchase_type': 'normal'
            })
            
            purchased_books.append(item.book.title)
            
            # 创建购买记录
            UserBookOwnership.objects.create(
                user_id=user.user_id,
                book_id=item.book.book_id,
                book_title=item.book.title,
                access_type='purchased',
                purchase_price=item.price,
                purchase_time=timezone.now(),
                reading_progress=0
            )
        
        if not order_content:
            return JsonResponse({
                'success': False,
                'message': '购物车中的书籍已全部购买'
            })
        
        # 创建订单
        order = BookOrder.objects.create(
            customer_name=user.username,
            order_number=order_number,
            order_content=json.dumps(order_content, ensure_ascii=False),
            book_count=len(order_content),  # 书籍数量（使用正确的字段名）
            order_amount=final_amount,
            payment_method='余额',
            order_status='已支付',
            create_time=timezone.now(),
            payment_time=timezone.now(),
        )
        
        # 扣除余额
        user.balance = float(user.balance) - final_amount
        user.save()
        
        # 清空购物车
        cart_items.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'购买成功！共购买 {len(purchased_books)} 本书',
            'order_number': order_number,
            'purchased_books': purchased_books,
            'final_amount': final_amount,
            'book_count': len(purchased_books)
        })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '用户不存在'}, status=404)
    except Exception as e:
        logger.error(f"从购物车购买失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({'success': False, 'message': f'购买失败: {str(e)}'}, status=500)

@csrf_exempt
def remove_book_from_cart_new(request):
    """从购物车移除指定书籍"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方法错误'})
    
    if not request.session.get('username'):
        return JsonResponse({'success': False, 'message': '请先登录'})
    
    try:
        data = json.loads(request.body)
        book_id = data.get('book_id')
        book_title = data.get('book_title')  # 支持通过书名删除
        
        username = request.session.get('username')
        user = UserProfile.objects.get(username=username)
        
        # 如果提供了book_id，使用book_id删除
        if book_id:
            CartItem.objects.filter(
                user=user,
                book__book_id=book_id
            ).delete()
        # 如果提供了book_title，使用书名删除
        elif book_title:
            CartItem.objects.filter(
                user=user,
                book__title=book_title
            ).delete()
        else:
            return JsonResponse({'success': False, 'message': '请提供book_id或book_title'})
        
        return JsonResponse({'success': True, 'message': '书籍已从购物车移除'})
        
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '用户不存在'}, status=404)
    except Exception as e:
        logger.error(f"移除书籍失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({'success': False, 'message': '移除失败'})

def remove_from_bookshelf(request):
    """从书架移除书籍API"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方法错误'}, status=405)
    
    if not request.session.get('username'):
        return JsonResponse({'success': False, 'message': '请先登录'}, status=401)
    
    try:
        data = json.loads(request.body)
        book_title = data.get('book_title')
        book_id = data.get('book_id')
        
        # 如果提供了book_id，先获取书名
        if book_id and not book_title:
            try:
                book = BookName.objects.get(book_id=book_id)
                book_title = book.title
            except BookName.DoesNotExist:
                return JsonResponse({'success': False, 'message': '书籍不存在'}, status=404)
        
        if not book_title:
            return JsonResponse({'success': False, 'message': '书籍标题或ID不能为空'}, status=400)
        
        user = UserProfile.objects.get(username=request.session['username'])
        bookshelf_books = user.get_bookshelf_books()
        
        # 检查是否在书架中
        if book_title not in bookshelf_books:
            return JsonResponse({'success': False, 'message': '不在书架中'})
        
        # 从书架移除
        bookshelf_books.remove(book_title)
        user.set_bookshelf_books(bookshelf_books)
        user.save()
        
        return JsonResponse({'success': True, 'message': '已从书架移除'})
        
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '用户不存在'}, status=404)
    except ValueError:
        return JsonResponse({'success': False, 'message': '书籍不在书架中'}, status=400)
    except Exception as e:
        logger.error(f"从书架移除失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({'success': False, 'message': '移除失败，请稍后重试'}, status=500)

@csrf_exempt
def remove_from_cart_new(request):
    """新版从购物车移除API（支持item_id和book_id）"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方法错误'}, status=405)
    
    if not request.session.get('username'):
        return JsonResponse({'success': False, 'message': '请先登录'}, status=401)
    
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        book_id = data.get('book_id')
        
        username = request.session.get('username')
        user = UserProfile.objects.get(username=username)
        
        # 优先使用item_id，如果没有则使用book_id
        if item_id:
            cart_item = CartItem.objects.filter(
                item_id=item_id,
                user=user
            ).first()
            if cart_item:
                cart_item.delete()
                return JsonResponse({'success': True, 'message': '移除成功'})
            else:
                return JsonResponse({'success': False, 'message': '购物车项目不存在'}, status=404)
        elif book_id:
            # 使用 book__book_id 保持与其他函数的一致性
            cart_item = CartItem.objects.filter(
                user=user,
                book__book_id=book_id
            ).first()
            if cart_item:
                cart_item.delete()
                return JsonResponse({'success': True, 'message': '移除成功'})
            else:
                return JsonResponse({'success': False, 'message': '购物车项目不存在'}, status=404)
        else:
            return JsonResponse({'success': False, 'message': '请提供item_id或book_id'}, status=400)
        
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '用户不存在'}, status=404)
    except Exception as e:
        logger.error(f"移除购物车项目失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({'success': False, 'message': '移除失败，请稍后重试'}, status=500)

def remove_from_collection(request):
    """取消收藏API"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方法错误'}, status=405)
    
    if not request.session.get('username'):
        return JsonResponse({'success': False, 'message': '请先登录'}, status=401)
    
    try:
        data = json.loads(request.body)
        book_title = data.get('book_title')
        
        if not book_title:
            return JsonResponse({'success': False, 'message': '书籍标题不能为空'}, status=400)
        
        user = UserProfile.objects.get(username=request.session['username'])
        collected_books = user.get_collected_books()
        
        # 移除收藏
        original_count = len(collected_books)
        collected_books = [
            item for item in collected_books
            if not (
                (isinstance(item, dict) and item.get('book_title') == book_title) or 
                (isinstance(item, str) and item == book_title)
            )
        ]
        
        if len(collected_books) == original_count:
            return JsonResponse({'success': False, 'message': '未收藏'})
        
        user.set_collected_books(collected_books)
        user.save()
        
        # 更新书籍收藏数
        collection_count = 0
        try:
            book = BookName.objects.get(title=book_title)
            book.collection_count = max(0, (book.collection_count or 0) - 1)
            book.save()
            collection_count = book.collection_count
        except BookName.DoesNotExist:
            pass
        
        return JsonResponse({
            'success': True,
            'message': '已取消收藏',
            'collection_count': collection_count
        })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '用户不存在'}, status=404)
    except Exception as e:
        logger.error(f"取消收藏失败: {e}")
        return JsonResponse({'success': False, 'message': '取消收藏失败，请稍后重试'}, status=500)

@csrf_exempt
def submit_review(request):
    """提交评价API"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方法错误'}, status=405)
    
    if not request.session.get('username'):
        return JsonResponse({'success': False, 'message': '请先登录'}, status=401)
    
    try:
        data = json.loads(request.body)
        book_title = data.get('book_title') or data.get('book_id')
        rating = data.get('rating')
        review_content = data.get('review_content') or data.get('content', '')
        
        if not book_title:
            return JsonResponse({'success': False, 'message': '书籍信息不能为空'}, status=400)
        
        if not rating:
            return JsonResponse({'success': False, 'message': '评分不能为空'}, status=400)
        
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                return JsonResponse({'success': False, 'message': '评分必须在1-5之间'}, status=400)
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'message': '评分格式错误'}, status=400)
        
        # 获取书籍信息
        try:
            if isinstance(book_title, int) or (isinstance(book_title, str) and book_title.isdigit()):
                book = BookName.objects.get(book_id=int(book_title))
            else:
                book = BookName.objects.get(title=book_title)
        except BookName.DoesNotExist:
            return JsonResponse({'success': False, 'message': '书籍不存在'}, status=404)
        
        username = request.session['username']
        user = UserProfile.objects.get(username=username)
        
        # 检查是否已经评价过
        existing_review = BookEvaluate.objects.filter(
            customer_name=username,
            book_title=book.title
        ).first()
        
        if existing_review:
            # 更新现有评价
            existing_review.rating = rating
            existing_review.review_content = review_content
            existing_review.save()
        else:
            # 创建新评价
            BookEvaluate.objects.create(
                customer_name=username,
                book_title=book.title,
                rating=rating,
                review_content=review_content
            )
        
        # 重新计算书籍的平均评分
        evaluations = BookEvaluate.objects.filter(book_title=book.title)
        avg_rating = evaluations.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0
        book.rating = round(float(avg_rating), 2)
        book.save()
        
        return JsonResponse({
            'success': True,
            'message': '评价提交成功',
            'rating': float(book.rating),
            'collection_count': book.collection_count or 0
        })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '用户不存在'}, status=404)
    except Exception as e:
        logger.error(f"提交评价失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({'success': False, 'message': '评价提交失败，请稍后重试'}, status=500)

@csrf_exempt
@csrf_exempt
def update_cart_item(request):
    """更新购物车项目（主要用于更新选中状态）"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方法错误'}, status=405)
    
    if not request.session.get('username'):
        return JsonResponse({'success': False, 'message': '请先登录'}, status=401)
    
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        is_selected = data.get('is_selected', True)
        
        username = request.session.get('username')
        user = UserProfile.objects.get(username=username)
        
        cart_item = CartItem.objects.get(
            item_id=item_id,
            user=user
        )
        
        cart_item.is_selected = is_selected
        cart_item.save()
        
        return JsonResponse({'success': True, 'message': '更新成功'})
        
    except CartItem.DoesNotExist:
        return JsonResponse({'success': False, 'message': '购物车项目不存在'}, status=404)
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '用户不存在'}, status=404)
    except Exception as e:
        logger.error(f"更新购物车项目失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({'success': False, 'message': '更新失败，请稍后重试'}, status=500)

@csrf_exempt
def update_read_time(request):
    """更新阅读时间API"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方法错误'}, status=405)
    
    if not request.session.get('username'):
        return JsonResponse({'success': False, 'message': '请先登录'}, status=401)
    
    try:
        data = json.loads(request.body)
        book_title = data.get('book_title')
        chapter_number = data.get('chapter_number')
        
        if not book_title:
            return JsonResponse({'success': False, 'message': '书籍标题不能为空'}, status=400)
        
        if not chapter_number:
            return JsonResponse({'success': False, 'message': '章节号不能为空'}, status=400)
        
        try:
            chapter_number = int(chapter_number)
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'message': '章节号格式错误'}, status=400)
        
        # 获取用户
        user_profile = UserProfile.objects.get(username=request.session['username'])
        
        # 查找书籍
        try:
            book = BookName.objects.get(title=book_title)
        except BookName.DoesNotExist:
            return JsonResponse({'success': False, 'message': '书籍不存在'}, status=404)
        except BookName.MultipleObjectsReturned:
            # 如果有多本同名书籍，取第一本
            book = BookName.objects.filter(title=book_title).first()
            if not book:
                return JsonResponse({'success': False, 'message': '书籍不存在'}, status=404)
        
        # 检查是否是免费章节（前两章）
        is_free_chapter = chapter_number <= 2
        
        # 检查是否是VIP用户
        is_vip_user = user_profile.vip_level == 'VIP'
        
        # 查找是否已存在购买记录
        ownership = UserBookOwnership.objects.filter(
            user_id=user_profile.user_id,
            book_id=book.book_id
        ).first()
        
        # 如果存在购买记录，更新阅读进度
        if ownership:
            # 只有当新章节号大于当前进度时才更新
            if chapter_number > (ownership.reading_progress or 0):
                ownership.reading_progress = chapter_number
                ownership.last_read_time = timezone.now()
                ownership.save()
            else:
                # 即使章节号没有增加，也更新最后阅读时间
                ownership.last_read_time = timezone.now()
                ownership.save()
        else:
            # 如果不存在购买记录
            # VIP用户不自动创建购买记录，只更新书架
            # 普通用户也不自动创建，只有真正购买时才创建记录
            # 这里只更新书架，不创建购买记录
            pass
        
        # 确保书籍在书架中
        bookshelf_books = user_profile.get_bookshelf_books()
        if book.title not in bookshelf_books:
            bookshelf_books.append(book.title)
            user_profile.set_bookshelf_books(bookshelf_books)
            user_profile.save()
        
        # 构建返回数据
        response_data = {
            'success': True, 
            'message': '阅读记录已更新',
        }
        
        # 如果有购买记录，添加阅读进度信息
        if ownership:
            response_data['reading_progress'] = ownership.reading_progress
            response_data['last_read_time'] = ownership.last_read_time.isoformat() if ownership.last_read_time else None
        else:
            # 没有购买记录（VIP用户或免费章节），只更新了书架
            response_data['reading_progress'] = chapter_number
            response_data['last_read_time'] = timezone.now().isoformat()
            response_data['message'] = '已添加到书架' if is_vip_user or is_free_chapter else '阅读记录已更新'
        
        return JsonResponse(response_data)
        
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '用户不存在'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': '请求数据格式错误'}, status=400)
    except Exception as e:
        logger.error(f"更新阅读记录失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({'success': False, 'message': '更新阅读记录失败，请稍后重试'}, status=500)

def user_get_order_detail(request, order_id):
    """用户获取订单详情API"""
    if not request.session.get('username'):
        return JsonResponse({'success': False, 'message': '请先登录'}, status=401)
    
    try:
        username = request.session.get('username')
        user = UserProfile.objects.get(username=username)
        
        # 获取订单
        order = BookOrder.objects.get(order_id=order_id, customer_name=user.username)
        
        # 解析订单内容
        order_content = order.get_order_content()
        
        # 构建书籍列表
        books = []
        for item in order_content:
            books.append({
                'book_id': item.get('book_id'),
                'book_title': item.get('book_title', '未知书籍'),
                'author': item.get('author', ''),
                'category': item.get('category', ''),
                'price': float(item.get('price', 0)),
                'quantity': item.get('quantity', 1),
            })
        
        return JsonResponse({
            'success': True,
            'order': {
                'order_id': order.order_id,
                'order_number': order.order_number,
                'order_status': order.order_status,
                'order_amount': float(order.order_amount),
                'create_time': order.create_time.strftime('%Y-%m-%d %H:%M:%S') if order.create_time else None,
                'payment_time': order.payment_time.strftime('%Y-%m-%d %H:%M:%S') if order.payment_time else None,
                'book_count': order.book_count,  # 使用正确的字段名
            },
            'books': books
        })
        
    except BookOrder.DoesNotExist:
        return JsonResponse({'success': False, 'message': '订单不存在'}, status=404)
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': '用户不存在'}, status=404)
    except Exception as e:
        logger.error(f"获取订单详情失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({'success': False, 'message': '获取订单详情失败'}, status=500)

def user_get_order_detail_by_number(request):
    """自动生成的函数 - user_get_order_detail_by_number"""
    return JsonResponse({'success': False, 'message': '功能暂未实现'})

def user_orders(request):
    """用户订单页面"""
    if not request.session.get('username'):
        messages.error(request, '请先登录！')
        return redirect('login')
    
    try:
        username = request.session.get('username')
        user = UserProfile.objects.get(username=username)
        
        # 获取用户的所有订单
        orders = BookOrder.objects.filter(customer_name=user.username).order_by('-create_time')
        
        # 分页
        paginator = Paginator(orders, 10)
        page_number = request.GET.get('page')
        page_orders = paginator.get_page(page_number)
        
        context = {
            'user': user,
            'orders': page_orders,
        }
        
        return render(request, 'novel_app/user_orders.html', context)
        
    except UserProfile.DoesNotExist:
        messages.error(request, '用户不存在！')
        return redirect('login')
    except Exception as e:
        logger.error(f"用户订单页面加载失败: {e}")
        messages.error(request, '订单页面加载失败，请稍后重试')
        return redirect('index')

def user_update_profile(request):
    """自动生成的函数 - user_update_profile"""
    return JsonResponse({'success': False, 'message': '功能暂未实现'})

def user_upload_avatar(request):
    """自动生成的函数 - user_upload_avatar"""
    return JsonResponse({'success': False, 'message': '功能暂未实现'})


def generate_order_number():
    """生成订单号"""
    import time
    timestamp = str(int(time.time()))
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"ORD{timestamp}{random_str}"


# ==================== 优化版管理员书籍管理API ====================

from .services.book_service import BookManagementService
from .services.file_service import FileManagementService
from .services.audit_service import AuditLogService
from .services.error_handler import ErrorHandler, handle_api_errors
from .services.decorators import (
    log_admin_operation, require_admin_permission, 
    validate_request_method, validate_json_request
)

# 初始化服务实例
book_service = BookManagementService()
file_service = FileManagementService()
audit_service = AuditLogService()


@handle_api_errors
@require_admin_permission
@validate_request_method(['POST'])
@validate_json_request
@log_admin_operation('search', 'book')
def api_admin_search_books(request):
    """
    管理员书籍搜索API
    
    POST /api/admin/books/search/
    {
        "query": "搜索关键词",
        "filters": {
            "category": "分类",
            "status": "状态",
            "author": "作者",
            "rating_min": 4.0,
            "rating_max": 5.0,
            "sort_by": "popularity"
        },
        "pagination": {
            "page": 1,
            "size": 20
        }
    }
    """
    try:
        data = getattr(request, 'json', {})
        
        query = data.get('query', '')
        filters = data.get('filters', {})
        pagination = data.get('pagination', {'page': 1, 'size': 20})
        
        # 调用服务层搜索
        result = book_service.search_books(query, filters, pagination)
        
        # 转换书籍对象为字典
        books_data = []
        for book in result['books']:
            book_data = {
                'book_id': book.book_id,
                'title': book.title,
                'author': book.author,
                'category': book.category,
                'status': book.status,
                'description': book.description,
                'cover_url': book.cover_url,
                'rating': float(book.rating),
                'collection_count': book.collection_count,
                'chapter_count': book.chapter_count,
                'view_count': getattr(book, 'view_count', 0),
                'purchase_count': getattr(book, 'purchase_count', 0),
                'price': float(getattr(book, 'price', 0)),
                'is_featured': getattr(book, 'is_featured', False),
                'is_hot': getattr(book, 'is_hot', False),
                'is_new': getattr(book, 'is_new', False),
                'create_time': book.create_time.isoformat() if book.create_time else None,
                'update_time': book.update_time.isoformat() if book.update_time else None,
            }
            books_data.append(book_data)
        
        response_data = {
            'books': books_data,
            'pagination': {
                'total_count': result['total_count'],
                'page_count': result.get('page_count', 1),
                'current_page': result.get('current_page', 1),
                'has_next': result.get('has_next', False),
                'has_previous': result.get('has_previous', False),
            }
        }
        
        return ErrorHandler.success_response(response_data, '搜索成功')
        
    except Exception as e:
        logger.error(f"书籍搜索失败: {str(e)}")
        raise


@admin_required
@csrf_exempt
def api_admin_get_book_detail(request, book_id):
    """
    获取书籍详细信息API
    
    GET /api/admin/books/{book_id}/
    """
    if request.method != 'GET':
        return JsonResponse({'success': False, 'message': '请求方法错误'}, status=405)
    
    try:
        # 确保book_id是整数
        try:
            book_id = int(book_id)
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'message': '无效的书籍ID'}, status=400)
        
        book = BookName.objects.get(book_id=book_id)
        
        # 获取章节统计
        try:
            chapter_count = BookChapter.objects.filter(book_id=book_id).count()
        except Exception as e:
            logger.error(f"获取章节统计失败: {str(e)}")
            chapter_count = 0
        
        # 获取收藏统计
        try:
            collection_count = UserProfile.objects.filter(
                collected_books__icontains=book.title
            ).count()
        except Exception as e:
            logger.error(f"获取收藏统计失败: {str(e)}")
            collection_count = 0
        
        # 获取评分统计
        try:
            rating_result = BookEvaluate.objects.filter(
                book_title=book.title
            ).aggregate(avg_rating=Avg('rating'))
            avg_rating = rating_result['avg_rating'] if rating_result['avg_rating'] is not None else 0
        except Exception as e:
            logger.error(f"获取评分统计失败: {str(e)}")
            avg_rating = 0
        
        # 安全获取字段值
        def safe_get_attr(obj, attr, default=None):
            try:
                value = getattr(obj, attr, default)
                if value is None:
                    return default
                return value
            except Exception:
                return default
        
        # 处理tags字段（可能是JSON字段）
        tags = safe_get_attr(book, 'tags', [])
        if isinstance(tags, str):
            try:
                import json
                tags = json.loads(tags)
            except:
                tags = []
        if not isinstance(tags, list):
            tags = []
        
        book_data = {
            'book_id': book.book_id,
            'title': book.title or '',
            'author': book.author or '',
            'category': book.category or '',
            'status': book.status or '连载中',
            'description': book.description or '',
            'word_count': book.word_count or '',
            'cover_url': book.cover_url or '',
            'rating': round(float(avg_rating), 1),
            'collection_count': collection_count,
            'chapter_count': chapter_count,
            'view_count': safe_get_attr(book, 'view_count', 0),
            'purchase_count': safe_get_attr(book, 'purchase_count', 0),
            'price': float(safe_get_attr(book, 'price', 0)),
            'original_price': float(safe_get_attr(book, 'original_price', 0)) if safe_get_attr(book, 'original_price', None) else None,
            'tags': tags,
            'is_featured': safe_get_attr(book, 'is_featured', False),
            'is_hot': safe_get_attr(book, 'is_hot', False),
            'is_new': safe_get_attr(book, 'is_new', False),
            'create_time': book.create_time.isoformat() if book.create_time else None,
            'update_time': book.update_time.isoformat() if book.update_time else None,
        }
        
        return JsonResponse({'success': True, 'data': book_data, 'message': '获取成功'})
        
    except BookName.DoesNotExist:
        return JsonResponse({'success': False, 'message': '书籍不存在'}, status=404)
    except Exception as e:
        import traceback
        logger.error(f"获取书籍详情失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return JsonResponse({'success': False, 'message': f'获取失败: {str(e)}'}, status=500)


@admin_required
@csrf_exempt
def api_admin_create_book(request):
    """
    创建书籍API
    
    POST /api/admin/books/
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方法错误'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        # 验证必填字段
        required_fields = ['title', 'author', 'category']
        for field in required_fields:
            if not data.get(field, '').strip():
                return JsonResponse({'success': False, 'message': f'{field}字段不能为空'}, status=400)
        
        # 检查书籍是否已存在
        if BookName.objects.filter(title=data['title'].strip(), author=data['author'].strip()).exists():
            return JsonResponse({'success': False, 'message': '该书籍已存在'}, status=400)
        
        # 创建书籍
        book = BookName.objects.create(
            title=data['title'].strip(),
            author=data['author'].strip(),
            category=data['category'].strip(),
            status=data.get('status', '连载中'),
            description=data.get('description', '').strip(),
            cover_url=data.get('cover_url', '').strip(),
            price=float(data.get('price', 9.99)),
            rating=0.0,
            collection_count=0,
            chapter_count=0,
            create_time=timezone.now(),
            update_time=timezone.now(),
        )
        
        book_data = {
            'book_id': book.book_id,
            'title': book.title,
            'author': book.author,
            'category': book.category,
            'status': book.status,
            'create_time': book.create_time.isoformat() if book.create_time else None,
        }
        
        return JsonResponse({'success': True, 'data': book_data, 'message': '书籍创建成功'})
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': '数据格式错误'}, status=400)
    except Exception as e:
        logger.error(f"创建书籍失败: {str(e)}")
        return JsonResponse({'success': False, 'message': '创建失败，请稍后重试'}, status=500)


@admin_required
@csrf_exempt
def api_admin_update_book(request, book_id):
    """
    更新书籍API
    
    PUT /api/admin/books/{book_id}/update/
    """
    if request.method != 'PUT':
        return JsonResponse({'success': False, 'message': '请求方法错误'}, status=405)
    
    try:
        # 确保book_id是整数
        try:
            book_id = int(book_id)
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'message': '无效的书籍ID'}, status=400)
        
        data = json.loads(request.body)
        
        book = BookName.objects.get(book_id=book_id)
        
        # 更新字段
        if 'title' in data and data['title']:
            book.title = str(data['title']).strip()
        if 'author' in data and data['author']:
            book.author = str(data['author']).strip()
        if 'category' in data and data['category']:
            book.category = str(data['category']).strip()
        if 'status' in data and data['status']:
            book.status = str(data['status'])
        if 'description' in data:
            book.description = str(data['description']).strip() if data['description'] else ''
        if 'cover_url' in data:
            book.cover_url = str(data['cover_url']).strip() if data['cover_url'] else ''
        if 'price' in data:
            try:
                book.price = float(data['price'])
            except (ValueError, TypeError):
                pass  # 如果价格无效，保持原值
        
        book.update_time = timezone.now()
        book.save()
        
        book_data = {
            'book_id': book.book_id,
            'title': book.title,
            'author': book.author,
            'category': book.category,
            'status': book.status,
            'update_time': book.update_time.isoformat() if book.update_time else None,
        }
        
        return JsonResponse({'success': True, 'data': book_data, 'message': '书籍更新成功'})
        
    except BookName.DoesNotExist:
        return JsonResponse({'success': False, 'message': '书籍不存在'}, status=404)
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析错误: {str(e)}")
        return JsonResponse({'success': False, 'message': '数据格式错误'}, status=400)
    except Exception as e:
        import traceback
        logger.error(f"更新书籍失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return JsonResponse({'success': False, 'message': f'更新失败: {str(e)}'}, status=500)


@admin_required
@csrf_exempt
def api_admin_delete_book(request, book_id):
    """
    删除书籍API
    
    DELETE /api/admin/books/{book_id}/delete/
    """
    if request.method != 'DELETE':
        return JsonResponse({'success': False, 'message': '请求方法错误'}, status=405)
    
    try:
        # 确保book_id是整数
        try:
            book_id = int(book_id)
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'message': '无效的书籍ID'}, status=400)
        
        book = BookName.objects.get(book_id=book_id)
        book_title = book.title
        
        # 删除相关章节（使用try-except确保即使失败也继续）
        try:
            BookChapter.objects.filter(book_id=book_id).delete()
        except Exception as e:
            logger.warning(f"删除章节失败: {str(e)}")
        
        # 删除相关评价
        try:
            BookEvaluate.objects.filter(book_title=book.title).delete()
        except Exception as e:
            logger.warning(f"删除评价失败: {str(e)}")
        
        # 删除用户拥有权记录
        try:
            UserBookOwnership.objects.filter(book_id=book_id).delete()
        except Exception as e:
            logger.warning(f"删除用户拥有权记录失败: {str(e)}")
        
        # 删除购物车中的记录
        try:
            CartItem.objects.filter(book=book).delete()
        except Exception as e:
            logger.warning(f"删除购物车记录失败: {str(e)}")
        
        # 删除书籍
        book.delete()
        
        return JsonResponse({'success': True, 'message': f'书籍《{book_title}》删除成功'})
        
    except BookName.DoesNotExist:
        return JsonResponse({'success': False, 'message': '书籍不存在'}, status=404)
    except Exception as e:
        import traceback
        logger.error(f"删除书籍失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return JsonResponse({'success': False, 'message': f'删除失败: {str(e)}'}, status=500)


@handle_api_errors
@require_admin_permission
@validate_request_method(['GET'])
def api_admin_get_categories(request):
    """
    获取所有书籍分类API
    
    GET /api/admin/books/categories/
    """
    try:
        categories = book_service.get_categories()
        return ErrorHandler.success_response(categories, '获取分类成功')
        
    except Exception as e:
        logger.error(f"获取分类失败: {str(e)}")
        raise


@handle_api_errors
@require_admin_permission
@validate_request_method(['GET'])
def api_admin_get_authors(request):
    """
    获取所有作者API
    
    GET /api/admin/books/authors/
    """
    try:
        authors = book_service.get_authors()
        return ErrorHandler.success_response(authors, '获取作者列表成功')
        
    except Exception as e:
        logger.error(f"获取作者列表失败: {str(e)}")
        raise


@admin_required
def admin_books(request):
    """管理员书籍管理页面"""
    try:
        from datetime import datetime, timedelta
        from django.utils import timezone
        
        # 获取搜索和筛选参数
        search_query = request.GET.get('search', '')
        channel = request.GET.get('channel', '')
        category = request.GET.get('category', '')
        update_time = request.GET.get('update_time', '')
        is_completed = request.GET.get('is_completed', '')
        
        # 频道和分类的映射关系
        channel_category_mapping = {
            '女生原创': ['现代言情', '古代言情', '幻想言情', '游戏竞技', '衍生言情', '现实主义'],
            '男生原创': ['历史', '军事', '科幻', '游戏', '玄幻奇幻', '都市', '奇闻异事', '武侠仙侠', '体育', 'N次元', '现实题材'],
            '出版图书': ['文学艺术', '人文社科', '经管励志', '经典文学', '出版小说', '少儿教育']
        }
        
        # 构建查询
        books = BookName.objects.all()
        
        # 搜索
        if search_query:
            books = books.filter(
                Q(title__icontains=search_query) | 
                Q(author__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        # 频道筛选（通过分类映射）
        if channel and channel in channel_category_mapping:
            allowed_categories = channel_category_mapping[channel]
            books = books.filter(category__in=allowed_categories)
        
        # 分类筛选
        if category:
            books = books.filter(category=category)
        
        # 更新时间筛选
        if update_time:
            now = timezone.now()
            if update_time == '3天内':
                books = books.filter(update_time__gte=now - timedelta(days=3))
            elif update_time == '7天内':
                books = books.filter(update_time__gte=now - timedelta(days=7))
            elif update_time == '30天内':
                books = books.filter(update_time__gte=now - timedelta(days=30))
        
        # 是否完结筛选
        if is_completed:
            if is_completed == '已完结':
                books = books.filter(status='完结')
            elif is_completed == '连载中':
                books = books.filter(status='连载中')
        
        # 排序（默认按创建时间倒序）
        books = books.order_by('-create_time')
        
        # 分页
        paginator = Paginator(books, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # 获取所有分类
        all_categories = BookName.objects.values_list('category', flat=True).distinct().order_by('category')
        categories_list = [cat for cat in all_categories if cat]
        
        # 频道选项
        channel_choices = [
            ('', '全部'),
            ('女生原创', '女生原创'),
            ('男生原创', '男生原创'),
            ('出版图书', '出版图书'),
        ]
        
        # 更新时间选项
        update_time_choices = [
            ('', '全部'),
            ('3天内', '3天内'),
            ('7天内', '7天内'),
            ('30天内', '30天内'),
        ]
        
        # 是否完结选项
        is_completed_choices = [
            ('', '全部'),
            ('已完结', '已完结'),
            ('连载中', '连载中'),
        ]
        
        import json
        context = {
            'page_obj': page_obj,
            'total_books': books.count(),
            'search_query': search_query,
            'channel': channel,
            'category': category,
            'update_time': update_time,
            'is_completed': is_completed,
            'categories': categories_list,
            'channel_choices': channel_choices,
            'update_time_choices': update_time_choices,
            'is_completed_choices': is_completed_choices,
            'channel_category_mapping': json.dumps(channel_category_mapping),
        }
        
        return render(request, 'novel_app/admin_books.html', context)
        
    except Exception as e:
        logger.error(f"管理员书籍页面加载失败: {str(e)}")
        messages.error(request, '页面加载失败，请稍后重试')
        return redirect('admin_dashboard')


@admin_required
@csrf_exempt
def admin_books_batch_update_status(request):
    """批量更新书籍状态"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方法错误'})
    
    try:
        data = json.loads(request.body)
        book_ids = data.get('book_ids', [])
        status = data.get('status', '')
        
        if not book_ids:
            return JsonResponse({'success': False, 'message': '请选择要修改的书籍'})
        
        if not status:
            return JsonResponse({'success': False, 'message': '请选择状态'})
        
        # 批量更新
        updated_count = BookName.objects.filter(book_id__in=book_ids).update(status=status)
        
        return JsonResponse({
            'success': True, 
            'message': f'成功修改 {updated_count} 本书籍的状态',
            'updated_count': updated_count
        })
        
    except Exception as e:
        logger.error(f"批量更新状态失败: {str(e)}")
        return JsonResponse({'success': False, 'message': '批量更新失败，请稍后重试'})


@admin_required
@csrf_exempt
def admin_books_batch_delete(request):
    """批量删除书籍"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方法错误'})
    
    try:
        data = json.loads(request.body)
        book_ids = data.get('book_ids', [])
        
        if not book_ids:
            return JsonResponse({'success': False, 'message': '请选择要删除的书籍'})
        
        # 批量删除
        deleted_count, _ = BookName.objects.filter(book_id__in=book_ids).delete()
        
        return JsonResponse({
            'success': True,
            'message': f'成功删除 {deleted_count} 本书籍',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        logger.error(f"批量删除失败: {str(e)}")
        return JsonResponse({'success': False, 'message': '批量删除失败，请稍后重试'})


@admin_required
@csrf_exempt
def admin_books_stats(request):
    """书籍统计API"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'message': '请求方法错误'})
    
    try:
        from django.db.models import Count, Avg, Sum
        from django.utils import timezone
        from datetime import timedelta
        
        # 基础统计
        total_books = BookName.objects.count()
        total_chapters = BookChapter.objects.count()
        
        # 按状态统计
        status_stats = BookName.objects.values('status').annotate(
            count=Count('status')
        ).order_by('-count')
        
        # 按分类统计
        category_stats = BookName.objects.values('category').annotate(
            count=Count('category')
        ).order_by('-count')
        
        # 最受欢迎的书籍（按收藏数）
        popular_books = BookName.objects.order_by('-collection_count')[:10]
        popular_books_data = []
        for book in popular_books:
            popular_books_data.append({
                'book_id': book.book_id,
                'title': book.title,
                'author': book.author,
                'collection_count': book.collection_count or 0,
                'rating': float(book.rating) if book.rating else 0,
            })
        
        # 最新添加的书籍
        recent_books = BookName.objects.order_by('-create_time')[:10]
        recent_books_data = []
        for book in recent_books:
            recent_books_data.append({
                'book_id': book.book_id,
                'title': book.title,
                'author': book.author,
                'create_time': book.create_time.isoformat() if book.create_time else None,
                'status': book.status,
            })
        
        # 评分统计
        rating_stats = BookEvaluate.objects.aggregate(
            avg_rating=Avg('rating'),
            total_evaluations=Count('id')
        )
        
        # 今日统计
        today = timezone.now().date()
        books_today = BookName.objects.filter(create_time__date=today).count()
        chapters_today = BookChapter.objects.filter(create_time__date=today).count()
        
        # 本周统计
        week_ago = today - timedelta(days=7)
        books_this_week = BookName.objects.filter(create_time__date__gte=week_ago).count()
        chapters_this_week = BookChapter.objects.filter(create_time__date__gte=week_ago).count()
        
        # 价格统计
        from django.db.models import Min, Max
        price_stats = BookName.objects.aggregate(
            avg_price=Avg('price'),
            min_price=Min('price'),
            max_price=Max('price'),
            total_value=Sum('price')
        )
        
        data = {
            'basic_stats': {
                'total_books': total_books,
                'total_chapters': total_chapters,
                'books_today': books_today,
                'chapters_today': chapters_today,
                'books_this_week': books_this_week,
                'chapters_this_week': chapters_this_week,
            },
            'status_stats': list(status_stats),
            'category_stats': list(category_stats),
            'popular_books': popular_books_data,
            'recent_books': recent_books_data,
            'rating_stats': {
                'avg_rating': round(float(rating_stats['avg_rating'] or 0), 1),
                'total_evaluations': rating_stats['total_evaluations'],
            },
            'price_stats': {
                'avg_price': round(float(price_stats['avg_price'] or 0), 2),
                'min_price': float(price_stats['min_price'] or 0),
                'max_price': float(price_stats['max_price'] or 0),
                'total_value': round(float(price_stats['total_value'] or 0), 2),
            }
        }
        
        return JsonResponse({'success': True, 'data': data})
        
    except Exception as e:
        logger.error(f"获取书籍统计失败: {str(e)}")
        return JsonResponse({'success': False, 'message': '获取统计数据失败'})


@admin_required
@csrf_exempt  
def admin_book_stats_detail(request, book_id):
    """单个书籍详细统计API"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'message': '请求方法错误'})
    
    try:
        book = BookName.objects.get(book_id=book_id)
        
        # 章节统计
        chapters = BookChapter.objects.filter(book_id=book_id)
        chapter_count = chapters.count()
        total_words = sum(len(chapter.content or '') for chapter in chapters)
        
        # 评价统计
        evaluations = BookEvaluate.objects.filter(book_title=book.title)
        evaluation_stats = evaluations.aggregate(
            avg_rating=Avg('rating'),
            total_evaluations=Count('id')
        )
        
        # 评分分布
        rating_distribution = {}
        for i in range(1, 6):
            rating_distribution[str(i)] = evaluations.filter(rating=i).count()
        
        # 收藏统计
        collection_count = UserProfile.objects.filter(
            collected_books__icontains=book.title
        ).count()
        
        # 购买统计
        purchase_stats = UserBookOwnership.objects.filter(book_id=book_id).aggregate(
            total_purchases=Count('id'),
            total_revenue=Sum('purchase_price')
        )
        
        # 阅读进度统计
        reading_progress = UserBookOwnership.objects.filter(
            book_id=book_id
        ).values('reading_progress').annotate(
            count=Count('reading_progress')
        ).order_by('reading_progress')
        
        data = {
            'book_info': {
                'book_id': book.book_id,
                'title': book.title,
                'author': book.author,
                'category': book.category,
                'status': book.status,
                'create_time': book.create_time.isoformat() if book.create_time else None,
            },
            'content_stats': {
                'chapter_count': chapter_count,
                'total_words': total_words,
                'avg_words_per_chapter': round(total_words / chapter_count, 0) if chapter_count > 0 else 0,
            },
            'evaluation_stats': {
                'avg_rating': round(float(evaluation_stats['avg_rating'] or 0), 1),
                'total_evaluations': evaluation_stats['total_evaluations'],
                'rating_distribution': rating_distribution,
            },
            'engagement_stats': {
                'collection_count': collection_count,
                'view_count': book.view_count or 0,
            },
            'purchase_stats': {
                'total_purchases': purchase_stats['total_purchases'],
                'total_revenue': float(purchase_stats['total_revenue'] or 0),
                'avg_revenue_per_purchase': round(
                    float(purchase_stats['total_revenue'] or 0) / max(purchase_stats['total_purchases'], 1), 2
                ),
            },
            'reading_progress': list(reading_progress),
        }
        
        return JsonResponse({'success': True, 'data': data})
        
    except BookName.DoesNotExist:
        return JsonResponse({'success': False, 'message': '书籍不存在'})
    except Exception as e:
        logger.error(f"获取书籍详细统计失败: {str(e)}")
        return JsonResponse({'success': False, 'message': '获取统计数据失败'})


# ==================== 爬虫监控相关API ====================

@csrf_exempt
def crawler_monitor_view(request):
    """爬虫监控页面"""
    if not request.session.get('is_admin'):
        messages.error(request, '需要管理员权限访问爬虫监控')
        return redirect('login')
    
    return render(request, 'novel_app/crawler_monitor.html')


@csrf_exempt
def api_crawler_statistics(request):
    """获取爬虫统计信息API"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'message': '仅支持GET请求'}, status=405)
    
    try:
        from .crawler_monitor import CrawlerMonitor
        from .models import CrawlerTask
        
        monitor = CrawlerMonitor()
        stats = monitor.get_statistics()
        
        return JsonResponse({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logger.error(f"获取爬虫统计信息失败: {e}")
        return JsonResponse({
            'success': False,
            'message': f'获取统计信息失败: {str(e)}'
        }, status=500)


@csrf_exempt
def api_crawler_tasks(request):
    """获取爬虫任务列表API"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'message': '仅支持GET请求'}, status=405)
    
    try:
        from .crawler_monitor import CrawlerMonitor
        from .models import CrawlerTask
        
        # 获取查询参数
        status = request.GET.get('status', '')
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        
        monitor = CrawlerMonitor()
        
        # 获取任务列表
        tasks_queryset = CrawlerTask.objects.all().order_by('-created_at')
        
        # 按状态筛选
        if status:
            tasks_queryset = tasks_queryset.filter(status=status)
        
        # 分页
        from django.core.paginator import Paginator
        paginator = Paginator(tasks_queryset, page_size)
        tasks_page = paginator.get_page(page)
        
        # 构建任务列表数据
        tasks_data = []
        for task in tasks_page:
            task_data = {
                'task_id': task.task_id,
                'book_id': task.book_id,
                'book_title': task.book_title,
                'status': task.status,
                'total_chapters': task.total_chapters,
                'completed_chapters': task.completed_chapters,
                'failed_chapters': task.failed_chapters,
                'progress_percentage': task.get_progress_percentage(),
                'created_at': task.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'started_at': task.started_at.strftime('%Y-%m-%d %H:%M:%S') if task.started_at else None,
                'completed_at': task.completed_at.strftime('%Y-%m-%d %H:%M:%S') if task.completed_at else None,
                'error_message': task.error_message,
                'retry_count': task.retry_count,
            }
            tasks_data.append(task_data)
        
        return JsonResponse({
            'success': True,
            'data': {
                'tasks': tasks_data,
                'pagination': {
                    'current_page': tasks_page.number,
                    'total_pages': paginator.num_pages,
                    'total_count': paginator.count,
                    'page_size': page_size,
                    'has_next': tasks_page.has_next(),
                    'has_previous': tasks_page.has_previous(),
                }
            }
        })
    except Exception as e:
        logger.error(f"获取爬虫任务列表失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'message': f'获取任务列表失败: {str(e)}'
        }, status=500)


@csrf_exempt
def api_crawler_task_detail(request, task_id):
    """获取爬虫任务详情API"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'message': '仅支持GET请求'}, status=405)
    
    try:
        from .crawler_monitor import CrawlerMonitor
        from .models import CrawlerTask
        
        monitor = CrawlerMonitor()
        task_detail = monitor.get_task_detail(task_id)
        
        if task_detail:
            return JsonResponse({
                'success': True,
                'data': task_detail
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f'任务 {task_id} 不存在'
            }, status=404)
    except Exception as e:
        logger.error(f"获取爬虫任务详情失败: {e}")
        return JsonResponse({
            'success': False,
            'message': f'获取任务详情失败: {str(e)}'
        }, status=500)


@csrf_exempt
def api_crawler_retry_task(request):
    """重试失败的爬虫任务API"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '仅支持POST请求'}, status=405)
    
    try:
        from .crawler_monitor import CrawlerMonitor
        
        # 解析请求数据
        data = json.loads(request.body)
        task_id = data.get('task_id')
        
        if not task_id:
            return JsonResponse({
                'success': False,
                'message': '缺少task_id参数'
            }, status=400)
        
        monitor = CrawlerMonitor()
        result = monitor.retry_task(task_id)
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': result['message']
            })
        else:
            return JsonResponse({
                'success': False,
                'message': result['message']
            }, status=400)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON数据'
        }, status=400)
    except Exception as e:
        logger.error(f"重试爬虫任务失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'message': f'重试任务失败: {str(e)}'
        }, status=500)


@csrf_exempt
def api_crawler_start_task(request):
    """启动新的爬虫任务API"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '仅支持POST请求'}, status=405)
    
    try:
        from .crawler_monitor import CrawlerMonitor
        
        # 解析请求数据
        data = json.loads(request.body)
        book_id = data.get('book_id')
        max_chapters = data.get('max_chapters', 10)
        chapter_numbers = data.get('chapter_numbers')  # 可选：指定章节编号列表
        
        if not book_id:
            return JsonResponse({
                'success': False,
                'message': '缺少book_id参数'
            }, status=400)
        
        # 验证书籍是否存在
        try:
            book = BookName.objects.get(book_id=book_id)
        except BookName.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': f'书籍ID {book_id} 不存在'
            }, status=404)
        
        monitor = CrawlerMonitor()
        task_id = monitor.start_crawl_task(
            book_id=book_id,
            book_title=book.title,
            max_chapters=max_chapters,
            chapter_numbers=chapter_numbers
        )
        
        return JsonResponse({
            'success': True,
            'message': f'成功启动爬虫任务',
            'data': {
                'task_id': task_id,
                'book_id': book_id,
                'book_title': book.title
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON数据'
        }, status=400)
    except Exception as e:
        logger.error(f"启动爬虫任务失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'message': f'启动任务失败: {str(e)}'
        }, status=500)
