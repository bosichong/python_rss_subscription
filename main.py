from concurrent.futures import ThreadPoolExecutor

import feedparser
import webbrowser
import os
from datetime import datetime, timedelta

# 定义你喜欢的博客的RSS链接地址，放入一个数组中
rss_feeds = [
    'https://hutusi.com/feed.xml',
    'https://scarsu.com/rss',
    'https://www.demochen.com/atom.xml',
    'https://onojyun.com/feed/',
    'https://hux6.com/feed/',
    'https://atjason.com/atom.xml',
    'https://www.ruanyifeng.com/blog/atom.xml',
    # 添加更多博客的RSS链接
]


def fetch_articles_from_feed(feed_url, one_week_ago):
    articles = []
    print("开始解析:"+feed_url)
    feed = feedparser.parse(feed_url)
    if 'entries' in feed:
        for entry in feed.entries:
            published_time = datetime(*entry.published_parsed[:6])
            if published_time >= one_week_ago:
                article = {
                    'title': entry.get('title', ''),
                    'link': entry.get('link', ''),
                    'published': entry.get('published', ''),
                    # 可以根据需要提取更多信息，如作者、摘要等
                }
                articles.append(article)
    print("解析完成！" + feed_url)
    return articles


def fetch_latest_articles(rss_feeds):
    articles = []
    one_week_ago = datetime.now() - timedelta(weeks=1)

    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(fetch_articles_from_feed, feed_url, one_week_ago) for feed_url in rss_feeds]

        for future in futures:
            articles.extend(future.result())

    return articles


def display_articles(articles):
    if not articles:
        print("没有找到一周内的文章。")
        return

    for index, article in enumerate(articles, start=1):
        print(f"{index}. {article['title']}")


def open_article_in_browser(article):
    webbrowser.open(article['link'])


if __name__ == "__main__":
    # 采集最新文章并保存到数组中
    articles = fetch_latest_articles(rss_feeds)

    # 在终端输出文章列表
    display_articles(articles)

    # 等待用户输入选择哪篇文章查看
    while True:
        try:
            choice = int(input("输入文章编号查看详情（输入0退出）: "))
            if choice == 0:
                break
            elif 1 <= choice <= len(articles):
                selected_article = articles[choice - 1]
                open_article_in_browser(selected_article)
            else:
                print("无效的选择，请重新输入。")
        except ValueError:
            print("无效的输入，请输入文章编号的数字。")
