const STORAGE_KEY = 'stock_portfolio';
let quotesLoaded = false;

function getPortfolio() {
  const data = localStorage.getItem(STORAGE_KEY);
  return data ? JSON.parse(data) : [];
}

function savePortfolio(list) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
}

document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
    if (tab.dataset.tab === 'portfolio' && !quotesLoaded) refreshQuotes();
    if (tab.dataset.tab === 'analysis') autoLoadAnalysis();
    if (tab.dataset.tab === 'news') autoLoadNews();
    if (tab.dataset.tab === 'manage') renderManageList();
  });
});

async function refreshQuotes() {
  const portfolio = getPortfolio();
  if (!portfolio.length) {
    document.getElementById('portfolio-list').innerHTML = '<div class="empty">暂无持仓，请在管理页添加</div>';
    document.getElementById('total-value').textContent = '¥0';
    document.getElementById('total-profit').textContent = '¥0';
    document.getElementById('total-profit-pct').textContent = '0%';
    return;
  }

  document.getElementById('portfolio-list').innerHTML = '<div class="loading">加载中...</div>';
  const codes = portfolio.map(s => s.code).join(',');

  try {
    const resp = await fetch('/api/quote?codes=' + codes);
    const quotes = await resp.json();
    let totalValue = 0, totalCost = 0;

    const listHtml = portfolio.map(stock => {
      const quote = quotes.find(q => q.code === stock.code) || {};
      const price = quote.price || 0;
      const changePct = quote.change_pct || 0;
      const marketValue = price * stock.shares;
      const cost = stock.cost * stock.shares;
      const profit = marketValue - cost;
      totalValue += marketValue;
      totalCost += cost;

      const colorClass = changePct > 0 ? 'up' : (changePct < 0 ? 'down' : '');
      const profitClass = profit > 0 ? 'up' : (profit < 0 ? 'down' : '');

      return `<div class="card stock-card">
        <div>
          <div class="stock-name">${stock.name}</div>
          <div class="stock-code">${stock.code} | ${stock.shares}股</div>
        </div>
        <div>
          <div class="stock-price ${colorClass}">${price ? price.toFixed(2) : '--'}</div>
          <div class="stock-change ${colorClass}">${changePct > 0 ? '+' : ''}${changePct.toFixed(2)}%</div>
          <div class="stock-change ${profitClass}">${profit >= 0 ? '+' : ''}${profit.toFixed(0)}元</div>
        </div>
      </div>`;
    }).join('');

    document.getElementById('portfolio-list').innerHTML = listHtml;

    const totalProfit = totalValue - totalCost;
    const totalProfitPct = totalCost > 0 ? (totalProfit / totalCost * 100) : 0;
    const cls = totalProfit >= 0 ? 'up' : 'down';

    document.getElementById('total-value').textContent = `¥${totalValue.toFixed(0)}`;
    document.getElementById('total-profit').textContent = `${totalProfit >= 0 ? '+' : ''}¥${totalProfit.toFixed(0)}`;
    document.getElementById('total-profit').className = `summary-value ${cls}`;
    document.getElementById('total-profit-pct').textContent = `${totalProfitPct >= 0 ? '+' : ''}${totalProfitPct.toFixed(1)}%`;
    document.getElementById('total-profit-pct').className = `summary-value ${cls}`;
    quotesLoaded = true;
  } catch (e) {
    document.getElementById('portfolio-list').innerHTML = '<div class="empty">获取行情失败，请重试</div>';
  }
}

function autoLoadAnalysis() {
  const portfolio = getPortfolio();
  const container = document.getElementById('analysis-list');
  if (!portfolio.length) {
    container.innerHTML = '<div class="empty">暂无持仓，请先添加</div>';
    return;
  }
  container.innerHTML = portfolio.map(s =>
    `<div class="collapse-card" id="analysis-${s.code}">
      <div class="collapse-header" onclick="toggleCollapse(this, '${s.code}', 'analysis')">
        <span class="title">${s.name} (${s.code})</span>
        <span class="arrow">▼</span>
      </div>
      <div class="collapse-body">
        <div class="collapse-content"><div class="loading">点击展开加载分析...</div></div>
      </div>
    </div>`
  ).join('');
}

function autoLoadNews() {
  const portfolio = getPortfolio();
  const container = document.getElementById('news-list');
  if (!portfolio.length) {
    container.innerHTML = '<div class="empty">暂无持仓，请先添加</div>';
    return;
  }
  container.innerHTML = portfolio.map(s =>
    `<div class="collapse-card" id="news-${s.code}">
      <div class="collapse-header" onclick="toggleCollapse(this, '${s.code}', 'news')">
        <span class="title">${s.name} (${s.code})</span>
        <span class="arrow">▼</span>
      </div>
      <div class="collapse-body">
        <div class="collapse-content"><div class="loading">点击展开加载新闻...</div></div>
      </div>
    </div>`
  ).join('');
}

async function toggleCollapse(header, code, type) {
  const card = header.parentElement;
  const isOpen = card.classList.contains('open');

  if (isOpen) {
    card.classList.remove('open');
    return;
  }

  card.classList.add('open');
  const content = card.querySelector('.collapse-content');

  if (content.dataset.loaded) return;

  content.innerHTML = '<div class="loading">加载中...</div>';

  if (type === 'analysis') {
    await loadAnalysisFor(code, content);
  } else {
    await loadNewsFor(code, content);
  }
  content.dataset.loaded = '1';
}

async function loadAnalysisFor(code, container) {
  try {
    const resp = await fetch('/api/analysis?code=' + code);
    const data = await resp.json();

    if (data.error) {
      container.innerHTML = `<div class="empty">${data.error}</div>`;
      return;
    }

    const advice = data.advice || {};
    const sr = data.support_resistance || {};

    let adviceClass = 'advice-hold';
    if (advice.action && (advice.action.includes('买入') || advice.action.includes('偏多'))) adviceClass = 'advice-buy';
    if (advice.action && (advice.action.includes('卖出') || advice.action.includes('偏空'))) adviceClass = 'advice-sell';

    let html = `<div style="margin-bottom:10px"><span class="advice-tag ${adviceClass}">${advice.action || '观望'}</span>
      <span style="margin-left:8px;font-size:12px;color:var(--text-dim)">评分: ${advice.score || 0} | ${advice.confidence || ''}</span></div>`;

    html += `<div style="font-size:14px;font-weight:600;margin-bottom:6px">当前: ¥${data.current_price}</div>`;

    if (sr.resistance && sr.resistance.length) {
      html += '<div class="level-list"><div style="font-size:12px;color:var(--red);margin-bottom:4px">压力位</div>';
      sr.resistance.slice(0, 4).forEach(r => {
        html += `<div class="level-row"><span class="level-label">${r.name}</span><span class="up">¥${r.price}</span></div>`;
      });
      html += '</div>';
    }

    if (sr.support && sr.support.length) {
      html += '<div class="level-list" style="margin-top:8px"><div style="font-size:12px;color:var(--green);margin-bottom:4px">支撑位</div>';
      sr.support.slice(0, 4).forEach(s => {
        html += `<div class="level-row"><span class="level-label">${s.name}</span><span class="down">¥${s.price}</span></div>`;
      });
      html += '</div>';
    }

    if (data.macd || data.rsi || data.kdj) {
      html += '<div class="indicator-grid">';
      if (data.macd) html += `<div class="indicator-item"><div class="indicator-label">MACD</div><div class="indicator-value">${data.macd.trend}${data.macd.signal ? ' ' + data.macd.signal : ''}</div></div>`;
      if (data.rsi) html += `<div class="indicator-item"><div class="indicator-label">RSI(14)</div><div class="indicator-value">${data.rsi.RSI} ${data.rsi.status}</div></div>`;
      if (data.kdj) html += `<div class="indicator-item"><div class="indicator-label">KDJ</div><div class="indicator-value">K${data.kdj.K} D${data.kdj.D} J${data.kdj.J}</div></div>`;
      if (data.boll) html += `<div class="indicator-item"><div class="indicator-label">BOLL</div><div class="indicator-value">${data.boll.upper}/${data.boll.middle}/${data.boll.lower}</div></div>`;
      html += '</div>';
    }

    if (advice.buy_points && advice.buy_points.length) {
      html += '<div style="margin-top:10px;font-size:12px;color:var(--green)">建议买入: ' +
        advice.buy_points.map(p => `¥${p.price}`).join(' / ') + '</div>';
    }
    if (advice.sell_points && advice.sell_points.length) {
      html += '<div style="margin-top:4px;font-size:12px;color:var(--red)">建议卖出: ' +
        advice.sell_points.map(p => `¥${p.price}`).join(' / ') + '</div>';
    }

    container.innerHTML = html;
  } catch (e) {
    container.innerHTML = '<div class="empty">分析失败</div>';
  }
}

async function loadNewsFor(code, container) {
  try {
    const resp = await fetch('/api/news?code=' + code);
    const news = await resp.json();

    if (!news.length) {
      container.innerHTML = '<div class="empty">暂无新闻</div>';
      return;
    }

    container.innerHTML = news.slice(0, 10).map(item =>
      `<div class="news-item">
        <div class="news-title">${item.title}</div>
        <div class="news-date">${item.source || ''} ${item.time || ''}</div>
      </div>`
    ).join('');
  } catch (e) {
    container.innerHTML = '<div class="empty">加载失败</div>';
  }
}

function searchAnalysis() {
  const code = document.getElementById('analysis-code').value.trim();
  if (!code) return;

  const container = document.getElementById('analysis-list');
  container.innerHTML = `<div class="collapse-card open" id="analysis-search">
    <div class="collapse-header">
      <span class="title">搜索: ${code}</span>
      <span class="arrow">▼</span>
    </div>
    <div class="collapse-body">
      <div class="collapse-content"><div class="loading">分析中...</div></div>
    </div>
  </div>`;

  const content = container.querySelector('.collapse-content');
  loadAnalysisFor(code, content);
}

function searchNews() {
  const code = document.getElementById('news-code').value.trim();
  if (!code) return;

  const container = document.getElementById('news-list');
  container.innerHTML = `<div class="collapse-card open" id="news-search">
    <div class="collapse-header">
      <span class="title">搜索: ${code}</span>
      <span class="arrow">▼</span>
    </div>
    <div class="collapse-body">
      <div class="collapse-content"><div class="loading">加载中...</div></div>
    </div>
  </div>`;

  const content = container.querySelector('.collapse-content');
  loadNewsFor(code, content);
}

function addStock(event) {
  event.preventDefault();
  const code = document.getElementById('input-code').value.trim();
  const name = document.getElementById('input-name').value.trim();
  const shares = parseInt(document.getElementById('input-shares').value);
  const cost = parseFloat(document.getElementById('input-cost').value);

  if (!code || !name || !shares || !cost) return;

  const portfolio = getPortfolio();
  const existing = portfolio.find(s => s.code === code);
  if (existing) {
    const totalShares = existing.shares + shares;
    existing.cost = (existing.cost * existing.shares + cost * shares) / totalShares;
    existing.shares = totalShares;
    existing.name = name;
  } else {
    portfolio.push({ code, name, shares, cost });
  }

  savePortfolio(portfolio);
  document.getElementById('add-form').reset();
  renderManageList();
  alert('添加成功');
}

function removeStock(code) {
  if (!confirm('确认删除？')) return;
  const portfolio = getPortfolio().filter(s => s.code !== code);
  savePortfolio(portfolio);
  renderManageList();
}

function renderManageList() {
  const portfolio = getPortfolio();
  const container = document.getElementById('manage-list');

  if (!portfolio.length) {
    container.innerHTML = '<div class="empty">暂无持仓</div>';
    return;
  }

  container.innerHTML = portfolio.map(stock =>
    `<div class="manage-item">
      <div class="manage-info">
        <div class="name">${stock.name} (${stock.code})</div>
        <div class="detail">${stock.shares}股 · 成本 ¥${stock.cost.toFixed(3)}</div>
      </div>
      <button class="btn-danger" onclick="removeStock('${stock.code}')">删除</button>
    </div>`
  ).join('');
}

document.addEventListener('DOMContentLoaded', () => {
  refreshQuotes();
});
