#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
今日头条文章抓取写入 Obsidian
从指定用户主页抓取 24 小时内的文章列表，写入 Obsidian 的「今日头条/{作者名}/YYYY-MM-DD.md」
"""

import os
import sys
import re
import yaml
import datetime
import time
from pathlib import Path

# 导入 selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

# 导入 hot_writer 的辅助函数
sys.path.insert(0, os.path.dirname(__file__))
from hot_writer import clean_filename, _write_items_to_file


def load_config():
    """从 config.yaml 读取配置"""
    config_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_relative_time(time_str):
    """
    解析相对时间字符串（如"5分钟前"、"2小时前"、"3天前"）为 datetime 对象
    返回发布的绝对时间，若无法解析则返回 None
    """
    if not time_str:
        return None

    time_str = time_str.strip()
    now = datetime.datetime.now()

    # 匹配 "N分钟前"
    m = re.search(r'(\d+)\s*分钟前', time_str)
    if m:
        minutes = int(m.group(1))
        return now - datetime.timedelta(minutes=minutes)

    # 匹配 "N小时前"
    m = re.search(r'(\d+)\s*小时前', time_str)
    if m:
        hours = int(m.group(1))
        return now - datetime.timedelta(hours=hours)

    # 匹配 "N天前"
    m = re.search(r'(\d+)\s*天前', time_str)
    if m:
        days = int(m.group(1))
        return now - datetime.timedelta(days=days)

    # 匹配 "刚刚"
    if "刚刚" in time_str:
        return now

    return None


def read_existing_links(filepath):
    """从本地文件读取已存在的链接"""
    if not os.path.isfile(filepath):
        return set()
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return set(re.findall(r'\]\(([^)\s]+)\)', content))
    except:
        return set()


def fetch_toutiao_articles(user_url, author_name, existing_links, headless=False):
    """
    从今日头条用户页智能增量抓取文章或视频列表
    - 如果第一个已存在，停止当前作者
    - 否则每次抓取 5 个，检查最后一个是否存在
    - 存在则停止，不存在则继续
    返回 list of dict: [{"title": "...", "link": "...", "pub_date": "..."}, ...]
    """
    articles = []

    # 判断是文章还是视频
    is_video = "tab=video" in user_url
    selector_container = "div.profile-large-video-card-wrapper" if is_video else "div.feed-card-article"
    selector_link = "a[href*='/video/']" if is_video else "a[href*='/article/']"

    # 配置 Chrome 选项
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        content_type = "视频" if is_video else "文章"
        print(f"[{author_name}] 打开页面 ({content_type}): {user_url}")
        driver.get(user_url)

        # 等待内容加载
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector_container)))

        batch_size = 5
        processed = 0
        should_stop = False

        # 批量加载和检查
        while not should_stop:
            # 滚动到底部，加载更多内容
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)

            # 获取当前页面的所有元素
            elements = driver.find_elements(By.CSS_SELECTOR, selector_container)
            total_found = len(elements)

            if total_found == 0:
                break

            # 处理这一批元素（从 processed 开始）
            for i in range(processed, min(processed + batch_size, total_found)):
                elem = elements[i]

                try:
                    link_elem = elem.find_element(By.CSS_SELECTOR, selector_link)
                    title = link_elem.get_attribute("title") or link_elem.text.strip()
                    link = link_elem.get_attribute("href") or ""

                    if link and link.startswith("/"):
                        link = "https://www.toutiao.com" + link

                    # 检查第一个是否已存在
                    if i == 0 and link in existing_links:
                        print(f"[{author_name}] ⏸ 检测到已存在内容，停止抓取")
                        should_stop = True
                        break

                    # 提取发布时间
                    pub_date_str = ""
                    try:
                        time_elem = elem.find_element(By.CSS_SELECTOR, "div.feed-card-footer-time-cmp, span[class*='time']")
                        pub_date_str = time_elem.text.strip()
                    except:
                        pass

                    if title and link:
                        articles.append({
                            "title": title,
                            "link": link,
                            "pub_date": pub_date_str,
                        })
                        print(f"  {i+1}. {title} ({pub_date_str})")

                        # 检查最后一个是否已存在
                        if i == min(processed + batch_size - 1, total_found - 1) and link in existing_links:
                            print(f"[{author_name}] ✓ 已到达已存在内容，停止抓取")
                            should_stop = True

                except Exception as e:
                    continue

            processed = min(processed + batch_size, total_found)

            # 如果已处理到底部且没有新增，停止
            if processed >= total_found:
                break

    finally:
        driver.quit()

    return articles


def filter_24h_articles(articles):
    """
    过滤出 24 小时内的文章
    返回 list of dict
    """
    cutoff = datetime.datetime.now() - datetime.timedelta(hours=24)
    filtered = []

    for article in articles:
        pub_time = parse_relative_time(article.get("pub_date", ""))
        if pub_time and pub_time >= cutoff:
            filtered.append(article)

    return filtered


def main():
    config = load_config()
    obsidian_base = config.get("obsidian_base", "")
    toutiao_users = config.get("toutiao_users", [])

    if not toutiao_users:
        print("未配置 toutiao_users，跳过今日头条抓取")
        return

    if not obsidian_base:
        print("错误：未配置 obsidian_base")
        return

    for user_config in toutiao_users:
        if not isinstance(user_config, dict):
            continue

        user_url = user_config.get("url", "")
        author_name = user_config.get("name", "未知作者")
        headless = user_config.get("headless", False)

        if not user_url:
            continue

        print(f"\n========== 抓取 {author_name} ==========")

        # 读取本地已存在的链接
        today = datetime.date.today().isoformat()
        toutiao_dir = os.path.join(obsidian_base, "今日头条", author_name)
        filepath = os.path.join(toutiao_dir, f"{today}.md")
        existing_links = read_existing_links(filepath)

        if existing_links:
            print(f"[{author_name}] 本地已有 {len(existing_links)} 条记录，启用增量模式")
        else:
            print(f"[{author_name}] 本地无记录，全量抓取")

        # 智能增量抓取
        articles = fetch_toutiao_articles(user_url, author_name, existing_links, headless=headless)

        if not articles:
            print(f"[{author_name}] 未找到新内容")
            continue

        # 过滤 24 小时内的文章
        filtered_articles = filter_24h_articles(articles)

        if not filtered_articles:
            print(f"[{author_name}] 未找到 24 小时内的新文章")
            continue

        print(f"[{author_name}] ✓ 新增 {len(filtered_articles)} 篇 24 小时内的内容")

        # 写入 Obsidian
        items = []
        for article in filtered_articles:
            items.append({
                "title": article["title"],
                "link": article["link"],
                "source": "今日头条",
                "pub_date": article["pub_date"],
                "summary": "",
            })

        # 使用 hot_writer 的增量写入逻辑
        os.makedirs(toutiao_dir, exist_ok=True)
        _write_items_to_file(obsidian_base, filepath, items, title=author_name, include_summary=False)
        print(f"[{author_name}] 保存到: {filepath}")


if __name__ == "__main__":
    main()
