"""获取个股相关新闻"""
import json
import re
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import urllib.request

HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}


def get_stock_news(code: str, limit: int = 15) -> list:
    """从新浪获取个股新闻（HTML解析）"""
    if code.startswith('6') or code.startswith('9'):
        symbol = f"sh{code}"
    else:
        symbol = f"sz{code}"

    url = f"https://vip.stock.finance.sina.com.cn/corp/view/vCB_AllNewsStock.php?symbol={symbol}&Page=1"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode('gbk', errors='ignore')
    except Exception:
        return get_market_news(limit)

    news_list = []
    items = re.findall(
        r'<a href="(https?://[^"]+)"[^>]*target="_blank">([^<]+)</a>.*?(\d{4}-\d{2}-\d{2})',
        text, re.DOTALL
    )
    if not items:
        items = re.findall(
            r'(\d{4}-\d{2}-\d{2}).*?<a href="(https?://[^"]+)"[^>]*>([^<]+)</a>',
            text
        )
        items = [(url_val, title, date) for date, url_val, title in items]

    for item_url, title, date in items[:limit]:
        title = title.strip()
        if not title or title in ('财经首页', '股票', '基金', '港股', '美股'):
            continue
        news_list.append({
            'title': title,
            'time': date,
            'source': '新浪财经',
            'url': item_url,
        })

    return news_list[:limit] if news_list else get_market_news(limit)


def get_market_news(limit: int = 20) -> list:
    """东方财富市场快讯"""
    url = "https://newsapi.eastmoney.com/kuaixun/v1/getlist_102_ajaxResult_50_1_.html"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode()
    except Exception:
        return []

    match = re.search(r'ajaxResult=(\{.*\})', text)
    if not match:
        return []

    try:
        data = json.loads(match.group(1))
    except Exception:
        return []

    news_list = []
    items = data.get('LivesList', data.get('Data', []))
    for item in items[:limit]:
        news_list.append({
            'title': item.get('Title', item.get('title', '')),
            'time': item.get('ShowTime', item.get('time', '')),
            'source': '东方财富',
            'url': '',
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
