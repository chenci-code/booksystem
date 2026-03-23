from django.apps import AppConfig

class NovelAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'novel_app'
    verbose_name = '小说阅读系统'
    
    def ready(self):
        """
        应用启动时的初始化
        
        注意：避免在此方法中直接访问数据库，这会导致RuntimeWarning。
        数据库表的创建和检查通过SQL脚本直接完成（数据库导入脚本/main.py），
        不使用Django迁移系统。如果需要检查数据库状态，请使用管理命令（如 check_database.py）。
        """
        # 应用初始化完成
        pass

