import os
import json
import hashlib
import time
from urllib.parse import urljoin, urlparse

import requests
from tqdm import tqdm
from bs4 import BeautifulSoup

BASE_URL = "https://www.taplowgroup.com"
NEWS_LIST_URL = BASE_URL + "/insights/news/pgrid/5286/pageid/{}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}
IMAGE_FOLDER = "news_images"
OUTPUT_FILE = "taplow_news.json"

def download_image(img_url, folder=IMAGE_FOLDER):
    if not img_url:
        return None
    if not img_url.startswith("http"):
        img_url = urljoin(BASE_URL, img_url)

    os.makedirs(folder, exist_ok=True)

    try:
        response = requests.get(img_url, headers=HEADERS, timeout=10)
        response.raise_for_status()

        parsed_url = urlparse(img_url)
        ext = os.path.splitext(parsed_url.path)[-1] or ".jpg"
        name_hash = hashlib.md5(img_url.encode()).hexdigest()
        filename = f"{name_hash}{ext}"
        filepath = os.path.join(folder, filename)

        with open(filepath, "wb") as f:
            f.write(response.content)

        return filepath.replace("\\", "/")
    except Exception as e:
        print(f"❌ Failed to download image {img_url}: {e}")
        return None

def get_all_news_links():
    page = 1
    all_links = []

    while True:
        url = NEWS_LIST_URL.format(page)
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
        except Exception as e:
            print(f"❌ Network error on page {page}: {e}")
            break

        soup = BeautifulSoup(res.text, "html.parser")
        cards = soup.select('.article.in_list.normal.box.col-md-4')

        if not cards:
            break

        print(f"🔎 Page {page}: Found {len(cards)} news articles")

        for card in cards:
            a_tag = card.select_one(".article_image a[href]")
            img_tag = a_tag.find("img") if a_tag else None

            if a_tag:
                news_url = urljoin(BASE_URL, a_tag["href"])
                card_img_url = img_tag["src"] if img_tag else None
                all_links.append({
                    "url": news_url,
                    "card_image_url": card_img_url
                })

        page += 1
        time.sleep(1)

    return all_links

def scrape_news(news_url, card_image_url):
    print(f"📰 Scraping: {news_url}")
    try:
        res = requests.get(news_url, headers=HEADERS, timeout=10)
    except Exception as e:
        print(f"❌ Error scraping {news_url}: {e}")
        return None

    soup = BeautifulSoup(res.text, "html.parser")

    # Title
    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "No title"

    # Author and Date
    meta_tag = soup.select_one("p.meta_text.no_margin")
    author = "No author"
    date = "No date"
    if meta_tag:
        author_tag = meta_tag.find("a")
        if author_tag:
            author = author_tag.text.strip()
        separators = meta_tag.find_all("span", class_="separator")
        if len(separators) >= 1:
            date_node = separators[0].next_sibling
            if date_node:
                date = date_node.strip()

    # Score
    score_tag = soup.select_one(".rate_article .current_rating")
    score = score_tag.get_text(strip=True) if score_tag else "No score"

    # Views
    views_tag = soup.select_one("p.meta_text.eds_viewsComments")
    views = "No view count"
    if views_tag:
        text = views_tag.get_text()
        if "Number of views" in text:
            try:
                views = text.split("Number of views")[1].split("(")[1].split(")")[0].strip()
            except:
                views = "No view count"

    # Content
    content_container = soup.select_one("div.main_content")
    if content_container:
        for tag in content_container.select("h1, .meta_text.no_margin, .rate_article, .meta_text.eds_viewsComments"):
            tag.decompose()
        content_html = str(content_container).strip()
    else:
        content_html = "No content"

    # Images
    all_image_tags = content_container.find_all("img") if content_container else []
    all_image_urls = [urljoin(news_url, img["src"]) for img in all_image_tags if "src" in img.attrs]
    all_images = [download_image(url) for url in all_image_urls]
    featured_image = all_images[0] if all_images else None
    card_image = download_image(card_image_url) if card_image_url else None

    return {
        "url": news_url,
        "title": title,
        "author": author,
        "date": date,
        "score": score,
        "views": views,
        "content": content_html,
        "card_image": card_image,
        "featured_image": featured_image,
        "all_images": all_images,
    }

def main():
    news_links = get_all_news_links()
    print(f"\n📰 Total news articles found: {len(news_links)}\n")

    all_news_data = []
    for news in tqdm(news_links, desc="Scraping News", ncols=80):
        data = scrape_news(news["url"], news.get("card_image_url"))
        if data:
            all_news_data.append(data)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_news_data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ All news articles saved to: {OUTPUT_FILE}")
    print(f"🖼️ Images saved to: {IMAGE_FOLDER}/")

if __name__ == "__main__":
    main()
