import requests
from bs4 import BeautifulSoup
import csv
import time

# 声明全局常量
HEADERS = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
    'Connection': 'keep-alive',
    'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8'
}
URL = 'https://filmarks.com/movies/70258'
BASE_DOMAIN = 'https://filmarks.com'

def download_pages(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status() 
        return response.content
    except requests.RequestException as e:
        print(f"请求异常: {url} -> {e}")
        return None

def parse_html_extra(url):
    """提取展开后的完整长评"""
    time.sleep(1.5) 
    html = download_pages(url)
    if not html:
        return "【长正文抓取失败】"
        
    soup = BeautifulSoup(html, features='lxml')
    page = soup.find('div', attrs={'class': 'p-timeline-mark__main'})
    if not page:
        page = soup.find('div', attrs={'class': 'p-mark-review'})
        
    if not page:
        return "【详情页节点解析失败】"
        
    return page.getText().strip()

def parse_html(html):
    if not html:
        return [], None
        
    soup = BeautifulSoup(html, features='lxml')
    page = soup.find('div', attrs={'class':'p-main-area p-timeline'})
    
    if not page:
        print("未找到主体内容节点，可能遭遇变版或风控。")
        return [], None

    comment_list = []
    
    for i in page.find_all('div', attrs={'class':'p-mark'}):
        # 1. 提取用户名与详情页链接
        heading_div = i.find('div', attrs={'class':'c2-user-m__heading'})
        if not heading_div:
            continue
            
        link_tag = heading_div.find("a")
        if not link_tag or 'href' not in link_tag.attrs:
            continue
            
        user_comment_link = BASE_DOMAIN + link_tag["href"]
        user_comment_name = link_tag.getText().replace('の感想・評価', '').strip()
        
        # 2. 提取发布时间
        time_tag = i.find('time', attrs={'class':'c-media__date'})
        user_comment_time = time_tag.getText().strip() if time_tag else "未知"
        
        # 3. 提取评分
        score_tag = i.find('div', attrs={'class':'c2-rating-s__text'})
        user_comment_star = score_tag.getText().strip() if score_tag else "-"

        # 4. 提取评论正文
        review_div = i.find('div', attrs={'class':'p-mark-review'})
        if not review_div:
            continue
            
        raw_text = review_div.getText()
        
        # 5. 判断是否需要请求详情页展开长评
        if '続きを読む' in raw_text:
            print(f"  -> [详情扩展] 正在展开用户 【{user_comment_name}】 的长篇评论...")
            user_comment = parse_html_extra(user_comment_link)
        else:
            user_comment = raw_text.strip()

        comment_list.append({
            'ID': user_comment_name,
            'Time': user_comment_time,
            'star': user_comment_star,
            'comments': user_comment.replace('\n', ' ').strip()
        })

    # 6. 提取下一页链接
    navi = page.find('div', attrs={'class':'c2-pagination'})
    next_page = navi.find('a', attrs={'class':'c2-pagination__next'}) if navi else None

    if next_page and 'href' in next_page.attrs:
        next_url = BASE_DOMAIN + next_page['href']
        return comment_list, next_url
        
    return comment_list, None

def main():
    url = URL
    with open('comments_filmarks.csv', 'wt', newline='', encoding='utf_8_sig') as comments:
        cw = csv.DictWriter(comments, fieldnames=['ID', 'Time', 'star', 'comments'])
        cw.writeheader()
        
        while url:
            print(f"正在抓取主页: {url}")
            html = download_pages(url)
            if not html:
                break
                
            comment_list, next_url = parse_html(html)
            if comment_list:
                cw.writerows(comment_list)
                comments.flush()  # 强行刷盘，防止表格无数据
                print(f" -> 成功抓取本页 {len(comment_list)} 条记录并写入 CSV。")
            else:
                print(" -> 本页未解析到有效数据。")
                break
                
            url = next_url
            if url:
                print(" -> 主干休眠 3 秒...")
                time.sleep(3)

if __name__ == "__main__":
    main()
