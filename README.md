# Cross-border E-commerce Analysis

基于 Python 的亚马逊手机壳榜单抓取与竞品分析项目，面向跨境电商选品、定价和竞品研究场景。项目以 Amazon Best Sellers 榜单为入口，抓取商品 ASIN、标题、价格、评分、评论数等信息，对 iPhone 手机壳细分类目进行数据清洗、可视化分析和初步商业判断，为新品切入和 Listing 优化提供参考。

## Project Summary

围绕跨境电商运营场景展开的轻量级竞品分析案例，目标是回答 3 个问题：

1. iPhone 手机壳类目的主流价格带在哪里；
2. 当前榜单中的品牌格局是否集中，是否存在新卖家切入空间；
3. 不同品牌的价格定位有何差异，适合采用什么样的竞争策略。

## Data Pipeline

项目目前包含 3 个核心步骤：

### 1. 榜单 ASIN 提取

脚本：`get_ASIN.py`

- 抓取 Amazon Best Sellers 页面；
- 解析榜单商品链接；
- 提取 ASIN，作为后续详情抓取入口。

### 2. 商品详情抓取

脚本：`get_data.py` / `get_data faster.py`

- 按 ASIN 访问商品详情页；
- 提取 `Title`、`Price`、`Rating`、`Reviews`、`URL` 等字段；
- 使用 `ThreadPoolExecutor` 做并发抓取；
- 通过重试、随机延时、代理等方式降低请求失败率。

### 3. 数据清洗与分析

脚本：`analyze_data.py`

- 清洗价格字段并转换为可分析数值；
- 过滤 iPhone 目标机型相关商品；
- 生成价格分布、品牌数量、品牌价格定位等图表；
- 输出适合竞品调研使用的清洗后结果。

### 4. 评论样本清洗与文本分析

脚本：`review_analysis.py`

- 读取评论原始数据 `asin_reviews_raw.csv` 与抓取状态表 `asin_review_crawl_status.csv`；
- 清洗编码异常、过滤乱码/非英文评论、提取星级数值与评论长度；
- 输出评论基础统计、星级分布、正负向高频词、痛点归类和 README 可复用摘要；
- 将评论分析与抓取覆盖率放在同一套叙述里，使项目更像真实数据采集与分析流程，而不是只挑少量评论做主观总结。

## Repository Structure

```text
Cross-border-e-commerce-analysis/
├── get_ASIN.py
├── get_data.py
├── get_data faster.py
├── analyze_data.py
├── review_analysis.py
├── plots_clean/
│   ├── 1_price_distribution.png
│   ├── 2_top_brands.png
│   └── 3_price_by_brand.png
└── README.md
```

## Tech Stack

- Python
- Requests
- BeautifulSoup4
- Pandas
- Matplotlib
- Seaborn
- concurrent.futures

## Key Analysis Outputs

### 1. Price Distribution

![Price Distribution](https://github.com/cheyunzhuan/Cross-border-e-commerce-analysis/blob/main/plots_clean/1_price_distribution.png)

观察结果：

- 榜单商品价格呈明显右偏分布；
- 主流价格集中在较低价格带；
- 大部分样本落在 `5 - 20 SGD` 区间；
- 高价产品数量明显减少，属于长尾高溢价市场。

业务解读：

- 如果目标是新品冷启动和快速出单，低中价位是更稳妥的切入区间；
- 高价策略并非不能做，但需要更强的品牌背书、材质卖点或防护能力支撑。

### 2. Brand Distribution

![Top Brands](https://github.com/cheyunzhuan/Cross-border-e-commerce-analysis/blob/main/plots_clean/2_top_brands.png)

观察结果：

- 榜单头部品牌数量优势并不明显；
- Top 10 品牌之间铺货数量差距有限；
- 市场呈现出较强的碎片化特征。

业务解读：

- 说明该细分市场并非被极少数品牌绝对垄断；
- 对新卖家来说，仍存在通过差异化卖点和页面优化切入的空间；
- 竞争重点更可能在 Listing 承接、定价、Review 积累和广告效率，而不是品牌垄断本身。

### 3. Price Positioning by Brand

![Price by Brand](https://github.com/cheyunzhuan/Cross-border-e-commerce-analysis/blob/main/plots_clean/3_price_by_brand.png)

观察结果：

- 不同品牌存在明显的价格梯队；
- 低价品牌集中在入门级区间；
- 中端品牌价格更稳定；
- 高端品牌具有更明显的溢价能力。

业务解读：

- 低价路线适合竞争激烈、以走量为主的策略；
- 中端路线需要清晰卖点支撑，如磁吸、防摔、抗黄变、镜头保护等；
- 高端路线更适合已有品牌认知或强功能心智的产品。

## Supporting Files

### 1. Review Insights

文件：`review_insights.md`

作用：

- 对 iPhone 手机壳类目的典型评论进行痛点归类；
- 提炼用户最关注的磁吸、防摔、黄变、手感、开孔、镜头保护等问题；
- 为 Listing 卖点排序、A+ 页面结构和广告创意提供依据。

### 2. Keyword Insights

文件：`keyword_insights.csv`

作用：

- 整理核心词、功能词、场景词和痛点词；
- 便于做关键词分层和页面埋词；
- 可直接作为后续 Listing 优化和广告投放的基础素材。

### 3. Listing Optimization Case

文件：`listing_optimization_case.md`

作用：

- 展示一个 iPhone 16 Pro 手机壳 Listing 的优化前后对比；
- 说明如何将评论痛点和关键词研究转化为 Title、Bullet Points、Description 和 Search Terms；
- 更贴近亚马逊运营助理岗位常见的实际工作内容。

### Deliverable Value

这 3 个补充文件与主项目共同构成了一个更完整的跨境电商运营分析，能够同时体现：

- 数据抓取与清洗能力；
- 竞品分析与图表解读能力；
- 评论痛点提炼能力；
- 关键词整理与页面埋词能力；
- Listing 优化和运营表达能力。

## Review Data Coverage

除榜单与详情页数据外，项目还引入了评论页样本分析。评论原始数据来自 `asin_reviews_raw.csv`，抓取状态记录在 `asin_review_crawl_status.csv`。

当前评论分析链路包含：

- 评论原始数据抓取；
- 评论编码清洗与异常文本过滤；
- 星级、长度、词频和痛点分类分析；
- 与抓取状态表联动，评估评论覆盖率和 captcha 影响。

当前样本特点如下：

- 清洗后保留评论 95 条；
- 覆盖 9 个成功抓取到评论文本的 ASIN；
- 原始尝试抓取 30 个 ASIN 的评论页；
- 其中 17 个 ASIN 在抓取过程中受到 captcha 影响，captcha 占比约 56.7%。

因此，评论洞察部分更适合作为 **sample-based insight extraction**，用于提炼高频卖点和主要负向反馈，而不是把它表述为整个类目的完整评论普查。把抓取状态一并保留下来，也能更真实地反映 Amazon 评论抓取过程中受到反爬限制的情况。

## Business Insights

基于当前样本，本项目得到以下几条可用于运营决策的初步结论：

1. **定价建议**  
   新品如果缺乏品牌心智，优先考虑主流价格带切入，先验证点击率和转化，再决定是否做高客单价路线。

2. **竞争判断**  
   当前榜单的品牌集中度有限，市场并非完全固化，新卖家仍可通过差异化定位争取机会。

3. **页面优化方向**  
   对于 iPhone 手机壳类目，页面重点通常应围绕磁吸、防摔、抗黄变、轻薄手感、镜头保护等核心卖点展开。

4. **适用场景**  
   该分析方法可复用于其他 3C 配件子类目，如钢化膜、支架壳、磁吸配件、车载配件等。

## Limitations

为了保持项目轻量可复现，当前版本也有几个边界：

- 数据样本主要来自榜单页和商品详情页，不包含更深层的广告、销量或转化数据；
- 评论数据受 Amazon captcha 影响较明显，当前评论分析仅覆盖部分成功抓取的 ASIN；
- 类目分析偏向静态截面，不是长期连续监控；
- 目前更适合做竞品研究与选品初筛，不适合作为完整经营分析结论。

后续如果继续完善，可以补充：

- 更多类目和更多时间维度的数据；
- 评论文本和卖点词频分析；
- 关键词聚类与 Listing 卖点对比；
- 更完整的 Dashboard 展示。

## How to Run

### 1. Install dependencies

```bash
pip install requests beautifulsoup4 pandas matplotlib seaborn fake-useragent openpyxl
```

### 2. Configure target URL and proxy

根据自己的环境修改脚本中的：

- `TARGET_URL`
- `SAVE_DIR`
- `PROXIES`

### 3. Run scraper

```bash
python get_ASIN.py
python get_data.py
```

如需更快抓取，可运行：

```bash
python "get_data faster.py"
```

### 4. Run analysis

```bash
python analyze_data.py
python review_analysis.py
```

## Resume-Oriented Value

如果用于求职展示，这个项目能够体现以下能力：

- 能从运营问题出发拆解分析目标，而不只是写脚本；
- 能完成基础数据抓取、清洗、可视化和竞品分析；
- 能把分析结果转化为定价、定位、评论洞察和 Listing 优化方向；
- 具备跨境电商运营助理常见的“数据支持 + 竞品研究”能力基础。

## Disclaimer

本项目仅用于学习、研究与个人作品展示，请勿用于高频、商业化或违反平台规则的数据抓取行为。实际使用时请遵守 Amazon 的平台政策及相关法律法规。
