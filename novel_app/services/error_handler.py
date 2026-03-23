"""
统一错误处理机制
"""
import logging
import traceback
from typing import Dict, Any
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from functools import wraps

from .exceptions import (
    BookManagementException, BookNotFoundError, BatchOperationError,
    FileUploadError, ValidationError, PermissionDeniedError, DuplicateBookError
)

logger = logging.getLogger(__name__)


class ErrorHandler:
    """错误处理器"""
    
    # 错误码映射
    ERROR_CODES = {
        BookNotFoundError: 'BOOK_NOT_FOUND',
        BatchOperationError: 'BATCH_OPERATION_ERROR',
        FileUploadError: 'FILE_UPLOAD_ERROR',
        ValidationError: 'VALIDATION_ERROR',
        PermissionDeniedError: 'PERMISSION_DENIED',
        DuplicateBookError: 'DUPLICATE_BOOK',
        BookManagementException: 'BOOK_MANAGEMENT_ERROR',
    }
    
    # HTTP状态码映射
    STATUS_CODES = {
        BookNotFoundError: 404,
        BatchOperationError: 400,
        FileUploadError: 400,
        ValidationError: 400,
        PermissionDeniedError: 403,
        DuplicateBookError: 409,
        BookManagementException: 500,
    }
    
    @classmethod
    def handle_exception(cls, exception: Exception, context: str = '') -> JsonResponse:
        """
        处理异常并返回JSON响应
        
        Args:
            exception: 异常对象
            context: 上下文信息
            
        Returns:
            JsonResponse: 错误响应
        """
        # 记录错误日志
        error_msg = f"{context}: {str(exception)}" if context else str(exception)
        logger.error(f"错误处理: {error_msg}")
        logger.error(f"异常堆栈: {traceback.format_exc()}")
        
        # 获取错误码和状态码
        exception_type = type(exception)
        error_code = cls.ERROR_CODES.get(exception_type, 'UNKNOWN_ERROR')
        status_code = cls.STATUS_CODES.get(exception_type, 500)
        
        # 构建响应数据
        response_data = {
            'success': False,
            'message': str(exception),
            'error_code': error_code,
            'timestamp': cls._get_timestamp(),
        }
        
        # 开发环境下添加调试信息
        if hasattr(settings, 'DEBUG') and settings.DEBUG:
            response_data['debug'] = {
                'exception_type': exception_type.__name__,
                'traceback': traceback.format_exc(),
                'context': context,
            }
        
        return JsonResponse(response_data, status=status_code)
    
    @classmethod
    def handle_validation_errors(cls, errors: Dict) -> JsonResponse:
        """
        处理表单验证错误
        
        Args:
            errors: 验证错误字典
            
        Returns:
            JsonResponse: 错误响应
        """
        response_data = {
            'success': False,
            'message': '数据验证失败',
            'error_code': 'VALIDATION_ERROR',
            'errors': errors,
            'timestamp': cls._get_timestamp(),
        }
        
        return JsonResponse(response_data, status=400)
    
    @classmethod
    def success_response(cls, data: Any = None, message: str = '操作成功') -> JsonResponse:
        """
        成功响应
        
        Args:
            data: 响应数据
            message: 成功消息
            
        Returns:
            JsonResponse: 成功响应
        """
        response_data = {
            'success': True,
            'message': message,
            'timestamp': cls._get_timestamp(),
        }
        
        if data is not None:
            response_data['data'] = data
        
        return JsonResponse(response_data)
    
    @classmethod
    def _get_timestamp(cls) -> str:
        """获取当前时间戳"""
        from django.utils import timezone
        return timezone.now().isoformat()


def handle_api_errors(func):
    """
    API错误处理装饰器
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        try:
            return func(request, *args, **kwargs)
        except (BookManagementException, ValidationError, FileUploadError) as e:
            return ErrorHandler.handle_exception(e, f"API调用: {func.__name__}")
        except Exception as e:
            # 未预期的异常
            logger.error(f"未处理的异常在 {func.__name__}: {str(e)}")
            logger.error(f"异常堆栈: {traceback.format_exc()}")
            return ErrorHandler.handle_exception(
                BookManagementException(f"系统内部错误: {str(e)}"),
                f"API调用: {func.__name__}"
            )
    return wrapper


def require_admin_permission(func):
    """
    管理员权限验证装饰器
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        # 检查是否登录
        if not request.session.get('username'):
            return ErrorHandler.handle_exception(
                PermissionDeniedError("请先登录"),
                "权限验证"
            )
        
        # 检查是否是管理员
        if not request.session.get('is_admin'):
            return ErrorHandler.handle_exception(
                PermissionDeniedError("需要管理员权限"),
                "权限验证"
            )
        
        return func(request, *args, **kwargs)
    return wrapper


def validate_request_method(allowed_methods: list):
    """
    请求方法验证装饰器
    
    Args:
        allowed_methods: 允许的HTTP方法列表
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            if request.method not in allowed_methods:
                return ErrorHandler.handle_exception(
                    ValidationError(f"不支持的请求方法: {request.method}"),
                    "请求方法验证"
                )
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
                import json
                if hasattr(request, 'body') and request.body:
                    request.json = json.loads(request.body.decode('utf-8'))
                else:
                    request.json = {}
            except json.JSONDecodeError as e:
                return ErrorHandler.handle_exception(
                    ValidationError(f"JSON格式错误: {str(e)}"),
                    "JSON验证"
                )
        return func(request, *args, **kwargs)
    return wrapper


# 全局异常处理中间件
class BookManagementExceptionMiddleware:
    """书籍管理异常处理中间件"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        return response
    
    def process_exception(self, request, exception):
        """处理未捕获的异常"""
        # 只处理API请求的异常
        if request.path.startswith('/api/'):
            logger.error(f"未捕获的异常: {str(exception)}")
            logger.error(f"请求路径: {request.path}")
            logger.error(f"异常堆栈: {traceback.format_exc()}")
            
            return ErrorHandler.handle_exception(
                BookManagementException(f"系统内部错误: {str(exception)}"),
                f"中间件异常处理: {request.path}"
            )
        
        # 非API请求返回None，让Django默认处理
        return None