import feedparser
import webbrowser
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import logging
import json
import os
import sys
from urllib.parse import urlparse

# Windows 终端颜色支持
if sys.platform == 'win32':
    try:
        from colorama import init
        init()
    except ImportError:
        pass

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ANSI颜色代码
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_color(text, color=Colors.RESET):
    """打印带颜色的文本"""
    print(f"{color}{text}{Colors.RESET}")

# 默认配置
DEFAULT_CONFIG = {
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

def load_config():
    """加载配置文件"""
    config_path = 'config.json'
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            # 合并默认配置和用户配置
            final_config = DEFAULT_CONFIG.copy()
            final_config.update(config)
            logger.info("配置文件加载成功")
            return final_config
        except Exception as e:
            logger.error(f"配置文件加载失败: {str(e)}，使用默认配置")
            return DEFAULT_CONFIG
    else:
        logger.info("配置文件不存在，使用默认配置")
        return DEFAULT_CONFIG

# 加载配置
config = load_config()
rss_feeds = config['rss_feeds']
weeks_limit = config['weeks_limit']
max_workers = config['max_workers']
request_timeout = config['request_timeout']

# 全局变量用于进度跟踪
total_feeds = len(rss_feeds)
completed_feeds = 0
current_feed_url = ""

def update_progress(feed_url, status="processing"):
    """更新进度显示"""
    global completed_feeds, current_feed_url
    current_feed_url = feed_url
    
    if status == "completed":
        completed_feeds += 1
    
    # 计算进度百分比
    progress = (completed_feeds / total_feeds) * 100
    bar_length = 30
    filled_length = int(bar_length * progress / 100)
    bar = '=' * filled_length + '-' * (bar_length - filled_length)
    
    # 清除当前行并显示进度
    sys.stdout.write('\r')
    sys.stdout.write(f"{Colors.CYAN}进度: {bar} {progress:.1f}% ({completed_feeds}/{total_feeds}){Colors.RESET}")
    sys.stdout.flush()
    
    if status == "completed":
        print(f"\n{Colors.GREEN}[OK]{Colors.RESET} 完成: {get_domain(feed_url)}")
    elif status == "error":
        print(f"\n{Colors.RED}[FAIL]{Colors.RESET} 失败: {get_domain(feed_url)}")
    
    if status == "processing":
        print(f"{Colors.YELLOW}[...]{Colors.RESET} 正在解析: {get_domain(feed_url)}")


def fetch_articles_from_feed(feed_url, one_week_ago):
    """从单个RSS源获取一周内的文章"""
    articles = []
    update_progress(feed_url, "processing")
    logger.info(f"开始解析RSS源: {feed_url}")
    
    try:
        # 使用requests设置超时，而不是手动线程管理
        response = requests.get(feed_url, timeout=request_timeout)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        
        if 'entries' in feed:
            for entry in feed.entries:
                # 处理可能缺失的published_parsed字段
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published_time = datetime(*entry.published_parsed[:6])
                    if published_time >= one_week_ago:
                        article = {
                            'title': entry.get('title', ''),
                            'link': entry.get('link', ''),
                            'published': entry.get('published', ''),
                            # 可以根据需要提取更多信息，如作者、摘要等
                        }
                        articles.append(article)
                else:
                    # 如果没有published_parsed，尝试使用updated_parsed
                    if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        updated_time = datetime(*entry.updated_parsed[:6])
                        if updated_time >= one_week_ago:
                            article = {
                                'title': entry.get('title', ''),
                                'link': entry.get('link', ''),
                                'published': entry.get('updated', ''),
                            }
                            articles.append(article)
        update_progress(feed_url, "completed")
        logger.info(f"成功解析RSS源: {feed_url}, 获取到 {len(articles)} 篇文章")
    except requests.RequestException as e:
        error_msg = f"网络请求错误 {feed_url}: {str(e)}"
        update_progress(feed_url, "error")
        logger.error(error_msg)
    except Exception as e:
        error_msg = f"解析{feed_url}出错：{str(e)}"
        update_progress(feed_url, "error")
        logger.error(error_msg)
        
    return articles


def fetch_latest_articles(rss_feeds):
    """从所有RSS源获取最新文章"""
    global completed_feeds
    completed_feeds = 0  # 重置进度
    
    articles = []
    one_week_ago = datetime.now() - timedelta(weeks=weeks_limit)
    logger.info(f"开始获取最近{weeks_limit}周的文章")

    # 使用ThreadPoolExecutor并行处理所有RSS源
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_feed = {
            executor.submit(fetch_articles_from_feed, feed_url, one_week_ago): feed_url 
            for feed_url in rss_feeds
        }
        
        # 收集结果
        for future in as_completed(future_to_feed):
            feed_url = future_to_feed[future]
            try:
                feed_articles = future.result()
                articles.extend(feed_articles)
            except Exception as e:
                error_msg = f"处理{feed_url}的结果时出错：{str(e)}"
                print_color(error_msg, Colors.RED)
                logger.error(error_msg)

    logger.info(f"总共获取到 {len(articles)} 篇文章")
    return articles


def display_articles(articles):
    """显示文章列表"""
    if not articles:
        print_color("\n没有找到一周内的文章。", Colors.YELLOW)
        return

    # 打印分隔线
    print_color("\n" + "=" * 80, Colors.CYAN)
    print_color(f"  找到 {len(articles)} 篇文章", Colors.BOLD + Colors.GREEN)
    print_color("=" * 80, Colors.CYAN)
    print()
    
    for index, article in enumerate(articles, start=1):
        # 截取过长的标题
        title = article['title']
        url = get_domain(article['link'])
        
        # 计算可用长度（总宽度100 - 序号 - 网址 - 时间 - 分隔符）
        max_title_length = 60
        if len(title) > max_title_length:
            title = title[:max_title_length - 3] + "..."
        
        # 格式化时间
        time_str = ""
        if 'published' in article and article['published']:
            relative_time = format_time(article['published'])
            time_str = f" {Colors.YELLOW}[{relative_time}]{Colors.RESET}"
        
        # 格式化输出 - 同一行显示
        print(f"{Colors.BLUE}{index:3d}.{Colors.RESET} {Colors.BOLD}{title}{Colors.RESET}  {Colors.CYAN}[{url}]{Colors.RESET}{time_str}")


def get_domain(url: str) -> str:
    """
    从给定的网址中提取域名。

    Args:
        url (str): 完整的网址 (e.g., 'https://www.example.com/page')

    Returns:
        str: 提取出的域名 (e.g., 'www.example.com')
        
    Raises:
        ValueError: 如果输入的 URL 格式无效。
    """
    # 如果 URL 没有协议前缀，则添加一个默认的协议前缀
    # urlparse 需要协议才能正确解析
    if not url.startswith(('http://', 'https://')):
        # 尝试添加 http:// 前缀进行解析
        parsed = urlparse('http://' + url)
    else:
        parsed = urlparse(url)

    # 检查是否存在有效的网络位置 (netloc)
    if not parsed.netloc:
        raise ValueError(f"无效的网址格式: '{url}'")

    # 返回域名部分 (netloc)
    return parsed.netloc


def format_time(published_str):
    """
    将RFC 2822格式的时间转换为中文友好的相对时间格式
    
    Args:
        published_str (str): RFC 2822格式的时间字符串 (e.g., 'Wed, 31 Dec 2025 02:04:27 +0000')
    
    Returns:
        str: 相对时间字符串 (e.g., '5天前', '2小时前', '刚刚')
    """
    try:
        # 使用email.utils的parsedate_to_datetime来解析时间
        from email.utils import parsedate_to_datetime
        published_time = parsedate_to_datetime(published_str)
        
        # 计算时间差
        now = datetime.now(published_time.tzinfo)
        delta = now - published_time
        
        # 转换为天数、小时、分钟
        total_seconds = int(delta.total_seconds())
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        
        # 返回相对时间
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
    except Exception as e:
        # 如果解析失败，返回原始字符串
        return published_str



def open_article_in_browser(article):
    """在浏览器中打开文章"""
    webbrowser.open(article['link'])
    print_color(f"[OK] 已在浏览器中打开: {article['title']}", Colors.GREEN)


def main():
    """主函数"""
    # 打印欢迎界面
    print_color("\n" + "╔" + "═" * 78 + "╗", Colors.CYAN)
    print_color("║" + " " * 78 + "║", Colors.CYAN)
    print_color("║" + " " * 31 + "RSS 订阅阅读器" + " " * 31 + "║", Colors.BOLD + Colors.CYAN)
    print_color("║" + " " * 78 + "║", Colors.CYAN)
    print_color("╚" + "═" * 78 + "╝\n", Colors.CYAN)
    
    print_color("正在获取最新文章，请稍候...", Colors.YELLOW)
    print_color("-" * 80, Colors.CYAN)
    print()
    
    # 采集最新文章并保存到数组中
    articles = fetch_latest_articles(rss_feeds)
    
    print()
    print_color("-" * 80, Colors.CYAN)

    # 在终端输出文章列表
    display_articles(articles)

    if not articles:
        return

    # 等待用户输入选择哪篇文章查看
    while True:
        try:
            choice = input(f"\n{Colors.GREEN}输入文章编号查看详情（输入0退出）: {Colors.RESET}").strip()
            if choice == "0":
                print_color("\n再见！", Colors.YELLOW)
                break
            elif choice.isdigit() and 1 <= int(choice) <= len(articles):
                selected_article = articles[int(choice) - 1]
                print_color(f"\n正在打开: {selected_article['title']}", Colors.CYAN)
                open_article_in_browser(selected_article)
                # 重新显示文章列表
                display_articles(articles)
            else:
                print_color("无效的选择，请重新输入。", Colors.RED)
        except KeyboardInterrupt:
            print_color("\n\n程序被用户中断，再见！", Colors.YELLOW)
            break
        except Exception as e:
            print_color(f"发生错误: {str(e)}", Colors.RED)


if __name__ == "__main__":
    main()
