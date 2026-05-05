# -*- coding: utf-8 -*-
"""B站浏览器自动化上传器

由于 stream_gears（biliupR）的投稿 API 已被 B站封禁（返回"投稿工具已停用"），
改用 patchright 浏览器自动化方式上传视频到 B站创作中心。

上传页面: https://member.bilibili.com/platform/upload/video/frame
登录页面: https://passport.bilibili.com/login
"""
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
from utils.base_social_media import set_init_script
from utils.log import bilibili_logger

BILIBILI_UPLOAD_URL = "https://member.bilibili.com/platform/upload/video/frame"
BILIBILI_LOGIN_URL = "https://passport.bilibili.com/login"
BILIBILI_HOME_URL = "https://member.bilibili.com/platform/home"
BILIBILI_PUBLISH_STRATEGY_IMMEDIATE = "immediate"
BILIBILI_PUBLISH_STRATEGY_SCHEDULED = "scheduled"


def _msg(emoji: str, text: str) -> str:
    return f"{emoji} {text}"


async def _find_first_visible(page: Page, selectors: list[str], timeout_ms: int = 10000):
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
    """检查浏览器连接是否还活着
    
    注意：patchright 的 page.evaluate() 不支持 timeout 参数，
    需要用 asyncio.wait_for 包装来实现超时。
    """
    try:
        if page.is_closed():
            return False
        # patchright 的 evaluate() 不接受 timeout 参数，用 asyncio.wait_for 代替
        await asyncio.wait_for(
            page.evaluate("() => document.readyState"),
            timeout=8.0,
        )
        return True
    except asyncio.TimeoutError:
        # evaluate 超时——页面可能卡住，但浏览器可能还活着
        bilibili_logger.warning(_msg("⚠️", "浏览器 evaluate 超时（8秒），但可能仍活着"))
        return False
    except Exception:
        return False


async def _emit_qrcode_callback(qrcode_callback, payload: dict):
    if not qrcode_callback:
        return
    callback_result = qrcode_callback(payload)
    if inspect.isawaitable(callback_result):
        await callback_result


def _build_login_result(success, status, message, account_file, qrcode=None, current_url=""):
    return {
        "success": success,
        "status": status,
        "message": message,
        "account_file": str(account_file),
        "qrcode": qrcode,
        "current_url": current_url,
    }


async def cookie_auth(account_file):
    """校验 B站 cookie 是否有效"""
    async with async_playwright() as playwright:
        launch_kwargs = {"headless": True, "args": ["--disable-gpu","--disable-dev-shm-usage","--no-sandbox","--disable-extensions","--disable-software-rasterizer"]}
        if LOCAL_CHROME_PATH:
            launch_kwargs["executable_path"] = LOCAL_CHROME_PATH
        else:
            launch_kwargs["channel"] = "chrome"
        browser = await playwright.chromium.launch(**launch_kwargs)
        try:
            context = await browser.new_context(storage_state=account_file)
            context = await set_init_script(context)
            page = await context.new_page()
            await page.goto(BILIBILI_HOME_URL, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(3)

            # 检查是否被重定向到登录页
            current_url = page.url
            if "passport.bilibili.com" in current_url:
                return False

            # 检查页面上是否有登录按钮
            login_btn = page.locator('text=登录').first
            if await login_btn.count() and await login_btn.is_visible():
                return False

            return True
        except Exception:
            return False
        finally:
            await browser.close()


async def bilibili_setup(account_file, handle=False, return_detail=False, qrcode_callback=None, headless=False):
    """B站登录入口"""
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            result = _build_login_result(False, "cookie_invalid", "cookie文件不存在或已失效", account_file)
            return result if return_detail else False
        bilibili_logger.info(_msg("🥹", "cookie 失效了，准备打开浏览器重新登录"))
        result = await bilibili_cookie_gen(account_file, qrcode_callback=qrcode_callback, headless=headless)
        return result if return_detail else result["success"]

    result = _build_login_result(True, "cookie_valid", "cookie有效", account_file)
    return result if return_detail else True


async def bilibili_cookie_gen(account_file, qrcode_callback=None, headless=False):
    """通过浏览器扫码登录B站，保存 cookie"""
    async with async_playwright() as playwright:
        launch_kwargs = {"headless": headless, "args": ["--disable-gpu","--disable-dev-shm-usage","--no-sandbox","--disable-extensions","--disable-software-rasterizer"]}
        if LOCAL_CHROME_PATH:
            launch_kwargs["executable_path"] = LOCAL_CHROME_PATH
        else:
            launch_kwargs["channel"] = "chrome"
        browser = await playwright.chromium.launch(**launch_kwargs)
        context = await browser.new_context()
        context = await set_init_script(context)
        result = _build_login_result(False, "failed", "B站登录失败", account_file)
        try:
            page = await context.new_page()
            # 导航到B站登录页（加重试）
            nav_ok = False
            for attempt in range(3):
                try:
                    await page.goto(BILIBILI_LOGIN_URL, timeout=60000, wait_until="domcontentloaded")
                    nav_ok = True
                    break
                except Exception as e:
                    bilibili_logger.warning(_msg("⚠️", f"B站登录页导航重试 {attempt+1}/3: {e}"))
                    if attempt < 2:
                        await asyncio.sleep(2)
            if not nav_ok:
                raise RuntimeError("B站登录页加载失败（3次重试均超时）")

            bilibili_logger.info(_msg("🧍", "已打开B站登录页面，等待扫码..."))

            # 等待页面加载完成（等待登录表单出现）
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass  # 不强求 networkidle，继续尝试

            # 等待二维码出现
            qrcode_img = None
            for sel in [
                '.qrcode-img img',
                'img[src*="qrcode"]',
                '.login-qrcode img',
                'img[alt*="二维码"]',
                '.passport-qrcode img',
                '.qrcode-con img',
                'div.qrcode-box img',
                'canvas',  # 有些页面用 canvas 渲染二维码
            ]:
                try:
                    loc = page.locator(sel).first
                    await loc.wait_for(state="visible", timeout=5000)
                    qrcode_img = loc
                    bilibili_logger.info(_msg("🖼️", f"找到二维码元素: {sel}"))
                    break
                except Exception:
                    continue

            if qrcode_img:
                qrcode_src = await qrcode_img.get_attribute("src")
                if qrcode_src and qrcode_callback:
                    qrcode_info = {
                        "image_path": "",
                        "image_data_url": qrcode_src,
                    }
                    await _emit_qrcode_callback(qrcode_callback, qrcode_info)
                    bilibili_logger.info(_msg("🖼️", "二维码已发送给前端"))
            else:
                # 没找到二维码元素，截图发送给前端
                bilibili_logger.warning(_msg("⚠️", "未找到二维码元素，尝试截图"))
                try:
                    screenshot_bytes = await page.screenshot()
                    import base64
                    screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
                    if qrcode_callback:
                        qrcode_info = {
                            "image_path": "",
                            "image_data_url": f"data:image/png;base64,{screenshot_b64}",
                        }
                        await _emit_qrcode_callback(qrcode_callback, qrcode_info)
                        bilibili_logger.info(_msg("📸", "登录页截图已发送给前端"))
                except Exception as e:
                    bilibili_logger.error(_msg("😢", f"截图失败: {e}"))

            # 等待登录成功（检测 URL 跳转或登录按钮消失）
            for _ in range(120):
                current_url = page.url
                # 成功跳转到首页
                if "passport.bilibili.com" not in current_url:
                    bilibili_logger.info(_msg("🥳", f"登录成功，已跳转到: {current_url}"))
                    await asyncio.sleep(2)
                    await context.storage_state(path=account_file)
                    result = _build_login_result(True, "success", "B站登录成功", account_file, current_url=current_url)
                    break

                # 检查是否有扫码成功的提示
                try:
                    scan_success = page.locator('text=扫码成功').first
                    if await scan_success.count() and await scan_success.is_visible():
                        bilibili_logger.info(_msg("🥳", "扫码成功，等待确认登录..."))
                except Exception:
                    pass

                await asyncio.sleep(3)
            else:
                result = _build_login_result(False, "timeout", "B站扫码登录超时", account_file, current_url=page.url)

        except Exception as exc:
            result = _build_login_result(False, "failed", str(exc), account_file, current_url=page.url if "page" in locals() else "")
        finally:
            if not result["success"]:
                bilibili_logger.error(_msg("😢", f"登录失败: {result['message']}"))
            await context.close()
            await browser.close()
        return result


class BilibiliVideo(BaseVideoUploader):
    """B站视频上传器（浏览器自动化方式）"""

    def __init__(
        self,
        title,
        file_path,
        tags,
        publish_date: datetime | int,
        account_file,
        desc: str | None = None,
        tid: int = 21,
        publish_strategy: str = BILIBILI_PUBLISH_STRATEGY_IMMEDIATE,
        debug: bool = DEBUG_MODE,
        headless: bool = False,  # B站需要 headed 模式
    ):
        self.title = title
        self.file_path = file_path
        self.tags = tags or []
        self.publish_date = publish_date
        self.account_file = account_file
        self.desc = desc or ""
        self.tid = tid
        self.publish_strategy = publish_strategy
        self.debug = debug
        self.local_executable_path = LOCAL_CHROME_PATH
        self.headless = headless

    async def validate_upload_args(self):
        if not os.path.exists(self.account_file):
            raise RuntimeError(f"cookie文件不存在，请先完成B站登录: {self.account_file}")
        if not self.title or not str(self.title).strip():
            raise ValueError("视频模式下，title 是必须的")
        self.file_path = str(self.validate_video_file(self.file_path))
        if self.publish_strategy == BILIBILI_PUBLISH_STRATEGY_SCHEDULED:
            self.publish_date = self.validate_publish_date(self.publish_date)
        else:
            self.publish_date = 0

    async def _wait_for_upload_complete(self, page: Page) -> bool:
        """等待视频上传完成"""
        upload_started = False
        max_wait = 300  # 最多等 600 秒
        consecutive_failures = 0  # 连续检测失败计数
        max_consecutive_failures = 5  # 允许连续失败5次（约10秒）才判定断开
        for i in range(max_wait):
            if not await _check_browser_alive(page):
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    raise RuntimeError(f"浏览器在上传过程中意外断开（连续{consecutive_failures}次检测失败）")
                bilibili_logger.warning(_msg("⚠️", f"浏览器检测失败 {consecutive_failures}/{max_consecutive_failures}，继续等待..."))
                await asyncio.sleep(2)
                continue
            else:
                consecutive_failures = 0  # 重置计数

            try:
                upload_state = await page.evaluate("""() => {
                    // 检查上传进度条
                    const progressBars = document.querySelectorAll('[class*="progress"]');
                    let isUploading = false;
                    for (const bar of progressBars) {
                        const text = (bar.innerText || '');
                        if (text.includes('%') || text.includes('上传中')) {
                            isUploading = true;
                            break;
                        }
                    }

                    // 检查上传完成标志
                    const allText = document.body.innerText || '';
                    const hasComplete = allText.includes('上传完成') || allText.includes('重新上传');
                    const hasFailed = allText.includes('上传失败');

                    // 检查上传状态元素
                    const statusEls = document.querySelectorAll('[class*="upload-status"], [class*="upload-state"]');
                    let statusText = '';
                    for (const el of statusEls) {
                        statusText += (el.innerText || '') + ' ';
                    }

                    return {
                        isUploading: isUploading || allText.includes('上传中'),
                        hasComplete: hasComplete || statusText.includes('完成'),
                        hasFailed: hasFailed,
                    };
                }""")

                if upload_state.get("hasComplete"):
                    bilibili_logger.info(_msg("🥳", "视频上传完成"))
                    return True

                if upload_state.get("hasFailed"):
                    bilibili_logger.error(_msg("😵", "视频上传失败"))
                    return False

                if upload_state.get("isUploading"):
                    upload_started = True
                    if i % 10 == 0:
                        bilibili_logger.info(_msg("🏃", "视频上传中..."))
                elif not upload_started:
                    if i % 5 == 0:
                        bilibili_logger.info(_msg("⏳", "等待上传开始..."))

            except Exception:
                bilibili_logger.debug(_msg("🧍", "检查上传状态时出错，继续等待"))

            await asyncio.sleep(2)

        bilibili_logger.error(_msg("😵", "视频上传超时"))
        return False

    async def _upload_cover(self, page: Page):
        """上传封面（B站投稿必填项）

        上传视频后 B站通常会自动截取视频帧作为封面。
        如果封面为空（.cover-empty 存在），需要手动上传封面图片。
        使用视频文件本身的第一帧截取为封面。
        """
        try:
            await asyncio.sleep(1)

            # 检查封面是否已自动截取
            cover_ready = await page.evaluate("""() => {
                const coverContent = document.querySelector('.cover-content');
                if (!coverContent) return 'no_cover_area';
                const empty = coverContent.querySelector('.cover-empty');
                if (empty) return 'empty';  // 封面为空，需要上传
                const img = coverContent.querySelector('img');
                if (img && img.src && !img.src.includes('data:')) return 'has_cover';
                return 'unknown';
            }""")

            if cover_ready in ('has_cover', 'unknown', 'no_cover_area'):
                bilibili_logger.info(_msg("🖼️", f"封面状态: {cover_ready}，跳过封面上传"))
                return

            bilibili_logger.info(_msg("🖼️", "封面为空，尝试上传封面..."))

            # 点击封面区域，弹出上传选项
            cover_clicked = False
            for click_sel in ['.cover-content', '.cover-empty', '.cover-main', 'text=封面设置']:
                try:
                    loc = page.locator(click_sel).first
                    if await loc.count() and await loc.is_visible():
                        await loc.click(timeout=5000)
                        cover_clicked = True
                        bilibili_logger.info(_msg("🖼️", f"点击了封面上传区域: {click_sel}"))
                        break
                except Exception:
                    continue

            if not cover_clicked:
                bilibili_logger.warning(_msg("⚠️", "未找到封面上传区域，跳过"))
                return

            await asyncio.sleep(2)

            # 检查弹出的面板，找"本地上传"按钮
            # B站封面上传面板可能包含：本地上传、视频截图、在线图库
            local_upload_clicked = False
            for attempt in range(3):
                try:
                    # 方式1: 查找"本地上传"按钮
                    for text in ['本地上传', '上传图片', '本地上传图片', '从本地上传']:
                        loc = page.locator(f'text={text}').first
                        if await loc.count() and await loc.is_visible():
                            await loc.click(timeout=3000)
                            local_upload_clicked = True
                            bilibili_logger.info(_msg("🖼️", f"点击了: {text}"))
                            break
                    if local_upload_clicked:
                        break

                    # 方式2: 直接检查是否有 file_chooser（某些情况下点击封面直接弹出文件选择）
                    async with page.expect_file_chooser(timeout=3000) as fc_info:
                        # 再次点击封面区域
                        await page.locator('.cover-content').first.click()
                    cover_fc = await fc_info.value
                    await cover_fc.set_files(self.file_path)
                    local_upload_clicked = True
                    bilibili_logger.info(_msg("🖼️", "通过 file_chooser 直接上传封面"))
                    break
                except Exception:
                    await asyncio.sleep(1)

            if not local_upload_clicked:
                bilibili_logger.warning(_msg("⚠️", "未找到本地上传入口，尝试 JS 触发 file input"))
                # 兜底: 尝试找到封面上传相关的 file input
                try:
                    cover_uploaded = await page.evaluate("""() => {
                        // 查找页面上所有隐藏的 file input，触发 accept 包含图片类型的那个
                        const fileInputs = document.querySelectorAll('input[type="file"]');
                        for (const fi of fileInputs) {
                            const accept = (fi.accept || '').toLowerCase();
                            if (accept.includes('image') || accept.includes('jpg') || accept.includes('png') || accept.includes('jpeg')) {
                                fi.click();
                                return true;
                            }
                        }
                        // 如果没找到图片 file input，尝试点击封面区域内部的上传按钮
                        const coverContent = document.querySelector('.cover-content');
                        if (coverContent) {
                            const btns = coverContent.querySelectorAll('div, span, button, a');
                            for (const btn of btns) {
                                if (btn.offsetWidth > 0 && btn.offsetHeight > 0) {
                                    btn.click();
                                    return 'clicked_inner';
                                }
                            }
                        }
                        return false;
                    }""")

                    if cover_uploaded:
                        bilibili_logger.info(_msg("🖼️", f"JS 触发封面上传: {cover_uploaded}"))
                        # 尝试接收 file_chooser
                        try:
                            async with page.expect_file_chooser(timeout=5000) as fc_info:
                                pass
                            cover_fc = await fc_info.value
                            # 用视频文件本身（B站会截取第一帧）或尝试找图片
                            await cover_fc.set_files(self.file_path)
                            bilibili_logger.info(_msg("🖼️", "封面文件已通过 file_chooser 上传"))
                        except Exception:
                            bilibili_logger.warning(_msg("⚠️", "file_chooser 未触发，封面可能已通过其他方式上传"))
                except Exception as e:
                    bilibili_logger.warning(_msg("⚠️", f"JS 触发封面失败: {e}"))

            await asyncio.sleep(3)

            # 检查封面是否上传成功
            cover_status = await page.evaluate("""() => {
                const coverContent = document.querySelector('.cover-content');
                if (!coverContent) return 'no_cover_area';
                const empty = coverContent.querySelector('.cover-empty');
                if (empty) return 'still_empty';
                const img = coverContent.querySelector('img');
                if (img && img.src) return 'uploaded';
                return 'unknown';
            }""")
            bilibili_logger.info(_msg("🖼️", f"封面上传后状态: {cover_status}"))

            if cover_status == 'still_empty':
                bilibili_logger.warning(_msg("⚠️", "封面仍为空，B站可能需要手动截取视频帧。尝试使用 opencv 截取..."))
                # 尝试用 opencv 从视频截取第一帧作为封面
                try:
                    import cv2
                    import numpy as np
                    import tempfile
                    video_path = self.file_path
                    if Path(video_path).suffix.lower() in ('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm'):
                        cap = cv2.VideoCapture(str(video_path))
                        ret, frame = cap.read()
                        cap.release()
                        if ret:
                            cover_path = str(Path(tempfile.gettempdir()) / "bili_cover.jpg")
                            cv2.imwrite(cover_path, frame)
                            bilibili_logger.info(_msg("🖼️", f"已截取视频帧: {cover_path}"))

                            # 尝试上传截取的封面
                            for attempt in range(3):
                                try:
                                    async with page.expect_file_chooser(timeout=5000) as fc_info:
                                        await page.locator('.cover-content').first.click()
                                    cover_fc = await fc_info.value
                                    await cover_fc.set_files(cover_path)
                                    bilibili_logger.info(_msg("✅", "视频帧封面已上传"))
                                    break
                                except Exception as e:
                                    bilibili_logger.warning(_msg("⚠️", f"封面上传尝试 {attempt+1} 失败: {e}"))
                                    await asyncio.sleep(1)
                except ImportError:
                    bilibili_logger.warning(_msg("⚠️", "opencv 未安装，无法截取视频帧作为封面"))
                except Exception as e:
                    bilibili_logger.warning(_msg("⚠️", f"截取视频帧失败: {e}"))

        except Exception as e:
            bilibili_logger.warning(_msg("⚠️", f"封面上传流程异常: {e}"))

    async def _fill_title(self, page: Page, title: str):
        """填写标题（B站上传页的标题框在上传完成后才出现）"""
        # 增加更多选择器，适配B站新版上传页
        title_input = await _find_first_visible(page, [
            'input[placeholder*="标题"]',
            '[class*="title"] input[type="text"]',
            '.video-title input',
            'input[maxlength]',
            '#video-title',
            'textarea[placeholder*="标题"]',
            '[class*="title"] [contenteditable="true"]',
            '[class*="title"] textarea',
            '.public-title input',
            '[class*="edit-title"] input',
        ], timeout_ms=30000)  # 增加到30秒等待，因为标题框在上传后才出现

        if title_input:
            await title_input.click()
            await asyncio.sleep(0.3)
            await page.keyboard.press("Control+KeyA")
            await page.keyboard.press("Backspace")
            await page.keyboard.type(title[:80])  # B站标题限制80字
            bilibili_logger.info(_msg("✍️", f"标题已填好: {title[:80]}"))
        else:
            # 诊断：输出页面上所有可编辑元素
            bilibili_logger.warning(_msg("⚠️", "找不到标题输入框，诊断页面元素..."))
            try:
                editable_els = await page.evaluate("""() => {
                    const els = document.querySelectorAll('input[type="text"], textarea, [contenteditable="true"]');
                    return Array.from(els).slice(0, 10).map(el => ({
                        tag: el.tagName, type: el.type||'', placeholder: el.placeholder||'',
                        id: el.id||'', cls: (el.className||'').toString().substring(0,60),
                    }));
                }""")
                bilibili_logger.info(_msg("🔍", f"可编辑元素: {editable_els}"))
            except Exception:
                pass
            bilibili_logger.warning(_msg("😵", "找不到标题输入框，尝试 Tab 键"))
            await page.keyboard.press("Tab")
            await page.keyboard.type(title[:80])

    async def _fill_desc(self, page: Page, desc: str):
        """填写简介/描述"""
        desc_editor = await _find_first_visible(page, [
            '[editor_id="desc_at_editor"]',
            '[class*="desc"] textarea',
            '[class*="desc"] [contenteditable="true"]',
            'textarea[placeholder*="简介"]',
            '[class*="video-desc"] textarea',
            '[class*="description"] textarea',
            '.ql-editor',
            '[class*="desc"] input[type="text"]',
            '[class*="abstract"] textarea',
            '[class*="intro"] textarea',
        ], timeout_ms=10000)

        if desc_editor:
            tag_name = await desc_editor.evaluate("el => el.tagName.toLowerCase()")
            await desc_editor.click()
            await asyncio.sleep(0.3)
            if tag_name == "textarea":
                await desc_editor.fill(desc)
            else:
                await page.keyboard.press("Control+KeyA")
                await page.keyboard.press("Delete")
                await page.keyboard.type(desc)
            bilibili_logger.info(_msg("📝", f"简介已填好（{len(desc)} 字）"))
        else:
            bilibili_logger.warning(_msg("😵", "找不到简介编辑器，跳过"))

    async def _fill_tags(self, page: Page, tags: list[str]):
        """填写标签"""
        tag_input = await _find_first_visible(page, [
            'input[placeholder*="回车"]',
            'input[placeholder*="标签"]',
            'input[placeholder*="Enter"]',
            '[class*="tag"] input',
        ], timeout_ms=10000)

        if not tag_input:
            bilibili_logger.warning(_msg("😵", "找不到标签输入框，跳过标签"))
            return

        for tag in tags[:10]:  # B站最多10个标签
            await tag_input.click()
            await asyncio.sleep(0.2)
            await page.keyboard.type(tag)
            await page.keyboard.press("Enter")
            await asyncio.sleep(0.5)
            bilibili_logger.info(_msg("🏷️", f"标签已添加: {tag}"))

    async def _select_zone(self, page: Page, tid: int):
        """选择分区

        B站投稿页分区选择器的 DOM 结构：
            <div class="form-item">
              <label>*分区</label>
              <div class="select-container">
                <div class="select-controller">
                  <p class="select-item-cont">动画</p>  ← 当前值
                </div>
              </div>
            </div>
        点击 .select-item-cont 展开下拉列表，然后选择分区。
        tid 是分区 ID。
        """
        try:
            # 滚动到分区区域
            try:
                await page.evaluate("""() => {
                    const formItems = document.querySelectorAll('.form-item');
                    for (const item of formItems) {
                        const label = item.querySelector('label, [class*="label"], h3, .section-title-content-main');
                        if (label && (label.textContent || '').includes('分区')) {
                            item.scrollIntoView({ block: 'center' });
                            break;
                        }
                    }
                }""")
                await asyncio.sleep(0.5)
            except Exception:
                pass

            # 点击分区选择器（.select-item-cont 是显示当前值的元素）
            zone_selector = await _find_first_visible(page, [
                '.select-item-cont',
                '.select-controller',
                '.select-container',
            ], timeout_ms=5000)

            if zone_selector:
                await zone_selector.click()
                await asyncio.sleep(1.5)
                bilibili_logger.info(_msg("📂", f"已点击分区选择器（tid={tid}）"))

                # B站分区是级联选择（主分区→子分区），通过 API 获取分区数据更可靠
                # 这里先尝试通过下拉列表点击
                tid_names = {
                    21: "科学科普", 24: "单机游戏", 95: "手机", 122: "野生技术协会",
                    75: "综合", 136: "音MAD", 138: "搞笑", 25: "Mugen",
                    27: "综合", 28: "原创音乐", 29: "三次元音乐", 30: "VOCALOID",
                    31: "翻唱", 59: "演奏", 130: "舞蹈", 154: "三次元舞蹈",
                    156: "舞蹈教程", 32: "完结动画", 33: "连载动画", 34: "资讯",
                    36: "短剧", 82: "日记", 128: "手工", 167: "国创",
                    # 主分区
                    1: "番剧", 13: "动画", 3: "音乐", 129: "舞蹈",
                    4: "游戏", 36: "知识", 188: "科技", 95: "生活",
                    21: "美食", 119: "动物圈", 22: "鬼畜", 26: "时尚",
                    23: "娱乐", 19: "影视", 217: "汽车", 181: "运动",
                }
                target_name = tid_names.get(tid, "")

                clicked = False
                if target_name:
                    # 等待下拉渲染
                    await asyncio.sleep(1)

                    # 通过 JS 在下拉列表中查找并点击分区选项
                    # B站下拉列表 DOM 可能是 .bcc-cascader-panel / .el-cascader-panel 等
                    for attempt in range(3):
                        js_result = await page.evaluate(f"""(targetName) => {{
                            // 查找所有可见的下拉面板
                            const panels = document.querySelectorAll(
                                '.bcc-cascader-panel, .el-cascader-panel, ' +
                                '[class*="cascader"], [class*="dropdown-menu"], ' +
                                '[class*="select-dropdown"], [class*="picker-dropdown"]'
                            );
                            
                            for (const panel of panels) {{
                                if (panel.offsetWidth === 0) continue;
                                
                                // 在面板中查找目标文字
                                const items = panel.querySelectorAll('li, [class*="item"], [class*="option"], span, div');
                                for (const item of items) {{
                                    const text = (item.textContent || '').trim();
                                    // 精确匹配或以目标名称开头
                                    if (text === targetName || text.startsWith(targetName + ' ')) {{
                                        // 检查是否可见
                                        if (item.offsetWidth > 0 && item.offsetHeight > 0) {{
                                            // 触发 Vue 事件
                                            const events = ['mouseover', 'mousedown', 'mouseup', 'click'];
                                            for (const type of events) {{
                                                item.dispatchEvent(new MouseEvent(type, {{bubbles: true, cancelable: true, view: window}}));
                                            }}
                                            return 'clicked: ' + text;
                                        }}
                                    }}
                                }}
                            }}
                            
                            // 也检查页面所有可见元素中的分区文字
                            const allEls = document.querySelectorAll('li, [class*="menu-item"], [class*="option"]');
                            for (const el of allEls) {{
                                const text = (el.textContent || '').trim();
                                if (text === targetName && el.offsetWidth > 0 && el.offsetHeight > 0) {{
                                    el.click();
                                    return 'fallback_click: ' + text;
                                }}
                            }}
                            
                            return null;
                        }}""", target_name)
                        
                        if js_result:
                            bilibili_logger.info(_msg("📂", f"JS 选择分区: {js_result}"))
                            clicked = True
                            break
                        await asyncio.sleep(0.5)

                if not clicked:
                    bilibili_logger.warning(_msg("⚠️", f"未找到分区选项 '{target_name}'（tid={tid}），使用默认分区"))
                    # 按 Escape 关闭可能打开的下拉
                    await page.keyboard.press("Escape")
                    await asyncio.sleep(0.5)

                await asyncio.sleep(1)
            else:
                bilibili_logger.info(_msg("📂", "未找到分区选择器，使用默认分区"))

        except Exception as e:
            bilibili_logger.warning(_msg("⚠️", f"分区选择失败: {e}，使用默认分区"))

    async def _set_copyright(self, page: Page, copyright_type: int = 2):
        """设置版权类型：1=原创，2=转载

        注意：B站要求转载视频必须填写转载来源，否则投稿按钮点击后会校验失败
        """
        try:
            if copyright_type == 2:
                # 点击"转载"单选框
                reprint_radio = page.locator('text=转载').first
                if await reprint_radio.count() and await reprint_radio.is_visible():
                    await reprint_radio.click()
                    bilibili_logger.info(_msg("📋", "已选择转载类型"))
                    await asyncio.sleep(1)

                    # 填写转载来源（必填项，否则无法投稿）
                    source_input = await _find_first_visible(page, [
                        'input[placeholder*="转载来源"]',
                        'input[placeholder*="来源"]',
                        'input[placeholder*="Source"]',
                        '[class*="reprint"] input',
                        '[class*="source"] input[type="text"]',
                        '[class*="copyright"] input[type="text"]',
                    ], timeout_ms=5000)

                    if source_input:
                        await source_input.click()
                        await asyncio.sleep(0.3)
                        await page.keyboard.press("Control+KeyA")
                        await page.keyboard.press("Backspace")
                        await page.keyboard.type("网络转载")
                        bilibili_logger.info(_msg("📋", "已填写转载来源: 网络转载"))
                    else:
                        bilibili_logger.warning(_msg("⚠️", "找不到转载来源输入框，可能需要手动填写"))
        except Exception as e:
            bilibili_logger.warning(_msg("⚠️", f"设置版权类型失败: {e}"))

    async def _click_publish(self, page: Page) -> bool:
        """点击发布/投稿按钮（只点一次，然后等待结果）

        Returns:
            True: 发布成功
            False: 发布失败或超时（按钮已点击，不应重试整个流程）

        Raises:
            RuntimeError: 找不到投稿按钮或无法点击（可重试）
        """
        # ── 第一步：滚动到页面底部，确保投稿按钮可见 ──
        # B站上传页的投稿按钮在页面底部，需要滚动才能看到
        bilibili_logger.info(_msg("📜", "滚动到页面底部，寻找投稿按钮..."))
        try:
            await page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)
        except Exception:
            pass

        # 也尝试滚动所有可能的滚动容器
        try:
            await page.evaluate("""() => {
                // B站上传页可能有多个滚动容器
                const containers = document.querySelectorAll(
                    '.upload-wrapper, [class*="scroll"], [class*="content"], main, .main'
                );
                for (const c of containers) {
                    c.scrollTop = c.scrollHeight;
                }
            }""")
            await asyncio.sleep(0.5)
        except Exception:
            pass

        # ── 第二步：找到并点击投稿按钮（只点一次）──
        # 重要：B站投稿按钮是 <span class="submit-add">立即投稿</span>，不是 <button>！
        # 需要先滚动到页面底部使其可见
        bilibili_logger.info(_msg("📤", "寻找投稿按钮..."))
        
        # 先滚动到投稿按钮区域（submit-container 在页面底部）
        try:
            await page.evaluate("""() => {
                // 滚动上传表单容器到底部
                const containers = [
                    '.york_videoup_wrapper', '.upload-wrap', '.cc-body', '#root',
                ];
                for (const sel of containers) {
                    const el = document.querySelector(sel);
                    if (el && el.scrollHeight > el.clientHeight) {
                        el.scrollTop = el.scrollHeight;
                    }
                }
                // 也直接滚动投稿按钮到可见区域
                const submitArea = document.querySelector('.submit-container, .submit-add');
                if (submitArea) submitArea.scrollIntoView({behavior: 'instant', block: 'center'});
            }""")
            await asyncio.sleep(1)
        except Exception:
            pass

        publish_btn = await _find_first_visible(page, [
            # B站实际投稿按钮：<span class="submit-add">立即投稿</span>
            'span.submit-add',
            '.submit-add',
            # 也兼容 button 形式（旧版/可能的变体）
            'button.submit-add',
            'button.bcc-button--primary:not(.small):not(.add)',
            # Playwright 选择器
            'span:has-text("立即投稿")',
            'span:has-text("投稿")',
            # 通用选择器
            '[class*="submit"] span',
            '[class*="submit"] button',
            '.btn-submit',
            '.submit-btn',
        ], timeout_ms=15000)

        if not publish_btn:
            # 诊断：列出页面上所有按钮（包括不可见的），帮助排查
            bilibili_logger.error(_msg("😵", "找不到投稿按钮，诊断页面上所有可点击元素..."))
            try:
                all_btns = await page.evaluate("""() => {
                    const btns = document.querySelectorAll('button, span[class*="submit"], span[class*="btn"], a[class*="btn"], [role="button"]');
                    return Array.from(btns).slice(0, 20).map(b => ({
                        tag: b.tagName,
                        text: (b.textContent || '').trim().substring(0, 30),
                        cls: (b.className || '').toString().substring(0, 100),
                        visible: b.offsetWidth > 0 && b.offsetHeight > 0,
                        disabled: b.disabled || false,
                    }));
                }""")
                bilibili_logger.info(_msg("🔍", f"所有按钮列表（含不可见）: {all_btns}"))
            except Exception as diag_err:
                bilibili_logger.warning(_msg("⚠️", f"诊断按钮列表失败: {diag_err}"))
            # 截图保存
            try:
                screenshot_path = Path(self.file_path).parent / "bili_no_publish_btn.png"
                await page.screenshot(full_page=True, path=str(screenshot_path))
                bilibili_logger.info(_msg("📸", f"诊断截图: {screenshot_path}"))
            except Exception:
                pass

            # 尝试通过 JS 直接查找并点击投稿按钮（绕过 Playwright 选择器限制）
            bilibili_logger.info(_msg("🔄", "尝试通过 JS 直接查找投稿按钮..."))
            try:
                js_clicked = await page.evaluate("""() => {
                    // B站投稿按钮是 <span class="submit-add">立即投稿</span>
                    const submitAdd = document.querySelector('span.submit-add, .submit-add');
                    if (submitAdd && submitAdd.offsetWidth > 0) {
                        submitAdd.scrollIntoView({behavior: 'instant', block: 'center'});
                        submitAdd.click();
                        return 'submit-add: ' + (submitAdd.textContent || '').trim();
                    }
                    // 也搜索 span 元素
                    const spans = document.querySelectorAll('span');
                    for (const span of spans) {
                        const text = (span.textContent || '').trim();
                        if (text === '立即投稿' || text === '投稿') {
                            span.scrollIntoView({behavior: 'instant', block: 'center'});
                            span.click();
                            return 'span: ' + text;
                        }
                    }
                    // 搜索 button 元素（兼容旧版）
                    const btns = document.querySelectorAll('button');
                    for (const btn of btns) {
                        const text = (btn.textContent || '').trim();
                        if (text === '投稿' || text === '立即投稿' || text.includes('投稿')) {
                            btn.scrollIntoView({behavior: 'instant', block: 'center'});
                            btn.click();
                            return text;
                        }
                    }
                    // 也尝试 bcc-button primary
                    const primaryBtns = document.querySelectorAll('button.bcc-button--primary');
                    for (const btn of primaryBtns) {
                        if (!btn.classList.contains('small') && !btn.classList.contains('add')) {
                            btn.click();
                            return 'bcc-button--primary: ' + (btn.textContent || '').trim();
                        }
                    }
                    return null;
                }""")
                if js_clicked:
                    bilibili_logger.info(_msg("✅", f"JS 直接点击投稿按钮成功: {js_clicked}"))
                    # JS 已点击，跳过 Playwright 点击步骤
                    publish_btn = None  # 标记：已通过 JS 点击，不需要 Playwright 再点击
                else:
                    raise RuntimeError("找不到投稿按钮（页面可能未完全加载或选择器需更新）")
            except RuntimeError:
                raise
            except Exception as js_err:
                raise RuntimeError(f"找不到投稿按钮（JS 查找也失败: {js_err}）")

        # Playwright 点击（仅在通过 _find_first_visible 找到按钮时执行）
        if publish_btn:
            # 先确保按钮在视口内（B站投稿按钮在页面底部，可能需要滚动）
            try:
                await publish_btn.evaluate("el => el.scrollIntoView({behavior: 'instant', block: 'center'})")
                await asyncio.sleep(0.5)
            except Exception:
                pass

            # 尝试 Playwright 点击（先 force=True 避免视口/遮挡检查失败）
            try:
                await publish_btn.click(force=True, timeout=10000)
                bilibili_logger.info(_msg("📤", "已点击投稿按钮 (Playwright force)"))
            except Exception as click_err:
                bilibili_logger.warning(_msg("⚠️", f"Playwright 点击失败，尝试 dispatchEvent: {click_err}"))
                try:
                    # 使用 dispatchEvent 触发 Vue 事件绑定（el.click() 对 Vue 无效）
                    clicked = await page.evaluate("""() => {
                        const btn = document.querySelector('span.submit-add, .submit-add');
                        if (!btn) return null;
                        btn.scrollIntoView({behavior: 'instant', block: 'center'});
                        // 完整的鼠标事件链，触发 Vue @click 处理
                        const events = ['mouseover', 'mousedown', 'mouseup', 'click'];
                        for (const type of events) {
                            btn.dispatchEvent(new MouseEvent(type, {
                                bubbles: true, cancelable: true, view: window,
                            }));
                        }
                        return btn.textContent;
                    }""")
                    if clicked:
                        bilibili_logger.info(_msg("📤", f"dispatchEvent 点击投稿按钮成功: {clicked}"))
                    else:
                        raise RuntimeError("dispatchEvent 未找到按钮")
                except Exception as js_err:
                    bilibili_logger.error(_msg("😵", f"所有点击方式均失败: {js_err}"))
                    raise RuntimeError(f"投稿按钮无法点击: {js_err}")

        # ── 第二步：等待发布结果（最多 90 秒）──
        # 先等待几秒让页面响应，同时自动处理可能弹出的确认对话框
        bilibili_logger.info(_msg("⏳", "已点击投稿，等待页面响应..."))
        await asyncio.sleep(3)

        # 尝试自动处理确认/二次确认弹窗
        try:
            dialog_handled = await page.evaluate("""() => {
                // 查找所有可能的确认按钮（注意：不能使用 :has-text() 伪选择器，
                // 那是 Playwright 扩展的，浏览器原生 querySelectorAll 不支持）
                const confirmBtns = document.querySelectorAll(
                    'button[class*="confirm"], button[class*="Confirm"], ' +
                    '[class*="dialog"] button[class*="primary"], [class*="modal"] button[class*="primary"], ' +
                    '.bcc-dialog__button--primary, [class*="popup"] button:last-child'
                );
                // 额外通过文本匹配寻找按钮
                const allBtns = document.querySelectorAll('button');
                const confirmTexts = ['确定', '确认', '知道了', '好的', 'OK', '继续'];
                for (const btn of allBtns) {
                    const text = (btn.textContent || '').trim();
                    if (confirmTexts.includes(text)) {
                        // 模拟 confirmBtns 的行为
                        if (btn.offsetWidth > 0 && btn.offsetHeight > 0) {
                            btn.click();
                            return text;
                        }
                    }
                }
                let clicked = null;
                for (const btn of confirmBtns) {
                    if (btn.offsetWidth > 0 && btn.offsetHeight > 0) {
                        const text = (btn.textContent || '').trim();
                        btn.click();
                        clicked = text || 'confirm-btn';
                        break; // 只点第一个可见的
                    }
                }
                return clicked;
            }""")
            if dialog_handled:
                bilibili_logger.info(_msg("✅", f"自动点击了确认弹窗按钮: {dialog_handled}"))
            else:
                bilibili_logger.debug(_msg("🧍", "未发现确认弹窗（正常，可能直接进入发布流程）"))
        except Exception as dialog_err:
            bilibili_logger.debug(_msg("🧍", f"检查确认弹窗时出错: {dialog_err}"))

        # 发布成功后的可能表现：
        # 1. 页面跳转（离开上传页）
        # 2. 弹出成功提示（toast / dialog / bcc-message）
        # 3. 表单被清空/重置（B站上传成功后会清空表单）
        # 4. 投稿按钮消失或禁用
        # 5. 出现"再次投稿"/"继续投稿"按钮
        # 6. 弹窗/对话框中包含成功信息（bcc-dialog / modal）
        # 7. 页面出现"审核中"/"稿件已提交"/"发布成功"等文字
        max_wait_seconds = 90
        consecutive_browser_failures = 0
        no_change_count = 0  # 连续无变化计数（用于提前退出）
        last_body_text = ""

        for wait_sec in range(max_wait_seconds):
            # 浏览器存活检测（容错）
            if not await _check_browser_alive(page):
                consecutive_browser_failures += 1
                if consecutive_browser_failures >= 5:
                    raise RuntimeError("浏览器在发布过程中意外断开（连续5次检测失败）")
                bilibili_logger.warning(_msg("⚠️", f"发布等待中浏览器检测失败 {consecutive_browser_failures}/5"))
                await asyncio.sleep(2)
                continue
            else:
                consecutive_browser_failures = 0

            try:
                result = await page.evaluate("""() => {
                    const bodyText = document.body.innerText || '';

                    // ═══ 1. 检查成功提示（toast / bcc 组件提示 / 全局弹层）═══
                    const toastSelectors = [
                        '[class*="toast"]', '[class*="Toast"]', '[class*="message"]', '[class*="Message"]',
                        '[class*="notice"]', '[class*="Notice"]', '.bcc-message', '.bcc-toast',
                        '[class*="tips"]', '[class*="alert"]', '[class*="notification"]',
                        '[class*="dialog"]', '[class*="Dialog"]', '[class*="modal"]', '[class*="Modal"]',
                        '[class*="popup"]', '[class*="Popup"]', '[class*="result"]',
                        '.bcc-dialog__body', '[class*="confirm"]', '[class*="prompt"]'
                    ];
                    const toastEls = document.querySelectorAll(toastSelectors.join(', '));
                    for (const t of toastEls) {
                        const text = (t.innerText || '').trim();
                        if (!text) continue;
                        // 成功关键词（更全面的匹配）
                        const successKeywords = ['投稿成功', '发布成功', '提交成功', '稿件投递成功',
                            '上传成功', '发表成功', '已发布', '已投稿', '已提交',
                            '成功发布', '成功投稿', '成功提交'];
                        for (const kw of successKeywords) {
                            if (text.includes(kw)) {
                                return { success: true, reason: 'toast: ' + text.substring(0, 60) };
                            }
                        }
                    }

                    // ═══ 2. 检查页面正文中的成功文字 ═══
                    // 有时成功信息不在特定容器中，而是直接出现在页面某处
                    const pageSuccessKw = ['投稿成功', '发布成功', '稿件投递成功', '上传成功',
                        '您的稿件', '稿件已提交', '已进入审核', '正在审核',
                        '视频已发布', '视频已投稿', '发布任务创建成功',
                        '定时发布成功', '预约发布成功'];
                    for (const kw of pageSuccessKw) {
                        if (bodyText.includes(kw)) {
                            // 排除 placeholder 和隐藏元素中的误判
                            const visibleCheck = bodyText.indexOf(kw);
                            return { success: true, reason: 'page_text: ' + kw };
                        }
                    }

                    // ═══ 3. 检查明确的错误提示 ═══
                    const errorKeywords = ['操作频繁', '账号异常', '验证码', '参数错误',
                        '请填写', '请选择', '不能为空', '请输入转载来源',
                        '稿件投递失败', '投稿失败', '发布失败', '提交失败',
                        '网络错误', '服务器错误', '系统繁忙', '请求超时',
                        '请先上传封面', '请上传封面', '不支持', '格式错误',
                        '请输入标题', '标题不能为空', '标签不能为空'];
                    for (const kw of errorKeywords) {
                        if (bodyText.includes(kw)) {
                            // 排除 "不能为空" 出现在 placeholder 中的情况
                            const inputs = document.querySelectorAll('input, textarea');
                            let inPlaceholder = false;
                            for (const inp of inputs) {
                                if ((inp.placeholder || '').includes(kw)) { inPlaceholder = true; break; }
                            }
                            if (!inPlaceholder) {
                                return { success: false, reason: 'error: ' + kw };
                            }
                        }
                    }

                    // ═══ 4. 检查表单是否被清空（B站发布成功后会重置表单）═══
                    const titleInput = document.querySelector(
                        'input[placeholder*="标题"], [class*="title"] input[type="text"]'
                    );
                    const hasUploadArea = document.querySelector(
                        '.bcc-upload-wrapper, [class*="upload-add"], [class*="upload-btn"], [class*="re-upload"]'
                    );
                    if (titleInput && titleInput.value === '' && hasUploadArea) {
                        return { success: true, reason: 'form_reset' };
                    }

                    // ═══ 5. 检查投稿按钮状态 ═══
                    const submitBtns = document.querySelectorAll(
                        'button.submit-add, button[class*="submit"], button.bcc-button--primary'
                    );
                    let foundSubmitBtn = false;
                    let allGoneOrDisabled = true;
                    for (const btn of submitBtns) {
                        const text = (btn.textContent || '').trim();
                        if (!text.includes('投稿') && !text.includes('提交') && !text.includes('发布')) continue;
                        if (text.includes('添加') || text.includes('分P')) continue;
                        foundSubmitBtn = true;
                        if (btn.offsetWidth > 0 && btn.offsetHeight > 0 && !btn.disabled) {
                            allGoneOrDisabled = false;
                            break;
                        }
                    }
                    if (foundSubmitBtn && allGoneOrDisabled) {
                        return { success: true, reason: 'submit_btn_gone_or_disabled' };
                    }

                    // ═══ 6. 检查"再次投稿"/"继续投稿"按钮 ═══
                    const allLinks = document.querySelectorAll('a, button, span, div');
                    for (const el of allLinks) {
                        const text = (el.textContent || '').trim();
                        if (text === '再次投稿' || text === '继续投稿' || text === '再投一个'
                            || text === '发布下一个' || text === '继续发布') {
                            return { success: true, reason: 'again_btn: ' + text };
                        }
                    }

                    // ═══ 7. 检查是否出现弹窗遮罩层（可能包含成功信息）═══
                    const overlay = document.querySelector('[class*="mask"], [class*="overlay"], [class*="backdrop"]');
                    if (overlay && overlay.offsetWidth > 0) {
                        // 有遮罩层，说明有弹窗，提取弹窗内容
                        const dialogs = document.querySelectorAll('[class*="dialog"], [class*="modal"], [class*="popup"], [role="dialog"]');
                        for (const d of dialogs) {
                            const dt = (d.innerText || '').trim();
                            if (dt) {
                                // 先排除已知的非成功弹窗
                                const excludeKw = ['批量操作', '批量填充', '队列信息', '分P', '多P'];
                                let excluded = false;
                                for (const exkw of excludeKw) {
                                    if (dt.includes(exkw)) { excluded = true; break; }
                                }
                                if (excluded) continue;

                                // 判断弹窗内容是否明确表示发布成功（必须非常精确，不能用"确定"等宽泛词）
                                const diagSuccessKw = ['投稿成功', '发布成功', '提交成功', '稿件投递成功',
                                    '稿件已提交', '已进入审核', '视频已发布', '视频已投稿',
                                    '发表成功', '上传成功'];
                                for (const skw of diagSuccessKw) {
                                    if (dt.includes(skw)) {
                                        return { success: true, reason: 'dialog: ' + dt.substring(0, 50) };
                                    }
                                }
                                const diagErrorKw = ['失败', '错误', '不能', '请填写', '请选择', '验证码',
                                    '操作频繁', '账号异常', '参数错误', '稿件投递失败'];
                                for (const ekw of diagErrorKw) {
                                    if (dt.includes(ekw)) {
                                        return { success: false, reason: 'dialog_error: ' + dt.substring(0, 50) };
                                    }
                                }
                            }
                        }
                    }

                    // 返回页面文本摘要（用于判断是否有变化）
                    return { success: null, reason: '', bodySnippet: bodyText.substring(0, 200) };
                }""")

                if result.get("success") is True:
                    bilibili_logger.success(_msg("🥳", f"发布成功! ({result.get('reason', '')})"))
                    return True

                if result.get("success") is False:
                    bilibili_logger.error(_msg("😵", f"发布失败: {result.get('reason', '')}"))
                    return False

                # success=None → 还没出结果
                # 先尝试关闭干扰弹窗（二创计划、批量操作等）
                # 重要：B站弹窗使用 Vue 事件绑定，JS click() 无法触发，必须用 Playwright 真实点击
                # 二创计划弹窗需要先勾选协议复选框，再点"同意"
                try:
                    dialog_closed = False

                    # 步骤0: 如果弹窗中有协议复选框，先勾选它
                    try:
                        checkbox = page.locator('[class*="dialog"] input[type="checkbox"], [class*="modal"] input[type="checkbox"], .bcc-dialog input[type="checkbox"]').first
                        if await checkbox.count() and await checkbox.is_visible():
                            checked = await checkbox.is_checked()
                            if not checked:
                                await checkbox.check(timeout=3000)
                                bilibili_logger.info(_msg("🧹", "勾选了弹窗中的协议复选框"))
                                await asyncio.sleep(0.5)
                    except Exception:
                        pass

                    # 方法1: 等待弹窗按钮出现并用 Playwright 点击
                    # 二创计划弹窗有 "同意" 按钮 (button.bcc-button--primary)
                    try:
                        agree_btn = page.locator('button.bcc-button--primary:has-text("同意")').first
                        await agree_btn.wait_for(state="visible", timeout=3000)
                        if await agree_btn.is_visible():
                            await agree_btn.click(timeout=5000)
                            bilibili_logger.info(_msg("🧹", "Playwright 点击了「同意」按钮关闭二创计划弹窗"))
                            dialog_closed = True
                            await asyncio.sleep(1)
                    except Exception:
                        pass  # 按钮不可见或不存在

                    # 方法2: 用 CDP Runtime.evaluate 直接触发 Vue 的 click 事件
                    if not dialog_closed:
                        try:
                            # 通过 CDP 执行真正的用户点击，可以触发 Vue 事件
                            await page.evaluate("""() => {
                                const btns = document.querySelectorAll('button.bcc-button--primary');
                                for (const btn of btns) {
                                    const t = (btn.textContent || '').trim();
                                    if (t === '同意' || t === '确定') {
                                        // 触发完整的事件链
                                        const events = ['mouseover', 'mousedown', 'mouseup', 'click'];
                                        for (const type of events) {
                                            btn.dispatchEvent(new MouseEvent(type, {bubbles: true, cancelable: true, view: window}));
                                        }
                                        return true;
                                    }
                                }
                                return false;
                            }""")
                            bilibili_logger.info(_msg("🧹", "通过 dispatchEvent 触发了弹窗按钮点击"))
                            await asyncio.sleep(1)
                        except Exception:
                            pass

                    # 方法3: Playwright 点击其他弹窗按钮
                    if not dialog_closed:
                        for text_sel in ['知道了', '确定', '确认', '关闭']:
                            try:
                                btn_loc = page.locator(f'button:has-text("{text_sel}")').first
                                if await btn_loc.count() and await btn_loc.is_visible():
                                    await btn_loc.click(timeout=3000)
                                    bilibili_logger.info(_msg("🧹", f"Playwright 点击弹窗按钮: {text_sel}"))
                                    dialog_closed = True
                                    await asyncio.sleep(1)
                                    break
                            except Exception:
                                continue

                    # 方法4: Playwright 点击弹窗关闭 X 按钮
                    if not dialog_closed:
                        for close_sel in [
                            '.bcc-dialog__close',
                            '[class*="dialog"] [class*="close"]',
                        ]:
                            try:
                                close_loc = page.locator(close_sel).first
                                if await close_loc.count() and await close_loc.is_visible():
                                    await close_loc.click(timeout=3000)
                                    bilibili_logger.info(_msg("🧹", f"Playwright 点击关闭按钮: {close_sel}"))
                                    dialog_closed = True
                                    await asyncio.sleep(1)
                                    break
                            except Exception:
                                continue

                    # 方法5: Playwright 按 Escape
                    if not dialog_closed:
                        try:
                            await page.keyboard.press("Escape")
                            bilibili_logger.info(_msg("🧹", "按 Escape 关闭弹窗"))
                            await asyncio.sleep(0.5)
                        except Exception:
                            pass

                except Exception as dismiss_err:
                    bilibili_logger.debug(_msg("🧍", f"关闭干扰弹窗时出错: {dismiss_err}"))

                # 检查页面是否有变化
                current_snippet = result.get("bodySnippet", "")
                if current_snippet == last_body_text and last_body_text:
                    no_change_count += 1
                    # 如果连续 15 秒（15次循环）页面完全没任何变化，大概率是卡了或已完成但我们没识别到
                    if no_change_count >= 15:
                        bilibili_logger.warning(_msg("⚠️", f"页面连续 {no_change_count} 秒无变化，做最终判定..."))
                        # 做一次最终综合判定：如果标题框为空或投稿按钮不可用，认为成功了
                        final_check = await page.evaluate("""() => {
                            // 先检查是否有弹窗遮挡（有弹窗时，投稿按钮可能被遮挡而非消失）
                            const overlays = document.querySelectorAll('[class*="mask"], [class*="overlay"], [class*="backdrop"]');
                            for (const ov of overlays) {
                                if (ov.offsetWidth > 0) {
                                    // 有弹窗遮挡，不能判定
                                    const dialog = ov.parentElement || ov.closest('[class*="dialog"], [class*="modal"], [class*="popup"]');
                                    if (dialog) {
                                        const dt = (dialog.innerText || '').trim();
                                        return 'blocked_by_dialog: ' + dt.substring(0, 60);
                                    }
                                    return 'blocked_by_overlay';
                                }
                            }

                            const titleInput = document.querySelector(
                                'input[placeholder*="标题"], [class*="title"] input[type="text"]'
                            );
                            const uploadArea = document.querySelector(
                                '.bcc-upload-wrapper, [class*="upload-add"], [class*="re-upload"]'
                            );
                            // 标题为空+有上传区域 = 表单重置 = 成功
                            if (titleInput && titleInput.value === '' && uploadArea) {
                                return 'form_reset_final';
                            }
                            // 检查是否有"再次投稿"
                            const allEls = document.querySelectorAll('a, button, span, div');
                            for (const el of allEls) {
                                const t = (el.textContent || '').trim();
                                if (t === '再次投稿' || t === '继续投稿' || t === '再投一个') {
                                    return 'again_btn';
                                }
                            }
                            // 检查投稿按钮是否还存在且可用
                            const btns = document.querySelectorAll('button');
                            for (const btn of btns) {
                                const t = (btn.textContent || '').trim();
                                if ((t === '投稿' || t === '立即投稿') && btn.offsetWidth > 0 && !btn.disabled) {
                                    return 'still_has_submit_btn';
                                }
                            }
                            // 投稿按钮消失了，且无弹窗遮挡 → 成功
                            return 'no_submit_btn_found';
                        }""")
                        if final_check in ('form_reset_final', 'again_btn', 'no_submit_btn_found'):
                            bilibili_logger.success(_msg("🥳", f"发布成功! (最终判定: {final_check})"))
                            return True
                        elif final_check == 'still_has_submit_btn':
                            bilibili_logger.warning(_msg("⚠️", "最终判定：投稿按钮仍存在且可用，可能未真正提交"))
                        elif final_check and final_check.startswith('blocked_by'):
                            bilibili_logger.warning(_msg("⚠️", f"最终判定：页面被弹窗遮挡 ({final_check})，尝试关闭弹窗后继续..."))
                            # 尝试关闭弹窗
                            try:
                                await page.evaluate("""() => {
                                    const dismissKw = ['二创计划', '批量操作', '加入计划', '邀请'];
                                    const dialogs = document.querySelectorAll(
                                        '[class*="dialog"], [class*="Dialog"], [class*="modal"], [class*="Modal"], ' +
                                        '[class*="popup"], [class*="Popup"], [role="dialog"], [class*="bcc-dialog"]'
                                    );
                                    for (const dlg of dialogs) {
                                        if (dlg.offsetWidth === 0 || dlg.offsetHeight === 0) continue;
                                        const dialogText = (dlg.innerText || '');
                                        let isDismissable = false;
                                        for (const kw of dismissKw) {
                                            if (dialogText.includes(kw)) { isDismissable = true; break; }
                                        }
                                        if (!isDismissable) continue;
                                        // 关闭按钮
                                        const closeBtns = dlg.querySelectorAll('button, [class*="close"], [role="button"], span[class*="icon"]');
                                        for (const btn of closeBtns) {
                                            const t = (btn.textContent || '').trim();
                                            const cls = (btn.className || '').toString();
                                            if (t === '取消' || t === '拒绝' || t === '不同意' || t === '暂不' || t === '关闭'
                                                || t === '稍后' || t === '暂不加入' || cls.includes('close')) {
                                                btn.click(); return;
                                            }
                                        }
                                    }
                                    // fallback: 点击遮罩
                                    const overlays = document.querySelectorAll('[class*="mask"], [class*="overlay"], [class*="backdrop"]');
                                    for (const ov of overlays) { if (ov.offsetWidth > 0) { ov.click(); break; } }
                                }""")
                                await asyncio.sleep(1)
                            except Exception:
                                pass
                            no_change_count = 0  # 重置，继续等待
                        # 否则继续等待
                else:
                    no_change_count = 0  # 页面有变化，重置计数
                last_body_text = current_snippet

                # 检查 URL 跳转
                current_url = page.url
                if "bilibili.com" in current_url and "upload" not in current_url:
                    bilibili_logger.success(_msg("🥳", f"已离开上传页面 ({current_url})"))
                    return True

            except Exception as e:
                bilibili_logger.debug(_msg("🧍", f"检测发布状态时出错: {e}"))

            # 每 10 秒输出一次诊断信息
            if wait_sec > 0 and wait_sec % 10 == 0:
                try:
                    diag = await page.evaluate("""() => {
                        const btns = document.querySelectorAll('button');
                        const visibleBtns = Array.from(btns).filter(b => b.offsetWidth > 0).map(b => ({
                            t: (b.textContent || '').trim().substring(0, 20),
                            d: b.disabled,
                            c: (b.className || '').toString().substring(0, 60),
                        }));
                        const toasts = document.querySelectorAll('[class*="toast"], [class*="message"], [class*="tips"], [class*="notice"], .bcc-message, .bcc-toast, [class*="dialog"], [class*="modal"]');
                        const toastTexts = Array.from(toasts).map(t => (t.innerText || '').trim().substring(0, 50)).filter(Boolean);
                        const overlays = document.querySelectorAll('[class*="mask"], [class*="overlay"], [class*="backdrop"]');
                        const hasOverlay = Array.from(overlays).some(o => o.offsetWidth > 0);
                        return { btns: visibleBtns.slice(0, 12), toasts: toastTexts.slice(0, 8), url: location.href, hasOverlay };
                    }""")
                    bilibili_logger.info(_msg("🔍", f"发布等待 {wait_sec}s 诊断: URL={diag.get('url','')[:60]}, 按钮={diag.get('btns',[])}, Toast/弹窗={diag.get('toasts',[])}, 遮罩={diag.get('hasOverlay',False)}"))
                except Exception:
                    pass

            await asyncio.sleep(1)

        bilibili_logger.error(_msg("😵", f"等待发布结果超时（{max_wait_seconds}秒）"))
        return False

    async def upload(self, playwright: Playwright) -> None:
        """B站视频上传主流程

        重试策略：
        - 只有在「投稿按钮点击前」的步骤失败才重试（导航/上传/填表）
        - 一旦投稿按钮已点击，即使检测超时也不重新上传（视频可能已发布成功）
        """
        bilibili_logger.info(_msg("🧍", "小人先检查 cookie 和视频文件"))
        await self.validate_upload_args()
        bilibili_logger.info(_msg("🥳", "上传前检查通过"))

        # 整体重试机制（仅在投稿按钮点击前生效）
        overall_retry = 0
        max_overall_retry = 3
        last_error = None

        while overall_retry < max_overall_retry:
            overall_retry += 1
            browser = None
            context = None
            page = None
            publish_clicked = False  # 跟踪是否已点击投稿按钮

            try:
                if overall_retry > 1:
                    bilibili_logger.warning(_msg("🔄", f"第 {overall_retry} 轮重试"))
                    await asyncio.sleep(5)

                launch_kwargs = {"headless": self.headless, "args": ["--disable-gpu","--disable-dev-shm-usage","--no-sandbox","--disable-extensions","--disable-software-rasterizer"]}
                if self.local_executable_path:
                    launch_kwargs["executable_path"] = self.local_executable_path
                else:
                    launch_kwargs["channel"] = "chrome"
                browser = await playwright.chromium.launch(**launch_kwargs)
                context = await browser.new_context(
                    storage_state=self.account_file,
                )
                context = await set_init_script(context)

                page = await context.new_page()
                bilibili_logger.info(_msg("🧭", "小人正在赶往B站上传页面"))
                # 导航到上传页（加重试）
                nav_ok = False
                for attempt in range(3):
                    try:
                        await page.goto(BILIBILI_UPLOAD_URL, timeout=60000, wait_until="domcontentloaded")
                        nav_ok = True
                        break
                    except Exception as e:
                        bilibili_logger.warning(_msg("⚠️", f"B站上传页导航重试 {attempt+1}/3: {e}"))
                        if attempt < 2:
                            await asyncio.sleep(3)
                if not nav_ok:
                    raise RuntimeError("B站上传页加载失败（3次重试均超时）")

                # 等待页面充分加载（B站上传页较重，需要等 JS 渲染完）
                try:
                    await page.wait_for_load_state("networkidle", timeout=30000)
                except Exception:
                    pass
                await asyncio.sleep(3)

                # 关闭可能出现的干扰弹窗（二创计划、本地草稿恢复等）
                # 这些弹窗会在页面加载后自动弹出，必须在操作前关闭
                bilibili_logger.info(_msg("🧹", "检查并关闭干扰弹窗..."))
                for dismiss_attempt in range(5):
                    try:
                        dismissed = False
                        # 优先处理"本地草稿恢复弹窗"——点击"不用了"
                        # 该弹窗文字为"本地浏览器存在N个未提交的视频"，有「继续编辑」「不用了」
                        for skip_text in ['不用了', '不再提醒', '忽略', '跳过']:
                            try:
                                btn_loc = page.locator(f'button:has-text("{skip_text}"), span:has-text("{skip_text}"), a:has-text("{skip_text}")').first
                                if await btn_loc.count() and await btn_loc.is_visible():
                                    await btn_loc.click(timeout=3000)
                                    bilibili_logger.info(_msg("🧹", f"点击了弹窗按钮: {skip_text}"))
                                    dismissed = True
                                    await asyncio.sleep(1.5)
                                    break
                            except Exception:
                                continue
                        if dismissed:
                            continue

                        # 处理"同意/确认"类弹窗（二创计划等）
                        for text_sel in ['同意', '确认加入', '知道了', '确定']:
                            try:
                                btn_loc = page.locator(f'button:has-text("{text_sel}"), span:has-text("{text_sel}")').first
                                if await btn_loc.count() and await btn_loc.is_visible():
                                    await btn_loc.click(timeout=3000)
                                    bilibili_logger.info(_msg("🧹", f"点击了弹窗按钮: {text_sel}"))
                                    dismissed = True
                                    await asyncio.sleep(1)
                                    break
                            except Exception:
                                continue
                        if dismissed:
                            continue

                        # 尝试点击 bcc-dialog 的关闭按钮 (X)
                        try:
                            close_btn = page.locator('.bcc-dialog__close, .close, [class*="close"]').first
                            if await close_btn.count() and await close_btn.is_visible():
                                await close_btn.click(timeout=3000)
                                bilibili_logger.info(_msg("🧹", "点击了弹窗关闭按钮(X)"))
                                dismissed = True
                                await asyncio.sleep(1)
                        except Exception:
                            pass
                        if dismissed:
                            continue

                        # JS 方式检测并关闭遮挡弹窗（兜底）
                        js_closed = await page.evaluate("""() => {
                            // 检查是否有全屏遮挡层/弹窗
                            const overlays = document.querySelectorAll(
                                '.bcc-dialog__wrapper, .bcc-overlay, [class*="dialog-wrapper"], [class*="mask"], [class*="overlay"]'
                            );
                            for (const ov of overlays) {
                                if (ov.offsetWidth > 0 && ov.offsetHeight > 100) {
                                    // 找弹窗内的关闭/跳过按钮
                                    const btns = ov.querySelectorAll('button, span, a');
                                    for (const btn of btns) {
                                        const t = (btn.textContent || '').trim();
                                        if (t === '不用了' || t === '跳过' || t === '忽略' || t === '关闭' || t === '取消') {
                                            btn.click();
                                            return 'clicked: ' + t;
                                        }
                                    }
                                    // 找 X 关闭按钮
                                    const closeBtns = ov.querySelectorAll('[class*="close"]');
                                    for (const cb of closeBtns) {
                                        if (cb.offsetWidth > 0) { cb.click(); return 'close-btn'; }
                                    }
                                    return 'overlay_found_no_button';
                                }
                            }
                            return null;
                        }""")
                        if js_closed:
                            bilibili_logger.info(_msg("🧹", f"JS 关闭弹窗: {js_closed}"))
                            await asyncio.sleep(1)
                        else:
                            break  # 没有弹窗了
                    except Exception:
                        break

                # 检查是否需要登录
                if "passport.bilibili.com" in page.url:
                    raise RuntimeError("B站登录已过期，请重新登录")

                # 1. 上传视频文件
                bilibili_logger.info(_msg("📤", f"小人开始上传视频: {self.title}"))

                # B站上传页使用 bcc-upload-wrapper 组件，直接 set_input_files 会导致浏览器断开
                # 必须通过 file_chooser 事件来上传（模拟真实用户点击上传区域触发文件选择）
                upload_success = False

                # 方式1: 点击上传区域触发 file_chooser（最稳定）
                for attempt in range(3):
                    try:
                        bilibili_logger.info(_msg("📤", f"尝试点击上传区域（第{attempt+1}次）..."))
                        async with page.expect_file_chooser(timeout=15000) as fc_info:
                            # 找到上传区域并点击
                            upload_clicked = False
                            # 尝试点击可见的上传按钮/区域
                            for click_sel in [
                                '.bcc-upload-wrapper',
                                '[class*="upload-add"]',
                                '[class*="upload-btn"]',
                                'text=上传视频',
                                'text=点击上传',
                                '[class*="add-video"]',
                                '[class*="upload"]',
                            ]:
                                try:
                                    loc = page.locator(click_sel).first
                                    if await loc.count() and await loc.is_visible():
                                        await loc.click()
                                        upload_clicked = True
                                        bilibili_logger.info(_msg("✅", f"点击了上传区域: {click_sel}"))
                                        break
                                except Exception:
                                    continue

                            if not upload_clicked:
                                # JS 点击上传区域
                                await page.evaluate("""() => {
                                    const wrappers = document.querySelectorAll('.bcc-upload-wrapper, [class*="upload"]');
                                    for (const el of wrappers) {
                                        if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                                            el.click();
                                            return true;
                                        }
                                    }
                                    // fallback: 触发 file input 的 click
                                    const fileInput = document.querySelector('input[type="file"]');
                                    if (fileInput) { fileInput.click(); return true; }
                                    return false;
                                }""")
                                bilibili_logger.info(_msg("✅", "通过 JS 点击了上传区域"))

                        file_chooser = await fc_info.value
                        await file_chooser.set_files(self.file_path)
                        bilibili_logger.info(_msg("📤", "通过 file_chooser 选择文件成功"))
                        upload_success = True
                        break
                    except Exception as e:
                        bilibili_logger.warning(_msg("⚠️", f"file_chooser 第{attempt+1}次失败: {e}"))
                        await asyncio.sleep(2)

                # 方式2: 如果 file_chooser 不行，降级直接 set_input_files
                if not upload_success:
                    bilibili_logger.info(_msg("🔄", "file_chooser 失败，尝试 set_input_files..."))
                    try:
                        file_input_loc = page.locator('input[type="file"]').first
                        if await file_input_loc.count():
                            await file_input_loc.set_input_files(self.file_path)
                            bilibili_logger.info(_msg("📤", "通过 set_input_files 上传文件"))
                            upload_success = True
                        else:
                            bilibili_logger.warning(_msg("⚠️", "找不到 file input"))
                    except Exception as e:
                        bilibili_logger.warning(_msg("⚠️", f"set_input_files 也失败: {e}"))

                if not upload_success:
                    raise RuntimeError("所有文件上传方式均失败")

                bilibili_logger.info(_msg("📤", "文件已选择，等待上传..."))

                # 2. 等待视频上传完成
                upload_ok = await self._wait_for_upload_complete(page)
                if not upload_ok:
                    raise RuntimeError("视频上传失败或超时")

                # 上传完成后等待编辑表单渲染（标题/描述等输入框在上传后才出现）
                bilibili_logger.info(_msg("⏳", "等待编辑表单渲染..."))
                try:
                    # 等待标题区域出现
                    await page.wait_for_selector(
                        'input[type="text"], textarea, [contenteditable="true"]',
                        timeout=30000, state="attached"
                    )
                except Exception:
                    bilibili_logger.warning(_msg("⚠️", "等待编辑表单超时，尝试继续"))
                await asyncio.sleep(2)

                # 2.5 上传封面（B站要求必须有封面才能投稿）
                # 上传视频后 B站通常会自动截取视频帧作为封面，但有时会失败
                # 如果封面为空，需要手动上传
                await self._upload_cover(page)

                # 3. 填写标题
                await self._fill_title(page, self.title)

                # 4. 填写简介
                if self.desc:
                    await self._fill_desc(page, self.desc)

                # 5. 填写标签
                if self.tags:
                    await self._fill_tags(page, self.tags)

                # 6. 选择分区
                await self._select_zone(page, self.tid)

                # 7. 设置版权类型
                await self._set_copyright(page, copyright_type=2)

                # 8. 点击发布
                # 注意：publish_clicked 只在 _click_publish 不抛异常时才为 True
                # （_click_publish 找不到按钮会抛 RuntimeError，可重试）
                publish_ok = await self._click_publish(page)
                publish_clicked = True  # 按钮已真正点击，此时才标记

                if not publish_ok:
                    # 投稿按钮已点击但检测超时——视频可能已发布成功
                    # 不要重试！重试会导致重复上传
                    bilibili_logger.warning(_msg("⚠️", "发布结果未确认，但投稿按钮已点击。视频可能已发布成功，不再重试。"))
                    # 尝试更新 cookie（即使不确定也更新，避免浪费）
                    try:
                        await context.storage_state(path=self.account_file)
                    except Exception:
                        pass
                    # 清理并标记（避免 finally 重复关闭）
                    await asyncio.sleep(2)
                    try:
                        await context.close()
                    except Exception:
                        pass
                    try:
                        await browser.close()
                    except Exception:
                        pass
                    context = None
                    browser = None
                    return

                # 成功：更新 cookie
                await context.storage_state(path=self.account_file)
                bilibili_logger.success(_msg("🥳", "B站视频发布成功，cookie 已更新"))
                await asyncio.sleep(2)
                await context.close()
                await browser.close()
                context = None
                browser = None
                return  # 成功完成

            except Exception as e:
                last_error = e

                # 关键：如果已点击投稿按钮，不重试
                if publish_clicked:
                    bilibili_logger.warning(_msg("⚠️", f"投稿按钮已点击后发生异常: {e}，视频可能已发布，不再重试"))
                    try:
                        await context.storage_state(path=self.account_file)
                    except Exception:
                        pass
                    # 标记已清理，finally 不再重复关闭
                    context = None
                    browser = None
                    return  # 不重试

                bilibili_logger.warning(_msg("⚠️", f"第 {overall_retry} 轮失败: {e}"))
                if page and not page.is_closed():
                    try:
                        screenshot_path = Path(self.file_path).parent / f"bili_error_round{overall_retry}.png"
                        await page.screenshot(full_page=True, path=str(screenshot_path))
                        bilibili_logger.info(_msg("📸", f"失败截图: {screenshot_path}"))
                    except Exception:
                        pass
            finally:
                # 清理未关闭的浏览器（成功路径和 publish_clicked 异常路径已自行清理）
                if context:
                    try:
                        await context.close()
                    except Exception:
                        pass
                if browser:
                    try:
                        await browser.close()
                    except Exception:
                        pass

        bilibili_logger.error(_msg("😵", f"发布全部 {max_overall_retry} 轮均失败，最后错误: {last_error}"))
        raise last_error or RuntimeError(f"发布全部 {max_overall_retry} 轮均失败")

    async def bilibili_upload_video(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)

    async def main(self):
        await self.bilibili_upload_video()
