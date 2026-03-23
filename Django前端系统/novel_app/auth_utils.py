"""
认证和权限工具模块
提供统一的用户认证、权限检查等功能
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from .models import UserProfile, Admin
import logging

logger = logging.getLogger(__name__)


def get_current_user(request):
    """
    获取当前登录用户
    
    Returns:
        UserProfile对象或None
    """
    username = request.session.get('username')
    if not username:
        return None
    
    try:
        return UserProfile.objects.get(username=username)
    except UserProfile.DoesNotExist:
        return None


def get_current_admin(request):
    """
    获取当前登录管理员
    
    Returns:
        Admin对象或None
    """
    username = request.session.get('username')
    is_admin = request.session.get('is_admin', False)
    
    if not username or not is_admin:
        return None
    
    try:
        return Admin.objects.get(username=username)
    except Admin.DoesNotExist:
        return None


def login_required(view_func):
    """
    登录验证装饰器
    要求用户必须登录才能访问
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('username'):
            messages.warning(request, '请先登录')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    """
    管理员权限装饰器
    要求用户必须是管理员才能访问
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('is_admin'):
            messages.error(request, '需要管理员权限！请先登录管理员账户。')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def get_user_or_redirect(request, redirect_to='login'):
    """
    获取当前用户，如果未登录则重定向
    
    Args:
        request: HTTP请求对象
        redirect_to: 重定向目标，默认为登录页
        
    Returns:
        UserProfile对象或重定向响应
    """
    user = get_current_user(request)
    if not user:
        messages.warning(request, '请先登录')
        return redirect(redirect_to)
    return user


def check_user_status(user):
    """
    检查用户状态是否正常
    
    Args:
        user: UserProfile对象
        
    Returns:
        (is_valid, message) 元组
    """
    if user.status == '禁用':
        return False, '该账户已被禁用，请联系管理员'
    return True, ''


def get_client_ip(request):
    """
    获取客户端IP地址
    
    Args:
        request: HTTP请求对象
        
    Returns:
        IP地址字符串
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
    return ip


def get_user_agent(request):
    """
    获取用户代理字符串
    
    Args:
        request: HTTP请求对象
        
    Returns:
        User-Agent字符串
    """
    return request.META.get('HTTP_USER_AGENT', '')
