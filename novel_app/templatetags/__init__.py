from django import template
from django.utils.safestring import mark_safe
import re

register = template.Library()

@register.simple_tag
def book_cover_image(book, css_class="w-full h-full book-cover-img", alt_text=None):
    """
    智能封面显示标签
    检测封面URL是否为占位符或无效图片，如果是则使用默认封面
    """
    if alt_text is None:
        alt_text = book.title
    
    # 默认封面路径
    default_cover = '/static/imgs/book.jpg'
    
    # 检查封面URL是否有效
    cover_url = None
    if (book.cover_url and 
        book.cover_url.strip() and 
        book.cover_url != 'None' and 
        book.cover_url != 'null' and 
        book.cover_url != 'undefined' and 
        len(book.cover_url) > 10):
        
        # 检查是否为占位符图片的URL模式
        placeholder_patterns = [
            r'placeholder',
            r'default',
            r'no-image',
            r'no-cover',
            r'empty',
            r'null',
            r'undefined',
            r'\.svg$',  # SVG文件通常是占位符
            r'data:image',  # 数据URL通常是占位符
        ]
        
        is_placeholder = False
        for pattern in placeholder_patterns:
            if re.search(pattern, book.cover_url.lower()):
                is_placeholder = True
                break
        
        if not is_placeholder:
            cover_url = book.cover_url
    
    # 如果没有有效的封面URL，使用默认封面
    if not cover_url:
        cover_url = default_cover
    
    # 生成HTML
    html = f'''
    <img src="{cover_url}" 
         class="{css_class}" 
         alt="{alt_text}" 
         loading="lazy"
         onload="this.classList.add('loaded'); this.style.display='block'; this.nextElementSibling.style.display='none';"
         onerror="this.style.display='none'; this.nextElementSibling.style.display='flex'; this.classList.remove('loaded');">
    <div class="no-cover" style="display: none;">
        <i class="fas fa-book"></i>
    </div>
    '''
    
    return mark_safe(html)

@register.simple_tag
def book_cover_simple(book, css_class="w-full h-full book-cover-img", alt_text=None):
    """
    简化版封面显示标签，只返回图片URL
    """
    if alt_text is None:
        alt_text = book.title
    
    # 默认封面路径
    default_cover = '/static/imgs/book.jpg'
    
    # 检查封面URL是否有效
    cover_url = None
    if (book.cover_url and 
        book.cover_url.strip() and 
        book.cover_url != 'None' and 
        book.cover_url != 'null' and 
        book.cover_url != 'undefined' and 
        len(book.cover_url) > 10):
        
        # 检查是否为占位符图片的URL模式
        placeholder_patterns = [
            r'placeholder',
            r'default',
            r'no-image',
            r'no-cover',
            r'empty',
            r'null',
            r'undefined',
            r'\.svg$',  # SVG文件通常是占位符
            r'data:image',  # 数据URL通常是占位符
        ]
        
        is_placeholder = False
        for pattern in placeholder_patterns:
            if re.search(pattern, book.cover_url.lower()):
                is_placeholder = True
                break
        
        if not is_placeholder:
            cover_url = book.cover_url
    
    # 如果没有有效的封面URL，使用默认封面
    if not cover_url:
        cover_url = default_cover
    
    return cover_url
