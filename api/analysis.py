"""技术分析 - 计算压力位、支撑位、操作建议"""
import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import urllib.request

HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}


def get_kline_data(code: str, period: int = 120) -> list:
    """获取日K线数据"""
    if code.startswith('6') or code.startswith('9'):
        symbol = f"sh{code}"
    else:
        symbol = f"sz{code}"

    url = f"https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketDataService.getKLineData?symbol={symbol}&scale=240&datalen={period}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception:
        return []

    klines = []
    if data and isinstance(data, list):
        for item in data:
            klines.append({
                'date': item.get('day', ''),
                'open': float(item.get('open', 0)),
                'close': float(item.get('close', 0)),
                'high': float(item.get('high', 0)),
                'low': float(item.get('low', 0)),
                'volume': float(item.get('volume', 0)),
            })
    return klines


def calculate_ma(klines: list, periods=None) -> dict:
    if periods is None:
        periods = [5, 10, 20, 60]
    closes = [k['close'] for k in klines]
    result = {}
    for p in periods:
        if len(closes) >= p:
            result[f'MA{p}'] = round(sum(closes[-p:]) / p, 2)
    return result


def calculate_boll(klines: list, period: int = 20) -> dict:
    if len(klines) < period:
        return {}
    closes = [k['close'] for k in klines]
    ma = sum(closes[-period:]) / period
    variance = sum((c - ma) ** 2 for c in closes[-period:]) / period
    std = variance ** 0.5
    return {
        'upper': round(ma + 2 * std, 2),
        'middle': round(ma, 2),
        'lower': round(ma - 2 * std, 2),
    }


def calculate_support_resistance(klines: list) -> dict:
    if len(klines) < 20:
        return {'support': [], 'resistance': []}

    closes = [k['close'] for k in klines]
    current = closes[-1]
    levels = set()

    ma_periods = [5, 10, 20, 60]
    for p in ma_periods:
        if len(closes) >= p:
            ma = round(sum(closes[-p:]) / p, 2)
            levels.add(('MA' + str(p), ma))

    if len(closes) >= 20:
        boll = calculate_boll(klines)
        levels.add(('BOLL上轨', boll['upper']))
        levels.add(('BOLL下轨', boll['lower']))

    recent_20 = klines[-20:]
    recent_high = max(k['high'] for k in recent_20)
    recent_low = min(k['low'] for k in recent_20)
    levels.add(('20日最高', round(recent_high, 2)))
    levels.add(('20日最低', round(recent_low, 2)))

    if len(klines) >= 60:
        recent_60 = klines[-60:]
        levels.add(('60日最高', round(max(k['high'] for k in recent_60), 2)))
        levels.add(('60日最低', round(min(k['low'] for k in recent_60), 2)))

    base = int(current)
    for offset in [-2, -1, 0, 1, 2]:
        lvl = base + offset
        if lvl > 0:
            levels.add((f'整数位{lvl}', float(lvl)))

    support = []
    resistance = []
    for name, price in levels:
        diff_pct = round((price - current) / current * 100, 2)
        entry = {'name': name, 'price': price, 'diff_pct': diff_pct}
        if price < current * 0.998:
            support.append(entry)
        elif price > current * 1.002:
            resistance.append(entry)

    support.sort(key=lambda x: x['price'], reverse=True)
    resistance.sort(key=lambda x: x['price'])

    return {'support': support[:6], 'resistance': resistance[:6]}


def calculate_macd(klines: list) -> dict:
    if len(klines) < 35:
        return {}
    closes = [k['close'] for k in klines]

    def ema(data, period):
        m = 2 / (period + 1)
        values = [data[0]]
        for price in data[1:]:
            values.append((price - values[-1]) * m + values[-1])
        return values

    ema12 = ema(closes, 12)
    ema26 = ema(closes, 26)
    dif = [ema12[i] - ema26[i] for i in range(len(ema12))]
    dea = ema(dif, 9)
    hist = [(dif[i] - dea[i]) * 2 for i in range(len(dea))]

    return {
        'DIF': round(dif[-1], 3),
        'DEA': round(dea[-1], 3),
        'MACD': round(hist[-1], 3),
        'trend': '多头' if dif[-1] > dea[-1] else '空头',
        'signal': '金叉' if len(dif) > 1 and dif[-2] <= dea[-2] and dif[-1] > dea[-1] else
                  ('死叉' if len(dif) > 1 and dif[-2] >= dea[-2] and dif[-1] < dea[-1] else ''),
    }


def calculate_rsi(klines: list, period: int = 14) -> dict:
    if len(klines) < period + 1:
        return {}
    closes = [k['close'] for k in klines]
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas[-period:]]
    losses = [-d if d < 0 else 0 for d in deltas[-period:]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        rsi = 100
    else:
        rsi = 100 - (100 / (1 + avg_gain / avg_loss))
    return {'RSI': round(rsi, 2), 'status': '超买' if rsi > 70 else ('超卖' if rsi < 30 else '正常')}


def calculate_kdj(klines: list, n: int = 9) -> dict:
    if len(klines) < n:
        return {}
    closes = [k['close'] for k in klines]
    highs = [k['high'] for k in klines]
    lows = [k['low'] for k in klines]

    rsv_list = []
    for i in range(n - 1, len(klines)):
        h = max(highs[i-n+1:i+1])
        l = min(lows[i-n+1:i+1])
        if h == l:
            rsv_list.append(50)
        else:
            rsv_list.append((closes[i] - l) / (h - l) * 100)

    k, d, j = 50, 50, 50
    for rsv in rsv_list:
        k = 2/3 * k + 1/3 * rsv
        d = 2/3 * d + 1/3 * k
        j = 3 * k - 2 * d

    return {'K': round(k, 2), 'D': round(d, 2), 'J': round(j, 2)}


def generate_advice(current_price, support_resistance, macd, rsi, kdj, ma) -> dict:
    signals = []
    score = 0

    if macd.get('trend') == '多头':
        score += 1
        if macd.get('signal') == '金叉':
            score += 2
            signals.append({'type': 'buy', 'reason': 'MACD金叉'})
    else:
        score -= 1
        if macd.get('signal') == '死叉':
            score -= 2
            signals.append({'type': 'sell', 'reason': 'MACD死叉'})

    if rsi.get('status') == '超卖':
        score += 2
        signals.append({'type': 'buy', 'reason': f"RSI超卖({rsi.get('RSI')})"})
    elif rsi.get('status') == '超买':
        score -= 2
        signals.append({'type': 'sell', 'reason': f"RSI超买({rsi.get('RSI')})"})

    if kdj:
        if kdj.get('J', 50) < 20:
            score += 1
            signals.append({'type': 'buy', 'reason': f"KDJ超卖(J={kdj.get('J')})"})
        elif kdj.get('J', 50) > 80:
            score -= 1
            signals.append({'type': 'sell', 'reason': f"KDJ超买(J={kdj.get('J')})"})

    if ma.get('MA5') and ma.get('MA20'):
        if ma['MA5'] > ma['MA20']:
            score += 1
            signals.append({'type': 'buy', 'reason': 'MA5>MA20 多头排列'})
        else:
            score -= 1
            signals.append({'type': 'sell', 'reason': 'MA5<MA20 空头排列'})

    sr = support_resistance
    buy_points = [{'price': s['price'], 'name': s['name'], 'diff_pct': s['diff_pct']} for s in sr.get('support', [])[:3]]
    sell_points = [{'price': r['price'], 'name': r['name'], 'diff_pct': r['diff_pct']} for r in sr.get('resistance', [])[:3]]

    if score >= 3:
        action, confidence = '建议买入', '强'
    elif score >= 1:
        action, confidence = '偏多观望', '中'
    elif score <= -3:
        action, confidence = '建议卖出', '强'
    elif score <= -1:
        action, confidence = '偏空观望', '中'
    else:
        action, confidence = '持仓观望', '弱'

    return {
        'action': action,
        'confidence': confidence,
        'score': score,
        'signals': signals,
        'buy_points': buy_points,
        'sell_points': sell_points,
    }


def analyze(code: str) -> dict:
    klines = get_kline_data(code)
    if not klines:
        return {'error': '无法获取K线数据'}

    current_price = klines[-1]['close']
    ma = calculate_ma(klines)
    boll = calculate_boll(klines)
    macd = calculate_macd(klines)
    rsi = calculate_rsi(klines)
    kdj = calculate_kdj(klines)
    sr = calculate_support_resistance(klines)
    advice = generate_advice(current_price, sr, macd, rsi, kdj, ma)

    return {
        'code': code,
        'current_price': current_price,
        'date': klines[-1]['date'],
        'ma': ma,
        'boll': boll,
        'macd': macd,
        'rsi': rsi,
        'kdj': kdj,
        'support_resistance': sr,
        'advice': advice,
    }


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        code = query.get('code', [''])[0].strip()

        if not code:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "code required"}).encode())
            return

        result = analyze(code)

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(result, ensure_ascii=False).encode())
