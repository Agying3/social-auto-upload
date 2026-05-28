# -*- coding: utf-8 -*-
"""
Tujue AutoSend - 主入口
启动 Flask 后端服务 → 打开 pywebview 桌面窗口
"""

import io
import sys
import os
import logging
import traceback
import threading
from pathlib import Path

# ============================================================
# 确保项目目录在搜索路径中
# ============================================================
PROJECT_DIR = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_DIR))

# ============================================================
# 修复 Windows 控制台编码，支持 emoji 和中文输出
# console=False 模式下 sys.stdout/stderr 可能为 None
# ============================================================
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    if hasattr(sys.stdout, 'buffer') and sys.stdout.buffer is not None:
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, 'buffer') and sys.stderr.buffer is not None:
        try:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
        except Exception:
            pass

# ============================================================
# 设置日志（冻结模式下写到 APPDATA 日志文件）
# ============================================================
if getattr(sys, 'frozen', False):
    from conf import DATA_DIR
    LOG_DIR = Path(DATA_DIR)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE = LOG_DIR / "tujue.log"

    # 文件日志 handler
    file_handler = logging.FileHandler(str(LOG_FILE), encoding="utf-8", mode="w")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)

    # 同时输出到 stderr（如果有）
    if sys.stderr is not None:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.INFO)
        root_logger.addHandler(console_handler)

    logging.info(f"TujueAutoSend 启动 (frozen mode)")
    logging.info(f"PROJECT_DIR = {PROJECT_DIR}")
    logging.info(f"DATA_DIR = {DATA_DIR}")
    logging.info(f"LOG_FILE = {LOG_FILE}")
else:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ============================================================
# 导入后端
# ============================================================
try:
    import backend
    logging.info("backend 模块加载成功")
except Exception as e:
    logging.error(f"backend 模块加载失败: {e}")
    logging.error(traceback.format_exc())
    raise

PORT = 18592


def start_flask():
    """在后台线程中启动 Flask 服务"""
    try:
        logging.info(f"Flask 服务启动中: http://127.0.0.1:{PORT}")
        # 使用 werkzeug 的 quiet 模式避免日志阻塞
        import werkzeug.serving
        werkzeug.serving._log_add_style = False  # 禁用颜色样式

        backend.app.run(
            host="127.0.0.1",
            port=PORT,
            debug=False,
            use_reloader=False,
            threaded=True,
        )
    except Exception as e:
        logging.error(f"Flask 服务异常: {e}")
        logging.error(traceback.format_exc())


def main():
    """主函数：启动服务并打开桌面窗口"""
    logging.info("""
╔══════════════════════════════════════════╗
║                                          ║
║     Tujue AutoSend  v1.0                ║
║     多平台视频一键发布工具                 ║
║                                          ║
╚══════════════════════════════════════════╝
    """)
    
    # ---- 在后台线程中启动 Flask 服务 ----
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()
    logging.info(f"Flask 后台线程已启动: http://127.0.0.1:{PORT}")

    # ---- 等待 Flask 就绪后再打开窗口 ----
    import time
    for i in range(30):  # 最多等 30 秒
        time.sleep(1)
        try:
            import urllib.request
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/platforms", timeout=2)
            logging.info(f"Flask 服务就绪 (等待了 {i+1} 秒)")
            break
        except Exception:
            if i == 29:
                logging.warning("Flask 服务未能在 30 秒内就绪")
            continue

    # ---- 使用 pywebview 打开桌面窗口 ----
    try:
        import webview
    except Exception as e:
        logging.error(f"pywebview 导入失败: {e}")
        return
    
    # ---- 窗口控制 JS API（暴露给前端调用）----
    class WindowApi:
        """无边框窗口控制 API —— 前端通过 window.pywebview.api.xxx() 调用"""
        def minimize(self):
            webview.windows[0].minimize()
        def close(self):
            webview.windows[0].destroy()

    api = WindowApi()  # 必须以实例传入，pywebview 不会自动实例化类

    # 创建窗口（frameless 模式）
    window = webview.create_window(
        title="Tujue AutoSend - 多平台视频一键发布",
        url=f"http://127.0.0.1:{PORT}",
        width=1100,
        height=780,
        min_size=(900, 600),
        frameless=True,
        easy_drag=True,
        shadow=False,
        transparent=False,
        background_color='#000000',  # fallback（transparent=True 会覆盖为 Color.Transparent）
        js_api=api,
    )
    
    logging.info("桌面窗口创建中...")
    webview.start(debug=False)
    
    logging.info("程序已退出")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f"主函数异常: {e}")
        logging.error(traceback.format_exc())
