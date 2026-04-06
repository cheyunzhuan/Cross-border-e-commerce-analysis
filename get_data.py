import os
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ================= 0. 预处理 =================
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================= 1. 配置区域 =================
SAVE_DIR = "/Users/cyz/cheche/Cross-border e-commerce analysis"
OUTPUT_FILE = os.path.join(SAVE_DIR, "iphone_cases_analysis_final.csv")

# --- 代理设置 ---
PROXIES = {
    "http": "http://127.0.0.1:1082",
    "https": "http://127.0.0.1:1082",
}

# --- 目标榜单链接 ---
BEST_SELLERS_URL = "https://www.amazon.com/Best-Sellers-Cell-Phones-Accessories-Cell-Phone-Cases-Covers/zgbs/wireless/2407760011"


# ================= 2. 核心函数 =================

def get_session():
    """
    创建带有重试机制的 Session
    """
    session = requests.Session()

    # 修复重试策略
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # 统一设置 Headers
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cookie": "skin=noskin; i18n-prefs=USD; lc-main=en_US"
    })

    return session


def fetch_html(url, session=None):
    """
    获取页面 HTML
    """
    if session is None:
        session = get_session()

    try:
        response = session.get(url, proxies=PROXIES, verify=False, timeout=30)
        if response.status_code == 200:
            # 检查是否被重定向到验证码页
            if "captcha" in response.text.lower() or "type the characters" in response.text.lower():
                print("❌ 触发验证码拦截！")
                return None
            return response.text
        else:
            print(f"❌ HTTP 状态码错误: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return None


def parse_asins_from_list(html):
    """
    解析榜单页面获取 ASIN (针对亚马逊最新结构)
    """
    soup = BeautifulSoup(html, "html.parser")
    asins = []

    print("🔍 正在解析榜单 ASIN...")

    # 方法 1: 寻找带有 data-asin 属性的容器 (亚马逊新榜单结构)
    # 参考你提供的源码，通常是 <div data-asin="..."> 或 <li data-asin="...">
    items_with_data = soup.find_all(attrs={"data-asin": True})

    for item in items_with_data:
        asin = item.get("data-asin")
        # 过滤掉无效的 ASIN (如 "undefined" 或 空值)
        if asin and len(asin) == 10 and asin not in asins:
            asins.append(asin)
            print(f"   ✅ 找到 ASIN (data-asin): {asin}")

    # 方法 2: 备用方案，查找 /dp/ 链接 (防止 data-asin 失效)
    if len(asins) < 10:  # 如果上面没抓到足够的数据，启用备用方案
        print("ℹ️ data-asin 方案数据不足，启动备用链接提取方案...")
        links = soup.find_all("a", href=True)
        for link in links:
            href = link['href']
            if '/dp/' in href:
                # 提取 /dp/ 后面的 10 位字符
                import re
                match = re.search(r'/dp/([A-Z0-9]{10})', href)
                if match:
                    asin = match.group(1)
                    if asin not in asins:
                        asins.append(asin)
                        print(f"   ✅ 找到 ASIN (链接提取): {asin}")

    # 限制只取前 30 个
    return asins[:30]


def parse_product_details(html, asin):
    """
    解析单个商品详情页
    """
    soup = BeautifulSoup(html, "html.parser")
    data = {"ASIN": asin}

    try:
        # 1. 标题
        title_tag = soup.find("span", id="productTitle")
        data["Title"] = title_tag.get_text(strip=True) if title_tag else "N/A"

        # 2. 价格 (处理多种价格结构)
        price = "N/A"
        # 尝试 1: 主价格类
        price_tag = soup.find("span", class_="a-price-whole")
        if price_tag:
            frac_tag = soup.find("span", class_="a-price-fraction")
            price = price_tag.get_text(strip=True) + (frac_tag.get_text(strip=True) if frac_tag else "")
        else:
            # 尝试 2: 隐藏价格类 (Offscreen)
            offscreen = soup.find("span", class_="a-offscreen")
            if offscreen:
                price = offscreen.get_text(strip=True)
        data["Price"] = price

        # 3. 评分
        rating_tag = soup.find("span", class_="a-icon-alt")
        data["Rating"] = rating_tag.get_text(strip=True) if rating_tag else "0"

        # 4. 评论数
        reviews_tag = soup.find("span", id="acrCustomerReviewText")
        data["Reviews"] = reviews_tag.get_text(strip=True) if reviews_tag else "0"

        # 5. 品牌
        brand_tag = soup.find("a", id="bylineInfo")
        data["Brand"] = brand_tag.get_text(strip=True).replace("Brand: ", "") if brand_tag else "N/A"

        # 6. BSR (销量排名)
        bsr_tag = soup.find("span", string="Best Sellers Rank")
        if not bsr_tag:
            # 备用查找
            bsr_tag = soup.find("td", string=lambda text: text and "Best Sellers Rank" in text)

        if bsr_tag:
            # 简单提取排名数字
            rank_text = bsr_tag.parent.get_text() if bsr_tag.name == "td" else bsr_tag.find_next().get_text()
            import re
            rank_num = re.search(r'#?[\d,]+', rank_text)
            data["BSR"] = rank_num.group(0).replace('#', '').replace(',', '') if rank_num else "N/A"
        else:
            data["BSR"] = "N/A"

        data["Status"] = "Success"

    except Exception as e:
        print(f"   ❌ 解析失败 {asin}: {e}")
        data["Status"] = "Parse Error"

    return data


def main():
    print("🚀 开始采集任务...")
    session = get_session()

    # 1. 获取榜单页面
    print(f"📥 正在抓取榜单: {BEST_SELLERS_URL}")
    list_html = fetch_html(BEST_SELLERS_URL, session)

    if not list_html:
        print("❌ 无法获取榜单页面，请检查网络或代理。")
        return

    # 2. 解析 ASIN (核心修复点)
    asin_list = parse_asins_from_list(list_html)

    if not asin_list:
        print("❌ 严重错误：未能解析到任何 ASIN。")
        print("💡 建议：将当前页面保存为 HTML 文件发给我，我来重新适配解析规则。")
        return

    print(f"✅ 成功获取 {len(asin_list)} 个 ASIN。准备抓取详情...")

    # 3. 多线程抓取详情
    results = []

    # 为了演示，我们先用单线程，避免被封，或者你可以改为 ThreadPoolExecutor
    for asin in asin_list:
        print(f"\n🕷️ 正在抓取详情: {asin}")

        # 拼接详情页链接
        detail_url = f"https://www.amazon.com/dp/{asin}"
        html = fetch_html(detail_url, session)

        if html:
            data = parse_product_details(html, asin)
            results.append(data)
        else:
            results.append({"ASIN": asin, "Status": "Failed to Fetch Detail"})

        # 随机延时，防止太快被封
        time.sleep(random.uniform(2, 5))

    # 4. 保存数据
    if results:
        df = pd.DataFrame(results)
        df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
        print(f"\n💾 数据已保存至: {OUTPUT_FILE}")
    else:
        print("⚠️ 未抓取到任何有效数据。")


if __name__ == "__main__":
    main()
