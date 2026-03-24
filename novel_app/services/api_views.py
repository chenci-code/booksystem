"""
API视图服务
提供RESTful API端点
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from decimal import Decimal
import logging
import json

from ..models import (
    BookName, BookChapter, UserProfile, UserBookOwnership,
    BookOrder, CartItem
)
from ..auth_utils import get_current_user, get_current_admin
from ..business_utils import (
    check_book_access, check_chapter_access, purchase_book,
    calculate_cart_total, generate_order_number
)
from ..crawler_service import DjangoBookCrawlerService

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def _crawl_single_chapter_api_legacy(request):
    """
    爬取单个章节API
    
    请求参数:
        - book_title: 书籍标题
        - chapter_number: 章节号
        - chapter_url: 章节URL(可选)
    
    返回:
        - success: 是否成功
        - message: 提示信息
        - chapter_data: 章节数据(成功时)
    """
    # 检查管理员权限
    admin = get_current_admin(request)
    if not admin:
        return JsonResponse({
            'success': False,
            'message': '需要管理员权限'
        }, status=403)
    
    try:
        # 解析请求数据
        data = json.loads(request.body)
        book_title = data.get('book_title')
        chapter_number = data.get('chapter_number')
        chapter_url = data.get('chapter_url')
        
        if not book_title or not chapter_number:
            return JsonResponse({
                'success': False,
                'message': '缺少必要参数: book_title 和 chapter_number'
            }, status=400)
        
        # 检查书籍是否存在
        try:
            book = BookName.objects.get(title=book_title)
        except BookName.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': f'书籍《{book_title}》不存在'
            }, status=404)
        
        # 检查章节是否已存在
        existing_chapter = BookChapter.objects.filter(
            book_title=book_title,
            chapter_number=chapter_number
        ).first()
        
        if existing_chapter and existing_chapter.is_crawled:
            return JsonResponse({
                'success': False,
                'message': f'章节已存在且已爬取',
                'chapter_data': {
                    'chapter_id': existing_chapter.chapter_id,
                    'chapter_title': existing_chapter.chapter_title,
                    'word_count': existing_chapter.word_count
                }
            })
        
        # 初始化爬虫服务
        crawler = DjangoBookCrawlerService()
        
        # 如果没有提供URL,尝试从书籍信息中获取
        if not chapter_url and book.chapter_list_api:
            # 这里需要根据实际的API格式来获取章节URL
            # 简化处理:直接返回错误
            return JsonResponse({
                'success': False,
                'message': '需要提供章节URL'
            }, status=400)
        
        # 爬取章节内容
        # 注意:这里需要根据实际的爬虫实现来调用
        # 简化版本:创建或更新章节记录
        if existing_chapter:
            chapter = existing_chapter
        else:
            chapter = BookChapter.objects.create(
                book_title=book_title,
                chapter_number=chapter_number,
                chapter_title=f'第{chapter_number}章',
                is_crawled=False
            )
        
        # 这里应该调用实际的爬虫逻辑
        # chapter_content = crawler.crawl_chapter_content(chapter_url)
        # chapter.chapter_content = chapter_content
        # chapter.word_count = len(chapter_content)
        # chapter.is_crawled = True
        # chapter.save()
        
        return JsonResponse({
            'success': True,
            'message': f'章节爬取任务已创建',
            'chapter_data': {
                'chapter_id': chapter.chapter_id,
                'chapter_number': chapter.chapter_number,
                'chapter_title': chapter.chapter_title,
                'is_crawled': chapter.is_crawled
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON数据'
        }, status=400)
    except Exception as e:
        logger.error(f"爬取章节失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'爬取失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def crawl_single_chapter_api(request):
    """按书籍和章节号爬取单章内容。"""
    admin = get_current_admin(request)
    if not admin:
        return JsonResponse({
            'success': False,
            'message': '需要管理员权限'
        }, status=403)

    try:
        data = json.loads(request.body)
        book_id = data.get('book_id')
        book_title = data.get('book_title')
        chapter_number = data.get('chapter_number')

        if not chapter_number:
            return JsonResponse({
                'success': False,
                'message': '缺少必要参数: chapter_number'
            }, status=400)

        try:
            chapter_number = int(chapter_number)
        except (ValueError, TypeError):
            return JsonResponse({
                'success': False,
                'message': 'chapter_number 格式错误'
            }, status=400)

        if book_id:
            book = BookName.objects.filter(book_id=book_id).first()
        elif book_title:
            book = BookName.objects.filter(title=book_title).first()
        else:
            book = None

        if not book:
            return JsonResponse({
                'success': False,
                'message': '书籍不存在或缺少 book_id/book_title'
            }, status=404)

        crawler = DjangoBookCrawlerService()
        result = crawler.crawl_book_chapters(
            book_id=book.book_id,
            max_chapters=1,
            async_crawl=False,
            chapter_numbers=[chapter_number]
        )

        status_code = 200 if result.get('success') else 400
        return JsonResponse(result, status=status_code)

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON数据'
        }, status=400)
    except Exception as e:
        logger.error(f"爬取章节失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'message': f'爬取失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def create_order_api(request):
    """
    创建订单API
    
    请求参数:
        - book_ids: 书籍ID列表 (从购物车结算时使用)
        - payment_method: 支付方式 (默认'余额')
    
    返回:
        - success: 是否成功
        - message: 提示信息
        - order_data: 订单数据(成功时)
    """
    # 检查用户登录
    user = get_current_user(request)
    if not user:
        return JsonResponse({
            'success': False,
            'message': '请先登录'
        }, status=401)
    
    try:
        # 解析请求数据
        data = json.loads(request.body)
        book_ids = data.get('book_ids', [])
        payment_method = data.get('payment_method', '余额')
        
        if not book_ids:
            return JsonResponse({
                'success': False,
                'message': '请选择要购买的书籍'
            }, status=400)
        
        # 获取购物车中选中的商品
        cart_items = CartItem.objects.filter(
            user=user,
            book_id__in=book_ids,
            is_selected=True
        ).select_related('book')
        
        if not cart_items.exists():
            return JsonResponse({
                'success': False,
                'message': '购物车中没有选中的商品'
            }, status=400)
        
        # 计算总价
        total_amount = Decimal('0.00')
        order_content = []
        
        for item in cart_items:
            book = item.book
            
            # 检查是否已购买
            existing_ownership = UserBookOwnership.objects.filter(
                user_id=user.user_id,
                book_id=book.book_id
            ).first()
            
            if existing_ownership:
                return JsonResponse({
                    'success': False,
                    'message': f'您已经购买过《{book.title}》了'
                }, status=400)
            
            total_amount += item.price
            order_content.append({
                'book_id': book.book_id,
                'book_title': book.title,
                'price': float(item.price)
            })
        
        # 检查余额是否充足
        if payment_method == '余额':
            if user.balance < total_amount:
                return JsonResponse({
                    'success': False,
                    'message': f'余额不足！当前余额: ¥{user.balance}, 需要: ¥{total_amount}'
                }, status=400)
        
        # 使用事务创建订单
        with transaction.atomic():
            # 生成订单号
            order_number = generate_order_number()
            
            # 创建订单
            order = BookOrder.objects.create(
                customer_name=user.name,
                order_number=order_number,
                book_count=len(order_content),
                order_amount=total_amount,
                payment_method=payment_method,
                order_status='待支付'
            )
            order.set_order_content(order_content)
            order.save()
            
            # 如果是余额支付,直接扣款并完成订单
            if payment_method == '余额':
                # 扣除余额
                user.balance -= total_amount
                user.save(update_fields=['balance'])
                
                # 更新订单状态
                order.order_status = '已支付'
                order.payment_time = timezone.now()
                order.complete_time = timezone.now()
                order.save(update_fields=['order_status', 'payment_time', 'complete_time'])
                
                # 为用户添加书籍拥有权
                for item_data in order_content:
                    book = BookName.objects.get(book_id=item_data['book_id'])
                    purchase_book(
                        user=user,
                        book=book,
                        price=item_data['price'],
                        access_type='purchased',
                        order_id=order.order_id
                    )
                
                # 清空购物车中已购买的商品
                CartItem.objects.filter(
                    user=user,
                    book_id__in=book_ids
                ).delete()
        
        return JsonResponse({
            'success': True,
            'message': '订单创建成功' if payment_method != '余额' else '购买成功！',
            'order_data': {
                'order_id': order.order_id,
                'order_number': order.order_number,
                'order_amount': float(order.order_amount),
                'order_status': order.order_status,
                'book_count': order.book_count
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON数据'
        }, status=400)
    except Exception as e:
        logger.error(f"创建订单失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'message': f'创建订单失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def check_book_access_api(request):
    """
    检查书籍访问权限API
    
    请求参数:
        - book_id: 书籍ID
    
    返回:
        - success: 是否成功
        - access_info: 访问权限信息
    """
    try:
        data = json.loads(request.body)
        book_id = data.get('book_id')
        
        if not book_id:
            return JsonResponse({
                'success': False,
                'message': '缺少book_id参数'
            }, status=400)
        
        # 获取书籍
        try:
            book = BookName.objects.get(book_id=book_id)
        except BookName.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '书籍不存在'
            }, status=404)
        
        # 获取当前用户
        user = get_current_user(request)
        
        # 检查访问权限
        access_info = check_book_access(user, book)
        
        return JsonResponse({
            'success': True,
            'access_info': access_info
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON数据'
        }, status=400)
    except Exception as e:
        logger.error(f"检查访问权限失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'检查失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def check_chapter_access_api(request):
    """
    检查章节访问权限API
    
    请求参数:
        - book_id: 书籍ID
        - chapter_number: 章节号
    
    返回:
        - success: 是否成功
        - access_info: 访问权限信息
    """
    try:
        data = json.loads(request.body)
        book_id = data.get('book_id')
        chapter_number = data.get('chapter_number')
        
        if not book_id or not chapter_number:
            return JsonResponse({
                'success': False,
                'message': '缺少必要参数'
            }, status=400)
        
        # 获取书籍
        try:
            book = BookName.objects.get(book_id=book_id)
        except BookName.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '书籍不存在'
            }, status=404)
        
        # 获取当前用户
        user = get_current_user(request)
        
        # 检查章节访问权限
        access_info = check_chapter_access(user, book, chapter_number)
        
        return JsonResponse({
            'success': True,
            'access_info': access_info
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON数据'
        }, status=400)
    except Exception as e:
        logger.error(f"检查章节访问权限失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'检查失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_cart_summary_api(request):
    """
    获取购物车摘要信息API
    
    返回:
        - success: 是否成功
        - cart_summary: 购物车摘要
    """
    user = get_current_user(request)
    if not user:
        return JsonResponse({
            'success': False,
            'message': '请先登录'
        }, status=401)
    
    try:
        # 计算购物车总价
        cart_info = calculate_cart_total(user, selected_only=False)
        selected_info = calculate_cart_total(user, selected_only=True)
        
        return JsonResponse({
            'success': True,
            'cart_summary': {
                'total_items': cart_info['book_count'],
                'selected_items': selected_info['book_count'],
                'total_price': float(cart_info['total_price']),
                'selected_price': float(selected_info['total_price'])
            }
        })
        
    except Exception as e:
        logger.error(f"获取购物车摘要失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'获取失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def batch_add_to_cart_api(request):
    """
    批量添加到购物车API
    
    请求参数:
        - book_ids: 书籍ID列表
    
    返回:
        - success: 是否成功
        - message: 提示信息
        - added_count: 成功添加的数量
    """
    user = get_current_user(request)
    if not user:
        return JsonResponse({
            'success': False,
            'message': '请先登录'
        }, status=401)
    
    try:
        data = json.loads(request.body)
        book_ids = data.get('book_ids', [])
        
        if not book_ids:
            return JsonResponse({
                'success': False,
                'message': '请选择要添加的书籍'
            }, status=400)
        
        added_count = 0
        skipped_books = []
        
        for book_id in book_ids:
            try:
                book = BookName.objects.get(book_id=book_id)
                
                # 检查是否已在购物车
                existing_item = CartItem.objects.filter(
                    user=user,
                    book=book
                ).first()
                
                if existing_item:
                    skipped_books.append(book.title)
                    continue
                
                # 检查是否已购买
                ownership = UserBookOwnership.objects.filter(
                    user_id=user.user_id,
                    book_id=book.book_id
                ).first()
                
                if ownership:
                    skipped_books.append(f"{book.title}(已购买)")
                    continue
                
                # 添加到购物车
                CartItem.objects.create(
                    user=user,
                    book=book,
                    price=book.price,
                    is_selected=True
                )
                added_count += 1
                
            except BookName.DoesNotExist:
                continue
        
        message = f'成功添加{added_count}本书到购物车'
        if skipped_books:
            message += f'，跳过{len(skipped_books)}本: {", ".join(skipped_books[:3])}'
            if len(skipped_books) > 3:
                message += f'等{len(skipped_books)}本'
        
        return JsonResponse({
            'success': True,
            'message': message,
            'added_count': added_count,
            'skipped_count': len(skipped_books)
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON数据'
        }, status=400)
    except Exception as e:
        logger.error(f"批量添加到购物车失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'添加失败: {str(e)}'
        }, status=500)
