import json
import logging
import os
from pathlib import Path
from typing import List

from conf import BASE_DIR, DATA_DIR, LOCAL_CHROME_PATH

SOCIAL_MEDIA_DOUYIN = "douyin"
SOCIAL_MEDIA_TENCENT = "tencent"
SOCIAL_MEDIA_TIKTOK = "tiktok"
SOCIAL_MEDIA_BILIBILI = "bilibili"
SOCIAL_MEDIA_KUAISHOU = "kuaishou"

BROWSER_DATA_DIR = DATA_DIR / "browser_data"

_logger = logging.getLogger("browser_persist")


def get_supported_social_media() -> List[str]:
    return [SOCIAL_MEDIA_DOUYIN, SOCIAL_MEDIA_TENCENT, SOCIAL_MEDIA_TIKTOK, SOCIAL_MEDIA_KUAISHOU]


def get_cli_action() -> List[str]:
    return ["upload", "login", "watch"]


async def set_init_script(context):
    stealth_js_path = Path(BASE_DIR / "utils/stealth.min.js")
    await context.add_init_script(path=stealth_js_path)
    return context


def get_user_data_dir(account_file: str) -> Path:
    """从 account_file（旧 .json 路径）推导持久化浏览器用户数据目录。

    例:
      cookies/douyin_uploader/account1.json
      -> browser_data/douyin_uploader/account1/
    """
    p = Path(account_file)
    # 尝试从路径中提取 uploader 和 account_name
    # 路径模式: .../cookies/{uploader}/{account}.json
    parts = p.parts
    uploader = ""
    account_name = p.stem  # 去掉 .json 后缀

    # 向上查找 cookies 目录
    for i, part in enumerate(parts):
        if part == "cookies" and i + 2 < len(parts):
            uploader = parts[i + 1]
            account_name = Path(parts[i + 2]).stem
            break

    if not uploader:
        # 无法解析，使用 account_file 的父目录名 + 文件名
        uploader = p.parent.name
        account_name = p.stem

    user_data_dir = BROWSER_DATA_DIR / uploader / account_name
    user_data_dir.mkdir(parents=True, exist_ok=True)
    return user_data_dir


def _old_storage_state_exists(account_file: str) -> bool:
    """检查旧的 storage_state .json 文件是否存在"""
    return os.path.exists(account_file)


def _user_data_dir_is_empty(user_data_dir: Path) -> bool:
    """检查 user_data_dir 是否为空目录（首次使用）"""
    try:
        return not any(user_data_dir.iterdir())
    except OSError:
        return True


async def migrate_storage_state_if_needed(context, account_file: str) -> bool:
    """如果是首次使用持久化目录，从旧 storage_state .json 迁移 cookies。

    返回 True 表示执行了迁移。
    """
    user_data_dir = get_user_data_dir(account_file)

    if not _old_storage_state_exists(account_file):
        return False
    if not _user_data_dir_is_empty(user_data_dir):
        return False  # 已经有数据，不需要迁移

    _logger.info(f"[browser_persist] 从旧 storage_state 迁移 cookies: {account_file}")

    try:
        with open(account_file, "r", encoding="utf-8") as f:
            state = json.load(f)

        # 迁移 cookies
        cookies = state.get("cookies", [])
        if cookies:
            await context.add_cookies(cookies)
            _logger.info(f"[browser_persist] 迁移了 {len(cookies)} 个 cookie")

        # 迁移 localStorage
        origins = state.get("origins", [])
        for origin in origins:
            origin_url = origin.get("origin", "")
            local_storage = origin.get("localStorage", [])
            if not local_storage or not origin_url:
                continue
            try:
                page = await context.new_page()
                await page.goto(origin_url, wait_until="domcontentloaded", timeout=15000)
                for item in local_storage:
                    name = item.get("name", "")
                    value = item.get("value", "")
                    if name:
                        await page.evaluate(
                            f"localStorage.setItem({json.dumps(name)}, {json.dumps(value)})"
                        )
                await page.close()
            except Exception as e:
                _logger.warning(f"[browser_persist] 迁移 localStorage 失败 ({origin_url}): {e}")

        return True
    except Exception as e:
        _logger.error(f"[browser_persist] 迁移 storage_state 失败: {e}")
        return False


def build_persistent_launch_kwargs(
    headless: bool = False,
    executable_path: str | None = None,
    extra_args: list[str] | None = None,
) -> dict:
    """构建 launch_persistent_context 的启动参数（不含 user_data_dir）。"""
    args = [
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--disable-extensions",
        "--disable-software-rasterizer",
        "--disable-background-networking",
        "--disable-sync",
        "--metrics-recording-only",
        "--no-first-run",
    ]
    if extra_args:
        args.extend(extra_args)

    kwargs: dict = {"headless": headless, "args": args}
    if executable_path or LOCAL_CHROME_PATH:
        kwargs["executable_path"] = executable_path or LOCAL_CHROME_PATH
    else:
        kwargs["channel"] = "chrome"
    return kwargs
