import os
import json
import hashlib
import time
from urllib.parse import urljoin, urlparse

import requests
from tqdm import tqdm
from bs4 import BeautifulSoup

# Constants
BASE_URL = "https://www.taplowgroup.com"
BLOG_LIST_URL = BASE_URL + "/insights/blogs/pgrid/5285/pageid/{}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}
IMAGE_FOLDER = "images"
OUTPUT_FILE = "taplow_blogs_full.json"

# Download and save image locally
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

# Step 1: Get all blog links and their card image URLs
def get_all_blog_links():
    page = 1
    all_links = []

    while True:
        url = BLOG_LIST_URL.format(page)
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
        except Exception as e:
            print(f"❌ Network error on page {page}: {e}")
            break

        soup = BeautifulSoup(res.text, "html.parser")
        cards = soup.select('.article.in_list.normal.box.col-md-4')

        if not cards:
            break

        print(f"🔎 Page {page}: Found {len(cards)} blogs")

        for card in cards:
            a_tag = card.select_one(".article_image a[href]")
            img_tag = a_tag.find("img") if a_tag else None

            if a_tag:
                blog_url = urljoin(BASE_URL, a_tag["href"])
                card_img_url = img_tag["src"] if img_tag else None
                all_links.append({
                    "url": blog_url,
                    "card_image_url": card_img_url
                })

        page += 1
        time.sleep(1)  # throttle like a human

    return all_links

# Step 2: Scrape each blog page
def scrape_blog(blog_url, card_image_url):
    print(f"📝 Scraping: {blog_url}")
    try:
        res = requests.get(blog_url, headers=HEADERS, timeout=10)
    except Exception as e:
        print(f"❌ Error scraping {blog_url}: {e}")
        return None

    soup = BeautifulSoup(res.text, "html.parser")

    # Title
    title_tag = soup.find("h1")
    title = title_tag.text.strip() if title_tag else "No title"

    # Author
    author_tag = soup.select_one("div.author")
    author = author_tag.text.strip() if author_tag else "No author"

    # Date
    date_tag = soup.select_one("div.date")
    date = date_tag.text.strip() if date_tag else "No date"

    # Article image section (score + views + featured image)
    image_section = soup.select_one("div.article_image.left_image")

    # Featured image
    featured_image_tag = image_section.find("img") if image_section else None
    featured_image_url = urljoin(blog_url, featured_image_tag["src"]) if featured_image_tag and "src" in featured_image_tag.attrs else None
    featured_image = download_image(featured_image_url) if featured_image_url else None

    # Score or rating (number of stars or rating value)
    score = None
    if image_section:
        score_tag = image_section.find(class_="rating")  # Adjust this class as per actual HTML
        score = score_tag.text.strip() if score_tag else "No score"

    # Views
    views = None
    if image_section:
        view_tag = image_section.find(class_="readcount")
        views = view_tag.text.strip() if view_tag else "No view count"

    # Content
    content_container = soup.select_one("div.article.details")
    content = content_container.get_text(separator="\n").strip() if content_container else "No content"

    # All images inside content
    all_image_tags = content_container.find_all("img") if content_container else []
    all_image_urls = [urljoin(blog_url, img["src"]) for img in all_image_tags if "src" in img.attrs]
    all_images = [download_image(url) for url in all_image_urls]

    # Card image (from listing page)
    card_image = download_image(card_image_url) if card_image_url else None

    return {
        "url": blog_url,
        "title": title,
        "author": author,
        "date": date,
        "score": score,
        "views": views,
        "content": content,
        "card_image": card_image,
        "featured_image": featured_image,
        "all_images": all_images,
    }

# Step 3: Run everything and save to JSON
def main():
    blog_links = get_all_blog_links()
    print(f"\n📄 Total blogs found: {len(blog_links)}\n")

    all_blog_data = []
    for blog in tqdm(blog_links, desc="Scraping Blogs", ncols=80):
        data = scrape_blog(blog["url"], blog.get("card_image_url"))
        if data:
            all_blog_data.append(data)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_blog_data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ All blogs saved to: {OUTPUT_FILE}")
    print(f"🖼️ Images saved to: {IMAGE_FOLDER}/")

if __name__ == "__main__":
    main()
