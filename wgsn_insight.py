from playwright.sync_api import Playwright, sync_playwright, expect, BrowserType, Response, BrowserContext
import time, re, requests, json, datetime, time, sys, os, getopt
import logging
import time
import logging, logging.handlers
import time
logging.basicConfig(level=logging.INFO,
                format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                datefmt='%Y-%m-%d-%H.%M.%S',
                filename='wgsn.log',
                filemode='a+')

root_dir = "/Users/ximi.lzx"
col_index = 0
interval = 60 * 60 * 24

opt, args = getopt.getopt(sys.argv[1:], 'd:t:n:', ['root_dir=', 'src_type=', 'interval='])
logging.info(opt)
for arg, value in opt:
    if arg in ('-d', '--user_dir'):
        root_dir = value
    if arg in ('-t', '--src_type'):
        col_index = int(value)
    if arg in ('-n', '--interval'):
        interval = int(value) * 60 * 60 * 24
col_type = ['insight', 'fashion', 'interiors']
col_config = [
    {'list_url': 'https://www.wgsnchina.cn/insight/reports?lang=cs',
     'detail_url': 'https://www.wgsnchina.cn/insight/article', 'account': 'zhangzan.zz@taobao.com',
     'pwd': 'qushiyanjiu2022'},
    {'list_url': 'https://www.wgsnchina.cn/fashion/reports?lang=cs',
     'detail_url': 'https://www.wgsnchina.cn/fashion/article', 'account': 'hy197681@alibaba-inc.com',
     'pwd': 'qushiyanjiu2022'},
    {'list_url': 'https://www.wgsnchina.cn/interiors/reports?lang=cs',
     'detail_url': 'https://www.wgsnchina.cn/interiors/article', 'account': 'jingde.zzw@taobao.com',
     'pwd': 'qushiyanjiu2022'}
    # {'list_url': '', 'detail_url': 'https://www.wgsnchina.cn/consumer/article', 'account': '', 'pwd': 'qushiyanjiu2022'}
]
cookie_dir = f"{root_dir}/playwright/{col_type[col_index]}"
save_path = f"{root_dir}/{col_type[col_index]}"
snapshot_path = f"{root_dir}/snapshot"
if not os.path.isdir(save_path):
    os.makedirs(save_path)
if not os.path.isdir(snapshot_path):
    os.makedirs(snapshot_path)

id_list = []


def get_downloaded_report_list():
    file_name_list = os.listdir(save_path)
    for i in range(0, len(file_name_list)):
        if '.pdf' not in file_name_list[i]:
            continue
        inx = file_name_list[i].find("_")
        file_name_list[i] = file_name_list[i][inx + 1]
    logging.info(file_name_list)
    return file_name_list


def list_response_callback(response: Response, gap=60 * 60 * 24) -> None:
    if "search/content/search" not in response.url:
        return
    logging.info("list_response_callback")
    article_list = json.loads(response.body().decode())["content"]
    cur_time = int(time.time())
    for item in article_list:
        if cur_time - int(item["date"]) >= gap:
            continue
        id_list.append(item["id"])
    logging.info(id_list)


def download_pdf(link, file_list, content=None):
    try:
        result = re.match('http[s]?://media\.wgsnchina\.cn/report_service/(.+)/pdf/(.+)', link)
        id = result.group(1)
        name = result.group(2)
        if name in file_list:
            return
        r = requests.get(url=link)
        logging.info(f"try download {link}, {save_path}/{id}_{name}")
        with open(f'{save_path}/{id}_{name}', 'wb+') as f:
            f.write(r.content)
            f.close()
    except Exception as e:
        logging.error(e)
        return False
    return True


def handle_login(page):
    try:
        logging.info("handle_login")
        page.locator("#userEmail").click()
        page.locator("#userEmail").fill(col_config[col_index]["account"])
        page.get_by_role("button", name="下一步").click()
        time.sleep(2)
        page.locator("#userEmail").click()
        page.locator("#userEmail").fill(col_config[col_index]["account"])
        page.get_by_label("密码").click()
        page.get_by_label("密码").fill(col_config[col_index]["pwd"])
        page.get_by_role("button", name="登录").click()
        time.sleep(5000)
        page.goto(col_config[col_index]["list_url"], wait_until="networkidle")
    except Exception as e:
        page.screenshot(path=f"{snapshot_path}/login.png")
        logging.error(e)


def run(playwright: Playwright) -> None:
    browserType = playwright.chromium
    # context = playwright.chromium.launch(headless=False).new_context()
    context = browserType.launch_persistent_context(user_data_dir=cookie_dir, headless=False, accept_downloads=True)
    page = context.new_page()
    list_url = col_config[col_index]["list_url"]
    page.on("response", lambda response: list_response_callback(response, interval))
    page.goto(list_url, wait_until="networkidle", timeout=100000)
    if "auth/login" in page.url:
        handle_login(page)
    file_list = get_downloaded_report_list()
    success_list = []
    for art_id in id_list:
        page1 = context.new_page()
        try:
            url = f"https://www.wgsnchina.cn/{col_type[col_index]}/article/{art_id}"
            logging.info(f"page goto {url}")
            page1.goto(url, wait_until="domcontentloaded")
            page1.screenshot(path=f"{snapshot_path}/detail_{art_id}.png")
            link = page1.get_attribute('//a[contains(@href, "pdf")]', 'href')
            if link is None:
                logging.error(f"get link failed:{art_id}")
                continue
            time.sleep(2)
            if download_pdf(link, file_list, page1.content()) is True:
                success_list.append(art_id)
            time.sleep(4)
        except Exception as e:
            page1.screenshot(path=f"{snapshot_path}/detail_{art_id}.png")
            logging.error(e)
        page1.close()
    page.close()
    context.close()


with sync_playwright() as playwright:
    try:
        run(playwright)
    except Exception as e:
        logging.error(e)
        raise e
