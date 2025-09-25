
# Python Private RSS subscription

python结合feedparser模块编写的终端私人RSS订阅程序




## 截图

![rss](rss.jpg)


## 在本地运行

Clone 这个 project

```bash
  git clone https://github.com/bosichong/python_rss_subscription
```

前往项目目录

```bash
  cd python_rss_subscription
```

安装依赖

```bash
  pip install -r requirements.txt
```

启动程序

```bash
  python main.py
```


## 使用方法

1. 编辑config.json文件中的rss_feeds数组，修改成自己喜欢的RSS源
2. 可以调整其他配置参数：
   - weeks_limit: 限制获取多少周内的文章（默认为1周）
   - max_workers: 最大并发线程数（默认为5）
   - request_timeout: 网络请求超时时间（秒，默认为30）


## 作者

- [@octokatherine](https://github.com/bosichong/python_rss_subscription)

- [@我的博客](https://suiyan.cc)

