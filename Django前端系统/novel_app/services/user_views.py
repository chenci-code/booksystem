"""
用户相关视图服务
处理用户认证、个人中心、书架等功能
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone
import logging
import json

from ..models import (
    UserProfile, UserBookOwnership, BookOrder, 
    BookEvaluate, CartItem, BookName
)
from ..auth_utils import get_current_user, login_required, check_user_status

logger = logging.getLogger(__name__)


@login_required
def user_profile_view(request):
    """
    用户个人中心视图
    """
    user = get_current_user(request)
    
    # 获取用户统计信息
    owned_books_count = UserBookOwnership.objects.filter(user_id=user.user_id).count()
    orders_count = BookOrder.objects.filter(customer_name=user.name).count()
    evaluations_count = BookEvaluate.objects.filter(customer_name=user.name).count()
    
    # 获取最近购买的书籍
    recent_purchases = UserBookOwnership.objects.filter(
        user_id=user.user_id
    ).order_by('-purchase_time')[:5]
    
    # 获取最近订单
    recent_orders = BookOrder.objects.filter(
        customer_name=user.name
    ).order_by('-create_time')[:5]
    
    context = {
        'user': user,
        'owned_books_count': owned_books_count,
        'orders_count': orders_count,
        'evaluations_count': evaluations_count,
        'recent_purchases': recent_purchases,
        'recent_orders': recent_orders,
        'is_vip': user.is_vip(),
        'vip_status': user.get_vip_status_display()
    }
    
    return render(request, 'novel_app/user_profile.html', context)


@login_required
def user_bookshelf_view(request):
    """
    用户书架视图
    显示用户拥有的所有书籍
    """
    user = get_current_user(request)
    
    # 获取用户拥有的书籍
    ownerships = UserBookOwnership.objects.filter(
        user_id=user.user_id
    ).select_related('book').order_by('-last_read_time', '-purchase_time')
    
    # 分类统计
    total_books = ownerships.count()
    purchased_books = ownerships.filter(access_type='purchased').count()
    vip_books = ownerships.filter(access_type='vip_free').count()
    
    context = {
        'ownerships': ownerships,
        'total_books': total_books,
        'purchased_books': purchased_books,
        'vip_books': vip_books
    }
    
    return render(request, 'novel_app/user_bookshelf.html', context)


@login_required
def user_orders_view(request):
    """
    用户订单列表视图
    """
    user = get_current_user(request)
    
    # 获取订单状态筛选
    status_filter = request.GET.get('status', '')
    
    # 查询订单
    orders = BookOrder.objects.filter(customer_name=user.name)
    
    if status_filter:
        orders = orders.filter(order_status=status_filter)
    
    orders = orders.order_by('-create_time')
    
    # 统计各状态订单数量
    status_counts = {
        'all': BookOrder.objects.filter(customer_name=user.name).count(),
        '待支付': BookOrder.objects.filter(customer_name=user.name, order_status='待支付').count(),
        '已支付': BookOrder.objects.filter(customer_name=user.name, order_status='已支付').count(),
        '已取消': BookOrder.objects.filter(customer_name=user.name, order_status='已取消').count()
    }
    
    context = {
        'orders': orders,
        'status_filter': status_filter,
        'status_counts': status_counts
    }
    
    return render(request, 'novel_app/user_orders.html', context)


@login_required
def user_evaluations_view(request):
    """
    用户评价列表视图
    """
    user = get_current_user(request)
    
    # 获取用户的所有评价
    evaluations = BookEvaluate.objects.filter(
        customer_name=user.name
    ).order_by('-create_time')
    
    context = {
        'evaluations': evaluations
    }
    
    return render(request, 'novel_app/user_evaluations.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def update_user_profile_api(request):
    """
    更新用户资料API
    """
    user = get_current_user(request)
    if not user:
        return JsonResponse({
            'success': False,
            'message': '请先登录'
        }, status=401)
    
    try:
        data = json.loads(request.body)
        
        # 可更新的字段
        if 'name' in data:
            user.name = data['name']
        
        # 保存更新
        user.save()
        
        return JsonResponse({
            'success': True,
            'message': '资料更新成功'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON数据'
        }, status=400)
    except Exception as e:
        logger.error(f"更新用户资料失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'更新失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def change_password_api(request):
    """
    修改密码API
    """
    user = get_current_user(request)
    if not user:
        return JsonResponse({
            'success': False,
            'message': '请先登录'
        }, status=401)
    
    try:
        data = json.loads(request.body)
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        
        if not old_password or not new_password:
            return JsonResponse({
                'success': False,
                'message': '请提供旧密码和新密码'
            }, status=400)
        
        # 验证旧密码
        if not user.check_password(old_password):
            return JsonResponse({
                'success': False,
                'message': '旧密码错误'
            }, status=400)
        
        # 设置新密码
        user.set_password(new_password)
        user.save()
        
        return JsonResponse({
            'success': True,
            'message': '密码修改成功,请重新登录'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON数据'
        }, status=400)
    except Exception as e:
        logger.error(f"修改密码失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'修改失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def add_to_collection_api(request):
    """
    添加到收藏API
    """
    user = get_current_user(request)
    if not user:
        return JsonResponse({
            'success': False,
            'message': '请先登录'
        }, status=401)
    
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
        
        # 获取收藏列表
        collected_books = user.get_collected_books()
        
        # 检查是否已收藏
        if any(b.get('book_id') == book_id for b in collected_books):
            return JsonResponse({
                'success': False,
                'message': '已经收藏过了'
            })
        
        # 添加到收藏
        collected_books.append({
            'book_id': book.book_id,
            'title': book.title,
            'author': book.author,
            'collect_time': timezone.now().isoformat()
        })
        
        user.set_collected_books(collected_books)
        user.save()
        
        # 更新书籍收藏量
        book.collection_count += 1
        book.save(update_fields=['collection_count'])
        
        return JsonResponse({
            'success': True,
            'message': '收藏成功'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON数据'
        }, status=400)
    except Exception as e:
        logger.error(f"添加收藏失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'收藏失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def remove_from_collection_api(request):
    """
    取消收藏API
    """
    user = get_current_user(request)
    if not user:
        return JsonResponse({
            'success': False,
            'message': '请先登录'
        }, status=401)
    
    try:
        data = json.loads(request.body)
        book_id = data.get('book_id')
        
        if not book_id:
            return JsonResponse({
                'success': False,
                'message': '缺少book_id参数'
            }, status=400)
        
        # 获取收藏列表
        collected_books = user.get_collected_books()
        
        # 移除收藏
        collected_books = [b for b in collected_books if b.get('book_id') != book_id]
        
        user.set_collected_books(collected_books)
        user.save()
        
        # 更新书籍收藏量
        try:
            book = BookName.objects.get(book_id=book_id)
            if book.collection_count > 0:
                book.collection_count -= 1
                book.save(update_fields=['collection_count'])
        except BookName.DoesNotExist:
            pass
        
        return JsonResponse({
            'success': True,
            'message': '取消收藏成功'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON数据'
        }, status=400)
    except Exception as e:
        logger.error(f"取消收藏失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'取消收藏失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_user_stats_api(request):
    """
    获取用户统计信息API
    """
    user = get_current_user(request)
    if not user:
        return JsonResponse({
            'success': False,
            'message': '请先登录'
        }, status=401)
    
    try:
        # 统计信息
        stats = {
            'owned_books': UserBookOwnership.objects.filter(user_id=user.user_id).count(),
            'collected_books': len(user.get_collected_books()),
            'total_orders': BookOrder.objects.filter(customer_name=user.name).count(),
            'paid_orders': BookOrder.objects.filter(customer_name=user.name, order_status='已支付').count(),
            'evaluations': BookEvaluate.objects.filter(customer_name=user.name).count(),
            'cart_items': CartItem.objects.filter(user=user).count(),
            'balance': float(user.balance),
            'is_vip': user.is_vip(),
            'vip_level': user.vip_level
        }
        
        return JsonResponse({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"获取用户统计失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'获取失败: {str(e)}'
        }, status=500)
