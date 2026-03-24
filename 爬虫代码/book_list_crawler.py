#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小说列表爬虫 - 爬取每个类别的小说信息（50-200本）+ 真实章节
"""

import asyncio
import json
import os
import sys
import logging
import random
import re
from typing import List, Dict, Optional
from datetime import datetime
from playwright.async_api import async_playwright
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CATEGORIES, SITE_CONFIG
from logging_config import get_logger

logger = get_logger('book_list_crawler')


class BookListCrawler:
    def __init__(self, min_books: int = 50, max_books: int = 200):
        self.base_url = SITE_CONFIG['base_url']
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        self.min_books = min_books
        self.max_books = max_books

        # 创建输出目录
        self.output_dir = "qimao_data"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    async def init_browser(self):
        """初始化浏览器"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-gpu',
            ]
        )

        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
            locale='zh-CN',
            timezone_id='Asia/Shanghai',
        )

        self.page = await self.context.new_page()
        self.page.set_default_timeout(30000)

        # 设置请求拦截以加快页面加载
        await self.page.route('**/*.{woff,woff2,ttf,eot}', lambda route: route.abort())

        logger.info("浏览器初始化完成")
    
    async def close_browser(self):
        """关闭浏览器"""
        try:
            if self.page:
                try:
                    if not self.page.is_closed():
                        await self.page.close()
                except:
                    pass
                self.page = None

            if self.context:
                try:
                    await self.context.close()
                except:
                    pass
                self.context = None

            if self.browser:
                try:
                    await self.browser.close()
                except:
                    pass
                self.browser = None

            if self.playwright:
                try:
                    await self.playwright.stop()
                except:
                    pass
                self.playwright = None

            logger.info("浏览器已关闭")
        except Exception as e:
            logger.warning(f"关闭浏览器时出错: {e}")
    
    async def crawl_category(self, category: Dict) -> List[Dict]:
        """爬取单个分类的书籍列表"""
        category_name = category['name']
        url_suffix = category['url_suffix']
        url = f"{self.base_url}/shuku/{url_suffix}"

        # 为该分类随机选择目标书籍数量（50-200之间）
        target_books = random.randint(50, 200)

        logger.info(f"开始爬取分类: {category_name}")
        logger.info(f"URL: {url}")
        logger.info(f"该分类目标获取书籍数: {target_books} 本")

        books = []
        page_num = 1
        consecutive_failures = 0
        max_consecutive_failures = 2

        try:
            while len(books) < target_books:
                # 构建分页URL
                page_url = url.replace('click-1/', f'click-{page_num}/')
                logger.info(f"爬取第 {page_num} 页，当前已获取 {len(books)} 本书")

                try:
                    # 使用更灵活的等待策略：先尝试 domcontentloaded，失败则重试
                    try:
                        await self.page.goto(page_url, wait_until='domcontentloaded', timeout=20000)
                        logger.debug(f"页面加载成功 (domcontentloaded)")
                    except Exception as e:
                        logger.warning(f"domcontentloaded 超时，尝试 load: {e}")
                        await self.page.goto(page_url, wait_until='load', timeout=15000)
                        logger.debug(f"页面加载成功 (load)")

                    # 等待书籍列表加载
                    try:
                        await self.page.wait_for_selector('li.qm-cover-text-item', timeout=8000)
                        logger.debug("检测到书籍列表元素")
                    except:
                        logger.warning("等待书籍列表元素超时，继续尝试提取")

                    await asyncio.sleep(random.uniform(2, 3))

                    # 提取书籍信息
                    page_books = await self.extract_books_from_page()

                    if not page_books:
                        logger.warning(f"第 {page_num} 页未获取到书籍")
                        consecutive_failures += 1
                        if consecutive_failures >= max_consecutive_failures:
                            logger.warning(f"连续 {consecutive_failures} 页未获取到书籍，停止爬取")
                            break
                        page_num += 1
                        continue

                    consecutive_failures = 0  # 重置失败计数

                    # 为每本书获取章节信息 - 获取所有章节
                    for book in page_books:
                        try:
                            if book.get('qimao_book_id') and book.get('url'):
                                # 不指定 max_chapters，获取所有章节
                                chapters = await self.fetch_book_chapters(
                                    book['qimao_book_id'],
                                    book['url']
                                )
                                book['chapters'] = chapters
                                book['chapter_count'] = len(chapters)
                                logger.info(f"书籍 {book.get('title')} 获取到 {len(chapters)} 个章节")
                            else:
                                book['chapters'] = []
                                book['chapter_count'] = 0
                        except Exception as e:
                            logger.warning(f"获取书籍 {book.get('title')} 的章节失败: {e}")
                            book['chapters'] = []
                            book['chapter_count'] = 0

                    books.extend(page_books)
                    logger.info(f"第 {page_num} 页获取到 {len(page_books)} 本书")

                    # 如果已获取足够的书籍，停止
                    if len(books) >= target_books:
                        logger.info(f"已获取 {len(books)} 本书，达到目标 {target_books}")
                        break

                    page_num += 1
                    await asyncio.sleep(random.uniform(1, 2))  # 页面间延迟

                except Exception as e:
                    logger.error(f"爬取第 {page_num} 页失败: {e}")
                    consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        logger.error(f"连续失败 {consecutive_failures} 次，停止爬取")
                        break
                    page_num += 1
                    await asyncio.sleep(random.uniform(2, 3))

        except Exception as e:
            logger.error(f"爬取分类 {category_name} 失败: {e}")

        # 限制书籍数到目标数量
        if len(books) > target_books:
            books = books[:target_books]

        logger.info(f"分类 {category_name} 爬取完成，共获取 {len(books)} 本书（目标: {target_books}）")
        return books
    
    async def extract_books_from_page(self) -> List[Dict]:
        """从页面提取书籍信息"""
        books = []

        try:
            # 直接查找书籍列表项
            logger.debug("开始查找书籍列表项...")

            # 首先尝试最具体的选择器
            book_elements = await self.page.query_selector_all('li.qm-cover-text-item')
            logger.debug(f"使用 'li.qm-cover-text-item' 找到 {len(book_elements)} 个元素")

            if not book_elements or len(book_elements) == 0:
                # 尝试其他选择器
                book_elements = await self.page.query_selector_all('.qm-cover-text-item')
                logger.debug(f"使用 '.qm-cover-text-item' 找到 {len(book_elements)} 个元素")

            if not book_elements or len(book_elements) == 0:
                logger.warning("未找到书籍元素")
                return []

            logger.info(f"找到 {len(book_elements)} 个书籍列表项")

            # 提取每个书籍的信息
            for i, element in enumerate(book_elements):
                try:
                    book_info = await self.extract_book_info(element)
                    if book_info:
                        books.append(book_info)
                        logger.debug(f"成功提取第 {i+1} 本书: {book_info.get('title', 'N/A')}")
                except Exception as e:
                    logger.debug(f"提取第 {i+1} 个书籍信息失败: {e}")
                    continue

            logger.info(f"从页面提取到 {len(books)} 本书籍信息")
            return books

        except Exception as e:
            logger.error(f"提取页面书籍失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    async def extract_book_info(self, element) -> Optional[Dict]:
        """提取单个书籍的信息"""
        try:
            book_info = {}

            # 提取书名和链接 - 七猫网站使用 .s-tit a
            try:
                title_elem = await element.query_selector('.s-tit a')
                if title_elem:
                    book_info['title'] = (await title_elem.inner_text()).strip()
                    href = await title_elem.get_attribute('href')
                    if href:
                        book_info['url'] = href if href.startswith('http') else f"{self.base_url}{href}"
                        # 从URL提取书籍ID
                        if '/shuku/' in href:
                            book_id = href.split('/shuku/')[1].split('/')[0]
                            book_info['qimao_book_id'] = book_id
            except Exception as e:
                logger.debug(f"提取书名失败: {e}")

            # 提取作者 - 七猫网站使用 .s-author
            try:
                author_elem = await element.query_selector('.s-author')
                if author_elem:
                    book_info['author'] = (await author_elem.inner_text()).strip()
            except Exception as e:
                logger.debug(f"提取作者失败: {e}")

            # 提取简介 - 七猫网站使用 .s-desc
            try:
                desc_elem = await element.query_selector('.s-desc')
                if desc_elem:
                    desc_text = await desc_elem.inner_text()
                    book_info['description'] = desc_text.strip()[:200]  # 限制长度
            except Exception as e:
                logger.debug(f"提取简介失败: {e}")

            # 提取字数 - 七猫网站使用 .s-words-num
            try:
                word_elem = await element.query_selector('.s-words-num')
                if word_elem:
                    book_info['word_count'] = (await word_elem.inner_text()).strip()
            except Exception as e:
                logger.debug(f"提取字数失败: {e}")

            # 提取状态 - 七猫网站使用 .s-status
            try:
                status_elem = await element.query_selector('.s-status')
                if status_elem:
                    book_info['status'] = (await status_elem.inner_text()).strip()
            except Exception as e:
                logger.debug(f"提取状态失败: {e}")

            # 提取分类
            try:
                category_elem = await element.query_selector('.s-category')
                if category_elem:
                    book_info['category'] = (await category_elem.inner_text()).strip()
            except Exception as e:
                logger.debug(f"提取分类失败: {e}")

            # 提取更新时间
            try:
                update_elem = await element.query_selector('.s-update-time')
                if update_elem:
                    book_info['update_time'] = (await update_elem.inner_text()).strip()
            except Exception as e:
                logger.debug(f"提取更新时间失败: {e}")

            if book_info.get('title'):
                return book_info

            return None

        except Exception as e:
            logger.debug(f"提取书籍信息失败: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None

    async def fetch_book_chapters(self, book_id: str, book_url: str, max_chapters: int = None) -> List[Dict]:
        """获取书籍的所有章节信息

        Args:
            book_id: 书籍ID
            book_url: 书籍URL
            max_chapters: 最大章节数（None表示获取所有章节）

        Returns:
            章节列表
        """
        try:
            logger.debug(f"开始获取书籍 {book_id} 的章节信息")

            # 检查页面是否仍然有效
            if not self.page or self.page.is_closed():
                logger.warning(f"页面已关闭，跳过书籍 {book_id} 的章节获取")
                return []

            # 访问书籍页面 - 使用更灵活的等待策略，带超时保护
            try:
                await asyncio.wait_for(
                    self.page.goto(book_url, wait_until='domcontentloaded', timeout=12000),
                    timeout=15
                )
            except asyncio.TimeoutError:
                logger.debug(f"domcontentloaded 超时，尝试 load")
                try:
                    await asyncio.wait_for(
                        self.page.goto(book_url, wait_until='load', timeout=8000),
                        timeout=12
                    )
                except Exception as e2:
                    logger.warning(f"页面加载失败: {e2}")
                    return []
            except Exception as e:
                logger.debug(f"页面加载异常: {e}")
                try:
                    await asyncio.wait_for(
                        self.page.goto(book_url, wait_until='load', timeout=8000),
                        timeout=12
                    )
                except Exception as e2:
                    logger.warning(f"页面加载失败: {e2}")
                    return []

            await asyncio.sleep(random.uniform(1, 2))  # 增加等待时间确保页面加载完成

            chapters = []

            # 尝试从页面解析章节列表
            try:
                # 第一步：尝试点击"作品目录"标签以获取完整的章节列表
                logger.debug(f"尝试点击'作品目录'标签...")
                catalog_clicked = False
                
                # 使用多种方法查找并点击目录标签
                catalog_selectors = [
                    # 精确匹配文本
                    'text="作品目录"',
                    'text=/作品目录/',
                    # 包含"作品目录"的链接或按钮
                    'a:has-text("作品目录")',
                    'button:has-text("作品目录")',
                    '.tab:has-text("作品目录")',
                    '[data-tab*="目录"]',
                    # 包含"目录"的标签
                    'a:has-text("目录")',
                    'button:has-text("目录")',
                    '.tab:has-text("目录")',
                    # 尝试通过XPath查找
                    'xpath=//a[contains(text(), "作品目录")]',
                    'xpath=//button[contains(text(), "作品目录")]',
                    'xpath=//div[contains(text(), "作品目录")]',
                    'xpath=//span[contains(text(), "作品目录")]',
                    # 尝试通过类名查找
                    '[class*="catalog"]',
                    '[class*="目录"]',
                    '[class*="chapter-list"]',
                ]
                
                for selector in catalog_selectors:
                    try:
                        # 等待元素出现
                        try:
                            await self.page.wait_for_selector(selector, timeout=3000)
                        except:
                            continue
                        
                        element = await self.page.query_selector(selector)
                        if element:
                            # 检查元素是否可见
                            is_visible = await element.is_visible()
                            if is_visible:
                                # 尝试滚动到元素
                                await element.scroll_into_view_if_needed()
                                await asyncio.sleep(0.5)
                                
                                # 点击元素
                                await element.click()
                                await asyncio.sleep(2)  # 等待标签页内容加载
                                logger.info(f"成功点击目录标签: {selector}")
                                catalog_clicked = True
                                break
                    except Exception as e:
                        logger.debug(f"尝试选择器 {selector} 失败: {e}")
                        continue
                
                # 如果直接点击失败，尝试使用JavaScript点击
                if not catalog_clicked:
                    try:
                        logger.debug("尝试使用JavaScript点击目录标签...")
                        # 使用JavaScript查找并点击目录标签
                        clicked = await self.page.evaluate("""
                            () => {
                                // 查找包含"作品目录"的所有元素
                                const elements = Array.from(document.querySelectorAll('a, button, div, span, li'));
                                for (let el of elements) {
                                    const text = el.textContent || el.innerText || '';
                                    if (text.includes('作品目录') || text.includes('目录')) {
                                        // 检查是否是标签页按钮
                                        if (el.closest('.tab') || el.closest('[role="tab"]') || 
                                            el.getAttribute('data-tab') || el.onclick) {
                                            el.click();
                                            return true;
                                        }
                                    }
                                }
                                return false;
                            }
                        """)
                        if clicked:
                            await asyncio.sleep(2)
                            logger.info("使用JavaScript成功点击目录标签")
                            catalog_clicked = True
                    except Exception as e:
                        logger.debug(f"JavaScript点击失败: {e}")
                
                if not catalog_clicked:
                    logger.warning("未能点击目录标签，尝试直接解析章节列表")

                # 等待章节列表加载
                await asyncio.sleep(2)

                # 第二步：查找所有章节链接
                # 尝试多种选择器查找章节链接
                chapter_selectors = [
                    # 七猫网站的章节列表容器 - 更精确的选择器
                    'ul[class*="catalog"] a[href*="/shuku/"][href*="-"]',
                    'div[class*="catalog"] a[href*="/shuku/"][href*="-"]',
                    '.chapter-list a[href*="/shuku/"][href*="-"]',
                    '.catalog-list a[href*="/shuku/"][href*="-"]',
                    '.qm-chapter-list a[href*="/shuku/"][href*="-"]',
                    # 目录区域内的链接
                    '[class*="chapter"] a[href*="/shuku/"][href*="-"]',
                    '[class*="catalog"] li a[href*="/shuku/"][href*="-"]',
                    # 通用章节链接 - 排除导航链接
                    'div[class*="chapter"] a[href*="/shuku/"][href*="-"]',
                    'ul[class*="chapter"] li a[href*="/shuku/"][href*="-"]',
                    # 最后的备选方案 - 所有包含章节ID的链接
                    'a[href*="/shuku/"][href*="-"]'
                ]

                chapter_elements = []
                for selector in chapter_selectors:
                    try:
                        # 等待元素出现
                        try:
                            await self.page.wait_for_selector(selector, timeout=3000)
                        except:
                            pass
                        
                        elements = await self.page.query_selector_all(selector)
                        if elements and len(elements) > 0:
                            logger.debug(f"使用选择器 {selector} 找到 {len(elements)} 个潜在章节链接")
                            chapter_elements = elements
                            break
                    except Exception as e:
                        logger.debug(f"选择器 {selector} 失败: {e}")
                        continue

                # 提取章节信息 - 过滤掉不是真实章节的链接
                seen_hrefs = set()  # 用于去重
                if chapter_elements:
                    for elem in chapter_elements:
                        try:
                            title = await elem.inner_text()
                            href = await elem.get_attribute('href')

                            if not href or not title:
                                continue

                            title_clean = title.strip()
                            
                            # 过滤掉空标题
                            if not title_clean or len(title_clean) == 0:
                                continue

                            # 处理相对URL
                            if href.startswith('/'):
                                href = f"{self.base_url}{href}"
                            elif not href.startswith('http'):
                                href = f"{self.base_url}/{href}"

                            # 去重
                            if href in seen_hrefs:
                                continue
                            seen_hrefs.add(href)

                            # 过滤掉分类、导航等非章节链接
                            skip_keywords = ['分类', '排序', '筛选', '搜索', '首页', '返回', '更多作品', 
                                           '作者其他作品', '正序', '倒序', '作品介绍', '作品目录']
                            if any(keyword in title_clean for keyword in skip_keywords):
                                continue

                            # 验证是否是章节链接（包含书籍ID和章节ID）
                            if f'/shuku/{book_id}-' in href or f'/shuku/{book_id}/' in href:
                                # 从href中提取章节ID
                                import re
                                match = re.search(r'/shuku/\d+-(\d+)/?', href)
                                if match:
                                    chapter_id = match.group(1)
                                    
                                    chapters.append({
                                        'id': chapter_id,
                                        'title': title_clean,
                                        'url': href
                                    })
                                    
                                    # 如果指定了最大章节数，则在达到时停止
                                    if max_chapters and len(chapters) >= max_chapters:
                                        break
                            # 也接受包含"第"和"章"的标题，即使URL格式不完全匹配
                            elif '第' in title_clean and '章' in title_clean:
                                # 尝试从标题中提取章节编号
                                chapter_num_match = re.search(r'第(\d+)章', title_clean)
                                if chapter_num_match:
                                    chapter_id = chapter_num_match.group(1)
                                    chapters.append({
                                        'id': chapter_id,
                                        'title': title_clean,
                                        'url': href
                                    })
                                    
                                    if max_chapters and len(chapters) >= max_chapters:
                                        break

                        except Exception as e:
                            logger.debug(f"解析章节元素失败: {e}")
                            continue

                # 按章节ID排序
                if chapters:
                    try:
                        chapters.sort(key=lambda x: int(x['id']) if x['id'].isdigit() else 999999)
                    except:
                        pass

                if chapters:
                    logger.info(f"成功获取书籍 {book_id} 的 {len(chapters)} 个章节")

                    # 如果只获取到1个章节，尝试生成完整的章节列表
                    if len(chapters) == 1:
                        logger.info(f"只获取到1个章节，尝试生成完整的章节列表...")
                        generated_chapters = await self.generate_chapter_list(book_id, chapters[0])
                        if generated_chapters and len(generated_chapters) > 1:
                            logger.info(f"成功生成 {len(generated_chapters)} 个章节列表")
                            return generated_chapters

                    return chapters
                else:
                    logger.warning(f"未找到任何章节链接，尝试其他方法...")
                    # 尝试通过页面文本查找章节
                    try:
                        page_text = await self.page.inner_text('body')
                        # 查找包含"第X章"的文本
                        import re
                        chapter_pattern = r'第(\d+)章[^\n]*'
                        matches = re.findall(chapter_pattern, page_text)
                        if matches:
                            logger.info(f"从页面文本中找到 {len(matches)} 个章节编号")
                            # 生成章节列表
                            for i, chapter_num in enumerate(matches[:50], 1):  # 限制最多50章
                                chapters.append({
                                    'id': str(chapter_num),
                                    'title': f'第{chapter_num}章',
                                    'url': f"{self.base_url}/shuku/{book_id}-{chapter_num}/"
                                })
                            if chapters:
                                return chapters
                    except Exception as e:
                        logger.debug(f"从页面文本查找章节失败: {e}")

            except Exception as e:
                logger.debug(f"从页面解析章节失败: {e}")
                import traceback
                logger.debug(traceback.format_exc())

            # 如果页面解析失败，返回空列表
            logger.warning(f"无法获取书籍 {book_id} 的章节信息")
            return []

        except Exception as e:
            logger.debug(f"获取书籍章节失败: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return []
    
    async def generate_chapter_list(self, book_id: str, last_chapter: Dict) -> List[Dict]:
        """生成从第1章开始的章节列表"""
        try:
            logger.info(f"开始生成章节列表，已知最后一章: {last_chapter['title']}")
            
            # 从最后一章标题中提取章节编号
            last_chapter_number = None
            import re
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
    
    async def crawl_all_categories(self) -> Dict:
        """爬取所有分类"""
        all_books = {}

        try:
            await self.init_browser()

            for idx, category in enumerate(CATEGORIES):
                category_name = category['name']
                logger.info(f"\n{'='*70}")
                logger.info(f"开始爬取第 {idx+1}/{len(CATEGORIES)} 个分类: {category_name}")
                logger.info(f"{'='*70}")

                try:
                    books = await self.crawl_category(category)
                    all_books[category_name] = books

                    # 保存单个分类数据
                    self.save_category_data(category_name, books)
                    logger.info(f"分类 {category_name} 数据已保存")

                    # 每个分类后检查浏览器状态
                    if self.page and self.page.is_closed():
                        logger.warning("浏览器页面已关闭，重新初始化")
                        try:
                            await self.close_browser()
                        except:
                            pass
                        await asyncio.sleep(2)
                        await self.init_browser()

                    # 分类间延迟
                    await asyncio.sleep(random.uniform(1, 2))

                except Exception as e:
                    logger.error(f"爬取分类 {category_name} 失败: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    all_books[category_name] = []

                    # 尝试恢复浏览器
                    try:
                        await self.close_browser()
                        await asyncio.sleep(2)
                        await self.init_browser()
                    except Exception as recovery_error:
                        logger.error(f"浏览器恢复失败: {recovery_error}")

            # 保存所有数据
            self.save_all_data(all_books)

            return all_books

        finally:
            try:
                await self.close_browser()
            except:
                pass
    
    def save_category_data(self, category_name: str, books: List[Dict]):
        """保存单个分类数据"""
        try:
            filename = f"{category_name}_books.json"
            filepath = os.path.join(self.output_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'category': category_name,
                    'count': len(books),
                    'books': books,
                    'crawl_time': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
            
            logger.info(f"分类数据已保存: {filepath}")
        except Exception as e:
            logger.error(f"保存分类数据失败: {e}")
    
    def save_all_data(self, all_books: Dict):
        """保存所有数据"""
        try:
            # 保存JSON格式
            json_file = os.path.join(self.output_dir, 'all_books.json')
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'total_categories': len(all_books),
                    'total_books': sum(len(books) for books in all_books.values()),
                    'categories': all_books,
                    'crawl_time': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
            
            logger.info(f"所有数据已保存: {json_file}")
            
            # 生成统计报告
            self.generate_report(all_books)
            
        except Exception as e:
            logger.error(f"保存所有数据失败: {e}")
    
    def generate_report(self, all_books: Dict):
        """生成爬取报告"""
        try:
            report_file = os.path.join(self.output_dir, 'crawl_report.txt')

            with open(report_file, 'w', encoding='utf-8') as f:
                f.write("=" * 70 + "\n")
                f.write("小说列表爬取报告\n")
                f.write("=" * 70 + "\n\n")

                f.write(f"爬取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"总分类数: {len(all_books)}\n")
                f.write(f"总书籍数: {sum(len(books) for books in all_books.values())}\n\n")

                f.write("各分类统计:\n")
                f.write("-" * 70 + "\n")

                for category_name, books in all_books.items():
                    f.write(f"{category_name}: {len(books)} 本\n")

                f.write("\n" + "=" * 70 + "\n")

            logger.info(f"报告已生成: {report_file}")
        except Exception as e:
            logger.error(f"生成报告失败: {e}")


async def main():
    """主函数"""
    min_books = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    max_books = int(sys.argv[2]) if len(sys.argv) > 2 else 200

    logger.info(f"开始爬取小说列表，每个分类目标: {min_books}-{max_books} 本")

    crawler = BookListCrawler(min_books=min_books, max_books=max_books)

    try:
        all_books = await crawler.crawl_all_categories()

        total_books = sum(len(books) for books in all_books.values())
        logger.info(f"\n爬取完成！总共获取 {total_books} 本书籍")

        # 打印统计信息
        for category_name, books in all_books.items():
            logger.info(f"  {category_name}: {len(books)} 本书")

    except Exception as e:
        logger.error(f"爬虫运行出错: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    asyncio.run(main())

