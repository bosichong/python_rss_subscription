import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import webbrowser
from rss_core import load_config, save_config, RSSFetcher, format_time, get_domain

class RSSReaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("RSS 订阅阅读器")
        self.root.geometry("1000x700")
        
        # 初始化变量
        self.articles = []
        self.current_feed_index = 0
        self.is_fetching = False
        
        # 加载配置
        self.config = load_config()
        self.rss_feeds = self.config.get('rss_feeds', [])
        self.weeks_limit = self.config.get('weeks_limit', 1)
        self.max_workers = self.config.get('max_workers', 5)
        self.request_timeout = self.config.get('request_timeout', 30)
        
        # 创建 RSS 获取器
        self.fetcher = RSSFetcher(self.config)
        
        # 创建界面
        self.create_widgets()
    
    def create_widgets(self):
        """创建界面组件"""
        # 创建主框架
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(1, weight=1)
        
        # 标题
        title_label = ttk.Label(
            self.main_frame, 
            text="RSS 订阅阅读器", 
            font=('Arial', 16, 'bold')
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        
        # 控制面板
        control_frame = ttk.LabelFrame(self.main_frame, text="控制面板", padding="10")
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        # 刷新按钮
        self.refresh_btn = ttk.Button(
            control_frame, 
            text="刷新文章", 
            command=self.start_fetch_articles
        )
        self.refresh_btn.pack(fill=tk.X, pady=(0, 5))
        
        # 配置按钮
        ttk.Button(
            control_frame, 
            text="配置设置", 
            command=self.open_config_window
        ).pack(fill=tk.X, pady=(0, 5))
        
        # RSS 源列表
        ttk.Label(control_frame, text="RSS 源列表:").pack(anchor=tk.W, pady=(10, 5))
        
        self.feeds_listbox = tk.Listbox(control_frame, height=15)
        self.feeds_listbox.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # 滚动条
        scrollbar = ttk.Scrollbar(control_frame, orient=tk.VERTICAL, command=self.feeds_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.feeds_listbox.config(yscrollcommand=scrollbar.set)
        
        # 添加/删除 RSS 源按钮
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(btn_frame, text="添加", command=self.add_feed).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        ttk.Button(btn_frame, text="删除", command=self.remove_feed).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))
        
        # 文章列表面板
        articles_frame = ttk.LabelFrame(self.main_frame, text="文章列表", padding="10")
        articles_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        articles_frame.columnconfigure(0, weight=1)
        articles_frame.rowconfigure(0, weight=1)
        
        # 创建 Treeview 显示文章
        columns = ('title', 'source', 'time')
        self.articles_tree = ttk.Treeview(articles_frame, columns=columns, show='headings', selectmode='browse')
        
        self.articles_tree.heading('title', text='标题')
        self.articles_tree.heading('source', text='来源')
        self.articles_tree.heading('time', text='时间')
        
        self.articles_tree.column('title', width=400)
        self.articles_tree.column('source', width=150)
        self.articles_tree.column('time', width=100)
        
        self.articles_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 文章列表滚动条
        articles_scrollbar = ttk.Scrollbar(articles_frame, orient=tk.VERTICAL, command=self.articles_tree.yview)
        articles_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.articles_tree.config(yscrollcommand=articles_scrollbar.set)
        
        # 双击打开文章
        self.articles_tree.bind('<Double-1>', self.open_article)
        
        # 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        status_bar = ttk.Label(self.main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # 加载 RSS 源列表
        self.load_feeds_list()
        
    def load_feeds_list(self):
        """加载 RSS 源列表"""
        self.feeds_listbox.delete(0, tk.END)
        for feed in self.rss_feeds:
            self.feeds_listbox.insert(tk.END, get_domain(feed))
    
    def add_feed(self):
        """添加 RSS 源"""
        feed_url = tk.simpledialog.askstring("添加 RSS 源", "请输入 RSS 源 URL:")
        if feed_url:
            self.rss_feeds.append(feed_url)
            self.load_feeds_list()
            self.save_config()
    
    def remove_feed(self):
        """删除 RSS 源"""
        selection = self.feeds_listbox.curselection()
        if selection:
            index = selection[0]
            del self.rss_feeds[index]
            self.load_feeds_list()
            self.save_config()
    
    def save_config(self):
        """保存配置"""
        config = {
            'rss_feeds': self.rss_feeds,
            'weeks_limit': self.weeks_limit,
            'max_workers': self.max_workers,
            'request_timeout': self.request_timeout
        }
        if not save_config(config):
            messagebox.showerror("错误", "保存配置失败")
    
    def open_config_window(self):
        """打开配置窗口"""
        config_window = tk.Toplevel(self.root)
        config_window.title("配置设置")
        config_window.geometry("400x300")
        
        frame = ttk.Frame(config_window, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 周数限制
        ttk.Label(frame, text="获取文章周数:").grid(row=0, column=0, sticky=tk.W, pady=5)
        weeks_var = tk.StringVar(value=str(self.weeks_limit))
        ttk.Entry(frame, textvariable=weeks_var, width=10).grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # 最大并发数
        ttk.Label(frame, text="最大并发数:").grid(row=1, column=0, sticky=tk.W, pady=5)
        workers_var = tk.StringVar(value=str(self.max_workers))
        ttk.Entry(frame, textvariable=workers_var, width=10).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # 请求超时
        ttk.Label(frame, text="请求超时(秒):").grid(row=2, column=0, sticky=tk.W, pady=5)
        timeout_var = tk.StringVar(value=str(self.request_timeout))
        ttk.Entry(frame, textvariable=timeout_var, width=10).grid(row=2, column=1, sticky=tk.W, pady=5)
        
        def save_and_close():
            try:
                self.weeks_limit = int(weeks_var.get())
                self.max_workers = int(workers_var.get())
                self.request_timeout = int(timeout_var.get())
                self.save_config()
                # 更新 fetcher 的配置
                self.fetcher.weeks_limit = self.weeks_limit
                self.fetcher.max_workers = self.max_workers
                self.fetcher.request_timeout = self.request_timeout
                config_window.destroy()
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数字")
        
        ttk.Button(frame, text="保存", command=save_and_close).grid(row=3, column=0, columnspan=2, pady=20)
    
    def start_fetch_articles(self):
        """开始获取文章（在新线程中）"""
        if self.is_fetching:
            messagebox.showwarning("警告", "正在获取文章，请稍候...")
            return
        
        if not self.rss_feeds:
            messagebox.showwarning("警告", "请先添加 RSS 源")
            return
        
        self.is_fetching = True
        self.refresh_btn.config(state=tk.DISABLED)
        self.status_var.set("正在获取文章...")
        
        # 清空当前文章列表
        for item in self.articles_tree.get_children():
            self.articles_tree.delete(item)
        
        # 在新线程中获取文章
        thread = threading.Thread(target=self.fetch_articles)
        thread.daemon = True
        thread.start()
    
    def fetch_articles(self):
        """获取文章"""
        try:
            # 设置进度回调
            def progress_callback(feed_url, status, progress):
                if status == 'processing':
                    self.root.after(0, lambda f=feed_url: self.update_progress(progress, f))
                elif status == 'completed':
                    self.root.after(0, lambda p=progress, f=feed_url: self.update_progress(p, f))
                elif status == 'error':
                    self.root.after(0, lambda f=feed_url: self.status_var.set(f"错误: {f}"))
            
            self.fetcher.set_progress_callback(progress_callback)
            
            # 获取文章
            articles = self.fetcher.fetch_all_articles()
            
            # 更新文章列表
            self.articles = articles
            self.root.after(0, self.display_articles)
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"获取文章失败: {str(e)}"))
        finally:
            self.is_fetching = False
            self.root.after(0, lambda: self.refresh_btn.config(state=tk.NORMAL))
    
    def update_progress(self, progress, feed_url):
        """更新进度"""
        self.status_var.set(f"正在获取: {get_domain(feed_url)} ({progress:.1f}%)")
    
    def display_articles(self):
        """显示文章列表"""
        # 清空现有列表
        for item in self.articles_tree.get_children():
            self.articles_tree.delete(item)
        
        # 添加新文章
        for article in self.articles:
            title = article['title']
            if len(title) > 50:
                title = title[:47] + "..."
            
            time_str = format_time(article['published'])
            
            self.articles_tree.insert('', tk.END, values=(
                title,
                article['source'],
                time_str
            ))
        
        self.status_var.set(f"找到 {len(self.articles)} 篇文章")
    
    def open_article(self, event):
        """在浏览器中打开文章"""
        selection = self.articles_tree.selection()
        if selection:
            item = self.articles_tree.item(selection[0])
            title = item['values'][0]
            
            # 查找对应的完整文章信息
            for article in self.articles:
                if article['title'].startswith(title.replace('...', '')):
                    webbrowser.open(article['link'])
                    self.status_var.set(f"已打开: {article['title']}")
                    break


def main():
    root = tk.Tk()
    app = RSSReaderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()