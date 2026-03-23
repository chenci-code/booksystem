from .models import UserProfile
from django.db import OperationalError

def user_profile_context(request):
    """上下文处理器：在所有页面中提供用户头像信息"""
    context = {}
    
    if request.session.get('username'):
        try:
            user_profile = UserProfile.objects.get(username=request.session.get('username'))
            context['user_profile'] = user_profile
        except UserProfile.DoesNotExist:
            context['user_profile'] = None
        except OperationalError as e:
            # 处理数据库字段不存在的情况（迁移未运行）
            # 这通常发生在添加新字段但未运行迁移时
            context['user_profile'] = None
    else:
        context['user_profile'] = None
    
    return context
