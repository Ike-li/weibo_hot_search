from typing import Optional
import requests
from typing import List
from dataclasses import dataclass
import colorama
from colorama import Fore, Style
import logging
from wcwidth import wcswidth, wcwidth
import os
from dotenv import load_dotenv
load_dotenv()


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

cookie = os.getenv("cookie")
if cookie is None:
    raise ValueError("请设置环境变量 cookie")


@dataclass
class HotSearchItem:
    rank: int
    word: str
    num: int
    label_name: Optional[str]
    icon_desc: Optional[str]


def adjust_width(text: str, max_width: int, ellipsis: str = "...", align: str = "left") -> str:
    """调整字符串到指定显示宽度，考虑全角字符，支持有颜色控制码的文本"""
    # 保存原始文本（包含颜色代码）
    original_text = text

    # 去除颜色代码以计算实际显示宽度
    plain_text = text.replace("\x1b[0m", "").replace(Fore.RED, "").replace(Fore.WHITE, "").replace(Fore.GREEN, "")
    plain_text = plain_text.replace(Fore.YELLOW, "").replace(Fore.CYAN, "").replace(Style.RESET_ALL, "")

    current_width = wcswidth(plain_text)
    ellipsis_width = wcswidth(ellipsis)

    # 如果当前宽度等于目标宽度，直接返回原始文本
    if current_width == max_width:
        return original_text

    # 如果当前宽度小于目标宽度，需要添加空格填充
    if current_width < max_width:
        pad = max_width - current_width
        if align == "left":
            return original_text + " " * pad
        if align == "right":
            return " " * pad + original_text
        if align == "center":
            left_pad = pad // 2
            right_pad = pad - left_pad
            return " " * left_pad + original_text + " " * right_pad
        return original_text + " " * pad

    # 需要截断处理
    truncated = []
    available = max_width - ellipsis_width
    if available <= 0:
        return ellipsis[:max_width]

    # 简化处理：移除所有颜色代码，截断纯文本，然后添加颜色代码
    i = 0
    width = 0
    while i < len(plain_text) and width < available:
        char_w = wcwidth(plain_text[i])
        if width + char_w > available:
            break
        width += char_w
        i += 1

    # 截断的纯文本
    truncated_plain = plain_text[:i]

    # 添加颜色代码（简化方式）
    if any(code in original_text for code in [Fore.RED, Fore.WHITE, Fore.GREEN, Fore.YELLOW, Fore.CYAN]):
        color_code = ""
        for code in [Fore.RED, Fore.WHITE, Fore.GREEN, Fore.YELLOW, Fore.CYAN]:
            if code in original_text:
                color_code = code
                break
        result = color_code + truncated_plain + Style.RESET_ALL + ellipsis
    else:
        result = truncated_plain + ellipsis

    return result


class WeiboHotSearch:
    BASE_URL = "https://weibo.com/ajax/side/hotSearch"

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            "Cookie": cookie
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def fetch_hot_search(self, limit: int = 50) -> List[HotSearchItem]:
        try:
            response = self.session.get(self.BASE_URL, timeout=10)
            response.raise_for_status()
            data = response.json()
            hot_searches = data.get("data", {}).get("realtime", [])
            return [
                HotSearchItem(
                    rank=item.get("rank", 0),
                    word=item.get("word", ""),
                    num=item.get("num", 0),
                    label_name=item.get("label_name"),
                    icon_desc=item.get("icon_desc")
                )
                for item in hot_searches[:limit]
            ]
        except requests.RequestException as e:
            logger.error(f"请求失败: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"处理数据失败: {str(e)}")
            return []

    @staticmethod
    def format_output(items: List[HotSearchItem]) -> None:
        colorama.init(autoreset=True)
        if not items:
            logger.warning("没有获取到热搜数据")
            return

        # 计算所需列宽
        # 检查热搜内容最长的词
        max_word_len = max(wcswidth(item.word) for item in items) if items else 30
        word_width = min(max_word_len + 4, 40)  # 动态设置词宽度，但不超过40

        # 设置其他列宽
        rank_width = 6
        num_width = 15
        label_width = 25

        # 分隔符
        separator = " │ "
        sep_width = wcswidth(separator)

        # 总宽度
        total_width = rank_width + word_width + num_width + label_width + sep_width * 3

        # 打印表头
        print(f"\n{Fore.CYAN}微博热搜榜单{Style.RESET_ALL}")
        print(f"{Fore.BLUE}{'=' * total_width}{Style.RESET_ALL}")

        # 列标题 - 添加分隔符
        rank_header = adjust_width("排名", rank_width, align="center")
        word_header = adjust_width("热搜内容", word_width)
        num_header = adjust_width("热度", num_width, align="right")
        label_header = adjust_width("标签", label_width)

        print(f"{Fore.YELLOW}{rank_header}{separator}{word_header}{separator}{num_header}{separator}{label_header}{Style.RESET_ALL}")
        print(f"{Fore.BLUE}{'-' * total_width}{Style.RESET_ALL}")

        # 数据行 - 使用分隔符提高可读性
        for item in items:
            # 排名颜色
            rank_color = Fore.RED if item.rank <= 3 else Fore.WHITE
            rank_text = adjust_width(str(item.rank), rank_width, align="center")
            rank = f"{rank_color}{rank_text}{Style.RESET_ALL}"

            # 热搜内容
            word_text = adjust_width(item.word, word_width)
            word = f"{Fore.WHITE}{word_text}{Style.RESET_ALL}"

            # 热度值
            num_str = f'{item.num:,}' if item.num else ''
            num_text = adjust_width(num_str, num_width, align="right")
            num = f"{Fore.CYAN}{num_text}{Style.RESET_ALL}"

            # 标签组合
            labels = []
            if item.label_name:
                labels.append(item.label_name)
            if item.icon_desc:
                labels.append(item.icon_desc)
            label_text = adjust_width(' '.join(labels), label_width)
            label = f"{Fore.GREEN}{label_text}{Style.RESET_ALL}"

            # 使用分隔符打印行
            print(f"{rank}{separator}{word}{separator}{num}{separator}{label}")

        print(f"{Fore.BLUE}{'=' * total_width}{Style.RESET_ALL}")
        print(f"共 {Fore.YELLOW}{len(items)}{Style.RESET_ALL} 条热搜")


def main():
    weibo = WeiboHotSearch()
    hot_items = weibo.fetch_hot_search()
    weibo.format_output(hot_items)


if __name__ == "__main__":
    main()