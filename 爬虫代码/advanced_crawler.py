#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级爬虫 - 使用 httpx + BeautifulSoup 爬取小说内容
"""

import asyncio
import json
import time
import random
import os
import sys
import logging
from typing import List, Dict, Optional, Tuple
import re
from urllib.parse import urljoin
import httpx
from bs4 import BeautifulSoup

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from logging_config import get_logger

# 配置日志
logger = get_logger('book_content_crawler')


class ContentExtractor:
    """内容提取器 - 使用多种策略提取章节内容"""
    
    def __init__(self, skip_keywords: List[str] = None):
        """
        初始化内容提取器
        
        Args:
            skip_keywords: 需要跳过的关键词列表
        """
        self.skip_keywords = skip_keywords or [
            '广告', '推荐', '点击', '收藏', '订阅', '投票',
            '上一章', '下一章', '目录', '返回', '首页',
            'copyright', '版权', '声明', '免责', '登录', '注册',
            '书名：', '作者：', '本章字数：', '更新时间：',
            '请收藏', '请订阅', '请投票', '请推荐',
            '七猫中文网', '奇猫', 'qimao', 'www.qimao.com',
            '导航', '菜单', '搜索', '登录', '注册', '帮助'
        ]
        
        # 七猫网站特定的内容选择器
        self.qimao_selectors = [
            '.chapter-content',
            '.content',
            '.article-content',
            '.chapter-text',
            '.read-content',
            '.novel-content',
            'article',
            '.main-content',
            '#content',
            '.text-content'
        ]
        
        # 通用内容选择器
        self.fallback_selectors = [
            '.chapter-body',
            '.chapter-main',
            '.read-main',
            '.book-content',
            '.story-content',
            '.chapter-detail',
            '.content-main',
            '.read-content-main',
            'div[class*="content"]',
            'div[class*="chapter"]',
            'div[class*="read"]',
            'div[class*="text"]',
            'div[class*="article"]'
        ]
    
    async def extract_with_selectors(self, soup: BeautifulSoup, selectors: List[str]) -> Tuple[List[str], str]:
        """
        使用CSS选择器提取内容
        
        Args:
            soup: BeautifulSoup对象
            selectors: CSS选择器列表
            
        Returns:
            Tuple[List[str], str]: (内容行列表, 使用的选择器)
        """
        for selector in selectors:
            try:
                elements = soup.select(selector)
                if elements:
                    logger.debug(f"选择器 {selector} 找到 {len(elements)} 个元素")
                    
                    content_lines = []
                    for i, element in enumerate(elements):
                        try:
                            text_content = element.get_text(separator='\n', strip=True)
                            
                            if text_content and len(text_content) > 50:
                                logger.debug(f"元素 {i} 文本长度: {len(text_content)}")
                                
                                lines = text_content.split('\n')
                                temp_lines = []
                                
                                for line in lines:
                                    line = line.strip()
                                    if line and len(line) > 5:
                                        if not any(skip in line for skip in self.skip_keywords):
                                            temp_lines.append(line)
                                
                                if len(temp_lines) > 3:
                                    content_lines.extend(temp_lines)
                                    logger.debug(f"选择器 {selector} 元素 {i} 提取到 {len(temp_lines)} 行内容")
                                    
                                    if len(content_lines) > 10:
                                        break
                                        
                        except Exception as e:
                            logger.debug(f"处理元素 {i} 失败: {e}")
                            continue
                    
                    if len(content_lines) > 5:
                        logger.info(f"选择器 {selector} 成功提取 {len(content_lines)} 行内容")
                        return content_lines, selector
                        
            except Exception as e:
                logger.debug(f"选择器 {selector} 失败: {e}")
                continue
        
        return [], ""
    
    async def extract_with_fallback(self, soup: BeautifulSoup) -> Tuple[List[str], str]:
        """
        使用p标签作为后备提取方法
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            Tuple[List[str], str]: (内容行列表, 提取方法)
        """
        try:
            logger.debug("尝试使用p标签提取内容")
            p_tags = soup.find_all('p')
            content_lines = []
            
            for p in p_tags:
                text = p.get_text(strip=True)
                if text and len(text) > 10:
                    if not any(skip in text for skip in self.skip_keywords):
                        content_lines.append(text)
            
            if content_lines:
                logger.info(f"通过p标签提取到 {len(content_lines)} 行内容")
                return content_lines, "p_tags"
                
        except Exception as e:
            logger.debug(f"p标签提取失败: {e}")
        
        # 尝试从body提取全文
        try:
            logger.debug("尝试从body提取全文")
            body = soup.find('body')
            if body:
                full_text = body.get_text(separator='\n', strip=True)
                
                if full_text and len(full_text) > 100:
                    lines = full_text.split('\n')
                    content_lines = []
                    
                    for line in lines:
                        line = line.strip()
                        if line and len(line) > 10:
                            if not any(skip in line for skip in self.skip_keywords):
                                content_lines.append(line)
                    
                    if content_lines:
                        logger.info(f"通过body全文提取到 {len(content_lines)} 行内容")
                        return content_lines, "body_text"
                        
        except Exception as e:
            logger.debug(f"body全文提取失败: {e}")
        
        return [], ""
    
    async def extract_with_regex(self, html_content: str) -> Tuple[List[str], str]:
        """
        使用正则表达式提取中文内容
        
        Args:
            html_content: HTML内容字符串
            
        Returns:
            Tuple[List[str], str]: (内容行列表, 提取方法)
        """
        try:
            logger.debug("尝试使用正则表达式提取中文内容")
            
            # 查找包含中文的段落（至少20个中文字符）
            chinese_pattern = r'[\u4e00-\u9fff]{20,}'
            chinese_matches = re.findall(chinese_pattern, html_content)
            
            if chinese_matches:
                content_lines = []
                for match in chinese_matches:
                    if not any(skip in match for skip in self.skip_keywords):
                        content_lines.append(match)
                
                if content_lines:
                    logger.info(f"通过正则表达式提取到 {len(content_lines)} 行内容")
                    return content_lines, "regex_chinese"
                    
        except Exception as e:
            logger.debug(f"正则表达式提取失败: {e}")
        
        return [], ""
    
    def clean_content_lines(self, lines: List[str]) -> List[str]:
        """
        清理内容行，去除重复和无效内容
        
        Args:
            lines: 原始内容行列表
            
        Returns:
            List[str]: 清理后的内容行列表
        """
        if not lines:
            return []
        
        cleaned_lines = []
        seen_lines = set()
        
        for line in lines:
            line = line.strip()
            
            # 跳过空行和过短的行
            if not line or len(line) < 5:
                continue
            
            # 跳过包含过滤关键词的行
            if any(skip in line for skip in self.skip_keywords):
                continue
            
            # 去重
            if line not in seen_lines:
                cleaned_lines.append(line)
                seen_lines.add(line)
        
        logger.debug(f"内容清理完成: 原始 {len(lines)} 行 -> 清理后 {len(cleaned_lines)} 行")
        return cleaned_lines
    
    async def extract_content(self, html_content: str, page_url: str = "") -> Dict:
        """
        主要的内容提取方法，按优先级尝试多种策略
        
        Args:
            html_content: HTML内容
            page_url: 页面URL（用于日志）
            
        Returns:
            Dict: 提取结果，包含content、method、word_count、success字段
        """
        start_time = time.time()
        logger.debug(f"开始提取内容，页面长度: {len(html_content)}")
        
        try:
            soup = BeautifulSoup(html_content, 'lxml')
        except Exception as e:
            logger.error(f"HTML解析失败: {e}")
            return {
                'content': [],
                'method': 'failed',
                'word_count': 0,
                'success': False
            }
        
        # 策略1: 使用七猫网站特定选择器
        content_lines, method = await self.extract_with_selectors(soup, self.qimao_selectors)
        if content_lines:
            cleaned_lines = self.clean_content_lines(content_lines)
            if cleaned_lines:
                word_count = sum(len(line) for line in cleaned_lines)
                extraction_time = time.time() - start_time
                logger.info(f"使用七猫选择器成功提取内容: {len(cleaned_lines)} 行, {word_count} 字, 耗时 {extraction_time:.2f}秒")
                return {
                    'content': cleaned_lines,
                    'method': f'qimao_selector_{method}',
                    'word_count': word_count,
                    'success': True
                }
        
        # 策略2: 使用通用选择器
        content_lines, method = await self.extract_with_selectors(soup, self.fallback_selectors)
        if content_lines:
            cleaned_lines = self.clean_content_lines(content_lines)
            if cleaned_lines:
                word_count = sum(len(line) for line in cleaned_lines)
                extraction_time = time.time() - start_time
                logger.info(f"使用通用选择器成功提取内容: {len(cleaned_lines)} 行, {word_count} 字, 耗时 {extraction_time:.2f}秒")
                return {
                    'content': cleaned_lines,
                    'method': f'fallback_selector_{method}',
                    'word_count': word_count,
                    'success': True
                }
        
        # 策略3: 使用后备方法（p标签和body）
        content_lines, method = await self.extract_with_fallback(soup)
        if content_lines:
            cleaned_lines = self.clean_content_lines(content_lines)
            if cleaned_lines:
                word_count = sum(len(line) for line in cleaned_lines)
                extraction_time = time.time() - start_time
                logger.info(f"使用后备方法成功提取内容: {len(cleaned_lines)} 行, {word_count} 字, 耗时 {extraction_time:.2f}秒")
                return {
                    'content': cleaned_lines,
                    'method': f'fallback_{method}',
                    'word_count': word_count,
                    'success': True
                }
        
        # 策略4: 使用正则表达式
        content_lines, method = await self.extract_with_regex(html_content)
        if content_lines:
            cleaned_lines = self.clean_content_lines(content_lines)
            if cleaned_lines:
                word_count = sum(len(line) for line in cleaned_lines)
                extraction_time = time.time() - start_time
                logger.info(f"使用正则表达式成功提取内容: {len(cleaned_lines)} 行, {word_count} 字, 耗时 {extraction_time:.2f}秒")
                return {
                    'content': cleaned_lines,
                    'method': f'regex_{method}',
                    'word_count': word_count,
                    'success': True
                }
        
        # 所有策略都失败
        extraction_time = time.time() - start_time
        logger.warning(f"所有内容提取策略都失败，页面URL: {page_url}, 耗时 {extraction_time:.2f}秒")
        return {
            'content': [],
            'method': 'all_failed',
            'word_count': 0,
            'success': False
        }


class RetryManager:
    """重试管理器 - 处理网络请求的重试逻辑"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        """
        初始化重试管理器
        
        Args:
            max_retries: 最大重试次数
            base_delay: 基础延迟时间（秒）
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    def calculate_delay(self, attempt: int) -> float:
        """
        计算重试延迟时间（指数退避）
        
        Args:
            attempt: 当前尝试次数（从0开始）
            
        Returns:
            float: 延迟时间（秒）
        """
        # 指数退避：base_delay * (2 ^ attempt) + 随机抖动
        delay = self.base_delay * (2 ** attempt)
        # 添加随机抖动，避免雷群效应
        jitter = random.uniform(0, delay * 0.1)
        total_delay = delay + jitter
        
        # 限制最大延迟时间为30秒
        return min(total_delay, 30.0)
    
    async def execute_with_retry(self, func, *args, **kwargs):
        """
        执行函数并在失败时重试
        
        Args:
            func: 要执行的异步函数
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            函数执行结果
            
        Raises:
            最后一次尝试的异常
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(f"执行函数 {func.__name__}，尝试 {attempt + 1}/{self.max_retries + 1}")
                result = await func(*args, **kwargs)
                
                if attempt > 0:
                    logger.info(f"函数 {func.__name__} 在第 {attempt + 1} 次尝试后成功")
                
                return result
                
            except httpx.TimeoutException as e:
                last_exception = e
                logger.warning(f"函数 {func.__name__} 超时，尝试 {attempt + 1}/{self.max_retries + 1}: {e}")
                
                if attempt < self.max_retries:
                    delay = self.calculate_delay(attempt)
                    logger.info(f"等待 {delay:.2f} 秒后重试...")
                    await asyncio.sleep(delay)
                
            except httpx.RequestError as e:
                last_exception = e
                logger.warning(f"函数 {func.__name__} 请求错误，尝试 {attempt + 1}/{self.max_retries + 1}: {e}")
                
                if attempt < self.max_retries:
                    delay = self.calculate_delay(attempt)
                    logger.info(f"等待 {delay:.2f} 秒后重试...")
                    await asyncio.sleep(delay)
                
            except httpx.HTTPStatusError as e:
                last_exception = e
                # 对于某些HTTP状态码，不进行重试
                if e.response.status_code in [404, 403, 401]:
                    logger.error(f"函数 {func.__name__} 遇到不可重试的HTTP错误: {e.response.status_code}")
                    raise e
                
                logger.warning(f"函数 {func.__name__} HTTP错误，尝试 {attempt + 1}/{self.max_retries + 1}: {e}")
                
                if attempt < self.max_retries:
                    delay = self.calculate_delay(attempt)
                    logger.info(f"等待 {delay:.2f} 秒后重试...")
                    await asyncio.sleep(delay)
                
            except Exception as e:
                last_exception = e
                logger.error(f"函数 {func.__name__} 未知错误，尝试 {attempt + 1}/{self.max_retries + 1}: {e}")
                
                if attempt < self.max_retries:
                    delay = self.calculate_delay(attempt)
                    logger.info(f"等待 {delay:.2f} 秒后重试...")
                    await asyncio.sleep(delay)
        
        # 所有重试都失败
        logger.error(f"函数 {func.__name__} 在 {self.max_retries + 1} 次尝试后仍然失败")
        raise last_exception


class AdvancedCrawler:
    """高级爬虫类 - 使用现代异步模式和多策略内容提取"""
    
    def __init__(self):
        """初始化爬虫"""
        # 导入配置
        try:
            from config import CHAPTER_CRAWLER_CONFIG, HEADERS, SITE_CONFIG
            self.config = CHAPTER_CRAWLER_CONFIG
            self.headers = HEADERS.copy()
            self.base_url = SITE_CONFIG['base_url']
        except ImportError:
            logger.warning("无法导入配置文件，使用默认配置")
            self.config = {
                'timeout': 30000,
                'max_retries': 3,
                'retry_delay': 2,
                'min_delay': 2,
                'max_delay': 4,
                'output_dir': 'book_contents',
                'detect_login': True,
                'save_login_info': True
            }
            self.headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'DNT': '1'
            }
            self.base_url = "https://www.qimao.com"
        
        # 初始化组件
        self.content_extractor = ContentExtractor()
        self.retry_manager = RetryManager(
            max_retries=self.config.get('max_retries', 3),
            base_delay=self.config.get('retry_delay', 2)
        )
        
        # HTTP客户端
        self.client = None
        
        # 创建输出目录
        self.output_dir = self.config.get('output_dir', 'book_contents')
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        logger.info("AdvancedCrawler 初始化完成")
    
    async def init_client(self) -> None:
        """初始化 httpx 客户端"""
        if self.client is None:
            timeout_ms = self.config.get('timeout', 30000)
            timeout_seconds = timeout_ms / 1000.0
            
            # 随机选择User-Agent（如果启用了轮换）
            if self.config.get('user_agent_rotation', True):
                try:
                    from config import USER_AGENTS
                    if USER_AGENTS:
                        selected_ua = random.choice(USER_AGENTS)
                        self.headers['User-Agent'] = selected_ua
                        logger.debug(f"使用随机User-Agent: {selected_ua}")
                except ImportError:
                    logger.debug("无法导入USER_AGENTS，使用默认User-Agent")
            
            # 添加更多真实的浏览器头部
            enhanced_headers = self.headers.copy()
            enhanced_headers.update({
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
                'Sec-Ch-Ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"'
            })
            
            self.client = httpx.AsyncClient(
                headers=enhanced_headers,
                timeout=timeout_seconds,
                follow_redirects=True,
                verify=True,
                limits=httpx.Limits(
                    max_keepalive_connections=5, 
                    max_connections=10,
                    keepalive_expiry=30.0
                )
            )
            logger.info(f"httpx 客户端初始化完成，超时设置: {timeout_seconds}秒")
            logger.debug(f"使用的User-Agent: {enhanced_headers.get('User-Agent', 'Unknown')}")
    
    async def close_client(self) -> None:
        """关闭 httpx 客户端"""
        if self.client:
            try:
                await self.client.aclose()
                self.client = None
                logger.info("httpx 客户端已关闭")
            except Exception as e:
                logger.warning(f"关闭客户端时出错: {e}")
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.init_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close_client()
    
    async def _make_request(self, url: str, **kwargs) -> httpx.Response:
        """
        发起HTTP请求的内部方法，集成重试机制和用户行为模拟
        
        Args:
            url: 请求URL
            **kwargs: 其他请求参数
            
        Returns:
            httpx.Response: 响应对象
        """
        await self.init_client()
        
        # 模拟用户行为 - 添加随机延迟
        if self.config.get('simulate_user_behavior', True):
            min_delay = self.config.get('min_delay', 2)
            max_delay = self.config.get('max_delay', 4)
            delay = random.uniform(min_delay, max_delay)
            logger.debug(f"模拟用户行为，延迟 {delay:.2f} 秒")
            await asyncio.sleep(delay)
        
        async def _request():
            response = await self.client.get(url, **kwargs)
            
            # 检查反爬虫指标
            if self._detect_anti_crawler(response):
                logger.warning(f"检测到反爬虫措施: {url}")
                anti_crawler_delay = self.config.get('anti_crawler_delay', 15)
                logger.info(f"等待 {anti_crawler_delay} 秒以避免反爬虫检测...")
                await asyncio.sleep(anti_crawler_delay)
            
            response.raise_for_status()
            return response
        
        return await self.retry_manager.execute_with_retry(_request)
    
    def _detect_anti_crawler(self, response: httpx.Response) -> bool:
        """
        检测响应中是否包含反爬虫指标
        
        Args:
            response: HTTP响应对象
            
        Returns:
            bool: 是否检测到反爬虫措施
        """
        try:
            from config import ANTI_CRAWLER_INDICATORS
            
            # 检查响应内容
            content = response.text.lower()
            for indicator in ANTI_CRAWLER_INDICATORS:
                if indicator.lower() in content:
                    logger.debug(f"检测到反爬虫指标: {indicator}")
                    return True
            
            # 检查响应头
            headers = str(response.headers).lower()
            for indicator in ANTI_CRAWLER_INDICATORS:
                if indicator.lower() in headers:
                    logger.debug(f"在响应头中检测到反爬虫指标: {indicator}")
                    return True
                    
        except ImportError:
            logger.debug("无法导入反爬虫指标配置")
        except Exception as e:
            logger.debug(f"反爬虫检测出错: {e}")
        
        return False
    
    async def parse_chapter_content(self, html_content: str, page_url: str = "") -> List[str]:
        """
        解析章节内容 - 使用新的ContentExtractor
        
        Args:
            html_content: HTML内容
            page_url: 页面URL
            
        Returns:
            List[str]: 提取的内容行列表
        """
        logger.debug(f"开始解析章节内容，页面长度: {len(html_content)}, URL: {page_url}")
        
        # 使用ContentExtractor提取内容
        result = await self.content_extractor.extract_content(html_content, page_url)
        
        if result['success']:
            logger.info(f"内容提取成功: 方法={result['method']}, 行数={len(result['content'])}, 字数={result['word_count']}")
            
            # 添加内容质量评估
            if result['word_count'] < 100:
                logger.warning(f"内容字数较少 ({result['word_count']} 字)，可能存在问题")
            elif result['word_count'] > 10000:
                logger.info(f"内容字数较多 ({result['word_count']} 字)，章节内容丰富")
            
            return result['content']
        else:
            logger.warning(f"内容提取失败: 方法={result['method']}, URL: {page_url}")
            return []
    
    async def get_chapter_list(self, book_id: str) -> List[Dict]:
        """
        获取章节列表 - 使用新的重试机制
        
        Args:
            book_id: 书籍ID
            
        Returns:
            List[Dict]: 章节列表
        """
        logger.info(f"尝试获取书籍 {book_id} 的章节列表")

        try:
            # 访问书籍详情页
            detail_url = f"{self.base_url}/shuku/{book_id}/"
            response = await self._make_request(detail_url)
            
            html_content = response.text
            
            # 解析章节列表
            chapters = await self.parse_chapter_list_from_page(html_content)
            
            if chapters:
                logger.info(f"成功获取 {len(chapters)} 个章节")
                
                # 如果只获取到1个章节，尝试使用API获取完整章节列表
                if len(chapters) == 1:
                    logger.warning("只获取到1个章节，尝试使用API获取完整章节列表...")
                    api_chapters = await self.get_chapters_from_api(book_id)
                    if api_chapters and len(api_chapters) > 1:
                        logger.info(f"API获取到 {len(api_chapters)} 个章节，使用API数据")
                        return api_chapters
                    else:
                        logger.warning("API也无法获取到更多章节，尝试生成章节列表...")
                        # 尝试生成从第1章开始的章节列表
                        generated_chapters = await self.generate_chapter_list(book_id, chapters[0])
                        if generated_chapters and len(generated_chapters) > 1:
                            logger.info(f"生成章节列表成功，共 {len(generated_chapters)} 个章节")
                            return generated_chapters
                
                return chapters
            else:
                logger.warning("未能获取到章节列表，尝试其他方法...")
                # 尝试通过页面文本查找章节
                try:
                    soup = BeautifulSoup(html_content, 'lxml')
                    page_text = soup.get_text()
                    # 查找包含"第X章"的文本
                    chapter_pattern = r'第(\d+)章[^\n]*'
                    matches = re.findall(chapter_pattern, page_text)
                    if matches:
                        logger.info(f"从页面文本中找到 {len(matches)} 个章节编号")
                        chapters = []
                        seen_ids = set()
                        for chapter_num in matches[:100]:  # 限制最多100章
                            if chapter_num not in seen_ids:
                                chapters.append({
                                    'id': str(chapter_num),
                                    'title': f'第{chapter_num}章',
                                    'url': f"{self.base_url}/shuku/{book_id}-{chapter_num}/"
                                })
                                seen_ids.add(chapter_num)
                        if chapters:
                            logger.info(f"从页面文本提取到 {len(chapters)} 个章节")
                            return chapters
                except Exception as e:
                    logger.debug(f"从页面文本查找章节失败: {e}")
                
                return []
                
        except Exception as e:
            logger.error(f"获取章节列表失败: {e}")
            return []
    
    async def get_chapters_from_api(self, book_id: str) -> List[Dict]:
        """尝试通过API获取章节列表"""
        try:
            logger.info(f"尝试通过API获取书籍 {book_id} 的章节列表")

            # 确保客户端已初始化
            await self.init_client()

            # 尝试多个可能的API端点
            api_urls = [
                f"https://www.qimao.com/api/book/chapter-list?book_id={book_id}",
                f"https://www.qimao.com/api/chapter/list?book_id={book_id}",
                f"https://www.qimao.com/api/book/{book_id}/chapters",
                f"https://www.qimao.com/shuku/{book_id}/chapters.json"
            ]

            for api_url in api_urls:
                try:
                    logger.info(f"尝试API: {api_url}")
                    response = await self.client.get(api_url, timeout=10.0)
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            logger.info(f"API响应成功: {api_url}")
                            logger.info(f"API响应数据: {data}")  # 添加调试信息
                        except:
                            logger.warning(f"API响应不是JSON格式: {api_url}")
                            continue
                        
                        # 解析API响应
                        chapters = []
                        
                        # 尝试多种数据结构
                        chapter_list = None
                        if 'data' in data and 'chapters' in data['data']:
                            # 七猫API的实际格式：data.chapters
                            chapter_list = data['data']['chapters']
                            logger.info(f"使用data.chapters格式，找到 {len(chapter_list)} 个章节")
                        elif 'data' in data and 'list' in data['data']:
                            chapter_list = data['data']['list']
                        elif 'data' in data and isinstance(data['data'], list):
                            chapter_list = data['data']
                        elif isinstance(data, list):
                            chapter_list = data
                        elif 'list' in data:
                            chapter_list = data['list']
                        
                        if chapter_list:
                            logger.info(f"找到章节列表，共 {len(chapter_list)} 个章节")
                            for i, chapter in enumerate(chapter_list):
                                chapter_id = str(chapter.get('id', i + 1))
                                chapter_title = chapter.get('title', f'第{i+1}章')
                                
                                # 如果API返回了URL，直接使用；否则构造URL
                                if 'url' in chapter and chapter['url']:
                                    chapter_url = chapter['url']
                                    if not chapter_url.startswith('http'):
                                        chapter_url = f"{self.base_url}{chapter_url}"
                                else:
                                    # 只有在没有URL时才构造URL，使用真实的章节ID
                                    chapter_url = f"{self.base_url}/shuku/{book_id}-{chapter_id}/"
                                
                                chapters.append({
                                    'id': chapter_id,
                                    'title': chapter_title,
                                    'url': chapter_url
                                })
                        else:
                            logger.warning(f"API响应中未找到章节列表，数据结构: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                            # 添加调试信息
                            if isinstance(data, dict) and 'data' in data:
                                logger.info(f"data字段内容结构: {list(data['data'].keys()) if isinstance(data['data'], dict) else type(data['data'])}")
                        
                        if chapters:
                            logger.info(f"API获取到 {len(chapters)} 个章节")
                            return chapters
                            
                except httpx.TimeoutException:
                    logger.debug(f"API请求超时: {api_url}")
                    continue
                except Exception as e:
                    logger.debug(f"API请求失败: {api_url}, 错误: {e}")
                    continue
            
            logger.warning("所有API端点都无法获取章节列表")
            return []
            
        except Exception as e:
            logger.error(f"API获取章节列表失败: {e}")
            return []
    
    async def generate_chapter_list(self, book_id: str, last_chapter: Dict) -> List[Dict]:
        """生成从第1章开始的章节列表"""
        try:
            logger.info(f"开始生成章节列表，已知最后一章: {last_chapter['title']}")
            
            # 从最后一章标题中提取章节编号
            last_chapter_number = None
            title_match = re.search(r'第(\d+)章', last_chapter['title'])
            if title_match:
                last_chapter_number = int(title_match.group(1))
                logger.info(f"检测到最后一章编号: {last_chapter_number}")
            else:
                logger.warning("无法从最后一章标题中提取章节编号")
                return []
            
            # 生成从第1章到最后一章的章节列表
            chapters = []
            for chapter_num in range(1, last_chapter_number + 1):
                chapter_url = f"{self.base_url}/shuku/{book_id}-{chapter_num}/"
                chapters.append({
                    'id': str(chapter_num),
                    'title': f'第{chapter_num}章',
                    'url': chapter_url
                })
            
            logger.info(f"生成章节列表完成，从第1章到第{last_chapter_number}章，共 {len(chapters)} 个章节")
            return chapters
            
        except Exception as e:
            logger.error(f"生成章节列表失败: {e}")
            return []
    
    async def parse_chapter_list_from_page(self, html_content: str) -> List[Dict]:
        """从页面解析章节列表"""
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            
            # 尝试多种选择器来查找章节链接（按优先级排序）
            chapter_selectors = [
                # 七猫中文网特定的章节选择器 - 更精确
                'ul[class*="catalog"] a[href*="/shuku/"][href*="-"]',
                'div[class*="catalog"] a[href*="/shuku/"][href*="-"]',
                '.chapter-list a[href*="/shuku/"][href*="-"]',
                '.catalog-list a[href*="/shuku/"][href*="-"]',
                '.qm-chapter-list a[href*="/shuku/"][href*="-"]',
                # 目录区域内的链接
                '[class*="chapter"] a[href*="/shuku/"][href*="-"]',
                '[class*="catalog"] li a[href*="/shuku/"][href*="-"]',
                # 通用章节链接
                '.chapter-item a[href*="/shuku/"]',
                'ul li a[href*="/shuku/"][href*="-"]',
                '.list-group a[href*="/shuku/"][href*="-"]',
                # 更具体的选择器
                'div[class*="chapter"] a[href*="/shuku/"]',
                'div[class*="catalog"] a[href*="/shuku/"]',
                'div[class*="list"] a[href*="/shuku/"][href*="-"]',
                # 添加更多可能的选择器
                'a[href*="/shuku/"][href*="-"]',
                'li a[href*="/shuku/"][href*="-"]',
                'div a[href*="/shuku/"][href*="-"]',
            ]
            
            chapters = []
            
            for selector in chapter_selectors:
                try:
                    elements = soup.select(selector)
                    if elements:
                        logger.info(f"使用选择器 {selector} 找到 {len(elements)} 个章节链接")
                        
                        for element in elements:
                            try:
                                href = element.get('href', '')
                                title = element.get_text(strip=True)
                                
                                # 添加详细的调试信息
                                logger.debug(f"处理链接: href={href}, title={title}")
                                
                                if not href or not title:
                                    continue

                                title_clean = title.strip()
                                
                                # 过滤掉空标题
                                if not title_clean or len(title_clean) == 0:
                                    continue

                                # 处理相对URL，转换为完整URL
                                if href.startswith('/'):
                                    full_url = f"{self.base_url}{href}"
                                elif not href.startswith('http'):
                                    full_url = f"{self.base_url}/{href}"
                                else:
                                    full_url = href

                                # 过滤掉分类、导航等非章节链接
                                skip_keywords = ['分类', '排序', '筛选', '搜索', '首页', '返回', '更多作品', 
                                               '作者其他作品', '正序', '倒序', '作品介绍', '作品目录', 'click', 'a-a-a']
                                if any(keyword in title_clean.lower() or keyword in full_url.lower() for keyword in skip_keywords):
                                    continue

                                # 验证是否是章节链接（包含书籍ID和章节ID）
                                # 从URL中提取章节ID
                                match = re.search(r'/shuku/\d+-(\d+)/?', full_url)
                                if match:
                                    chapter_id = match.group(1)
                                    
                                    # 保留原始的章节ID，不管它有多长
                                    # 七猫网站使用长数字作为真实的章节ID
                                    logger.debug(f"提取到章节ID: {chapter_id} 来自URL: {full_url}")
                                    
                                    chapters.append({
                                        'id': chapter_id,
                                        'title': title_clean,
                                        'url': full_url  # 使用完整的URL
                                    })
                                # 也接受包含"第"和"章"的标题，即使URL格式不完全匹配
                                elif '第' in title_clean and '章' in title_clean:
                                    # 尝试从标题中提取章节编号
                                    chapter_num_match = re.search(r'第(\d+)章', title_clean)
                                    if chapter_num_match:
                                        chapter_id = chapter_num_match.group(1)
                                        chapters.append({
                                            'id': chapter_id,
                                            'title': title_clean,
                                            'url': full_url
                                        })
                                    if chapter_num_match:
                                        chapter_id = chapter_num_match.group(1)
                                        chapters.append({
                                            'id': chapter_id,
                                            'title': title_clean,
                                            'url': original_href  # 使用完全未修改的原始URL
                                        })
                            except Exception as e:
                                logger.debug(f"解析章节元素失败: {e}")
                                continue
                        
                        # 不要过早跳出，继续尝试其他选择器以获取更多章节
                        if len(chapters) >= 10:  # 如果已经找到足够多的章节，可以考虑跳出
                            logger.info(f"已找到 {len(chapters)} 个章节，继续尝试其他选择器...")
                            
                except Exception as e:
                    logger.debug(f"选择器 {selector} 失败: {e}")
                    continue
            
            # 去重并保持DOM顺序
            unique_chapters = []
            seen_ids = set()
            logger.info(f"开始去重处理，原始章节数: {len(chapters)}")
            
            for i, chapter in enumerate(chapters):
                chapter_id = chapter['id']
                if chapter_id not in seen_ids:
                    unique_chapters.append(chapter)
                    seen_ids.add(chapter_id)
                    logger.debug(f"添加章节 {i+1}: ID={chapter_id}, 标题={chapter['title']}")
                else:
                    logger.debug(f"跳过重复章节: ID={chapter_id}, 标题={chapter['title']}")
            
            logger.info(f"去重完成，唯一章节数: {len(unique_chapters)}")
            
            # 添加调试信息
            if unique_chapters:
                logger.info(f"DOM原始顺序章节：前5章ID为 {[ch['id'] for ch in unique_chapters[:5]]}")
                logger.info(f"DOM原始顺序章节：后5章ID为 {[ch['id'] for ch in unique_chapters[-5:]]}")
                
                # 验证DOM顺序是否正确（应该是正序）
                first_chapter_id = unique_chapters[0]['id']
                last_chapter_id = unique_chapters[-1]['id']
                logger.info(f"DOM原始顺序：从章节{first_chapter_id}到章节{last_chapter_id}")
            
            # 强制按章节编号进行正序排序，确保从第一章开始爬取
            try:
                # 优先从标题中提取章节编号进行排序，这样更准确
                def get_sort_key(chapter):
                    # 优先从标题中提取章节编号
                    title = chapter.get('title', '')
                    title_match = re.search(r'第(\d+)章', title)
                    if title_match:
                        return int(title_match.group(1))
                    
                    # 如果标题中没有章节编号，尝试使用ID
                    chapter_id = chapter['id']
                    try:
                        # 如果ID是合理的数字，直接使用
                        if len(chapter_id) <= 10:
                            return int(chapter_id)
                        else:
                            # 如果ID太长，使用ID的前几位
                            return int(chapter_id[:10])
                    except (ValueError, TypeError):
                        return 999999  # 无法解析的章节放在最后
                
                unique_chapters.sort(key=get_sort_key)
                logger.info(f"强制正序排序完成，共 {len(unique_chapters)} 个章节")
                
                # 验证排序结果
                if unique_chapters:
                    sorted_first_id = unique_chapters[0]['id']
                    sorted_first_title = unique_chapters[0]['title']
                    sorted_last_id = unique_chapters[-1]['id']
                    sorted_last_title = unique_chapters[-1]['title']
                    logger.info(f"排序后顺序：从 {sorted_first_title}(ID:{sorted_first_id}) 到 {sorted_last_title}(ID:{sorted_last_id})")
                    
                    # 显示前10章和后10章的标题和ID
                    if len(unique_chapters) >= 10:
                        logger.info(f"前10章: {[(ch['title'], ch['id']) for ch in unique_chapters[:10]]}")
                        logger.info(f"后10章: {[(ch['title'], ch['id']) for ch in unique_chapters[-10:]]}")
                    else:
                        logger.info(f"所有章节: {[(ch['title'], ch['id']) for ch in unique_chapters]}")
                        
            except (ValueError, TypeError) as e:
                logger.warning(f"章节ID排序失败: {e}，保持原始顺序")
            
            return unique_chapters
            
        except Exception as e:
            logger.error(f"解析章节列表失败: {e}")
            return []
    
    async def crawl_chapter_advanced(self, book_id: str, chapter_id: str, chapter_title: str = "", book_name: str = "", max_retries: int = None) -> Optional[List[str]]:
        """
        爬取章节内容 - 使用新的重试机制和内容提取器
        
        Args:
            book_id: 书籍ID
            chapter_id: 章节ID
            chapter_title: 章节标题
            book_name: 书名
            max_retries: 最大重试次数（如果为None则使用配置中的值）
            
        Returns:
            Optional[List[str]]: 章节内容行列表，失败时返回None
        """
        logger.info(f"开始爬取章节: {chapter_title} (ID: {chapter_id})")
        
        # 使用配置中的重试次数
        if max_retries is None:
            max_retries = self.config.get('max_retries', 3)
        
        # 尝试多种URL格式
        url_formats = [
            f"{self.base_url}/shuku/{book_id}-{chapter_id}/",
            f"{self.base_url}/shuku/{book_id}-{chapter_id}",
            f"{self.base_url}/book/{book_id}/chapter/{chapter_id}/",
            f"{self.base_url}/chapter/{book_id}-{chapter_id}/",
            f"{self.base_url}/read/{book_id}/{chapter_id}/"
        ]
        
        logger.debug(f"尝试的URL格式: {url_formats}")
        
        for chapter_url in url_formats:
            logger.info(f"正在尝试爬取章节: {chapter_title} -> {chapter_url}")
            
            try:
                # 使用重试机制发起请求
                response = await self._make_request(chapter_url)
                
                if response.status_code != 200:
                    logger.warning(f"章节页面返回状态码: {response.status_code}")
                    continue
                
                # 解析HTML内容
                html_content = response.text
                content_lines = await self.parse_chapter_content(html_content, chapter_url)
                
                # 检查是否需要登录 - 使用更准确的检测逻辑
                login_required = False
                if content_lines and len(content_lines) > 0:
                    # 扩展的登录检测指标
                    login_indicators = [
                        '登录', 'VIP', '会员', '付费', '订阅', '充值',
                        '解锁', '购买', '开通', '升级', '续费',
                        'login', 'vip', 'member', 'pay', 'subscribe'
                    ]
                    
                    # 检查前10行内容中是否包含登录指标
                    check_lines = content_lines[:10]
                    login_count = 0
                    
                    for line in check_lines:
                        line_lower = line.lower()
                        for indicator in login_indicators:
                            if indicator.lower() in line_lower:
                                login_count += 1
                                logger.debug(f"检测到登录指标 '{indicator}' 在行: {line[:50]}...")
                                break
                    
                    # 如果多行包含登录指标，或者内容过少，可能需要登录
                    if login_count >= 2 or (len(content_lines) < 3 and login_count >= 1):
                        login_required = True
                        logger.info(f"检测到登录需求: 登录指标数量={login_count}, 内容行数={len(content_lines)}")
                    
                    # 额外检查：如果内容过少且包含特定关键词
                    if len(content_lines) < 5:
                        short_content_text = ' '.join(content_lines).lower()
                        if any(keyword in short_content_text for keyword in ['需要登录', '请登录', '会员专享', 'vip专享']):
                            login_required = True
                            logger.info("检测到短内容中的明确登录提示")
                
                if login_required and self.config.get('detect_login', True):
                    logger.warning(f"章节 {chapter_title} 需要登录才能访问")
                    if self.config.get('save_login_info', True):
                        login_message = await self.generate_login_required_message(
                            book_id, chapter_id, chapter_title, book_name, chapter_url
                        )
                        await self.save_login_required_info(book_name, chapter_title, login_message)
                        return [login_message]
                
                if content_lines and len(content_lines) > 0:
                    logger.info(f"成功获取章节内容，共 {len(content_lines)} 行")
                    return content_lines
                else:
                    logger.warning(f"章节内容获取失败或内容过少: {chapter_title}")
                    # 尝试使用API获取内容
                    api_content = await self.get_chapter_content_via_api(book_id, chapter_id)
                    if api_content:
                        logger.info(f"通过API成功获取章节内容，共 {len(api_content)} 行")
                        return api_content
                    continue  # 尝试下一个URL格式
                    
            except httpx.HTTPStatusError as e:
                # 详细的HTTP错误处理
                status_code = e.response.status_code
                if status_code == 404:
                    logger.warning(f"章节不存在 (404): {chapter_url}")
                elif status_code == 403:
                    logger.warning(f"访问被拒绝 (403): {chapter_url}")
                elif status_code == 401:
                    logger.warning(f"需要认证 (401): {chapter_url}")
                elif status_code == 429:
                    logger.warning(f"请求过于频繁 (429): {chapter_url}")
                    # 对于429错误，等待更长时间
                    await asyncio.sleep(self.config.get('anti_crawler_delay', 15))
                elif status_code >= 500:
                    logger.warning(f"服务器错误 ({status_code}): {chapter_url}")
                else:
                    logger.warning(f"HTTP错误 ({status_code}): {chapter_url}")
                
                # 对于某些错误码，不继续尝试其他URL
                if status_code in [404, 403, 401]:
                    continue
                else:
                    # 对于服务器错误，可能是临时的，继续尝试其他URL
                    continue
                    
            except httpx.TimeoutException as e:
                logger.warning(f"请求超时: {chapter_url} - {e}")
                continue
                
            except httpx.RequestError as e:
                logger.warning(f"请求错误: {chapter_url} - {e}")
                continue
                
            except Exception as e:
                logger.error(f"未知错误处理章节 {chapter_url}: {type(e).__name__}: {e}")
                continue
        
        logger.error(f"所有URL格式都无法获取章节内容: {chapter_title}")
        return None
    
    async def parse_chapter_content(self, html_content: str, page_url: str = "") -> List[str]:
        """使用 BeautifulSoup 解析章节内容"""
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            logger.debug(f"页面内容长度: {len(html_content)}")
            
            # 过滤关键词
            skip_keywords = [
                '广告', '推荐', '点击', '收藏', '订阅', '投票',
                '上一章', '下一章', '目录', '返回', '首页',
                'copyright', '版权', '声明', '免责', '登录', '注册',
                '书名：', '作者：', '本章字数：', '更新时间：',
                '请收藏', '请订阅', '请投票', '请推荐',
                '七猫中文网', '奇猫', 'qimao', 'www.qimao.com',
                '导航', '菜单', '搜索', '登录', '注册', '帮助'
            ]
            
            content_lines = []
            
            # 尝试多种选择器来查找章节内容
            content_selectors = [
                # 七猫中文网特定的选择器
                '.chapter-content',
                '.content',
                '.article-content',
                '.chapter-text',
                '.read-content',
                '.novel-content',
                'article',
                '.main-content',
                '#content',
                '.text-content',
                # 添加更多可能的选择器
                '.chapter-body',
                '.chapter-main',
                '.read-main',
                '.book-content',
                '.story-content',
                '.chapter-detail',
                '.content-main',
                '.read-content-main',
                # 通用选择器
                'div[class*="content"]',
                'div[class*="chapter"]',
                'div[class*="read"]',
                'div[class*="text"]',
                'div[class*="article"]',
            ]
            
            for selector in content_selectors:
                try:
                    elements = soup.select(selector)
                    if elements:
                        logger.debug(f"选择器 {selector} 找到 {len(elements)} 个元素")
                        
                        for i, element in enumerate(elements):
                            try:
                                # 获取元素内的所有文本
                                text_content = element.get_text(separator='\n', strip=True)
                                
                                if text_content and len(text_content) > 50:
                                    logger.debug(f"元素 {i} 文本长度: {len(text_content)}, 前100字符: {text_content[:100]}")
                                    
                                    # 按行分割并清理
                                    lines = text_content.split('\n')
                                    temp_lines = []
                                    
                                    for line in lines:
                                        line = line.strip()
                                        if line and len(line) > 5:
                                            # 过滤掉不需要的内容
                                            if not any(skip in line for skip in skip_keywords):
                                                temp_lines.append(line)
                                    
                                    if len(temp_lines) > 3:
                                        content_lines.extend(temp_lines)
                                        logger.info(f"使用选择器 {selector} 元素 {i} 成功解析内容，共 {len(temp_lines)} 行")
                                        
                                        # 如果已经找到足够的内容，可以停止
                                        if len(content_lines) > 10:
                                            break
                                            
                            except Exception as e:
                                logger.debug(f"处理元素 {i} 失败: {e}")
                                continue
                        
                        if len(content_lines) > 5:
                            logger.info(f"选择器 {selector} 总共解析到 {len(content_lines)} 行内容")
                            break
                                
                except Exception as e:
                    logger.debug(f"选择器 {selector} 失败: {e}")
                    continue
            
            # 如果上述方法都失败，尝试查找所有p标签
            if not content_lines:
                logger.warning("所有选择器都失败，尝试查找p标签")
                try:
                    p_tags = soup.find_all('p')
                    for p in p_tags:
                        text = p.get_text(strip=True)
                        if text and len(text) > 10:
                            if not any(skip in text for skip in skip_keywords):
                                content_lines.append(text)
                    
                    if content_lines:
                        logger.info(f"通过p标签解析到 {len(content_lines)} 行内容")
                except Exception as e:
                    logger.debug(f"p标签解析失败: {e}")
            
            # 如果还是没有内容，尝试从body中提取文本
            if not content_lines:
                logger.warning("所有解析方法都失败，尝试从body提取文本")
                try:
                    body = soup.find('body')
                    if body:
                        full_text = body.get_text(separator='\n', strip=True)
                        logger.debug(f"页面全文长度: {len(full_text)}")
                        
                        if full_text and len(full_text) > 100:
                            lines = full_text.split('\n')
                            for line in lines:
                                line = line.strip()
                                if line and len(line) > 10:
                                    if not any(skip in line for skip in skip_keywords):
                                        content_lines.append(line)
                            
                            if content_lines:
                                logger.info(f"通过body全文解析到 {len(content_lines)} 行内容")
                except Exception as e:
                    logger.debug(f"body全文解析失败: {e}")
            
            # 如果还是没有内容，尝试正则表达式提取中文内容
            if not content_lines:
                logger.warning("所有解析方法都失败，尝试正则表达式提取")
                try:
                    # 查找包含中文的段落
                    chinese_pattern = r'[\u4e00-\u9fff]{20,}'
                    chinese_matches = re.findall(chinese_pattern, html_content)
                    
                    if chinese_matches:
                        for match in chinese_matches:
                            if not any(skip in match for skip in skip_keywords):
                                content_lines.append(match)
                        
                        if content_lines:
                            logger.info(f"通过正则表达式解析到 {len(content_lines)} 行内容")
                except Exception as e:
                    logger.debug(f"正则表达式解析失败: {e}")
            
            # 最终检查
            if content_lines:
                logger.info(f"最终解析到 {len(content_lines)} 行内容")
                # 显示前几行内容作为调试
                for i, line in enumerate(content_lines[:3]):
                    logger.debug(f"内容行 {i+1}: {line[:100]}...")
            else:
                logger.warning("未能解析到任何章节内容")
            
            return content_lines
            
        except Exception as e:
            logger.error(f"解析章节内容失败: {e}")
            return []
    
    async def get_chapter_content_via_api(self, book_id: str, chapter_id: str) -> Optional[List[str]]:
        """通过API获取章节内容"""
        try:
            logger.info(f"尝试通过API获取章节内容: {book_id}-{chapter_id}")

            # 确保客户端已初始化
            await self.init_client()

            # 尝试多个可能的API端点
            api_urls = [
                f"https://www.qimao.com/api/chapter/content?book_id={book_id}&chapter_id={chapter_id}",
                f"https://www.qimao.com/api/book/chapter-content?book_id={book_id}&chapter_id={chapter_id}",
                f"https://www.qimao.com/api/read/{book_id}/{chapter_id}",
                f"https://www.qimao.com/api/chapter/{book_id}-{chapter_id}",
                f"https://www.qimao.com/api/book/{book_id}/chapter/{chapter_id}/content"
            ]

            for api_url in api_urls:
                try:
                    logger.info(f"尝试API: {api_url}")
                    response = await self.client.get(api_url, timeout=10.0)
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            logger.info(f"API响应成功: {api_url}")
                        except:
                            # 如果不是JSON，尝试解析为文本
                            data = response.text
                            logger.info(f"API响应为文本格式: {api_url}")
                        
                        # 解析API响应
                        content_lines = []
                        
                        # 尝试多种数据结构
                        if isinstance(data, dict):
                            if 'data' in data:
                                content_data = data['data']
                                if isinstance(content_data, dict):
                                    # 查找内容字段
                                    content_fields = ['content', 'text', 'body', 'chapter_content', 'chapter_text']
                                    for field in content_fields:
                                        if field in content_data and content_data[field]:
                                            content = content_data[field]
                                            if isinstance(content, str):
                                                # 按行分割内容
                                                lines = content.split('\n')
                                                for line in lines:
                                                    line = line.strip()
                                                    if line and len(line) > 5:
                                                        content_lines.append(line)
                                            break
                                elif isinstance(content_data, str):
                                    # 直接是字符串内容
                                    lines = content_data.split('\n')
                                    for line in lines:
                                        line = line.strip()
                                        if line and len(line) > 5:
                                            content_lines.append(line)
                            else:
                                # 直接查找内容字段
                                content_fields = ['content', 'text', 'body', 'chapter_content', 'chapter_text']
                                for field in content_fields:
                                    if field in data and data[field]:
                                        content = data[field]
                                        if isinstance(content, str):
                                            lines = content.split('\n')
                                            for line in lines:
                                                line = line.strip()
                                                if line and len(line) > 5:
                                                    content_lines.append(line)
                                        break
                        elif isinstance(data, str):
                            # 直接是字符串内容
                            lines = data.split('\n')
                            for line in lines:
                                line = line.strip()
                                if line and len(line) > 5:
                                    content_lines.append(line)
                        
                        if content_lines:
                            logger.info(f"API获取到 {len(content_lines)} 行内容")
                            return content_lines
                        else:
                            logger.warning(f"API响应中未找到内容，数据结构: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                            
                except httpx.TimeoutException:
                    logger.debug(f"API请求超时: {api_url}")
                    continue
                except Exception as e:
                    logger.debug(f"API请求失败: {api_url}, 错误: {e}")
                    continue
            
            logger.warning("所有API端点都无法获取章节内容")
            return None

        except Exception as e:
            logger.error(f"API获取章节内容失败: {e}")
            return None

    async def generate_login_required_message(self, book_id: str, chapter_id: str, chapter_title: str, book_name: str, page_url: str = "") -> str:
        """生成需要登录的提示信息"""
        try:
            # 生成提示信息
            message = f"""【需要登录】
书籍: {book_name}
章节: {chapter_title}
章节ID: {chapter_id}
书籍ID: {book_id}
页面URL: {page_url}

该章节需要登录才能查看内容。
请访问 https://www.qimao.com 进行登录。"""
            logger.warning(f"生成登录提示信息: {message}")
            return message
        except Exception as e:
            logger.error(f"生成登录提示信息失败: {e}")
            return f"【需要登录】{chapter_title}"

    async def save_login_required_info(self, book_name: str, chapter_title: str, message: str):
        """
        保存需要登录的信息到文件
        
        Args:
            book_name: 书名
            chapter_title: 章节标题
            message: 登录提示信息
        """
        try:
            # 使用配置中的登录目录
            login_dir = self.config.get('login_dir', 'login_required')
            if not os.path.exists(login_dir):
                os.makedirs(login_dir)

            # 生成文件名并清理非法字符
            filename = f"{book_name}_{chapter_title}_login_required.txt"
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            filepath = os.path.join(login_dir, filename)

            # 保存信息到文件
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(message)

            logger.info(f"✅ 登录提示信息已保存到: {filepath}")
            
        except Exception as e:
            logger.error(f"保存登录提示信息失败: {e}")
            # 尝试保存到当前目录作为备选
            try:
                fallback_filename = f"login_required_{int(time.time())}.txt"
                with open(fallback_filename, 'w', encoding='utf-8') as f:
                    f.write(message)
                logger.info(f"登录提示信息已保存到备选位置: {fallback_filename}")
            except Exception as fallback_error:
                logger.error(f"备选保存也失败: {fallback_error}")

    async def get_book_info(self, book_id: str) -> Optional[Dict]:
        """获取书籍基本信息

        Args:
            book_id: 书籍ID

        Returns:
            书籍信息字典，包含 title, author, description 等
        """
        try:
            logger.info(f"开始获取书籍信息: {book_id}")

            # 确保客户端已初始化
            await self.init_client()

            # 访问书籍详情页
            book_url = f"{self.base_url}/shuku/{book_id}/"
            response = await self.client.get(book_url, timeout=30.0)
            
            if response.status_code != 200:
                logger.warning(f"书籍详情页返回状态码: {response.status_code}")
                return None
            
            html_content = response.text
            soup = BeautifulSoup(html_content, 'lxml')

            book_info = {
                'book_id': book_id,
                'url': book_url,
                'title': '',
                'author': '',
                'description': '',
                'status': '',
                'word_count': '',
                'rating': '',
                'collection_count': ''
            }

            # 提取书籍标题
            try:
                title_selectors = ['h1', '.book-title', '.title', '[class*="title"]']
                for selector in title_selectors:
                    title_elem = soup.select_one(selector)
                    if title_elem:
                        title_text = title_elem.get_text(strip=True)
                        # 清理标题中的评分信息（例如 "书名9.8分" -> "书名"）
                        title_text = re.sub(r'\d+\.\d+分$', '', title_text).strip()
                        if title_text:
                            book_info['title'] = title_text
                            logger.info(f"提取书籍标题: {book_info['title']}")
                            break
            except Exception as e:
                logger.debug(f"提取标题失败: {e}")

            # 提取作者
            try:
                author_selectors = [
                    '.book-author', '.author', '[class*="author"]'
                ]
                for selector in author_selectors:
                    try:
                        author_elem = soup.select_one(selector)
                        if author_elem:
                            author_text = author_elem.get_text(strip=True)
                            # 清理文本，移除"作者："前缀
                            author_text = author_text.replace('作者：', '').replace('作者:', '').strip()
                            if author_text:
                                book_info['author'] = author_text
                                logger.info(f"提取作者: {book_info['author']}")
                                break
                    except:
                        continue
            except Exception as e:
                logger.debug(f"提取作者失败: {e}")

            # 提取简介
            try:
                desc_selectors = [
                    '.book-description', '.description', '.intro', '.synopsis',
                    '[class*="description"]', '[class*="intro"]'
                ]
                for selector in desc_selectors:
                    try:
                        desc_elem = soup.select_one(selector)
                        if desc_elem:
                            desc_text = desc_elem.get_text(strip=True)
                            if desc_text:
                                book_info['description'] = desc_text[:500]  # 限制长度
                                logger.info(f"提取简介: {book_info['description'][:100]}...")
                                break
                    except:
                        continue
            except Exception as e:
                logger.debug(f"提取简介失败: {e}")

            # 提取其他信息（状态、字数等）
            try:
                page_text = soup.get_text()

                # 提取字数
                word_match = re.search(r'(\d+(?:\.\d+)?)\s*万?\s*字', page_text)
                if word_match:
                    book_info['word_count'] = word_match.group(0).strip()

                # 提取状态
                if '连载中' in page_text:
                    book_info['status'] = '连载中'
                elif '完结' in page_text:
                    book_info['status'] = '完结'

                # 提取评分
                rating_match = re.search(r'(\d+\.\d+)\s*分', page_text)
                if rating_match:
                    book_info['rating'] = rating_match.group(1)

                # 提取收藏数
                collection_match = re.search(r'(\d+(?:,\d+)?)\s*收藏', page_text)
                if collection_match:
                    book_info['collection_count'] = collection_match.group(1)

            except Exception as e:
                logger.debug(f"提取其他信息失败: {e}")

            logger.info(f"书籍信息获取完成: {book_info['title']}")
            return book_info

        except Exception as e:
            logger.error(f"获取书籍信息失败: {e}")
            return None

    async def crawl_book_advanced(self, book_id: str, book_title: str = None, max_chapters: int = 10) -> List[Dict]:
        """使用 httpx + BeautifulSoup 爬取书籍"""
        start_time = time.time()
        
        if book_title is None:
            book_title = f"书籍ID_{book_id}"

        logger.info(f"开始爬取书籍: {book_title} (ID: {book_id}), 最大章节数: {max_chapters}")

        # 统计信息
        stats = {
            'total_chapters': 0,
            'successful_chapters': 0,
            'failed_chapters': 0,
            'login_required_chapters': 0,
            'total_words': 0,
            'extraction_methods': {}
        }

        try:
            # 初始化客户端
            await self.init_client()

            # 获取章节列表
            chapters_info = await self.get_chapter_list(book_id)
            if not chapters_info:
                logger.warning(f"无法获取章节列表: {book_title}")
                return []

            # 添加调试信息
            stats['total_chapters'] = len(chapters_info)
            logger.info(f"获取到 {len(chapters_info)} 个章节")
            if chapters_info:
                logger.info(f"第一个章节: ID={chapters_info[0]['id']}, 标题={chapters_info[0]['title']}")
                logger.info(f"最后一个章节: ID={chapters_info[-1]['id']}, 标题={chapters_info[-1]['title']}")

            # 限制爬取章节数量
            if max_chapters and len(chapters_info) > max_chapters:
                chapters_info = chapters_info[:max_chapters]
                logger.info(f"限制爬取前 {max_chapters} 章")
                stats['total_chapters'] = len(chapters_info)

            crawled_chapters = []

            for i, chapter_info in enumerate(chapters_info, 1):
                chapter_start_time = time.time()
                chapter_id = chapter_info.get('id', '')
                chapter_title = chapter_info.get('title', f'第{i}章')

                logger.info(f"进度: {i}/{len(chapters_info)} ({i/len(chapters_info)*100:.1f}%) - {chapter_title}")

                # 爬取章节内容
                content_lines = await self.crawl_chapter_advanced(book_id, chapter_id, chapter_title, book_title)

                chapter_time = time.time() - chapter_start_time
                
                if content_lines:
                    # 检查是否是登录提示
                    if len(content_lines) == 1 and '【需要登录】' in content_lines[0]:
                        stats['login_required_chapters'] += 1
                        logger.info(f"章节需要登录: {chapter_title}, 耗时 {chapter_time:.2f}秒")
                    else:
                        word_count = sum(len(line) for line in content_lines)
                        stats['successful_chapters'] += 1
                        stats['total_words'] += word_count
                        
                        chapter_data = {
                            'title': chapter_title,
                            'id': chapter_id,
                            'content': content_lines
                        }
                        crawled_chapters.append(chapter_data)

                        # 保存单个章节
                        self.save_chapter_to_file(book_title, chapter_title, content_lines)
                        
                        logger.info(f"章节爬取成功: {chapter_title}, {word_count} 字, 耗时 {chapter_time:.2f}秒")
                else:
                    stats['failed_chapters'] += 1
                    logger.warning(f"章节爬取失败: {chapter_title}, 耗时 {chapter_time:.2f}秒")

                # 延迟避免请求过快
                await asyncio.sleep(random.uniform(2, 4))

            # 保存整本书
            if crawled_chapters:
                self.save_book_to_file(book_title, crawled_chapters)

            # 输出最终统计信息
            total_time = time.time() - start_time
            success_rate = (stats['successful_chapters'] / stats['total_chapters'] * 100) if stats['total_chapters'] > 0 else 0
            
            logger.info(f"书籍爬取完成: {book_title}")
            logger.info(f"统计信息:")
            logger.info(f"  - 总章节数: {stats['total_chapters']}")
            logger.info(f"  - 成功章节: {stats['successful_chapters']}")
            logger.info(f"  - 失败章节: {stats['failed_chapters']}")
            logger.info(f"  - 需要登录: {stats['login_required_chapters']}")
            logger.info(f"  - 成功率: {success_rate:.1f}%")
            logger.info(f"  - 总字数: {stats['total_words']:,}")
            logger.info(f"  - 总耗时: {total_time:.2f}秒")
            logger.info(f"  - 平均每章耗时: {total_time/stats['total_chapters']:.2f}秒")
            
            return crawled_chapters

        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"爬取书籍失败: {e}, 耗时 {total_time:.2f}秒")
            return []
        finally:
            # 关闭客户端
            await self.close_client()
    
    def save_chapter_to_file(self, book_title: str, chapter_title: str, content_lines: List[str]):
        """保存章节到文件"""
        try:
            safe_book_title = re.sub(r'[<>:"/\\|?*]', '_', book_title)
            safe_chapter_title = re.sub(r'[<>:"/\\|?*]', '_', chapter_title)
            
            filename = f"{safe_book_title}_{safe_chapter_title}.txt"
            filepath = os.path.join(self.output_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"{chapter_title}\n")
                f.write("=" * 50 + "\n\n")
                for line in content_lines:
                    f.write(line + "\n")
            
            logger.info(f"章节内容已保存到: {filepath}")
            
        except Exception as e:
            logger.error(f"保存章节内容失败: {e}")
    
    def save_book_to_file(self, book_title: str, chapters: List[Dict]):
        """保存整本书到文件"""
        try:
            safe_book_title = re.sub(r'[<>:"/\\|?*]', '_', book_title)
            filename = f"{safe_book_title}_完整版.txt"
            filepath = os.path.join(self.output_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"《{book_title}》\n")
                f.write("=" * 50 + "\n\n")
                
                for i, chapter in enumerate(chapters, 1):
                    chapter_title = chapter.get('title', f'第{i}章')
                    content_lines = chapter.get('content', [])
                    
                    f.write(f"{chapter_title}\n")
                    f.write("-" * 30 + "\n")
                    
                    for line in content_lines:
                        f.write(line + "\n")
                    
                    f.write("\n\n")
            
            logger.info(f"整本书已保存到: {filepath}")
            
        except Exception as e:
            logger.error(f"保存整本书失败: {e}")

async def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法: python advanced_crawler.py <book_id> [book_title] [max_chapters]")
        print("示例: python advanced_crawler.py 195958 '盖世神医' 5")
        return
    
    book_id = sys.argv[1]
    book_title = sys.argv[2] if len(sys.argv) > 2 else None
    max_chapters = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    
    crawler = AdvancedCrawler()
    
    try:
        crawled_chapters = await crawler.crawl_book_advanced(book_id, book_title, max_chapters)
        if crawled_chapters:
            print(f"\n爬取完成！成功获取 {len(crawled_chapters)} 章内容")
            print("前3章内容预览:")
            for i, chapter in enumerate(crawled_chapters[:3], 1):
                print(f"\n{chapter['title']}:")
                for j, line in enumerate(chapter['content'][:3], 1):
                    print(f"  {j}. {line}")
        else:
            print("爬取失败，未获取到内容")
    except KeyboardInterrupt:
        logger.info("用户中断爬虫")
    except Exception as e:
        logger.error(f"爬虫运行出错: {e}")

# 为了兼容性，创建别名
BookContentCrawler = AdvancedCrawler

if __name__ == "__main__":
    asyncio.run(main())
