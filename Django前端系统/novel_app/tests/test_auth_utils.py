"""
认证和权限工具函数测试
测试 auth_utils.py 中的认证和权限检查功能
"""
from django.test import TestCase, RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from novel_app.models import UserProfile, Admin
from novel_app.auth_utils import (
    get_current_user,
    get_current_admin,
    login_required,
    admin_required,
    get_user_or_redirect,
    check_user_status,
    get_client_ip,
    get_user_agent
)


class GetCurrentUserTestCase(TestCase):
    """测试获取当前登录用户功能"""
    
    def setUp(self):
        """测试前准备数据"""
        self.factory = RequestFactory()
        self.user = UserProfile.objects.create(
            name='测试用户',
            username='test_user',
            password='password123'
        )
    
    def _add_session_to_request(self, request):
        """为请求添加session支持"""
        middleware = SessionMiddleware(lambda x: HttpResponse())
        middleware.process_request(request)
        request.session.save()
        return request
    
    def test_get_current_user_with_session(self):
        """测试从session获取当前用户"""
        request = self.factory.get('/')
        request = self._add_session_to_request(request)
        request.session['username'] = 'test_user'
        
        user = get_current_user(request)
        
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'test_user')
    
    def test_get_current_user_without_session(self):
        """测试未登录时获取用户"""
        request = self.factory.get('/')
        request = self._add_session_to_request(request)
        
        user = get_current_user(request)
        
        self.assertIsNone(user)
    
    def test_get_current_user_invalid_username(self):
        """测试session中用户名不存在"""
        request = self.factory.get('/')
        request = self._add_session_to_request(request)
        request.session['username'] = 'nonexistent_user'
        
        user = get_current_user(request)
        
        self.assertIsNone(user)


class GetCurrentAdminTestCase(TestCase):
    """测试获取当前登录管理员功能"""
    
    def setUp(self):
        """测试前准备数据"""
        self.factory = RequestFactory()
        self.admin = Admin.objects.create(
            username='admin_user',
            password='admin123',
            email='admin@test.com'
        )
    
    def _add_session_to_request(self, request):
        """为请求添加session支持"""
        middleware = SessionMiddleware(lambda x: HttpResponse())
        middleware.process_request(request)
        request.session.save()
        return request
    
    def test_get_current_admin_with_session(self):
        """测试从session获取当前管理员"""
        request = self.factory.get('/')
        request = self._add_session_to_request(request)
        request.session['username'] = 'admin_user'
        request.session['is_admin'] = True
        
        admin = get_current_admin(request)
        
        self.assertIsNotNone(admin)
        self.assertEqual(admin.username, 'admin_user')
    
    def test_get_current_admin_without_admin_flag(self):
        """测试非管理员session"""
        request = self.factory.get('/')
        request = self._add_session_to_request(request)
        request.session['username'] = 'admin_user'
        request.session['is_admin'] = False
        
        admin = get_current_admin(request)
        
        self.assertIsNone(admin)
    
    def test_get_current_admin_without_session(self):
        """测试未登录时获取管理员"""
        request = self.factory.get('/')
        request = self._add_session_to_request(request)
        
        admin = get_current_admin(request)
        
        self.assertIsNone(admin)


class LoginRequiredDecoratorTestCase(TestCase):
    """测试登录验证装饰器"""
    
    def setUp(self):
        """测试前准备数据"""
        self.factory = RequestFactory()
    
    def _add_session_to_request(self, request):
        """为请求添加session支持"""
        middleware = SessionMiddleware(lambda x: HttpResponse())
        middleware.process_request(request)
        request.session.save()
        return request
    
    def test_login_required_with_login(self):
        """测试已登录用户访问受保护视图"""
        @login_required
        def protected_view(request):
            return HttpResponse('Success')
        
        request = self.factory.get('/')
        request = self._add_session_to_request(request)
        request.session['username'] = 'test_user'
        
        response = protected_view(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), 'Success')
    
    def test_login_required_without_login(self):
        """测试未登录用户访问受保护视图"""
        @login_required
        def protected_view(request):
            return HttpResponse('Success')
        
        request = self.factory.get('/')
        request = self._add_session_to_request(request)
        
        response = protected_view(request)
        
        # 应该重定向到登录页
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('/login/'))


class AdminRequiredDecoratorTestCase(TestCase):
    """测试管理员权限装饰器"""
    
    def setUp(self):
        """测试前准备数据"""
        self.factory = RequestFactory()
    
    def _add_session_to_request(self, request):
        """为请求添加session支持"""
        middleware = SessionMiddleware(lambda x: HttpResponse())
        middleware.process_request(request)
        request.session.save()
        return request
    
    def test_admin_required_with_admin(self):
        """测试管理员访问受保护视图"""
        @admin_required
        def admin_view(request):
            return HttpResponse('Admin Success')
        
        request = self.factory.get('/')
        request = self._add_session_to_request(request)
        request.session['username'] = 'admin_user'
        request.session['is_admin'] = True
        
        response = admin_view(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), 'Admin Success')
    
    def test_admin_required_without_admin(self):
        """测试非管理员访问受保护视图"""
        @admin_required
        def admin_view(request):
            return HttpResponse('Admin Success')
        
        request = self.factory.get('/')
        request = self._add_session_to_request(request)
        request.session['username'] = 'normal_user'
        request.session['is_admin'] = False
        
        response = admin_view(request)
        
        # 应该重定向到登录页
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('/login/'))


class CheckUserStatusTestCase(TestCase):
    """测试用户状态检查功能"""
    
    def test_check_normal_user_status(self):
        """测试正常用户状态"""
        user = UserProfile.objects.create(
            name='正常用户',
            username='normal_user',
            password='password123',
            status='正常'
        )
        
        is_valid, message = check_user_status(user)
        
        self.assertTrue(is_valid)
        self.assertEqual(message, '')
    
    def test_check_disabled_user_status(self):
        """测试禁用用户状态"""
        user = UserProfile.objects.create(
            name='禁用用户',
            username='disabled_user',
            password='password123',
            status='禁用'
        )
        
        is_valid, message = check_user_status(user)
        
        self.assertFalse(is_valid)
        self.assertIn('已被禁用', message)


class GetClientIPTestCase(TestCase):
    """测试获取客户端IP地址功能"""
    
    def setUp(self):
        """测试前准备数据"""
        self.factory = RequestFactory()
    
    def test_get_ip_from_x_forwarded_for(self):
        """测试从X-Forwarded-For头获取IP"""
        request = self.factory.get('/', HTTP_X_FORWARDED_FOR='192.168.1.100, 10.0.0.1')
        
        ip = get_client_ip(request)
        
        self.assertEqual(ip, '192.168.1.100')
    
    def test_get_ip_from_remote_addr(self):
        """测试从REMOTE_ADDR获取IP"""
        request = self.factory.get('/', REMOTE_ADDR='192.168.1.200')
        
        ip = get_client_ip(request)
        
        self.assertEqual(ip, '192.168.1.200')
    
    def test_get_ip_default(self):
        """测试默认IP"""
        request = self.factory.get('/')
        
        ip = get_client_ip(request)
        
        # 默认应该返回某个IP地址
        self.assertIsNotNone(ip)


class GetUserAgentTestCase(TestCase):
    """测试获取用户代理字符串功能"""
    
    def setUp(self):
        """测试前准备数据"""
        self.factory = RequestFactory()
    
    def test_get_user_agent(self):
        """测试获取User-Agent"""
        user_agent_string = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        request = self.factory.get('/', HTTP_USER_AGENT=user_agent_string)
        
        user_agent = get_user_agent(request)
        
        self.assertEqual(user_agent, user_agent_string)
    
    def test_get_user_agent_empty(self):
        """测试没有User-Agent时"""
        request = self.factory.get('/')
        
        user_agent = get_user_agent(request)
        
        self.assertEqual(user_agent, '')
