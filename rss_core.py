import feedparser
import requests
import json
import os
from datetime import datetime, timedelta
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.utils import parsedate_to_datetime
import re


def load_config():
    """加载配置文件"""
    config_path = 'config.json'
    default_config = {
        'rss_feeds': [
            'https://hutusi.com/feed.xml',
            'https://scarsu.com/rss',
            'https://www.demochen.com/atom.xml',
            'https://onojyun.com/feed/',
            'https://hux6.com/feed/',
            'https://atjason.com/atom.xml',
            'https://www.ruanyifeng.com/blog/atom.xml',
        ],
        'weeks_limit': 1,
        'max_workers': 5,
        'request_timeout': 30
    }
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            # 合并默认配置和用户配置
            final_config = default_config.copy()
            final_config.update(config)
            return final_config
        except Exception as e:
            print(f"配置文件加载失败: {str(e)}，使用默认配置")
            return default_config
    else:
        print("配置文件不存在，使用默认配置")
        return default_config


def save_config(config):
    """保存配置文件"""
    try:
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"保存配置失败: {str(e)}")
        return False


def get_domain(url):
    """从 URL 中提取域名"""
    if not url.startswith(('http://', 'https://')):
        parsed = urlparse('http://' + url)
    else:
        parsed = urlparse(url)
    return parsed.netloc


def format_time(published_str):
    """格式化时间为相对时间
    
    Args:
        published_str (str): 时间字符串，支持多种格式
        
    Returns:
        str: 相对时间字符串（如"3天前"、"2小时前"）或日期
    """
    if not published_str:
        return ""
        
    published_time = None
    
    # 尝试多种解析方式
    try:
        published_time = parsedate_to_datetime(published_str)
    except:
        try:
            # 尝试使用 feedparser 的时间解析
            parsed = feedparser.parse(published_str)
            if parsed and isinstance(parsed, dict) and 'published_parsed' in parsed:
                published_time = datetime(*parsed['published_parsed'][:6])
        except:
            pass
    
    # 如果所有解析方式都失败，尝试直接解析 ISO 格式
    if published_time is None:
        try:
            # 处理 ISO 8601 格式 (如: 2026-01-09T00:11:26Z)
            if 'T' in published_str:
                match = re.match(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', published_str)
                if match:
                    published_time = datetime.fromisoformat(match.group(1))
        except:
            pass
    
    # 如果成功解析时间，计算相对时间
    if published_time:
        try:
            # 如果有时区信息，使用时区；否则使用本地时间
            if hasattr(published_time, 'tzinfo') and published_time.tzinfo:
                now = datetime.now(published_time.tzinfo)
            else:
                now = datetime.now()
            
            delta = now - published_time
            
            total_seconds = int(delta.total_seconds())
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            minutes = (total_seconds % 3600) // 60
            
            if days > 0:
                if days >= 7:
                    weeks = days // 7
                    return f"{weeks}周前"
                return f"{days}天前"
            elif hours > 0:
                return f"{hours}小时前"
            elif minutes > 0:
                return f"{minutes}分钟前"
            else:
                return "刚刚"
        except:
            pass
    
    # 如果所有方式都失败，尝试提取日期部分
    try:
        # 尝试提取 YYYY-MM-DD 格式的日期
        match = re.search(r'(\d{4}-\d{2}-\d{2})', published_str)
        if match:
            return match.group(1)
    except:
        pass
    
    # 最后返回原始字符串，但限制长度
    if len(published_str) > 20:
        return published_str[:20] + "..."
    return published_str


class RSSFetcher:
    """RSS 文章获取器"""
    
    def __init__(self, config=None):
        """
        初始化 RSS 获取器
        
        Args:
            config: 配置字典，如果为None则从文件加载
        """
        if config is None:
            self.config = load_config()
        else:
            self.config = config
            
        self.rss_feeds = self.config.get('rss_feeds', [])
        self.weeks_limit = self.config.get('weeks_limit', 1)
        self.max_workers = self.config.get('max_workers', 5)
        self.request_timeout = self.config.get('request_timeout', 30)
        
        # 进度回调函数
        self.progress_callback = None
    
    def set_progress_callback(self, callback):
        """设置进度回调函数
        
        Args:
            callback: 回调函数，接收参数 (feed_url, status, progress)
                     status: 'processing', 'completed', 'error'
                     progress: 进度百分比 (0-100)
        """
        self.progress_callback = callback
    
    def _update_progress(self, feed_url, status, progress):
        """更新进度"""
        if self.progress_callback:
            self.progress_callback(feed_url, status, progress)
    
    def fetch_articles_from_feed(self, feed_url, one_week_ago):
        """从单个 RSS 源获取文章
        
        Args:
            feed_url: RSS 源 URL
            one_week_ago: 时间截止点
            
        Returns:
            list: 文章列表
        """
        articles = []
        self._update_progress(feed_url, 'processing', 0)
        
        try:
            response = requests.get(feed_url, timeout=self.request_timeout)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            
            if 'entries' in feed:
                for entry in feed.entries:
                    # 优先使用 published_parsed，其次使用 updated_parsed
                    published_time = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published_time = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        published_time = datetime(*entry.updated_parsed[:6])
                    
                    if published_time and published_time >= one_week_ago:
                        article = {
                            'title': entry.get('title', ''),
                            'link': entry.get('link', ''),
                            'published': entry.get('published', entry.get('updated', '')),
                            'source': get_domain(feed_url)
                        }
                        articles.append(article)
            
            self._update_progress(feed_url, 'completed', 100)
            
        except requests.RequestException as e:
            self._update_progress(feed_url, 'error', 0)
            print(f"网络请求错误 {feed_url}: {str(e)}")
        except Exception as e:
            self._update_progress(feed_url, 'error', 0)
            print(f"解析 {feed_url} 出错：{str(e)}")
        
        return articles
    
    def fetch_all_articles(self):
        """从所有 RSS 源获取文章
        
        Returns:
            list: 所有文章列表
        """
        articles = []
        one_week_ago = datetime.now() - timedelta(weeks=self.weeks_limit)
        
        total_feeds = len(self.rss_feeds)
        completed_feeds = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_feed = {
                executor.submit(self.fetch_articles_from_feed, feed_url, one_week_ago): feed_url 
                for feed_url in self.rss_feeds
            }
            
            for future in as_completed(future_to_feed):
                feed_url = future_to_feed[future]
                try:
                    feed_articles = future.result()
                    articles.extend(feed_articles)
                    completed_feeds += 1
                    progress = (completed_feeds / total_feeds) * 100
                    self._update_progress(feed_url, 'completed', progress)
                except Exception as e:
                    print(f"处理 {feed_url} 的结果时出错：{str(e)}")
        
        # 按相对时间降序排序（最新的在前）
        def get_seconds_ago(article):
            pub = article.get('published', '')
            if not pub:
                return float('inf')
            try:
                pub_time = parsedate_to_datetime(pub)
                # 转换为本地时间
                if hasattr(pub_time, 'tzinfo') and pub_time.tzinfo:
                    now = datetime.now(pub_time.tzinfo)
                else:
                    now = datetime.now()
                delta = now - pub_time
                return delta.total_seconds()
            except:
                return float('inf')
        
        articles.sort(key=get_seconds_ago)
        
        return articles