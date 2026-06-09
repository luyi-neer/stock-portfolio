"""获取股票实时行情"""
import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import urllib.request


HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}


def get_realtime_quote(codes: list) -> list:
    """从东方财富获取实时行情"""
    secids = []
    for code in codes:
        code = code.strip()
        if code.startswith('6') or code.startswith('9'):
            secids.append(f"1.{code}")
        elif code.startswith('0') or code.startswith('3'):
            secids.append(f"0.{code}")
        elif code.startswith('8') or code.startswith('4'):
            secids.append(f"0.{code}")
        else:
            secids.append(f"1.{code}")

    secids_str = ",".join(secids)
    url = (
        f"https://push2.eastmoney.com/api/qt/ulist.np/get?"
        f"secids={secids_str}&"
        f"fields=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18"
    )

    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        return [{"error": str(e)}]

    results = []
    if data and data.get('data') and data['data'].get('diff'):
        for item in data['data']['diff']:
            results.append({
                'code': item.get('f12', ''),
                'name': item.get('f14', ''),
                'price': item.get('f2', 0) / 100 if isinstance(item.get('f2'), int) else item.get('f2', 0),
                'change_pct': item.get('f3', 0) / 100 if isinstance(item.get('f3'), int) else item.get('f3', 0),
                'change_amt': item.get('f4', 0) / 100 if isinstance(item.get('f4'), int) else item.get('f4', 0),
                'volume': item.get('f5', 0),
                'amount': item.get('f6', 0),
                'amplitude': item.get('f7', 0) / 100 if isinstance(item.get('f7'), int) else item.get('f7', 0),
                'high': item.get('f15', 0) / 100 if isinstance(item.get('f15'), int) else item.get('f15', 0),
                'low': item.get('f16', 0) / 100 if isinstance(item.get('f16'), int) else item.get('f16', 0),
                'open': item.get('f17', 0) / 100 if isinstance(item.get('f17'), int) else item.get('f17', 0),
                'prev_close': item.get('f18', 0) / 100 if isinstance(item.get('f18'), int) else item.get('f18', 0),
                'turnover': item.get('f8', 0) / 100 if isinstance(item.get('f8'), int) else item.get('f8', 0),
            })

    return results


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        codes = query.get('codes', [''])[0].split(',')

        if not codes or codes == ['']:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "codes required"}).encode())
            return

        result = get_realtime_quote(codes)

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(result, ensure_ascii=False).encode())
