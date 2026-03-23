"""
自定义异常类
"""


class BookManagementException(Exception):
    """书籍管理异常基类"""
    pass


class BookNotFoundError(BookManagementException):
    """书籍不存在错误"""
    pass


class BatchOperationError(BookManagementException):
    """批量操作错误"""
    pass


class FileUploadError(BookManagementException):
    """文件上传错误"""
    pass


class ValidationError(BookManagementException):
    """数据验证错误"""
    pass


class PermissionDeniedError(BookManagementException):
    """权限不足错误"""
    pass


class DuplicateBookError(BookManagementException):
    """书籍重复错误"""
    pass