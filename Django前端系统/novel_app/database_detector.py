#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Django数据库检测服务
检测数据库和表是否存在，如果不存在则调用数据库导入脚本进行初始化
"""

import os
import sys
import subprocess
import logging
from typing import Dict, List, Tuple, Optional
from django.conf import settings
from django.db import connection
from django.core.management import execute_from_command_line

logger = logging.getLogger(__name__)

class DatabaseDetector:
    """数据库检测器"""
    
    def __init__(self):
        self.db_config = settings.DATABASES['default']
        self.import_script_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            '..', 
            '数据库导入脚本'
        )
    
    def check_database_exists(self) -> bool:
        """检查数据库是否存在"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = %s", 
                             [self.db_config['NAME']])
                result = cursor.fetchone()
                return result is not None
        except Exception as e:
            logger.error(f"检查数据库存在性时出错: {e}")
            return False
    
    def check_tables_exist(self) -> Dict[str, bool]:
        """检查所有必需的表是否存在"""
        required_tables = [
            'book-name', 'book-chapter', 'book-user', 'user', 
            'book-order', 'book-shoppingcart', 'book-avaluate', 
            'admins', 'system_config'
        ]
        
        table_status = {}
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                existing_tables = [row[0] for row in cursor.fetchall()]
                
                for table in required_tables:
                    table_status[table] = table in existing_tables
                    
        except Exception as e:
            logger.error(f"检查表存在性时出错: {e}")
            for table in required_tables:
                table_status[table] = False
        
        return table_status
    
    def check_table_structure(self, table_name: str) -> Dict[str, bool]:
        """检查表结构是否完整"""
        required_fields = {
            'book-name': ['book_id', 'title', 'author', 'category', 'status', 'qimao_book_id'],
            'book-chapter': ['chapter_id', 'book_title', 'chapter_number', 'chapter_title', 
                           'content_file_path', 'is_crawled', 'crawl_time'],
            'book-user': ['id', 'book_title', 'chapter_number', 'purchaser'],
            'user': ['user_id', 'name', 'username', 'password', 'balance'],
            'book-order': ['order_id', 'customer_name', 'order_number', 'order_books'],
            'book-shoppingcart': ['cart_id', 'customer_name', 'cart_number', 'cart_content'],
            'book-avaluate': ['evaluate_id', 'customer_name', 'book_title', 'rating'],
            'admins': ['admin_id', 'username', 'password', 'email', 'role'],
            'system_config': ['config_id', 'config_key', 'config_value']
        }
        
        field_status = {}
        
        if table_name not in required_fields:
            return field_status
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"DESCRIBE `{table_name}`")
                existing_fields = [row[0] for row in cursor.fetchall()]
                
                for field in required_fields[table_name]:
                    field_status[field] = field in existing_fields
                    
        except Exception as e:
            logger.error(f"检查表 {table_name} 结构时出错: {e}")
            for field in required_fields[table_name]:
                field_status[field] = False
        
        return field_status
    
    def check_crawler_fields(self) -> bool:
        """检查爬虫相关字段是否存在"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SHOW COLUMNS FROM `book-chapter` LIKE 'content_file_path'")
                content_file_path_exists = cursor.fetchone() is not None
                
                cursor.execute("SHOW COLUMNS FROM `book-chapter` LIKE 'is_crawled'")
                is_crawled_exists = cursor.fetchone() is not None
                
                cursor.execute("SHOW COLUMNS FROM `book-chapter` LIKE 'crawl_time'")
                crawl_time_exists = cursor.fetchone() is not None
                
                return content_file_path_exists and is_crawled_exists and crawl_time_exists
                
        except Exception as e:
            logger.error(f"检查爬虫字段时出错: {e}")
            return False
    
    def run_database_import_script(self) -> bool:
        """运行数据库导入脚本"""
        try:
            # 构建命令
            script_path = os.path.join(self.import_script_dir, 'main.py')
            
            if not os.path.exists(script_path):
                logger.error(f"数据库导入脚本不存在: {script_path}")
                return False
            
            # 构建参数
            cmd = [
                sys.executable, script_path,
                '--init',
                '--host', self.db_config['HOST'],
                '--port', str(self.db_config['PORT']),
                '--user', self.db_config['USER'],
                '--password', self.db_config['PASSWORD'],
                '--database', self.db_config['NAME']
            ]
            
            logger.info(f"执行数据库导入脚本: {' '.join(cmd)}")
            
            # 执行脚本
            result = subprocess.run(
                cmd,
                cwd=self.import_script_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            if result.returncode == 0:
                logger.info("数据库导入脚本执行成功")
                logger.info(f"输出: {result.stdout}")
                return True
            else:
                logger.error(f"数据库导入脚本执行失败: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("数据库导入脚本执行超时")
            return False
        except Exception as e:
            logger.error(f"执行数据库导入脚本时出错: {e}")
            return False
    
    def add_crawler_fields_if_missing(self) -> bool:
        """如果爬虫字段缺失，则添加它们"""
        if self.check_crawler_fields():
            logger.info("爬虫字段已存在")
            return True
        
        try:
            with connection.cursor() as cursor:
                # 添加 content_file_path 字段
                cursor.execute("""
                    ALTER TABLE `book-chapter` 
                    ADD COLUMN `content_file_path` VARCHAR(500) NULL COMMENT '内容文件路径'
                """)
                logger.info("添加 content_file_path 字段")
                
                # 添加 is_crawled 字段
                cursor.execute("""
                    ALTER TABLE `book-chapter` 
                    ADD COLUMN `is_crawled` BOOLEAN DEFAULT FALSE COMMENT '是否已爬取'
                """)
                logger.info("添加 is_crawled 字段")
                
                # 添加 crawl_time 字段
                cursor.execute("""
                    ALTER TABLE `book-chapter` 
                    ADD COLUMN `crawl_time` DATETIME NULL COMMENT '爬取时间'
                """)
                logger.info("添加 crawl_time 字段")
                
                # 添加索引
                cursor.execute("""
                    ALTER TABLE `book-chapter` 
                    ADD INDEX `idx_is_crawled` (`is_crawled`)
                """)
                logger.info("添加 is_crawled 索引")
                
            return True
            
        except Exception as e:
            logger.error(f"添加爬虫字段时出错: {e}")
            return False
    
    def detect_and_initialize(self) -> bool:
        """检测数据库状态并进行必要的初始化"""
        logger.info("开始检测数据库状态...")
        
        # 1. 检查数据库是否存在
        if not self.check_database_exists():
            logger.warning("数据库不存在，开始初始化...")
            if not self.run_database_import_script():
                logger.error("数据库初始化失败")
                return False
        
        # 2. 检查表是否存在
        table_status = self.check_tables_exist()
        missing_tables = [table for table, exists in table_status.items() if not exists]
        
        if missing_tables:
            logger.warning(f"缺失表: {missing_tables}，开始初始化...")
            if not self.run_database_import_script():
                logger.error("表初始化失败")
                return False
        
        # 3. 检查爬虫字段是否存在
        if not self.check_crawler_fields():
            logger.warning("爬虫字段缺失，开始添加...")
            if not self.add_crawler_fields_if_missing():
                logger.error("添加爬虫字段失败")
                return False
        
        # 4. 最终验证
        final_table_status = self.check_tables_exist()
        all_tables_exist = all(final_table_status.values())
        
        if all_tables_exist and self.check_crawler_fields():
            logger.info("数据库检测完成，所有组件正常")
            return True
        else:
            logger.error("数据库检测失败，部分组件缺失")
            return False
    
    def get_database_status(self) -> Dict:
        """获取数据库状态信息"""
        status = {
            'database_exists': self.check_database_exists(),
            'tables_status': self.check_tables_exist(),
            'crawler_fields_exist': self.check_crawler_fields(),
            'all_ready': False
        }
        
        # 检查是否所有组件都就绪
        status['all_ready'] = (
            status['database_exists'] and 
            all(status['tables_status'].values()) and 
            status['crawler_fields_exist']
        )
        
        return status

def ensure_database_ready():
    """确保数据库就绪的便捷函数"""
    detector = DatabaseDetector()
    return detector.detect_and_initialize()
