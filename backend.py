# -*- coding: utf-8 -*-
"""
Tujue AutoSend - 桌面版后端 API
基于 social-auto-upload 项目，提供视频多平台一键发布功能
"""

import asyncio
import json
import logging
import os
import shutil
import sys
import threading
import traceback
import uuid
from datetime import datetime
import time
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

# ============================================================
# 1. 将项目目录加入 sys.path，确保能导入 uploader 模块
# ============================================================
def _get_project_dir():
    """获取项目资源目录：冻结模式用 _MEIPASS（exe 内部解压），开发模式用 __file__ 目录"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.resolve()

PROJECT_DIR = _get_project_dir()
sys.path.insert(0, str(PROJECT_DIR))
# 工作目录切换到 exe 所在目录（开发模式下与 PROJECT_DIR 相同）
os.chdir(str(Path(sys.executable).parent if getattr(sys, 'frozen', False) else PROJECT_DIR))


# ============================================================
# 1.5 子进程函数（用于绕过 stream_gears 的 GIL 阻塞）
# ============================================================
def _bilibili_login_subprocess(qrcode_data, result_queue):
    """子进程：执行 stream_gears.login_by_qrcode，避免 GIL 阻塞 Flask"""
    try:
        import stream_gears as _sg
        login_result = _sg.login_by_qrcode(qrcode_data)
        result_queue.put(("success", login_result))
    except Exception as e:
        result_queue.put(("error", str(e)))


def _bilibili_upload_subprocess(kwargs, result_queue):
    """子进程：执行 stream_gears.upload，避免 GIL 阻塞 Flask"""
    try:
        import stream_gears as _sg
        _sg.upload(**kwargs)
        result_queue.put(("success", None))
    except Exception as e:
        result_queue.put(("error", str(e)))

# ============================================================
# 2. 创建 Flask 应用 + 跨域支持（前后端分离）
# ============================================================
app = Flask(__name__, static_folder=str(PROJECT_DIR))
CORS(app)

# ============================================================
# 3. 全局状态：记录各平台的上传进度和登录状态
# ============================================================
upload_status = {}       # 记录每个平台的上传状态 {platform: {"status": "...", "msg": "..."}}
upload_lock = threading.Lock()  # 线程安全锁

# 平台配置映射表（中文名 → 技术标识）
PLATFORM_MAP = {
    "douyin":   {"name": "抖音", "uploader": "douyin_uploader"},
    "kuaishou": {"name": "快手", "uploader": "ks_uploader"},
    "xhs":      {"name": "小红书", "uploader": "xiaohongshu_uploader"},
    "bilibili": {"name": "B站", "uploader": "bilibili_uploader"},
    "tencent":  {"name": "视频号", "uploader": "tencent_uploader"},
    "tiktok":   {"name": "TikTok", "uploader": "tk_uploader"},
}

# Cookie 目录约定（冻结模式在 %APPDATA%/TujueAutoSend/cookies）
from conf import DATA_DIR
COOKIES_DIR = DATA_DIR / "cookies"
# 持久化浏览器用户数据目录（launch_persistent_context 使用）
BROWSER_DATA_DIR = DATA_DIR / "browser_data"


def _remove_browser_data(platform_uploader: str, account_name: str = ""):
    """删除持久化浏览器用户数据目录（退出登录/重置时调用）

    Args:
        platform_uploader: 上传器目录名（如 "douyin_uploader"）
        account_name: 账号名，空字符串表示删除该平台全部
    """
    base_dir = BROWSER_DATA_DIR / platform_uploader
    if not base_dir.exists():
        return []

    removed = []
    if account_name:
        target = base_dir / account_name
        if target.exists():
            try:
                shutil.rmtree(str(target))
                removed.append(account_name)
            except Exception as e:
                logging.warning(f"[AutoSend] 删除浏览器数据目录失败 {target}: {e}")
    else:
        for item in base_dir.iterdir():
            if item.is_dir():
                try:
                    shutil.rmtree(str(item))
                    removed.append(item.name)
                except Exception as e:
                    logging.warning(f"[AutoSend] 删除浏览器数据目录失败 {item}: {e}")
    return removed


def requests_post_internal(url, json_data=None):
    """通过 Flask test_client 发起内部 POST 请求（用于同进程内调用 API）"""
    client = app.test_client()
    resp = client.post(url, json=json_data or {})
    return resp


def set_platform_status(platform: str, status: str, msg: str = ""):
    """更新某平台的上传状态，线程安全"""
    with upload_lock:
        upload_status[platform] = {"status": status, "msg": msg}


def get_all_status():
    """获取所有平台的状态快照"""
    with upload_lock:
        return dict(upload_status)


# ============================================================
# 4. 页面路由：直接返回 gui.html
# ============================================================

@app.route("/")
def index():
    """首页：返回 GUI 界面"""
    return send_from_directory(str(PROJECT_DIR), "gui.html")


@app.route("/<path:filename>")
def static_files(filename):
    """静态资源（图片等）"""
    return send_from_directory(str(PROJECT_DIR), filename)



# ============================================================
# 5. API 接口：账号 / 登录 / 上传
# ============================================================

# 视频上传目录
# uploads 存到项目所在磁盘，避免 C 盘空间不足
_PROJECT_DRIVE = Path(__file__).resolve().drive  # 如 "G:"
_UPLOAD_BASE = Path(f"{_PROJECT_DRIVE}/TujueAutoSend/uploads")
UPLOADS_DIR = _UPLOAD_BASE
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


@app.route("/api/upload/video", methods=["POST"])
def api_upload_video():
    """
    上传视频文件到服务器临时目录
    前端选择视频后先上传，获取服务器端绝对路径，再用于发布
    解决浏览器环境下 file.path 不可用的问题
    """
    if "file" not in request.files:
        return jsonify({"code": 400, "msg": "未找到上传文件"})

    file = request.files["file"]
    if not file.filename:
        return jsonify({"code": 400, "msg": "文件名为空"})

    # 安全处理文件名
    original_name = secure_filename(file.filename)
    if not original_name:
        original_name = "video.mp4"

    # 用时间戳+UUID 避免冲突
    stem = Path(original_name).stem
    suffix = Path(original_name).suffix or ".mp4"
    unique_name = f"{stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}{suffix}"

    save_path = UPLOADS_DIR / unique_name
    file.save(str(save_path))

    # 验证文件
    if not save_path.exists() or save_path.stat().st_size == 0:
        return jsonify({"code": 500, "msg": "文件保存失败"})

    logging.info(f"[AutoSend] 视频已上传: {save_path} ({save_path.stat().st_size / 1024 / 1024:.1f} MB)")
    return jsonify({
        "code": 0,
        "msg": "上传成功",
        "data": {
            "path": str(save_path),
            "name": original_name,
            "size": save_path.stat().st_size,
            "size_human": f"{save_path.stat().st_size / 1024 / 1024:.1f} MB",
        }
    })


@app.route("/api/platforms", methods=["GET"])
def api_platforms():
    """
    返回所有支持的平台列表及其登录状态
    前端在加载时调用此接口初始化界面
    """
    result = []
    for key, info in PLATFORM_MAP.items():
        # 判断 cookie 文件是否存在（粗略判断是否已登录）
        cookie_dir = COOKIES_DIR / info["uploader"]
        cookie_files = list(cookie_dir.glob("*.json")) if cookie_dir.exists() else []
        
        # 获取最新 cookie 修改时间（前端用于显示登录时间）
        cookie_modified = None
        if cookie_files:
            cookie_modified = max(f.stat().st_mtime for f in cookie_files)
        
        result.append({
            "id": key,
            "name": info["name"],
            "logged_in": len(cookie_files) > 0,
            "account_count": len(cookie_files),
            "supported": True,     # social-auto-upload 支持的平台标记为 True
            "cookie_modified": cookie_modified,  # 最新 cookie 修改时间戳
        })

    # 额外添加暂不支持的平台（占位）
    for pid, pname in [("youtube", "YouTube"), ("instagram", "Instagram"), ("x", "X")]:
        result.append({
            "id": pid,
            "name": pname,
            "logged_in": False,
            "account_count": 0,
            "supported": False,    # 标记为不支持
        })

    return jsonify({"code": 0, "data": result})


@app.route("/api/login/<platform>", methods=["POST"])
def api_login(platform):
    """
    触发指定平台的扫码登录
    返回二维码信息或登录结果
    """
    if platform not in PLATFORM_MAP:
        return jsonify({"code": 404, "msg": f"不支持的平台: {platform}"})

    try:
        data = request.get_json(force=True) or {}
        account_name = data.get("account", "default")
        cookie_path = str(COOKIES_DIR / PLATFORM_MAP[platform]["uploader"] / f"{account_name}.json")

        # 在新线程中执行异步登录操作
        loop = asyncio.new_event_loop()
        
        if platform == "douyin":
            from uploader.douyin_uploader.main import douyin_setup
            result = loop.run_until_complete(douyin_setup(cookie_path, handle=True, return_detail=True, headless=False))
        elif platform == "kuaishou":
            from uploader.ks_uploader.main import ks_setup
            result = loop.run_until_complete(ks_setup(cookie_path, handle=True, return_detail=True, headless=False))
        elif platform == "tencent":
            from uploader.tencent_uploader.main import tencent_setup
            result = loop.run_until_complete(tencent_setup(cookie_path, handle=True, return_detail=True, headless=False))
        elif platform == "tiktok":
            from uploader.tk_uploader.main import tiktok_setup
            result = loop.run_until_complete(tiktok_setup(cookie_path, handle=True))
            if not isinstance(result, dict):
                result = {"success": bool(result), "status": "ok" if result else "failed"}
        elif platform == "xhs":
            from uploader.xiaohongshu_uploader.main import xiaohongshu_setup
            result = loop.run_until_complete(
                xiaohongshu_setup(cookie_path, handle=True, return_detail=True, headless=False)
            )
        else:
            return jsonify({"code": 400, "msg": f"{PLATFORM_MAP[platform]['name']} 暂不支持通过 GUI 登录"})

        loop.close()

        if result.get("success"):
            return jsonify({
                "code": 0,
                "msg": f"{PLATFORM_MAP[platform]['name']} 登录成功",
                "data": {"status": "success"}
            })
        else:
            return jsonify({
                "code": 500,
                "msg": result.get("message", "登录失败"),
                "data": result
            })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"code": 500, "msg": f"登录出错: {str(e)}"})


@app.route("/api/upload", methods=["POST"])
def api_upload():
    """
    一键上传到多个平台
    
    请求参数 JSON：
    {
        "video": "视频文件绝对路径",
        "title": "视频标题",
        "desc": "作品描述",
        "tags": ["标签1", "标签2"],
        "platforms": ["douyin", "kuaishou", ...],
        "schedule_time": "" 或 "2026-04-25 12:00"
    }
    """
    data = request.get_json(force=True)
    
    video_path = data.get("video", "")
    title = data.get("title", "").strip()
    desc = data.get("desc", "").strip()
    tags = data.get("tags", [])
    platforms = data.get("platforms", [])
    schedule_str = data.get("schedule_time", "")
    platform_extra = data.get("platform_extra", {})  # 平台特定参数，如 {"bilibili": {"tid": 122}}

    # ---- 参数校验 ----
    if not video_path or not os.path.exists(video_path):
        return jsonify({"code": 400, "msg": "视频文件不存在"})
    if not title:
        return jsonify({"code": 400, "msg": "标题不能为空"})
    if not platforms:
        return jsonify({"code": 400, "msg": "请至少选择一个发布平台"})

    # 解析定时发布时间
    publish_date = 0  # 0 表示立即发布
    if schedule_str:
        try:
            publish_date = datetime.strptime(schedule_str, "%Y-%m-%d %H:%M")
        except ValueError:
            return jsonify({"code": 400, "msg": "时间格式错误，请使用 YYYY-MM-DD HH:MM"})

    # ---- 过滤掉不支持和未选中的平台 ----
    valid_platforms = [p for p in platforms if p in PLATFORM_MAP]
    unsupported = [p for p in platforms if p not in PLATFORM_MAP]

    # ---- 在后台线程中 asyncio 并发上传 ----
    # 读取线程分配方案（前端传入，如 {"douyin": 1, "bilibili": 2, "kuaishou": 1}）
    thread_assignment = data.get("thread_assignment", {})
    # 根据分配方案分组：{1: ["douyin", "kuaishou"], 2: ["bilibili"]}
    thread_groups = {}
    for platform in valid_platforms:
        tid = thread_assignment.get(platform, 1)
        thread_groups.setdefault(tid, []).append(platform)

    def upload_worker():
        """上传工作线程：asyncio 并发处理多平台发布任务"""
        # 创建一条初始的历史记录（pending 状态）
        history_record = {
            "video": video_path,
            "video_name": os.path.basename(video_path) if video_path else "",
            "title": title,
            "desc": desc,
            "tags": tags,
            "platforms": valid_platforms + unsupported,
            "status": "pending",
            "schedule_time": schedule_str,
        }
        hr_resp = None
        try:
            hr_resp = requests_post_internal("/api/history", json_data=history_record)
        except Exception as e:
            logging.warning(f"[AutoSend] 创建历史记录失败（非致命）: {e}")

        record_id = None
        if hr_resp:
            try:
                record_id = hr_resp.get_json().get("data", {}).get("id")
            except Exception as e:
                logging.warning(f"[AutoSend] 解析历史记录ID失败（非致命）: {e}")

        # ---- asyncio 并发上传 ----
        try:
            platform_details = asyncio.run(_async_upload_all(
                valid_platforms, video_path, title, desc, tags, publish_date,
                platform_extra, thread_groups, unsupported
            ))
        except Exception as outer_e:
            logging.critical(f"[AutoSend] upload_worker 严重异常: {outer_e}")
            traceback.print_exc(file=sys.stderr) if sys.stderr else logging.critical(traceback.format_exc())
            platform_details = [{"platform": p, "status": "error", "msg": str(outer_e)} for p in valid_platforms + unsupported]

        # ---- 更新历史记录状态 ----
        if record_id:
            success_cnt = sum(1 for d in platform_details if d.get("status") == "success")
            error_cnt = sum(1 for d in platform_details if d.get("status") == "error")
            final_status = "success" if error_cnt == 0 else ("partial" if success_cnt > 0 else "error")
            try:
                requests_post_internal(
                    "/api/history/update/" + record_id,
                    json_data={"status": final_status, "platform_details": platform_details}
                )
            except Exception as e:
                logging.warning(f"[AutoSend] 更新历史记录状态失败: {e}")

    thread = threading.Thread(target=upload_worker, daemon=True)
    thread.start()

    return jsonify({
        "code": 0,
        "msg": f"已开始发布到 {len(valid_platforms)} 个平台，请在界面查看进度",
        "data": {
            "total": len(valid_platforms),
            "platforms": valid_platforms,
            "unsupported": unsupported
        }
    })


# ============================================================
# asyncio 并发上传核心
# ============================================================

async def _async_upload_all(valid_platforms, video_path, title, desc, tags, publish_date, platform_extra, thread_groups, unsupported):
    """
    asyncio 并发上传到多个平台
    - valid_platforms: 已选平台列表
    - thread_groups: {thread_id: [platform, ...]}  前端传入的线程分配方案
    - 使用 Semaphore 控制并发数（= len(thread_groups)）
    """
    settings = load_settings()
    max_concurrent = settings.get("concurrent_uploads", 2)
    max_concurrent = max(1, min(max_concurrent, len(valid_platforms)))

    # 先设置所有平台为 "等待中"
    for platform in valid_platforms:
        tid = _find_thread_for_platform(platform, thread_groups)
        set_platform_status(platform, "uploading", f"等待中 (线程{tid})...")

    sem = asyncio.Semaphore(max_concurrent)

    async def _worker(platform):
        extra = platform_extra.get(platform, {})
        tid = _find_thread_for_platform(platform, thread_groups)
        async with sem:
            try:
                set_platform_status(platform, "uploading", f"上传中 (线程{tid})...")
                await _do_upload_async(platform, video_path, title, desc, tags, publish_date, extra)
                set_platform_status(platform, "success", f"发布成功 (线程{tid})")
                return {"platform": platform, "status": "success", "msg": "发布成功"}
            except Exception as e:
                err_msg = str(e)
                logging.error(f"[AutoSend] {PLATFORM_MAP.get(platform, {}).get('name', platform)} 上传失败: {err_msg}")
                set_platform_status(platform, "error", f"失败 (线程{tid}): {err_msg[:20]}")
                return {"platform": platform, "status": "error", "msg": err_msg}

    # 发起所有协程
    results = await asyncio.gather(*[_worker(p) for p in valid_platforms], return_exceptions=True)

    # 处理结果
    platform_details = []
    for r in results:
        if isinstance(r, Exception):
            platform_details.append({"platform": "unknown", "status": "error", "msg": str(r)})
        elif isinstance(r, dict):
            platform_details.append(r)
        else:
            platform_details.append({"platform": "unknown", "status": "error", "msg": str(r)})

    # 对不支持的平台标记
    for p in unsupported:
        set_platform_status(p, "error", "⚠️ 暂不支持该平台")
        platform_details.append({"platform": p, "status": "error", "msg": "暂不支持"})

    return platform_details


def _find_thread_for_platform(platform, thread_groups):
    """查找某平台归属的线程ID"""
    for tid, plats in thread_groups.items():
        if platform in plats:
            return tid
    return 1


async def _do_upload_async(platform: str, video_path: str, title: str, desc: str, tags: list, publish_date, extra: dict = None):
    """
    async 单平台上传（直接 await uploader 的 async 方法，无需 event loop 包装）
    """
    extra = extra or {}
    cookie_dir = COOKIES_DIR / PLATFORM_MAP[platform]["uploader"]
    cookie_files = list(cookie_dir.glob("*.json")) if cookie_dir.exists() else []

    if not cookie_files:
        raise RuntimeError(f"{PLATFORM_MAP[platform]['name']} 尚未登录，请先扫码登录")

    account_file = str(cookie_files[0])
    logging.info(f"[AutoSend] 开始上传到 {PLATFORM_MAP[platform]['name']}: {title}")

    if platform == "douyin":
        from uploader.douyin_uploader.main import DouYinVideo, DOUYIN_PUBLISH_STRATEGY_IMMEDIATE
        strategy = DOUYIN_PUBLISH_STRATEGY_IMMEDIATE if publish_date == 0 else "scheduled"
        app_obj = DouYinVideo(
            title=title, file_path=video_path, tags=tags, publish_date=publish_date,
            account_file=account_file, desc=desc, publish_strategy=strategy, headless=False,
        )
        await app_obj.douyin_upload_video()

    elif platform == "kuaishou":
        from uploader.ks_uploader.main import KSVideo
        app_obj = KSVideo(
            title=title, file_path=video_path, tags=tags, publish_date=publish_date,
            account_file=account_file, desc=desc, headless=False,
        )
        await app_obj.main()

    elif platform == "tencent":
        from uploader.tencent_uploader.main import TencentVideo, TENCENT_PUBLISH_STRATEGY_IMMEDIATE
        strategy = TENCENT_PUBLISH_STRATEGY_IMMEDIATE if publish_date == 0 else "scheduled"
        app_obj = TencentVideo(
            title=title, file_path=video_path, tags=tags, publish_date=publish_date,
            account_file=account_file, desc=desc, publish_strategy=strategy, headless=False,
        )
        await app_obj.tencent_upload_video()

    elif platform == "tiktok":
        from uploader.tk_uploader.main import TiktokVideo
        app_obj = TiktokVideo(
            title=title, file_path=video_path, tags=tags, publish_date=publish_date,
            account_file=account_file,
        )
        await app_obj.main()

    elif platform == "bilibili":
        from uploader.bilibili_uploader.main import BilibiliVideo, BILIBILI_PUBLISH_STRATEGY_IMMEDIATE
        tid = extra.get("tid", 21)
        strategy = BILIBILI_PUBLISH_STRATEGY_IMMEDIATE if publish_date == 0 else "scheduled"
        app_obj = BilibiliVideo(
            title=title, file_path=video_path, tags=tags, publish_date=publish_date,
            account_file=account_file, desc=desc, tid=tid, publish_strategy=strategy, headless=False,
        )
        await app_obj.main()

    elif platform == "xhs":
        from uploader.xiaohongshu_uploader.main import XiaoHongShuVideo, XIAOHONGSHU_PUBLISH_STRATEGY_IMMEDIATE
        strategy = XIAOHONGSHU_PUBLISH_STRATEGY_IMMEDIATE if publish_date == 0 else "scheduled"
        app_obj = XiaoHongShuVideo(
            title=title, file_path=video_path, tags=tags, publish_date=publish_date,
            account_file=account_file, desc=desc, publish_strategy=strategy, headless=False,
        )
        await app_obj.xiaohongshu_upload_video()

    else:
        raise RuntimeError(f"未知平台: {platform}")

    logging.info(f"[AutoSend] {PLATFORM_MAP[platform]['name']} 上传完成")


@app.route("/api/status", methods=["GET"])
def api_status():
    """查询当前各平台的上传进度状态"""
    return jsonify({"code": 0, "data": get_all_status()})


# ============================================================
# 5.5 登录相关增强 API（二维码 / 退出登录 / 账号列表）
# ============================================================

# 存储登录会话信息（二维码 token 等）
login_sessions = {}  # {session_id: {platform, status, qrcode_data, ...}}


@app.route("/api/diagnose/upload", methods=["POST"])
def api_diagnose_upload():
    """
    诊断端点：用 headless 模式运行一次上传测试，日志写到文件
    请求: { "video": "绝对路径", "platform": "douyin" }
    """
    data = request.get_json(force=True) or {}
    video_path = data.get("video", "")
    platform = data.get("platform", "douyin")

    if not video_path or not os.path.exists(video_path):
        return jsonify({"code": 400, "msg": f"视频文件不存在: {video_path}"})

    diag_log = DATA_DIR / "logs" / f"diag_upload_{datetime.now().strftime('%H%M%S')}.log"
    diag_log.parent.mkdir(exist_ok=True)

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        cookie_dir = COOKIES_DIR / PLATFORM_MAP[platform]["uploader"]
        cookie_files = list(cookie_dir.glob("*.json")) if cookie_dir.exists() else []
        if not cookie_files:
            loop.close()
            return jsonify({"code": 400, "msg": f"{PLATFORM_MAP[platform]['name']} 尚未登录"})

        account_file = str(cookie_files[0])

        if platform == "douyin":
            from uploader.douyin_uploader.main import DouYinVideo, DOUYIN_PUBLISH_STRATEGY_IMMEDIATE
            app_obj = DouYinVideo(
                title="诊断测试",
                file_path=video_path,
                tags=["诊断"],
                publish_date=0,
                account_file=account_file,
                desc="诊断测试",
                publish_strategy=DOUYIN_PUBLISH_STRATEGY_IMMEDIATE,
                headless=True,  # headless 模式，不打开窗口
            )
            loop.run_until_complete(app_obj.douyin_upload_video())

        loop.close()

        # 返回日志内容
        logs = diag_log.read_text(encoding="utf-8", errors="replace") if diag_log.exists() else ""
        return jsonify({"code": 0, "msg": "诊断完成", "log_file": str(diag_log), "logs": logs})
    except Exception as e:
        import traceback
        err = traceback.format_exc()
        logs = diag_log.read_text(encoding="utf-8", errors="replace") if diag_log.exists() else ""
        return jsonify({"code": 500, "msg": str(e), "logs": logs, "trace": err})


@app.route("/api/accounts/<platform>", methods=["GET"])
def api_accounts(platform):
    """
    获取指定平台的账号列表详情
    返回每个 cookie 文件名、大小、修改时间、以及从 cookie 中提取的用户信息
    """
    if platform not in PLATFORM_MAP:
        return jsonify({"code": 404, "msg": f"不支持的平台: {platform}"})

    cookie_dir = COOKIES_DIR / PLATFORM_MAP[platform]["uploader"]
    accounts = []
    if cookie_dir.exists():
        for cf in sorted(cookie_dir.glob("*.json")):
            stat = cf.stat()
            account_name = cf.stem

            # 从 cookie 文件中提取用户信息
            user_info = _extract_user_info(platform, cf)

            accounts.append({
                "name": account_name,
                "file": str(cf),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "nickname": user_info.get("nickname", ""),
                "avatar_url": user_info.get("avatar_url", ""),
                "user_id": user_info.get("user_id", ""),
            })

    return jsonify({
        "code": 0,
        "data": {
            "platform": platform,
            "platform_name": PLATFORM_MAP[platform]["name"],
            "accounts": accounts,
            "total": len(accounts),
        }
    })


def _extract_user_info(platform: str, cookie_file: Path) -> dict:
    """从 cookie 文件中提取用户信息（昵称、头像、用户 ID）"""
    info = {"nickname": "", "avatar_url": "", "user_id": ""}
    try:
        with open(cookie_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        cookies = data.get("cookies", [])

        if platform == "douyin":
            # 抖音：提取 uid_tt 作为用户 ID
            for c in cookies:
                if c.get("name") == "uid_tt":
                    info["user_id"] = c.get("value", "")[:16]
                    break
            # 尝试从 localStorage 中获取用户信息
            for origin in data.get("origins", []):
                ls = origin.get("localStorage", [])
                for item in ls:
                    name = item.get("name", "")
                    val = item.get("value", "")
                    if "user" in name.lower() and val:
                        try:
                            udata = json.loads(val) if isinstance(val, str) else val
                            if isinstance(udata, dict):
                                info["nickname"] = udata.get("nickname", "") or udata.get("name", "")
                                info["avatar_url"] = udata.get("avatar_url", "") or udata.get("avatar", "")
                                info["user_id"] = udata.get("uid", "") or udata.get("user_id", info["user_id"])
                        except (json.JSONDecodeError, TypeError):
                            pass

        elif platform == "kuaishou":
            # 快手：提取 userId
            for c in cookies:
                if c.get("name") == "userId":
                    info["user_id"] = c.get("value", "")
                    break
            # 尝试从 localStorage 获取
            for origin in data.get("origins", []):
                ls = origin.get("localStorage", [])
                for item in ls:
                    name = item.get("name", "")
                    val = item.get("value", "")
                    if "user" in name.lower() and val:
                        try:
                            udata = json.loads(val) if isinstance(val, str) else val
                            if isinstance(udata, dict):
                                info["nickname"] = udata.get("nickname", "") or udata.get("name", "")
                                info["avatar_url"] = udata.get("avatar_url", "") or udata.get("headurl", "")
                                info["user_id"] = udata.get("userId", "") or udata.get("user_id", info["user_id"])
                        except (json.JSONDecodeError, TypeError):
                            pass

        elif platform == "tencent":
            # 视频号
            for origin in data.get("origins", []):
                ls = origin.get("localStorage", [])
                for item in ls:
                    name = item.get("name", "")
                    val = item.get("value", "")
                    if "user" in name.lower() and val:
                        try:
                            udata = json.loads(val) if isinstance(val, str) else val
                            if isinstance(udata, dict):
                                info["nickname"] = udata.get("nickname", "") or udata.get("name", "")
                                info["avatar_url"] = udata.get("avatar_url", "") or udata.get("headimgurl", "")
                                info["user_id"] = udata.get("uid", "") or udata.get("user_id", "")
                        except (json.JSONDecodeError, TypeError):
                            pass

        elif platform == "bilibili":
            for c in cookies:
                if c.get("name") == "DedeUserName":
                    info["nickname"] = c.get("value", "")
                elif c.get("name") == "DedeUserID":
                    info["user_id"] = c.get("value", "")

        elif platform == "tiktok":
            for c in cookies:
                name = c.get("name", "")
                if name == "uid_tt":
                    info["user_id"] = c.get("value", "")[:16]
                elif name == "unique_id":
                    info["nickname"] = c.get("value", "")

    except Exception as e:
        logging.warning(f"[AutoSend] 提取用户信息失败 ({platform}): {e}")

    return info


@app.route("/api/logout/<platform>", methods=["POST"])
def api_logout(platform):
    """
    退出指定平台的登录（删除 cookie 文件）
    可选 JSON 参数：{"account": "default"} 指定要退出的账号，不传则删除全部
    """
    if platform not in PLATFORM_MAP:
        return jsonify({"code": 404, "msg": f"不支持的平台: {platform}"})

    data = request.get_json(force=True) or {}
    target_account = data.get("account", "")  # 空字符串表示全部退出

    cookie_dir = COOKIES_DIR / PLATFORM_MAP[platform]["uploader"]
    if not cookie_dir.exists() or not any(cookie_dir.glob("*.json")):
        return jsonify({"code": 0, "msg": f"{PLATFORM_MAP[platform]['name']} 当前没有已登录的账号"})

    removed = []
    for cf in list(cookie_dir.glob("*.json")):
        account_name = cf.stem
        # 如果指定了账号名，只删匹配的；否则全删
        if target_account and account_name != target_account:
            continue
        try:
            cf.unlink()  # 删除 cookie 文件
            removed.append(account_name)
        except Exception as e:
            return jsonify({"code": 500, "msg": f"删除 {account_name} 的登录信息失败: {e}"})

    # 同时删除持久化浏览器用户数据目录
    uploader_name = PLATFORM_MAP[platform]["uploader"]
    if target_account:
        _remove_browser_data(uploader_name, target_account)
    else:
        _remove_browser_data(uploader_name)

    if not removed:
        return jsonify({"code": 404, "msg": f"未找到账号 {target_account}"})

    logging.info(f"[AutoSend] {PLATFORM_MAP[platform]['name']} 已退出登录: {removed}")
    return jsonify({
        "code": 0,
        "msg": f"已退出 {PLATFORM_MAP[platform]['name']} 的 {len(removed)} 个账号",
        "data": {"removed": removed}
    })


@app.route("/api/login/start/<platform>", methods=["POST"])
def api_login_start(platform):
    """
    启动登录流程 — 在后台线程中打开浏览器获取二维码
    返回 session_id，前端可用此 ID 轮询二维码状态
    """
    if platform not in PLATFORM_MAP:
        return jsonify({"code": 404, "msg": f"不支持的平台: {platform}"})

    try:
        data = request.get_json(force=True) or {}
        account_name = data.get("account", "default")
        cookie_path = str(COOKIES_DIR / PLATFORM_MAP[platform]["uploader"] / f"{account_name}.json")

        # 创建登录会话
        session_id = uuid.uuid4().hex[:12]
        login_sessions[session_id] = {
            "platform": platform,
            "account": account_name,
            "status": "browser_opening",   # browser_opening → waiting_scan → scanned → success/failed
            "qrcode_base64": "",           # 二维码图片的 base64 数据
            "qrcode_url": "",              # 二维码 URL 或文本
            "message": "正在打开浏览器...",
            "result": None,
        }

        def login_worker(sid, plat, cpath):
            """后台执行登录流程"""
            sess = login_sessions.get(sid)
            if not sess:
                return

            def on_qrcode(qrcode_info: dict):
                """二维码回调：将二维码数据写入会话，前端可轮询获取"""
                sess["qrcode_base64"] = qrcode_info.get("image_data_url", "")
                sess["qrcode_url"] = qrcode_info.get("image_path", "")
                if sess["status"] == "browser_opening":
                    sess["status"] = "waiting_scan"
                    sess["message"] = "请扫描二维码登录"

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                if plat == "douyin":
                    from uploader.douyin_uploader.main import douyin_setup
                    result = loop.run_until_complete(
                        douyin_setup(cpath, handle=True, return_detail=True, qrcode_callback=on_qrcode, headless=False)
                    )
                elif plat == "kuaishou":
                    from uploader.ks_uploader.main import ks_setup
                    result = loop.run_until_complete(
                        ks_setup(cpath, handle=True, return_detail=True, qrcode_callback=on_qrcode, headless=False)
                    )
                elif plat == "tencent":
                    from uploader.tencent_uploader.main import tencent_setup
                    result = loop.run_until_complete(
                        tencent_setup(cpath, handle=True, return_detail=True, qrcode_callback=on_qrcode, headless=False)
                    )
                elif plat == "tiktok":
                    from uploader.tk_uploader.main import tiktok_setup
                    result = loop.run_until_complete(tiktok_setup(cpath, handle=True))
                    if not isinstance(result, dict):
                        result = {"success": bool(result), "status": "ok" if result else "failed"}
                elif plat == "bilibili":
                    # B站改用浏览器自动化登录（stream_gears API 已被封禁）
                    # 使用 patchright 打开B站登录页面，扫码后保存 storage_state
                    loop.close()
                    import asyncio as _asyncio
                    loop2 = _asyncio.new_event_loop()
                    _asyncio.set_event_loop(loop2)
                    from uploader.bilibili_uploader.main import bilibili_cookie_gen

                    def on_bili_qrcode(payload):
                        if payload.get("image_data_url"):
                            sess["qrcode_base64"] = payload["image_data_url"]
                        sess["status"] = "waiting_scan"
                        sess["message"] = "请扫描二维码登录B站"

                    try:
                        sess["status"] = "browser_opening"
                        sess["message"] = "正在打开B站登录页面..."

                        result = loop2.run_until_complete(
                            bilibili_cookie_gen(cpath, qrcode_callback=on_bili_qrcode, headless=False)
                        )

                        if result.get("success"):
                            sess["status"] = "success"
                            sess["message"] = "B站登录成功！"
                            sess["result"] = {"success": True, "status": "ok", "account_file": cpath}
                        else:
                            sess["status"] = "failed"
                            sess["message"] = result.get("message", "B站登录失败")
                            sess["result"] = {"success": False, "status": "failed", "message": result.get("message", "")}

                    except Exception as e:
                        sess["status"] = "failed"
                        sess["message"] = f"B站登录失败: {str(e)}"
                        sess["result"] = {"success": False, "status": "failed", "message": str(e)}
                    return
                elif plat == "xhs":
                    from uploader.xiaohongshu_uploader.main import xiaohongshu_setup
                    result = loop.run_until_complete(
                        xiaohongshu_setup(cpath, handle=True, return_detail=True, qrcode_callback=on_qrcode, headless=False)
                    )
                else:
                    sess["status"] = "failed"
                    sess["message"] = f"{PLATFORM_MAP[plat]['name']} 暂不支持 GUI 登录"
                    return

                loop.close()

                if result.get("success"):
                    sess["status"] = "success"
                    sess["message"] = f"{PLATFORM_MAP[plat]['name']} 登录成功！"
                    sess["result"] = result
                else:
                    sess["status"] = "failed"
                    sess["message"] = result.get("message", "登录失败，请重试")
                    sess["result"] = result

            except Exception as e:
                sess["status"] = "failed"
                sess["message"] = f"登录出错: {str(e)}"
                traceback.print_exc()

        # 启动登录线程
        thread = threading.Thread(target=login_worker, args=(session_id, platform, cookie_path), daemon=True)
        thread.start()

        return jsonify({
            "code": 0,
            "data": {
                "session_id": session_id,
                "platform": platform,
                "platform_name": PLATFORM_MAP[platform]["name"],
                "status": "browser_opening",
                "message": "正在启动浏览器，请稍候...",
            }
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"code": 500, "msg": f"启动登录失败: {str(e)}"})


@app.route("/api/login/status/<session_id>", methods=["GET"])
def api_login_status(session_id):
    """
    轮询登录状态
    前端调用 /api/login/start 后，定时轮询此接口直到 status 为 success 或 failed
    """
    sess = login_sessions.get(session_id)
    if not sess:
        return jsonify({"code": 404, "msg": "登录会话不存在或已过期"})

    resp = {
        "code": 0,
        "data": {
            "session_id": session_id,
            "status": sess["status"],         # browser_opening / waiting_scan / scanned / success / failed
            "message": sess["message"],
            "platform": sess["platform"],
            "platform_name": PLATFORM_MAP.get(sess["platform"], {}).get("name", sess["platform"]),
        }
    }

    # 二维码可用时附上 base64 数据（前端直接用作 <img src>）
    if sess.get("qrcode_base64"):
        resp["data"]["qrcode_base64"] = sess["qrcode_base64"]

    # 成功或失败时附上详细信息
    if sess["status"] in ("success", "failed") and sess.get("result"):
        resp["data"]["result"] = sess["result"]

    return jsonify(resp)


# Cookie 校验缓存（避免频繁启动浏览器）
_cookie_check_cache = {}
COOKIE_CHECK_CACHE_TTL = 300  # 5 分钟内不重复检测


@app.route("/api/check-cookie/<platform>", methods=["GET"])
def api_check_cookie(platform):
    """检查指定平台的 cookie 是否有效"""
    if platform not in PLATFORM_MAP:
        return jsonify({"code": 404, "msg": f"不支持的平台: {platform}"})

    # 检查缓存（5 分钟内不重复检测）
    cache_entry = _cookie_check_cache.get(platform)
    if cache_entry and (time.time() - cache_entry["time"]) < COOKIE_CHECK_CACHE_TTL:
        return jsonify({"code": 0, "data": cache_entry["data"]})

    cookie_dir = COOKIES_DIR / PLATFORM_MAP[platform]["uploader"]
    cookie_files = list(cookie_dir.glob("*.json")) if cookie_dir.exists() else []

    if not cookie_files:
        result_data = {"valid": False, "reason": "尚未登录"}
        _cookie_check_cache[platform] = {"data": result_data, "time": time.time()}
        return jsonify({"code": 0, "data": result_data})

    # 异步校验 cookie
    try:
        loop = asyncio.new_event_loop()

        if platform == "bilibili":
            # B站改用浏览器自动化校验 cookie
            from uploader.bilibili_uploader.main import cookie_auth as bili_cookie_auth
            try:
                valid = loop.run_until_complete(bili_cookie_auth(str(cookie_files[0])))
                result_data = {"valid": valid, "reason": "" if valid else "cookie 已过期"}
                _cookie_check_cache[platform] = {"data": result_data, "time": time.time()}
                return jsonify({"code": 0, "data": result_data})
            except Exception as e:
                result_data = {"valid": False, "reason": str(e)}
                _cookie_check_cache[platform] = {"data": result_data, "time": time.time()}
                return jsonify({"code": 0, "data": result_data})

        if platform == "douyin":
            from uploader.douyin_uploader.main import cookie_auth
            valid = loop.run_until_complete(cookie_auth(str(cookie_files[0])))
        elif platform == "kuaishou":
            from uploader.ks_uploader.main import cookie_auth
            valid = loop.run_until_complete(cookie_auth(str(cookie_files[0])))
        elif platform == "tencent":
            from uploader.tencent_uploader.main import cookie_auth
            valid = loop.run_until_complete(cookie_auth(str(cookie_files[0])))
        elif platform == "tiktok":
            from uploader.tk_uploader.main import cookie_auth
            valid = loop.run_until_complete(cookie_auth(str(cookie_files[0])))
        else:
            valid = True  # 其他平台默认认为有效

        loop.close()
        result_data = {"valid": valid, "reason": "" if valid else "cookie 已过期"}
        _cookie_check_cache[platform] = {"data": result_data, "time": time.time()}
        return jsonify({"code": 0, "data": result_data})
    except Exception as e:
        result_data = {"valid": False, "reason": str(e)}
        _cookie_check_cache[platform] = {"data": result_data, "time": time.time()}
        return jsonify({"code": 0, "data": result_data})


# ============================================================
# 5.6 B站分区列表 API
# ============================================================

# B站常用分区（id → 名称），从 VideoZoneTypes 枚举提取
BILIBILI_ZONES = [
    {"tid": 1,   "name": "动画",     "sub": [
        {"tid": 24,  "name": "MAD·AMV"},
        {"tid": 25,  "name": "MMD·3D"},
        {"tid": 47,  "name": "短片·手书·配音"},
        {"tid": 210, "name": "手办·模玩"},
        {"tid": 86,  "name": "特摄"},
        {"tid": 253, "name": "动漫杂谈"},
        {"tid": 27,  "name": "综合"},
    ]},
    {"tid": 4,   "name": "游戏",     "sub": [
        {"tid": 17,  "name": "单机游戏"},
        {"tid": 171, "name": "电子竞技"},
        {"tid": 172, "name": "手机游戏"},
        {"tid": 65,  "name": "网络游戏"},
        {"tid": 173, "name": "桌游棋牌"},
        {"tid": 121, "name": "GMV"},
        {"tid": 136, "name": "音游"},
        {"tid": 19,  "name": "Mugen"},
    ]},
    {"tid": 3,   "name": "音乐",     "sub": [
        {"tid": 28,  "name": "原创音乐"},
        {"tid": 31,  "name": "翻唱"},
        {"tid": 59,  "name": "演奏"},
        {"tid": 30,  "name": "VOCALOID·UTAU"},
        {"tid": 29,  "name": "音乐现场"},
        {"tid": 193, "name": "MV"},
        {"tid": 243, "name": "乐评盘点"},
        {"tid": 244, "name": "音乐教学"},
        {"tid": 130, "name": "音乐综合"},
    ]},
    {"tid": 129, "name": "舞蹈",     "sub": [
        {"tid": 20,  "name": "宅舞"},
        {"tid": 198, "name": "街舞"},
        {"tid": 199, "name": "明星舞蹈"},
        {"tid": 200, "name": "中国舞"},
        {"tid": 154, "name": "舞蹈综合"},
        {"tid": 156, "name": "舞蹈教程"},
    ]},
    {"tid": 36,  "name": "知识",     "sub": [
        {"tid": 201, "name": "科学科普"},
        {"tid": 124, "name": "社科·法律·心理"},
        {"tid": 228, "name": "人文历史"},
        {"tid": 207, "name": "财经商业"},
        {"tid": 208, "name": "校园学习"},
        {"tid": 209, "name": "职业职场"},
        {"tid": 229, "name": "设计·创意"},
        {"tid": 122, "name": "野生技能协会"},
    ]},
    {"tid": 188, "name": "科技",     "sub": [
        {"tid": 95,  "name": "数码"},
        {"tid": 230, "name": "软件应用"},
        {"tid": 231, "name": "计算机技术"},
        {"tid": 232, "name": "科工机械"},
    ]},
    {"tid": 181, "name": "影视",     "sub": [
        {"tid": 182, "name": "影视杂谈"},
        {"tid": 183, "name": "影视剪辑"},
        {"tid": 85,  "name": "小剧场"},
        {"tid": 184, "name": "预告·资讯"},
    ]},
    {"tid": 5,   "name": "娱乐",     "sub": [
        {"tid": 71,  "name": "综艺"},
        {"tid": 241, "name": "娱乐杂谈"},
        {"tid": 242, "name": "粉丝创作"},
        {"tid": 137, "name": "明星综合"},
    ]},
    {"tid": 211, "name": "美食",     "sub": [
        {"tid": 76,  "name": "美食制作"},
        {"tid": 212, "name": "美食侦探"},
        {"tid": 213, "name": "美食测评"},
        {"tid": 214, "name": "田园美食"},
        {"tid": 215, "name": "美食记录"},
    ]},
    {"tid": 160, "name": "生活",     "sub": [
        {"tid": 138, "name": "搞笑"},
        {"tid": 250, "name": "出行"},
        {"tid": 251, "name": "三农"},
        {"tid": 239, "name": "家居房产"},
        {"tid": 161, "name": "手工"},
        {"tid": 162, "name": "绘画"},
        {"tid": 21,  "name": "日常"},
    ]},
    {"tid": 119, "name": "鬼畜",     "sub": [
        {"tid": 22,  "name": "鬼畜调教"},
        {"tid": 26,  "name": "音MAD"},
        {"tid": 126, "name": "人力VOCALOID"},
        {"tid": 216, "name": "鬼畜剧场"},
        {"tid": 127, "name": "教程演示"},
    ]},
    {"tid": 155, "name": "时尚",     "sub": [
        {"tid": 157, "name": "美妆护肤"},
        {"tid": 252, "name": "仿妆cos"},
        {"tid": 158, "name": "穿搭"},
        {"tid": 159, "name": "时尚潮流"},
    ]},
    {"tid": 234, "name": "运动",     "sub": [
        {"tid": 235, "name": "篮球"},
        {"tid": 249, "name": "足球"},
        {"tid": 164, "name": "健身"},
        {"tid": 236, "name": "竞技体育"},
        {"tid": 237, "name": "运动文化"},
        {"tid": 238, "name": "运动综合"},
    ]},
    {"tid": 223, "name": "汽车",     "sub": [
        {"tid": 245, "name": "赛车"},
        {"tid": 246, "name": "改装玩车"},
        {"tid": 247, "name": "新能源车"},
        {"tid": 248, "name": "房车"},
        {"tid": 240, "name": "摩托车"},
        {"tid": 227, "name": "购车攻略"},
        {"tid": 176, "name": "汽车生活"},
    ]},
    {"tid": 217, "name": "动物圈",   "sub": [
        {"tid": 218, "name": "喵星人"},
        {"tid": 219, "name": "汪星人"},
        {"tid": 220, "name": "大熊猫"},
        {"tid": 221, "name": "野生动物"},
        {"tid": 222, "name": "爬宠"},
        {"tid": 75,  "name": "动物综合"},
    ]},
    {"tid": 202, "name": "资讯",     "sub": [
        {"tid": 203, "name": "热点"},
        {"tid": 204, "name": "环球"},
        {"tid": 205, "name": "社会"},
        {"tid": 206, "name": "综合"},
    ]},
]


@app.route("/api/bilibili/zones", methods=["GET"])
def api_bilibili_zones():
    """返回B站分区列表，供前端选择"""
    return jsonify({"code": 0, "data": BILIBILI_ZONES})


# ============================================================
# 6. 设置管理 API（配置读写 / 缓存清理 / 导入导出）
# ============================================================

# 配置文件路径（JSON 格式，与程序同目录）
SETTINGS_FILE = DATA_DIR / "settings.json"

# 默认配置
DEFAULT_SETTINGS = {
    "browser_mode": "headed",           # headed(有头) / headless(无头)
    "concurrent_uploads": 2,            # asyncio 并发上传数（Semaphore 控制）
    "default_tags": ["热门推荐", "精彩瞬间", "干货分享"],  # 默认标签列表
    "auto_retry": True,                 # 上传失败是否自动重试
    "retry_count": 2,                   # 重试次数
    "schedule_default_hours": 2,        # 定时发布默认提前小时数
}


def load_settings():
    """读取配置文件，不存在则返回默认配置"""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            # 合并默认值（确保新增字段有默认值）
            merged = {**DEFAULT_SETTINGS, **saved}
            return merged
        except Exception:
            pass
    return dict(DEFAULT_SETTINGS)


def save_settings(data: dict):
    """写入配置文件"""
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@app.route("/api/settings", methods=["GET"])
def api_get_settings():
    """获取当前所有设置项"""
    settings = load_settings()

    # 计算缓存占用大小
    cache_size = 0
    if COOKIES_DIR.exists():
        for cf in COOKIES_DIR.rglob("*"):
            if cf.is_file():
                cache_size += cf.stat().st_size
    # 也计算持久化浏览器数据目录的大小
    if BROWSER_DATA_DIR.exists():
        for cf in BROWSER_DATA_DIR.rglob("*"):
            if cf.is_file():
                try:
                    cache_size += cf.stat().st_size
                except Exception:
                    pass

    # 格式化大小
    def fmt_size(b):
        for unit in ["B", "KB", "MB", "GB"]:
            if b < 1024:
                return f"{b:.1f} {unit}"
            b /= 1024
        return f"{b:.1f} TB"

    return jsonify({
        "code": 0,
        "data": {
            **settings,
            "cache_size_bytes": cache_size,
            "cache_size_human": fmt_size(cache_size),
            "cookies_dir": str(COOKIES_DIR),
            "settings_file": str(SETTINGS_FILE),
        }
    })


@app.route("/api/settings", methods=["POST"])
def api_save_settings():
    """
    保存设置项
    接收 JSON：{"browser_mode":"headed","concurrent_uploads":3,"default_tags":[...],...}
    只接受已知字段，忽略非法字段
    """
    data = request.get_json(force=True) or {}

    # 白名单过滤：只保存预定义的配置字段
    current = load_settings()
    allowed = list(DEFAULT_SETTINGS.keys())

    for key in allowed:
        if key in data:
            current[key] = data[key]

    save_settings(current)
    logging.info(f"[AutoSend] 设置已保存: {list(data.keys())}")
    return jsonify({"code": 0, "msg": "设置已保存"})


@app.route("/api/cache/clear", methods=["POST"])
def api_cache_clear():
    """
    清理缓存（Cookie 文件 + 浏览器临时数据）
    可选参数 {"clear_all": true} 清除全部，或 {"platforms": ["douyin"]} 清除指定平台
    """
    data = request.get_json(force=True) or {}
    clear_all = data.get("clear_all", False)
    target_platforms = data.get("platforms", [])

    removed_count = 0
    removed_files = []

    if not COOKIES_DIR.exists():
        return jsonify({"code": 0, "msg": "缓存目录不存在，无需清理"})

    if clear_all or not target_platforms:
        # 清除整个 cookies 目录下所有文件
        for cf in COOKIES_DIR.rglob("*.json"):
            try:
                cf.unlink()
                removed_files.append(str(cf))
                removed_count += 1
            except Exception as e:
                return jsonify({"code": 500, "msg": f"删除失败 {cf.name}: {e}"})
        # 同时清除全部持久化浏览器数据
        if BROWSER_DATA_DIR.exists():
            try:
                shutil.rmtree(str(BROWSER_DATA_DIR))
            except Exception:
                pass
    else:
        # 只清除指定平台的 cookie
        for plat_id in target_platforms:
            if plat_id not in PLATFORM_MAP:
                continue
            plat_dir = COOKIES_DIR / PLATFORM_MAP[plat_id]["uploader"]
            if plat_dir.exists():
                for cf in plat_dir.glob("*.json"):
                    try:
                        cf.unlink()
                        removed_files.append(str(cf))
                        removed_count += 1
                    except Exception as e:
                        return jsonify({"code": 500, "msg": f"删除失败 {cf.name}: {e}"})
            # 同时清除该平台的持久化浏览器数据
            _remove_browser_data(PLATFORM_MAP[plat_id]["uploader"])

    logging.info(f"[AutoSend] 缓存已清理: {removed_count} 个文件")
    return jsonify({
        "code": 0,
        "msg": f"已清理 {removed_count} 个缓存文件",
        "data": {"removed_count": removed_count, "files": [f.split("\\")[-1] for f in removed_files]}
    })


@app.route("/api/reset/all", methods=["POST"])
def api_reset_all():
    """一键清除所有使用痕迹（cookies + browser_data + settings + history + wallpapers）"""
    import shutil
    removed = {}

    # 1. 清除 cookies
    if COOKIES_DIR.exists():
        count = 0
        for cf in COOKIES_DIR.rglob("*"):
            if cf.is_file():
                try:
                    cf.unlink()
                    count += 1
                except Exception:
                    pass
        removed["cookies"] = count

    # 1.5 清除持久化浏览器用户数据目录
    if BROWSER_DATA_DIR.exists():
        try:
            shutil.rmtree(str(BROWSER_DATA_DIR))
            removed["browser_data"] = True
        except Exception:
            removed["browser_data"] = False

    # 2. 重置 settings.json 为默认值
    if SETTINGS_FILE.exists():
        try:
            SETTINGS_FILE.unlink()
            removed["settings"] = True
        except Exception:
            removed["settings"] = False

    # 3. 清除历史记录
    if HISTORY_FILE.exists():
        try:
            HISTORY_FILE.unlink()
            removed["history"] = True
        except Exception:
            removed["history"] = False

    # 4. 清除壁纸选择记录
    wp_json = DATA_DIR / "wallpaper_selection.json"
    if wp_json.exists():
        try:
            wp_json.unlink()
            removed["wallpapers"] = True
        except Exception:
            removed["wallpapers"] = False

    logging.info(f"[AutoSend] 全部数据已重置: {removed}")
    return jsonify({"code": 0, "msg": "所有使用痕迹已清除", "data": removed})


@app.route("/api/config/export", methods=["GET"])
def api_export_config():
    """
    导出完整配置（设置 + cookie 信息摘要）为 JSON 文件下载
    返回 JSON 数据供前端生成下载
    """
    settings = load_settings()

    # 收集各平台登录信息（不含敏感 cookie 内容）
    accounts_summary = []
    for key, info in PLATFORM_MAP.items():
        cookie_dir = COOKIES_DIR / info["uploader"]
        cookies = []
        if cookie_dir.exists():
            for cf in sorted(cookie_dir.glob("*.json")):
                stat = cf.stat()
                cookies.append({
                    "account": cf.stem,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "size": stat.st_size,
                })
        accounts_summary.append({
            "platform": key,
            "name": info["name"],
            "accounts": cookies,
        })

    export_data = {
        "version": "1.0",
        "export_time": datetime.now().isoformat(),
        "app": "Tujue AutoSend",
        "settings": settings,
        "accounts_summary": accounts_summary,
    }

    return jsonify({
        "code": 0,
        "data": export_data,
    })


@app.route("/api/config/import", methods=["POST"])
def api_import_config():
    """
    导入配置
    接收 JSON：{"settings": {...}} 或完整的导出文件内容
    注意：不会导入 cookie（需要重新扫码登录）
    """
    data = request.get_json(force=True) or {}

    if "settings" in data:
        # 只导入设置部分
        imported = data["settings"]
        current = load_settings()
        allowed = list(DEFAULT_SETTINGS.keys())
        for key in allowed:
            if key in imported:
                current[key] = imported[key]
        save_settings(current)
        logging.info(f"[AutoSend] 导入设置成功")
        return jsonify({"code": 0, "msg": "设置导入成功"})
    else:
        return jsonify({"code": 400, "msg": "无效的导入数据格式，缺少 settings 字段"})


# ============================================================
# 7. 发布历史记录 API（列表 / 筛选 / 重试 / 删除）
# ============================================================

# 历史记录文件路径
HISTORY_FILE = DATA_DIR / "history.json"


def load_history():
    """读取历史记录文件"""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_history(records):
    """写入历史记录文件"""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


@app.route("/api/history", methods=["GET"])
def api_get_history():
    """
    获取发布历史记录列表
    支持查询参数：
      - platform: 按平台筛选 (如 douyin)
      - status: 按状态筛选 (success/error/pending)
      - keyword: 关键词搜索（匹配标题/视频名）
      - page/size: 分页参数
    """
    records = load_history()

    # ---- 筛选 ----
    platform_filter = request.args.get("platform", "")
    status_filter = request.args.get("status", "")
    keyword = request.args.get("keyword", "").strip()

    if platform_filter:
        records = [r for r in records if platform_filter in r.get("platforms", [])]
    if status_filter:
        records = [r for r in records if r.get("status") == status_filter]
    if keyword:
        kw = keyword.lower()
        records = [r for r in records
                   if kw in r.get("title", "").lower() or kw in r.get("video_name", "").lower()]

    # ---- 排序（最新的在前）----
    records.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    # ---- 分页 ----
    page = int(request.args.get("page", 1))
    size = int(request.args.get("size", 20))
    total = len(records)
    start = (page - 1) * size
    end = start + size
    page_records = records[start:end]

    # ---- 统计各状态的计数 ----
    stats = {"total": total, "success": 0, "error": 0}
    for r in load_history():
        s = r.get("status", "")
        if s == "success":
            stats["success"] += 1
        elif s == "error":
            stats["error"] += 1

    return jsonify({
        "code": 0,
        "data": {
            "records": page_records,
            "total": total,
            "page": page,
            "size": size,
            "stats": stats,
        }
    })


@app.route("/api/history", methods=["POST"])
def api_add_history():
    """
    新增一条发布历史记录
    在上传任务提交时由后端自动调用记录
    """
    data = request.get_json(force=True) or {}

    record = {
        "id": uuid.uuid4().hex[:12],
        "video_path": data.get("video", ""),
        "video_name": data.get("video_name", ""),
        "title": data.get("title", ""),
        "desc": data.get("desc", ""),
        "tags": data.get("tags", []),
        "platforms": data.get("platforms", []),
        "status": data.get("status", "pending"),   # pending / success / error / partial
        "platform_details": data.get("platform_details", []),  # 各平台详细结果
        "schedule_time": data.get("schedule_time", ""),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "finished_at": None,
    }

    records = load_history()
    records.append(record)
    save_history(records)

    logging.info(f"[AutoSend] 历史记录已创建: {record['id']} - {record['title']}")
    return jsonify({"code": 0, "msg": "记录已保存", "data": record})


@app.route("/api/history/update/<record_id>", methods=["POST"])
def api_update_history(record_id):
    """更新某条历史记录的状态和详情（在上传完成时调用）"""
    data = request.get_json(force=True) or {}
    records = load_history()

    for r in records:
        if r["id"] == record_id:
            r["status"] = data.get("status", r.get("status", "pending"))
            if "platform_details" in data:
                r["platform_details"] = data["platform_details"]
            if data.get("status") in ("success", "error", "partial"):
                r["finished_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            break
    else:
        return jsonify({"code": 404, "msg": "记录不存在"})

    save_history(records)
    return jsonify({"code": 0, "msg": "记录已更新"})


@app.route("/api/history/retry/<record_id>", methods=["POST"])
def api_retry_history(record_id):
    """
    重试某条失败的历史记录
    返回原始上传参数供前端调用 doPublish
    """
    records = load_history()
    target = None

    for r in records:
        if r["id"] == record_id:
            target = r
            break

    if not target:
        return jsonify({"code": 404, "msg": "记录不存在"})

    video_path = target.get("video_path", "")
    if video_path and not os.path.exists(video_path):
        return jsonify({"code": 400, "msg": f"视频文件已不存在: {target.get('video_name', '')}"})

    return jsonify({
        "code": 0,
        "msg": "获取重试信息成功",
        "data": {
            "video": video_path,
            "title": target.get("title", ""),
            "desc": target.get("desc", ""),
            "tags": target.get("tags", []),
            "platforms": target.get("platforms", []),
            "schedule_time": "",
        }
    })


@app.route("/api/history/delete/<record_id>", methods=["POST"])
def api_delete_history(record_id):
    """删除一条历史记录"""
    records = load_history()
    new_records = [r for r in records if r["id"] != record_id]

    if len(new_records) == len(records):
        return jsonify({"code": 404, "msg": "记录不存在"})

    save_history(new_records)
    return jsonify({"code": 0, "msg": "记录已删除"})


# ============================================================
# 8. 自定义壁纸管理 API
# ============================================================

WALLPAPERS_DIR = DATA_DIR / "wallpapers"
WALLPAPERS_DIR.mkdir(parents=True, exist_ok=True)
MAX_WALLPAPERS = 10  # 自定义壁纸最多10张
MAX_CAROUSEL = 3     # 轮播最多选3张
ALLOWED_WP_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
WALLPAPER_SELECTION_FILE = DATA_DIR / "wallpaper_selection.json"


def _load_wp_selection():
    """读取壁纸轮播选择状态"""
    if WALLPAPER_SELECTION_FILE.exists():
        try:
            with open(WALLPAPER_SELECTION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # 默认：两张默认壁纸都选中
    return ["default_1", "default_2"]


def _save_wp_selection(selection):
    """保存壁纸轮播选择状态"""
    with open(WALLPAPER_SELECTION_FILE, "w", encoding="utf-8") as f:
        json.dump(selection, f, ensure_ascii=False, indent=2)


@app.route("/api/wallpapers", methods=["GET"])
def api_get_wallpapers():
    """获取壁纸列表：2张默认(base64) + 用户上传的(文件URL)，含轮播选择状态"""
    selection = _load_wp_selection()
    wallpapers = []
    # 默认壁纸（内嵌在 gui.html 中的 base64）
    wallpapers.append({"id": "default_1", "name": "默认壁纸 1", "type": "default", "url": None, "selected": "default_1" in selection})
    wallpapers.append({"id": "default_2", "name": "默认壁纸 2", "type": "default", "url": None, "selected": "default_2" in selection})
    # 自定义壁纸
    for f in sorted(WALLPAPERS_DIR.iterdir()):
        if f.is_file() and f.suffix.lower() in ALLOWED_WP_EXT:
            wp_id = f"custom_{f.name}"
            wallpapers.append({
                "id": wp_id,
                "name": f.stem,
                "type": "custom",
                "url": f"/wallpapers/{f.name}",
                "selected": wp_id in selection,
            })
    return jsonify({"code": 0, "data": wallpapers})


@app.route("/api/wallpapers/upload", methods=["POST"])
def api_upload_wallpaper():
    """上传自定义壁纸（最多MAX_WALLPAPERS张）"""
    if "file" not in request.files:
        return jsonify({"code": 400, "msg": "未找到文件"})
    file = request.files["file"]
    if not file.filename:
        return jsonify({"code": 400, "msg": "文件名为空"})

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_WP_EXT:
        return jsonify({"code": 400, "msg": f"不支持的格式 {ext}，仅支持 jpg/png/webp/bmp"})

    # 检查数量限制
    existing = [f for f in WALLPAPERS_DIR.iterdir() if f.is_file() and f.suffix.lower() in ALLOWED_WP_EXT]
    if len(existing) >= MAX_WALLPAPERS:
        return jsonify({"code": 400, "msg": f"自定义壁纸最多 {MAX_WALLPAPERS} 张，请先删除已有壁纸"})

    # 安全保存
    safe_name = secure_filename(file.filename) or f"custom{ext}"
    save_path = WALLPAPERS_DIR / safe_name
    file.save(str(save_path))
    logging.info(f"[AutoSend] 壁纸已保存: {save_path}")
    return jsonify({"code": 0, "msg": "壁纸上传成功", "data": {"url": f"/wallpapers/{safe_name}"}})


@app.route("/api/wallpapers/<path:filename>", methods=["DELETE"])
def api_delete_wallpaper(filename):
    """删除自定义壁纸"""
    safe_name = secure_filename(filename)
    target = WALLPAPERS_DIR / safe_name
    if not target.exists() or not target.is_file():
        return jsonify({"code": 404, "msg": "壁纸不存在"})
    try:
        target.unlink()
        logging.info(f"[AutoSend] 壁纸已删除: {target}")
        return jsonify({"code": 0, "msg": "壁纸已删除"})
    except Exception as e:
        return jsonify({"code": 500, "msg": f"删除失败: {e}"})


@app.route("/api/wallpapers/select", methods=["POST"])
def api_select_wallpapers():
    """设置轮播壁纸选择，最多3张"""
    data = request.get_json(force=True) or {}
    selected_ids = data.get("selected", [])
    if not isinstance(selected_ids, list):
        return jsonify({"code": 400, "msg": "selected 必须是数组"})
    if len(selected_ids) > MAX_CAROUSEL:
        return jsonify({"code": 400, "msg": f"轮播壁纸最多选 {MAX_CAROUSEL} 张"})
    # 验证 id 有效性
    valid_ids = {"default_1", "default_2"}
    for f in WALLPAPERS_DIR.iterdir():
        if f.is_file() and f.suffix.lower() in ALLOWED_WP_EXT:
            valid_ids.add(f"custom_{f.name}")
    for sid in selected_ids:
        if sid not in valid_ids:
            return jsonify({"code": 400, "msg": f"无效的壁纸 ID: {sid}"})
    _save_wp_selection(selected_ids)
    logging.info(f"[AutoSend] 壁纸轮播选择已更新: {selected_ids}")
    return jsonify({"code": 0, "msg": "轮播选择已更新", "data": {"selected": selected_ids}})


@app.route("/wallpapers/<path:filename>")
def serve_wallpaper(filename):
    """提供自定义壁纸文件"""
    return send_from_directory(str(WALLPAPERS_DIR), filename)


# ============================================================
# 启动参数
# ============================================================

if __name__ == "__main__":
    port = 18592
    print(f"""
╔══════════════════════════════════════╗
║   🚀 Tujue AutoSend 后端服务启动中   ║
║   http://127.0.0.1:{port}              ║
╚══════════════════════════════════════╝
""")
    app.run(host="127.0.0.1", port=port, debug=False)
