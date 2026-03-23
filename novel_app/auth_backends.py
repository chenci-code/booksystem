"""
自定义认证后端 - 支持明文密码验证
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User


class PlainTextPasswordBackend(ModelBackend):
    """
    自定义认证后端，支持明文密码验证
    """
    
    def authenticate(self, request=None, username=None, password=None, **kwargs):
        """
        使用哈希密码进行认证
        """
        if username is None or password is None:
            return None
        
        try:
            # 获取用户
            user = User.objects.get(username=username)
            
            # 检查密码是否匹配（使用哈希验证）
            if user.check_password(password):
                return user
            else:
                return None
                
        except User.DoesNotExist:
            return None
    
    def get_user(self, user_id):
        """
        根据用户ID获取用户对象
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

