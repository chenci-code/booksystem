#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一的日志配置文件
为所有爬虫提供一致的日志配置
"""

import logging
import os
from datetime import datetime

def setup_logger(name: str, log_file: str = None, level: str = 'INFO') -> logging.Logger:
    """
    设置日志记录器（仅控制台输出）
    
    Args:
        name: 日志记录器名称
        log_file: 日志文件路径（已忽略，不保存到文件）
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        配置好的日志记录器
    """
    # 创建日志记录器
    logger = logging.getLogger(name)
    
    # 避免重复配置
    if logger.handlers:
        return logger
    
    # 设置日志级别
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # 创建日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 只创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

def get_crawler_logger(crawler_name: str, log_dir: str = 'logs') -> logging.Logger:
    """
    获取爬虫专用的日志记录器（仅控制台输出）
    
    Args:
        crawler_name: 爬虫名称
        log_dir: 日志目录（已忽略，不保存到文件）
    
    Returns:
        配置好的日志记录器
    """
    return setup_logger(crawler_name)

# 预定义的日志记录器配置（仅控制台输出）
CRAWLER_LOGGERS = {
    'playwright_crawler': {
        'name': 'playwright_crawler',
        'level': 'INFO'
    },
    'bypass_crawler': {
        'name': 'bypass_crawler',
        'level': 'INFO'
    },
    'book_content_crawler': {
        'name': 'book_content_crawler',
        'level': 'INFO'
    },
    'book_list_crawler': {
        'name': 'book_list_crawler',
        'level': 'INFO'
    },
    'test_book_list_crawler': {
        'name': 'test_book_list_crawler',
        'level': 'INFO'
    },
}

def get_logger(crawler_type: str) -> logging.Logger:
    """
    根据爬虫类型获取预配置的日志记录器（仅控制台输出）
    
    Args:
        crawler_type: 爬虫类型，可选值见 CRAWLER_LOGGERS
    
    Returns:
        配置好的日志记录器
    """
    if crawler_type not in CRAWLER_LOGGERS:
        raise ValueError(f"未知的爬虫类型: {crawler_type}")
    
    config = CRAWLER_LOGGERS[crawler_type]
    return setup_logger(config['name'], level=config['level'])

# 日志级别配置
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

def set_global_log_level(level: str):
    """
    设置全局日志级别
    
    Args:
        level: 日志级别字符串
    """
    if level.upper() not in LOG_LEVELS:
        raise ValueError(f"无效的日志级别: {level}")
    
    log_level = LOG_LEVELS[level.upper()]
    
    # 设置所有现有日志记录器的级别
    for logger_name in logging.Logger.manager.loggerDict:
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)
        
        # 同时设置所有处理器的级别
        for handler in logger.handlers:
            handler.setLevel(log_level)

# 日志配置示例
def example_usage():
    """日志配置使用示例（仅控制台输出）"""
    
    # 方法1: 使用预配置的日志记录器
    logger = get_logger('playwright_crawler')
    logger.info("这是奇猫爬虫的日志信息")
    
    # 方法2: 自定义日志记录器
    custom_logger = setup_logger('custom_crawler', level='DEBUG')
    custom_logger.debug("这是调试信息")
    
    # 方法3: 使用爬虫专用日志记录器
    crawler_logger = get_crawler_logger('my_crawler')
    crawler_logger.warning("这是警告信息")

if __name__ == "__main__":
    # 测试日志配置
    example_usage()


