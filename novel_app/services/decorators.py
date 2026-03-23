"""
服务层装饰器
"""
import logging
import json
from functools import wraps
from django.utils import timezone

logger = logging.getLogger(__name__)


def log_admin_operation(operation_type, target_type='book'):
    """
    管理员操作日志装饰器
    
    Args:
        operation_type: 操作类型 (create, update, delete, etc.)
        target_type: 目标类型 (book, user, order, etc.)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # 获取管理员信息
            admin_id = request.session.get('admin_id', 0)
            admin_username = request.session.get('username', '')
            ip_address = request.META.get('REMOTE_ADDR', '')
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # 记录开始时间
            start_time = timezone.now()
            
            try:
                # 执行原函数
                result = func(request, *args, **kwargs)
                
                # 记录成功的操作日志
                try:
                    from ..models import AdminOperationLog
                    
                    # 从结果中提取相关信息
                    target_id = None
                    target_title = ''
                    operation_details = {
                        'success': True,
                        'execution_time': (timezone.now() - start_time).total_seconds(),
                        'args': list(args),
                        'kwargs': {k: v for k, v in kwargs.items() if k != 'request'},
                    }
                    
                    # 如果是JsonResponse，尝试解析内容
                    if hasattr(result, 'content'):
                        try:
                            response_data = json.loads(result.content.decode())
                            if isinstance(response_data, dict):
                                operation_details.update(response_data)
                                
                                # 尝试提取目标信息
                                if 'data' in response_data and isinstance(response_data['data'], dict):
                                    data = response_data['data']
                                    if 'book_id' in data:
                                        target_id = data['book_id']
                                    if 'title' in data:
                                        target_title = data['title']
                                    elif 'book_title' in data:
                                        target_title = data['book_title']
                        except:
                            pass
                    
                    # 从URL参数中提取目标ID
                    if not target_id and args:
                        try:
                            # 假设第一个参数可能是ID
                            if isinstance(args[0], int):
                                target_id = args[0]
                        except:
                            pass
                    
                    AdminOperationLog.objects.create(
                        admin_id=admin_id,
                        admin_username=admin_username,
                        operation_type=operation_type,
                        target_type=target_type,
                        target_id=target_id,
                        target_title=target_title,
                        operation_details=operation_details,
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                    
                except Exception as e:
                    logger.error(f"记录操作日志失败: {str(e)}")
                
                return result
                
            except Exception as e:
                # 记录失败的操作日志
                try:
                    from ..models import AdminOperationLog
                    
                    operation_details = {
                        'success': False,
                        'error': str(e),
                        'execution_time': (timezone.now() - start_time).total_seconds(),
                        'args': list(args),
                        'kwargs': {k: v for k, v in kwargs.items() if k != 'request'},
                    }
                    
                    AdminOperationLog.objects.create(
                        admin_id=admin_id,
                        admin_username=admin_username,
                        operation_type=operation_type,
                        target_type=target_type,
                        operation_details=operation_details,
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                    
                except Exception as log_error:
                    logger.error(f"记录失败操作日志失败: {str(log_error)}")
                
                # 重新抛出原异常
                raise e
                
        return wrapper
    return decorator


def require_admin_permission(func):
    """
    管理员权限验证装饰器
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        # 检查是否登录
        if not request.session.get('username'):
            from django.http import JsonResponse
            return JsonResponse({
                'success': False,
                'message': '请先登录',
                'error_code': 'NOT_LOGGED_IN'
            }, status=401)
        
        # 检查是否是管理员
        if not request.session.get('is_admin'):
            from django.http import JsonResponse
            return JsonResponse({
                'success': False,
                'message': '需要管理员权限',
                'error_code': 'PERMISSION_DENIED'
            }, status=403)
        
        return func(request, *args, **kwargs)
    return wrapper


def validate_request_method(allowed_methods):
    """
    请求方法验证装饰器
    
    Args:
        allowed_methods: 允许的HTTP方法列表，如 ['GET', 'POST']
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            if request.method not in allowed_methods:
                from django.http import JsonResponse
                return JsonResponse({
                    'success': False,
                    'message': f'不支持的请求方法: {request.method}',
                    'error_code': 'METHOD_NOT_ALLOWED'
                }, status=405)
            return func(request, *args, **kwargs)
        return wrapper
    return decorator


def validate_json_request(func):
    """
    JSON请求验证装饰器
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                if hasattr(request, 'body') and request.body:
                    request.json = json.loads(request.body.decode('utf-8'))
                else:
                    request.json = {}
            except json.JSONDecodeError as e:
                from django.http import JsonResponse
                return JsonResponse({
                    'success': False,
                    'message': f'JSON格式错误: {str(e)}',
                    'error_code': 'INVALID_JSON'
                }, status=400)
        return func(request, *args, **kwargs)
    return wrapper


def rate_limit(max_requests=60, window_seconds=60):
    """
    简单的速率限制装饰器
    
    Args:
        max_requests: 时间窗口内最大请求数
        window_seconds: 时间窗口大小（秒）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # 这里可以实现基于IP或用户的速率限制
            # 简化实现，实际项目中可以使用Redis等
            return func(request, *args, **kwargs)
        return wrapper
    return decorator