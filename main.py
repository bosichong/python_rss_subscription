import webbrowser
import logging
import sys
from rss_core import load_config, RSSFetcher, format_time, get_domain

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
        url = article.get('source', get_domain(article['link']))
        
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



def main():
    """主函数"""
    # 打印欢迎界面
    print_color("\n" + "╔" + "═" * 78 + "╗", Colors.CYAN)
    print_color("║" + " " * 78 + "║", Colors.CYAN)
    print_color("║" + " " * 31 + "RSS 订阅阅读器" + " " * 31 + "║", Colors.BOLD + Colors.CYAN)
    print_color("║" + " " * 78 + "║", Colors.CYAN)
    print_color("╚" + "═" * 78 + "╝\n", Colors.CYAN)
    
    # 加载配置
    config = load_config()
    
    # 创建 RSS 获取器
    fetcher = RSSFetcher(config)
    
    # 设置进度回调
    total_feeds = len(fetcher.rss_feeds)
    completed_feeds = 0
    
    def progress_callback(feed_url, status, progress):
        nonlocal completed_feeds
        if status == "completed":
            completed_feeds += 1
            bar_length = 30
            filled_length = int(bar_length * progress / 100)
            bar = '=' * filled_length + '-' * (bar_length - filled_length)
            sys.stdout.write(f"\r{Colors.CYAN}进度: {bar} {progress:.1f}% ({completed_feeds}/{total_feeds}){Colors.RESET}")
            sys.stdout.flush()
            print(f"\n{Colors.GREEN}[OK]{Colors.RESET} 完成: {get_domain(feed_url)}")
        elif status == "error":
            print(f"\n{Colors.RED}[FAIL]{Colors.RESET} 失败: {get_domain(feed_url)}")
    
    fetcher.set_progress_callback(progress_callback)
    
    print_color("正在获取最新文章，请稍候...", Colors.YELLOW)
    print_color("-" * 80, Colors.CYAN)
    print()
    
    # 采集最新文章
    articles = fetcher.fetch_all_articles()
    
    # 按相对时间降序排序（最新的在前）
    try:
        from email.utils import parsedate_to_datetime
        from datetime import datetime
        
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
    except Exception as e:
        pass  # 排序失败不影响程序运行
    
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
                webbrowser.open(selected_article['link'])
                print_color(f"[OK] 已在浏览器中打开: {selected_article['title']}", Colors.GREEN)
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
