import os
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd
from fake_useragent import UserAgent
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ================= 0. 预处理 =================
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================= 1. 配置区域 =================
SAVE_DIR = "/Users/cyz/cheche/Cross-border e-commerce analysis"
OUTPUT_FILE = os.path.join(SAVE_DIR, "iphone_cases_top50.csv")

# --- 代理设置 ---
# 请确保小火箭开启了“允许来自局域网的连接”
PROXIES = {
    "http": "http://127.0.0.1:1082",
    "https": "http://127.0.0.1:1082",
}

# 目标榜单链接
TARGET_URL = "https://www.amazon.com/Best-Sellers-Cell-Phones-Accessories-Cell-Phone-Cases-Covers/zgbs/wireless/2407760011"

# ================= 2. 核心函数 =================

def get_session():
    """
    创建一个带有重试机制的 Session
    """
    session = requests.Session()

    # 设置重试策略：总共重试3次，遇到连接错误或被重定向都重试
    retry_strategy = Retry(
        total=3,
        backoff_factor=2,  # 重试间隔：1秒, 2秒, 4秒
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session

def fetch_best_sellers():
    """
    获取榜单页面的 HTML
    """
    session = get_session()

    # 伪装成非常新的 Chrome 浏览器
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        # 强制指定地区 Cookie，防止跳转
        "Cookie": "skin=noskin; i18n-prefs=USD"
    }

    try:
        print(f"🚀 正在连接亚马逊榜单...")
        response = session.get(
            TARGET_URL,
            headers=headers,
            proxies=PROXIES,
            verify=False, # 忽略 SSL 验证
            timeout=30    # 延长超时时间到 30 秒
        )

        if response.status_code == 200:
            print("✅ 榜单页面获取成功！")
            return response.text
        else:
            print(f"❌ 获取失败，状态码：{response.status_code}")
            # 打印前 200 个字符，看看亚马逊返回了什么（通常是验证码或拦截页）
            print(f"⚠️ 服务器返回内容预览：{response.text[:200]}")
            return None

    except Exception as e:
        print(f"❌ 连接异常：{e}")
        print("💡 提示：如果一直报错，请检查 Shadowrocket 是否开启了“允许来自局域网的连接”。")
        return None

def parse_asins(html):
    """
    解析 Top 50 ASIN
    """
    soup = BeautifulSoup(html, "html.parser")
    asins = []

    # 亚马逊榜单的新结构通常是 grid，旧结构是 list
    # 我们尝试抓取所有带有 ASIN 信息的链接
    links = soup.find_all("a", href=True)

    print(f"🔍 正在扫描页面链接... 共发现 {len(links)} 个链接")

    for link in links:
        href = link["href"]
        # 筛选包含 /dp/ 或 /gp/product/ 的链接
        if "/dp/" in href or "/gp/product/" in href:
            # 简单的 ASIN 提取逻辑（ASIN 通常是 10 位字母数字）
            parts = href.split("/")
            for part in parts:
                if len(part) == 10 and (part[0].isdigit() or part[0].isalpha()):
                    if part not in asins:
                        asins.append(part)
                        print(f"   📦 找到 ASIN: {part}")

    return list(set(asins)) # 去重

def main():
    print(f"🚀 启动 iPhone 17 Pro Max 手机壳市场分析任务...")

    # 1. 获取榜单页面
    html = fetch_best_sellers()

    if not html:
        print("❌ 任务终止：无法获取页面源码。")
        return

    # 2. 解析 ASIN
    asin_list = parse_asins(html)

    if not asin_list:
        print("❌ 未获取到 ASIN，可能是页面结构变化或被重定向到了登录页。")
        # 保存源码以便调试
        with open("debug_amazon.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("💡 已将当前页面源码保存为 debug_amazon.html，请检查文件内容。")
        return

    print(f"\n🎉 成功获取 {len(asin_list)} 个 ASIN！")
    print(f"示例: {asin_list[:5]}")

    # 这里你可以继续调用之前的详情爬取函数...
    # (为了演示，这里先只展示获取 ASIN 的部分)

if __name__ == "__main__":
    main()