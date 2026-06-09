"""获取个股相关新闻"""
import json
import re
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import urllib.request

HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}


def get_stock_news(code: str, limit: int = 15) -> list:
    """从同花顺获取个股新闻"""
    url = f"https://news.10jqka.com.cn/tapp/news/push/stock/?page=1&tag=&track=website&pagesize={limit}&code={code}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception:
        return get_market_news(limit)

    news_list = []
    items = data.get('data', {}).get('list', []) if data.get('data') else []
    for item in items[:limit]:
        title = item.get('title', '')
        if not title:
            continue
        news_list.append({
            'title': title,
            'time': item.get('ctime', ''),
            'source': '同花顺',
            'url': item.get('url', ''),
        })

    return news_list if news_list else get_market_news(limit)


def get_market_news(limit: int = 20) -> list:
    """同花顺市场快讯"""
    url = f"https://news.10jqka.com.cn/tapp/news/push/stock/?page=1&tag=&track=website&pagesize={limit}&code="
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception:
        return []

    news_list = []
    items = data.get('data', {}).get('list', []) if data.get('data') else []
    for item in items[:limit]:
        title = item.get('title', '')
        if not title:
            continue
        news_list.append({
            'title': title,
            'time': item.get('ctime', ''),
            'source': '同花顺',
            'url': item.get('url', ''),
        })

    return news_list


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        code = query.get('code', [''])[0].strip()

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        if code:
            result = get_stock_news(code)
        else:
            result = get_market_news()

        self.wfile.write(json.dumps(result, ensure_ascii=False).encode())
