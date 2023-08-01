
import feedparser

d = feedparser.parse('https://suiyan.cc/rss')
# print(d.feed)
print(d.feed.title)
print(d.feed.link)
print(d.entries)
for data in d.entries:
    print("title:"+data.title)
    print("description:" + data.description)
    print("link:" + data.link)
    print("---------------------------------------------")

