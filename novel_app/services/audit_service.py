"""
操作日志和审计服务类
"""
import logging
import json
from typing import Dict, List, Optional, Any
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q

from .exceptions import ValidationError

logger = logging.getLogger(__name__)


class AuditLogService:
    """操作日志服务类"""
    
    # 操作类型常量
    OPERATION_TYPES = {
        'CREATE': 'create',
        'UPDATE': 'update', 
        'DELETE': 'delete',
        'BATCH_UPDATE': 'batch_update',
        'BATCH_DELETE': 'batch_delete',
        'IMPORT': 'import',
        'EXPORT': 'export',
        'UPLOAD': 'upload',
        'LOGIN': 'login',
        'LOGOUT': 'logout',
    }
    
    def __init__(self):
        self.logger = logger
    
    def log_operation(self, admin_id: int, admin_username: str, operation_type: str, 
                     target_type: str, target_id: Optional[int] = None, 
                     details: Dict = None, ip_address: str = '', 
                     user_agent: str = '') -> bool:
        """
        记录操作日志
        
        Args:
            admin_id: 管理员ID
            admin_username: 管理员用户名
            operation_type: 操作类型
            target_type: 目标类型 (book, user, order等)
            target_id: 目标ID
            details: 操作详情
            ip_address: IP地址
            user_agent: 用户代理
            
        Returns:
            bool: 记录是否成功
        """
        try:
            # 这里暂时使用日志记录，后续会创建数据库模型
            log_data = {
                'admin_id': admin_id,
                'admin_username': admin_username,
                'operation_type': operation_type,
                'target_type': target_type,
                'target_id': target_id,
                'details': details or {},
                'ip_address': ip_address,
                'user_agent': user_agent,
                'timestamp': timezone.now().isoformat(),
            }
            
            # 记录到日志文件
            self.logger.info(f"AUDIT_LOG: {json.dumps(log_data, ensure_ascii=False)}")
            
            # TODO: 后续会保存到数据库
            # AdminOperationLog.objects.create(**log_data)
            
            return True
            
        except Exception as e:
            self.logger.error(f"记录操作日志失败: {str(e)}")
            return False
    
    def log_book_operation(self, admin_id: int, admin_username: str, 
                          operation_type: str, book_id: Optional[int] = None,
                          book_title: str = '', old_data: Dict = None, 
                          new_data: Dict = None, ip_address: str = '', 
                          user_agent: str = '') -> bool:
        """
        记录书籍操作日志
        
        Args:
            admin_id: 管理员ID
            admin_username: 管理员用户名
            operation_type: 操作类型
            book_id: 书籍ID
            book_title: 书籍标题
            old_data: 操作前数据
            new_data: 操作后数据
            ip_address: IP地址
            user_agent: 用户代理
            
        Returns:
            bool: 记录是否成功
        """
        details = {
            'book_title': book_title,
            'old_data': old_data or {},
            'new_data': new_data or {},
        }
        
        return self.log_operation(
            admin_id=admin_id,
            admin_username=admin_username,
            operation_type=operation_type,
            target_type='book',
            target_id=book_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def log_batch_operation(self, admin_id: int, admin_username: str,
                           operation_type: str, target_type: str,
                           target_ids: List[int], operation_result: Dict,
                           ip_address: str = '', user_agent: str = '') -> bool:
        """
        记录批量操作日志
        
        Args:
            admin_id: 管理员ID
            admin_username: 管理员用户名
            operation_type: 操作类型
            target_type: 目标类型
            target_ids: 目标ID列表
            operation_result: 操作结果
            ip_address: IP地址
            user_agent: 用户代理
            
        Returns:
            bool: 记录是否成功
        """
        details = {
            'target_ids': target_ids,
            'target_count': len(target_ids),
            'operation_result': operation_result,
        }
        
        return self.log_operation(
            admin_id=admin_id,
            admin_username=admin_username,
            operation_type=operation_type,
            target_type=target_type,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def log_file_operation(self, admin_id: int, admin_username: str,
                          operation_type: str, file_info: Dict,
                          book_id: Optional[int] = None,
                          ip_address: str = '', user_agent: str = '') -> bool:
        """
        记录文件操作日志
        
        Args:
            admin_id: 管理员ID
            admin_username: 管理员用户名
            operation_type: 操作类型
            file_info: 文件信息
            book_id: 关联书籍ID
            ip_address: IP地址
            user_agent: 用户代理
            
        Returns:
            bool: 记录是否成功
        """
        details = {
            'file_info': file_info,
            'book_id': book_id,
        }
        
        return self.log_operation(
            admin_id=admin_id,
            admin_username=admin_username,
            operation_type=operation_type,
            target_type='file',
            target_id=book_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def get_operation_logs(self, filters: Dict = None, pagination: Dict = None) -> Dict:
        """
        获取操作日志
        
        Args:
            filters: 筛选条件
            pagination: 分页参数
            
        Returns:
            Dict: 日志列表和分页信息
        """
        try:
            # TODO: 后续从数据库查询
            # 现在返回模拟数据
            logs = []
            
            return {
                'logs': logs,
                'total_count': 0,
                'page_count': 0,
                'current_page': 1,
                'has_next': False,
                'has_previous': False,
            }
            
        except Exception as e:
            self.logger.error(f"获取操作日志失败: {str(e)}")
            return {
                'logs': [],
                'total_count': 0,
                'page_count': 0,
                'current_page': 1,
                'has_next': False,
                'has_previous': False,
                'error': str(e)
            }
    
    def get_book_operation_history(self, book_id: int) -> List[Dict]:
        """
        获取书籍操作历史
        
        Args:
            book_id: 书籍ID
            
        Returns:
            List[Dict]: 操作历史列表
        """
        try:
            # TODO: 后续从数据库查询
            # 现在返回模拟数据
            history = []
            
            return history
            
        except Exception as e:
            self.logger.error(f"获取书籍操作历史失败: {str(e)}")
            return []
    
    def get_admin_operation_stats(self, admin_id: int, days: int = 30) -> Dict:
        """
        获取管理员操作统计
        
        Args:
            admin_id: 管理员ID
            days: 统计天数
            
        Returns:
            Dict: 操作统计信息
        """
        try:
            # TODO: 后续从数据库统计
            stats = {
                'total_operations': 0,
                'operation_types': {},
                'daily_operations': {},
                'most_active_day': '',
                'average_daily_operations': 0,
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"获取管理员操作统计失败: {str(e)}")
            return {}
    
    def cleanup_old_logs(self, days: int = 90) -> int:
        """
        清理旧日志
        
        Args:
            days: 保留天数
            
        Returns:
            int: 清理的日志数量
        """
        try:
            # TODO: 后续实现数据库清理
            cleaned_count = 0
            
            self.logger.info(f"清理了 {cleaned_count} 条旧日志")
            return cleaned_count
            
        except Exception as e:
            self.logger.error(f"清理旧日志失败: {str(e)}")
            return 0


# 操作日志装饰器
def log_admin_operation(operation_type: str, target_type: str = 'book'):
    """
    管理员操作日志装饰器
    
    Args:
        operation_type: 操作类型
        target_type: 目标类型
    """
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            # 获取管理员信息
            admin_id = request.session.get('admin_id', 0)
            admin_username = request.session.get('username', '')
            ip_address = request.META.get('REMOTE_ADDR', '')
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # 执行原函数
            result = func(request, *args, **kwargs)
            
            # 记录日志
            try:
                audit_service = AuditLogService()
                
                # 从结果中提取相关信息
                if hasattr(result, 'content'):
                    # JsonResponse
                    import json
                    try:
                        response_data = json.loads(result.content.decode())
                        if response_data.get('success'):
                            audit_service.log_operation(
                                admin_id=admin_id,
                                admin_username=admin_username,
                                operation_type=operation_type,
                                target_type=target_type,
                                details=response_data,
                                ip_address=ip_address,
                                user_agent=user_agent
                            )
                    except:
                        pass
                        
            except Exception as e:
                logger.error(f"记录操作日志失败: {str(e)}")
            
            return result
        return wrapper
    return decorator