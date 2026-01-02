import os
import time
from urllib.parse import quote_plus

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 配置区域：按需修改
EDGE_DRIVER_PATH = r"C:\Users\Administrator\Downloads\edgedriver_win64\msedgedriver.exe"
OUTPUT_FILE = "link.txt"  # 直接从这个文件读取链接

BUTTON_KEYWORDS = [
    "发送",
    "在线咨询",
    "在线客服",
    "点击发送",
    "点击咨询",
]

BUTTON_CLICK_WAIT_SECONDS = 10  # 按钮点击后等待时间
MESSAGES_TO_SEND = [
    "你好",
    "我想要了解一下",
    "手机号码：1345678910",
    "谢谢",
]

MESSAGE_INTERVAL_SECONDS = 10  # 每条消息之间的间隔时间
WAIT_TIMEOUT = 25
HEADLESS = False
SCROLL_MAX_ROUNDS = 5
SCROLL_PAUSE = 0.6

# 等待页面加载完成
def wait_page_ready(driver):
    WebDriverWait(driver, WAIT_TIMEOUT).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )

# 滚动页面触发懒加载
def auto_scroll(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")
    rounds = 0
    while rounds < SCROLL_MAX_ROUNDS:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        rounds += 1

# 查找并点击相关按钮
def click_buy_like_button(driver):
    try:
        time.sleep(3)  # 给页面一点加载时间
        print("🔍 正在查找购买/咨询相关按钮...")

        keywords = [kw.lower() for kw in BUTTON_KEYWORDS]

        candidates = driver.find_elements(
            By.XPATH,
            "//button | //a | //input[@type='button' or @type='submit']"
        )

        target = None

        for el in candidates:
            try:
                text = (el.text or "").strip()
                if not text:
                    text = (el.get_attribute("value") or "").strip()
                if not text:
                    text = (el.get_attribute("aria-label") or "").strip()
                if not text:
                    continue

                text_low = text.lower()

                if any(k in text_low for k in keywords):
                    target = el
                    break
            except Exception:
                continue

        if target:
            label = (
                target.text
                or target.get_attribute("value")
                or target.get_attribute("aria-label")
                or ""
            ).strip()
            print(f"✅ 找到按钮：{label!r}")
            try:
                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", target
                )
                time.sleep(0.8)
                target.click()
                print("👉 已点击按钮，等待页面响应...")
            except Exception as e:
                print(f"⚠ 点击按钮失败：{e!r}")
        else:
            print("⚠ 未找到匹配 BUTTON_KEYWORDS 的按钮，跳过点击。")

    except Exception as e:
        print(f"⚠ click_buy_like_button 出错：{e!r}")

# 查找输入框
def find_message_input(driver):
    try:
        driver.switch_to.default_content()
    except Exception:
        pass
    field = _scan_inputs_in_current_context(driver)
    if field:
        return field

    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    for idx, frame in enumerate(iframes, start=1):
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(frame)
            field = _scan_inputs_in_current_context(driver)
            if field:
                return field
        except Exception as e:
            print(f"⚠ 进入第 {idx} 个 iframe 时出错：{e!r}")
            continue
    return None

def _scan_inputs_in_current_context(driver):
    hint_keywords = [
        "请详细描述",
        "请输入您的问题",
        "请输入问题",
        "留言内容",
        "message",
        "chat",
        "type your message",
    ]
    input_candidates = driver.find_elements(
        By.CSS_SELECTOR,
        "textarea, input[type='text'], input[type='search'], input:not([type])"
    )

    editable_candidates = driver.find_elements(
        By.CSS_SELECTOR,
        "[contenteditable='true'], [contenteditable=''], div[role='textbox'], span[role='textbox']"
    )

    candidates = list(input_candidates) + list(editable_candidates)
    best = None

    for field in candidates:
        try:
            if not (field.is_displayed() and field.is_enabled()):
                continue
            placeholder = (field.get_attribute("placeholder") or "").lower()
            aria = (field.get_attribute("aria-label") or "").lower()
            title = (field.get_attribute("title") or "").lower()
            txt = (field.text or "").lower()
            meta = " ".join([placeholder, aria, title, txt])
            if any(k.lower() in meta for k in hint_keywords):
                return field
            if best is None:
                best = field
        except Exception:
            continue

    return best

# 发送消息
def send_messages_with_interval(driver, messages: list[str], interval_seconds: int):
    if not messages:
        print("ℹ 没有配置任何要发送的消息，跳过发送。")
        return

    field = find_message_input(driver)
    if not field:
        print("⚠ 未找到可用输入框，无法发送消息。")
        return

    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", field)
        time.sleep(0.8)
        field.click()
    except Exception:
        pass

    for idx, msg in enumerate(messages):
        try:
            print(f"✉ 正在发送第 {idx+1} 句消息：{msg!r}")
            field.clear()
            field.send_keys(msg)
            time.sleep(1)
            field.send_keys(Keys.ENTER)
            print("✅ 已发送")
        except Exception as e:
            print(f"⚠ 发送消息出错：{e!r}")

        if idx < len(messages) - 1:
            time.sleep(interval_seconds)

    print("✨ 所有配置的消息已发送完成。")

# 读取链接
def load_links(filename: str) -> list[str]:
    """从文件中读取链接，每行一个"""
    if not os.path.exists(filename):
        print(f"❌ 文件不存在：{filename}")
        return []

    links = []
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            url = line.strip()
            if url:
                links.append(url)
    return links

# 处理单个链接
def handle_single_link(driver, url: str):
    print(f"🔗 打开链接：{url}")
    driver.get(url)
    try:
        wait_page_ready(driver)
    except Exception:
        pass
    click_buy_like_button(driver)
    time.sleep(BUTTON_CLICK_WAIT_SECONDS)
    send_messages_with_interval(driver, MESSAGES_TO_SEND, MESSAGE_INTERVAL_SECONDS)

# 打开所有链接并操作
def open_links_and_interact(driver, links: list[str]):
    if not links:
        print("⚠ 没有可处理的链接。")
        return
    for i, url in enumerate(links, start=1):
        print(f"\n=== 处理第 {i}/{len(links)} 个链接 ===")
        handle_single_link(driver, url)

# 主函数
def main():
    opts = EdgeOptions()
    if HEADLESS:
        opts.add_argument("--headless=new")
        opts.add_argument("--disable-gpu")
    opts.add_argument("--start-maximized")
    opts.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Edge(
        service=EdgeService(executable_path=EDGE_DRIVER_PATH),
        options=opts
    )

    try:
        # 从 link.txt 读取链接
        links_from_file = load_links(OUTPUT_FILE)
        if not links_from_file:
            print("⚠ link.txt 中没有可用链接，流程结束。")
            return

        open_links_and_interact(driver, links_from_file)

    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()

