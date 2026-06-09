# 股票持仓管理 H5

移动端友好的股票持仓管理工具，支持实时行情、技术分析、个股新闻。

## 功能

1. **持仓总览** - 实时价格、盈亏计算
2. **技术分析** - 压力位/支撑位/MACD/RSI/KDJ/布林带，自动生成买卖建议
3. **个股新闻** - 东方财富/新浪财经新闻聚合
4. **持仓管理** - 添加/删除持仓，数据存于浏览器 localStorage

## 部署到 Vercel（免费）

### 方式一：命令行部署

```bash
npm i -g vercel
cd stock-portfolio
vercel
vercel --prod
```

### 方式二：GitHub 自动部署

1. 将 `stock-portfolio` 目录推送到 GitHub 仓库
2. 访问 vercel.com，用 GitHub 账号登录
3. 点击 "Import Project"，选择仓库
4. 直接点 "Deploy"

部署完成后得到 `xxx.vercel.app` 域名，手机浏览器直接访问。

## 本地开发

```bash
npm i -g vercel
vercel dev
```

访问 http://localhost:3000

## 技术栈

- 前端: 纯 HTML/CSS/JS（移动端适配）
- 后端: Python Serverless Functions (Vercel)
- 数据源: 东方财富 + 新浪财经
- 存储: 浏览器 localStorage

## API 接口

| 接口 | 参数 | 说明 |
|------|------|------|
| GET /api/quote | codes=600519,000001 | 批量获取实时行情 |
| GET /api/analysis | code=600519 | 技术分析（压力位/支撑位/建议） |
| GET /api/news | code=600519 | 个股新闻 |
