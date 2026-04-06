import os
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ================= 0. 预处理 =================
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================= 1. 配置区域 =================
SAVE_DIR = "/Users/cyz/cheche/Cross-border e-commerce analysis"
OUTPUT_FILE = os.path.join(SAVE_DIR, "iphone_cases_top50_fast.csv")

# --- 代理设置 ---
PROXIES = {
    "http": "http://127.0.0.1:1082",
    "https": "http://127.0.0.1:1082",
}

# 目标榜单链接
TARGET_URL = "https://www.amazon.com/Best-Sellers-Cell-Phones-Accessories-Cell-Phone-Cases-Covers/zgbs/wireless/2407760011"

# --- 速度控制 ---
MAX_WORKERS = 10  # 同时开启的线程数，建议 5-15，太高容易被封
TIMEOUT = 15  # 单次请求超时时间，太长会拖慢速度


# ================= 2. 核心函数优化 =================

def get_session():
    """优化的 Session，带重试但不拖沓"""
    session = requests.Session()
    # 减少重试次数以提高速度，失败了直接跳过换下一个
    retry_strategy = Retry(total=2, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=100, pool_maxsize=100)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


# 全局 Session 池（复用连接）
SESSION = get_session()


def fetch_best_sellers():
    """获取榜单页面"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
    }

    try:
        print(f"🚀 正在抓取榜单...")
        response = SESSION.get(TARGET_URL, headers=headers, proxies=PROXIES, verify=False, timeout=TIMEOUT)
        if response.status_code == 200:
            print("✅ 榜单获取成功，解析 ASIN...")
            return response.text
        else:
            print(f"❌ 榜单请求失败: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 榜单连接异常: {e}")
        return None


def parse_asins(html):
    """解析 ASIN (基于 data-asin 属性，这是亚马逊最新的结构)"""
    soup = BeautifulSoup(html, "html.parser")
    asins = []

    # 亚马逊新版结构通常使用 data-asin 属性
    # 查找所有包含 data-asin 的 div 或 li 标签
    items = soup.find_all(attrs={"data-asin": True})

    for item in items:
        asin = item['data-asin']
        # 过滤掉无效的 ASIN (如页面侧边栏的推荐位)
        if len(asin) == 10 and asin not in asins:
            # 简单判断是否为榜单主区域 (通常主区域有特定的类名或父级结构)
            # 这里做一个简单的容错：如果包含销量排名数字，则认为是主榜单
            if item.find_previous_sibling() or True:  # 简单模式，直接收录
                asins.append(asin)

    # 限制只取前 30 个，防止抓到页面其他推荐位的干扰数据
    return asins[:30]


# ================= 3. 多线程详情抓取 (极速核心) =================

def fetch_product_detail(asin):
    """
    单个商品抓取函数
    这个函数会被多个线程同时调用
    """
    # 随机浮动延时，模拟真人操作，防封
    # 注意：这里不是死等，而是随机 0.5-1 秒，配合多线程，整体速度依然很快
    time.sleep(random.uniform(0.5, 1.0))

    url = f"https://www.amazon.com/dp/{asin}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
    }

    try:
        response = SESSION.get(url, headers=headers, proxies=PROXIES, verify=False, timeout=TIMEOUT)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")

            # --- 数据提取逻辑 (根据网页结构优化) ---
            # 1. 标题
            title = "N/A"
            for id_sel in ['productTitle', 'title', 'title_feature_div']:
                tag = soup.find(id=id_sel)
                if tag:
                    title = tag.get_text(strip=True)
                    break

            # 2. 价格 (亚马逊价格结构复杂，尝试多种选择器)
            price = "N/A"
            price_selectors = [
                '#price_inside_buybox',
                '#priceblock_ourprice',
                '.a-price.a-text-price.a-size-medium.apexPriceToPay',
                '.a-offscreen'
            ]
            for sel in price_selectors:
                tag = soup.select_one(sel)
                if tag and tag.get_text(strip=True):
                    price = tag.get_text(strip=True)
                    break

            # 3. 评分
            rating = "N/A"
            rating_tag = soup.find("i", attrs={"data-hook": "average-star-rating"})
            if rating_tag:
                rating = rating_tag.get_text(strip=True)
            else:
                # 备用选择器
                span = soup.find("span", class_="a-icon-alt")
                if span:
                    rating = span.get_text(strip=True)

            # 4. 评论数
            reviews = "N/A"
            rev_tag = soup.find("span", attrs={"data-hook": "total-review-count"})
            if rev_tag:
                reviews = rev_tag.get_text(strip=True)
            else:
                # 备用
                rev_span = soup.find("span", id="acrCustomerReviewText")
                if rev_span:
                    reviews = rev_span.get_text(strip=True)

            print(f"   ✅ [{asin}] 抓取成功 | {title[:30]}...")
            return {
                "ASIN": asin,
                "Title": title,
                "Price": price,
                "Rating": rating,
                "Reviews": reviews,
                "URL": url
            }
        else:
            print(f"   ⚠️ [{asin}] 页面访问失败: {response.status_code}")
            return {"ASIN": asin, "Error": f"Status {response.status_code}"}

    except Exception as e:
        print(f"   ❌ [{asin}] 抓取异常: {str(e)[:50]}")
        return {"ASIN": asin, "Error": str(e)}


def main():
    print(f"🚀 启动极速版 iPhone 手机壳市场分析任务...")
    start_time = time.time()

    # 1. 获取榜单页面
    html = fetch_best_sellers()
    if not html:
        return

    # 2. 解析 ASIN
    asin_list = parse_asins(html)
    if not asin_list:
        print("❌ 未解析到 ASIN")
        return

    print(f"\n🎯 准备并发抓取 {len(asin_list)} 个商品，开启 {MAX_WORKERS} 个线程...\n")

    # 3. 多线程并发抓取
    # 使用 ThreadPoolExecutor
    results = []

    # max_workers 控制并发数
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 提交所有任务
        # fetch_product_detail 是函数名，asin 是参数
        future_to_asin = {executor.submit(fetch_product_detail, asin): asin for asin in asin_list}

        # as_completed 会在线程完成时立即返回，无需等待其他线程
        for future in as_completed(future_to_asin):
            data = future.result()
            results.append(data)

    # 4. 数据清洗与保存
    # 过滤掉可能存在的错误字典，只保留有效数据
    valid_results = [r for r in results if 'Error' not in r]

    if valid_results:
        df = pd.DataFrame(valid_results)
        os.makedirs(SAVE_DIR, exist_ok=True)
        df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
        print(f"\n🎉 任务完成！成功抓取 {len(valid_results)} 条数据。")
        print(f"📁 已保存至: {OUTPUT_FILE}")
    else:
        print("\n⚠️ 所有数据抓取均失败，请检查网络或代理。")

    print(f"⏱️ 总耗时: {time.time() - start_time:.2f} 秒")


if __name__ == "__main__":
    main()