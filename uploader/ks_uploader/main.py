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

from conf import DEBUG_MODE, LOCAL_CHROME_HEADLESS, LOCAL_CHROME_PATH
from uploader.base_video import BaseVideoUploader
from utils.base_social_media import set_init_script, get_user_data_dir, migrate_storage_state_if_needed, build_persistent_launch_kwargs
from utils.files_times import get_absolute_path
from utils.login_qrcode import build_login_qrcode_path
from utils.login_qrcode import decode_qrcode_from_path
from utils.login_qrcode import print_terminal_qrcode
from utils.login_qrcode import remove_qrcode_file
from utils.login_qrcode import save_data_url_image
from utils.log import kuaishou_logger

KUAISHOU_UPLOAD_URL = "https://cp.kuaishou.com/article/publish/video"
KUAISHOU_MANAGE_URL = "https://cp.kuaishou.com/article/manage/video?status=2&from=publish"
KUAISHOU_LOGIN_URL = "https://passport.kuaishou.com/pc/account/login/?sid=kuaishou.web.cp.api&callback=https%3A%2F%2Fcp.kuaishou.com%2Frest%2Finfra%2Fsts%3FfollowUrl%3Dhttps%253A%252F%252Fcp.kuaishou.com%252Farticle%252Fpublish%252Fvideo%26setRootDomain%3Dtrue"
KUAISHOU_UPLOAD_URL_PATTERN = "**/article/publish/video**"
KUAISHOU_MANAGE_URL_PATTERN = "**/article/manage/video?status=2&from=publish**"
KUAISHOU_COOKIE_INVALID_SELECTOR = "div.names div.container div.name:text('机构服务')"
KUAISHOU_PUBLISH_STRATEGY_IMMEDIATE = "immediate"
KUAISHOU_PUBLISH_STRATEGY_SCHEDULED = "scheduled"


def _msg(emoji: str, text: str) -> str:
    return f"{emoji} {text}"


def _print_ks_qrcode(qrcode_content: str, qrcode_path: Path) -> None:
    try:
        print_terminal_qrcode(qrcode_content, qrcode_path, "快手APP", compact=False, border=2)
    except TypeError as exc:
        if "unexpected keyword argument 'compact'" not in str(exc):
            raise
        kuaishou_logger.warning(_msg("😵", "检测到旧版二维码打印函数，小人切回兼容模式继续登录"))
        print_terminal_qrcode(qrcode_content, qrcode_path, "快手APP")


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


async def _is_ks_cookie_invalid(page: Page, timeout: int = 5000) -> bool:
    try:
        await page.wait_for_selector(KUAISHOU_COOKIE_INVALID_SELECTOR, timeout=timeout)
        return True
    except Exception:
        return False


async def _extract_ks_qrcode_src(page: Page) -> str:
    login_form = page.locator("main#login-form").first
    await login_form.wait_for(state="visible", timeout=30000)

    qrcode_img = login_form.locator('div.qr-login img[alt="qrcode"]').first
    try:
        if not await qrcode_img.count() or not await qrcode_img.is_visible():
            platform_switch = login_form.locator("div.platform-switch").first
            await platform_switch.wait_for(state="visible", timeout=10000)
            await platform_switch.click()
            await asyncio.sleep(1)
    except Exception:
        platform_switch = login_form.locator("div.platform-switch").first
        await platform_switch.wait_for(state="visible", timeout=10000)
        await platform_switch.click()
        await asyncio.sleep(1)

    await qrcode_img.wait_for(state="visible", timeout=15000)

    qrcode_src = await qrcode_img.get_attribute("src")
    if not qrcode_src:
        raise RuntimeError("未获取到快手登录二维码地址")

    return qrcode_src


async def _save_ks_qrcode(page: Page, account_file: str, previous_qrcode_path: Path | None = None, qrcode_callback=None) -> dict:
    qrcode_src = await _extract_ks_qrcode_src(page)
    qrcode_path = save_data_url_image(qrcode_src, build_login_qrcode_path(account_file, suffix="ks_login_qrcode"))

    if previous_qrcode_path and previous_qrcode_path != qrcode_path:
        if remove_qrcode_file(previous_qrcode_path):
            kuaishou_logger.info(_msg("🧹", f"临时二维码文件已清理: {previous_qrcode_path}"))

    kuaishou_logger.info(_msg("🖼️", f"二维码已经准备好啦，已保存到: {qrcode_path}"))
    qrcode_content = decode_qrcode_from_path(qrcode_path)
    if qrcode_content:
        _print_ks_qrcode(qrcode_content, qrcode_path)
    else:
        kuaishou_logger.warning(_msg("😵", f"终端没法完整显示二维码，请打开 {qrcode_path} 扫码"))

    qrcode_info = {
        "image_path": str(qrcode_path),
        "image_data_url": qrcode_src,
    }
    await _emit_qrcode_callback(qrcode_callback, qrcode_info)
    return qrcode_info


async def _is_ks_qrcode_expired(page: Page) -> bool:
    expired_box = page.locator("div.qrcode-status.qrcode-status-timeout").first
    try:
        if not await expired_box.count():
            return False
        return await expired_box.is_visible()
    except Exception:
        return False


async def _is_ks_login_page_gone(page: Page) -> bool:
    try:
        login_form = page.locator("main#login-form").first
        if not await login_form.count():
            return True
        return not await login_form.is_visible()
    except Exception:
        return True


async def cookie_auth(account_file):
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
            await page.goto(KUAISHOU_UPLOAD_URL, timeout=60000, wait_until="domcontentloaded")
            if await _is_ks_cookie_invalid(page):
                kuaishou_logger.info(_msg("🥹", "cookie 已失效，得重新登录一下"))
                return False

            kuaishou_logger.success(_msg("🥳", "cookie 有效"))
            return True
        except Exception as exc:
            kuaishou_logger.warning(_msg("😵", f"cookie 校验时出错，按失效处理: {exc}"))
            return False
        finally:
            await context.close()


async def ks_setup(account_file, handle=False, return_detail=False, qrcode_callback=None, headless: bool = LOCAL_CHROME_HEADLESS):
    account_file = get_absolute_path(account_file, "ks_uploader")
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            result = _build_login_result(False, "cookie_invalid", "cookie文件不存在或已失效", account_file)
            return result if return_detail else False
        kuaishou_logger.info(_msg("🥹", "cookie 失效了，准备重新登录快手创作者平台"))
        result = await get_ks_cookie(account_file, qrcode_callback=qrcode_callback, headless=headless)
        return result if return_detail else result["success"]

    result = _build_login_result(True, "cookie_valid", "cookie有效", account_file)
    return result if return_detail else True


async def get_ks_cookie(
    account_file,
    qrcode_callback=None,
    headless: bool = LOCAL_CHROME_HEADLESS,
    poll_interval: int = 3,
    max_checks: int = 100,
):
    if headless:
        kuaishou_logger.info(_msg("🖼️", "快手登录将以无头模式运行，小人会输出终端二维码并保存本地二维码图片"))

    user_data_dir = get_user_data_dir(account_file)
    async with async_playwright() as playwright:
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            **build_persistent_launch_kwargs(headless=headless),
        )
        context = await set_init_script(context)
        qrcode_path = None
        qrcode_info = None
        result = _build_login_result(False, "failed", "快手登录失败", account_file)
        try:
            page = await context.new_page()
            await page.goto(KUAISHOU_LOGIN_URL)
            kuaishou_logger.info(_msg("🧍", "请在浏览器里扫码登录快手，小人正在耐心等待"))

            qrcode_info = await _save_ks_qrcode(page, account_file, qrcode_callback=qrcode_callback)
            qrcode_path = Path(qrcode_info["image_path"])

            for _ in range(max_checks):
                if page.url.startswith(KUAISHOU_UPLOAD_URL) or await _is_ks_login_page_gone(page):
                    try:
                        await context.storage_state(path=account_file)
                    except Exception:
                        pass
                    # 用当前 page 做校验（避免开第二个浏览器抢占 user_data_dir）
                    if not await _is_ks_cookie_invalid(page):
                        kuaishou_logger.success(_msg("🥳", "快手扫码登录成功，小人开心收工"))
                        result = _build_login_result(True, "success", "快手扫码登录成功", account_file, qrcode_info, page.url)
                    else:
                        kuaishou_logger.error(_msg("😢", "快手扫码完成了，但 cookie 校验失败"))
                        result = _build_login_result(
                            False,
                            "cookie_invalid",
                            "快手扫码流程结束，但 cookie 校验失败",
                            account_file,
                            qrcode_info,
                            page.url,
                        )
                    return result

                if qrcode_info and await _is_ks_qrcode_expired(page):
                    kuaishou_logger.warning(_msg("😵", "二维码失效了，小人马上去刷新"))
                    refresh_button = page.locator("p.qrcode-refresh").first
                    if await refresh_button.count():
                        await refresh_button.click()
                        await asyncio.sleep(1)
                    qrcode_info = await _save_ks_qrcode(
                        page,
                        account_file,
                        qrcode_path,
                        qrcode_callback=qrcode_callback,
                    )
                    qrcode_path = Path(qrcode_info["image_path"])

                await asyncio.sleep(poll_interval)

            result = _build_login_result(
                False,
                "timeout",
                "等待快手扫码登录超时",
                account_file,
                qrcode_info,
                page.url,
            )
        except Exception as exc:
            result = _build_login_result(False, "failed", str(exc), account_file, current_url=page.url if "page" in locals() else "")
        finally:
            if remove_qrcode_file(qrcode_path):
                kuaishou_logger.info(_msg("🧹", f"临时二维码文件已清理: {qrcode_path}"))
            if not result["success"]:
                kuaishou_logger.error(_msg("😢", f"登录失败: {result['message']}"))
            await context.close()

    return result


class KSBaseUploader(BaseVideoUploader):
    def __init__(
        self,
        publish_date: datetime | int,
        account_file,
        publish_strategy: str | None = None,
        debug: bool = DEBUG_MODE,
        headless: bool = LOCAL_CHROME_HEADLESS,
    ):
        self.publish_date = publish_date
        self.account_file = str(account_file)
        self.publish_strategy = publish_strategy
        self.debug = debug
        self.headless = headless
        self.local_executable_path = LOCAL_CHROME_PATH
        self.date_format = "%Y-%m-%d %H:%M"

    async def validate_base_args(self):
        if not os.path.exists(self.account_file):
            raise RuntimeError(f"cookie文件不存在，请先完成快手登录: {self.account_file}")
        if not await cookie_auth(self.account_file):
            raise RuntimeError(f"cookie文件已失效，请先完成快手登录: {self.account_file}")

        if self.publish_strategy is None:
            self.publish_strategy = (
                KUAISHOU_PUBLISH_STRATEGY_SCHEDULED
                if self.publish_date != 0
                else KUAISHOU_PUBLISH_STRATEGY_IMMEDIATE
            )

        if self.publish_strategy not in {
            KUAISHOU_PUBLISH_STRATEGY_IMMEDIATE,
            KUAISHOU_PUBLISH_STRATEGY_SCHEDULED,
        }:
            raise ValueError(f"不支持的发布策略: {self.publish_strategy}")

        if self.publish_strategy == KUAISHOU_PUBLISH_STRATEGY_SCHEDULED:
            self.publish_date = self.validate_publish_date(self.publish_date)
        else:
            self.publish_date = 0

    async def set_schedule_time(self, page: Page, publish_date: datetime):
        kuaishou_logger.info(_msg("🕒", "小人准备设置定时发布时间"))
        publish_date_hour = publish_date.strftime("%Y-%m-%d %H:%M:%S")
        await page.locator("label:text('发布时间')").locator("xpath=following-sibling::div").locator(".ant-radio-input").nth(1).click()
        await asyncio.sleep(1)
        await page.locator('div.ant-picker-input input[placeholder="选择日期时间"]').click()
        await asyncio.sleep(1)
        await page.keyboard.press("Control+KeyA")
        await page.keyboard.type(publish_date_hour)
        await page.keyboard.press("Enter")
        await asyncio.sleep(1)

    async def close_micro_support_modal(self, page: Page) -> bool:
        """关闭快手创作者服务中心弹窗（#microSupport ant-modal）"""
        try:
            modal_wrap = page.locator('#microSupport .ant-modal-wrap')
            if await modal_wrap.count() > 0 and await modal_wrap.first.is_visible():
                kuaishou_logger.info(_msg("🔔", "检测到创作者服务弹窗(microSupport)，正在关闭..."))
                # 优先点击确认按钮（ant-modal-confirm 弹窗通常有"我知道了"/"确认"按钮）
                confirm_btn = page.locator('#microSupport .ant-modal-confirm-btns .ant-btn-primary')
                if await confirm_btn.count() > 0 and await confirm_btn.first.is_visible():
                    await confirm_btn.first.click()
                    await asyncio.sleep(0.5)
                # 尝试点击关闭按钮（X）
                close_btn = page.locator('#microSupport .ant-modal-close')
                if await close_btn.count() > 0 and await close_btn.first.is_visible():
                    await close_btn.first.click()
                    await asyncio.sleep(0.5)
                # 如果弹窗还在，用 JS 强制隐藏遮罩层
                still_visible = await modal_wrap.first.is_visible()
                if still_visible:
                    await page.evaluate('''() => {
                        const wrap = document.querySelector('#microSupport .ant-modal-wrap');
                        if (wrap) wrap.remove();
                        const container = document.querySelector('#microSupport');
                        if (container) container.remove();
                    }''')
                    kuaishou_logger.info(_msg("🔧", "已用 JS 强制移除弹窗 DOM"))
                kuaishou_logger.success(_msg("🥳", "已关闭创作者服务弹窗"))
                await asyncio.sleep(1)
                return True
        except Exception as exc:
            kuaishou_logger.warning(_msg("⚠️", f"关闭弹窗时出错（不影响主流程）: {exc}"))
        return False

    async def close_guide_overlay(self, page: Page) -> bool:
        joyride_tooltip = page.locator('div[id^="react-joyride-step"] div[role="alertdialog"]')

        # 判断是否显示
        if await joyride_tooltip.count() > 0 and await joyride_tooltip.first.is_visible():
            print("检测到 Joyride 引导遮罩，正在关闭...")

            # 点击关闭按钮（X），使用多个可靠特征
            close_button = page.locator('div[role="alertdialog"]').locator(
                '[aria-label="Skip"], [data-action="skip"], button[title="Skip"]'
            )

            await close_button.click(force=True)

            # 等待遮罩消失
            await joyride_tooltip.wait_for(state="hidden", timeout=5000)

            print("✅ 已关闭 Joyride 遮罩")
        else:
            print("未检测到 Joyride 遮罩，继续执行")


class KSVideo(KSBaseUploader):
    def __init__(
        self,
        title,
        file_path,
        tags,
        publish_date: datetime | int,
        account_file,
        publish_strategy: str | None = None,
        debug: bool = DEBUG_MODE,
        headless: bool = LOCAL_CHROME_HEADLESS,
        thumbnail_path=None,
        desc: str | None = None,
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
        self.thumbnail_path = thumbnail_path
        self.desc = desc or ""

    async def validate_upload_args(self):
        await self.validate_base_args()
        if not self.title or not str(self.title).strip():
            raise ValueError("快手视频上传时，title 是必须的")
        self.file_path = str(self.validate_video_file(self.file_path))
        if self.thumbnail_path:
            self.thumbnail_path = str(self.validate_image_file(self.thumbnail_path))

    async def handle_upload_error(self, page: Page):
        kuaishou_logger.warning(_msg("😵", "视频上传摔了一跤，小人马上重新上传"))
        await page.locator('div.progress-div [class^="upload-btn-input"]').set_input_files(self.file_path)

    async def set_thumbnail(self, page: Page):
        if not self.thumbnail_path:
            return

        kuaishou_logger.info(_msg("🖼️", "小人准备设置封面"))

        cover_label = page.locator("span").filter(has_text="封面设置")
        await cover_label.wait_for(state="visible", timeout=30000)
        await cover_label.locator("xpath=../following-sibling::div[1]").locator('div').nth(0).click()

        modal = page.locator('div[role="document"].ant-modal')
        await modal.wait_for(state="visible", timeout=30000)

        upload_cover_tab = modal.get_by_text("上传封面", exact=True)
        await upload_cover_tab.wait_for(state="visible", timeout=10000)
        await upload_cover_tab.click()

        file_input = modal.locator('input[type="file"]')
        await file_input.wait_for(state="attached", timeout=30000)
        await file_input.set_input_files(self.thumbnail_path)
        await asyncio.sleep(1)

        confirm_button = modal.get_by_role("button", name="确认", exact=True)
        await confirm_button.wait_for(state="visible", timeout=10000)
        await confirm_button.click()

        await modal.wait_for(state="hidden", timeout=30000)
        kuaishou_logger.success(_msg("🥳", "封面已经设置完成"))

    async def upload(self, playwright: Playwright) -> None:
        kuaishou_logger.info(_msg("🧍", "小人先检查 cookie、视频文件、封面和发布时间"))
        await self.validate_upload_args()
        kuaishou_logger.info(_msg("🥳", "上传前检查通过"))

        user_data_dir = get_user_data_dir(self.account_file)
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            **build_persistent_launch_kwargs(headless=self.headless, executable_path=self.local_executable_path),
        )
        await migrate_storage_state_if_needed(context, self.account_file)
        context = await set_init_script(context)

        upload_success = False
        try:
            page = await context.new_page()
            # 导航加重试，避免超时
            nav_ok = False
            for attempt in range(3):
                try:
                    await page.goto(KUAISHOU_UPLOAD_URL, timeout=60000, wait_until="domcontentloaded")
                    nav_ok = True
                    break
                except Exception as e:
                    kuaishou_logger.warning(_msg("⚠️", f"导航重试 {attempt+1}/3: {e}"))
                    if attempt < 2:
                        await asyncio.sleep(2)
            if not nav_ok:
                raise RuntimeError("快手上传页面加载失败（3次重试均超时）")
            kuaishou_logger.info(_msg("🏃", f"小人开始搬运视频: {self.title}.mp4"))
            kuaishou_logger.info(_msg("🧭", "小人正在赶往快手上传主页"))
            await page.wait_for_url(KUAISHOU_UPLOAD_URL_PATTERN)

            upload_button = page.locator("button[class^='_upload-btn']")
            await upload_button.wait_for(state="visible", timeout=10000)

            async with page.expect_file_chooser() as fc_info:
                await upload_button.click()
            file_chooser = await fc_info.value
            await file_chooser.set_files(self.file_path)

            await asyncio.sleep(2)

            know_button = page.locator('button[type="button"] span:text("我知道了")').first
            try:
                if await know_button.count() and await know_button.is_visible():
                    await know_button.click()
            except Exception:
                pass

            await self.close_guide_overlay(page)

            kuaishou_logger.info(_msg("✍️", "小人开始填描述和话题"))
            await page.get_by_text("描述").locator("xpath=following-sibling::div").click()
            await page.keyboard.press("Backspace")
            await page.keyboard.press("Control+KeyA")
            await page.keyboard.press("Delete")
            await page.keyboard.type(self.desc or self.title)
            await page.keyboard.press("Enter")

            for index, tag in enumerate(self.tags[:3], start=1):
                kuaishou_logger.info(_msg("🏷️", f"小人正在添加第 {index} 个话题: #{tag}"))
                await page.keyboard.type(f"#{tag} ")
                await asyncio.sleep(2)

            max_retries = 300  # 300 次 × 2 秒 = 600 秒 = 10 分钟（大视频需要更长上传时间）
            retry_count = 0
            upload_done = False
            while retry_count < max_retries:
                try:
                    number = await page.locator("text=上传中").count()
                    if number == 0:
                        kuaishou_logger.success(_msg("🥳", f"视频已经传完啦（{retry_count * 2}秒）"))
                        upload_done = True
                        break

                    if retry_count % 15 == 0:  # 每 30 秒打一次日志
                        kuaishou_logger.info(_msg("🏃", f"小人正在努力上传视频（{retry_count * 2}秒）"))

                    if await page.locator("text=上传失败").count():
                        await self.handle_upload_error(page)

                    await asyncio.sleep(2)
                except Exception as exc:
                    kuaishou_logger.warning(_msg("😵", f"检查上传状态时出错，小人继续重试: {exc}"))
                    await asyncio.sleep(2)
                retry_count += 1

            if not upload_done:
                kuaishou_logger.error(_msg("😵", f"视频上传超时（{max_retries * 2}秒），放弃发布"))
                raise RuntimeError(f"快手视频上传超时（{max_retries * 2}秒）")

            await self.set_thumbnail(page)

            if self.publish_strategy == KUAISHOU_PUBLISH_STRATEGY_SCHEDULED and self.publish_date != 0:
                await self.set_schedule_time(page, self.publish_date)

            # 发布前先关闭可能弹出的创作者服务弹窗
            await self.close_micro_support_modal(page)

            # === 第一步：点击发布按钮（只点一次） ===
            # 快手的发布按钮不是 <button>，而是 <div>，位于页面底部
            # DOM: div[class*='edit-section-btns'] > div[class*='button-primary'] > "发布"
            # 注意：按钮可能在视口外（y≈1189），需要先滚动
            publish_clicked = False
            publish_selectors = [
                # 最精确：编辑区域底部的发布按钮容器内找"发布"
                "div[class*='edit-section-btns'] div[class*='button-primary']",
                # fallback：任何 class 含 button-primary 且文本为"发布"的 div
                "div[class*='button-primary']:has-text('发布')",
                # fallback2：get_by_role
                page.get_by_role("button", name="发布", exact=True),
            ]
            for sel in publish_selectors:
                try:
                    if isinstance(sel, str):
                        locator = page.locator(sel).first
                    else:
                        locator = sel
                    if await locator.count() > 0:
                        # 滚动到可见
                        await locator.scroll_into_view_if_needed(timeout=5000)
                        await asyncio.sleep(0.5)
                        await locator.click()
                        publish_clicked = True
                        kuaishou_logger.info(_msg("📤", f"已点击发布按钮（选择器: {sel if isinstance(sel, str) else 'role=button'}）"))
                        break
                except Exception as e:
                    kuaishou_logger.debug(_msg("🔍", f"选择器 {sel if isinstance(sel, str) else 'role'} 未命中: {e}"))
                    continue

            if not publish_clicked:
                kuaishou_logger.warning(_msg("⚠️", "所有发布按钮选择器均未命中"))

            await asyncio.sleep(1)

            # 检查是否弹出确认发布按钮
            confirm_selectors = [
                "div[class*='button-primary']:has-text('确认发布')",
                page.get_by_role("button", name="确认发布", exact=True),
                page.locator("text=确认发布"),
            ]
            for sel in confirm_selectors:
                if isinstance(sel, str):
                    locator = page.locator(sel).first
                else:
                    locator = sel
                if await locator.count() > 0:
                    try:
                        await locator.click()
                        kuaishou_logger.info(_msg("📤", "已点击确认发布"))
                    except Exception:
                        pass
                    break

            await asyncio.sleep(2)

            # === 第二步：多信号检测发布结果 ===
            if not publish_clicked:
                raise RuntimeError("未找到发布按钮，无法发布")

            max_wait = 60  # 最多等待 120 秒
            publish_success = False
            for check_i in range(max_wait):
                # 定期关闭弹窗
                if check_i % 5 == 0:
                    await self.close_micro_support_modal(page)

                try:
                    current_url = page.url
                    # 信号1：URL 跳转到管理页
                    if "article/manage/video" in current_url:
                        kuaishou_logger.success(_msg("🥳", f"视频发布成功（URL跳转检测）: {current_url}"))
                        publish_success = True
                        break

                    # 信号2：页面出现"发布成功"相关提示
                    success_texts = ["发布成功", "投稿成功", "已发布"]
                    for txt in success_texts:
                        if await page.locator(f"text={txt}").count() > 0:
                            kuaishou_logger.success(_msg("🥳", f"视频发布成功（页面提示检测）: {txt}"))
                            publish_success = True
                            break
                    if publish_success:
                        break

                    # 信号3：发布按钮消失（发布中→已完成）
                    if await page.locator("div[class*='edit-section-btns']").count() == 0 and check_i > 3:
                        kuaishou_logger.success(_msg("🥳", "视频发布成功（发布按钮消失）"))
                        publish_success = True
                        break

                    # 反爬拦截检测 → 立即终止
                    page_content = await page.content()
                    anti_bot_markers = ["操作频繁", "账号异常", "验证码", "人机验证", "captcha"]
                    for marker in anti_bot_markers:
                        if marker in page_content:
                            kuaishou_logger.error(_msg("🚫", f"检测到反爬拦截: {marker}，终止发布"))
                            raise RuntimeError(f"快手发布被反爬拦截: {marker}")

                    # 错误检测
                    error_markers = ["发布失败", "上传失败", "审核不通过", "违规"]
                    for marker in error_markers:
                        if await page.locator(f"text={marker}").count() > 0:
                            kuaishou_logger.error(_msg("❌", f"视频发布失败: {marker}"))
                            raise RuntimeError(f"快手发布失败: {marker}")

                except RuntimeError:
                    raise
                except Exception as exc:
                    kuaishou_logger.warning(_msg("😵", f"检测发布结果时出错: {exc}"))

                await asyncio.sleep(2)

            if not publish_success:
                kuaishou_logger.warning(_msg("⚠️", f"发布结果检测超时（{max_wait * 2}秒），但视频可能已发布成功"))

            # 无论检测结果如何，只要点了发布按钮就视为成功（避免重复上传已发布视频）
            upload_success = True
        finally:
            if upload_success:
                try:
                    await context.storage_state(path=self.account_file)
                except Exception:
                    pass
                kuaishou_logger.success(_msg("🥳", "cookie 更新完毕"))
                await asyncio.sleep(2)
            await context.close()

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)


class KSNote(KSBaseUploader):
    def __init__(
        self,
        image_paths,
        note,
        tags,
        publish_date: datetime | int,
        account_file,
        title: str | None = None,
        publish_strategy: str | None = None,
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
        self.image_paths = image_paths
        self.note = note or ""
        self.title = title or (self.note[:20] if self.note else "")
        self.tags = tags or []

    async def validate_upload_args(self):
        await self.validate_base_args()
        if not self.title or not str(self.title).strip():
            raise ValueError("快手图文上传时，title 是必须的")
        if not self.image_paths:
            raise ValueError("快手图文上传时，图片是必须的")

        if isinstance(self.image_paths, (str, Path)):
            self.image_paths = [self.image_paths]

        normalized_image_paths = []
        for image_path in self.image_paths:
            normalized_image_paths.append(str(self.validate_image_file(image_path)))
        self.image_paths = normalized_image_paths

    async def upload_note_content(self, page: Page) -> None:
        kuaishou_logger.info(_msg("🏃", f"小人开始搬运图文，共 {len(self.image_paths)} 张图片"))
        kuaishou_logger.info(_msg("🔀", "小人正在切换到图文发布"))
        await page.locator('div[role="tablist"] div[role="tab"]:has-text("图文")').click()
        await page.wait_for_timeout(1000)

        kuaishou_logger.info(_msg("📤", "小人正在上传图片"))
        upload_button = page.locator("button[class^='_upload-btn']").filter(has_text="上传图片")
        await upload_button.wait_for(state="visible", timeout=10000)

        async with page.expect_file_chooser() as fc_info:
            await upload_button.click()
        file_chooser = await fc_info.value
        await file_chooser.set_files(self.image_paths)

        know_button = page.locator('button[type="button"] span:text("我知道了")').first
        try:
            if await know_button.count() and await know_button.is_visible():
                await know_button.click()
        except Exception:
            pass

        await self.close_guide_overlay(page)

        kuaishou_logger.info(_msg("✍️", "小人开始填写图文内容和话题"))
        await page.get_by_text("描述").locator("xpath=following-sibling::div").click()
        await page.keyboard.press("Backspace")
        await page.keyboard.press("Control+KeyA")
        await page.keyboard.press("Delete")
        await page.keyboard.type(self.note)
        await page.keyboard.press("Enter")

        for index, tag in enumerate(self.tags[:3], start=1):
            kuaishou_logger.info(_msg("🏷️", f"小人正在添加第 {index} 个话题: #{tag}"))
            await page.keyboard.type(f"#{tag} ")
            await asyncio.sleep(2)

        max_retries = 60
        retry_count = 0
        while retry_count < max_retries:
            try:
                number = await page.locator("text=上传中").count()
                if number == 0:
                    kuaishou_logger.success(_msg("🥳", "图文素材已经传完啦"))
                    break

                if retry_count % 5 == 0:
                    kuaishou_logger.info(_msg("🏃", "小人正在努力上传图文素材"))

                if await page.locator("text=上传失败").count():
                    kuaishou_logger.warning(_msg("😵", "图文素材上传摔了一跤，小人马上重新上传"))
                    await page.locator('div.progress-div [class^="upload-btn-input"]').set_input_files(self.image_paths)

                await asyncio.sleep(2)
            except Exception as exc:
                kuaishou_logger.warning(_msg("😵", f"检查图文上传状态时出错，小人继续重试: {exc}"))
                await asyncio.sleep(2)
            retry_count += 1

        if retry_count == max_retries:
            kuaishou_logger.warning(_msg("😵", "超过最大重试次数，图文上传可能未完成"))

        if self.publish_strategy == KUAISHOU_PUBLISH_STRATEGY_SCHEDULED and self.publish_date != 0:
            await self.set_schedule_time(page, self.publish_date)

        publish_retry_count = 0
        max_publish_attempts = 120
        while publish_retry_count < max_publish_attempts:
            publish_retry_count += 1
            try:
                publish_button = page.get_by_role("button", name="发布", exact=True)
                if await publish_button.count() > 0:
                    await publish_button.click()
                    kuaishou_logger.info(_msg("📤", f"已点击发布按钮（尝试 {publish_retry_count}）"))

                await asyncio.sleep(1)
                confirm_button = page.get_by_role("button", name="确认发布", exact=True)
                if await confirm_button.count() > 0:
                    await confirm_button.click()
                    kuaishou_logger.info(_msg("📤", "已点击确认发布"))

                await page.wait_for_url(KUAISHOU_MANAGE_URL_PATTERN, timeout=5000)
                kuaishou_logger.success(_msg("🥳", "图文发布成功，小人开心收工"))
                break
            except Exception as exc:
                anti_bot_markers = ["操作频繁", "账号异常", "验证", "captcha", "人机", "打码"]
                if any(m in str(exc) for m in anti_bot_markers):
                    kuaishou_logger.error(_msg("🚫", f"检测到反爬拦截: {exc}，终止发布"))
                    raise
                kuaishou_logger.info(_msg("🏃", f"小人正在冲刺发布图文: {exc}（{publish_retry_count}/{max_publish_attempts}）"))
                if self.debug:
                    try:
                        await page.screenshot(full_page=True, path=f"debug_ks_note_{publish_retry_count}.png")
                    except Exception:
                        pass
                await asyncio.sleep(2)

        if publish_retry_count >= max_publish_attempts:
            kuaishou_logger.error(_msg("😵", f"图文发布按钮循环超时（{max_publish_attempts} 次）"))
            raise RuntimeError(f"快手图文发布按钮循环超时（{max_publish_attempts} 次尝试均未成功）")

    async def upload(self, playwright: Playwright) -> None:
        kuaishou_logger.info(_msg("🧍", "小人先检查 cookie、图片和发布时间"))
        await self.validate_upload_args()
        kuaishou_logger.info(_msg("🥳", "图文上传前检查通过"))

        user_data_dir = get_user_data_dir(self.account_file)
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            **build_persistent_launch_kwargs(headless=self.headless, executable_path=self.local_executable_path),
        )
        await migrate_storage_state_if_needed(context, self.account_file)
        context = await set_init_script(context)

        upload_success = False
        try:
            page = await context.new_page()
            nav_ok = False
            for attempt in range(3):
                try:
                    await page.goto(KUAISHOU_UPLOAD_URL, timeout=60000, wait_until="domcontentloaded")
                    nav_ok = True
                    break
                except Exception as e:
                    kuaishou_logger.warning(_msg("⚠️", f"导航重试 {attempt+1}/3: {e}"))
                    if attempt < 2:
                        await asyncio.sleep(2)
            if not nav_ok:
                raise RuntimeError("快手图文发布页加载失败（3次重试均超时）")
            kuaishou_logger.info(_msg("🧭", "小人正在赶往快手图文发布页"))
            await page.wait_for_url(KUAISHOU_UPLOAD_URL_PATTERN)

            await self.upload_note_content(page)
            upload_success = True
        finally:
            if upload_success:
                try:
                    await context.storage_state(path=self.account_file)
                except Exception:
                    pass
                kuaishou_logger.success(_msg("🥳", "cookie 更新完毕"))
                await asyncio.sleep(2)
            await context.close()

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)
