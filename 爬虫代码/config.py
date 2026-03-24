#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
七猫小说网爬虫配置文件 - 统一配置
"""

# ============================================================================
# 章节爬虫配置 (高级爬虫)
# ============================================================================
CHAPTER_CRAWLER_CONFIG = {
    # 浏览器设置
    'headless': False,              # 是否无头模式
    'disable_images': True,         # 禁用图片加载以提高速度

    # 请求设置
    'timeout': 30000,               # 请求超时时间（毫秒）
    'max_retries': 3,               # 最大重试次数
    'retry_delay': 2,               # 重试延迟（秒）

    # 延迟设置
    'min_delay': 2,                 # 最小延迟（秒）
    'max_delay': 4,                 # 最大延迟（秒）
    'anti_crawler_delay': 15,       # 检测到反爬虫时的延迟时间（秒）

    # 输出设置
    'output_dir': 'book_contents',  # 章节内容输出目录
    'login_dir': 'login_required',  # 登录提示输出目录
    'data_dir': 'qimao_data',       # 数据输出目录

    # 功能设置
    'detect_login': True,           # 是否检测登录需求
    'save_login_info': True,        # 是否保存登录提示信息
    'auto_retry': True,             # 是否自动重试
    
    # 反爬虫设置
    'user_agent_rotation': True,    # 是否启用User-Agent轮换
    'simulate_user_behavior': True, # 是否模拟用户行为
    'enable_bypass': True,          # 是否启用反爬虫绕过
}

# 爬虫基本设置 (书籍列表爬虫)
CRAWLER_CONFIG = {
    # 请求设置
    'timeout': 20,                  # 请求超时时间（秒）
    'retries': 3,                   # 重试次数
    'delay_min': 5,                 # 最小延迟时间（秒）
    'delay_max': 12,                # 最大延迟时间（秒）
    'anti_crawler_delay': 15,       # 检测到反爬虫时的延迟时间（秒）

    # 爬取设置
    'max_pages_per_category': 2,    # 每个分类最大爬取页数
    'max_books_per_page': 15,       # 每页最大书籍数量
    'target_books_per_category': 30,# 每分类目标书籍数量

    # 输出设置
    'output_dir': 'qimao_data',     # 输出目录
    'save_csv': True,               # 是否保存CSV格式
    'save_json': True,              # 是否保存JSON格式
    'save_individual': False,       # 是否保存单个分类文件

    # 反爬虫设置
    'enable_bypass': True,          # 是否启用反爬虫绕过
    'max_bypass_attempts': 3,       # 最大绕过尝试次数
    'user_agent_rotation': True,    # 是否启用User-Agent轮换
    'simulate_user_behavior': True, # 是否模拟用户行为
}

# 请求头设置 - 使用更真实的浏览器信息
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
    'DNT': '1',
    'Sec-Ch-Ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
}

# 网站设置
SITE_CONFIG = {
    'base_url': 'https://www.qimao.com',
    'main_page': '/shuku/a-a-a-a-a-a-a-click-1/',
}

# 分类设置 - 根据用户提供的准确URL
CATEGORIES = [
    # 频道分类
    {'name': '女生原创', 'url_suffix': '1-a-a-a-a-a-a-click-1/', 'type': 'channel'},
    {'name': '男生原创', 'url_suffix': '0-a-a-a-a-a-a-click-1/', 'type': 'channel'},
    {'name': '出版图书', 'url_suffix': '2-a-a-a-a-a-a-click-1/', 'type': 'channel'},
    
    # 作品分类
    {'name': '现代言情', 'url_suffix': 'a-1-a-a-a-a-a-click-1/', 'type': 'category'},
    {'name': '古代言情', 'url_suffix': 'a-2-a-a-a-a-a-click-1/', 'type': 'category'},
    {'name': '幻想言情', 'url_suffix': 'a-4-a-a-a-a-a-click-1/', 'type': 'category'},
    {'name': '历史', 'url_suffix': 'a-56-a-a-a-a-a-click-1/', 'type': 'category'},
    {'name': '军事', 'url_suffix': 'a-60-a-a-a-a-a-click-1/', 'type': 'category'},
    {'name': '科幻', 'url_suffix': 'a-64-a-a-a-a-a-click-1/', 'type': 'category'},
    {'name': '游戏', 'url_suffix': 'a-75-a-a-a-a-a-click-1/', 'type': 'category'},
    {'name': '游戏竞技', 'url_suffix': 'a-200-a-a-a-a-a-click-1/', 'type': 'category'},
    {'name': '玄幻奇幻', 'url_suffix': 'a-202-a-a-a-a-a-click-1/', 'type': 'category'},
    {'name': '都市', 'url_suffix': 'a-203-a-a-a-a-a-click-1/', 'type': 'category'},
    {'name': '奇闻异事', 'url_suffix': 'a-204-a-a-a-a-a-click-1/', 'type': 'category'},
    {'name': '武侠仙侠', 'url_suffix': 'a-205-a-a-a-a-a-click-1/', 'type': 'category'},
    {'name': '体育', 'url_suffix': 'a-206-a-a-a-a-a-click-1/', 'type': 'category'},
    {'name': 'N次元', 'url_suffix': 'a-207-a-a-a-a-a-click-1/', 'type': 'category'},
    {'name': '文学艺术', 'url_suffix': 'a-240-a-a-a-a-a-click-1/', 'type': 'category'},
    {'name': '人文社科', 'url_suffix': 'a-241-a-a-a-a-a-click-1/', 'type': 'category'},
    {'name': '经管励志', 'url_suffix': 'a-242-a-a-a-a-a-click-1/', 'type': 'category'},
    {'name': '经典文学', 'url_suffix': 'a-243-a-a-a-a-a-click-1/', 'type': 'category'},
    {'name': '出版小说', 'url_suffix': 'a-257-a-a-a-a-a-click-1/', 'type': 'category'},
    {'name': '少儿教育', 'url_suffix': 'a-258-a-a-a-a-a-click-1/', 'type': 'category'},
    {'name': '衍生言情', 'url_suffix': 'a-277-a-a-a-a-a-click-1/', 'type': 'category'},
    {'name': '现代题材', 'url_suffix': 'a-306-a-a-a-a-a-click-1/', 'type': 'category'},
    {'name': '现实主义', 'url_suffix': 'a-307-a-a-a-a-a-click-1/', 'type': 'category'},
]

# 日志设置 - 仅输出到终端
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(levelname)s - %(message)s',
    'encoding': 'utf-8',
}

# 备用User-Agent列表
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/131.0.0.0 Safari/537.36',
]

# 反爬虫检测关键词
ANTI_CRAWLER_INDICATORS = [
    'acw_sc__v2',
    'aliyunwaf',
    'arg1=',
    'setCookie',
    'reload(',
    'document.location.reload',
    'anti-crawler',
    'access denied',
    'forbidden',
    'cloudflare',
    'ddos-guard',
    'incapsula',
    'sucuri',
    'maxcdn',
    'keycdn'
]

# 预热页面列表
WARMUP_PAGES = [
    'https://www.qimao.com/',
    'https://www.qimao.com/shuku/a-a-a-a-a-a-a-click-1/',
    'https://www.qimao.com/shuku/1-a-a-a-a-a-a-click-1/',
]

# 数据字段设置 - 与数据库模型字段匹配
BOOK_FIELDS = [
    'title',            # 书名
    'author',           # 作者名
    'category',         # 类别
    'status',           # 状态
    'word_count',       # 字数
    'description',      # 简介
    'update_time',      # 更新时间
    'book_url',         # 书籍URL
    'cover_url',        # 封面图片URL
    'qimao_book_id',    # 书籍ID（奇猫网）
    'chapter_count',    # 章节数
    'chapter_list_api', # 章节列表API
    'collection_count', # 收藏量
    'rating',           # 评分
]
