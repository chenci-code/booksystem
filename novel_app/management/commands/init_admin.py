from django.core.management.base import BaseCommand
from novel_app.models import Admin


class Command(BaseCommand):
    help = '初始化管理员账户'

    def handle(self, *args, **options):
        # 创建默认管理员账户
        if not Admin.objects.filter(username='admin').exists():
            admin = Admin.objects.create(
                username='admin',
                email='admin@example.com',
                status='正常'
            )
            admin.set_password('admin123')
            admin.save()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'成功创建管理员账户: admin / admin123'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING('管理员账户已存在')
            )