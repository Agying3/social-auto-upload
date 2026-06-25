# -*- coding: utf-8 -*-
from __future__ import annotations
from datetime import datetime

import asyncio
import inspect
import os
from pathlib import Path

from patchright.async_api import Page
from patchright.async_api import Playwright
from patchright.async_api import async_playwright

from conf import DEBUG_MODE, LOCAL_CHROME_HEADLESS, LOCAL_CHROME_PATH
from uploader.base_video import BaseVideoUploader
from utils.base_social_media import set_init_script, get_user_data_dir, migrate_storage_state_if_needed, build_persistent_launch_kwargs
from utils.login_qrcode import build_login_qrcode_path
from utils.login_qrcode import decode_qrcode_from_path
from utils.login_qrcode import print_terminal_qrcode
from utils.login_qrcode import remove_qrcode_file
from utils.login_qrcode import save_data_url_image
from utils.log import douyin_logger

DOUYIN_PUBLISH_STRATEGY_IMMEDIATE = "immediate"
DOUYIN_PUBLISH_STRATEGY_SCHEDULED = "scheduled"


def _msg(emoji: str, text: str) -> str:
    return f"{emoji} {text}"


async def _find_first_visible(page: Page, selectors: list[str], timeout_ms: int = 10000) -> "Page.locator" | None:
    """依次尝试多个选择器，返回第一个可见的元素 locator，找不到返回 None"""
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if await loc.count() and await loc.is_visible():
                return loc
        except Exception:
            continue
    return None


async def _check_browser_alive(page: Page) -> bool:
    """检查浏览器连接是否还活着（页面是否已关闭）
    
    注意：patchright 的 page.evaluate() 不支持 timeout 参数，
    需要用 asyncio.wait_for 包装来实现超时。
    """
    try:
        if page.is_closed():
            return False
        # patchright 的 evaluate() 不接受 timeout 参数，用 asyncio.wait_for 代替
        await asyncio.wait_for(
            page.evaluate("() => document.readyState"),
            timeout=3.0,
        )
        return True
    except asyncio.TimeoutError:
        return False
    except Exception:
        return False


async def _emit_qrcode_callback(qrcode_callback, payload: dict):
    if not qrcode_callback:
        return

    callback_result = qrcode_callback(payload)
    if inspect.isawaitable(callback_result):
        await callback_result


def _build_login_result(success: bool, status: str, message: str, account_file: str, qrcode: dict | None = None, current_url: str = "") -> dict:
    return {
        "success": success,
        "status": status,
        "message": message,
        "account_file": str(account_file),
        "qrcode": qrcode,
        "current_url": current_url,
    }


async def cookie_auth(account_file):
    user_data_dir = get_user_data_dir(account_file)
    async with async_playwright() as playwright:
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            **build_persistent_launch_kwargs(headless=False),
        )
        try:
            await migrate_storage_state_if_needed(context, account_file)
            context = await set_init_script(context)
            page = await context.new_page()
            await page.goto("https://creator.douyin.com/creator-micro/content/upload", timeout=60000, wait_until="domcontentloaded")
            try:
                await page.wait_for_url("https://creator.douyin.com/creator-micro/content/upload", timeout=5000)
            except Exception:
                return False

            if await page.get_by_text("手机号登录").count() or await page.get_by_text("扫码登录").count():
                return False

            return True
        finally:
            await context.close()


async def douyin_setup(account_file, handle=False, return_detail=False, qrcode_callback=None, headless: bool = LOCAL_CHROME_HEADLESS):
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            result = _build_login_result(False, "cookie_invalid", "cookie文件不存在或已失效", account_file)
            return result if return_detail else False
        douyin_logger.info(_msg("🥹", "cookie 失效了，准备打开浏览器重新登录"))
        result = await douyin_cookie_gen(account_file, qrcode_callback=qrcode_callback, headless=headless)
        return result if return_detail else result["success"]

    result = _build_login_result(True, "cookie_valid", "cookie有效", account_file)
    return result if return_detail else True


async def _extract_douyin_qrcode_src(page: Page) -> str:
    scan_login_tab = page.get_by_text("扫码登录", exact=True).first
    await scan_login_tab.wait_for(timeout=30000)

    qrcode_img = (
        scan_login_tab
        .locator("..")
        .locator("xpath=following-sibling::div[1]")
        .locator('img[aria-label="二维码"]')
        .first
    )

    if not await qrcode_img.count():
        qrcode_img = page.get_by_role("img", name="二维码").first

    await qrcode_img.wait_for(state="visible", timeout=30000)
    src = await qrcode_img.get_attribute("src")
    if not src:
        raise RuntimeError("未获取到抖音登录二维码地址")

    return src


async def _save_douyin_qrcode(page: Page, account_file: str, previous_qrcode_path: Path | None = None, qrcode_callback=None) -> dict:
    qrcode_src = await _extract_douyin_qrcode_src(page)
    qrcode_path = save_data_url_image(qrcode_src, build_login_qrcode_path(account_file))
    if previous_qrcode_path and previous_qrcode_path != qrcode_path:
        if remove_qrcode_file(previous_qrcode_path):
            douyin_logger.info(_msg("🧹", f"临时二维码文件已清理: {previous_qrcode_path}"))
    douyin_logger.info(_msg("🖼️", f"二维码已经准备好啦，已保存到: {qrcode_path}"))
    qrcode_content = decode_qrcode_from_path(qrcode_path)
    if qrcode_content:
        print_terminal_qrcode(qrcode_content, qrcode_path, "抖音APP")
    else:
        douyin_logger.warning(_msg("😵", f"终端没法完整显示二维码，请打开 {qrcode_path} 扫码"))
    qrcode_info = {
        "image_path": str(qrcode_path),
        "image_data_url": qrcode_src,
    }
    await _emit_qrcode_callback(qrcode_callback, qrcode_info)
    return qrcode_info


async def _is_douyin_login_completed(page: Page) -> bool:
    if not page.url.startswith("https://creator.douyin.com/creator-micro/home"):
        return False

    login_markers = [
        page.get_by_text("扫码登录", exact=True).first,
        page.get_by_text("手机号登录", exact=True).first,
        page.get_by_text("二维码失效", exact=True).first,
        page.get_by_role("img", name="二维码").first,
    ]

    for marker in login_markers:
        if not await marker.count():
            continue
        try:
            if await marker.is_visible():
                return False
        except Exception:
            continue

    return True


async def _wait_for_douyin_login(page: Page, account_file: str, qrcode_info: dict, qrcode_callback=None, poll_interval: int = 3, max_checks: int = 100) -> dict:
    qrcode_path = Path(qrcode_info["image_path"])
    for _ in range(max_checks):
        if await _is_douyin_login_completed(page):
            douyin_logger.info(_msg("🥳", f"扫码成功，已经跳转到登录后页面: {page.url}"))
            return _build_login_result(True, "success", "抖音扫码登录成功", account_file, qrcode_info, page.url)

        expired_box = page.get_by_text("二维码失效", exact=True).locator("..").first
        if await expired_box.count() and await expired_box.is_visible():
            douyin_logger.warning(_msg("😵", "二维码失效了，小人马上去刷新"))
            await expired_box.click()
            await asyncio.sleep(1)
            qrcode_info = await _save_douyin_qrcode(page, account_file, qrcode_path, qrcode_callback=qrcode_callback)
            qrcode_path = Path(qrcode_info["image_path"])

        await asyncio.sleep(poll_interval)

    return _build_login_result(False, "timeout", "等待抖音扫码登录超时", account_file, qrcode_info, page.url)


async def douyin_cookie_gen(
    account_file,
    qrcode_callback=None,
    poll_interval: int = 3,
    max_checks: int = 100,
    headless: bool = LOCAL_CHROME_HEADLESS,
):
    user_data_dir = get_user_data_dir(account_file)
    async with async_playwright() as playwright:
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            **build_persistent_launch_kwargs(headless=headless),
        )
        context = await set_init_script(context)
        qrcode_path = None
        result = _build_login_result(False, "failed", "抖音登录失败", account_file)
        try:
            page = await context.new_page()
            # 导航到抖音创作者中心（加重试，避免超时）
            nav_ok = False
            for attempt in range(3):
                try:
                    await page.goto(
                        "https://creator.douyin.com/",
                        timeout=90000,
                        wait_until="domcontentloaded",
                    )
                    nav_ok = True
                    break
                except Exception as e:
                    douyin_logger.warning(_msg("⚠️", f"导航重试 {attempt+1}/3: {e}"))
                    if attempt < 2:
                        await asyncio.sleep(2)
            if not nav_ok:
                raise RuntimeError("抖音创作者中心页面加载失败（3次重试均超时）")

            qrcode_info = await _save_douyin_qrcode(page, account_file, qrcode_callback=qrcode_callback)
            qrcode_path = Path(qrcode_info["image_path"])
            douyin_logger.info(_msg("🧍", "请扫码，小人正在耐心等待登录完成"))
            result = await _wait_for_douyin_login(
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
                    await verify_page.goto(
                        "https://creator.douyin.com/creator-micro/content/upload",
                        timeout=60000, wait_until="domcontentloaded",
                    )
                    if await verify_page.get_by_text("手机号登录").count() or \
                       await verify_page.get_by_text("扫码登录").count():
                        result = _build_login_result(
                            False,
                            "cookie_invalid",
                            "抖音扫码流程结束，但 cookie 校验失败",
                            account_file,
                            qrcode_info,
                            page.url,
                        )
                finally:
                    await verify_page.close()
        except Exception as exc:
            result = _build_login_result(False, "failed", str(exc), account_file, current_url=page.url if "page" in locals() else "")
        finally:
            if remove_qrcode_file(qrcode_path):
                douyin_logger.info(_msg("🧹", f"临时二维码文件已清理: {qrcode_path}"))
            if not result["success"]:
                douyin_logger.error(_msg("😢", f"登录失败: {result['message']}"))
            await context.close()
        return result


class DouYinBaseUploader(BaseVideoUploader):
    def __init__(
        self,
        publish_date: datetime | int,
        account_file,
        publish_strategy: str = DOUYIN_PUBLISH_STRATEGY_IMMEDIATE,
        debug: bool = DEBUG_MODE,
        headless: bool = LOCAL_CHROME_HEADLESS,
    ):
        self.publish_date = publish_date
        self.account_file = account_file
        self.publish_strategy = publish_strategy
        self.debug = debug
        self.date_format = "%Y年%m月%d日 %H:%M"
        self.local_executable_path = LOCAL_CHROME_PATH
        self.headless = headless

    async def validate_base_args(self):
        if not os.path.exists(self.account_file):
            raise RuntimeError(f"cookie文件不存在，请先完成抖音登录: {self.account_file}")
        if not await cookie_auth(self.account_file):
            raise RuntimeError(f"cookie文件已失效，请先完成抖音登录: {self.account_file}")
        if self.publish_strategy not in {DOUYIN_PUBLISH_STRATEGY_IMMEDIATE, DOUYIN_PUBLISH_STRATEGY_SCHEDULED}:
            raise ValueError(f"不支持的发布策略: {self.publish_strategy}")

        if self.publish_strategy == DOUYIN_PUBLISH_STRATEGY_SCHEDULED:
            self.publish_date = self.validate_publish_date(self.publish_date)
        else:
            self.publish_date = 0

    async def set_schedule_time_douyin(self, page, publish_date):
        label_element = page.locator("[class^='radio']:has-text('定时发布')")
        await label_element.click()
        await asyncio.sleep(1)
        publish_date_hour = publish_date.strftime("%Y-%m-%d %H:%M")

        await asyncio.sleep(1)
        await page.locator('.semi-input[placeholder="日期和时间"]').click()
        await page.keyboard.press("Control+KeyA")
        await page.keyboard.type(str(publish_date_hour))
        await page.keyboard.press("Enter")
        await asyncio.sleep(1)

    async def fill_title_and_description(self, page: Page, title: str, description: str, tags: list[str] | None = None):
        # 标题输入框：主选择器 + fallback
        title_input_loc = await _find_first_visible(
            page,
            [
                # 主选择器
                "input[type='text']",
                # fallback 按优先级排列
                "[class*='title'] input",
                "[class*='Title'] input",
                "[class*='input-area'] input",
                "[placeholder*='标题']",
                "[aria-label*='标题']",
            ],
            timeout_ms=15000,
        )
        if title_input_loc:
            await title_input_loc.fill(title[:30])
            douyin_logger.info(_msg("✍️", f"标题已填好: {title[:30]}"))
        else:
            douyin_logger.warning(_msg("😵", "找不到标题输入框，跳过标题填写"))
            # 尝试直接在页面上键盘输入
            await page.keyboard.press("Tab")
            await page.keyboard.type(title[:30])
            douyin_logger.warning(_msg("⚠️", "用键盘 Tab 方式填标题"))

        # 描述编辑器：主选择器 + fallback
        desc_editor_loc = await _find_first_visible(
            page,
            [
                # 主选择器
                "[contenteditable='true']",
                "[contenteditable=\"true\"]",
                # fallback
                ".zone-container[contenteditable='true']",
                "[class*='desc-editor']",
                "[class*='description']",
                "[class*='editor']",
                "[class*='rich-editor']",
            ],
            timeout_ms=15000,
        )
        if desc_editor_loc:
            await desc_editor_loc.click()
            await page.keyboard.press("Control+KeyA")
            await page.keyboard.press("Delete")
            await asyncio.sleep(0.3)
            await page.keyboard.type(description)
            douyin_logger.info(_msg("📝", f"描述已填好（{len(description)} 字）"))
        else:
            douyin_logger.warning(_msg("😵", "找不到描述编辑器，跳过描述填写"))

        # 话题标签
        for tag in tags or []:
            await page.keyboard.type(" #" + tag)
            await page.keyboard.press("Space")
        douyin_logger.info(_msg("🏷️", f"小人一共贴了 {len(tags or [])} 个话题"))

    async def set_location(self, page: Page, location: str = ""):
        if not location:
            return
        await page.locator('div.semi-select span:has-text("输入地理位置")').click()
        await page.keyboard.press("Backspace")
        await page.wait_for_timeout(2000)
        await page.keyboard.type(location)
        await page.wait_for_selector('div[role="listbox"] [role="option"]', timeout=5000)
        await page.locator('div[role="listbox"] [role="option"]').first.click()

    async def handle_product_dialog(self, page: Page, product_title: str):
        await page.wait_for_timeout(2000)
        await page.wait_for_selector('input[placeholder="请输入商品短标题"]', timeout=10000)
        short_title_input = page.locator('input[placeholder="请输入商品短标题"]')
        if not await short_title_input.count():
            douyin_logger.error(_msg("😵", "没找到商品短标题输入框"))
            return False

        product_title = product_title[:10]
        await short_title_input.fill(product_title)
        await page.wait_for_timeout(1000)

        finish_button = page.locator('button:has-text("完成编辑")')
        if "disabled" not in await finish_button.get_attribute("class"):
            await finish_button.click()
            douyin_logger.debug(_msg("🥳", "已点击“完成编辑”按钮"))
            await page.wait_for_selector(".semi-modal-content", state="hidden", timeout=5000)
            return True

        douyin_logger.error(_msg("😵", "“完成编辑”按钮是灰的，小人先把弹窗关掉"))
        cancel_button = page.locator('button:has-text("取消")')
        if await cancel_button.count():
            await cancel_button.click()
        else:
            close_button = page.locator(".semi-modal-close")
            await close_button.click()
        await page.wait_for_selector(".semi-modal-content", state="hidden", timeout=5000)
        return False

    async def set_product_link(self, page: Page, product_link: str, product_title: str):
        await page.wait_for_timeout(2000)
        try:
            await page.wait_for_selector("text=添加标签", timeout=10000)
            dropdown = page.get_by_text("添加标签").locator("..").locator("..").locator("..").locator(".semi-select").first
            if not await dropdown.count():
                douyin_logger.error(_msg("😵", "没找到标签下拉框"))
                return False
            douyin_logger.debug(_msg("🧍", "找到标签下拉框，小人准备选择“购物车”"))
            await dropdown.click()
            await page.wait_for_selector('[role="listbox"]', timeout=5000)
            await page.locator('[role="option"]:has-text("购物车")').click()
            douyin_logger.debug(_msg("🥳", "已经选中“购物车”"))

            await page.wait_for_selector('input[placeholder="粘贴商品链接"]', timeout=5000)
            input_field = page.locator('input[placeholder="粘贴商品链接"]')
            await input_field.fill(product_link)
            douyin_logger.debug(_msg("🔗", f"商品链接已经填好了: {product_link}"))

            add_button = page.locator('span:has-text("添加链接")')
            button_class = await add_button.get_attribute("class")
            if "disable" in button_class:
                douyin_logger.error(_msg("😵", "“添加链接”按钮现在点不了"))
                return False
            await add_button.click()
            douyin_logger.debug(_msg("🥳", "已点击“添加链接”按钮"))

            await page.wait_for_timeout(2000)
            error_modal = page.locator("text=未搜索到对应商品")
            if await error_modal.count():
                confirm_button = page.locator('button:has-text("确定")')
                await confirm_button.click()
                douyin_logger.error(_msg("😢", "这个商品链接无效"))
                return False

            if not await self.handle_product_dialog(page, product_title):
                return False

            douyin_logger.debug(_msg("🥳", "商品链接设置好了"))
            return True
        except Exception as e:
            douyin_logger.error(_msg("😢", f"设置商品链接时出错: {str(e)}"))
            return False


class DouYinVideo(DouYinBaseUploader):
    def __init__(
        self,
        title,
        file_path,
        tags,
        publish_date: datetime | int,
        account_file,
        thumbnail_landscape_path=None,
        productLink="",
        productTitle="",
        thumbnail_portrait_path=None,
        desc: str | None = None,
        publish_strategy: str = DOUYIN_PUBLISH_STRATEGY_IMMEDIATE,
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
        self.tags = tags
        self.thumbnail_landscape_path = thumbnail_landscape_path
        self.thumbnail_portrait_path = thumbnail_portrait_path
        self.productLink = productLink
        self.productTitle = productTitle
        self.desc = desc or ""

    async def validate_upload_args(self):
        await self.validate_base_args()
        if not self.title or not str(self.title).strip():
            raise ValueError("视频模式下，title 是必须的")

        self.file_path = str(self.validate_video_file(self.file_path))
        if self.thumbnail_landscape_path:
            self.thumbnail_landscape_path = str(self.validate_image_file(self.thumbnail_landscape_path))
        if self.thumbnail_portrait_path:
            self.thumbnail_portrait_path = str(self.validate_image_file(self.thumbnail_portrait_path))

    async def handle_upload_error(self, page):
        douyin_logger.warning(_msg("😵", "视频上传摔了一跤，小人马上重新上传"))
        # 兼容新旧版抖音上传页面
        old_btn = page.locator('div.progress-div [class^="upload-btn-input"]')
        if await old_btn.count():
            await old_btn.set_input_files(self.file_path)
        else:
            # 新版：找 upload-card 中的重新上传按钮
            reupload_btn = page.locator('[class*="upload-card"] button, [class*="upload-card"] [class*="reupload"]').first
            if await reupload_btn.count():
                async with page.expect_file_chooser(timeout=10000) as fc_info:
                    await reupload_btn.click()
                fc = await fc_info.value
                await fc.set_files(self.file_path)
            else:
                # 最后降级：直接用 file input
                file_input = page.locator('input[type="file"][accept*="video"]').first
                if await file_input.count():
                    await file_input.set_input_files(self.file_path)

    async def _dismiss_guide_popups(self, page: Page) -> None:
        """关闭抖音创作者中心的引导弹窗（shepherd 新手引导、功能提示等）"""
        try:
            # Shepherd 新手引导弹窗：点击"我知道了"按钮
            dismiss_btns = await page.evaluate("""() => {
                const results = [];
                // Shepherd 引导弹窗
                const shepherdBtns = document.querySelectorAll('.shepherd-element button, .shepherd-element [class*="btn"]');
                for (const btn of shepherdBtns) {
                    const text = (btn.textContent || '').trim();
                    if (text.includes('我知道了') || text.includes('知道了') || text.includes('关闭') || text.includes('下次再说') || text.includes('不再提示')) {
                        const rect = btn.getBoundingClientRect();
                        results.push({
                            x: Math.round(rect.x + rect.width / 2),
                            y: Math.round(rect.y + rect.height / 2),
                            text: text.substring(0, 20),
                        });
                    }
                }
                // 通用关闭按钮（X 图标）
                const closeBtns = document.querySelectorAll('[class*="shepherd"] [class*="close"], [class*="guide"] [class*="close"], [class*="modal"] [class*="close"]');
                for (const btn of closeBtns) {
                    const rect = btn.getBoundingClientRect();
                    if (rect.width > 0) {
                        results.push({
                            x: Math.round(rect.x + rect.width / 2),
                            y: Math.round(rect.y + rect.height / 2),
                            text: 'close',
                        });
                    }
                }
                return results;
            }""")
            for btn in dismiss_btns:
                douyin_logger.info(_msg("🧹", f"关闭引导弹窗: {btn.get('text', '')}"))
                await page.mouse.click(btn['x'], btn['y'])
                await asyncio.sleep(0.5)
        except Exception:
            pass  # 引导弹窗处理失败不影响主流程

    async def handle_auto_video_cover(self, page):
        if await page.get_by_text("请设置封面后再发布").first.is_visible():
            douyin_logger.info(_msg("🧍", "发布前还得先把封面弄好"))
            recommend_cover = page.locator('[class^="recommendCover-"]').first
            if await recommend_cover.count():
                douyin_logger.info(_msg("🏃", "小人去选第一个推荐封面"))
                try:
                    await recommend_cover.click()
                    await asyncio.sleep(1)
                    confirm_text = "是否确认应用此封面？"
                    if await page.get_by_text(confirm_text).first.is_visible():
                        douyin_logger.info(_msg("🪟", f"弹出确认框了: {confirm_text}"))
                        await page.get_by_role("button", name="确定").click()
                        douyin_logger.info(_msg("🥳", "推荐封面已经应用"))
                        await asyncio.sleep(1)
                    douyin_logger.info(_msg("🥳", "封面选择流程完成"))
                    return True
                except Exception as e:
                    douyin_logger.warning(_msg("😵", f"推荐封面没选成功: {e}"))
        return False

    async def set_thumbnail(self, page: Page):
        if not self.thumbnail_landscape_path and not self.thumbnail_portrait_path:
            return

        douyin_logger.info(_msg("🏃", "小人正在设置视频封面"))
        await page.click('text="选择封面"')
        cover_locator_str = 'div[id*="creator-content-modal"]'
        cover_locator = page.locator(cover_locator_str)
        await page.wait_for_selector(cover_locator_str)

        upload_input = cover_locator.locator("div[class^='semi-upload upload'] >> input.semi-upload-hidden-input")

        if self.thumbnail_landscape_path:
            await page.wait_for_timeout(1000)
            await upload_input.set_input_files(self.thumbnail_landscape_path)
            await page.wait_for_timeout(2000)
            douyin_logger.info(_msg("🖼️", "横版封面上传完成"))

        if self.thumbnail_portrait_path:
            await cover_locator.locator("div[class*='steps'] div").nth(1).click()
            await page.wait_for_timeout(1000)
            await upload_input.set_input_files(self.thumbnail_portrait_path)
            await page.wait_for_timeout(2000)
            douyin_logger.info(_msg("🖼️", "竖版封面上传完成"))

        await cover_locator.locator('button:visible:has-text("完成")').click()
        douyin_logger.info(_msg("🥳", "视频封面设置完成"))
        await page.wait_for_selector("div.extractFooter", state="detached")

    async def upload(self, playwright: Playwright) -> None:
        douyin_logger.info(_msg("🧍", "小人先检查 cookie、视频文件、封面和发布时间"))
        await self.validate_upload_args()
        douyin_logger.info(_msg("🥳", "上传前检查通过"))

        # 整体重试机制：最多 3 轮，中途任何错误都重来
        overall_retry = 0
        max_overall_retry = 3
        last_error = None

        while overall_retry < max_overall_retry:
            overall_retry += 1
            context = None
            page = None

            try:
                if overall_retry > 1:
                    douyin_logger.warning(_msg("🔄", f"第 {overall_retry} 轮重试启动（最多 {max_overall_retry} 轮）"))
                    await asyncio.sleep(5)  # 重试前稍作休息

                user_data_dir = get_user_data_dir(self.account_file)
                context = await playwright.chromium.launch_persistent_context(
                    user_data_dir=str(user_data_dir),
                    **build_persistent_launch_kwargs(headless=self.headless, executable_path=self.local_executable_path),
                )
                await migrate_storage_state_if_needed(context, self.account_file)
                context = await set_init_script(context)

                page = await context.new_page()
                await page.goto("https://creator.douyin.com/creator-micro/content/upload", timeout=60000, wait_until="domcontentloaded")
                douyin_logger.info(_msg("🏃", f"小人开始搬运视频: {self.title}.mp4"))
                douyin_logger.info(_msg("🧭", "小人正在赶往上传主页"))
                await page.wait_for_url("https://creator.douyin.com/creator-micro/content/upload")

                # 文件输入框：主选择器 + 4 个 fallback，依次尝试
                file_input_loc = await _find_first_visible(
                    page,
                    [
                        "div[class^='container'] input[type='file']",
                        "div[class*='container'] input[type='file']",
                        "input[type='file'][accept*='video']",
                        "input[type='file']",
                        ".upload-container input[type='file']",
                    ],
                    timeout_ms=15000,
                )
                if not file_input_loc:
                    douyin_logger.warning(_msg("😵", "找不到文件输入框，尝试 CDP 直接注入"))
                    # 最后降级：用 CDP 直接注入（绕过 DOM 选择）
                    file_input_files = await page.evaluate(
                        """(filePath) => {
                            const inputs = document.querySelectorAll('input[type="file"]');
                            const info = Array.from(inputs).map(i => ({
                                tag: i.tagName,
                                accept: i.accept || '',
                                visible: i.offsetParent !== null,
                                parent: i.parentElement?.className || '',
                            }));
                            return info;
                        }""",
                        self.file_path,
                    )
                    douyin_logger.warning(_msg("😵", f"文件输入框降级诊断: {file_input_files}"))
                    raise RuntimeError("无法定位抖音上传页面的文件输入框（主选择器和 fallback 均失败）")

                douyin_logger.info(_msg("📤", "找到文件输入框，小人准备上传"))
                await file_input_loc.set_input_files(self.file_path)

                # 等待进入发布页面（最多 90 秒，防止无限等待）
                page_ready = False
                for _ in range(90):
                    try:
                        await page.wait_for_url(
                            "https://creator.douyin.com/creator-micro/content/publish?enter_from=publish_page",
                            timeout=2000,
                        )
                        douyin_logger.info(_msg("🥳", "已经进入 version_1 发布页面"))
                        page_ready = True
                        break
                    except Exception:
                        pass
                    try:
                        await page.wait_for_url(
                            "https://creator.douyin.com/creator-micro/content/post/video?enter_from=publish_page",
                            timeout=2000,
                        )
                        douyin_logger.info(_msg("🥳", "已经进入 version_2 发布页面"))
                        page_ready = True
                        break
                    except Exception:
                        pass
                    # 检查页面上是否有发布表单元素（兜底：URL 没变但表单已加载）
                    try:
                        form_visible = await page.locator("[class*='title-area'], [class*='desc-area']").count() > 0
                        if form_visible:
                            douyin_logger.info(_msg("🥳", "发布表单已加载（URL 未变）"))
                            page_ready = True
                            break
                    except Exception:
                        pass
                    douyin_logger.debug(_msg("🧍", f"还没进到视频发布页面，继续等待... ({_}/90)"))
                    await asyncio.sleep(1)

                if not page_ready:
                    douyin_logger.warning(_msg("😵", "等待发布页面超时，尝试继续处理"))

                await asyncio.sleep(1)
                douyin_logger.info(_msg("✍️", "小人开始填标题、描述和话题"))
                await self.fill_title_and_description(page, self.title, self.desc or self.title, self.tags)

                # 等待视频上传完成（最多 300 秒，防止无限等待）
                # 关键：必须先确认"上传进度"出现，再等它消失，才算完成
                upload_started = False
                upload_wait_count = 0
                max_upload_wait = 300  # 300 轮 × 2 秒 = 600 秒
                while True:
                    try:
                        upload_state = await page.evaluate("""() => {
                            // ═══ 扩展上传进度检测（抖音页面常改版）═══
                            const selectors = [
                                '[class*="uploading-container"]',
                                '[class*="upload-progress"]',
                                '[class*="uploading"]',
                                '[class*="progress-bar"]',
                                '[class*="progress"]',
                                '[class*="percent"]',
                                '[class*="video-upload"]',
                                '[class*="upload-card"]',
                                '[class*="video-card"]',
                                '[class*="file-card"]',
                            ];
                            let hasUploading = false;
                            let isFailed = false;
                            let hasReupload = false;
                            
                            for (const sel of selectors) {
                                try {
                                    const el = document.querySelector(sel);
                                    if (el && el.offsetWidth > 0) {
                                        const text = (el.innerText || el.textContent || '').trim();
                                        if (text.includes('上传中') || text.includes('上传进度') || text.includes('%')) {
                                            hasUploading = true;
                                        }
                                        if (text.includes('上传失败')) isFailed = true;
                                        if (text.includes('重新上传')) hasReupload = true;
                                    }
                                } catch(e) {}
                            }
                            
                            // 检测 upload-card 元素
                            const uploadCards = document.querySelectorAll('[class*="upload-card"], [class*="card"]');
                            for (const card of uploadCards) {
                                try {
                                    const text = (card.innerText || '');
                                    if (text.includes('上传过程中') || text.includes('上传中')) hasUploading = true;
                                    if (text.includes('上传失败') || text.includes('失败')) isFailed = true;
                                } catch(e) {}
                            }
                            
                            // 检测 long-card（上传完成 → 显示重新上传按钮）
                            const longCardDiv = document.querySelector('[class^="long-card"] div, [class*="long-card"] div');
                            if (longCardDiv) {
                                try {
                                    const t = longCardDiv.innerText || '';
                                    if (t.includes('重新上传')) hasReupload = true;
                                } catch(e) {}
                            }
                            
                            // 检测 progress-div
                            const progressDiv = document.querySelector('div.progress-div > div, [class*="progress"] div');
                            if (progressDiv) {
                                try {
                                    const t = progressDiv.innerText || '';
                                    if (t.includes('上传失败')) isFailed = true;
                                    if (t.includes('%')) hasUploading = true;
                                } catch(e) {}
                            }
                            
                            // ═══ 额外诊断：统计页面上所有可见文本（前 20 行）═══
                            let pageSummary = '';
                            try {
                                const body = document.querySelector('[class*="content"], [class*="main"], main, body');
                                if (body) {
                                    const lines = (body.innerText || '').split('\\n').filter(l => l.trim()).slice(0, 20);
                                    pageSummary = lines.join(' | ');
                                }
                            } catch(e) {}
                            
                            return {
                                hasUploading: hasUploading,
                                isFailed: isFailed,
                                hasReupload: hasReupload,
                                pageSummary: pageSummary.substring(0, 200),
                            };
                        }""")

                        if upload_state.get("hasReupload"):
                            douyin_logger.success(_msg("🥳", "视频已经传完啦"))
                            break

                        if upload_state.get("hasUploading"):
                            upload_started = True
                            douyin_logger.info(_msg("🏃", "小人正在努力上传视频"))
                        elif upload_started:
                            douyin_logger.success(_msg("🥳", "视频上传完成"))
                            break
                        else:
                            douyin_logger.info(_msg("⏳", "等待上传开始..."))

                        if upload_state.get("isFailed"):
                            douyin_logger.error(_msg("😵", "检测到上传失败，小人准备重试"))
                            await self.handle_upload_error(page)
                            continue

                        await asyncio.sleep(2)
                    except Exception:
                        douyin_logger.debug(_msg("🧍", "小人还在等视频上传完成"))
                        await asyncio.sleep(2)

                    upload_wait_count += 1
                    if upload_wait_count >= max_upload_wait:
                        douyin_logger.error(_msg("😵", f"上传等待超时（{max_upload_wait * 2}秒），强制结束等待"))
                        # 诊断：输出页面摘要
                        try:
                            diag = await page.evaluate("() => (document.body?.innerText || '').substring(0, 300)")
                            douyin_logger.info(_msg("🔍", f"页面诊断: {diag}"))
                        except Exception:
                            pass
                        break
                    # 每 5 轮未开始上传时输出诊断
                    if not upload_started and upload_wait_count == 5:
                        try:
                            page_text = upload_state.get("pageSummary", "")
                            if page_text:
                                douyin_logger.info(_msg("🔍", f"上传诊断({upload_wait_count}轮): {page_text}"))
                        except Exception:
                            pass
                    # 每 10 轮检查一次浏览器是否还活着
                    if upload_wait_count % 10 == 0 and not await _check_browser_alive(page):
                        douyin_logger.error(_msg("😵", "浏览器在上传过程中意外断开"))
                        raise RuntimeError("浏览器在视频上传过程中意外断开")

                if self.productLink and self.productTitle:
                    douyin_logger.info(_msg("🛒", "小人正在设置商品链接"))
                    await self.set_product_link(page, self.productLink, self.productTitle)
                    douyin_logger.info(_msg("🥳", "商品链接设置完成"))

                await self.set_thumbnail(page)

                third_part_element = '[class^="info"] > [class^="first-part"] div div.semi-switch'
                if await page.locator(third_part_element).count():
                    if "semi-switch-checked" not in await page.eval_on_selector(third_part_element, "div => div.className"):
                        await page.locator(third_part_element).locator("input.semi-switch-native-control").click()

                if self.publish_strategy == DOUYIN_PUBLISH_STRATEGY_SCHEDULED and self.publish_date != 0:
                    await self.set_schedule_time_douyin(page, self.publish_date)

                # 发布按钮循环：最多 120 轮（每轮约 3-5 秒，最多 6 分钟）
                publish_retry_count = 0
                max_publish_attempts = 120
                while publish_retry_count < max_publish_attempts:
                    publish_retry_count += 1

                    if not await _check_browser_alive(page):
                        douyin_logger.error(_msg("😵", "浏览器连接已断开，发布流程终止"))
                        raise RuntimeError("浏览器在发布过程中意外断开")

                    try:
                        await self._dismiss_guide_popups(page)

                        # 优先用 get_by_role 精确匹配发布按钮，避免匹配无关元素
                        publish_btn_loc = None
                        publish_button = page.get_by_role("button", name="发布", exact=True)
                        if await publish_button.count():
                            publish_btn_loc = publish_button.first

                        # fallback：尝试 CSS 选择器（仅限可见的按钮类元素）
                        if not publish_btn_loc:
                            publish_btn_loc = await _find_first_visible(
                                page,
                                [
                                    "button[class*='publish']",
                                    "button[class*='Publish']",
                                    "button[class*='submit']",
                                    "button[class*='Submit']",
                                ],
                                timeout_ms=5000,
                            )

                        if publish_btn_loc:
                            try:
                                await publish_btn_loc.click()
                                douyin_logger.info(_msg("📤", f"已点击发布按钮（尝试 {publish_retry_count}）"))
                            except Exception as click_err:
                                douyin_logger.warning(_msg("⚠️", f"点击失败，尝试 JS: {click_err}"))
                                await page.evaluate("(el) => el.click()", await publish_btn_loc.element_handle())
                            douyin_logger.info(_msg("⏳", "等待发布完成..."))
                        else:
                            douyin_logger.debug(_msg("🧍", f"发布按钮未找到（{publish_retry_count}/{max_publish_attempts}）"))

                        await page.wait_for_url(
                            "https://creator.douyin.com/creator-micro/content/manage**",
                            timeout=60000,
                        )
                        douyin_logger.success(_msg("🥳", "视频发布成功，小人开心收工"))
                        break
                    except Exception as e:
                        err_str = str(e)

                        try:
                            is_publishing = await page.evaluate("""() => {
                                const toasts = document.querySelectorAll('[class*="toast"], [class*="Toast"], [class*="message"], [class*="Message"]');
                                for (const t of toasts) {
                                    const text = (t.innerText || '').trim();
                                    if (text.includes('正在发布') || text.includes('发布中') || text.includes('发布成功')) return text;
                                }
                                return null;
                            }""")
                        except Exception:
                            is_publishing = None

                        if is_publishing:
                            douyin_logger.info(_msg("⏳", f"发布中: {is_publishing}"))
                            try:
                                await page.wait_for_url(
                                    "https://creator.douyin.com/creator-micro/content/manage**",
                                    timeout=60000,
                                )
                                douyin_logger.success(_msg("🥳", "视频发布成功"))
                                break
                            except Exception:
                                douyin_logger.warning(_msg("⚠️", "发布等待超时"))

                        # 检测反爬拦截 → 立即终止，不重试
                        anti_bot_markers = ["操作频繁", "账号异常", "验证", "captcha", "Captcha", "人机", "打码"]
                        if any(m in err_str for m in anti_bot_markers):
                            douyin_logger.error(_msg("🚫", f"检测到反爬拦截: {e}，终止发布"))
                            if self.debug:
                                try:
                                    await page.screenshot(full_page=True, path=str(Path(self.file_path).parent / "error_antibot.png"))
                                except Exception:
                                    pass
                            raise

                        if "TimeoutError" in err_str or "timeout" in err_str.lower():
                            await self.handle_auto_video_cover(page)
                            douyin_logger.warning(_msg("⏳", f"发布等待中... ({publish_retry_count}/{max_publish_attempts})"))
                        else:
                            douyin_logger.warning(_msg("⚠️", f"发布尝试失败: {err_str}（{publish_retry_count}/{max_publish_attempts}）"))
                            await self.handle_auto_video_cover(page)

                        if self.debug:
                            try:
                                debug_path = Path(self.file_path).parent / f"debug_publish_{publish_retry_count}.png"
                                await page.screenshot(full_page=True, path=str(debug_path))
                                douyin_logger.info(_msg("📸", f"调试截图: {debug_path}"))
                            except Exception:
                                pass

                        await asyncio.sleep(3)

                if publish_retry_count >= max_publish_attempts:
                    douyin_logger.error(_msg("😵", f"发布按钮循环超时（{max_publish_attempts} 次）"))
                    try:
                        await page.screenshot(full_page=True, path=str(Path(self.file_path).parent / "error_publish_timeout.png"))
                    except Exception:
                        pass
                    raise RuntimeError(f"发布按钮循环超时（{max_publish_attempts} 次尝试均未成功）")

                # 成功：更新 cookie 并正常退出
                try:
                    await context.storage_state(path=self.account_file)
                except Exception:
                    pass
                douyin_logger.success(_msg("🥳", "cookie 更新完毕"))
                await asyncio.sleep(2)
                await context.close()
                return  # 成功完成，退出整体重试循环

            except Exception as e:
                last_error = e
                douyin_logger.warning(_msg("⚠️", f"第 {overall_retry} 轮失败: {e}"))
                # 保存失败截图（如果页面还活着）
                if page and not (page.is_closed() if hasattr(page, "is_closed") else False):
                    try:
                        screenshot_path = Path(self.file_path).parent / f"error_round{overall_retry}.png"
                        await page.screenshot(full_page=True, path=str(screenshot_path))
                        douyin_logger.info(_msg("📸", f"第 {overall_retry} 轮失败截图: {screenshot_path}"))
                    except Exception:
                        pass
            finally:
                # 确保浏览器上下文被关闭（无论成功还是失败）
                if context:
                    try:
                        await context.close()
                    except Exception:
                        pass

        # 3 轮全部失败，抛出最后一次错误
        douyin_logger.error(_msg("😵", f"发布流程全部 {max_overall_retry} 轮均失败，最后错误: {last_error}"))
        raise last_error or RuntimeError(f"发布流程全部 {max_overall_retry} 轮均失败")

    async def douyin_upload_video(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)

    async def main(self):
        await self.douyin_upload_video()


class DouYinNote(DouYinBaseUploader):
    def __init__(
        self,
        image_paths,
        note,
        tags,
        publish_date: datetime | int,
        account_file,
        title: str | None = None,
        publish_strategy: str = DOUYIN_PUBLISH_STRATEGY_IMMEDIATE,
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
        self.title = title or (self.note[:30] if self.note else "")
        self.tags = tags or []

    async def validate_upload_args(self):
        await self.validate_base_args()
        if not self.title or not str(self.title).strip():
            raise ValueError("图文模式下，title 是必须的")
        if not self.image_paths:
            raise ValueError("图文模式下，图片是必须的")

        if isinstance(self.image_paths, (str, Path)):
            self.image_paths = [self.image_paths]

        if len(self.image_paths) > 35:
            raise ValueError("图文模式下最多只支持上传 35 张图片")

        normalized_image_paths = []
        for image_path in self.image_paths:
            normalized_image_paths.append(str(self.validate_image_file(image_path)))
        self.image_paths = normalized_image_paths

    async def upload_note_content(self, page: Page) -> None:
        douyin_logger.info(_msg("🏃", f"小人开始搬运图文，共 {len(self.image_paths)} 张图片"))
        douyin_logger.info(_msg("🔀", "小人正在切换到图文发布"))
        note_tab_loc = await _find_first_visible(
            page,
            [
                "[class*='image']:has-text('发布图文')",
                "[class*='note']:has-text('发布图文')",
                "button:has-text('发布图文')",
                "div:has-text('发布图文')",
                "[role='tab']:has-text('图文')",
            ],
            timeout_ms=10000,
        )
        if note_tab_loc:
            await note_tab_loc.click()
        else:
            # 降级：用精确文本点击
            await page.get_by_text("发布图文", exact=True).click()
        await page.wait_for_timeout(1000)

        douyin_logger.info(_msg("📤", "小人正在上传图片"))
        image_input_loc = await _find_first_visible(
            page,
            [
                "div[class^='container'] input[type='file'][accept*='image']",
                "div[class^='container'] input[accept*='image']",
                "input[type='file'][accept*='image']",
                "input[type='file']",
            ],
            timeout_ms=10000,
        )
        if not image_input_loc:
            raise RuntimeError("无法定位图片上传输入框")
        await image_input_loc.set_input_files(self.image_paths)

        # 图片上传等待（最多 180 轮 × 0.5 秒 = 90 秒）
        image_upload_count = 0
        while image_upload_count < 180:
            image_upload_count += 1
            if not await _check_browser_alive(page):
                raise RuntimeError("浏览器在图片上传过程中意外断开")
            try:
                await page.wait_for_url(
                    "**/creator-micro/content/post/image?**",
                    timeout=2000,
                )
                douyin_logger.info(_msg("🥳", "已经进入图文发布页面"))
                break
            except Exception:
                douyin_logger.debug(_msg("🧍", f"等图片上传...（{image_upload_count}/180）"))
                await asyncio.sleep(0.5)
        else:
            douyin_logger.warning(_msg("😵", "图片上传等待超时，尝试继续处理"))

        await asyncio.sleep(1)
        douyin_logger.info(_msg("✍️", "小人开始填标题、描述和话题"))
        await self.fill_title_and_description(page, self.title, self.note, self.tags)

        if self.publish_strategy == DOUYIN_PUBLISH_STRATEGY_SCHEDULED and self.publish_date != 0:
            await self.set_schedule_time_douyin(page, self.publish_date)

        note_publish_count = 0
        max_note_publish = 60  # 最多 60 轮（约 30 秒）
        while note_publish_count < max_note_publish:
            note_publish_count += 1
            if not await _check_browser_alive(page):
                raise RuntimeError("浏览器在图文发布过程中意外断开")
            try:
                publish_button = page.get_by_role("button", name="发布", exact=True)
                if await publish_button.count():
                    await publish_button.click()
                await page.wait_for_url(
                    "**/creator-micro/content/manage?enter_from=publish**",
                    timeout=3000,
                )
                douyin_logger.success(_msg("🥳", "图文发布成功，小人开心收工"))
                return True
            except Exception:
                douyin_logger.info(_msg("🏃", f"小人正在冲刺发布图文（{note_publish_count}/{max_note_publish}）"))
                await asyncio.sleep(0.5)
        douyin_logger.error(_msg("😵", "图文发布按钮循环超时"))
        raise RuntimeError("图文发布按钮循环超时")

    async def upload(self, playwright: Playwright) -> None:
        douyin_logger.info(_msg("🧍", "小人先检查 cookie、图片和发布时间"))
        await self.validate_upload_args()
        douyin_logger.info(_msg("🥳", "图文上传前检查通过"))

        # 整体重试机制：最多 3 轮
        overall_retry = 0
        max_overall_retry = 3
        last_error = None

        while overall_retry < max_overall_retry:
            overall_retry += 1
            context = None
            page = None

            try:
                if overall_retry > 1:
                    douyin_logger.warning(_msg("🔄", f"图文第 {overall_retry} 轮重试"))
                    await asyncio.sleep(5)

                user_data_dir = get_user_data_dir(self.account_file)
                context = await playwright.chromium.launch_persistent_context(
                    user_data_dir=str(user_data_dir),
                    **build_persistent_launch_kwargs(headless=self.headless, executable_path=self.local_executable_path),
                )
                await migrate_storage_state_if_needed(context, self.account_file)
                context = await set_init_script(context)

                page = await context.new_page()
                await page.goto("https://creator.douyin.com/creator-micro/content/upload", timeout=60000, wait_until="domcontentloaded")
                douyin_logger.info(_msg("🧭", "小人正在赶往图文发布页"))
                await page.wait_for_url("https://creator.douyin.com/creator-micro/content/upload")

                await self.upload_note_content(page)

                # 成功：更新 cookie 并正常退出
                try:
                    await context.storage_state(path=self.account_file)
                except Exception:
                    pass
                douyin_logger.success(_msg("🥳", "cookie 更新完毕"))
                await asyncio.sleep(2)
                await context.close()
                return  # 成功，退出重试循环

            except Exception as e:
                last_error = e
                douyin_logger.warning(_msg("⚠️", f"图文第 {overall_retry} 轮失败: {e}"))
                if page:
                    try:
                        await page.screenshot(full_page=True, path=str(Path(self.image_paths[0]).parent / f"error_note_round{overall_retry}.png"))
                    except Exception:
                        pass
            finally:
                if context:
                    try:
                        await context.close()
                    except Exception:
                        pass

        douyin_logger.error(_msg("😵", f"图文发布全部 {max_overall_retry} 轮均失败"))
        raise last_error or RuntimeError(f"图文发布全部 {max_overall_retry} 轮均失败")

    async def douyin_upload_note(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)
