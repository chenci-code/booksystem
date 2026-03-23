#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Django管理命令：将章节购买数据迁移到整本购买模式
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from novel_app.models import BookName, BookUser, UserProfile, UserBookOwnership
from collections import defaultdict


class Command(BaseCommand):
    help = '将章节购买数据迁移到整本购买模式'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只显示将要执行的操作，不实际修改数据'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制执行迁移，即使已存在UserBookOwnership记录'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        self.stdout.write("开始数据迁移：章节购买 -> 整本购买")
        self.stdout.write("=" * 60)
        
        if dry_run:
            self.stdout.write(self.style.WARNING("这是一次试运行，不会修改任何数据"))
        
        try:
            # 1. 分析现有数据
            self.stdout.write("步骤1: 分析现有数据...")
            self.analyze_existing_data()
            
            # 2. 为VIP用户创建免费访问权限
            self.stdout.write("\n步骤2: 为VIP用户创建免费访问权限...")
            vip_count = self.create_vip_access(dry_run, force)
            
            # 3. 迁移章节购买数据到整本购买
            self.stdout.write("\n步骤3: 迁移章节购买数据...")
            migrated_count = self.migrate_chapter_purchases(dry_run, force)
            
            # 4. 数据一致性检查
            self.stdout.write("\n步骤4: 数据一致性检查...")
            self.check_data_consistency()
            
            # 输出结果
            self.stdout.write("\n" + "=" * 60)
            if dry_run:
                self.stdout.write(self.style.SUCCESS("试运行完成！"))
                self.stdout.write(f"将为 {vip_count} 个VIP用户创建免费访问权限")
                self.stdout.write(f"将迁移 {migrated_count} 条购买记录")
            else:
                self.stdout.write(self.style.SUCCESS("数据迁移完成！"))
                self.stdout.write(f"已为 {vip_count} 个VIP用户创建免费访问权限")
                self.stdout.write(f"已迁移 {migrated_count} 条购买记录")
            self.stdout.write("=" * 60)
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"迁移过程中出错: {e}"))
            import traceback
            self.stdout.write(traceback.format_exc())

    def analyze_existing_data(self):
        """分析现有数据"""
        # 统计用户数据
        total_users = UserProfile.objects.count()
        vip_users = UserProfile.objects.filter(vip_level='VIP').count()
        regular_users = total_users - vip_users
        
        # 统计书籍数据
        total_books = BookName.objects.count()
        
        # 统计章节购买数据
        total_chapter_purchases = BookUser.objects.count()
        unique_book_purchases = BookUser.objects.values('purchaser', 'book_title').distinct().count()
        
        # 统计现有整本购买数据
        existing_ownership = UserBookOwnership.objects.count()
        
        self.stdout.write(f"用户统计: 总计 {total_users} 个用户 (VIP: {vip_users}, 普通: {regular_users})")
        self.stdout.write(f"书籍统计: 总计 {total_books} 本书籍")
        self.stdout.write(f"章节购买记录: {total_chapter_purchases} 条 (涉及 {unique_book_purchases} 本书籍)")
        self.stdout.write(f"现有整本购买记录: {existing_ownership} 条")

    def create_vip_access(self, dry_run=False, force=False):
        """为VIP用户创建免费访问权限"""
        vip_users = UserProfile.objects.filter(vip_level='VIP')
        all_books = BookName.objects.all()
        
        created_count = 0
        
        for user in vip_users:
            for book in all_books:
                # 检查是否已存在记录
                existing = UserBookOwnership.objects.filter(
                    user_id=user.user_id,
                    book_id=book.book_id
                ).exists()
                
                if existing and not force:
                    continue
                
                if not dry_run:
                    UserBookOwnership.objects.get_or_create(
                        user_id=user.user_id,
                        book_id=book.book_id,
                        defaults={
                            'book_title': book.title,
                            'purchase_price': 0.00,
                            'access_type': 'vip_free',
                            'purchase_time': user.register_time or timezone.now(),
                        }
                    )
                
                created_count += 1
        
        return created_count

    def migrate_chapter_purchases(self, dry_run=False, force=False):
        """迁移章节购买数据到整本购买"""
        # 按用户和书籍分组章节购买记录
        purchase_groups = defaultdict(list)
        
        for purchase in BookUser.objects.all():
            key = (purchase.purchaser, purchase.book_title)
            purchase_groups[key].append(purchase)
        
        migrated_count = 0
        
        for (purchaser_name, book_title), purchases in purchase_groups.items():
            try:
                # 获取用户和书籍对象
                user = UserProfile.objects.get(name=purchaser_name)
                book = BookName.objects.get(title=book_title)
                
                # 检查是否已存在整本购买记录
                existing = UserBookOwnership.objects.filter(
                    user_id=user.user_id,
                    book_id=book.book_id
                ).exists()
                
                if existing and not force:
                    continue
                
                # 计算总价格和最早购买时间
                total_price = sum(p.chapter_price for p in purchases)
                earliest_purchase = min(p.purchase_time for p in purchases)
                latest_read = max((p.last_read_time for p in purchases if p.last_read_time), default=None)
                max_chapter = max(p.chapter_number for p in purchases)
                
                if not dry_run:
                    UserBookOwnership.objects.get_or_create(
                        user_id=user.user_id,
                        book_id=book.book_id,
                        defaults={
                            'book_title': book.title,
                            'purchase_price': total_price,
                            'access_type': 'purchased',
                            'purchase_time': earliest_purchase,
                            'last_read_time': latest_read,
                            'reading_progress': max_chapter,
                        }
                    )
                
                migrated_count += 1
                
            except (UserProfile.DoesNotExist, BookName.DoesNotExist) as e:
                self.stdout.write(
                    self.style.WARNING(f"跳过记录 {purchaser_name} - {book_title}: {e}")
                )
                continue
        
        return migrated_count

    def check_data_consistency(self):
        """检查数据一致性"""
        issues = []
        
        # 检查1: UserBookOwnership记录是否有对应的用户和书籍
        orphaned_ownership = 0
        for ownership in UserBookOwnership.objects.all():
            try:
                user = UserProfile.objects.get(user_id=ownership.user_id)
                book = BookName.objects.get(book_id=ownership.book_id)
            except (UserProfile.DoesNotExist, BookName.DoesNotExist):
                orphaned_ownership += 1
        
        if orphaned_ownership > 0:
            issues.append(f"发现 {orphaned_ownership} 条孤立的拥有权记录")
        
        # 检查2: VIP用户是否都有免费访问权限
        vip_users = UserProfile.objects.filter(vip_level='VIP')
        total_books = BookName.objects.count()
        
        for user in vip_users:
            vip_access_count = UserBookOwnership.objects.filter(
                user_id=user.user_id,
                access_type='vip_free'
            ).count()
            
            if vip_access_count < total_books:
                issues.append(f"VIP用户 {user.name} 缺少 {total_books - vip_access_count} 本书的免费访问权限")
        
        # 检查3: 重复的拥有权记录
        duplicate_count = UserBookOwnership.objects.values('user_id', 'book_id').annotate(
            count=models.Count('id')
        ).filter(count__gt=1).count()
        
        if duplicate_count > 0:
            issues.append(f"发现 {duplicate_count} 组重复的拥有权记录")
        
        # 输出检查结果
        if issues:
            self.stdout.write(self.style.WARNING("发现以下数据一致性问题:"))
            for issue in issues:
                self.stdout.write(f"  - {issue}")
        else:
            self.stdout.write(self.style.SUCCESS("数据一致性检查通过"))