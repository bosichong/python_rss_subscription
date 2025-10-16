import feedparser
import webbrowser
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import logging
import json
import os
from urllib.parse import urlparse

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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


def fetch_articles_from_feed(feed_url, one_week_ago):
    """从单个RSS源获取一周内的文章"""
    articles = []
    print("开始解析:" + feed_url)
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
        print("解析完成！" + feed_url)
        logger.info(f"成功解析RSS源: {feed_url}, 获取到 {len(articles)} 篇文章")
    except requests.RequestException as e:
        error_msg = f"网络请求错误 {feed_url}: {str(e)}"
        print(error_msg)
        logger.error(error_msg)
    except Exception as e:
        error_msg = f"解析{feed_url}出错：{str(e)}"
        print(error_msg)
        logger.error(error_msg)
        
    return articles


def fetch_latest_articles(rss_feeds):
    """从所有RSS源获取最新文章"""
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
                print(error_msg)
                logger.error(error_msg)

    logger.info(f"总共获取到 {len(articles)} 篇文章")
    return articles


def display_articles(articles):
    """显示文章列表"""
    if not articles:
        print("没有找到一周内的文章。")
        return

    print(f"\n找到 {len(articles)} 篇文章：\n")
    for index, article in enumerate(articles, start=1):
        # 截取过长的标题
        title = article['title']
        url = get_domain(article['link'])
        if len(title) > 80:
            title = title[:77] + "..."
        print(f"{index:2d}. {title} {url}")


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



def open_article_in_browser(article):
    """在浏览器中打开文章"""
    webbrowser.open(article['link'])
    print(f"已在浏览器中打开: {article['title']}")


def main():
    """主函数"""
    print("正在获取最新文章，请稍候...")
    
    # 采集最新文章并保存到数组中
    articles = fetch_latest_articles(rss_feeds)

    # 在终端输出文章列表
    display_articles(articles)

    if not articles:
        return

    # 等待用户输入选择哪篇文章查看
    while True:
        try:
            choice = input("\n输入文章编号查看详情（输入0退出）: ").strip()
            if choice == "0":
                print("再见！")
                break
            elif choice.isdigit() and 1 <= int(choice) <= len(articles):
                selected_article = articles[int(choice) - 1]
                open_article_in_browser(selected_article)
                # 重新显示文章列表
                display_articles(articles)
            else:
                print("无效的选择，请重新输入。")
        except KeyboardInterrupt:
            print("\n\n程序被用户中断，再见！")
            break
        except Exception as e:
            print(f"发生错误: {str(e)}")


if __name__ == "__main__":
    main()
