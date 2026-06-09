"""获取个股相关新闻"""
import json
import re
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import urllib.request

HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}


def get_stock_news(code: str, limit: int = 15) -> list:
    """从东方财富获取个股新闻"""
    if code.startswith('6') or code.startswith('9'):
        market = '1'
    else:
        market = '0'

    url = (
        f"https://search-api-web.eastmoney.com/search/jsonp?"
        f"cb=cb&param=%7B%22uid%22%3A%22%22%2C%22keyword%22%3A%22{code}%22%2C"
        f"%22type%22%3A%5B%22cmsArticleWebOld%22%5D%2C%22client%22%3A%22web%22%2C"
        f"%22clientType%22%3A%22web%22%2C%22clientVersion%22%3A%22curr%22%2C"
        f"%22param%22%3A%7B%22cmsArticleWebOld%22%3A%7B%22searchScope%22%3A%22default%22%2C"
        f"%22sort%22%3A%22default%22%2C%22pageIndex%22%3A1%2C%22pageSize%22%3A{limit}%2C"
        f"%22preTag%22%3A%22%22%2C%22postTag%22%3A%22%22%7D%7D%7D"
    )

    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode()
    except Exception:
        return get_eastmoney_stock_news(code, market, limit)

    match = re.search(r'cb\((\{.*\})\)', text, re.DOTALL)
    if not match:
        return get_eastmoney_stock_news(code, market, limit)

    try:
        data = json.loads(match.group(1))
    except Exception:
        return get_eastmoney_stock_news(code, market, limit)

    news_list = []
    results = data.get('result', {})
    articles = results.get('cmsArticleWebOld', {}).get('list', [])

    for item in articles[:limit]:
        title = item.get('title', '').replace('<em>', '').replace('</em>', '')
        if not title:
            continue
        news_list.append({
            'title': title,
            'time': item.get('date', ''),
            'source': item.get('mediaName', '东方财富'),
            'url': item.get('url', ''),
        })

    return news_list if news_list else get_eastmoney_stock_news(code, market, limit)


def get_eastmoney_stock_news(code: str, market: str, limit: int = 15) -> list:
    """东方财富个股资讯接口（备用）"""
    url = (
        f"https://np-listapi.eastmoney.com/comm/web/getNewsByStock?"
        f"code={code}&market={market}&pageSize={limit}&page=1"
    )
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
            'time': item.get('showTime', item.get('newsDate', '')),
            'source': item.get('source', '东方财富'),
            'url': item.get('url', item.get('infoUrl', '')),
        })

    return news_list if news_list else get_market_news(limit)


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
