# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import inspect
import os
from datetime import datetime
from pathlib import Path

from patchright.async_api import Page
from patchright.async_api import Playwright
from patchright.async_api import async_playwright

from conf import BASE_DIR, DEBUG_MODE, LOCAL_CHROME_HEADLESS, LOCAL_CHROME_PATH
from uploader.base_video import BaseVideoUploader
from utils.base_social_media import set_init_script, get_user_data_dir, migrate_storage_state_if_needed, build_persistent_launch_kwargs
from utils.log import tencent_logger

TENCENT_LOGIN_URL = "https://channels.weixin.qq.com"
TENCENT_UPLOAD_URL = "https://channels.weixin.qq.com/platform/post/create"
TENCENT_MANAGE_URL = "https://channels.weixin.qq.com/platform/post/list"
TENCENT_PUBLISH_STRATEGY_IMMEDIATE = "immediate"
TENCENT_PUBLISH_STRATEGY_SCHEDULED = "scheduled"


def _msg(emoji: str, text: str) -> str:
    return f"{emoji} {text}"


def _resolve_account_file(account_file: str | Path) -> str:
    path = Path(account_file).expanduser()
    if path.is_absolute():
        return str(path)

    if len(path.parts) == 1:
        return str((Path(BASE_DIR) / "cookies" / "tencent_uploader" / path).resolve())

    return str(path.resolve())


async def _emit_qrcode_callback(qrcode_callback, payload: dict):
    if not qrcode_callback:
        return

    callback_result = qrcode_callback(payload)
    if inspect.isawaitable(callback_result):
        await callback_result


def _build_login_result(
    success: bool,
    status: str,
    message: str,
    account_file: str,
    qrcode: dict | None = None,
    current_url: str = "",
) -> dict:
    return {
        "success": success,
        "status": status,
        "message": message,
        "account_file": str(account_file),
        "qrcode": qrcode,
        "current_url": current_url,
    }


def _build_launch_kwargs(headless: bool) -> dict:
    launch_kwargs = {
        "headless": headless,
        "args": ["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox", "--disable-extensions", "--disable-software-rasterizer"],
    }
    if LOCAL_CHROME_PATH:
        launch_kwargs["executable_path"] = LOCAL_CHROME_PATH
    else:
        launch_kwargs["channel"] = "chrome"
    return launch_kwargs


def _get_qrcode_utils():
    from utils.login_qrcode import build_login_qrcode_path
    from utils.login_qrcode import decode_qrcode_from_path
    from utils.login_qrcode import print_terminal_qrcode
    from utils.login_qrcode import remove_qrcode_file
    from utils.login_qrcode import save_data_url_image

    return {
        "build_login_qrcode_path": build_login_qrcode_path,
        "decode_qrcode_from_path": decode_qrcode_from_path,
        "print_terminal_qrcode": print_terminal_qrcode,
        "remove_qrcode_file": remove_qrcode_file,
        "save_data_url_image": save_data_url_image,
    }


def format_str_for_short_title(origin_title: str) -> str:
    allowed_special_chars = "《》“”:+?%°"
    filtered_chars = [char if char.isalnum() or char in allowed_special_chars else " " if char == "," else "" for char in origin_title]
    formatted_string = "".join(filtered_chars)

    if len(formatted_string) > 16:
        formatted_string = formatted_string[:16]
    elif len(formatted_string) < 6:
        formatted_string += " " * (6 - len(formatted_string))

    return formatted_string


async def _check_tencent_cookie_inline(page: Page) -> bool:
    """在当前页面上检测视频号登录状态（不新建浏览器）"""
    # 方法 1：检查 Wujie shadow DOM
    login_status = await page.evaluate("""() => {
        const wujieApp = document.querySelector('wujie-app');
        if (!wujieApp || !wujieApp.shadowRoot) {
            return { hasWujie: false, needLogin: null };
        }

        const sr = wujieApp.shadowRoot;

        // 检查是否有扫码登录提示
        const loginElements = sr.querySelectorAll('*');
        for (const el of loginElements) {
            const text = (el.textContent || '').trim();
            if (text.includes('扫码登录') && el.offsetWidth > 0) {
                return { hasWujie: true, needLogin: true };
            }
        }

        // 检查是否有发表视频按钮（已登录标志）
        const buttons = sr.querySelectorAll('button');
        for (const btn of buttons) {
            const text = (btn.textContent || '').trim();
            if (text.includes('发表视频') || text.includes('发表')) {
                return { hasWujie: true, needLogin: false };
            }
        }

        return { hasWujie: true, needLogin: null };
    }""")

    # 如果 shadow DOM 明确判断了登录状态，直接返回
    if login_status.get("needLogin") is True:
        tencent_logger.info(_msg("🥹", "cookie 已失效，得重新登录一下"))
        return False
    if login_status.get("needLogin") is False:
        tencent_logger.success(_msg("🥳", "cookie 有效"))
        return True

    # 方法 2：降级到传统页面选择器
    if await page.get_by_text("扫码登录", exact=True).count():
        tencent_logger.info(_msg("🥹", "cookie 已失效，得重新登录一下"))
        return False

    # 如果有「发表视频」文字或「发表」按钮，说明已登录
    if await page.get_by_text("发表视频", exact=True).count():
        tencent_logger.success(_msg("🥳", "cookie 有效"))
        return True

    if await page.get_by_role("button", name="发表").count():
        tencent_logger.success(_msg("🥳", "cookie 有效"))
        return True

    # 无法确定，按失效处理
    tencent_logger.info(_msg("🥹", "cookie 已失效，得重新登录一下"))
    return False


async def cookie_auth(account_file):
    account_file = _resolve_account_file(account_file)
    user_data_dir = get_user_data_dir(account_file)
    async with async_playwright() as playwright:
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            **build_persistent_launch_kwargs(headless=True),
        )
        try:
            await migrate_storage_state_if_needed(context, account_file)
            context = await set_init_script(context)
            page = await context.new_page()
            await page.goto("https://channels.weixin.qq.com/platform")
            # 等待页面加载（Wujie 微前端需要时间渲染）
            await asyncio.sleep(8)
            return await _check_tencent_cookie_inline(page)
        except Exception as exc:
            tencent_logger.warning(_msg("😵", f"cookie 校验时出错，按失效处理: {exc}"))
            return False
        finally:
            await context.close()


async def _extract_tencent_qrcode_src(page: Page) -> str:
    """提取登录二维码 - 支持 Wujie shadow DOM 和传统页面"""

    # 优先检查 Wujie shadow DOM 中的二维码
    qrcode_src = await page.evaluate("""() => {
        const wujieApp = document.querySelector('wujie-app');
        if (!wujieApp || !wujieApp.shadowRoot) return null;

        const sr = wujieApp.shadowRoot;
        const imgs = sr.querySelectorAll('img');
        for (const img of imgs) {
            const src = img.getAttribute('src') || '';
            if (src.startsWith('data:image/') && img.offsetWidth > 50) {
                return src;
            }
        }
        return null;
    }""")

    if qrcode_src:
        return qrcode_src

    # 传统 iframe 方式
    if hasattr(page, "frame_locator"):
        try:
            iframe_locator = page.frame_locator('[src*="login-for-iframe"]')
            qr_code_img = iframe_locator.locator('div#app img.qrcode').first
            await qr_code_img.wait_for(state="visible", timeout=15000)
            src = await qr_code_img.get_attribute("src")
            if src and src.startswith("data:image/"):
                return src
        except Exception:
            pass

    # 降级到直接页面选择器
    selector_candidates = [
        "div.login-qrcode-wrap img.qrcode",
        "div.qrcode-wrap img.qrcode",
        "img.qrcode",
        'img[src^="data:image/"]',
    ]
    for selector in selector_candidates:
        qr_code_img = page.locator(selector).first
        try:
            if not await qr_code_img.count() or not await qr_code_img.is_visible():
                continue
            src = await qr_code_img.get_attribute("src")
            if src and src.startswith("data:image/"):
                return src
        except Exception:
            continue

    raise RuntimeError("未获取到视频号登录二维码地址")


async def _save_tencent_qrcode(page: Page, account_file: str, previous_qrcode_path: Path | None = None, qrcode_callback=None) -> dict:
    qrcode_utils = _get_qrcode_utils()
    qrcode_src = await _extract_tencent_qrcode_src(page)
    qrcode_path = qrcode_utils["save_data_url_image"](
        qrcode_src,
        qrcode_utils["build_login_qrcode_path"](account_file, suffix="tencent_login_qrcode"),
    )
    if previous_qrcode_path and previous_qrcode_path != qrcode_path:
        if qrcode_utils["remove_qrcode_file"](previous_qrcode_path):
            tencent_logger.info(_msg("🧹", f"临时二维码文件已清理: {previous_qrcode_path}"))

    tencent_logger.info(_msg("🖼️", f"二维码已经准备好啦，已保存到: {qrcode_path}"))
    qrcode_content = qrcode_utils["decode_qrcode_from_path"](qrcode_path)
    if qrcode_content:
        qrcode_utils["print_terminal_qrcode"](qrcode_content, qrcode_path, "微信")
    else:
        tencent_logger.warning(
            _msg(
                "😵",
                f"没能从二维码图片里解析出可打印内容，所以这次没法在终端重绘二维码；请直接打开 {qrcode_path} 扫码",
            )
        )

    qrcode_info = {
        "image_path": str(qrcode_path),
        "image_data_url": qrcode_src,
    }
    await _emit_qrcode_callback(qrcode_callback, qrcode_info)
    return qrcode_info


async def _is_tencent_login_completed(page: Page) -> bool:
    """检查是否登录完成 - 同时检查 Wujie shadow DOM 和传统页面"""
    # 先检查 Wujie shadow DOM
    login_completed = await page.evaluate("""() => {
        const wujieApp = document.querySelector('wujie-app');
        if (!wujieApp || !wujieApp.shadowRoot) return null;

        const sr = wujieApp.shadowRoot;

        // 检查是否有发表视频按钮（已登录标志）
        const buttons = sr.querySelectorAll('button');
        for (const btn of buttons) {
            const text = (btn.textContent || '').trim();
            if (text.includes('发表视频') || text.includes('发表')) {
                return true;
            }
        }

        // 检查是否有扫码登录（未登录标志）
        const allEls = sr.querySelectorAll('*');
        for (const el of allEls) {
            const text = (el.textContent || '').trim();
            if (text.includes('扫码登录') && el.offsetWidth > 0) {
                return false;
            }
        }

        return null;  // 不确定
    }""")

    if login_completed is True:
        return True
    if login_completed is False:
        return False

    # 降级到传统页面检查
    publish_markers = [
        page.locator('div:has-text("发表视频")').first,
        page.locator('button:has-text("发表")').first,
        page.locator('button:has-text("保存草稿")').first,
    ]
    for marker in publish_markers:
        try:
            if await marker.count() and await marker.is_visible():
                return True
        except Exception:
            continue

    if not (page.url.startswith(TENCENT_UPLOAD_URL) or page.url.startswith(TENCENT_MANAGE_URL)):
        return False

    login_markers = [
        page.locator("div.login-qrcode-wrap").first,
        page.locator("div.qrcode-wrap").first,
        page.locator("img.qrcode").first,
        page.locator('span:has-text("微信扫码登录 视频号助手")').first,
    ]
    for marker in login_markers:
        try:
            if await marker.count() and await marker.is_visible():
                return False
        except Exception:
            continue

    return True


async def _is_tencent_qrcode_expired(page: Page) -> bool:
    tip_selectors = [
        'div.mask.show p.refresh-tip:has-text("二维码已过期，点击刷新")',
        'div.mask.show p.refresh-tip:has-text("网络不可用，点击刷新")',
        'p.refresh-tip:has-text("二维码已过期，点击刷新")',
        'p.refresh-tip:has-text("网络不可用，点击刷新")',
    ]
    for selector in tip_selectors:
        tip = page.locator(selector).first
        try:
            if await tip.count() and await tip.is_visible():
                return True
        except Exception:
            continue
    return False


async def _is_tencent_qrcode_scanned(page: Page) -> bool:
    """检查二维码是否已被扫描 - 支持 Wujie shadow DOM"""
    # 先检查 shadow DOM
    scanned = await page.evaluate("""() => {
        const wujieApp = document.querySelector('wujie-app');
        if (!wujieApp || !wujieApp.shadowRoot) return false;

        const sr = wujieApp.shadowRoot;
        const allEls = sr.querySelectorAll('*');
        for (const el of allEls) {
            const text = (el.textContent || '').trim();
            if ((text.includes('已扫码') || text.includes('确认')) && el.offsetWidth > 0) {
                return true;
            }
        }
        return false;
    }""")

    if scanned:
        return True

    # 降级到传统选择器
    scanned_tips = [
        'div.qr-tip div:has-text("已扫码")',
        'div.qr-tip div:has-text("需在手机上进行确认")',
    ]
    for selector in scanned_tips:
        tip = page.locator(selector).first
        try:
            if await tip.count() and await tip.is_visible():
                return True
        except Exception:
            continue
    return False


async def _refresh_tencent_qrcode(page: Page) -> None:
    """刷新过期二维码 - 支持 Wujie shadow DOM"""
    # 先在 shadow DOM 中查找刷新按钮
    refresh_info = await page.evaluate("""() => {
        const wujieApp = document.querySelector('wujie-app');
        if (!wujieApp || !wujieApp.shadowRoot) return null;

        const sr = wujieApp.shadowRoot;
        const allEls = sr.querySelectorAll('*');
        for (const el of allEls) {
            const text = (el.textContent || '').trim();
            if ((text.includes('刷新') || text.includes('重新获取')) && el.offsetWidth > 0) {
                const style = getComputedStyle(el);
                if (style.cursor === 'pointer') {
                    const rect = el.getBoundingClientRect();
                    return {
                        x: Math.round(rect.x + rect.width / 2),
                        y: Math.round(rect.y + rect.height / 2),
                    };
                }
            }
        }
        return null;
    }""")

    if refresh_info:
        await page.mouse.click(refresh_info['x'], refresh_info['y'])
        return

    # 降级到传统选择器
    visible_refresh_selectors = [
        "div.login-qrcode-wrap div.mask.show div.refresh-wrap",
        "div.login-qrcode-wrap div.mask.show .refresh-wrap",
    ]
    for selector in visible_refresh_selectors:
        refresh_wrap = page.locator(selector).first
        try:
            if not await refresh_wrap.count() or not await refresh_wrap.is_visible():
                continue
            await refresh_wrap.click()
            return
        except Exception:
            continue

    tip_selectors = [
        'div.mask.show p.refresh-tip:has-text("二维码已过期，点击刷新")',
        'div.mask.show p.refresh-tip:has-text("网络不可用，点击刷新")',
        'p.refresh-tip:has-text("二维码已过期，点击刷新")',
        'p.refresh-tip:has-text("网络不可用，点击刷新")',
    ]
    for selector in tip_selectors:
        tip = page.locator(selector).first
        try:
            if not await tip.count() or not await tip.is_visible():
                continue
            refresh_wrap = tip.locator("xpath=ancestor::div[contains(@class, 'refresh-wrap')]").first
            if await refresh_wrap.count():
                await refresh_wrap.click()
            else:
                await tip.click()
            return
        except Exception:
            continue

    fallback_refresh = page.locator("div.login-qrcode-wrap div.refresh-wrap").first
    if await fallback_refresh.count():
        await fallback_refresh.click()
        return

    raise RuntimeError("未找到可点击的视频号二维码刷新区域")


async def _wait_for_tencent_login(
    page: Page,
    account_file: str,
    qrcode_info: dict,
    qrcode_callback=None,
    poll_interval: int = 3,
    max_checks: int = 100,
) -> dict:
    qrcode_path = Path(qrcode_info["image_path"])
    scanned_logged = False
    for _ in range(max_checks):
        if await _is_tencent_login_completed(page):
            tencent_logger.info(_msg("🥳", f"扫码成功，已经跳转到登录后页面: {page.url}"))
            return _build_login_result(True, "success", "视频号扫码登录成功", account_file, qrcode_info, page.url)

        if not scanned_logged and await _is_tencent_qrcode_scanned(page):
            tencent_logger.info(_msg("📱", "已经扫码啦，还差手机端确认一下"))
            scanned_logged = True

        if await _is_tencent_qrcode_expired(page):
            tencent_logger.warning(_msg("😵", "二维码失效了，小人马上去刷新"))
            await _refresh_tencent_qrcode(page)
            await asyncio.sleep(1)
            qrcode_info = await _save_tencent_qrcode(
                page,
                account_file,
                previous_qrcode_path=qrcode_path,
                qrcode_callback=qrcode_callback,
            )
            qrcode_path = Path(qrcode_info["image_path"])

        await asyncio.sleep(poll_interval)

    return _build_login_result(False, "timeout", "等待视频号扫码登录超时", account_file, qrcode_info, page.url)


async def tencent_cookie_gen(
    account_file,
    qrcode_callback=None,
    poll_interval: int = 3,
    max_checks: int = 100,
    headless: bool = LOCAL_CHROME_HEADLESS,
):
    account_file = _resolve_account_file(account_file)
    user_data_dir = get_user_data_dir(account_file)
    Path(account_file).parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as playwright:
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            **build_persistent_launch_kwargs(headless=headless),
        )
        qrcode_path = None
        result = _build_login_result(False, "failed", "视频号登录失败", account_file)
        try:
            page = await context.new_page()
            await page.goto(TENCENT_LOGIN_URL)
            qrcode_info = await _save_tencent_qrcode(page, account_file, qrcode_callback=qrcode_callback)
            qrcode_path = Path(qrcode_info["image_path"])
            tencent_logger.info(_msg("🧍", "请扫码，小人正在耐心等待登录完成"))
            result = await _wait_for_tencent_login(
                page,
                account_file,
                qrcode_info,
                qrcode_callback=qrcode_callback,
                poll_interval=poll_interval,
                max_checks=max_checks,
            )
            if result["success"]:
                await asyncio.sleep(2)
                # 持久化上下文自动保存状态；同时导出 storage_state 作为备份
                try:
                    await context.storage_state(path=account_file)
                except Exception:
                    pass
                # 用当前 context 做 cookie 校验（避免开第二个浏览器抢占 user_data_dir）
                verify_page = await context.new_page()
                try:
                    await verify_page.goto("https://channels.weixin.qq.com/platform")
                    await asyncio.sleep(8)
                    if not await _check_tencent_cookie_inline(verify_page):
                        result = _build_login_result(
                            False,
                            "cookie_invalid",
                            "视频号扫码流程结束，但 cookie 校验失败",
                            account_file,
                            qrcode_info,
                            page.url,
                        )
                finally:
                    await verify_page.close()
            return result
        except Exception as exc:
            result = _build_login_result(
                False,
                "failed",
                str(exc),
                account_file,
                current_url=page.url if "page" in locals() else "",
            )
            return result
        finally:
            qrcode_utils = _get_qrcode_utils()
            if qrcode_utils["remove_qrcode_file"](qrcode_path):
                tencent_logger.info(_msg("🧹", f"临时二维码文件已清理: {qrcode_path}"))
            if not result["success"]:
                tencent_logger.error(_msg("😢", f"登录失败: {result['message']}"))
            await context.close()


async def tencent_setup(
    account_file,
    handle=False,
    return_detail=False,
    qrcode_callback=None,
    headless: bool = LOCAL_CHROME_HEADLESS,
):
    account_file = _resolve_account_file(account_file)
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            result = _build_login_result(False, "cookie_invalid", "cookie文件不存在或已失效", account_file)
            return result if return_detail else False

        tencent_logger.info(_msg("🥹", "cookie 失效了，准备打开浏览器重新登录"))
        result = await tencent_cookie_gen(account_file, qrcode_callback=qrcode_callback, headless=headless)
        return result if return_detail else result["success"]

    result = _build_login_result(True, "cookie_valid", "cookie有效", account_file)
    return result if return_detail else True


async def get_tencent_cookie(account_file, qrcode_callback=None, headless: bool = LOCAL_CHROME_HEADLESS):
    return await tencent_cookie_gen(account_file, qrcode_callback=qrcode_callback, headless=headless)


async def weixin_setup(
    account_file,
    handle=False,
    return_detail=False,
    qrcode_callback=None,
    headless: bool = LOCAL_CHROME_HEADLESS,
):
    return await tencent_setup(
        account_file,
        handle=handle,
        return_detail=return_detail,
        qrcode_callback=qrcode_callback,
        headless=headless,
    )


class TencentBaseUploader(BaseVideoUploader):
    def __init__(
        self,
        publish_date: datetime | int,
        account_file,
        publish_strategy: str = TENCENT_PUBLISH_STRATEGY_IMMEDIATE,
        debug: bool = DEBUG_MODE,
        headless: bool = LOCAL_CHROME_HEADLESS,
    ):
        self.publish_date = publish_date
        self.account_file = _resolve_account_file(account_file)
        self.publish_strategy = publish_strategy
        self.debug = debug
        self.headless = headless
        self.local_executable_path = LOCAL_CHROME_PATH

    async def validate_base_args(self):
        if not os.path.exists(self.account_file):
            raise RuntimeError(f"cookie文件不存在，请先完成视频号登录: {self.account_file}")
        if not await cookie_auth(self.account_file):
            raise RuntimeError(f"cookie文件已失效，请先完成视频号登录: {self.account_file}")
        if self.publish_strategy not in {TENCENT_PUBLISH_STRATEGY_IMMEDIATE, TENCENT_PUBLISH_STRATEGY_SCHEDULED}:
            raise ValueError(f"不支持的发布策略: {self.publish_strategy}")

        if self.publish_strategy == TENCENT_PUBLISH_STRATEGY_SCHEDULED:
            self.publish_date = self.validate_publish_date(self.publish_date)
        else:
            self.publish_date = 0

    async def set_schedule_time_tencent(self, page: Page, publish_date: datetime):
        """设置定时发表 - 在 Wujie shadow DOM 中查找定时选项"""
        try:
            # 在 shadow DOM 中查找「定时」选项
            schedule_info = await page.evaluate("""() => {
                const wujieApp = document.querySelector('wujie-app');
                if (!wujieApp || !wujieApp.shadowRoot) return null;

                const sr = wujieApp.shadowRoot;
                const allEls = sr.querySelectorAll('*');
                for (const el of allEls) {
                    const text = (el.textContent || '').trim();
                    if (text === '定时' && el.offsetWidth > 0) {
                        const rect = el.getBoundingClientRect();
                        return {
                            x: Math.round(rect.x + rect.width / 2),
                            y: Math.round(rect.y + rect.height / 2),
                        };
                    }
                }
                return null;
            }""")

            if schedule_info:
                await page.mouse.click(schedule_info['x'], schedule_info['y'])
                await asyncio.sleep(1)
                # 点击时间输入框
                time_input_info = await page.evaluate("""() => {
                    const wujieApp = document.querySelector('wujie-app');
                    if (!wujieApp || !wujieApp.shadowRoot) return null;

                    const sr = wujieApp.shadowRoot;
                    const inputs = sr.querySelectorAll('input');
                    for (const inp of inputs) {
                        const ph = (inp.placeholder || '');
                        if (ph.includes('时间') || ph.includes('日期')) {
                            const rect = inp.getBoundingClientRect();
                            return {
                                x: Math.round(rect.x + rect.width / 2),
                                y: Math.round(rect.y + rect.height / 2),
                            };
                        }
                    }
                    return null;
                }""")

                if time_input_info:
                    await page.mouse.click(time_input_info['x'], time_input_info['y'])
                    await page.keyboard.press("Control+KeyA")
                    await page.keyboard.type(publish_date.strftime("%Y-%m-%d %H:%M"))
                    await page.keyboard.press("Enter")
                    await asyncio.sleep(1)
            else:
                # 降级方案
                label_element = page.locator("label").filter(has_text="定时").nth(1)
                if await label_element.count():
                    await label_element.click()
        except Exception as e:
            tencent_logger.warning(_msg("😵", f"设置定时发表失败: {e}"))

    async def open_upload_page(self, page: Page) -> None:
        """打开上传页面 - 必须先导航到 /platform，然后点击「发表视频」进入上传表单。
        
        直接导航到 /platform/post/create 不会触发 Wujie 子应用渲染上传表单，
        必须通过点击「发表视频」按钮来进入上传页面。
        """
        await page.goto("https://channels.weixin.qq.com/platform")
        # 等待 Wujie shadow DOM 渲染「发表视频」按钮（需要足够时间加载微前端）
        # 渐进式等待：每秒检查一次，最多 15 秒
        for _ in range(15):
            has_publish_btn = await page.evaluate("""() => {
                const wujieApp = document.querySelector('wujie-app');
                if (!wujieApp || !wujieApp.shadowRoot) return false;
                const sr = wujieApp.shadowRoot;
                const buttons = sr.querySelectorAll('button');
                for (const btn of buttons) {
                    const text = (btn.textContent || '').trim();
                    if (text.includes('发表视频') || text.includes('发表')) {
                        return btn.offsetWidth > 0;
                    }
                }
                return false;
            }""")
            if has_publish_btn:
                break
            await asyncio.sleep(1)

    async def _dismiss_guide_popups(self, page: Page) -> None:
        """关闭视频号 Wujie Shadow DOM 中的引导弹窗（'我知道了'等）"""
        for round_idx in range(3):  # 最多关闭 3 轮弹窗
            dismissed = await page.evaluate("""() => {
                const app = document.querySelector('wujie-app');
                if (!app || !app.shadowRoot) return 0;
                const sr = app.shadowRoot;
                let count = 0;
                // 只点击"我知道了"等确认按钮来关闭弹窗
                // ⚠️ 不要用 .remove() 删除 overlay 元素，可能误删 Wujie 的渲染容器
                const btns = sr.querySelectorAll('button');
                for (const btn of btns) {
                    const text = (btn.textContent || '').trim();
                    if (text.includes('我知道了') || text.includes('知道了') || text.includes('关闭') || text.includes('下一步')) {
                        btn.click();
                        count++;
                    }
                }
                return count;
            }""")
            if dismissed > 0:
                tencent_logger.info(_msg("🧹", f"关闭了 {dismissed} 个引导弹窗（第{round_idx+1}轮）"))
                await asyncio.sleep(0.5)
            else:
                break

    async def _click_publish_video_button(self, page: Page) -> None:
        """在 Wujie shadow DOM 中点击「发表视频」按钮，进入上传表单页面"""
        # 先关闭可能存在的引导弹窗
        await self._dismiss_guide_popups(page)

        # 直接在 JS 中点击按钮（比 mouse.click 更可靠，避免 Shadow DOM 点击分发问题）
        click_result = await page.evaluate("""() => {
            const wujieApp = document.querySelector('wujie-app');
            if (!wujieApp || !wujieApp.shadowRoot) return { found: false, reason: 'no wujie shadowRoot' };

            const sr = wujieApp.shadowRoot;
            const buttons = sr.querySelectorAll('button');
            for (const btn of buttons) {
                const text = (btn.textContent || '').trim();
                if (text.includes('发表视频') || text === '发表') {
                    const rect = btn.getBoundingClientRect();
                    // 直接用 JS click 而非返回坐标用 mouse.click
                    btn.click();
                    return { found: true, text: text, x: Math.round(rect.x + rect.width / 2), y: Math.round(rect.y + rect.height / 2) };
                }
            }
            // 列出所有按钮文本以便调试
            const allTexts = Array.from(buttons).map(b => (b.textContent || '').trim().substring(0, 20));
            return { found: false, allBtns: allTexts };
        }""")

        if click_result and click_result.get('found'):
            tencent_logger.info(_msg("🧭", f"找到「{click_result['text']}」按钮，点击进入上传页"))
        else:
            tencent_logger.warning(_msg("😵", f"未找到「发表视频」按钮: {click_result}"))
            # 降级：尝试 mouse.click 默认坐标
            await page.mouse.click(1228, 505)
            await asyncio.sleep(3)

        # 等待 URL 变化到上传页面 + Wujie 子应用渲染上传表单
        await asyncio.sleep(4)
        # 验证上传表单是否渲染
        for attempt in range(15):
            has_upload = await page.evaluate("""() => {
                const wujieApp = document.querySelector('wujie-app');
                if (!wujieApp || !wujieApp.shadowRoot) return false;
                const sr = wujieApp.shadowRoot;
                return sr.querySelectorAll('.ant-upload').length > 0 ||
                       sr.querySelectorAll('input[type="file"]').length > 0;
            }""")
            if has_upload:
                tencent_logger.info(_msg("✅", "上传表单已渲染"))
                return
            await asyncio.sleep(1)
        tencent_logger.warning(_msg("⚠️", "点击「发表视频」后未检测到上传表单，继续尝试"))

    async def upload_video_file(self, page: Page, file_path: str) -> None:
        """通过 file_chooser 上传视频文件（Wujie shadow DOM 方式）"""
        # 先点击「发表视频」按钮进入上传表单
        await self._click_publish_video_button(page)

        # 在 Wujie shadow DOM 中找到 ant-upload-drag 区域并点击
        upload_area_info = await page.evaluate("""() => {
            const wujieApp = document.querySelector('wujie-app');
            if (!wujieApp || !wujieApp.shadowRoot) return null;

            const sr = wujieApp.shadowRoot;
            const uploadAreas = sr.querySelectorAll('.ant-upload-drag, .ant-upload');
            for (const area of uploadAreas) {
                const rect = area.getBoundingClientRect();
                if (rect.width > 50 && rect.height > 50) {
                    return {
                        x: Math.round(rect.x + rect.width / 2),
                        y: Math.round(rect.y + rect.height / 2),
                        className: (area.className || '').toString().substring(0, 60),
                    };
                }
            }
            return null;
        }""")

        if upload_area_info:
            tencent_logger.info(_msg("📤", f"找到上传区域，点击选择文件: {upload_area_info['className']}"))
            # 等待一小段时间确保 Shadow DOM 内的 JS 事件绑定完成
            await asyncio.sleep(1)
            try:
                async with page.expect_file_chooser(timeout=10000) as fc_info:
                    await page.mouse.click(upload_area_info['x'], upload_area_info['y'])
                file_chooser = await fc_info.value
                await file_chooser.set_files(file_path)
                tencent_logger.info(_msg("✅", "视频文件已选择"))
            except Exception as e:
                tencent_logger.warning(_msg("⚠️", f"file_chooser 触发失败，尝试 CDP 方式: {e}"))
                # 降级方案：使用 CDP (Chrome DevTools Protocol) 直接设置 Shadow DOM 中的 file input
                try:
                    cdp = await page.context.new_cdp_session(page)
                    doc = await cdp.send("DOM.getDocument", {"depth": -1, "pierce": True})
                    nodes = await cdp.send("DOM.querySelectorAll", {
                        "nodeId": doc["root"]["nodeId"],
                        "selector": "input[type='file']"
                    })
                    node_ids = nodes.get("nodeIds", [])
                    if node_ids:
                        await cdp.send("DOM.setFileInputFiles", {
                            "files": [file_path],
                            "nodeId": node_ids[0],
                        })
                        tencent_logger.info(_msg("✅", "通过 CDP 方式设置视频文件成功"))
                    else:
                        raise RuntimeError("CDP 未找到 input[type=file] 元素")
                except Exception as cdp_err:
                    raise RuntimeError(f"file_chooser 和 CDP 方式均失败: {e} / {cdp_err}")
        else:
            # 降级方案：尝试传统的 input[type=file]
            tencent_logger.warning(_msg("😵", "未找到 Wujie 上传区域，尝试传统 file input"))
            file_input = page.locator('input[type="file"]')
            if await file_input.count():
                await file_input.set_input_files(file_path)
            else:
                raise RuntimeError("无法找到视频上传入口，请检查视频号页面结构是否变更")

    async def set_short_title(self, page: Page, title: str, short_title: str | None = None) -> None:
        """设置短标题 - 在 Wujie shadow DOM 中查找输入框"""
        input_info = await page.evaluate("""() => {
            const wujieApp = document.querySelector('wujie-app');
            if (!wujieApp || !wujieApp.shadowRoot) return null;

            const sr = wujieApp.shadowRoot;
            // 查找短标题输入框（placeholder 包含"6-16"）
            const inputs = sr.querySelectorAll('input[type="text"]');
            for (const inp of inputs) {
                const ph = (inp.placeholder || '').toLowerCase();
                if (ph.includes('6-16') || ph.includes('概括') || ph.includes('短标题')) {
                    const rect = inp.getBoundingClientRect();
                    return {
                        x: Math.round(rect.x + rect.width / 2),
                        y: Math.round(rect.y + rect.height / 2),
                        placeholder: inp.placeholder || '',
                    };
                }
            }
            return null;
        }""")

        if input_info:
            tencent_logger.info(_msg("📝", f"找到短标题输入框: {input_info['placeholder']}"))
            await page.mouse.click(input_info['x'], input_info['y'])
            await asyncio.sleep(0.5)
            await page.keyboard.press("Control+KeyA")
            await page.keyboard.press("Backspace")
            await page.keyboard.type(short_title or format_str_for_short_title(title))
        else:
            # 降级方案
            tencent_logger.warning(_msg("😵", "未找到短标题输入框，尝试传统选择器"))
            short_title_element = (
                page.get_by_text("短标题", exact=True)
                .locator("..")
                .locator("xpath=following-sibling::div")
                .locator('span input[type="text"]')
            )
            if await short_title_element.count():
                await short_title_element.fill(short_title or format_str_for_short_title(title))

    async def fill_title_and_tags(self, page: Page) -> None:
        """填写标题和标签 - 在 Wujie shadow DOM 中查找编辑区域"""
        # 查找标题/描述编辑区域
        editor_info = await page.evaluate("""() => {
            const wujieApp = document.querySelector('wujie-app');
            if (!wujieApp || !wujieApp.shadowRoot) return null;

            const sr = wujieApp.shadowRoot;
            // 查找 contenteditable 或 div.input-editor
            const editors = sr.querySelectorAll('[contenteditable="true"], .input-editor');
            for (const el of editors) {
                const rect = el.getBoundingClientRect();
                if (rect.width > 50 && rect.height > 20) {
                    return {
                        x: Math.round(rect.x + rect.width / 2),
                        y: Math.round(rect.y + 10),
                        className: (el.className || '').toString().substring(0, 60),
                    };
                }
            }
            return null;
        }""")

        if editor_info:
            tencent_logger.info(_msg("📝", f"找到标题编辑区域: {editor_info['className']}"))
            await page.mouse.click(editor_info['x'], editor_info['y'])
            await asyncio.sleep(0.5)
            await page.keyboard.type(self.title)
            await page.keyboard.press("Enter")
            for tag in self.tags:
                await page.keyboard.type("#" + tag)
                await page.keyboard.press("Space")
            tencent_logger.info(_msg("🏷️", f"成功添加 hashtag: {len(self.tags)}"))
        else:
            # 降级方案
            tencent_logger.warning(_msg("😵", "未找到标题编辑区域，尝试传统选择器"))
            await page.locator("div.input-editor").click()
            await page.keyboard.type(self.title)
            await page.keyboard.press("Enter")
            for tag in self.tags:
                await page.keyboard.type("#" + tag)
                await page.keyboard.press("Space")
            tencent_logger.info(_msg("🏷️", f"成功添加 hashtag: {len(self.tags)}"))

    async def fill_description(self, page: Page) -> None:
        """填写描述 - 在标题输入后，按 Enter 然后输入描述"""
        await page.keyboard.press("Enter")
        await page.keyboard.type(self.desc)
        tencent_logger.info(_msg("📝", f"成功添加 desc: {len(self.desc)}"))

    async def apply_collection(self, page: Page) -> None:
        """添加到合集 - 在 Wujie shadow DOM 中查找"""
        collection_info = await page.evaluate("""() => {
            const wujieApp = document.querySelector('wujie-app');
            if (!wujieApp || !wujieApp.shadowRoot) return null;

            const sr = wujieApp.shadowRoot;
            const allEls = sr.querySelectorAll('*');
            for (const el of allEls) {
                const text = (el.textContent || '').trim();
                if (text.includes('添加到合集') && el.offsetWidth > 0) {
                    const rect = el.getBoundingClientRect();
                    return {
                        x: Math.round(rect.x),
                        y: Math.round(rect.y),
                        text: text.substring(0, 30),
                    };
                }
            }
            return null;
        }""")

        if not collection_info:
            return

        # 降级方案 - 尝试传统选择器
        try:
            collection_elements = (
                page.get_by_text("添加到合集")
                .locator("xpath=following-sibling::div")
                .locator(".option-list-wrap > div")
            )
            if await collection_elements.count() > 1:
                await page.get_by_text("添加到合集").locator("xpath=following-sibling::div").click()
                await collection_elements.first.click()
        except Exception:
            tencent_logger.debug(_msg("🧍", "合集操作跳过"))

    async def apply_original_statement(self, page: Page) -> None:
        """声明原创 - 在 Wujie shadow DOM 中查找"""
        try:
            # 尝试在 shadow DOM 中找到原创声明复选框
            checkbox_info = await page.evaluate("""() => {
                const wujieApp = document.querySelector('wujie-app');
                if (!wujieApp || !wujieApp.shadowRoot) return null;

                const sr = wujieApp.shadowRoot;
                const checkboxes = sr.querySelectorAll('input[type="checkbox"]');
                for (const cb of checkboxes) {
                    const parent = cb.closest('label, .ant-checkbox-wrapper');
                    const text = parent ? (parent.textContent || '').trim() : '';
                    if (text.includes('原创') || text.includes('声明')) {
                        const rect = cb.getBoundingClientRect();
                        return {
                            x: Math.round(rect.x + rect.width / 2),
                            y: Math.round(rect.y + rect.height / 2),
                            text: text.substring(0, 50),
                        };
                    }
                }
                return null;
            }""")

            if checkbox_info:
                tencent_logger.info(_msg("📝", f"找到原创声明选项: {checkbox_info['text']}"))
                await page.mouse.click(checkbox_info['x'], checkbox_info['y'])
                await asyncio.sleep(1)
        except Exception as e:
            tencent_logger.debug(_msg("🧍", f"原创声明操作跳过: {e}"))

    async def wait_for_upload_complete(self, page: Page) -> None:
        """等待视频上传完成 - 检查 Wujie shadow DOM 中的上传进度"""
        while True:
            try:
                # 在 shadow DOM 中查找发表按钮状态
                publish_btn_info = await page.evaluate("""() => {
                    const wujieApp = document.querySelector('wujie-app');
                    if (!wujieApp || !wujieApp.shadowRoot) return null;

                    const sr = wujieApp.shadowRoot;
                    const buttons = sr.querySelectorAll('button');
                    for (const btn of buttons) {
                        const text = (btn.textContent || '').trim();
                        if (text === '发表') {
                            const rect = btn.getBoundingClientRect();
                            const disabled = btn.disabled || btn.className.includes('disabled');
                            return {
                                disabled: disabled,
                                x: Math.round(rect.x + rect.width / 2),
                                y: Math.round(rect.y + rect.height / 2),
                                text: text,
                            };
                        }
                    }
                    return null;
                }""")

                if publish_btn_info and not publish_btn_info['disabled']:
                    tencent_logger.info(_msg("🥳", "视频上传完毕"))
                    break

                # 检查上传错误
                error_info = await page.evaluate("""() => {
                    const wujieApp = document.querySelector('wujie-app');
                    if (!wujieApp || !wujieApp.shadowRoot) return false;

                    const sr = wujieApp.shadowRoot;
                    const errorEls = sr.querySelectorAll('.status-msg.error, .upload-error');
                    return errorEls.length > 0;
                }""")

                if error_info:
                    tencent_logger.error(_msg("😵", "发现上传出错了，准备重试"))
                    await self.handle_upload_error(page)

                tencent_logger.info(_msg("🏃", "正在上传视频中..."))
                await asyncio.sleep(2)
            except Exception:
                tencent_logger.info(_msg("🏃", "正在上传视频中..."))
                await asyncio.sleep(2)

    async def submit_publish(self, page: Page) -> None:
        """提交发布 - 在 Wujie shadow DOM 中查找并点击发表按钮"""
        max_wait = 180  # 最多等待 180 秒
        start_time = asyncio.get_event_loop().time()
        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > max_wait:
                tencent_logger.error(_msg("😵", f"发布超时（{max_wait}秒），可能被平台拦截"))
                break
            try:
                # 在 shadow DOM 中查找发表按钮并用 JS click 点击
                is_draft = getattr(self, "is_draft", False)
                publish_result = await page.evaluate(f"""() => {{
                    const wujieApp = document.querySelector('wujie-app');
                    if (!wujieApp || !wujieApp.shadowRoot) return {{ found: false, reason: 'no shadowRoot' }};

                    const sr = wujieApp.shadowRoot;
                    const buttons = sr.querySelectorAll('button');
                    const allTexts = Array.from(buttons).map(b => (b.textContent || '').trim().substring(0, 20));
                    
                    // 优先查找「发表」按钮（不是「发表视频」）
                    var targetText = '{"保存草稿" if is_draft else "发表"}';
                    for (const btn of buttons) {{
                        const text = (btn.textContent || '').trim();
                        if (text === targetText) {{
                            const rect = btn.getBoundingClientRect();
                            const disabled = btn.disabled || btn.className.includes('disabled');
                            if (!disabled) {{
                                btn.click();
                                return {{ found: true, clicked: true, text: text, w: Math.round(rect.width), h: Math.round(rect.height) }};
                            }} else {{
                                return {{ found: true, clicked: false, text: text, disabled: true }};
                            }}
                        }}
                    }}
                    return {{ found: false, allBtns: allTexts }};
                }}""")

                if getattr(self, "is_draft", False):
                    if publish_result and publish_result.get('found') and '草稿' in publish_result.get('text', ''):
                        if publish_result.get('clicked'):
                            tencent_logger.info(_msg("📤", f"点击草稿按钮: {publish_result['text']}"))
                    if "post/list" in page.url or "draft" in page.url:
                        tencent_logger.success(_msg("🥳", "视频草稿保存成功"))
                        break
                else:
                    if publish_result and publish_result.get('found'):
                        if publish_result.get('clicked'):
                            tencent_logger.info(_msg("📤", f"点击发表按钮: {publish_result['text']} ({publish_result.get('w')}x{publish_result.get('h')})"))
                            await asyncio.sleep(3)
                        elif publish_result.get('disabled'):
                            tencent_logger.info(_msg("⏳", "发表按钮仍为禁用状态，等待中..."))
                    else:
                        # 调试：每 10 秒输出一次按钮列表
                        if int(elapsed) % 10 == 0:
                            tencent_logger.info(_msg("🔍", f"未找到发表按钮: {publish_result}"))

                    if TENCENT_MANAGE_URL in page.url or "post/list" in page.url:
                        tencent_logger.success(_msg("🥳", "视频发布成功"))
                        break

                tencent_logger.info(_msg("🏃", "视频正在发布中..."))
                await asyncio.sleep(1)
            except Exception as exc:
                current_url = page.url
                if getattr(self, "is_draft", False):
                    if "post/list" in current_url or "draft" in current_url:
                        tencent_logger.success(_msg("🥳", "视频草稿保存成功"))
                        break
                else:
                    if TENCENT_MANAGE_URL in current_url:
                        tencent_logger.success(_msg("🥳", "视频发布成功"))
                        break
                tencent_logger.exception(f"  [-] Exception: {exc}")
                tencent_logger.info(_msg("🏃", "视频正在发布中..."))
                await asyncio.sleep(0.5)


class TencentVideo(TencentBaseUploader):
    def __init__(
        self,
        title,
        file_path,
        tags,
        publish_date: datetime | int,
        account_file,
        category=None,
        is_draft=False,
        desc: str | None = None,
        thumbnail_path: str | None = None,
        short_title: str | None = None,
        publish_strategy: str = TENCENT_PUBLISH_STRATEGY_IMMEDIATE,
        debug: bool = DEBUG_MODE,
        headless: bool = LOCAL_CHROME_HEADLESS,
    ):
        super().__init__(
            publish_date=publish_date,
            account_file=account_file,
            publish_strategy=publish_strategy,
            debug=debug,
            headless=headless,
        )
        self.title = title
        self.file_path = file_path
        self.tags = tags or []
        self.category = category
        self.is_draft = is_draft
        self.desc = desc or ""
        self.thumbnail_path = thumbnail_path
        self.short_title = short_title

    async def validate_upload_args(self):
        await self.validate_base_args()
        if not self.title or not str(self.title).strip():
            raise ValueError("视频模式下，title 是必须的")
        self.file_path = str(self.validate_video_file(self.file_path))
        if self.thumbnail_path:
            self.thumbnail_path = str(self.validate_image_file(self.thumbnail_path))

    async def handle_upload_error(self, page: Page) -> None:
        """处理上传错误 - 在 Wujie shadow DOM 中删除并重新上传"""
        tencent_logger.info(_msg("😵", "视频出错了，重新上传中"))

        # 尝试在 shadow DOM 中找到删除按钮
        delete_info = await page.evaluate("""() => {
            const wujieApp = document.querySelector('wujie-app');
            if (!wujieApp || !wujieApp.shadowRoot) return null;

            const sr = wujieApp.shadowRoot;
            const allEls = sr.querySelectorAll('*');
            for (const el of allEls) {
                const text = (el.textContent || '').trim();
                if (text === '删除' && el.offsetWidth > 0) {
                    const rect = el.getBoundingClientRect();
                    return {
                        x: Math.round(rect.x + rect.width / 2),
                        y: Math.round(rect.y + rect.height / 2),
                        tag: el.tagName,
                    };
                }
            }
            return null;
        }""")

        if delete_info:
            await page.mouse.click(delete_info['x'], delete_info['y'])
            await asyncio.sleep(1)

        await self.upload_video_file(page, self.file_path)

    async def set_thumbnail(self, page: Page) -> None:
        if not self.thumbnail_path:
            return

        tencent_logger.info(_msg("🖼️", "小人准备设置封面"))

        # 在 Wujie shadow DOM 中查找封面相关区域
        cover_info = await page.evaluate("""() => {
            const wujieApp = document.querySelector('wujie-app');
            if (!wujieApp || !wujieApp.shadowRoot) return null;

            const sr = wujieApp.shadowRoot;
            // 查找封面相关元素
            const allEls = sr.querySelectorAll('*');
            for (const el of allEls) {
                const text = (el.textContent || '').trim();
                const cls = (el.className || '').toString();
                if ((text.includes('封面') || cls.includes('cover')) && el.offsetWidth > 0 && el.offsetWidth < 300) {
                    const rect = el.getBoundingClientRect();
                    return {
                        x: Math.round(rect.x + rect.width / 2),
                        y: Math.round(rect.y + rect.height / 2),
                        text: text.substring(0, 30),
                        className: cls.substring(0, 60),
                    };
                }
            }
            return null;
        }""")

        if not cover_info:
            tencent_logger.info(_msg("🧍", "未找到封面设置入口，跳过自定义封面"))
            return

        tencent_logger.info(_msg("🖼️", f"找到封面区域: {cover_info.get('text', '')}"))
        # 点击封面设置入口
        await page.mouse.click(cover_info['x'], cover_info['y'])
        await page.wait_for_timeout(1000)

        # 尝试找到文件输入来上传封面图
        try:
            async with page.expect_file_chooser(timeout=5000) as fc_info:
                # 点击封面区域的文件上传入口
                # 封面编辑弹窗中的上传按钮通常在弹窗中央
                await page.mouse.click(cover_info['x'], cover_info['y'] + 100)
            file_chooser = await fc_info.value
            await file_chooser.set_files(self.thumbnail_path)
            tencent_logger.success(_msg("🥳", "封面图片已上传"))
            await page.wait_for_timeout(2000)
        except Exception as exc:
            tencent_logger.warning(_msg("😵", f"封面上传失败: {exc}"))

        # 尝试点击确认按钮
        confirm_info = await page.evaluate("""() => {
            const wujieApp = document.querySelector('wujie-app');
            if (!wujieApp || !wujieApp.shadowRoot) return null;

            const sr = wujieApp.shadowRoot;
            const buttons = sr.querySelectorAll('button');
            for (const btn of buttons) {
                const text = (btn.textContent || '').trim();
                if (text === '确认' || text === '确定') {
                    const rect = btn.getBoundingClientRect();
                    return {
                        x: Math.round(rect.x + rect.width / 2),
                        y: Math.round(rect.y + rect.height / 2),
                    };
                }
            }
            return null;
        }""")

        if confirm_info:
            await page.mouse.click(confirm_info['x'], confirm_info['y'])
            tencent_logger.success(_msg("🥳", "封面设置完成"))
            await page.wait_for_timeout(1000)

    async def prepare_video_for_publish(self, page: Page) -> None:
        await self.fill_title_and_tags(page)
        await self.fill_description(page)
        await self.apply_collection(page)
        await self.apply_original_statement(page)

    async def upload(self, playwright: Playwright) -> None:
        tencent_logger.info(_msg("🧍", "小人先检查 cookie、视频文件和发布时间"))
        await self.validate_upload_args()
        tencent_logger.info(_msg("🥳", "上传前检查通过"))

        user_data_dir = get_user_data_dir(self.account_file)
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            **build_persistent_launch_kwargs(headless=self.headless),
        )
        await migrate_storage_state_if_needed(context, self.account_file)

        try:
            page = await context.new_page()
            await self.open_upload_page(page)
            tencent_logger.info(_msg("🏃", f"小人开始搬运视频: {self.title}"))

            await self.upload_video_file(page, self.file_path)
            await self.prepare_video_for_publish(page)
            await self.wait_for_upload_complete(page)
            await self.set_thumbnail(page)

            if self.publish_strategy == TENCENT_PUBLISH_STRATEGY_SCHEDULED and self.publish_date != 0:
                await self.set_schedule_time_tencent(page, self.publish_date)

            await self.set_short_title(page, self.title, self.short_title)
            await self.submit_publish(page)

            try:
                await context.storage_state(path=self.account_file)
            except Exception:
                pass
            tencent_logger.success(_msg("🥳", "cookie 更新完毕"))
        finally:
            await context.close()

    async def tencent_upload_video(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)

    async def main(self):
        await self.tencent_upload_video()


class TencentNote(TencentBaseUploader):
    def __init__(
        self,
        image_paths,
        note,
        tags,
        publish_date: datetime | int,
        account_file,
        title: str | None = None,
        publish_strategy: str = TENCENT_PUBLISH_STRATEGY_IMMEDIATE,
        debug: bool = DEBUG_MODE,
        headless: bool = LOCAL_CHROME_HEADLESS,
        is_draft: bool = False,
    ):
        super().__init__(
            publish_date=publish_date,
            account_file=account_file,
            publish_strategy=publish_strategy,
            debug=debug,
            headless=headless,
        )
        self.image_paths = image_paths
        self.note = note or ""
        self.title = title or (self.note[:30] if self.note else "")
        self.tags = tags or []
        self.is_draft = is_draft

    async def validate_upload_args(self):
        await self.validate_base_args()
        if not self.title or not str(self.title).strip():
            raise ValueError("图文模式下，title 是必须的")
        if not self.image_paths:
            raise ValueError("图文模式下，图片是必须的")

        if isinstance(self.image_paths, (str, Path)):
            self.image_paths = [self.image_paths]

        normalized_image_paths = []
        for image_path in self.image_paths:
            normalized_image_paths.append(str(self.validate_image_file(image_path)))
        self.image_paths = normalized_image_paths

    async def switch_to_note_mode(self, page: Page) -> None:
        raise NotImplementedError("请在 TencentNote.switch_to_note_mode 中补充视频号切换到图文发布模式的逻辑")

    async def upload_note_images(self, page: Page) -> None:
        raise NotImplementedError("请在 TencentNote.upload_note_images 中补充视频号图文图片上传逻辑")

    async def fill_note_title_and_tags(self, page: Page) -> None:
        raise NotImplementedError("请在 TencentNote.fill_note_title_and_tags 中补充视频号图文标题/话题填写逻辑")

    async def fill_note_body(self, page: Page) -> None:
        return None

    async def prepare_note_for_publish(self, page: Page) -> None:
        await self.fill_note_title_and_tags(page)
        await self.fill_note_body(page)
        await self.apply_collection(page)
        await self.apply_original_statement(page)

    async def upload_note_content(self, page: Page) -> None:
        await self.switch_to_note_mode(page)
        await self.upload_note_images(page)
        await self.prepare_note_for_publish(page)

    async def upload(self, playwright: Playwright) -> None:
        tencent_logger.info(_msg("🧍", "小人先检查 cookie、图文图片和发布时间"))
        await self.validate_upload_args()
        tencent_logger.info(_msg("🥳", "图文上传前检查通过"))

        user_data_dir = get_user_data_dir(self.account_file)
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            **build_persistent_launch_kwargs(headless=self.headless),
        )
        await migrate_storage_state_if_needed(context, self.account_file)
        context = await set_init_script(context)

        try:
            page = await context.new_page()
            await self.open_upload_page(page)
            tencent_logger.info(_msg("🏃", f"小人开始搬运图文，共 {len(self.image_paths)} 张图片"))

            await self.upload_note_content(page)

            if self.publish_strategy == TENCENT_PUBLISH_STRATEGY_SCHEDULED and self.publish_date != 0:
                await self.set_schedule_time_tencent(page, self.publish_date)

            await self.submit_publish(page)

            try:
                await context.storage_state(path=self.account_file)
            except Exception:
                pass
            tencent_logger.success(_msg("🥳", "cookie 更新完毕"))
        finally:
            await context.close()

    async def tencent_upload_note(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)

    async def main(self):
        await self.tencent_upload_note()
