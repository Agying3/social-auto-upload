# -*- coding: utf-8 -*-
"""
构建 GUI HTML（v4 - 对接后端 API 版）
将背景图 base64 嵌入，生成最终 gui.html
"""

import base64

def build():
    # 读取两张背景图
    with open("11.jpeg", "rb") as f:
        bg1 = base64.b64encode(f.read()).decode()
    with open("22.jpeg", "rb") as f:
        bg2 = base64.b64encode(f.read()).decode()

    html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🚀 Tujue AutoSend - 多平台视频一键发布</title>
<style>
/* ========== 全局重置 ========== */
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
::selection {{ background: rgba(99,102,241,0.35); color: #fff; }}
::-webkit-scrollbar {{ width: 6px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{
    background: rgba(255,255,255,0.12); border-radius: 3px;
}}
::-webkit-scrollbar-thumb:hover {{ background: rgba(255,255,255,0.2); }}

/* ====== 标题栏窗口按钮（ai0 PySide6 QSS 风格）====== */
.win-btn {{
    -webkit-app-region: no-drag;
    width: 28px; height: 28px; border-radius: 7px;
    background: transparent; border: 0.5px solid transparent;
    color: rgba(255,255,255,0.30); font-size: 14px; font-weight: 400;
    cursor: pointer; display: flex; align-items: center; justify-content: center;
    transition: all 0.15s;
    margin-left: 4px; padding: 0; line-height: 1;
}}
.win-btn:hover {{
    background: rgba(255,255,255,0.07); color: rgba(255,255,255,0.70);
    border-color: rgba(255,255,255,0.06);
}}
.win-btn:active {{ background: rgba(255,255,255,0.04); }}
.win-close:hover {{
    background: rgba(237,69,96,0.30); color: #ffb3bb;
    border-color: rgba(237,69,96,0.20);
}}

html {{
    width: 100vw; height: 100vh; margin: 0; padding: 0;
    overflow: hidden;
    background: #14161c;
}}
body {{
    font-family: "DengXian","Segoe UI","Microsoft YaHei",sans-serif;
    color: #fff; width: 100vw; min-height: 100vh; margin: 0; padding: 0;
    overflow: hidden;
    background: #14161c;
    -webkit-app-region: no-drag;
}}

/* ====== 内容滚动层 ====== */
.scroll-area {{
    position: absolute; inset: 0; z-index: 1;
    overflow-y: auto; overflow-x: hidden; scroll-behavior: smooth;
    padding-top: 50px;
}}
.scroll-area::-webkit-scrollbar {{ width: 3px; }}
.scroll-area::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,0.1); border-radius: 3px; }}
.scroll-area::-webkit-scrollbar-track {{ background: transparent; }}

/* ========== 壁纸轮播层 ========== */
#wallpaper-bg {{
    position: absolute; top: 0; left: 0; width: 100%; height: 100%;
    z-index: 0; overflow: hidden;
}}
#wallpaper-bg .wp {{
    position: absolute; top: 0; left: 0; width: 100%; height: 100%;
    background-size: cover; background-position: center;
    opacity: 0; transition: opacity 1.2s ease;
}}
#wallpaper-bg .wp.active {{ opacity: 1; }}
/* 暗角遮罩 */
#wallpaper-bg::after {{
    content:""; position:absolute; inset:0;
    background:
        linear-gradient(to bottom, rgba(0,0,0,0.15) 0%, transparent 15%, transparent 80%, rgba(0,0,0,0.4) 100%),
        radial-gradient(ellipse at center, transparent 30%, rgba(0,0,0,0.45) 100%);
    pointer-events: none;
}}

/* ========== 轮播指示器 ========== */
.wp-indicators {{
    position: fixed; bottom: 20px; right: 20px; z-index: 10;
    display: flex; gap: 8px;
}}
.wp-indicators span {{
    width: 8px; height: 8px; border-radius: 50%;
    background: rgba(255,255,255,0.3); cursor: pointer;
    transition: all 0.3s ease;
}}
.wp-indicators span.active {{ background: #fff; transform: scale(1.25); }}

/* ========== 主容器 ========== */
.app-container {{
    position: absolute; inset: 0; z-index: 1;
    overflow-y: auto; overflow-x: hidden; scroll-behavior: smooth;
    padding: 52px 20px 40px 20px;
    -webkit-app-region: no-drag;
}}

/* ========== 页面区域 ========== */
.page-section {{ display: none; }}
.page-section.active {{ display: block; }}

/* ========== 导航首页（Dashboard） ========== */
.page-home {{
    display: none;
    padding-top: 40px;
}}
.page-home.active {{ display: block; }}

/* 首页欢迎区 */
.home-welcome {{
    text-align: center; margin-bottom: 48px; padding-top: 20px;
}}
.home-welcome h1 {{
    font-size: 36px; font-weight: 800; letter-spacing: 4px;
    background: linear-gradient(135deg, #e0e7ff 0%, #a5b4fc 30%, #818cf8 60%, #c4b5fd 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text; margin-bottom: 12px;
    filter: drop-shadow(0 2px 12px rgba(129,140,248,0.25));
}}
.home-welcome p {{
    font-size: 14px; color: rgba(255,255,255,0.4); letter-spacing: 2px;
    font-weight: 300;
}}

/* 功能卡片网格 */
.nav-cards-grid {{
    display: grid; grid-template-columns: repeat(2, 1fr); gap: 22px;
    max-width: 800px; margin: 0 auto;
}}

/* 单个功能入口卡片 */
.nav-card {{
    position: relative; border-radius: 22px; padding: 36px 28px;
    cursor: pointer; text-align: center;
    border: 1px solid rgba(255,255,255,0.08);
    transition: all 0.4s cubic-bezier(.4,0,.2,1);
    overflow: hidden;
    box-shadow: 0 2px 16px rgba(0,0,0,0.15);
}}
.nav-card::before {{
    content: ""; position: absolute; inset: 0;
    background: linear-gradient(135deg, var(--nc-glow) 0%, transparent 60%);
    opacity: 0; transition: opacity 0.4s ease;
}}
/* 发光边框层 */
.nav-card::after {{
    content: ""; position: absolute; inset: -1px;
    border-radius: 22px;
    background: linear-gradient(135deg, var(--nc-accent), transparent 40%, transparent 60%, var(--nc-accent));
    opacity: 0; transition: opacity 0.4s ease;
    z-index: -1; filter: blur(8px);
}}
.nav-card:hover::before {{ opacity: 1; }}
.nav-card:hover::after {{ opacity: 0.6; }}
.nav-card:hover {{
    transform: translateY(-8px) scale(1.02);
    border-color: var(--nc-accent);
    box-shadow: 0 16px 48px rgba(0,0,0,0.3), 0 0 40px var(--nc-glow-alpha);
}}

/* 四张卡片各自的配色 */
.nav-card.nc-publish {{
    --nc-bg: rgba(99,102,241,0.12);
    --nc-glow: rgba(99,102,241,0.25);
    --nc-accent: rgba(99,102,241,0.4);
    --nc-glow-alpha: rgba(99,102,241,0.12);
    background: linear-gradient(145deg, rgba(99,102,241,0.15), rgba(79,70,229,0.08));
}}
.nav-card.nc-login {{
    --nc-bg: rgba(16,185,129,0.12);
    --nc-glow: rgba(16,185,129,0.25);
    --nc-accent: rgba(16,185,129,0.4);
    --nc-glow-alpha: rgba(16,185,129,0.12);
    background: linear-gradient(145deg, rgba(16,185,129,0.15), rgba(5,150,105,0.08));
}}
.nav-card.nc-history {{
    --nc-bg: rgba(245,158,11,0.12);
    --nc-glow: rgba(245,158,11,0.25);
    --nc-accent: rgba(245,158,11,0.4);
    --nc-glow-alpha: rgba(245,158,11,0.12);
    background: linear-gradient(145deg, rgba(245,158,11,0.15), rgba(217,119,6,0.08));
}}
.nav-card.nc-settings {{
    --nc-bg: rgba(139,92,246,0.12);
    --nc-glow: rgba(139,92,246,0.25);
    --nc-accent: rgba(139,92,246,0.4);
    --nc-glow-alpha: rgba(139,92,246,0.12);
    background: linear-gradient(145deg, rgba(139,92,246,0.15), rgba(124,58,237,0.08));
}}

/* 卡片图标 */
.nav-card-icon {{
    font-size: 48px; margin-bottom: 16px; display: block;
    filter: drop-shadow(0 2px 8px rgba(0,0,0,0.3));
    transition: transform 0.35s ease;
}}
.nav-card:hover .nav-card-icon {{ transform: scale(1.15) translateY(-4px); }}

/* 卡片标题和描述 */
.nav-card-title {{
    font-size: 19px; font-weight: 600; color: #fff;
    margin-bottom: 8px; letter-spacing: 1px;
}}
.nav-card-desc {{
    font-size: 13px; color: rgba(255,255,255,0.45);
    line-height: 1.5; letter-spacing: 0.5px;
}}

/* 子页面顶部的返回条 */
.subpage-header {{
    display: flex; align-items: center; gap: 14px; margin-bottom: 22px;
}}
.back-home-btn {{
    display: inline-flex; align-items: center; gap: 6px;
    padding: 8px 20px; border-radius: 22px; cursor: pointer;
    font-size: 13px; font-weight: 500; color: rgba(255,255,255,0.55);
    background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
    transition: all 0.25s cubic-bezier(.4,0,.2,1); user-select: none;
    box-shadow: 0 1px 4px rgba(0,0,0,0.1);
}}
.back-home-btn:hover {{
    background: rgba(255,255,255,0.1); color: #fff;
    border-color: rgba(255,255,255,0.2);
    transform: translateX(-3px);
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}}
.back-home-btn.disabled {{
    cursor: not-allowed;
    background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.65);
    border-color: rgba(255,255,255,0.14);
}}
@keyframes btnShake {{
    0%,100%{{transform:translateX(-3px)}}
    20%{{transform:translateX(1px)}}
    40%{{transform:translateX(-4px)}}
    60%{{transform:translateX(2px)}}
    80%{{transform:translateX(-1px)}}
}}
.back-home-btn.shaking {{ animation:btnShake 0.35s ease; }}

/* ========== 卡片通用样式 ========== */
.card {{
    background: rgba(20,22,30,0.92);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 20px; padding: 24px; margin-bottom: 18px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.06);
    transition: border-color 0.3s, box-shadow 0.3s;
}}
.card:hover {{
    border-color: rgba(255,255,255,0.18);
    box-shadow: 0 8px 32px rgba(0,0,0,0.28), inset 0 1px 0 rgba(255,255,255,0.08);
}}

.card-title {{
    font-size: 16px; font-weight: 600; margin-bottom: 16px;
    display: flex; align-items: center; gap: 8px;
    color: rgba(255,255,255,0.95);
    letter-spacing: 0.3px;
}}
.card-title .icon {{ font-size: 19px; }}

/* ========== 视频上传区 ========== */
.upload-zone {{
    border: 2px dashed rgba(255,255,255,0.18); border-radius: 16px;
    padding: 38px; text-align: center; cursor: pointer;
    transition: all 0.35s ease; position: relative;
    background: rgba(255,255,255,0.02);
    animation: uploadBreathe 3s ease-in-out infinite;
}}
@keyframes uploadBreathe {{
    0%, 100% {{ border-color: rgba(255,255,255,0.15); }}
    50% {{ border-color: rgba(99,102,241,0.3); }}
}}
.upload-zone:hover {{
    border-color: rgba(99,102,241,0.55); background: rgba(99,102,241,0.05);
    animation: none;
    box-shadow: inset 0 0 30px rgba(99,102,241,0.06);
}}
.upload-zone.has-file {{
    border-style: solid; border-color: rgba(34,197,94,0.35);
    padding: 18px; text-align: left; animation: none;
}}
.upload-zone input[type="file"] {{ display: none; }}

.video-preview {{
    max-width: 100%; max-height: 260px; border-radius: 10px;
    margin-top: 12px; display: none;
}}
.upload-zone.has-file .video-preview {{ display: inline-block; }}

/* ========== 输入框 ========== */
.form-group {{ margin-bottom: 14px; }}
.form-group label {{
    font-size: 13px; color: rgba(255,255,255,0.55); margin-bottom: 6px;
    display: block; font-weight: 500;
}}
.input-field {{
    width: 100%; padding: 11px 15px; border-radius: 12px;
    background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12);
    color: #fff; font-size: 14px; outline: none; transition: all 0.3s;
    font-family: inherit;
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.15);
}}
.input-field:focus {{
    border-color: rgba(99,102,241,0.6);
    background: rgba(255,255,255,0.09);
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.1), 0 0 0 3px rgba(99,102,241,0.12);
}}
.input-field::placeholder {{ color: rgba(255,255,255,0.25); }}
textarea.input-field {{ resize: vertical; min-height: 80px; line-height: 1.6; }}
/* ========== 自定义下拉菜单 ========== */
.custom-select-wrap {{
    position: relative; display: inline-block; width: 100%;
}}
.custom-select-wrap select {{ display: none !important; }}
.custom-select-trigger {{
    width: 100%; padding: 11px 36px 11px 15px; border-radius: 11px;
    background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.14);
    color: #fff; font-size: 14px; cursor: pointer; outline: none;
    transition: all 0.25s; font-family: inherit; user-select: none;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    box-sizing: border-box;
}}
.custom-select-trigger:focus,
.custom-select-trigger.open {{
    border-color: rgba(99,102,241,0.55);
    background: rgba(255,255,255,0.1);
}}
.custom-select-trigger::after {{
    content: ''; position: absolute; right: 14px; top: 50%;
    transform: translateY(-50%); pointer-events: none;
    border-left: 5px solid transparent; border-right: 5px solid transparent;
    border-top: 6px solid rgba(255,255,255,0.5);
    transition: transform 0.2s;
}}
.custom-select-trigger.open::after {{
    transform: translateY(-50%) rotate(180deg);
}}
.custom-select-panel {{
    position: absolute; top: calc(100% + 4px); left: 0; right: 0;
    z-index: 9999; border-radius: 12px; overflow: hidden;
    background: rgba(18,18,32,0.78);
    border: 1px solid rgba(255,255,255,0.15);
    box-shadow: 0 8px 32px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.06);
    max-height: 240px; overflow-y: auto;
    opacity: 0; transform: translateY(-12px) scaleY(0.88);
    transform-origin: top center;
    transition: opacity 0.3s cubic-bezier(.4,0,.2,1), transform 0.3s cubic-bezier(.34,1.56,.64,1);
    pointer-events: none;
}}
.custom-select-panel.open {{
    opacity: 1; transform: translateY(0) scaleY(1);
    pointer-events: auto;
}}
/* 向上弹出模式 */
.custom-select-wrap.dropup .custom-select-panel {{
    top: auto; bottom: calc(100% + 4px);
    transform-origin: bottom center;
    transform: translateY(12px) scaleY(0.88);
}}
.custom-select-wrap.dropup .custom-select-panel.open {{
    transform: translateY(0) scaleY(1);
}}
.custom-select-option {{
    padding: 9px 15px; color: rgba(255,255,255,0.92); font-size: 13px;
    cursor: pointer; transition: background 0.15s;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    text-shadow: 0 1px 3px rgba(0,0,0,0.5);
}}
.custom-select-option:hover {{
    background: rgba(99,102,241,0.22); color: #fff;
}}
.custom-select-option.selected {{
    background: rgba(99,102,241,0.18); color: #a5b4fc;
}}
/* 小尺寸下拉（历史筛选等） */
.custom-select-wrap.sm .custom-select-trigger {{
    padding: 7px 28px 7px 10px; font-size: 12px; border-radius: 8px;
}}
.custom-select-wrap.sm .custom-select-option {{
    padding: 7px 10px; font-size: 12px;
}}

/* ========== 标签选择器 ========== */
.tags-row {{ display: flex; gap: 7px; flex-wrap: wrap; margin-top: 8px; }}
.tag-pill {{
    padding: 5px 14px; border-radius: 18px; font-size: 12px; cursor: pointer;
    background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.55);
    border: 1px solid rgba(255,255,255,0.1);
    transition: all 0.25s cubic-bezier(.4,0,.2,1); user-select: none;
}}
.tag-pill:hover {{
    background: rgba(255,255,255,0.12); border-color: rgba(255,255,255,0.2);
    transform: translateY(-1px);
}}
.tag-pill.selected {{
    background: rgba(99,102,241,0.25); color: #c7d2fe;
    border-color: rgba(99,102,241,0.5);
    box-shadow: 0 0 12px rgba(99,102,241,0.12);
}}
.custom-tag-input {{
    padding: 5px 12px; border-radius: 17px; font-size: 12px;
    background: rgba(255,255,255,0.06); border: 1px dashed rgba(255,255,255,0.25);
    color: #fff; outline: none; width: 120px; transition: all 0.25s;
    font-family: inherit;
}}
.custom-tag-input:focus {{ border-color: rgba(99,102,241,0.5); }}
.custom-tag-input::placeholder {{ color: rgba(255,255,255,0.25); }}

/* ========== 平台选择网格 ========== */
.platform-grid {{
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;
}}
.platform-btn {{
    padding: 14px; border-radius: 14px; cursor: pointer;
    text-align: center; font-size: 14px; font-weight: 500;
    background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
    color: rgba(255,255,255,0.65); transition: all 0.3s cubic-bezier(.4,0,.2,1); user-select: none;
    position: relative; overflow: hidden;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
}}
.platform-btn:hover {{
    background: rgba(255,255,255,0.1); border-color: rgba(255,255,255,0.2);
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0,0,0,0.2);
}}
.platform-btn.selected {{
    background: rgba(99,102,241,0.22); border-color: rgba(99,102,241,0.45);
    color: #e0e7ff; box-shadow: 0 0 20px rgba(99,102,241,0.12), inset 0 1px 0 rgba(255,255,255,0.08);
}}
/* 选中状态光晕 */
.platform-btn.selected::after {{
    content: ""; position: absolute; inset: -1px;
    border-radius: 14px;
    background: linear-gradient(135deg, rgba(99,102,241,0.15), transparent 50%);
    pointer-events: none;
}}
.platform-btn .p-icon {{
    width: 32px; height: 32px; margin: 0 auto 6px;
    display: flex; align-items: center; justify-content: center;
    border-radius: 10px; overflow: hidden;
}}
.platform-btn .p-icon svg {{
    width: 32px; height: 32px; border-radius: 8px;
}}
.platform-btn .p-icon img {{
    width: 32px; height: 32px; border-radius: 8px; object-fit: cover;
}}
.platform-btn .p-name {{ margin-bottom: 3px; }}
.platform-btn .p-status {{
    font-size: 11px; margin-top: 3px; display: flex; align-items: center; justify-content: center; gap: 4px;
}}
.dot {{ width: 7px; height: 7px; border-radius: 50%; display: inline-block; }}
.dot.green {{ background: #22c55e; }}
.dot.red {{ background: #ef4444; }}
.dot.gray {{ background: rgba(255,255,255,0.25); }}
.unsupported-badge {{
    font-size: 9px; padding: 1px 6px; border-radius: 6px;
    background: rgba(239,68,68,0.15); color: #fca5a5;
    position: absolute; top: 6px; right: 6px;
}}

/* ========== 定时发布开关 ========== */
@keyframes knob-pop {{
    0%   {{ transform: scale(1); }}
    40%  {{ transform: scale(1.25); }}
    70%  {{ transform: scale(0.9); }}
    100% {{ transform: scale(1); }}
}}
@keyframes toggle-glow {{
    0%, 100% {{ box-shadow: 0 0 8px rgba(99,102,241,0.35); }}
    50%       {{ box-shadow: 0 0 18px rgba(99,102,241,0.65); }}
}}
@keyframes row-light {{
    from {{ background: rgba(99,102,241,0.08); border-color: rgba(129,140,248,0.25); }}
    to   {{ background: rgba(255,255,255,0.03); border-color: rgba(255,255,255,0.08); }}
}}
.schedule-toggle {{
    display: flex; align-items: center; gap: 14px;
    padding: 14px 18px; border-radius: 14px;
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08);
    transition: background 0.4s ease, border-color 0.4s ease;
}}
.schedule-toggle.sched-on {{
    background: rgba(99,102,241,0.08);
    border-color: rgba(129,140,248,0.25);
}}
/* 状态文字 */
.sched-label {{
    font-size: 14px; font-weight: 500;
    transition: color 0.3s ease;
}}
.schedule-toggle.sched-on .sched-label {{ color: #a5b4fc; }}

/* 开/关 徽标 */
.sched-badge {{
    font-size: 11px; font-weight: 700; letter-spacing: 0.5px;
    padding: 2px 7px; border-radius: 20px;
    transition: all 0.3s ease;
    background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.35);
    border: 1px solid rgba(255,255,255,0.12);
}}
.schedule-toggle.sched-on .sched-badge {{
    background: rgba(99,102,241,0.2); color: #a5b4fc;
    border-color: rgba(129,140,248,0.35);
}}

/* 开关轨道 */
.toggle-switch {{
    flex-shrink: 0;
    width: 46px; height: 26px; border-radius: 13px; position: relative;
    cursor: pointer;
    background: rgba(120,125,140,0.45);
    border: 1px solid rgba(255,255,255,0.2);
    transition: background 0.35s cubic-bezier(.4,0,.2,1),
                border-color 0.35s ease,
                box-shadow 0.35s ease;
    box-shadow: inset 0 1px 4px rgba(0,0,0,0.3);
}}
.toggle-switch.on {{
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    border-color: rgba(139,92,246,0.5);
    animation: toggle-glow 2s ease-in-out infinite;
}}
/* 轨道内小图标 */
.toggle-switch::before {{
    content: "✕";
    position: absolute; right: 6px; top: 50%;
    transform: translateY(-50%);
    font-size: 9px; color: rgba(255,255,255,0.35);
    transition: opacity 0.2s ease;
    line-height: 1;
}}
.toggle-switch.on::before {{
    content: "✓";
    left: 6px; right: auto;
    font-size: 10px; color: rgba(255,255,255,0.85);
}}
/* 圆形滑块 */
.toggle-switch .knob {{
    width: 20px; height: 20px; border-radius: 50%;
    background: #fff; position: absolute; top: 2px; left: 2px;
    transition: left 0.35s cubic-bezier(.4,0,.2,1);
    box-shadow: 0 1px 5px rgba(0,0,0,0.35);
    z-index: 1;
}}
.toggle-switch.on .knob {{ left: 22px; }}
.toggle-switch .knob.pop {{ animation: knob-pop 0.35s cubic-bezier(.4,0,.2,1); }}
.datetime-picker {{
    padding: 8px 14px; border-radius: 9px; font-size: 13px;
    background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.15);
    color: rgba(255,255,255,0.9); outline: none; font-family: inherit;
    display: none; color-scheme: dark;
    backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
}}
.datetime-picker:focus {{
    border-color: rgba(129,140,248,0.5);
    box-shadow: 0 0 0 2px rgba(99,102,241,0.15);
    background: rgba(255,255,255,0.1);
}}
.datetime-picker::-webkit-calendar-picker-indicator {{
    filter: invert(0.85) brightness(1.2);
    cursor: pointer; opacity: 0.75;
}}
.datetime-picker.show {{ display: inline-block; }}

/* ========== 发布按钮 ========== */
.publish-btn {{
    display: flex; align-items: center; justify-content: center; gap: 10px;
    width: 100%; padding: 15px 28px; border-radius: 14px; font-size: 15px; font-weight: 600;
    cursor: pointer; border: 1.5px solid rgba(129,140,248,0.35); color: #fff; letter-spacing: 1.5px;
    background: linear-gradient(135deg, rgba(99,102,241,0.2) 0%, rgba(139,92,246,0.15) 50%, rgba(99,102,241,0.2) 100%);
    transition: all 0.4s cubic-bezier(.4,0,.2,1); position: relative; overflow: hidden;
    font-family: inherit;
    box-shadow: 0 2px 16px rgba(99,102,241,0.12), inset 0 1px 0 rgba(255,255,255,0.06);
}}
.publish-btn:hover {{
    transform: translateY(-2px);
    border-color: rgba(129,140,248,0.6);
    background: linear-gradient(135deg, rgba(99,102,241,0.35) 0%, rgba(139,92,246,0.25) 50%, rgba(99,102,241,0.35) 100%);
    box-shadow: 0 8px 32px rgba(99,102,241,0.25), 0 0 40px rgba(139,92,246,0.1), inset 0 1px 0 rgba(255,255,255,0.1);
}}
.publish-btn:active {{ transform: translateY(0); filter: brightness(0.95); }}
.publish-btn:disabled {{
    background: rgba(255,255,255,0.05); cursor: not-allowed; border-color: rgba(255,255,255,0.08);
    box-shadow: none; transform: none; filter: none; letter-spacing: 1px;
}}
.publish-btn .btn-text {{ position: relative; z-index: 1; display:flex; align-items:center; gap:10px; }}
.publish-btn .btn-arrow {{
    display:inline-block; transition: transform 0.3s ease; font-size:18px; opacity:0.7;
}}
.publish-btn:hover .btn-arrow {{ transform: translateX(4px); opacity:1; }}
/* 按钮边框流光 */
.publish-btn:not(:disabled)::before {{
    content: ""; position: absolute; inset: -1px;
    border-radius: 15px; padding: 1.5px;
    background: linear-gradient(90deg, rgba(99,102,241,0.3), rgba(167,139,250,0.6), rgba(139,92,246,0.3), rgba(99,102,241,0.3));
    background-size: 300% 100%;
    animation: btnBorderFlow 3s linear infinite;
    -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
    -webkit-mask-composite: xor; mask-composite: exclude;
    pointer-events: none; z-index: 0;
}}
@keyframes btnBorderFlow {{
    0% {{ background-position: 0% 50%; }}
    100% {{ background-position: 300% 50%; }}
}}

/* ========== 进度面板 ========== */
.progress-panel {{
    margin-top: 18px;
}}
.progress-item {{
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 16px; border-radius: 12px; margin-bottom: 8px;
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
    transition: all 0.3s;
}}
.progress-item .pi-left {{
    display: flex; align-items: center; gap: 10px; font-size: 14px;
}}
.pi-status {{
    font-size: 12px; padding: 3px 10px; border-radius: 8px;
    font-weight: 600; letter-spacing: 0.3px;
}}
.pi-status.uploading {{ background: rgba(59,130,246,0.18); color: #93c5fd; }}
.pi-status.success {{ background: rgba(34,197,94,0.18); color: #86efac; }}
.pi-status.error {{ background: rgba(239,68,68,0.18); color: #fca5a5; }}
.pi-status.pending {{ background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.35); }}

/* ========== 底部状态栏 ========== */
.status-bar {{
    position: fixed; bottom: 0; left: 0; right: 0; z-index: 20;
    padding: 10px 24px; display: flex; justify-content: space-between;
    align-items: center; font-size: 12px; color: rgba(255,255,255,0.3);
    background: linear-gradient(to top, rgba(0,0,0,0.65) 0%, rgba(0,0,0,0.3) 60%, transparent 100%);
    pointer-events: none; letter-spacing: 0.3px;
}}
.status-bar .stat-item {{
    display: flex; align-items: center; gap: 5px;
}}
.status-bar b {{ color: rgba(255,255,255,0.6); font-weight: 600; }}

/* ========== 登录页面 ========== */
.login-grid {{
    display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px;
}}
.login-card {{
    background: rgba(20,22,30,0.88);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 18px; padding: 22px; text-align: center;
    transition: all 0.3s cubic-bezier(.4,0,.2,1);
    box-shadow: 0 2px 12px rgba(0,0,0,0.15);
}}
.login-card:hover {{
    border-color: rgba(99,102,241,0.3);
    transform: translateY(-3px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.25);
}}
.login-card .lc-icon {{ font-size: 36px; margin-bottom: 10px; }}
.login-card .lc-name {{
    font-size: 17px; font-weight: 600; margin-bottom: 6px;
}}
.login-card .lc-desc {{ font-size: 12px; color: rgba(255,255,255,0.4); margin-bottom: 14px; }}
.login-btn {{
    padding: 9px 28px; border-radius: 20px; font-size: 13px; font-weight: 500;
    cursor: pointer; border: none; color: #fff; transition: all 0.25s;
    background: rgba(99,102,241,0.35); border: 1px solid rgba(99,102,241,0.4);
    font-family: inherit;
}}
.login-btn:hover {{ background: rgba(99,102,241,0.55); }}
.login-btn.logged-in {{
    background: rgba(34,197,94,0.2); border-color: rgba(34,197,94,0.35);
    color: #86efac; cursor: default;
}}
.qrcode-modal {{
    display: none; position: fixed; inset: 0; z-index: 100;
    background: rgba(0,0,0,0.82); justify-content: center; align-items: center;
}}
.qrcode-modal.show {{ display: flex; }}
.qrcode-content {{
    background: rgba(25,27,38,0.92); border: 1px solid rgba(255,255,255,0.12);
    border-radius: 22px; padding: 32px; text-align: center; max-width: 380px;
    box-shadow: 0 16px 64px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.05);
}}
.qrcode-content img {{
    max-width: 220px; border-radius: 12px; margin: 14px 0;
}}
.qrcode-content p {{ color: rgba(255,255,255,0.5); font-size: 13px; }}

/* ========== Toast 提示 ========== */
.toast {{
    position: fixed; top: 24px; left: 50%; transform: translateX(-50%) translateY(-20px);
    padding: 12px 28px; border-radius: 14px; font-size: 14px; font-weight: 600;
    z-index: 200; opacity: 0; transition: all 0.35s ease;
    pointer-events: none; white-space: nowrap;
    border: 1px solid rgba(255,255,255,0.15);
    letter-spacing: 0.5px;
}}
.toast.show {{ opacity: 1; transform: translateX(-50%) translateY(0); }}
.toast.success {{ background: rgba(34,197,94,0.92); color: #fff; box-shadow: 0 4px 20px rgba(34,197,94,0.25); }}
.toast.error {{ background: rgba(239,68,68,0.92); color: #fff; box-shadow: 0 4px 20px rgba(239,68,68,0.25); }}
.toast.info {{ background: rgba(59,130,246,0.92); color: #fff; box-shadow: 0 4px 20px rgba(59,130,246,0.25); }}

/* ========== 动画 ========== */
@keyframes fadeInUp {{
    from {{ opacity: 0; transform: translateY(20px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}
.card {{ animation: fadeInUp 0.45s cubic-bezier(.4,0,.2,1) both; }}
.card:nth-child(2) {{ animation-delay: 0.06s; }}
.card:nth-child(3) {{ animation-delay: 0.12s; }}
.card:nth-child(4) {{ animation-delay: 0.18s; }}
.card:nth-child(5) {{ animation-delay: 0.24s; }}
/* 页面切换过渡 —— 纯 transform 动画，避免 opacity 触发重绘 */
.page-section.active {{
    animation: pageSlideIn 0.28s cubic-bezier(.25,.46,.45,.94) both;
}}
.page-home.active {{
    /* 首页不需要入场动画，直接显示 */
}}
@keyframes pageSlideIn {{
    from {{ opacity: 0; transform: translateY(8px) scale(0.995); }}
    to   {{ opacity: 1; transform: translateY(0) scale(1); }}
}}

/* ========== 登录管理页样式 ========== */
/* 平台卡片 */
#platformCards .plat-card {{
    background: rgba(255,255,255,0.035);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 18px;
    padding: 18px;
    transition: all 0.3s cubic-bezier(.4,0,.2,1);
    box-shadow: 0 2px 12px rgba(0,0,0,0.1);
}}
#platformCards .plat-card:hover {{
    background: rgba(255,255,255,0.065);
    border-color: rgba(99,102,241,0.3);
    transform: translateY(-3px);
    box-shadow: 0 8px 28px rgba(0,0,0,0.22), 0 0 20px rgba(99,102,241,0.08);
}}

/* 卡片头部：图标+名称+状态徽章 */
.pch-wrap {{ display:flex; align-items:center; justify-content:space-between; margin-bottom:14px; }}
.pch-left {{ display:flex; align-items:center; gap:10px; }}
.pch-icon {{
    width:40px; height:40px; border-radius:10px;
    display:flex; align-items:center; justify-content:center;
    flex-shrink:0; overflow:visible;
}}
.pch-icon svg {{
    width:34px; height:34px;
}}
.pch-name {{ font-size:16px; font-weight:700; color:#fff; }}
.pch-nickname {{ font-size:11px; color:rgba(255,255,255,0.45); margin-top:1px; max-width:140px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.pch-badge {{
    font-size:11px; padding:3px 10px; border-radius:20px;
    font-weight:600; letter-spacing:0.5px;
}}
.badge-in  {{ background:rgba(34,197,94,0.2); color:#4ade80; border:1px solid rgba(34,197,94,0.3); }}
.badge-out {{ background:rgba(239,68,68,0.15); color:#f87171; border:1px solid rgba(239,68,68,0.25); }}
.badge-na  {{ background:rgba(156,163,175,0.15); color:#9ca3af; border:1px solid rgba(156,163,175,0.2); }}
.badge-expired {{ background:rgba(251,191,36,0.2); color:#fbbf24; border:1px solid rgba(251,191,36,0.3); }}

/* 账号列表项 */
.acct-list {{ margin-top:4px; }}
.acct-item {{
    display:flex; align-items:center; justify-content:space-between;
    padding:9px 12px; margin-top:6px;
    background:rgba(0,0,0,0.22); border-radius:10px;
    border:1px solid rgba(255,255,255,0.05);
}}
.acct-info {{ display:flex; align-items:center; gap:8px; }}
.acct-avatar {{
    width:28px; height:28px; border-radius:50%;
    background:linear-gradient(135deg,#6366f1,#8b5cf6);
    display:flex; align-items:center; justify-content:center;
    font-size:11px; color:#fff; flex-shrink:0;
}}
.acct-detail .acct-name {{ font-size:13px; color:rgba(255,255,255,0.88); }}
.acct-detail .acct-time {{ font-size:11px; color:rgba(255,255,255,0.33); }}
.btn-logout-sm {{
    font-size:11px; padding:4px 12px; border-radius:8px;
    background:rgba(239,68,68,0.13); color:#f87171;
    border:1px solid rgba(239,68,68,0.22); cursor:pointer; transition:all 0.2s;
}}
.btn-logout-sm:hover {{ background:rgba(239,68,68,0.28); }}

/* 无账号提示 */
.no-acct-hint {{ text-align:center; padding:16px; color:rgba(255,255,255,0.32); font-size:13px; }}

/* 卡底部操作按钮 */
.pca-actions {{ display:flex; gap:8px; margin-top:14px; padding-top:12px; border-top:1px solid rgba(255,255,255,0.06); }}
.btn-login-card {{
    flex:1; padding:10px; border-radius:12px; font-size:13px; font-weight:600;
    cursor:pointer; transition:all 0.3s cubic-bezier(.4,0,.2,1); text-align:center; border:none; outline:none;
    background:linear-gradient(135deg,rgba(99,102,241,0.22),rgba(139,92,246,0.15));
    border:1px solid rgba(99,102,241,0.25); color:#fff;
    letter-spacing: 0.5px;
}}
.btn-login-card:hover {{
    background:linear-gradient(135deg,rgba(99,102,241,0.38),rgba(139,92,246,0.3));
    box-shadow:0 4px 20px rgba(99,102,241,0.2);
    transform: translateY(-1px);
}}
.btn-login-card:disabled {{ opacity:0.38; cursor:not-allowed; }}

/* 刷新按钮动画 */
#btnRefreshLogin:hover {{ background:rgba(255,255,255,0.14); color:#fff; }}
#btnRefreshLogin.spinning #refreshIcon {{ animation: spin 0.8s linear infinite; }}
#btnRefreshPublish:hover {{ background:rgba(255,255,255,0.14); color:#fff; }}
#btnRefreshPublish.spinning #refreshPublishIcon {{ animation: spin 0.8s linear infinite; }}
/* 点击刷新时图标单次旋转 */
#refreshIcon.click-spin, #refreshPublishIcon.click-spin {{
    animation: spinOnce 0.5s cubic-bezier(.4,0,.2,1);
}}
@keyframes spinOnce {{
    from {{ transform: rotate(0deg); }}
    to {{ transform: rotate(360deg); }}
}}

/* 登录弹窗动画 */
#loginModal {{ position:fixed !important; z-index:2000 !important; }}
.spin-icon {{ animation: spin 1.5s linear infinite; }}
@keyframes spin {{ from{{transform:rotate(0deg)}} to{{transform:rotate(360deg)}} }}
.lm-success .spin-icon {{ animation:none; color:#4ade80; }}
.lm-failed .spin-icon {{ animation:none; color:#f87171; }}


/* ========== 设置页样式 ========== */
/* 滑块控件 */
.slider-wrap {{ display:flex; align-items:center; gap:10px; margin-top:6px; }}
.range-slider {{
    flex:1; height:6px; -webkit-appearance:none; appearance:none;
    background:rgba(255,255,255,0.12); border-radius:3px; outline:none;
    transition: background 0.2s;
}}
.range-slider:hover {{
    background:rgba(255,255,255,0.18);
}}
.range-slider::-webkit-slider-thumb {{
    -webkit-appearance:none; width:20px; height:20px;
    background:linear-gradient(135deg,#6366f1,#8b5cf6); border-radius:50%;
    cursor:pointer; box-shadow:0 2px 10px rgba(99,102,241,0.4);
    transition: transform 0.2s, box-shadow 0.2s;
}}
.range-slider::-webkit-slider-thumb:hover {{
    transform: scale(1.15);
    box-shadow:0 3px 14px rgba(99,102,241,0.5);
}}
.slider-val {{ font-size:22px; font-weight:800; color:#a5b4fc; min-width:24px;text-align:center; }}
.slider-unit {{ font-size:11px; color:rgba(255,255,255,0.35); }}

/* 字段提示 */
.field-hint {{ display:block; font-size:11px; color:rgba(255,255,255,0.3); margin-top:4px; }}

/* 小型开关 */
.toggle-row {{ display:flex; align-items:center; margin-top:6px; cursor:pointer; }}
.toggle-switch-sm {{
    width:42px; height:24px; border-radius:12px; position:relative;
    background:rgba(255,255,255,0.1); transition:all 0.3s cubic-bezier(.4,0,.2,1); flex-shrink:0;
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.2);
}}
.toggle-switch-sm.on {{
    background:linear-gradient(135deg,#22c55e,#16a34a);
    box-shadow: 0 0 12px rgba(34,197,94,0.2);
}}
.knob-sm {{
    width:18px; height:18px; border-radius:50%; background:#fff;
    position:absolute; top:3px; left:3px;
    transition:all 0.3s cubic-bezier(.4,0,.2,1); box-shadow:0 1px 4px rgba(0,0,0,0.25);
}}
.toggle-switch-sm.on .knob-sm {{ left:21px; }}

/* 默认标签列表 */
.dtags-list {{ display:flex; flex-wrap:wrap; gap:8px; margin-bottom:12px; min-height:36px; }}
.dtag-pill {{
    padding:5px 14px; border-radius:20px; font-size:13px;
    background:rgba(99,102,241,0.12); border:1px solid rgba(99,102,241,0.25);
    color:#c7d2fe; display:flex; align-items:center; gap:6px; transition:all 0.25s;
}}
.dtag-pill:hover {{ background:rgba(99,102,241,0.2); transform: translateY(-1px); }}
.dtag-remove {{
    width:16px; height:16px; border-radius:50%; text-align:center;line-height:16px;
    font-size:11px; background:rgba(239,68,68,0.15); color:#f87171;
    cursor:pointer; transition:all 0.2s; display:inline-block;
}}
.dtag-remove:hover {{ background:rgba(239,68,68,0.35); transform: scale(1.1); }}
.dtags-input-row {{ display:flex; gap:8px; }}
.btn-add-tag {{
    padding:9px 18px; border-radius:12px; font-size:13px; font-weight:600;
    background:linear-gradient(135deg,rgba(99,102,241,0.22),rgba(139,92,246,0.15));
    border:1px solid rgba(99,102,241,0.3); color:#fff; cursor:pointer;
    white-space:nowrap; transition:all 0.25s;
}}
.btn-add-tag:hover {{
    background:linear-gradient(135deg,rgba(99,102,241,0.38),rgba(139,92,246,0.28));
    transform: translateY(-1px);
    box-shadow: 0 2px 12px rgba(99,102,241,0.15);
}}

/* 缓存信息网格 */
.cache-info-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:12px; margin-bottom:18px; }}
.cache-info-item {{
    padding:12px 14px; border-radius:10px;
    background:rgba(0,0,0,0.2); border:1px solid rgba(255,255,255,0.05);
}}
.cache-label {{ display:block; font-size:11px; color:rgba(255,255,255,0.35); margin-bottom:4px; }}
.cache-value {{ font-size:13px; color:rgba(255,255,255,0.75); word-break:break-all; }}

/* 操作按钮行 */
.action-buttons-row {{ display:flex; flex-wrap:wrap; gap:10px; }}
.btn-action {{
    padding:9px 20px; border-radius:12px; font-size:13px; font-weight:600;
    cursor:pointer; transition:all 0.25s cubic-bezier(.4,0,.2,1); border:none;
    letter-spacing: 0.3px;
}}
.btn-warn {{ background:rgba(239,68,68,0.12); color:#f87171; border:1px solid rgba(239,68,68,0.22); }}
.btn-warn:hover {{ background:rgba(239,68,68,0.22); transform: translateY(-1px); }}
.btn-safe {{ background:rgba(34,197,94,0.12); color:#4ade80; border:1px solid rgba(34,197,94,0.22); }}
.btn-safe:hover {{ background:rgba(34,197,94,0.22); transform: translateY(-1px); }}
.btn-primary-act {{ background:rgba(59,130,246,0.12); color:#60a5fa; border:1px solid rgba(59,130,246,0.22); }}
.btn-primary-act:hover {{ background:rgba(59,130,246,0.22); transform: translateY(-1px); }}

/* 关于卡片 */
.card-about {{ background:linear-gradient(135deg,rgba(99,102,241,0.06),rgba(139,92,246,0.04)); }}

/* ========== 历史记录页样式 ========== */
/* 工具栏卡片 */
.hist-toolbar-card {{ padding:16px 22px; margin-bottom:12px; }}
.hist-toolbar {{
    display:flex; align-items:center; gap:10px;
    flex-wrap:wrap; width:100%;
}}
.hist-search-wrap {{ flex:1; min-width:200px; }}
.hist-search-input {{
    width:100%; padding:9px 14px; border-radius:10px; font-size:13px;
    background:rgba(255,255,255,0.07); border:1px solid rgba(255,255,255,0.12);
    color:#fff; outline:none; transition:all 0.25s; font-family:inherit;
}}
.hist-search-input:focus {{ border-color:rgba(99,102,241,0.5); background:rgba(255,255,255,0.1); }}
.hist-search-input::placeholder {{ color:rgba(255,255,255,0.28); }}
.hist-filter-select {{
    padding:9px 14px; border-radius:10px; font-size:13px;
    background:rgba(255,255,255,0.07); border:1px solid rgba(255,255,255,0.12);
    color:#fff; outline:none; cursor:pointer; transition:all 0.25s; font-family:inherit;
    min-width:120px;
}}
.hist-filter-select:focus {{ border-color:rgba(99,102,241,0.5); }}
/* 历史筛选下拉已改用自定义组件，无需原生 option 样式 */
.btn-hist-refresh {{
    padding:8px 18px; border-radius:10px; font-size:13px; font-weight:600;
    background:linear-gradient(135deg,rgba(99,102,241,0.25),rgba(139,92,246,0.18));
    border:1px solid rgba(99,102,241,0.35); color:#fff; cursor:pointer;
    white-space:nowrap; transition:all 0.2s;
}}
.btn-hist-refresh:hover {{ background:linear-gradient(135deg,rgba(99,102,241,0.4),rgba(139,92,246,0.3)); }}
/* 历史刷新按钮旋转动画 */
#btnHistRefresh.spinning #histRefreshIcon {{ animation: spin 0.8s linear infinite; }}
#histRefreshIcon.click-spin {{ animation: spinOnce 0.5s cubic-bezier(.4,0,.2,1); }}

/* 统计条 */
.hist-stats-bar {{
    display:flex; align-items:center; gap:20px; padding:14px 22px;
    background:rgba(20,22,30,0.88); border:1px solid rgba(255,255,255,0.08);
    border-radius:14px; margin-bottom:14px; flex-wrap:wrap;
    box-shadow: 0 2px 12px rgba(0,0,0,0.15);
}}
.hist-stat-item {{ font-size:13px; color:rgba(255,255,255,0.6); }}
.hist-stat-item b {{ color:rgba(255,255,255,0.88); font-size:15px; margin-right:3px; }}
.stat-ok b {{ color:#4ade80; }}
.stat-fail b {{ color:#f87171; }}

/* 历史记录列表项 */
.hist-record {{
    padding:16px 18px; margin-bottom:10px; border-radius:14px;
    background:rgba(0,0,0,0.18); border:1px solid rgba(255,255,255,0.06);
    transition:all 0.3s cubic-bezier(.4,0,.2,1); position:relative;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
}}
.hist-record:hover {{
    border-color:rgba(99,102,241,0.2); background:rgba(0,0,0,0.25);
    box-shadow: 0 4px 16px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.05);
}}
.hist-rec-header {{ display:flex; align-items:center; justify-content:space-between; margin-bottom:10px; }}
.hist-rec-title {{
    font-size:15px; font-weight:600; color:rgba(255,255,255,0.92);
    overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:420px;
}}
.hist-rec-status {{
    font-size:11px; padding:3px 11px; border-radius:20px; font-weight:600; letter-spacing:0.4px;
    flex-shrink:0; margin-left:10px;
}}
.hst-success {{ background:rgba(34,197,94,0.15); color:#4ade80; border:1px solid rgba(34,197,94,0.25); }}
.hst-error {{ background:rgba(239,68,68,0.15); color:#f87171; border:1px solid rgba(239,68,68,0.25); }}
.hst-pending {{ background:rgba(59,130,246,0.15); color:#60a5fa; border:1px solid rgba(59,130,246,0.25); }}
.hst-partial {{ background:rgba(245,158,11,0.15); color:#fbbf24; border:1px solid rgba(245,158,11,0.25); }}

.hist-rec-body {{ display:flex; gap:16px; align-items:flex-start; }}
.hist-rec-info {{ flex:1; min-width:0; }}
.hist-rec-meta {{
    font-size:12px; color:rgba(255,255,255,0.38); line-height:1.9;
}}
.hist-rec-meta span {{ margin-right:16px; }}
.hist-rec-platforms {{ margin-top:8px; display:flex; flex-wrap:wrap; gap:6px; }}
.hist-plat-tag {{
    font-size:11px; padding:2px 10px; border-radius:8px;
    background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.1);
    color:rgba(255,255,255,0.55); display:inline-flex; align-items:center; gap:4px;
}}
.plat-tag-ok {{ color:#4ade80; border-color:rgba(34,197,94,0.25); background:rgba(34,197,94,0.08); }}
.plat-tag-err {{ color:#f87171; border-color:rgba(239,68,68,0.25); background:rgba(239,68,68,0.08); }}

/* 右侧操作按钮组 */
.hist-rec-actions {{
    display:flex; flex-direction:column; gap:6px; flex-shrink:0;
    align-items:flex-end;
}}
.btn-hist-action {{
    padding:5px 14px; border-radius:8px; font-size:12px; font-weight:500;
    cursor:pointer; border:none; transition:all 0.2s; white-space:nowrap;
    font-family:inherit;
}}
.btn-retry {{ background:rgba(59,130,246,0.15); color:#60a5fa; border:1px solid rgba(59,130,246,0.25); }}
.btn-retry:hover {{ background:rgba(59,130,246,0.3); }}
.btn-del {{ background:rgba(239,68,68,0.1); color:#f87171; border:1px solid rgba(239,68,68,0.2); }}
.btn-del:hover {{ background:rgba(239,68,68,0.22); }}

/* ========== 自定义图标网格 ========== */
.icon-grid {{
    display: grid; grid-template-columns: repeat(auto-fill, minmax(90px, 1fr));
    gap: 10px;
}}
.icon-item {{
    display: flex; flex-direction: column; align-items: center; gap: 6px;
    padding: 14px 8px; border-radius: 14px; cursor: pointer;
    background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06);
    transition: all 0.25s ease; position: relative;
}}
.icon-item:hover {{
    background: rgba(99,102,241,0.1); border-color: rgba(99,102,241,0.3);
    transform: translateY(-3px); box-shadow: 0 6px 20px rgba(99,102,241,0.12);
}}
.icon-item.has-custom {{
    border-color: rgba(99,102,241,0.25); background: rgba(99,102,241,0.06);
}}
.ii-preview {{
    width: 42px; height: 42px; display: flex; align-items: center; justify-content: center;
    border-radius: 12px; background: rgba(255,255,255,0.06);
}}
.ii-preview img {{
    width: 36px !important; height: 36px !important; border-radius: 10px !important; object-fit: cover;
}}
.ii-preview svg {{
    width: 28px; height: 28px;
}}
.ii-name {{
    font-size: 11px; color: rgba(255,255,255,0.65); white-space: nowrap;
}}
.ii-remove {{
    position: absolute; top: 4px; right: 6px; font-size: 13px; color: rgba(255,255,255,0.35);
    cursor: pointer; line-height: 1; transition: color 0.2s;
}}
.ii-remove:hover {{ color: #f87171; }}
.plat-icon-text {{ display:none; }}

/* ========== 新增动画效果 ========== */

/* E1: 发布按钮波纹 Ripple - 多层波纹+颜色更亮 */
.publish-btn .ripple {{
    position: absolute; border-radius: 50%;
    background: radial-gradient(circle, rgba(255,255,255,0.5) 0%, rgba(129,140,248,0.35) 60%, transparent 100%);
    transform: scale(0); animation: rippleAnim 0.8s ease-out forwards;
    pointer-events: none;
    box-shadow: 0 0 12px rgba(129,140,248,0.3);
}}
@keyframes rippleAnim {{
    0% {{ transform: scale(0); opacity: 1; }}
    100% {{ transform: scale(4); opacity: 0; }}
}}

/* E2: 卡片 3D 悬浮倾斜 - 更大倾斜角+光泽层 */
.nav-card {{
    position: relative;
    padding: 36px 28px;
    border-radius: 22px;
    overflow: hidden;
    perspective: 600px;
    transform-style: preserve-3d;
    /* will-change 已移除：CEF 下强制提升合成层反增 GPU 压力，JS 直接控制 transform 时不需要 */
    transition: background 0.35s, border-color 0.35s, box-shadow 0.35s, opacity 0.25s, transform 0.12s ease-out;
}}
.nav-card::before {{
    content: ""; position: absolute; inset: 0; border-radius: inherit;
    background: linear-gradient(135deg, rgba(255,255,255,0.12) 0%, transparent 50%);
    opacity: 0; transition: opacity 0.3s; pointer-events: none; z-index: 1;
}}
.nav-card:hover::before {{ opacity: 1; }}

/* E3: Confetti 纸屑 - 更多形状+摇摆+更鲜艳 */
#confetti-container {{
    position: fixed; inset: 0; pointer-events: none; z-index: 9999;
    overflow: hidden;
}}
.confetti-piece {{
    position: absolute; width: 10px; height: 14px; top: -20px;
    opacity: 1;
}}
@keyframes confettiFall {{
    0% {{ transform: translateY(0) rotateZ(0deg) rotateX(0deg); opacity: 1; }}
    25% {{ transform: translateY(25vh) rotateZ(180deg) rotateX(90deg); }}
    50% {{ transform: translateY(50vh) rotateZ(360deg) rotateX(180deg); opacity: 0.8; }}
    75% {{ transform: translateY(75vh) rotateZ(540deg) rotateX(270deg); }}
    100% {{ transform: translateY(100vh) rotateZ(720deg) rotateX(360deg); opacity: 0; }}
}}
@keyframes confettiSway {{
    0%,100% {{ margin-left: 0; }}
    25% {{ margin-left: 30px; }}
    75% {{ margin-left: -30px; }}
}}

/* E4: 鼠标跟随光晕 - 更大更亮+多色 */
#cursor-glow {{
    position: fixed; width: 300px; height: 300px;
    border-radius: 50%; pointer-events: none; z-index: 3;
    background: radial-gradient(circle,
        rgba(99,102,241,0.10) 0%,
        rgba(139,92,246,0.05) 25%,
        rgba(236,72,153,0.03) 45%,
        transparent 70%
    );
    transform: translate(-50%, -50%);
    /* 移除 will-change 和 mix-blend-mode —— WebView2 中这两个是最大的 GPU 消耗源 */
    /* JS 中通过 requestAnimationFrame 直接设置 transform 定位 */
}}

/* E5: 打字机光标闪烁 - 更粗更亮 */
.typewriter-cursor {{
    display: inline-block; width: 3px; height: 1.1em;
    background: linear-gradient(to bottom, #818cf8, #6366f1);
    margin-left: 3px; vertical-align: text-bottom;
    animation: cursorBlink 0.8s step-end infinite;
    box-shadow: 0 0 8px rgba(129,140,248,0.5);
}}
@keyframes cursorBlink {{
    0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0; }}
}}
/* E11: 标题彩蛋 - 点击重放打字机 */
#typewriter-title {{
    cursor: pointer; user-select: none;
    transition: filter 0.2s;
}}
#typewriter-title:hover {{
    filter: brightness(1.15);
}}

/* E6: 进度条流光 - 更亮更宽+脉冲 */
.progress-item.pi-uploading {{
    position: relative; overflow: hidden;
    border-color: rgba(99,102,241,0.2);
    box-shadow: 0 0 12px rgba(99,102,241,0.08);
    contain: layout style;  /* 限制重绘范围，提升渲染性能 */
}}
.progress-item.pi-uploading::after {{
    content:""; position:absolute; inset:0;
    background: linear-gradient(90deg,
        transparent 0%,
        rgba(129,140,248,0.08) 10%,
        rgba(165,180,252,0.28) 25%,
        rgba(255,255,255,0.35) 50%,
        rgba(165,180,252,0.28) 75%,
        rgba(129,140,248,0.08) 90%,
        transparent 100%
    );
    animation: progressShimmer 2s linear infinite;
    pointer-events: none;
}}
@keyframes progressShimmer {{
    0% {{ transform: translateX(-100%); }}
    100% {{ transform: translateX(100%); }}
}}

/* E7: 平台选中弹跳 - 更夸张的弹簧 */
.platform-btn.p-bounce {{
    animation: platBounce 0.6s cubic-bezier(.34,1.56,.64,1);
}}
@keyframes platBounce {{
    0% {{ transform: scale(1); }}
    25% {{ transform: scale(1.2); }}
    50% {{ transform: scale(0.9); }}
    70% {{ transform: scale(1.06); }}
    85% {{ transform: scale(0.98); }}
    100% {{ transform: scale(1); }}
}}
/* E7b: 平台取消选中收缩动画 */
.platform-btn.p-shrink {{
    animation: platShrink 0.6s cubic-bezier(.4,0,.2,1);
}}
@keyframes platShrink {{
    0% {{ transform: scale(1); }}
    25% {{ transform: scale(0.82); }}
    50% {{ transform: scale(1.05); }}
    75% {{ transform: scale(0.98); }}
    100% {{ transform: scale(1); }}
}}

/* E8: Toast 弹簧弹出 - 更弹+发光 */
.toast {{
    transition: all 0.5s cubic-bezier(.34,1.56,.64,1);
}}
.toast.show {{
    animation: toastSpringIn 0.6s cubic-bezier(.34,1.56,.64,1) both;
}}
@keyframes toastSpringIn {{
    0% {{ opacity: 0; transform: translateX(-50%) translateY(-30px) scale(0.7); }}
    50% {{ opacity: 1; transform: translateX(-50%) translateY(4px) scale(1.05); }}
    70% {{ transform: translateX(-50%) translateY(-2px) scale(0.98); }}
    85% {{ transform: translateX(-50%) translateY(1px) scale(1.01); }}
    100% {{ opacity: 1; transform: translateX(-50%) translateY(0) scale(1); }}
}}

/* E9: 数字滚动（纯JS实现，无需额外CSS） */

/* E10: 骨架屏闪烁 - 更亮更明显 */
.skeleton {{
    background: linear-gradient(90deg,
        rgba(255,255,255,0.04) 25%,
        rgba(99,102,241,0.12) 50%,
        rgba(255,255,255,0.04) 75%
    );
    background-size: 200% 100%;
    animation: skeletonShimmer 1.5s ease-in-out infinite;
    border-radius: 8px;
}}
@keyframes skeletonShimmer {{
    0% {{ background-position: 200% 0; }}
    100% {{ background-position: -200% 0; }}
}}
.skeleton-text {{
    height: 14px; margin-bottom: 10px;
}}
.skeleton-text.short {{ width: 60%; }}
.skeleton-text.medium {{ width: 80%; }}
.skeleton-circle {{
    width: 44px; height: 44px; border-radius: 50%; margin: 0 auto 10px;
}}
.skeleton-card {{
    padding: 22px; border-radius: 18px;
    background: rgba(20,22,30,0.88); border: 1px solid rgba(255,255,255,0.08);
}}

/* ========== 小太阳弧形动画 ========== */
.sun-arc-wrap {{
    position: relative; height: 80px; margin: 6px 0 -8px;
    overflow: visible; user-select: none; -webkit-user-select: none;
}}
.sun-arc-wrap svg {{ pointer-events: none; }}
.sun-orb {{
    position: absolute; width: 28px; height: 28px; border-radius: 50%;
    cursor: grab; z-index: 3; transform: translate(-50%, -50%);
    transition: opacity 0.4s ease;
}}
.sun-orb.falling {{ opacity: 0; }}
.sun-orb.rising {{ opacity: 0; transition: opacity 0.6s ease-out; }}
.sun-orb.visible {{ opacity: 1; }}
.sun-orb:active, .sun-orb.dragging {{ cursor: grabbing; }}
.sun-body {{
    width: 100%; height: 100%; border-radius: 50%; position: relative; z-index: 2;
}}
.sun-shadow {{
    position: absolute; width: 18px; height: 4px; border-radius: 50%;
    bottom: -11px; left: 50%; transform: translateX(-50%); z-index: 1;
    background: rgba(0,0,0,0.25); filter: blur(3px);
}}
/* 云朵（跟随太阳，覆盖在太阳上） */
.sun-cloud {{
    position: absolute; border-radius: 12px; opacity: 0; z-index: 4; pointer-events: none;
}}

/* ========== 小太阳爆炸特效 ========== */
.sun-particle {{
    position: absolute; border-radius: 50%; z-index: 10; pointer-events: none;
    will-change: transform, opacity;
}}
@keyframes particleFly {{
    0% {{ transform:translate(-50%,-50%) scale(1); opacity:1; }}
    100% {{ opacity:0; }}
}}
.sun-flash {{
    position: absolute; border-radius: 50%; z-index: 9; pointer-events: none;
    background: radial-gradient(circle, rgba(255,255,240,0.95) 0%, rgba(255,200,80,0.6) 40%, transparent 70%);
}}
@keyframes flashBang {{
    0% {{ transform:translate(-50%,-50%) scale(0); opacity:1; }}
    25% {{ transform:translate(-50%,-50%) scale(3.5); opacity:0.85; }}
    100% {{ transform:translate(-50%,-50%) scale(5); opacity:0; }}
}}
.sun-shockwave {{
    position: absolute; border-radius: 50%; z-index: 8; pointer-events: none;
    border: 2px solid rgba(255,180,60,0.7);
    background: radial-gradient(circle, rgba(255,200,100,0.15) 0%, transparent 70%);
}}
@keyframes shockwaveExpand {{
    0% {{ transform:translate(-50%,-50%) scale(0.3); opacity:1; border-width:3px; }}
    100% {{ transform:translate(-50%,-50%) scale(6); opacity:0; border-width:0.5px; }}
}}
@keyframes orbShrink {{
    0% {{ transform:translate(-50%,-50%) scale(1); opacity:1; }}
    40% {{ transform:translate(-50%,-50%) scale(1.4); opacity:0.8; }}
    100% {{ transform:translate(-50%,-50%) scale(0); opacity:0; }}
}}
.sun-orb.exploding {{ animation:orbShrink 0.45s cubic-bezier(.4,0,.2,1) forwards; pointer-events:none; }}
.sun-spark {{
    position: absolute; width:2px; height:2px; border-radius: 50%; z-index: 11; pointer-events:none;
    background:#fff;
}}
@keyframes sparkFly {{
    0% {{ transform:translate(-50%,-50%) scale(1); opacity:1; }}
    100% {{ opacity:0; }}
}}

/* ========== 新手引导（Onboarding Guide）—— 轻量版，无 backdrop-filter 无大 box-shadow ========== */
#guide-overlay {{
    position: fixed; inset: 0; z-index: 10000;
    background: rgba(6,8,18,0.72);
    display: none;
}}
#guide-overlay.active {{ display: block; }}

/* 高亮聚光灯 —— 用 clip-path 做镂空，避免 CEF 的超大 box-shadow 性能灾难 */
#guide-spotlight {{
    position: fixed; border-radius: 12px;
    z-index: 10001; pointer-events: none;
    outline: 2px solid rgba(99,102,241,0.7); outline-offset: 4px;
    display: none;
    /* 不用 box-shadow: 0 0 0 9999px，改由 overlay + clip-path 配合实现遮罩效果 */
}}

/* 气泡提示框 —— 纯色背景，零 blur */
.guide-tooltip {{
    position: fixed; z-index: 10002;
    max-width: 280px; min-width: 200px;
    padding: 14px 18px;
    background: rgba(22,24,38,0.96);
    border: 1px solid rgba(129,140,248,0.25);
    border-radius: 14px;
    color: rgba(255,255,255,0.92);
    font-size: 13px; line-height: 1.6;
    box-shadow: 0 8px 28px rgba(0,0,0,0.45);
    display: none;
}}
.guide-tooltip.visible {{ display: block; }}
.guide-tooltip::after {{
    content: ''; position: absolute; width: 10px; height: 10px;
    background: rgba(22,24,38,0.96);
    border-right: 1px solid rgba(129,140,248,0.25);
    border-bottom: 1px solid rgba(129,140,248,0.25);
    transform: rotate(45deg);
}}
/* 气泡位置 */
.guide-tooltip.below {{ margin-top: 16px; }} .guide-tooltip.below::after {{ top: -6px; left: 26px; }}
.guide-tooltip.above {{ margin-bottom: 16px; }} .guide-tooltip.above::after {{ bottom: -6px; left: 26px; transform: rotate(-135deg); }}
.guide-tooltip.right {{ margin-left: 20px; }} .guide-tooltip.right::after {{ left: -6px; top: 22px; transform: rotate(-45deg); }}
.guide-tooltip.left {{ margin-right: 20px; }} .guide-tooltip.left::after {{ right: -6px; top: 22px; transform: rotate(135deg); }}

.guide-title {{
    font-size: 14px; font-weight: 700; color: #c7d2fe;
    margin-bottom: 5px; display: flex; align-items: center; gap: 6px;
}}
.guide-title .step-num {{
    display:inline-flex; align-items:center; justify-content:center;
    width:20px;height:20px;border-radius:50%;
    background:#5b5ce8; font-size:11px;font-weight:800;color:#fff; flex-shrink:0;
}}
.guide-desc {{ color: rgba(255,255,255,0.55); font-size: 12px; margin-bottom: 12px; line-height: 1.65; }}

/* 按钮区 */
.guide-actions {{ display: flex; align-items: center; justify-content: space-between; gap: 8px; }}
.guide-btn {{
    padding: 6px 15px; border-radius: 8px; font-size: 12px;
    cursor: pointer; border: none; font-weight: 600;
    font-family: inherit; transition: opacity 0.15s;
}} .guide-btn:hover {{ opacity: 0.85; }}
.guide-btn-skip {{ background: transparent; color: rgba(255,255,255,0.3); padding: 6px 10px; }}
.guide-btn-next {{ background: #5b5ce8; color: #fff; }}
.guide-btn-done {{ background: #16a34a; color: #fff; flex: 1; text-align: center; padding: 8px 18px; font-size: 13px; }}

/* 进度点 */
.guide-progress {{
    position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
    display: flex; gap: 5px; z-index: 10003;
}}
.guide-dot {{
    width: 7px; height: 7px; border-radius: 50%;
    background: rgba(255,255,255,0.2); cursor: pointer; transition: all 0.2s ease;
}}
.guide-dot.active {{ background: #818cf8; width: 20px; border-radius: 3.5px; }}
.guide-dot.done {{ background: rgba(129,140,248,0.5); }}

/* ========== 彩蛋引导（Easter Egg Guide）—— 活泼版 ========== */
#egg-guide-overlay {{
    position: fixed; inset: 0; z-index: 10000;
    background: rgba(6,8,18,0.72);
    display: none;
}}
#egg-guide-overlay.active {{ display: block; }}

/* 聚光灯 —— 金色系，区别于新手引导的紫色 */
#egg-guide-spotlight-gold {{
    position: fixed; border-radius: 14px;
    z-index: 10001; pointer-events: none;
    outline: 2px solid rgba(250,204,21,0.7); outline-offset: 4px;
    display: none;
}}

/* 气泡 —— 暖色调背景 */
.egg-guide-tooltip {{
    position: fixed; z-index: 10005; pointer-events: auto;
    max-width: 290px; min-width: 220px;
    padding: 16px 20px;
    background: rgba(30,24,12,0.96);
    border: 1px solid rgba(250,204,21,0.3);
    border-radius: 16px;
    color: rgba(255,255,255,0.92);
    font-size: 13px; line-height: 1.65;
    box-shadow: 0 8px 32px rgba(0,0,0,0.5), 0 0 24px rgba(250,204,21,0.08);
    display: none;
}}
.egg-guide-tooltip.visible {{ display: block; }}
.egg-guide-tooltip::after {{
    content: ''; position: absolute; width: 10px; height: 10px;
    background: rgba(30,24,12,0.96);
    border-right: 1px solid rgba(250,204,21,0.3);
    border-bottom: 1px solid rgba(250,204,21,0.3);
    transform: rotate(45deg);
}}
.egg-guide-tooltip.below {{ margin-top: 16px; }} .egg-guide-tooltip.below::after {{ top: -6px; left: 26px; }}
.egg-guide-tooltip.above {{ margin-bottom: 16px; }} .egg-guide-tooltip.above::after {{ bottom: -6px; left: 26px; transform: rotate(-135deg); }}
.egg-guide-tooltip.right {{ margin-left: 20px; }} .egg-guide-tooltip.right::after {{ left: -6px; top: 22px; transform: rotate(-45deg); }}
.egg-guide-tooltip.left {{ margin-right: 20px; }} .egg-guide-tooltip.left::after {{ right: -6px; top: 22px; transform: rotate(135deg); }}

.egg-guide-title {{
    font-size: 15px; font-weight: 700; color: #fcd84d;
    margin-bottom: 6px; display: flex; align-items: center; gap: 6px;
}}
.egg-guide-title .step-num {{
    display:inline-flex; align-items:center; justify-content:center;
    width:22px;height:22px;border-radius:50%;
    background:linear-gradient(135deg,#f59e0b,#d97706); font-size:11px;font-weight:800;color:#fff; flex-shrink:0;
}}
.egg-guide-desc {{ color: rgba(255,255,255,0.55); font-size: 12px; margin-bottom: 14px; line-height: 1.65; }}
.egg-guide-hint {{
    font-size: 11px; color: rgba(250,204,21,0.6); padding: 6px 10px;
    border-radius: 8px; background: rgba(250,204,21,0.08); margin-bottom: 12px;
    border-left: 2px solid rgba(250,204,21,0.4);
}}

/* 按钮 */
.egg-guide-btn {{
    padding: 7px 18px; border-radius: 10px; font-size: 12px;
    cursor: pointer; border: none; font-weight: 700;
    font-family: inherit; transition: opacity 0.15s, transform 0.15s;
}} .egg-guide-btn:hover {{ opacity: 0.88; transform: scale(1.04); }}
.egg-guide-btn-skip {{ background: transparent; color: rgba(255,255,255,0.3); padding: 7px 12px; }}
.egg-guide-btn-next {{ background: linear-gradient(135deg,#f59e0b,#d97706); color:#fff; box-shadow: 0 2px 12px rgba(245,158,11,0.3); }}
.egg-guide-btn-done {{ background: linear-gradient(135deg,#10b981,#059669); color:#fff; flex: 1; text-align:center; padding: 10px 20px; font-size: 14px; box-shadow: 0 2px 16px rgba(16,185,129,0.25); }}

/* 彩蛋发现进度 —— 用星星/彩蛋图标替代圆点 */
.egg-guide-progress {{
    position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
    display: flex; gap: 6px; z-index: 10003;
}}
.egg-dot {{
    width: 8px; height: 8px; border-radius: 50%;
    background: rgba(255,255,255,0.2); cursor: pointer; transition: all 0.25s ease;
    font-size: 9px; display: flex; align-items: center; justify-content: center;
}} .egg-dot:hover {{ transform: scale(1.3); }}
.egg-dot.active {{ background: #fcd84d; width: 22px; border-radius: 4px; box-shadow: 0 0 8px rgba(250,204,21,0.4); }}
.egg-dot.done {{ background: rgba(250,204,21,0.45); }}

/* 设置页入口按钮 */
.egg-entry-btn {{
    display:flex;align-items:center;gap:6px;padding:9px 18px;
    border-radius:10px;border:none;font-size:13px;font-weight:600;
    font-family:inherit;cursor:pointer;transition:all 0.2s;
}
.egg9-overlay {{
    position:fixed; inset:0; background:rgba(0,0,0,0.55);
    z-index:9999; display:none; align-items:center; justify-content:center;
}}
.egg9-panel {{
    background:rgba(22,24,35,0.95); border:1px solid rgba(255,255,255,0.12);
    border-radius:18px; padding:22px; width:300px; max-width:88vw;
    box-shadow: 0 20px 60px rgba(0,0,0,0.5), 0 0 40px rgba(99,102,241,0.08);
    animation: egg9Pop 0.3s cubic-bezier(.34,1.56,.64,1);
}}
@keyframes egg9Pop {{
    from{{transform:scale(0.8); opacity:0}} to{{transform:scale(1); opacity:1}}
}}
.egg9-title {{
    font-size:15px; font-weight:700; color:#fff; text-align:center; margin-bottom:4px;
}}
.egg9-subtitle {{
    font-size:11px; color:rgba(255,255,255,0.45); text-align:center; margin-bottom:16px;
}}
.egg9-target-name {{
    font-size:13px; color:rgba(129,140,248,0.85); text-align:center;
    margin-bottom:14px; padding:6px 14px; border-radius:10px;
    background:rgba(99,102,241,0.1); border:1px solid rgba(129,140,241,0.2);
}}
.egg9-swatches {{
    display:grid; grid-template-columns: repeat(5,1fr); gap:8px; margin-bottom:14px;
}}
.egg9-swatch {{
    width:100%; aspect-ratio:1; border-radius:10px; cursor:pointer;
    border:2px solid transparent; transition:all 0.2s; position:relative;
}}
.egg9-swatch:hover {{ transform:scale(1.12); border-color:rgba(255,255,255,0.4); }}
.egg9-swatch.selected {{ border-color:#fff; box-shadow:0 0 8px rgba(255,255,255,0.3); }}
.egg9-swatch.selected::after {{
    content:'✓'; position:absolute; inset:0; display:flex; align-items:center;
    justify-content:center; font-size:13px; font-weight:900; color:#fff;
    text-shadow:0 1px 3px rgba(0,0,0,0.7);
}}
.egg9-custom-row {{
    display:flex; gap:8px; align-items:center; margin-bottom:16px;
}}
.egg9-custom-row input[type="color"] {{
    width:40px; height:36px; border:none; border-radius:8px; cursor:pointer;
    background:none; padding:2px;
}}
.egg9-custom-row span {{
    font-size:12px; color:rgba(255,255,255,0.5); flex:1;
}}
.egg9-actions {{
    display:flex; gap:8px;
}}
.egg9-btn {{
    flex:1; padding:9px; border-radius:10px; font-size:13px; font-weight:600;
    cursor:pointer; border:1px solid rgba(255,255,255,0.1); transition:all 0.2s;
    font-family:inherit; text-align:center;
}}
.egg9-btn-apply {{
    background:linear-gradient(135deg,#6366f1,#8b5cf6); color:#fff;
    border-color:rgba(99,102,241,0.3);
}}
.egg9-btn-apply:hover {{
    background:linear-gradient(135deg,#7c83f5,#a078f7);
    box-shadow:0 4px 16px rgba(99,102,241,0.3);
}}
.egg9-btn-cancel {{
    background:rgba(255,255,255,0.05); color:rgba(255,255,255,0.55);
}}
.egg9-btn-cancel:hover {{ background:rgba(255,255,255,0.1); }}
</style>
<body>

<!-- ====== 标题栏（纯透明，仅 text+按钮，拖拽区）====== -->
<div class="title-bar" style="
    position:fixed; top:0; left:0; right:0; z-index:9999;
    display:flex; align-items:center; padding:0 14px 0 20px; height:48px;
    -webkit-app-region:drag; box-sizing:border-box;
">
    <!-- 左侧：标题（可拖拽） -->
    <span style="font-size:13px;font-weight:600;color:rgba(255,255,255,0.45);-webkit-app-region:drag;user-select:none;">
        Tujue AutoSend
    </span>
    <!-- 中间占位 -->
    <div style="flex:1;-webkit-app-region:drag;"></div>
    <!-- 右侧：窗口控制按钮（ai0 风格） -->
    <button class="win-btn" onclick="window.pywebview.api.minimize()" title="\\u6700\\u5C0F\\u5316">─</button>
    <button class="win-btn" onclick="void(0)" title="\\u6700\\u5927\\u5316">□</button>
    <button class="win-btn win-close" onclick="window.pywebview.api.close()" title="\\u5173\\u95ED">✕</button>
</div>

<!-- ====== 鼠标跟随光晕 E4 ====== -->
<div id="cursor-glow"></div>

<!-- ====== Confetti 纸屑容器 E3 ====== -->
<div id="confetti-container"></div>

<!-- ====== 新手引导组件（轻量） ====== -->
<div id="guide-overlay" style="display:none;"></div>
<div id="guide-spotlight" style="display:none;"></div>
<div class="guide-tooltip" id="guideTooltip" style="display:none;">
    <div class="guide-title"><span class="step-num" id="guideStepNum">1</span> <span id="guideTitleText">标题</span></div>
    <div class="guide-desc" id="guideDesc">描述文字</div>
    <div class="guide-actions">
        <button class="guide-btn guide-btn-skip" onclick="endGuide()">跳过</button>
        <button class="guide-btn guide-btn-next" id="guideBtnNext" onclick="nextGuideStep()">下一步 →</button>
    </div>
</div>
<div class="guide-progress" id="guideProgress" style="display:none;"></div>

<!-- ====== 彩蛋引导组件（金色活泼版） ====== -->
<div id="egg-guide-overlay" style="display:none;"></div>
<div id="egg-guide-spotlight-gold" style="display:none;"></div>
<div class="egg-guide-tooltip" id="egg-guide-tooltip" style="display:none;">
    <div class="egg-guide-title"><span class="step-num" id="eggStepNum">1</span> <span id="eggTitleText">标题</span></div>
    <div class="egg-guide-hint" id="eggHintBar" style="display:none;">提示</div>
    <div class="egg-guide-desc" id="eggDesc">描述文字</div>
    <div class="guide-actions">
        <button class="egg-guide-btn egg-guide-btn-skip" onclick="endEggGuide()">跳过</button>
        <button class="egg-guide-btn egg-guide-btn-next" id="eggBtnNext" onclick="nextEggGuideStep()">下一个 →</button>
    </div>
</div>
<div class="egg-guide-progress" id="egg-guide-progress" style="display:none;"></div>

<!-- ====== 壁纸轮播层 ====== -->
<div id="wallpaper-bg">
    <div class="wp active" style="background-image:url(data:image/jpeg;base64,__BG1__)"></div>
    <div class="wp" style="background-image:url(data:image/jpeg;base64,__BG2__)"></div>
</div>
<div class="wp-indicators" id="wpIndicators">
    <span data-idx="0" class="active" onclick="switchWP(0)"></span>
    <span data-idx="1" onclick="switchWP(1)"></span>
</div>

<!-- ====== 主容器 ====== -->
<div class="app-container">

<!-- ==================== 导航首页（Dashboard） ==================== -->
<section id="page-home" class="page-home active">

    <!-- 欢迎区 -->
    <div class="home-welcome">
        <h1 id="typewriter-title"></h1>
        <p>多平台视频一键发布工具 · 选择功能进入</p>
    </div>

    <!-- 四个功能入口卡片 -->
    <div class="nav-cards-grid">
        <!-- 发布卡片 -->
        <div class="nav-card nc-publish" onclick="goToPage('page-publish')">
            <span class="nav-card-icon">📤</span>
            <div class="nav-card-title">一键发布</div>
            <div class="nav-card-desc">选择视频文件，填写信息<br>同时发布到多个平台</div>
        </div>

        <!-- 登录管理卡片 -->
        <div class="nav-card nc-login" onclick="goToPage('page-login')">
            <span class="nav-card-icon">🔑</span>
            <div class="nav-card-title">登录管理</div>
            <div class="nav-card-desc">管理各平台账号状态<br>扫码登录或退出账号</div>
        </div>

        <!-- 发布历史卡片 -->
        <div class="nav-card nc-history" onclick="goToPage('page-history')">
            <span class="nav-card-icon">📋</span>
            <div class="nav-card-title">发布历史</div>
            <div class="nav-card-desc">查看所有发布记录<br>支持筛选、搜索和重试</div>
        </div>

        <!-- 设置卡片 -->
        <div class="nav-card nc-settings" onclick="goToPage('page-settings')">
            <span class="nav-card-icon">⚙️</span>
            <div class="nav-card-title">系统设置</div>
            <div class="nav-card-desc">浏览器模式、并发数、标签管理<br>缓存清理与配置导出</div>
        </div>
    </div>

</section>


<!-- ==================== 发布页 ==================== -->
<section id="page-publish" class="page-section">

    <!-- 返回首页按钮 -->
    <div class="subpage-header">
        <div class="back-home-btn" id="backHomeBtnLogin" onclick="smartGoHome()">◀ 返回首页</div>
    </div>

    <!-- 视频选择 -->
    <div class="card">
        <div class="card-title"><span class="icon">🎬</span> 选择视频文件</div>
        <div class="upload-zone" id="uploadZone" onclick="document.getElementById('videoInput').click()">
            <input type="file" id="videoInput" accept="video/*" onchange="handleVideoSelect(event)">
            <div id="uploadHint">
                <div style="font-size:36px;margin-bottom:8px;">📹</div>
                <div style="font-size:15px;color:rgba(255,255,255,0.7);margin-bottom:4px;">点击或拖拽选择视频文件</div>
                <div style="font-size:12px;color:rgba(255,255,255,0.35);">支持 mp4 / mov / avi / mkv / webm</div>
            </div>
            <video id="videoPreview" class="video-preview" controls></video>
            <div id="fileInfo" style="display:none;margin-top:10px;font-size:13px;color:rgba(255,255,255,0.6);"></div>
        </div>
    </div>

    <!-- 编辑内容 -->
    <div class="card">
        <div class="card-title"><span class="icon">✏️</span> 编辑发布内容</div>
        
        <div class="form-group">
            <label>视频标题 *</label>
            <input type="text" class="input-field" id="titleInput" placeholder="请输入视频标题..." maxlength="50">
        </div>
        
        <div class="form-group">
            <label>作品描述</label>
            <textarea class="input-field" id="descInput" placeholder="输入作品描述（可选）..." maxlength="2000"></textarea>
        </div>
        
        <div class="form-group">
            <label>话题标签（点击添加/取消）</label>
            <div class="tags-row" id="tagsRow">
                <span class="tag-pill" onclick="toggleTag(this)">🔥 热门推荐</span>
                <span class="tag-pill" onclick="toggleTag(this)">✨ 精彩瞬间</span>
                <span class="tag-pill" onclick="toggleTag(this)">💡 干货分享</span>
                <span class="tag-pill" onclick="toggleTag(this)">🌟 今日份快乐</span>
                <span class="tag-pill" onclick="toggleTag(this)">🎯 必看系列</span>
                <span class="tag-pill" onclick="toggleTag(this)">💪 每日一练</span>
                <input type="text" class="custom-tag-input" id="customTagInput"
                       placeholder="+ 自定义标签" onkeydown="if(event.key==='Enter'){{event.preventDefault();addCustomTag();}}">
            </div>
        </div>
    </div>

    <!-- 平台选择 + 定时 + 发布 -->
    <div class="card">
        <div style="display:flex;align-items:center;justify-content:space-between;">
            <div class="card-title"><span class="icon">🌐</span> 选择发布平台</div>
            <button id="btnRefreshPublish" onclick="refreshPublishPlatforms()" style="display:flex;align-items:center;gap:5px;padding:7px 14px;border-radius:10px;background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.12);color:rgba(255,255,255,0.7);font-size:12px;cursor:pointer;transition:all 0.2s;">
                <svg id="refreshPublishIcon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 2v6h-6"/><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M3 22v-6h6"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/></svg>
                刷新状态
            </button>
        </div>
        <div class="platform-grid" id="platformGrid">
            <!-- 由 JS 动态生成 -->
        </div>
    </div>

    <!-- B站分区选择（选中B站时显示） -->
    <div class="card" id="bilibiliZoneCard" style="display:none;">
        <div class="card-title"><span class="icon">📁</span> B站分区选择</div>
        <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:8px;">
            <select id="biliZoneSelect" onchange="updateBiliSubZones()" style="flex:1;min-width:200px;padding:8px 12px;border-radius:10px;background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.15);color:#fff;font-size:13px;outline:none;">
                <option value="21">日常（默认）</option>
            </select>
            <select id="biliSubZoneSelect" style="flex:1;min-width:200px;padding:8px 12px;border-radius:10px;background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.15);color:#fff;font-size:13px;outline:none;">
            </select>
        </div>
    </div>

    <!-- 定时发布 -->
    <div class="card">
        <div class="schedule-toggle" id="schedRow">
            <div class="toggle-switch" id="schedToggle" onclick="toggleSchedule()">
                <div class="knob" id="schedKnob"></div>
            </div>
            <span class="sched-label">定时发布</span>
            <span class="sched-badge" id="schedBadge">关</span>
            <input type="datetime-local" class="datetime-picker" id="datetimePicker">
        </div>
    </div>

    <!-- 一键发布按钮 -->
    <button class="publish-btn" id="publishBtn" onclick="doPublish()">
        <span class="btn-text">🚀 一键发布到选中平台 <span class="btn-arrow">→</span></span>
    </button>

    <!-- 上传进度面板 -->
    <div class="progress-panel card" id="progressPanel" style="display:none;">
        <div class="card-title"><span class="icon">📊</span> 发布进度</div>
        <div id="progressList"></div>
    </div>

</section>


<!-- ==================== 登录管理页（完整版） ==================== -->
<section id="page-login" class="page-section">

    <!-- 返回首页按钮 -->
    <div class="subpage-header">
        <div class="back-home-btn" id="backHomeBtnLogin" onclick="smartGoHome()">◀ 返回首页</div>
    </div>

    <!-- 页面标题 + 操作按钮 -->
    <div class="card">
        <div style="display:flex;align-items:center;justify-content:space-between;">
            <div class="card-title"><span class="icon">🔑</span> 登录管理</div>
            <div style="display:flex;gap:8px;">
                <button id="btnCheckCookies" onclick="checkAllCookies()" style="display:flex;align-items:center;gap:5px;padding:7px 14px;border-radius:10px;background:rgba(251,191,36,0.15);border:1px solid rgba(251,191,36,0.25);color:#fbbf24;font-size:12px;cursor:pointer;transition:all 0.2s;"
                    title="检测所有已登录平台的 Cookie 是否有效">
                    🔍 检测登录状态
                </button>
                <button id="btnRefreshLogin" onclick="refreshLoginPage()" style="display:flex;align-items:center;gap:5px;padding:7px 14px;border-radius:10px;background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.12);color:rgba(255,255,255,0.7);font-size:12px;cursor:pointer;transition:all 0.2s;">
                    <svg id="refreshIcon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 2v6h-6"/><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M3 22v-6h6"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/></svg>
                    刷新状态
                </button>
            </div>
        </div>

        <!-- 小太阳弧形动画 -->
        <div id="sunArcWrap" class="sun-arc-wrap">
            <svg width="100%" height="80" style="position:absolute;top:0;left:0;">
                <path id="sunTrack" fill="none" stroke="rgba(255,255,255,0.04)" stroke-width="1" stroke-dasharray="4 8"/>
            </svg>
            <div id="sunOrb" class="sun-orb">
                <div id="sunBody" class="sun-body"></div>
                <div id="sunShadow" class="sun-shadow"></div>
                <!-- 云朵跟随太阳 -->
                <span id="sunClouds"></span>
            </div>
        </div>

        <p style="font-size:13px;color:rgba(255,255,255,0.4);margin-bottom:18px;">
            管理各平台账号，扫码登录或退出已登录的账号<br>
            <span style="font-size:11px;color:rgba(255,255,255,0.25);">💡 双击上方太阳 → 退出 / 切换账号</span>
        </p>

        <!-- 全局提示条 -->
        <div id="loginTip" class="tip-bar info" style="margin-bottom:16px;display:none;">
            💡 <span id="loginTipText"></span>
        </div>

        <!-- 平台账号卡片列表（JS 动态渲染） -->
        <div id="platformCards" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:14px;">
            <div style="grid-column:1/-1;" id="platSkeleton"></div>
        </div>
    </div>
</section>

<!-- ==================== 登录弹窗（二维码+状态） ==================== -->
<div id="loginModal" class="qrcode-modal" style="display:none">
    <div class="qrcode-content" onclick="event.stopPropagation()">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;">
            <h3 id="lmTitle" style="font-size:17px;margin:0;">抖音 登录</h3>
            <button onclick="closeLoginModal()" style="width:32px;height:32px;border-radius:50%;border:none;background:rgba(255,255,255,0.08);color:rgba(255,255,255,0.6);font-size:18px;cursor:pointer;">&times;</button>
        </div>

        <!-- 状态/二维码展示区 -->
        <div id="lmBody" style="text-align:center;min-height:200px;display:flex;flex-direction:column;align-items:center;justify-content:center;">
            <div id="lmStatusIcon" class="spin-icon" style="font-size:48px;">⏳</div>
            <p id="lmStatusText" style="color:rgba(255,255,255,0.7);font-size:14px;margin-top:12px;">正在启动浏览器...</p>
        </div>

        <!-- 二维码区域（有二维码时显示） -->
        <div id="lmQrArea" style="display:none;text-align:center;padding:20px 0;">
            <img id="lmQrImage" src="" alt="扫码登录" 
                 style="max-width:220px;border-radius:12px;border:2px solid rgba(255,255,255,0.2);">
            <p style="color:rgba(255,255,255,0.55);font-size:12px;margin-top:10px;">
                请使用对应 App 扫描上方二维码
            </p>
        </div>

        <!-- 底部按钮 -->
        <div style="display:flex;justify-content:flex-end;gap:10px;margin-top:20px;padding-top:16px;border-top:1px solid rgba(255,255,255,0.08);">
            <button onclick="closeLoginModal()" style="padding:8px 20px;border-radius:10px;background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.15);color:#fff;cursor:pointer;font-size:13px;">
                取消
            </button>
            <button id="lmRetryBtn" onclick="retryLogin()" style="padding:8px 20px;border-radius:10px;background:linear-gradient(135deg,#6366f1,#8b5cf6);border:none;color:#fff;cursor:pointer;font-size:13px;font-weight:600;display:none;">
                🔄 重新扫码
            </button>
        </div>
    </div>
</div>


<!-- ==================== 历史记录页（完整版） ==================== -->
<section id="page-history" class="page-section">

    <!-- 返回首页按钮 -->
    <div class="subpage-header">
        <div class="back-home-btn" id="backHomeBtnLogin" onclick="smartGoHome()">◀ 返回首页</div>
    </div>

    <!-- 筛选工具栏 -->
    <div class="card hist-toolbar-card">
        <div class="hist-toolbar">
            <!-- 搜索框 -->
            <div class="hist-search-wrap">
                <input type="text" class="hist-search-input" id="histSearchInput"
                       placeholder="🔍 搜索标题或视频名..." oninput="onHistFilterChange()">
            </div>

            <!-- 平台筛选下拉框 -->
            <select class="hist-filter-select" id="histPlatFilter" onchange="onHistFilterChange()">
                <option value="">全部平台</option>
                <option value="douyin">抖音</option>
                <option value="kuaishou">快手</option>
                <option value="xhs">小红书</option>
                <option value="bilibili">B站</option>
                <option value="tencent">视频号</option>
                <option value="tiktok">TikTok</option>
            </select>

            <!-- 状态筛选下拉框 -->
            <select class="hist-filter-select" id="histStatusFilter" onchange="onHistFilterChange()">
                <option value="">全部状态</option>
                <option value="success">✅ 成功</option>
                <option value="error">❌ 失败</option>
                <option value="pending">⏳ 进行中</option>
                <option value="partial">⚠️ 部分成功</option>
            </select>

            <!-- 刷新按钮 -->
            <button id="btnHistRefresh" class="btn-hist-refresh" onclick="loadHistory()">
                <svg id="histRefreshIcon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-2px;margin-right:4px;"><path d="M21 2v6h-6"/><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M3 22v-6h6"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/></svg>
                刷新
            </button>
        </div>
    </div>

    <!-- 统计概览条 -->
    <div class="hist-stats-bar" id="histStatsBar">
        <span class="hist-stat-item"><b id="histTotalCnt">0</b> 条记录</span>
        <span class="hist-stat-item stat-ok"><b id="histSuccessCnt">0</b> 成功</span>
        <span class="hist-stat-item stat-fail"><b id="histErrorCnt">0</b> 失败</span>
    </div>

    <!-- 历史记录列表 -->
    <div class="card">
        <div class="card-title"><span class="icon">📋</span> 发布历史记录</div>
        <div id="historyList">
            <!-- JS 动态渲染列表项 -->
            <div class="hist-empty-state" id="histEmptyState" style="text-align:center;padding:40px;color:rgba(255,255,255,0.35);">
                <div style="font-size:44px;margin-bottom:10px;">📭</div>
                <p style="font-size:14px;">暂无发布记录</p>
                <p style="font-size:12px;margin-top:6px;color:rgba(255,255,255,0.25);">发布视频后会自动记录在这里</p>
            </div>
        </div>
    </div>
</section>


<!-- ==================== 设置页（完整版） ==================== -->
<section id="page-settings" class="page-section">

    <!-- 返回首页按钮 -->
    <div class="subpage-header">
        <div class="back-home-btn" id="backHomeBtnLogin" onclick="smartGoHome()">◀ 返回首页</div>
    </div>

    <!-- 基本设置 -->
    <div class="card">
        <div class="card-title"><span class="icon">⚙️</span> 基本设置</div>

        <div class="form-group">
            <label>浏览器模式</label>
            <select class="input-field" id="setBrowserMode" style="cursor:pointer;">
                <option value="headed">🖥️ 有头模式（弹出浏览器窗口，可观察上传过程）</option>
                <option value="headless">⏳ 无头模式（后台静默运行，不弹窗）</option>
            </select>
            <span class="field-hint">发布时是否显示浏览器窗口</span>
        </div>

        <div class="form-group">
            <label>并发上传数</label>
            <div class="slider-wrap">
                <input type="range" id="setConcurrent" min="1" max="6" value="3" class="range-slider"
                       oninput="document.getElementById('concurrentVal').textContent=this.value">
                <span class="slider-val" id="concurrentVal">3</span>
                <span class="slider-unit">个平台同时上传</span>
            </div>
            <span class="field-hint">同时向多少个平台发布视频（过多可能导致浏览器资源不足）</span>
        </div>

        <div class="form-group">
            <label>失败自动重试</label>
            <div class="toggle-row">
                <span class="toggle-switch-sm" id="toggleAutoRetry" onclick="toggleSettingBool('autoRetry')">
                    <span class="knob-sm"></span>
                </span>
                <span id="autoRetryLabel" style="font-size:13px;color:rgba(255,255,255,0.6);margin-left:8px;">开启</span>
            </div>
        </div>

        <div class="form-group" id="retryCountGroup">
            <label>重试次数</label>
            <select class="input-field" id="setRetryCount" style="cursor:pointer;width:140px;">
                <option value="1">1 次</option>
                <option value="2" selected>2 次</option>
                <option value="3">3 次</option>
            </select>
        </div>
    </div>

    <!-- 默认标签管理 -->
    <div class="card">
        <div class="card-title"><span class="icon">🏷️</span> 默认标签</div>
        <p style="font-size:12px;color:rgba(255,255,255,0.35);margin-bottom:14px;">
            发布时自动填入的默认标签（可在发布页修改）
        </p>
        <div id="defaultTagsList" class="dtags-list">
            <!-- JS 动态渲染 -->
        </div>
        <div class="dtags-input-row">
            <input type="text" class="input-field" id="newTagInput" placeholder="输入新标签名称..."
                   onkeydown="if(event.key==='Enter'){{event.preventDefault();addDefaultTag();}}" style="flex:1;">
            <button class="btn-add-tag" onclick="addDefaultTag()">+ 添加</button>
        </div>
    </div>

    <!-- 自定义壁纸 -->
    <div class="card">
        <div class="card-title"><span class="icon">🖼️</span> 自定义壁纸</div>
        <p style="font-size:12px;color:rgba(255,255,255,0.35);margin-bottom:14px;">
            上传壁纸并勾选参与轮播（最多选3张，当前已选 <span id="wpSelectedCount">0</span>/3 张）
        </p>
        <div id="wallpaperGrid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;margin-bottom:12px;">
            <!-- JS 动态渲染 -->
        </div>
        <div style="display:flex;gap:8px;">
            <label class="btn-action btn-primary" for="wpUploadInput" style="flex:1;text-align:center;">
                📤 上传壁纸
            </label>
            <input type="file" id="wpUploadInput" accept="image/jpeg,image/png,image/webp,image/bmp" style="display:none;" onchange="handleWPUpload(event)">
        </div>
    </div>

    <!-- 自定义平台图标 -->
    <div class="card">
        <div class="card-title"><span class="icon">🎨</span> 平台图标</div>
        <p style="font-size:12px;color:rgba(255,255,255,0.35);margin-bottom:14px;">
            点击图标可上传自定义图片替换，点击 × 恢复默认
        </p>
        <div id="customIconGrid" class="icon-grid"></div>
        <button class="btn-action btn-safe" onclick="resetAllIcons()" style="margin-top:12px;width:100%;">
            ↺ 全部恢复默认图标
        </button>
    </div>

    <!-- 缓存与存储 -->
    <div class="card">
        <div class="card-title"><span class="icon">🗑️</span> 缓存与存储</div>

        <div class="cache-info-grid">
            <div class="cache-info-item">
                <span class="cache-label">Cookie 目录</span>
                <span class="cache-value" id="cacheDirPath">./cookies/</span>
            </div>
            <div class="cache-info-item">
                <span class="cache-label">缓存占用</span>
                <span class="cache-value" id="cacheSizeVal">计算中...</span>
            </div>
            <div class="cache-info-item">
                <span class="cache-label">配置文件</span>
                <span class="cache-value" id="settingsFilePath">settings.json</span>
            </div>
        </div>

        <div class="action-buttons-row">
            <button class="btn-action btn-warn" onclick="doCacheClear()">
                🗑️ 清理全部缓存
            </button>
            <button class="btn-action btn-safe" onclick="doExportConfig()">
                📤 导出配置
            </button>
            <label class="btn-action btn-primary" for="importFileInput">
                📥 导入配置
            </label>
            <input type="file" id="importFileInput" accept=".json" style="display:none;"
                   onchange="doImportConfig(event)">
        </div>
    </div>

    <!-- 新手引导入口 -->
    <div class="card" style="margin-top:14px;">
        <div class="card-title"><span class="icon">📖</span> 帮助与引导</div>
        <div class="action-buttons-row">
            <button class="btn-action btn-primary-act" onclick="startGuide()">✨ 新手引导</button>
            <button class="btn-action" onclick="startEggGuide()" style="background:rgba(245,158,11,0.12);color:#fbbf24;border:1px solid rgba(245,158,11,0.22);">🥚✨ 彩蛋引导</button>
        </div>
    </div>
    <div class="card card-about">
        <div style="text-align:center;padding:10px 0;">
            <div style="font-size:32px;margin-bottom:8px;">🚀</div>
            <h3 style="color:#fff;font-size:18px;margin-bottom:4px;">Tujue AutoSend</h3>
            <p style="font-size:12px;color:rgba(255,255,255,0.35);">Version 1.0 &mdash; 多平台视频一键发布工具</p>
        </div>
        <div style="border-top:1px solid rgba(255,255,255,0.06);padding-top:14px;margin-top:8px;font-size:12px;color:rgba(255,255,255,0.5);line-height:2;">
            <b>支持平台：</b>抖音 / 快手 / B站 / 视频号 / TikTok<br>
            <b>技术栈：</b>Python + Flask + pywebview + social-auto-upload<br>
            <b>协议：</b>基于 MIT 开源协议构建
        </div>
    </div>
</section>

</div><!-- /.app-container -->



<!-- ====== 底部状态栏 ====== -->
<div class="status-bar">
    <div class="stat-item">平台数: <b id="sbPlatforms">-</b></div>
    <div class="stat-item">已登录: <b id="sbLoggedIn">0</b></div>
    <div class="stat-item">已发布: <b id="sbPublished">0</b></div>
    <div class="stat-item" style="margin-left:auto;">Tujue AutoSend v1.0</div>
</div>

<!-- ====== Toast 提示 ====== -->
<div class="toast" id="toast"></div>

<!-- ====== 二维码弹窗 ====== -->
<div class="qrcode-modal" id="qrcodeModal" onclick="if(event.target===this)this.classList.remove('show')">
    <div class="qrcode-content">
        <h3 id="qrTitle" style="font-size:17px;margin-bottom:6px;">扫码登录</h3>
        <img id="qrImage" src="" alt="二维码">
        <p id="qrHint">请使用对应 APP 扫描二维码登录</p>
        <button onclick="document.getElementById('qrcodeModal').classList.remove('show')"
                style="margin-top:14px;padding:7px 24px;border-radius:16px;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);color:#fff;cursor:pointer;font-size:13px;">
            关闭
        </button>
    </div>
</div>



<!-- ==================== JavaScript ==================== -->
<script>
// ============================================================
// 全局状态
// ============================================================
let selectedVideo = "";          // 当前选中的视频路径
let selectedPlatforms = [];      // 已选中的平台 ID 列表
let platformData = [];           // 从后端获取的平台列表
let publishedCount = 0;          // 已发布计数

// ============================================================
// 安全工具：HTML 属性转义（防 XSS）
// ============================================================
function attrEscape(s) {{
    if (s === null || s === undefined) return '';
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/'/g, '&#39;')
        .replace(/"/g, '&quot;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}}

// ============================================================
// 壁纸轮播（6秒切换）+ 自定义壁纸管理
// ============================================================
let currentWP = 0;
let wpTimer = null;

function getWPCount() {{
    return document.querySelectorAll("#wallpaper-bg .wp").length;
}}

function startWPCarousel() {{
    if (wpTimer) clearInterval(wpTimer);
    wpTimer = setInterval(() => {{
        const count = getWPCount();
        if (count < 2) return;
        const wps = document.querySelectorAll("#wallpaper-bg .wp");
        const dots = document.querySelectorAll("#wpIndicators span");
        wps[currentWP].classList.remove("active");
        if (dots[currentWP]) dots[currentWP].classList.remove("active");
        currentWP = (currentWP + 1) % count;
        wps[currentWP].classList.add("active");
        if (dots[currentWP]) dots[currentWP].classList.add("active");
    }}, 20000);  // 20 秒切换一次（降低 GPU 合成负担）
}}

function switchWP(idx) {{
    const wps = document.querySelectorAll("#wallpaper-bg .wp");
    const dots = document.querySelectorAll("#wpIndicators span");
    wps[currentWP].classList.remove("active");
    if (dots[currentWP]) dots[currentWP].classList.remove("active");
    currentWP = idx;
    wps[currentWP].classList.add("active");
    if (dots[currentWP]) dots[currentWP].classList.add("active");
}}

/** 加载自定义壁纸并更新轮播 */
async function loadWallpapers() {{
    try {{
        var resp = await fetch('/api/wallpapers');
        var json = await resp.json();
        if (json.code !== 0) return;
        var wps = json.data;

        var container = document.getElementById("wallpaper-bg");
        var indicators = document.getElementById("wpIndicators");

        // 只保留 selected 的壁纸到轮播
        var selectedWps = wps.filter(function(w) {{ return w.selected; }});
        // 清除旧的轮播元素
        container.innerHTML = '';
        indicators.innerHTML = '';
        // 添加选中的壁纸
        selectedWps.forEach(function(wp, idx) {{
            var div = document.createElement('div');
            div.className = 'wp' + (idx === 0 ? ' active' : '');
            if (wp.type === 'default') {{
                // 默认壁纸用 base64 占位，实际从已有DOM获取
                div.style.backgroundImage = wp.url ? 'url(' + wp.url + ')' : '';
                div.dataset.wpId = wp.id;
            }} else {{
                div.style.backgroundImage = 'url(' + wp.url + ')';
                div.dataset.wpId = wp.id;
            }}
            container.appendChild(div);
            // 指示器
            var span = document.createElement('span');
            span.dataset.idx = idx;
            if (idx === 0) span.classList.add('active');
            span.setAttribute('onclick', 'switchWP(' + idx + ')');
            indicators.appendChild(span);
        }});

        // 重新设置默认壁纸的 base64（前两个 .wp 需要）
        var bg1Data = 'data:image/jpeg;base64,__BG1__';
        var bg2Data = 'data:image/jpeg;base64,__BG2__';
        var allDivs = container.querySelectorAll('.wp');
        allDivs.forEach(function(d) {{
            if (d.dataset.wpId === 'default_1' && !d.style.backgroundImage) d.style.backgroundImage = 'url(' + bg1Data + ')';
            if (d.dataset.wpId === 'default_2' && !d.style.backgroundImage) d.style.backgroundImage = 'url(' + bg2Data + ')';
        }});

        currentWP = 0;
        startWPCarousel();

        // 同时更新设置页壁纸网格
        renderWPGrid(wps);
    }} catch(e) {{
        console.error('加载壁纸失败:', e);
    }}
}}

/** 渲染设置页壁纸网格（含勾选框） */
function renderWPGrid(wps) {{
    var grid = document.getElementById('wallpaperGrid');
    if (!grid) return;
    var selectedCount = wps.filter(function(w) {{ return w.selected; }}).length;
    var countEl = document.getElementById('wpSelectedCount');
    if (countEl) countEl.textContent = selectedCount;
    var html = '';
    wps.forEach(function(wp) {{
        var thumbStyle = '';
        if (wp.type === 'default') {{
            thumbStyle = 'background:linear-gradient(135deg,rgba(99,102,241,0.3),rgba(139,92,246,0.2));';
        }} else {{
            thumbStyle = 'background-image:url(' + wp.url + ');background-size:cover;background-position:center;';
        }}
        var selBorder = wp.selected ? 'border:2px solid rgba(99,102,241,0.7);' : 'border:2px solid transparent;';
        var checkIcon = wp.selected ? '\\u2705' : '\\u2b55';
        html += '<div style="border-radius:12px;overflow:hidden;' + selBorder + 'position:relative;cursor:pointer;transition:border-color 0.2s;" onclick="toggleWPSelect(\\'' + wp.id + '\\')">';
        html += '<div style="height:80px;' + thumbStyle + 'display:flex;align-items:center;justify-content:center;position:relative;">';
        if (wp.type === 'default') {{
            html += '<span style="font-size:24px;opacity:0.7;">\\u{1F305}</span>';
        }}
        // 勾选标记
        html += '<span style="position:absolute;top:4px;right:4px;font-size:14px;text-shadow:0 1px 3px rgba(0,0,0,0.6);">' + checkIcon + '</span>';
        html += '</div>';
        html += '<div style="padding:6px 8px;font-size:11px;color:rgba(255,255,255,0.6);display:flex;justify-content:space-between;align-items:center;">';
        html += '<span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:80px;">' + wp.name + '</span>';
        if (wp.type === 'custom') {{
            html += '<span style="color:#f87171;cursor:pointer;font-size:13px;line-height:1;" onclick="event.stopPropagation();deleteWP(\\'' + wp.id.replace('custom_','') + '\\')">&times;</span>';
        }}
        html += '</div></div>';
    }});
    grid.innerHTML = html;
}}

/** 切换壁纸轮播选择 */
async function toggleWPSelect(wpId) {{
    // 先获取当前选择状态
    var resp = await fetch('/api/wallpapers');
    var json = await resp.json();
    if (json.code !== 0) return;
    var wps = json.data;
    var current = wps.filter(function(w) {{ return w.selected; }}).map(function(w) {{ return w.id; }});
    var idx = current.indexOf(wpId);
    if (idx >= 0) {{
        // 取消选择（至少保留1张）
        if (current.length <= 1) {{
            showToast('轮播至少需要1张壁纸', 'error');
            return;
        }}
        current.splice(idx, 1);
    }} else {{
        // 添加选择（最多3张）
        if (current.length >= 3) {{
            showToast('轮播最多选3张壁纸', 'error');
            return;
        }}
        current.push(wpId);
    }}
    // 保存选择
    var saveResp = await fetch('/api/wallpapers/select', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ selected: current }})
    }});
    var saveJson = await saveResp.json();
    if (saveJson.code === 0) {{
        loadWallpapers();
    }} else {{
        showToast(saveJson.msg || '选择失败', 'error');
    }}
}}

/** 上传壁纸 */
async function handleWPUpload(event) {{
    var file = event.target.files[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {{
        showToast('壁纸文件不能超过 10MB', 'error');
        event.target.value = '';
        return;
    }}
    var formData = new FormData();
    formData.append('file', file);
    try {{
        var resp = await fetch('/api/wallpapers/upload', {{ method: 'POST', body: formData }});
        var json = await resp.json();
        if (json.code === 0) {{
            showToast('壁纸上传成功', 'success');
            loadWallpapers();
        }} else {{
            showToast(json.msg || '上传失败', 'error');
        }}
    }} catch(e) {{
        showToast('上传失败: ' + e.message, 'error');
    }}
    event.target.value = '';
}}

/** 删除壁纸 */
async function deleteWP(filename) {{
    if (!confirm('确定要删除这张自定义壁纸吗？')) return;
    try {{
        var resp = await fetch('/api/wallpapers/' + encodeURIComponent(filename), {{ method: 'DELETE' }});
        var json = await resp.json();
        if (json.code === 0) {{
            showToast('壁纸已删除', 'success');
            loadWallpapers();
        }} else {{
            showToast(json.msg || '删除失败', 'error');
        }}
    }} catch(e) {{
        showToast('删除失败: ' + e.message, 'error');
    }}
}}
// ============================================================
// 设置页逻辑 - 完整版
// ============================================================

function onShowSettingsPage() {{ 
    loadSettings(); 
    loadWallpapers(); 
    /* 引导入口按钮渲染（独立 try-catch 确保互不影响） */
    try {{ if (typeof renderGuideEntry === 'function') renderGuideEntry(); }} catch(e) {{ console.warn('[settings] renderGuideEntry:', e); }}
    try {{ if (typeof renderEggGuideEntry === 'function') renderEggGuideEntry(); }} catch(e) {{ console.warn('[settings] renderEggGuideEntry:', e); }}
}}

let currentSettings = {};

async function loadSettings() {
    try {
        var resp = await fetch('/api/settings');
        var json = await resp.json();
        if (json.code !== 0) return;
        var s = json.data;
        currentSettings = s;

        document.getElementById('setBrowserMode').value = s.browser_mode || 'headed';
        var cc = s.concurrent_uploads || 3;
        document.getElementById('setConcurrent').value = cc;
        document.getElementById('concurrentVal').textContent = cc;

        var ar = s.auto_retry !== false;
        setToggleUI('toggleAutoRetry', ar);
        document.getElementById('autoRetryLabel').textContent = ar ? '\u5f00\u542f' : '\u5173\u95ed';
        document.getElementById('retryCountGroup').style.display = ar ? '' : 'none';
        if (ar) document.getElementById('setRetryCount').value = s.retry_count || 2;

        renderDefaultTags(s.default_tags || []);
        document.getElementById('cacheDirPath').textContent = (s.cookies_dir || './cookies/').replace(/\\\\\\\\/g,'/');
        document.getElementById('cacheSizeVal').textContent = s.cache_size_human || '0 B';
        var sf = (s.settings_file || 'settings.json').replace(/\\\\\\\\/g,'/');
        document.getElementById('settingsFilePath').textContent = sf.split('/').pop();
    } catch(e) { console.warn('loadSettings error:', e); }
}

function renderDefaultTags(tags) {
    var c = document.getElementById('defaultTagsList');
    if (!tags || !tags.length) { c.innerHTML = '<span style="font-size:12px;color:rgba(255,255,255,0.3);padding:6px 0;">\u6682\u65e0\u9ed8\u8ba4\u6807\u7bfe</span>'; return; }
    var h = '';
    for (var i=0;i<tags.length;i++) h+='<span class="dtag">'+esc(tags[i])+'<span class="dtag-remove" onclick="removeDefaultTag('+i+',event)">\u2715</span></span>';
    c.innerHTML = h;
}
function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}

function addDefaultTag() {
    var v = document.getElementById('newTagInput').value.trim();
    if(!v){showToast('\u8bf7\u8f93\u5165\u6807\u7bfe\u540d','error');return;}
    if(!currentSettings.default_tags) currentSettings.default_tags=[];
    if(currentSettings.default_tags.indexOf(v)>=0){showToast('\u8be5\u6807\u7bfe\u5df2\u5b58\u5728','error');return;}
    currentSettings.default_tags.push(v);
    document.getElementById('newTagInput').value='';
    renderDefaultTags(currentSettings.default_tags);
    saveCurrentSettings();
}

function removeDefaultTag(i,e){e.stopPropagation();if(!currentSettings.default_tags)return;currentSettings.default_tags.splice(i,1);renderDefaultTags(currentSettings.default_tags);saveCurrentSettings();}

function toggleSettingBool(k){
    var nv=!currentSettings[k]; currentSettings[k]=nv;
    if(k==='autoRetry'){setToggleUI('toggleAutoRetry',nv);document.getElementById('autoRetryLabel').textContent=nv?'\u5f00\u542f':'\u5173\u95ed';document.getElementById('retryCountGroup').style.display=nv?'':'none';}
    saveCurrentSettings();
}
function setToggleUI(id,on){var el=document.getElementById(id);if(on)el.classList.add('on');else el.classList.remove('on');}

async function saveCurrentSettings(){
    currentSettings.browser_mode=document.getElementById('setBrowserMode').value;
    currentSettings.concurrent_uploads=parseInt(document.getElementById('setConcurrent').value)||3;
    currentSettings.retry_count=parseInt(document.getElementById('setRetryCount').value)||2;
    try{await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(currentSettings)});}catch(e){}
}

async function doCacheClear(){
    if(!confirm('\u26a0\ufe0f \u786e\u5b9a\u6e05\u7406\u5168\u90e8 Cookie \u7f13\u58de?'))return;
    try{
        var r=await fetch('/api/cache/clear',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({clear_all:true})});
        var j=await r.json();
        if(j.code===0){showToast(j.msg||'\u6e05\u7406\u5b8c\u6210','success');loadSettings();}
        else showToast(j.msg||'\u6e05\u7406\u5931\u8d25','error');
    }catch(e){showToast('\u7f51\u7edc\u9519\u8bef:'+e.message,'error')}
}

async function doExportConfig(){
    try{
        var r=await fetch('/api/config/export'),j=await r.json();
        if(j.code!==0)return showToast(j.msg||'\u5bfc\u51fa\u5931\u8d25','error');
        var b=new Blob([JSON.stringify(j.data,null,2)],{type:'application/json'});
        var a=document.createElement('a');a.href=URL.createObjectURL(b);
        a.download='tujue_config_'+new Date().toISOString().slice(0,10)+'.json';a.click();URL.revokeObjectURL(a.href);
        showToast('\u2705 \u914d\u7f6e\u5df2\u5bfc\u51fa','success');
    }catch(e){showToast('\u5bfc\u51fa\u5931\u8d25:'+e.message,'error')}
}

function doImportConfig(evt){
    var f=evt.target.files[0];if(!f)return;
    var rd=new FileReader();
    rd.onload=function(ev){
        try{var d=JSON.parse(ev.target.result);}catch(e){showToast('Invalid JSON','error');return;}
        importCfg(d);
    };
    rd.readAsText(f);evt.target.value='';
}

async function importCfg(data){
    if(!data.settings&&!data.browser_mode)return showToast('\u65e0\u6cd5\u8bc6\u522b','error');
    try{
        var p=data.settings||data,clean={},ok=['browser_mode','concurrent_uploads','default_tags','auto_retry','retry_count'];
        for(var k in p)if(ok.indexOf(k)>=0)clean[k]=p[k];
        var r=await fetch('/api/config/import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({settings:clean})});
        var j=await r.json();
        if(j.code===0){showToast('\u2705 \u5bfc\u5165\u6210\u529f','success');loadSettings();}
        else showToast(j.msg||'\u5bfc\u5165\u5931\u8d25','error');
    }catch(e){showToast('err:'+e.message,'error')}
}


// ============================================================
// 历史记录页逻辑 - 完整版
// ============================================================

let allHistoryRecords = [];       // 全量历史记录（用于前端筛选）
let histFilterTimer = null;        // 搜索防抖定时器

/** 切到历史记录页时触发 */
function onShowHistoryPage() {{ loadHistory(); }}

/**
 * 加载历史记录列表（调用后端 API）
 */
async function loadHistory() {{
    var btn = document.getElementById('btnHistRefresh');
    if (btn && btn.classList.contains('spinning')) return;
    if (btn) {{
        var ico = document.getElementById('histRefreshIcon');
        ico.classList.remove('click-spin'); void ico.offsetWidth; ico.classList.add('click-spin');
        setTimeout(() => ico.classList.remove('click-spin'), 500);
        btn.classList.add('spinning'); btn.disabled = true;
    }}
    var listEl = document.getElementById('historyList');
    var emptyEl = document.getElementById('histEmptyState');

    // 显示加载状态
    if (listEl) {{
        var loadingHtml = '<div style="text-align:center;padding:40px;color:rgba(255,255,255,0.4);">'
            + '<div style="font-size:32px;margin-bottom:8px;">⏳</div>'
            + '<p style="font-size:13px;">正在加载...</p></div>';
        listEl.innerHTML = loadingHtml;
    }}

    try {{
        var resp = await fetch('/api/history?size=100');   // 一次加载最近100条
        var json = await resp.json();
        if (json.code !== 0) return;

        allHistoryRecords = json.data.records || [];
        var stats = json.data.stats || {{}};

        // 更新统计条
        document.getElementById('histTotalCnt').textContent = stats.total || 0;
        document.getElementById('histSuccessCnt').textContent = stats.success || 0;
        document.getElementById('histErrorCnt').textContent = stats.error || 0;

        renderHistoryList(allHistoryRecords);

    }} catch (e) {{
        console.error('loadHistory error:', e);
        listEl.innerHTML = '<div style="text-align:center;padding:30px;color:#f87171;">'
            + '\u274C 加载失败: ' + e.message + '</div>';
    }} finally {{
        if (btn) {{ btn.classList.remove('spinning'); btn.disabled = false; }}
    }}
}}

/**
 * 根据当前筛选条件渲染列表
 * @param {Array} records - 要渲染的数据数组
 */
function renderHistoryList(records) {{
    var listEl = document.getElementById('historyList');

    if (!records || records.length === 0) {{
        listEl.innerHTML =
            '<div class="hist-empty-state" style="text-align:center;padding:40px;color:rgba(255,255,255,0.35);">'
            + '<div style="font-size:44px;margin-bottom:10px;">📭</div>'
            + '<p style="font-size:14px;">暂无发布记录</p>'
            + '<p style="font-size:12px;margin-top:6px;color:rgba(255,255,255,0.25);">发布视频后会自动记录在这里</p>'
            + '</div>';
        return;
    }}

    var html = '';
    for (var i = 0; i < records.length; i++) {{
        var rec = records[i];

        // 状态映射
        var statusMap = {{
            'success':  {{cls:'hst-success', text:'\u2705 \u53d1\u5e03\u6210\u529f'}},
            'error':    {{cls:'hst-error',   text:'\u274C \u53d1\u5e03\u5931\u8d25'}},
            'pending':  {{cls:'hst-pending', text:'\u23f3 \u8fdb\u884c\u4e2d'}},
            'partial':  {{cls:'hst-partial', text:'\u26a0\ufe0f \u90e8\u5206\u6210\u529f'}},
        }};
        var st = statusMap[rec.status] || statusMap['pending'];

        // 平台标签
        var platTagsHtml = '';
        var platforms = rec.platforms || [];
        var details = rec.platform_details || [];

        for (var j = 0; j < platforms.length; j++) {{
            var pid = platforms[j];
            // 在 details 中查找该平台的结果
            var detail = null;
            for (var d = 0; d < details.length; d++) {{
                if (details[d].platform === pid) {{ detail = details[d]; break; }}
            }}
            var tagCls = (detail && detail.status === 'success') ? 'plat-tag-ok' : ((detail && detail.status === 'error') ? 'plat-tag-err' : '');
            var dotIcon = (detail && detail.status === 'success') ? '\u2705' : ((detail && detail.status === 'error') ? '\u274C' : '\u23F3');
            var platName = getPlatName(pid);
            platTagsHtml += '<span class="hist-plat-tag ' + tagCls + '">' + dotIcon + ' ' + esc(platName) + '</span>';
        }}

        // 操作按钮（只有失败/部分成功的可重试）
        var actionsHtml = '';
        if (rec.status === 'error' || rec.status === 'partial') {{
            actionsHtml += '<button class="btn-hist-action btn-retry" onclick="doRetryHistory(\\'' + attrEscape(rec.id) + '\\',event)">🔄 重试</button>';
        }}
        actionsHtml += '<button class="btn-hist-action btn-del" onclick="doDeleteHistory(\\'' + attrEscape(rec.id) + '\\',event)">🗑 删除</button>';

        // 视频名
        var videoName = rec.video_name || (rec.video_path ? rec.video_path.split('/').pop().split("\\\\").pop() : '');

        html += '<div class="hist-record">';
        html += '<div class="hist-rec-header">';
        html += '<div class="hist-rec-title">' + esc(rec.title || '\u65e0\u6807\u9898') + '</div>';
        html += '<span class="hist-rec-status ' + st.cls + '">' + st.text + '</span>';
        html += '</div>';  // end header

        html += '<div class="hist-rec-body">';
        html += '<div class="hist-rec-info">';

        // 元信息行
        html += '<div class="hist-rec-meta">';
        html += '<span>📁 ' + esc(videoName) + '</span>';
        if (rec.created_at) html += '<span>🕐 ' + esc(rec.created_at) + '</span>';
        if (rec.finished_at) html += '<span>✅ ' + esc(rec.finished_at) + '</span>';
        html += '</div>';

        // 平台标签组
        if (platTagsHtml) {{
            html += '<div class="hist-rec-platforms">' + platTagsHtml + '</div>';
        }}

        html += '</div>';  // end info

        // 右侧操作按钮
        html += '<div class="hist-rec-actions">' + actionsHtml + '</div>';
        html += '</div>';  // end body
        html += '</div>';  // end record
    }}

    listEl.innerHTML = html;
}}

/** 获取平台中文名 */
function getPlatName(pid) {{
    var names = {{
        douyin:'\u6296\u97f3', kuaishou:'\u5feb\u624b', xhs:'\u5c0f\u7ea2\u4e66',
        bilibili:'B\u7ad9', tencent:'\u89c6\u9891\u53f7', tiktok:'TikTok',
        youtube:'YouTube', instagram:'Instagram', x:'X',
    }};
    return names[pid] || pid;
}}

/** 筛选条件变化时触发（防抖搜索） */
function onHistFilterChange() {{
    if (histFilterTimer) clearTimeout(histFilterTimer);
    histFilterTimer = setTimeout(function() {{
        filterHistory();
    }}, 300);  // 300ms 防抖
}}

/** 前端筛选逻辑（在已加载数据上过滤） */
function filterHistory() {{
    var keyword = document.getElementById('histSearchInput').value.trim().toLowerCase();
    var platFilter = document.getElementById('histPlatFilter').value;
    var statusFilter = document.getElementById('histStatusFilter').value;

    var filtered = allHistoryRecords.filter(function(rec) {{

        // 关键词匹配标题或视频名
        if (keyword) {{
            var titleMatch = (rec.title || '').toLowerCase().indexOf(keyword) >= 0;
            var videoMatch = (rec.video_name || '').toLowerCase().indexOf(keyword) >= 0;
            if (!titleMatch && !videoMatch) return false;
        }}

        // 平台筛选
        if (platFilter) {{
            var hasPlat = (rec.platforms || []).indexOf(platFilter) >= 0;
            if (!hasPlat) return false;
        }}

        // 状态筛选
        if (statusFilter && rec.status !== statusFilter) return false;

        return true;
    }});

    renderHistoryList(filtered);
}}

/**
 * 重试某条失败记录
 * 调用 /api/history/retry/<id> 获取参数 → 自动跳转发布页并填充
 */
async function doRetryHistory(recordId, evt) {{
    if (evt) evt.stopPropagation();

    try {{
        var r = await fetch('/api/history/retry/' + recordId);
        var j = await r.json();
        if (j.code !== 0) {{ showToast(j.msg || '\u83b7\u53d6\u91cd\u8bd5\u4fe1\u606f\u5931\u8d25', 'error'); return; }}

        var data = j.data;

        // ---- 填充发布表单 ----
        selectedVideo = data.video;
        selectedPlatforms = data.platforms || [];

        document.getElementById('titleInput').value = data.title || '';
        document.getElementById('descInput').value = data.desc || '';

        // 设置选中状态
        data.platforms.forEach(function(pid) {{
            var btns = document.querySelectorAll('.platform-btn[data-id="' + pid + '"]');
            btns.forEach(function(b) {{ b.classList.add('selected'); }});
        }});
        updateStatusBar();

        // 切到发布页并提示用户（不用 goToPage，避免清除刚设置的视频状态）
        goToPageWithoutClear('page-publish');

        showToast('\u2705 \u5df2\u586b\u5145\u91cd\u8bd5\u53c2\u6570\uff0c\u70b9\u51fb\u53d1\u5e03\u6309\u94ae\u5373\u53ef', 'success');

    }} catch (e) {{
        showToast('\u91cd\u8bd5\u5931\u8d25: ' + e.message, 'error');
    }}
}}

/**
 * 删除一条历史记录
 * POST /api/history/delete/<id>
 */
async function doDeleteHistory(recordId, evt) {{
    if (evt) evt.stopPropagation();

    if (!confirm('\u786e\u5b9a\u5220\u9664\u8be9\u6761\u53d1\u5e03\u8bb0\u5f55?')) return;

    try {{
        var r = await fetch('/api/history/delete/' + recordId, {{ method: 'POST' }});
        var j = await r.json();
        if (j.code === 0) {{
            showToast('\u274C \u8bb0\u5f55\u5df2\u5220\u9664', 'info');
            loadHistory();  // 刷新列表
        }} else {{
            showToast(j.msg || '\u5220\u9664\u5931\u8d25', 'error');
        }}
    }} catch (e) {{
        showToast('\u7f51\u7edc\u9519\u8bef: ' + e.message, 'error');
    }}
}}


// ============================================================
// 导航首页 → 子页面 跳转
// ============================================================
function goToPage(pageId) {{
    // 隐藏首页及所有子页面
    document.getElementById('page-home').classList.remove('active');
    document.querySelectorAll(".page-section").forEach(function(p) {{
        p.classList.remove("active");
    }});
    // 清除首页卡片 3D 残留
    var home = document.getElementById('page-home');
    home.querySelectorAll(".nav-card").forEach(function(c) {{ c.style.transform = ""; }});

    var target = document.getElementById(pageId);
    if (target) target.classList.add('active');
    // 离开登录页时停止自动检测
    if (pageId !== 'page-login') stopAutoCookieCheck();
    triggerPageCallback(pageId);
}}

/** 跳转页面但不清理发布状态（供重试历史等内部流程使用） */
function goToPageWithoutClear(pageId) {{
    document.getElementById('page-home').classList.remove('active');
    document.querySelectorAll(".page-section").forEach(function(p) {{
        p.classList.remove("active");
    }});
    var home = document.getElementById('page-home');
    home.querySelectorAll(".nav-card").forEach(function(c) {{ c.style.transform = ""; }});
    var target = document.getElementById(pageId);
    if (target) target.classList.add('active');
    if (pageId !== 'page-login') stopAutoCookieCheck();
    triggerPageCallback(pageId);
}}

/** 清理发布页面的视频选择状态（保留标题/描述文本） */
function clearPublishState() {{
    selectedVideo = "";
    var zone = document.getElementById("uploadZone");
    if (zone) zone.classList.remove("has-file");
    var hint = document.getElementById("uploadHint");
    if (hint) hint.style.display = "";
    var preview = document.getElementById("videoPreview");
    if (preview) {{
        if (preview.src && preview.src.startsWith('blob:')) URL.revokeObjectURL(preview.src);
        preview.src = "";
        preview.style.display = "none";
    }}
    var fileInfo = document.getElementById("fileInfo");
    if (fileInfo) fileInfo.style.display = "none";
    var input = document.getElementById("videoInput");
    if (input) input.value = "";
}}

// ============================================================
// 返回首页（从任意子页）
// ============================================================
function goHome() {{
    // 清理发布页状态
    clearPublishState();
    stopAutoCookieCheck();
    // 隐藏所有子页面和首页
    document.querySelectorAll(".page-section").forEach(function(p) {{
        p.classList.remove("active");
    }});
    document.querySelectorAll(".page-home").forEach(function(p) {{
        p.classList.remove("active");
    }});
    // 显示首页
    document.getElementById('page-home').classList.add('active');
}}

/** 智能返回首页：有登录进行中时阻止跳转 */
function smartGoHome() {{
    if (curLoginSid) {{
        goHomeDisabled(document.getElementById('backHomeBtnLogin'));
        return;
    }}
    goHome();
}}

/* 失效的返回首页按钮（登录管理页专用）：只给反馈，不跳转 */
function goHomeDisabled(btn) {{
    btn.classList.remove('shaking');
    void btn.offsetWidth;
    btn.classList.add('shaking');
    setTimeout(function() {{ btn.classList.remove('shaking'); }}, 350);
}}

// ============================================================
// 页面切换回调触发（兼容旧逻辑）
// ============================================================
function triggerPageCallback(pageId) {{
    if (pageId === "page-login" && typeof onShowLoginPage === "function") {{
        onShowLoginPage();
    }}
    if (pageId === "page-settings" && typeof onShowSettingsPage === "function") {{
        onShowSettingsPage();
    }}
    if (pageId === "page-history" && typeof onShowHistoryPage === "function") {{
        onShowHistoryPage();
    }}
}}

// ============================================================
// 视频选择与预览
// ============================================================
function handleVideoSelect(event) {{
    const file = event.target.files[0];
    if (!file) return;

    // 验证文件类型
    const validExts = [".mp4",".mov",".avi",".mkv",".m4v",".webm",".flv",".wmv"];
    const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
    if (!validExts.includes(ext)) {{
        showToast("不支持的视频格式","error");
        return;
    }}

    // 先在本地显示预览
    const zone = document.getElementById("uploadZone");
    zone.classList.add("has-file");
    document.getElementById("uploadHint").style.display = "none";

    const preview = document.getElementById("videoPreview");
    // 释放旧的 Blob URL 防止内存泄漏
    if (preview.src && preview.src.startsWith('blob:')) {{
        URL.revokeObjectURL(preview.src);
    }}
    preview.src = URL.createObjectURL(file);
    preview.style.display = "inline-block";

    document.getElementById("fileInfo").style.display = "block";
    document.getElementById("fileInfo").innerHTML =
        `📁 <b>${{file.name}}</b> &nbsp; ${{(file.size/1024/1024).toFixed(1)}} MB &nbsp; <span id="uploadStatus" style="color:rgba(255,255,255,0.4);">\\u4E0A\\u4F20\\u4E2D...</span>`;

    // 上传视频到服务器，获取真实文件路径
    uploadVideoFile(file);
}}

/** 上传视频文件到服务器，获取服务端绝对路径 */
async function uploadVideoFile(file) {{
    const formData = new FormData();
    formData.append('file', file);

    try {{
        const resp = await fetch('/api/upload/video', {{
            method: 'POST',
            body: formData,
        }});
        const result = await resp.json();

        if (result.code === 0) {{
            selectedVideo = result.data.path;  // 服务器端绝对路径
            const statusEl = document.getElementById('uploadStatus');
            if (statusEl) statusEl.textContent = ' \\u2705 \\u5DF2\\u5C31\\u7EEA';
            if (statusEl) statusEl.style.color = '#4ade80';
        }} else {{
            showToast(result.msg || '\\u4E0A\\u4F20\\u5931\\u8D25', 'error');
            const statusEl = document.getElementById('uploadStatus');
            if (statusEl) {{ statusEl.textContent = ' \\u274C \\u4E0A\\u4F20\\u5931\\u8D25'; statusEl.style.color = '#f87171'; }}
        }}
    }} catch(e) {{
        showToast('\\u4E0A\\u4F20\\u51FA\\u9519: ' + e.message, 'error');
        const statusEl = document.getElementById('uploadStatus');
        if (statusEl) {{ statusEl.textContent = ' \\u274C \\u7F51\\u7EDC\\u9519\\u8BEF'; statusEl.style.color = '#f87171'; }}
    }}
}}

// 拖拽上传支持（在 DOMContentLoaded 中初始化）
function initUploadZone() {{
    const uploadZone = document.getElementById("uploadZone");
    if (!uploadZone) return;
    uploadZone.addEventListener("dragover", e => {{
        e.preventDefault(); uploadZone.style.borderColor = "rgba(99,102,241,0.55)";
    }});
    uploadZone.addEventListener("dragleave", () => {{
        uploadZone.style.borderColor = "";
    }});
    uploadZone.addEventListener("drop", e => {{
        e.preventDefault();
        uploadZone.style.borderColor = "";
        if (e.dataTransfer.files.length > 0) {{
            document.getElementById("videoInput").files = e.dataTransfer.files;
            handleVideoSelect({{target: {files: e.dataTransfer.files}}});
        }}
    }});
}}

// ============================================================
// 标签选择
// ============================================================
function toggleTag(el) {{
    el.classList.toggle("selected");
}}
function addCustomTag() {{
    const input = document.getElementById("customTagInput");
    const val = input.value.trim();
    if (!val) return;
    
    const tagEl = document.createElement("span");
    tagEl.className = "tag-pill selected";
    tagEl.textContent = "#"+val;
    tagEl.onclick = function() {{ toggleTag(this); }};
    
    const row = document.getElementById("tagsRow");
    row.insertBefore(tagEl, input);
    input.value = "";
}}

// ============================================================
// 定时发布开关
// ============================================================
function toggleSchedule() {{
    const toggle = document.getElementById("schedToggle");
    const picker = document.getElementById("datetimePicker");
    const row    = document.getElementById("schedRow");
    const knob   = document.getElementById("schedKnob");
    const badge  = document.getElementById("schedBadge");

    toggle.classList.toggle("on");
    row.classList.toggle("sched-on");
    picker.classList.toggle("show");

    // knob 弹跳动画
    knob.classList.remove("pop");
    void knob.offsetWidth; // reflow 强制重新触发
    knob.classList.add("pop");

    const isOn = toggle.classList.contains("on");
    badge.textContent = isOn ? "开" : "关";

    if (isOn) {{
        // 默认设置为2小时后
        const now = new Date();
        now.setHours(now.getHours()+2);
        const y = now.getFullYear(), m=String(now.getMonth()+1).padStart(2,"0"),
              d=String(now.getDate()).padStart(2,"0"), h=String(now.getHours()).padStart(2,"0"),
              min=String(now.getMinutes()).padStart(2,"0");
        picker.value = `${{y}}-${{m}}-${{d}}T${{h}}:${{min}}`;
    }}
}}

// ============================================================
// 平台网格渲染 + 选择
// ============================================================
function renderPlatformGrid() {{
    const grid = document.getElementById("platformGrid");
    grid.innerHTML = "";

    platformData.forEach(p => {{
        const isSupported = p.supported !== false;
        const btn = document.createElement("div");
        btn.className = `platform-btn ${{selectedPlatforms.includes(p.id) ? "selected" : ""}}`;
        btn.dataset.id = p.id;
        btn.onclick = function() {{
            if (!isSupported) {{
                showToast(`${{p.name}} 暂不支持发布`,"info");
                return;
            }}
            
            if (selectedPlatforms.includes(p.id)) {{
                selectedPlatforms = selectedPlatforms.filter(x => x!==p.id);
                this.classList.remove("selected");
                /* E7b: 取消选中收缩动画 */
                this.classList.remove("p-shrink");
                void this.offsetWidth;
                this.classList.add("p-shrink");
                setTimeout(() => this.classList.remove("p-shrink"), 600);
            }} else {{
                selectedPlatforms.push(p.id);
                this.classList.add("selected");
                /* E7: 选中弹跳动画 */
                this.classList.remove("p-bounce");
                void this.offsetWidth;  /* 触发 reflow 重置动画 */
                this.classList.add("p-bounce");
                setTimeout(() => this.classList.remove("p-bounce"), 600);
            }}
            updateStatusBar();
            updateBilibiliZoneCard();
        }};

        const statusClass = p.logged_in ? "green" : "red";
        const statusText = p.logged_in ? "已登录" : "未登录";
        const iconHtml = getPlatformIcon(p.id);

        btn.innerHTML = `
            <div class="p-icon">${{iconHtml}}</div>
            <div class="p-name">${{p.name}}</div>
            <div class="p-status">
                <span class="dot ${{statusClass}}"></span> ${{statusText}}
                ${!isSupported ? '<span class="unsupported-badge">暂不支持</span>' : ""}
            </div>`;
        grid.appendChild(btn);
    }});

    updateStatusBar();
}}

function updateStatusBar() {{
    var elPlat = document.getElementById("sbPlatforms");
    var elLogin = document.getElementById("sbLoggedIn");
    var elPub = document.getElementById("sbPublished");
    var platVal = platformData.length;
    var loginVal = platformData.filter(p=>p.logged_in).length;
    /* E9: 数字滚动 */
    if (elPlat.textContent !== String(platVal)) animateNumber(elPlat, platVal);
    if (elLogin.textContent !== String(loginVal)) animateNumber(elLogin, loginVal);
    if (elPub.textContent !== String(publishedCount)) animateNumber(elPub, publishedCount);
}}

// ============================================================
// B站分区选择逻辑
// ============================================================
let biliZonesData = [];  // B站分区数据缓存

async function loadBiliZones() {{
    if (biliZonesData.length > 0) return;  // 已缓存则跳过
    try {{
        const resp = await fetch("/api/bilibili/zones");
        const result = await resp.json();
        if (result.code === 0) {{
            biliZonesData = result.data;
            renderBiliZoneSelect();
        }}
    }} catch(e) {{
        console.error("加载B站分区失败:", e);
    }}
}}

function renderBiliZoneSelect() {{
    const cs = customSelects["biliZoneSelect"];
    if (cs) {{
        const opts = biliZonesData.map(z => ({{ value: z.tid, text: z.name }}));
        cs.updateOptions(opts);
    }}
    updateBiliSubZones();
}}

function updateBiliSubZones() {{
    const mainSel = document.getElementById("biliZoneSelect");
    const mainTid = parseInt(mainSel.value);
    const zone = biliZonesData.find(z => z.tid === mainTid);
    const cs = customSelects["biliSubZoneSelect"];
    if (cs) {{
        const opts = (zone && zone.sub) ? zone.sub.map(s => ({{ value: s.tid, text: s.name }})) : [];
        cs.updateOptions(opts);
    }}
}}

function updateBilibiliZoneCard() {{
    const card = document.getElementById("bilibiliZoneCard");
    if (selectedPlatforms.includes("bilibili")) {{
        card.style.display = "block";
        loadBiliZones();
    }} else {{
        card.style.display = "none";
    }}
}}

function getSelectedBiliTid() {{
    if (!selectedPlatforms.includes("bilibili")) return 21;
    const subSelect = document.getElementById("biliSubZoneSelect");
    if (subSelect.value) return parseInt(subSelect.value);
    const mainSelect = document.getElementById("biliZoneSelect");
    return parseInt(mainSelect.value) || 21;
}}

// ============================================================
// ============================================================
// 登录管理页 - 完整版（异步会话模式）
// ============================================================
const PLAT_ICONS = {{
    douyin:   {{svg:'<svg viewBox="0 0 48 48" fill="none"><path d="M33 14c-2-1-3-3-3-5h-5v22c0 2.2-1.8 4-4 4s-4-1.8-4-4 1.8-4 4-4c.7 0 1.4.2 2 .5v-5.2c-.7-.2-1.3-.3-2-.3-5 0-9 4-9 9s4 9 9 9 9-4 9-9V21c2 1.5 4.5 2 7 2v-5c-2 0-3.5-.8-4-2z" fill="#25F4EE"/><path d="M33 14c-2-1-3-3-3-5h-5v22c0 2.2-1.8 4-4 4s-4-1.8-4-4 1.8-4 4-4c.7 0 1.4.2 2 .5v-5.2c-.7-.2-1.3-.3-2-.3-5 0-9 4-9 9s4 9 9 9 9-4 9-9V21c2 1.5 4.5 2 7 2v-5c-2 0-3.5-.8-4-2z" fill="#FE2C55" opacity=".7" transform="translate(1 1)"/></svg>'}},
    kuaishou: {{svg:'<svg viewBox="0 0 48 48" fill="none"><circle cx="24" cy="22" r="10" stroke="#FF4906" stroke-width="3" fill="none"/><path d="M17 33l3-5h8l3 5" stroke="#FF4906" stroke-width="2.5" stroke-linecap="round" fill="none"/><circle cx="21" cy="20" r="2" fill="#FF4906"/><circle cx="27" cy="20" r="2" fill="#FF4906"/></svg>'}},
    xhs:      {{svg:'<svg viewBox="0 0 48 48" fill="none"><rect x="12" y="12" width="24" height="24" rx="4" stroke="#FF2442" stroke-width="2.5" fill="none"/><line x1="12" y1="20" x2="36" y2="20" stroke="#FF2442" stroke-width="2"/><line x1="20" y1="12" x2="20" y2="36" stroke="#FF2442" stroke-width="2"/><circle cx="28" cy="28" r="3" fill="#FF2442" opacity=".8"/></svg>'}},
    bilibili: {{svg:'<svg viewBox="0 0 48 48" fill="none"><rect x="10" y="16" width="28" height="20" rx="4" stroke="#00A1D6" stroke-width="2.5" fill="none"/><circle cx="19" cy="26" r="2.5" fill="#00A1D6"/><circle cx="29" cy="26" r="2.5" fill="#00A1D6"/><path d="M16 12l4 4M32 12l-4 4" stroke="#00A1D6" stroke-width="2.5" stroke-linecap="round"/></svg>'}},
    tencent:  {{svg:'<svg viewBox="0 0 48 48" fill="none"><path d="M35 25c0-6-5-11-11-11s-11 5-11 11c0 3.5 1.5 6.5 4 8.5l-1.5 3c-.3.5.2 1 .7.8l3.5-1.2c1.4.5 2.8.8 4.3.8s2.9-.3 4.3-.8l3.5 1.2c.5.2 1-.3.7-.8L31 33.5c2.5-2 4-5 4-8.5z" fill="#07C160"/><circle cx="20" cy="24" r="2" fill="#fff"/><circle cx="28" cy="24" r="2" fill="#fff"/></svg>'}},
    tiktok:   {{svg:'<svg viewBox="0 0 48 48" fill="none"><path d="M32 12c0 0-1.5 4-5 4v-4h-4v20c0 2.2-1.8 4-4 4s-4-1.8-4-4 1.8-4 4-4c.5 0 1 .1 1.5.3V14c0-2 2-5 5-5h2v5c3.5 0 5-4 5-4v2z" fill="#25F4EE"/><path d="M32 14c0 0-1.5 4-5 4v-4h-4v20c0 2.2-1.8 4-4 4s-4-1.8-4-4 1.8-4 4-4c.5 0 1 .1 1.5.3V16c0-2 2-5 5-5h2v5c3.5 0 5-4 5-4v2z" fill="#FE2C55" opacity=".6" transform="translate(1 1)"/></svg>'}},
    youtube:  {{svg:'<svg viewBox="0 0 48 48" fill="none"><rect x="6" y="14" width="36" height="20" rx="5" stroke="#FF0000" stroke-width="2.5" fill="none"/><path d="M21 18v12l10-6-10-6z" fill="#FF0000"/></svg>'}},
    instagram:{{svg:'<svg viewBox="0 0 48 48" fill="none"><defs><linearGradient id="igc" x1="0" y1="48" x2="48" y2="0"><stop offset="0" stop-color="#FFDC80"/><stop offset=".2" stop-color="#F77737"/><stop offset=".5" stop-color="#E1306C"/><stop offset=".8" stop-color="#C13584"/><stop offset="1" stop-color="#833AB4"/></linearGradient></defs><rect x="12" y="12" width="24" height="24" rx="6" stroke="url(#igc)" stroke-width="2.5" fill="none"/><circle cx="24" cy="24" r="6" stroke="url(#igc)" stroke-width="2.5" fill="none"/><circle cx="33" cy="15" r="2" fill="#E1306C"/></svg>'}},
    x:        {{svg:'<svg viewBox="0 0 48 48" fill="none"><path d="M26.3 21.2L35.5 11h-2.2l-8 8.9L18.8 11H11l9.7 13.6L11 35h2.2l8.5-9.4L29.2 35H37l-10.7-13.8zm-3 3.3l-1-1.4-7.8-11h3.4l5 7 1 1.4 8.2 11.5h-3.4l-5.4-7.5z" fill="#ccc"/></svg>'}},
}};

let curLoginSid = null;       // 当前登录 session_id
let curLoginPlat = null;      // 当前登录的平台 ID
let loginPollTimer = null;    // 轮询定时器

/** 切到登录页时触发 */
function onShowLoginPage() {{ renderPlatformCards(); initSunArc(); startAutoCookieCheck(); }}

// ============================================================
// 小太阳弧形动画（顺时针高弧线 + 日出日落 + 云朵 + 可拖动）
// ============================================================
var sunAngle = 0;           // 0=左(日出) ~ 1=右(日落)
var sunDragging = false;
var sunAutoSpeed = 0.00028;   // 每帧增量（~60秒一圈）
var sunAnimFrame = null;
var sunInited = false;
var sunCloudEls = [];        // 缓存云朵元素
var sunState = 'visible';    // visible | falling | rising
var FALL_FADE_START = 0.92;  // 开始淡出
var RISE_FADE_END = 0.08;    // 淡入完成

function initSunArc() {{
    var wrap = document.getElementById('sunArcWrap');
    if (!wrap) return;
    /* 首次初始化或动画已停止（如爆炸后）→ 重启 */
    if (sunInited && sunAnimFrame) return;
    sunInited = true;

    /* 重置所有状态（防止爆炸/切换页面后残留脏状态） */
    sunAngle = 0;
    sunState = 'visible';
    sunDragging = false;
    _sunExploded = false;
    var orb = document.getElementById('sunOrb');
    if (orb) {
        orb.className = 'sun-orb visible';
        orb.style.transform = '';
        orb.style.left = '';
        orb.style.top = '';
        orb.style.opacity = '';
    }
    drawSunTrack();
    createClouds();
    updateSunPosition();
    startSunAnimation();
    // 拖动事件
    var orb = document.getElementById('sunOrb');
    if (!orb) return;
    orb.addEventListener('mousedown', onSunDragStart);
    orb.addEventListener('touchstart', onSunDragStart, {{passive: false}});
    orb.addEventListener('dblclick', onSunDblClick);
    document.addEventListener('mousemove', onSunDragMove);
    document.addEventListener('touchmove', onSunDragMove, {{passive: false}});
    document.addEventListener('mouseup', onSunDragEnd);
    document.addEventListener('touchend', onSunDragEnd);
    window.addEventListener('resize', function() {{ drawSunTrack(); updateSunPosition(); }});
}}

/* 绘制高弧形轨迹（左右留白，不贴边） */
function drawSunTrack() {{
    var wrap = document.getElementById('sunArcWrap');
    var track = document.getElementById('sunTrack');
    if (!wrap || !track) return;
    var w = wrap.offsetWidth;
    var h = wrap.offsetHeight;
    // 左右各留 12% 空白：从卡片中间区域开始
    var padL = w * 0.12;   // 起点偏移（登录管理标题右侧）
    var padR = w * 0.12;   // 终点偏移（刷新状态按钮左侧）
    var arcW = w - padL - padR;  // 实际弧宽
    var arcTopY = h * 0.08;
    var d = 'M ' + padL + ',' + (h - 2) + ' Q ' + (padL + arcW / 2) + ',' + arcTopY + ' ' + (w - padR) + ',' + (h - 2);
    track.setAttribute('d', d);
}}

/* 高弧形贝塞尔位置计算（带左右内边距） */
var _sunPadL = 0, _sunPadR = 0, _sunArcW = 0;

function getSunPos(t) {{
    var wrap = document.getElementById('sunArcWrap');
    if (!wrap) return {{x: 0, y: 0}};
    var w = wrap.offsetWidth;
    var h = wrap.offsetHeight;
    _sunPadL = w * 0.12;
    _sunPadR = w * 0.12;
    _sunArcW = w - _sunPadL - _sunPadR;
    var arcTopY = h * 0.08;
    // 贝塞尔: P0=(padL, h-2), P1=(padL+arcW/2, arcTopY), P2=(w-padR, h-2)
    var cx = 2 * (1 - t) * t * (_sunArcW / 2);
    var cy = 2 * (1 - t) * t * arcTopY;
    var x = (1 - t) * (1 - t) * _sunPadL + cx + t * t * (w - _sunPadR);
    var y = (1 - t) * (1 - t) * (h - 2) + cy + t * t * (h - 2);
    return {{x: x, y: y}};
}}

/* 创建云朵层（跟随太阳的小云片） */
function createClouds() {{
    var container = document.getElementById('sunClouds');
    if (!container) return;
    container.innerHTML = '';
    sunCloudEls = [];
    /* 云朵数据：每朵是相对于太阳中心的位置偏移 + 大小 */
    var cloudData = [
        {{ox: -16, oy: -12, w: 18, h: 6, s: 0.55, phase: 0.0}},
        {{ox:   4, oy: -15, w: 22, h: 7, s: 0.65, phase: 0.3}},
        {{ox:  14, oy:  -5, w: 16, h: 5, s: 0.45, phase: 0.55}},
        {{ox:  -8, oy:   2, w: 14, h: 5, s: 0.35, phase: 0.75}},
        {{ox:  -2, oy:  10, w: 20, h: 6, s: 0.40, phase: 0.9}},
    ];
    for (var i = 0; i < cloudData.length; i++) {{
        var c = cloudData[i];
        var el = document.createElement('div');
        el.className = 'sun-cloud';
        el.style.width = c.w + 'px';
        el.style.height = c.h + 'px';
        el.dataset.baseOpacity = c.s.toFixed(2);
        el.dataset.phase = c.phase.toFixed(2);
        el.dataset.ox = c.ox;
        el.dataset.oy = c.oy;
        container.appendChild(el);
        sunCloudEls.push(el);
    }}
}}

/* 更新太阳位置、颜色、云朵、平台阴影 */
function updateSunPosition() {{
    var orb = document.getElementById('sunOrb');
    var body = document.getElementById('sunBody');
    var shadow = document.getElementById('sunShadow');
    if (!orb || !body) return;

    var t = sunAngle;
    var pos = getSunPos(t);
    orb.style.left = pos.x + 'px';
    orb.style.top = pos.y + 'px';

    /* ---- 边缘淡入/淡出 ---- */
    if (t > FALL_FADE_START && !sunDragging && sunState === 'visible') {{
        orb.classList.remove('visible');
        orb.classList.add('falling');
        sunState = 'falling';
    }} else if (t >= 0.99 && !sunDragging) {{
        sunAngle = 0;
        orb.classList.remove('falling');
        orb.classList.add('rising');
        sunState = 'rising';
        requestAnimationFrame(function() {{
            var o = document.getElementById('sunOrb');
            if (o) {{ o.classList.remove('rising'); o.classList.add('visible'); }}
            sunState = 'visible';
        }});
        return;  // 跳过本帧渲染
    }} else if (sunState !== 'visible' && !orb.classList.contains('falling') && !orb.classList.contains('rising')) {{
        orb.className = 'sun-orb visible';
        sunState = 'visible';
    }}

    /* ---- 太阳颜色：日出→正午(超亮) → 下午 → 晚霞 → 日落 ---- */
    var r, g, b, glowSize, coreWhite;
    if (t < 0.25) {{
        /* 日出阶段：暗红橙 → 橙黄 */
        var p = t / 0.25;
        r = 255;
        g = Math.round(90 + p * 110);     // 90 → 200
        b = Math.round(10 + p * 30);       // 10 → 40
        glowSize = 4 + p * 24;             // 4 → 28
        coreWhite = 0.65 + p * 0.2;       // 0.65 → 0.85
    }} else if (t < 0.5) {{
        /* 上午到正午：金黄 → 白金(最亮!) */
        var p = (t - 0.25) / 0.25;
        r = 255;
        g = Math.round(200 + p * 45);     // 200 → 245
        b = Math.round(40 + p * 60);      // 40 → 100
        glowSize = 28 + p * 14;           // 28 → 42 (正午最大!)
        coreWhite = 0.85 + p * 0.13;     // 0.85 → 0.98 (正午几乎白!)
    }} else if (t < 0.7) {{
        /* 正午到下午：白金 → 暖黄 */
        var p = (t - 0.5) / 0.2;
        r = 255;
        g = Math.round(245 - p * 50);     // 245 → 195
        b = Math.round(100 - p * 50);     // 100 → 50
        glowSize = 42 - p * 10;           // 42 → 32
        coreWhite = 0.98 - p * 0.13;     // 0.98 → 0.85
    }} else if (t < 0.88) {{
        /* 下午到傍晚：暖黄 → 晚霞红橙 */
        var p = (t - 0.7) / 0.18;
        r = 255;
        g = Math.round(195 - p * 95);     // 195 → 100
        b = Math.round(50 - p * 45);      // 50 → 5
        glowSize = 32 - p * 14;           // 32 → 18
        coreWhite = 0.85 - p * 0.3;      // 0.85 → 0.55
    }} else {{
        /* 晚霞到日落：红橙 → 暗红 */
        var p = (t - 0.88) / 0.12;
        r = Math.round(255 - p * 30);     // 255 → 225
        g = Math.round(100 - p * 70);     // 100 → 30
        b = Math.max(0, Math.round(5 - p * 5)); // 5 → 0
        glowSize = 18 - p * 12;           // 18 → 6
        coreWhite = 0.55 - p * 0.35;     // 0.55 → 0.2
    }}

    body.style.background = 'radial-gradient(circle at 38% 38%, rgba(255,255,255,' + coreWhite.toFixed(2) + '), rgb(' + r + ',' + g + ',' + b + '))';
    body.style.boxShadow =
        '0 0 ' + glowSize + 'px rgba(' + r + ',' + g + ',' + b + ',0.6),' +
        '0 0 ' + Math.round(glowSize * 2.2) + 'px rgba(' + r + ',' + g + ',' + b + ',0.2),' +
        'inset 0 0 ' + Math.round(glowSize * 0.4) + 'px rgba(255,255,255,0.15)';

    /* ---- 太阳底部阴影 ---- */
    if (shadow) {{
        var shadowOffX = Math.round((0.5 - t) * 26);
        var shadowScale = 1.4 - Math.sin(Math.PI * t) * 0.6;
        var shadowAlpha = (0.08 + Math.sin(Math.PI * t) * 0.28).toFixed(2);
        shadow.style.transform = 'translateX(calc(-50% + ' + shadowOffX + 'px)) scaleX(' + shadowScale.toFixed(2) + ')';
        shadow.style.opacity = shadowAlpha;
        shadow.style.background = 'rgba(' + Math.round(r * 0.2) + ',' + Math.round(g * 0.2) + ',' + Math.round(b * 0.2) + ',0.5)';
    }}

    /* ---- 云朵更新（t > 0.5 开始出现）---- */
    updateClouds(t);
}}

/* 云朵系统（跟随太阳的小云片，覆盖在太阳上） */
function updateClouds(t) {{
    if (t <= 0.48) {{
        /* 正午前无云 */
        for (var i = 0; i < sunCloudEls.length; i++) {{
            sunCloudEls[i].style.opacity = '0';
            sunCloudEls[i].style.transform = 'none';
            sunCloudEls[i].style.left = '';
            sunCloudEls[i].style.top = '';
        }}
        return;
    }}
    var cloudT = (t - 0.48) / 0.52;  // 0(正午刚过) ~ 1(日落边缘)
    var orbSize = 28;  /* 太阳直径 */
    for (var i = 0; i < sunCloudEls.length; i++) {{
        var el = sunCloudEls[i];
        var baseO = parseFloat(el.dataset.baseOpacity);
        var phase = parseFloat(el.dataset.phase);
        var ox = parseInt(el.dataset.ox);
        var oy = parseInt(el.dataset.oy);

        var localT = (cloudT + phase) % 1;

        /* 飘动微移 */
        var driftX = Math.sin(localT * Math.PI * 2 + phase * 6.28) * 4;
        var driftY = Math.cos(localT * Math.PI * 2.5 + phase * 6.28) * 2.5;

        /* 浓度随时间增长，晚霞期加浓 */
        var densityMult = 1;
        if (cloudT > 0.45) densityMult = 1 + (cloudT - 0.45) * 1.8;
        var opacity = Math.min(1, baseO * localT * densityMult * 3).toFixed(3);

        /* 颜色：白色→暖橙→晚霞红 */
        var cr = 255, cg = 245, cb = 240;
        if (t > 0.75) {{
            var sp = (t - 0.75) / 0.25;
            cg = Math.round(245 - sp * 130);
            cb = Math.round(240 - sp * 170);
        }} else if (t > 0.58) {{
            var ep = (t - 0.58) / 0.17;
            cb = Math.round(240 - ep * 50);
        }}

        /* 定位：相对于太阳中心（太阳是 28x28，居中 translate(-50%,-50%)） */
        var cx = (orbSize / 2) + ox + driftX;
        var cy = (orbSize / 2) + oy + driftY;

        el.style.opacity = opacity;
        el.style.left = cx.toFixed(1) + 'px';
        el.style.top = cy.toFixed(1) + 'px';
        el.style.transform = 'translate(-50%, -50%)';
        el.style.background = 'rgba(' + cr + ',' + cg + ',' + cb + ',' + (parseFloat(opacity) * 0.85).toFixed(3) + ')';
        el.style.boxShadow = '0 1px 8px rgba(' + cr + ',' + cg + ',' + cb + ',' + (parseFloat(opacity) * 0.35).toFixed(3) + ')';
    }}
}}

/* 动画主循环：单向循环（日出→日落→落下→升起），非登录页自动暂停 */
function startSunAnimation() {{
    if (sunAnimFrame) cancelAnimationFrame(sunAnimFrame);
    function tick() {{
        /* 性能优化：不在登录页时暂停 RAF，不浪费 CPU */
        var loginPage = document.getElementById('page-login');
        if (!loginPage || !loginPage.classList.contains('active')) {{
            /* 不在登录页 → 暂停，每秒检查一次是否回来 */
            if (sunAnimFrame) {{ cancelAnimationFrame(sunAnimFrame); sunAnimFrame = null; }}
            sunPauseCheck = setTimeout(function() {{
                sunPauseCheck = null;
                startSunAnimation();  /* 重新启动（会先检查页面） */
            }}, 1000);
            return;
        }}
        if (!sunDragging) {{
            sunAngle += sunAutoSpeed;
            if (sunAngle > 1.02) sunAngle = 1.02;
        }}
        updateSunPosition();
        sunAnimFrame = requestAnimationFrame(tick);
    }}
    tick();
}}
var sunPauseCheck = null;  /* 非登录页时的低频轮询 */

function onSunDragStart(e) {{
    e.preventDefault();
    sunDragging = true;
    var orb = document.getElementById('sunOrb');
    if (orb) orb.classList.add('dragging');
}}

function onSunDragMove(e) {{
    if (!sunDragging) return;
    e.preventDefault();
    var wrap = document.getElementById('sunArcWrap');
    if (!wrap) return;
    var rect = wrap.getBoundingClientRect();
    var clientX = e.touches ? e.touches[0].clientX : e.clientX;
    var clientY = e.touches ? e.touches[0].clientY : e.clientY;
    var mx = clientX - rect.left;
    var my = clientY - rect.top;
    var bestT = 0, bestDist = Infinity;
    for (var i = 0; i <= 120; i++) {{
        var tt = i / 120;
        var p = getSunPos(tt);
        var dx = p.x - mx, dy = p.y - my;
        var d = dx * dx + dy * dy;
        if (d < bestDist) {{ bestDist = d; bestT = tt; }}
    }}
    sunAngle = bestT;
    /* 拖动时强制可见 */
    var orb = document.getElementById('sunOrb');
    if (orb) {{
        orb.className = 'sun-orb visible dragging';
        sunState = 'visible';
    }}
    updateSunPosition();
}}

function onSunDragEnd() {{
    sunDragging = false;
    var orb = document.getElementById('sunOrb');
    if (orb) orb.classList.remove('dragging');
}}

/* 双击太阳 → 爆炸 → 跳转首页 */
function onSunDblClick(e) {{
    e.preventDefault();
    e.stopPropagation();
    var orb = document.getElementById('sunOrb');
    if (!orb || orb.classList.contains('exploding')) return;
    explodeSun(orb);
}}

/* ========== 小太阳爆炸动画 ========== */
var _sunExploded = false;
function explodeSun(orb) {{
    if (_sunExploded) return;
    _sunExploded = true;

    /* 停止自动动画 */
    if (sunAnimFrame) {{ cancelAnimationFrame(sunAnimFrame); sunAnimFrame = null; }}

    /* 获取太阳当前屏幕位置（用于爆炸粒子定位） */
    var wrap = document.getElementById('sunArcWrap');
    var rect = wrap ? wrap.getBoundingClientRect() : null;
    var orbRect = orb.getBoundingClientRect();

    /* 1. 太阳本体缩小消失动画 */
    orb.classList.add('exploding');

    /* 爆炸中心坐标（相对于 wrap） */
    var cx = orb.offsetLeft + orb.offsetWidth / 2;
    var cy = orb.offsetTop + orb.offsetHeight / 2;

    /* 2. 创建中央闪光 */
    var flash = document.createElement('div');
    flash.className = 'sun-flash';
    flash.style.cssText = 'left:' + cx + 'px;top:' + cy + 'px;width:30px;height:30px;';
    flash.style.animation = 'flashBang 0.5s ease-out forwards';
    wrap.appendChild(flash);

    /* 3. 创建冲击波环 */
    var shock = document.createElement('div');
    shock.className = 'sun-shockwave';
    shock.style.cssText = 'left:' + cx + 'px;top:' + cy + 'px;width:28px;height:28px;';
    shock.style.animation = 'shockwaveExpand 0.6s ease-out forwards';
    wrap.appendChild(shock);

    /* 4. 创建爆炸粒子群（主粒子：大小圆点，向外飞散） */
    var particleColors = [
        '#FFE066', '#FFB347', '#FF8C42', '#FF6B35',
        '#FFF5CC', '#FFFFFF', '#FFD700', '#FF4500',
        '#FFA500', '#FFE4B5', '#FF7F50', '#F4A460'
    ];
    var particleCount = 26;
    for (var i = 0; i < particleCount; i++) {{
        var p = document.createElement('div');
        p.className = 'sun-particle';

        /* 随机大小：大粒子(4-7px)和小粒子(2-3px)混合 */
        var isBig = Math.random() > 0.45;
        var size = isBig ? (4 + Math.random() * 3) : (2 + Math.random() * 1.5);
        p.style.width = size + 'px';
        p.style.height = size + 'px';
        p.style.background = particleColors[Math.floor(Math.random() * particleColors.length)];
        p.style.left = cx + 'px';
        p.style.top = cy + 'px';
        p.style.boxShadow = '0 0 ' + (size * 1.5) + 'px rgba(255,200,80,0.6)';

        /* 随机方向（全圆360度均匀分布） */
        var angle = (Math.PI * 2 / particleCount) * i + (Math.random() - 0.5) * 0.6;
        var dist = 40 + Math.random() * 55;   // 飞散距离
        var dx = Math.cos(angle) * dist;
        var dy = Math.sin(angle) * dist;

        /* 飞散时间 0.4~0.75s 随机 */
        var dur = 0.4 + Math.random() * 0.35;
        var delay = Math.random() * 0.08;       // 微小错开

        p.style.animation = 'particleFly ' + dur + 's ease-out ' + delay + 's forwards';
        /* 用 CSS 变量传递目标位移 */
        p.style.setProperty('--px', dx + 'px');
        p.style.setProperty('--py', dy + 'px');

        wrap.appendChild(p);
    }}

    /* 5. 创建火花/星芒（细长光线状） */
    var sparkCount = 14;
    for (var j = 0; j < sparkCount; j++) {{
        var sp = document.createElement('div');
        sp.className = 'sun-spark';
        sp.style.left = cx + 'px';
        sp.style.top = cy + 'px';
        sp.style.background = Math.random() > 0.3 ? '#FFF' : '#FFE066';
        sp.style.boxShadow = '0 0 4px rgba(255,255,220,0.9)';
        var sAngle = (Math.PI * 2 / sparkCount) * j + Math.random() * 0.5;
        var sDist = 50 + Math.random() * 50;
        var sdx = Math.cos(sAngle) * sDist;
        var sdy = Math.sin(sAngle) * sDist;
        var sdur = 0.35 + Math.random() * 0.3;
        var sDelay = Math.random() * 0.05;
        sp.style.setProperty('--sx', sdx + 'px');
        sp.style.setProperty('--sy', sdy + 'px');
        sp.style.animation = 'sparkFly ' + sdur + 's ease-out ' + sDelay + 's forwards';
        wrap.appendChild(sp);
    }}

    /* 6. 更新 @keyframes 使粒子使用自定义属性 */
    injectExplodeKeyframes();

    /* 7. 爆炸完成后清理并跳转首页 */
    setTimeout(function() {{
        /* 清理所有爆炸元素 */
        var toRemove = wrap.querySelectorAll('.sun-particle,.sun-flash,.sun-shockwave,.sun-spark');
        toRemove.forEach(function(el) {{ el.remove(); }});
        /* 重置状态 */
        _sunExploded = false;
        orb.classList.remove('exploding');
        /* 跳转首页！ */
        goHome();
    }}, 750);
}}

/* 注入带 CSS 自定义属性的 keyframes（使每个粒子有独立方向） */
function injectExplodeKeyframes() {{
    if (document.getElementById('_explodeKF')) return;
    var style = document.createElement('style');
    style.id = '_explodeKF';
    style.textContent =
        '@keyframes particleFly {' +
            '0%{{transform:translate(-50%,-50%) scale(1); opacity:1}}' +
            '100%{{transform:translate(calc(-50%+var(--px,20px)),calc(-50%+var(--py,-15px))) scale(0); opacity:0}}' +
        '}}' +
        '@keyframes sparkFly {' +
            '0%{{transform:translate(-50%,-50%) scale(1); opacity:1}}' +
            '100%{{transform:translate(calc(-50%+var(--sx,25px)),calc(-50%+var(--sy,20px))) scale(0.2); opacity:0}}' +
        '}}';
    document.head.appendChild(style);
}}

// ============================================================
// 彩蛋：9连击颜色选择器
// ============================================================
var _egg9State = {{}};  /* { elementId: { count, timer, targetName, cssClass } } */

/* 预设调色板 */
var _EGG9_COLORS = [
    '#6366f1', '#8b5cf6', '#ec4899', '#ef4444', '#f97316',
    '#eab308', '#22c55e', '#14b8a6', '#06b6d4', '#3b82f6',
    '#a855f7', '#f43f5e', '#84cc16', '#0ea5e9', '#d946ef'
];

function initEgg9Clicker(elId, labelName, cssClass) {{
    var el = document.getElementById(elId);
    if (!el) return;
    _egg9State[elId] = {{ count: 0, timer: null, targetName: labelName, cssClass: cssClass }};
    el.addEventListener('click', function(e) {{
        handleEgg9Click(elId);
    }});
}}

function handleEgg9Click(elId) {{
    var state = _egg9State[elId];
    if (!state) return;
    state.count++;
    /* 1.2秒内必须点完，否则重置 */
    if (state.timer) clearTimeout(state.timer);
    state.timer = setTimeout(function() {{ state.count = 0; }}, 1200);
    /* 第9下 → 弹出选择器 */
    if (state.count >= 9) {{
        state.count = 0;
        if (state.timer) {{ clearTimeout(state.timer); state.timer = null; }}
        openEgg9Panel(state.targetName, state.cssClass, elId);
    }}
}}

/* 当前正在编辑的目标 */
var _egg9CurrentTarget = null;
var _egg9SelectedColor = '';

function openEgg9Panel(targetName, cssClass, elId) {{
    _egg9CurrentTarget = {{ name: targetName, cssClass: cssClass, elId: elId }};
    var overlay = document.getElementById('egg9Overlay');
    var nameEl = document.getElementById('egg9TargetName');
    var swatchEl = document.getElementById('egg9Swatches');

    nameEl.textContent = '\\u6B63\\u5728\\u81EA\\u5B9A\\u4E49\\uFF1A' + targetName;

    /* 生成色块 */
    swatchEl.innerHTML = '';
    for (var i = 0; i < _EGG9_COLORS.length; i++) {{
        (function(color) {{
            var d = document.createElement('div');
            d.className = 'egg9-swatch';
            d.style.background = color;
            d.dataset.color = color;
            d.addEventListener('click', function() {{
                selectEgg9Swatch(this, color);
            }});
            swatchEl.appendChild(d);
        }})(_EGG9_COLORS[i]);
    }}

    /* 默认选中第一个 */
    _egg9SelectedColor = _EGG9_COLORS[0];
    swatchEl.children[0].classList.add('selected');

    /* 自定义颜色输入 */
    var customInput = document.getElementById('egg9CustomColor');
    customInput.value = _EGG9_COLORS[0];
    customInput.oninput = function() {{
        _egg9SelectedColor = this.value;
        var allS = swatchEl.querySelectorAll('.egg9-swatch');
        for (var s = 0; s < allS.length; s++) allS[s].classList.remove('selected');
    }};

    overlay.style.display = 'flex';
}}

function selectEgg9Swatch(el, color) {{
    var container = document.getElementById('egg9Swatches');
    var all = container.querySelectorAll('.egg9-swatch');
    for (var i = 0; i < all.length; i++) all[i].classList.remove('selected');
    el.classList.add('selected');
    _egg9SelectedColor = color;
    document.getElementById('egg9CustomColor').value = color;
}}

function closeEgg9Panel(e) {{
    if (e && e.target !== e.currentTarget) return;
    document.getElementById('egg9Overlay').style.display = 'none';
    _egg9CurrentTarget = null;
}}

/* 应用颜色到目标按钮（渐变效果） */
function applyEgg9Color() {{
    if (!_egg9CurrentTarget || !_egg9SelectedColor) return;

    var baseColor = _egg9SelectedColor;
    var el = document.getElementById(_egg9CurrentTarget.elId);
    if (!el) {{ closeEgg9Panel(); return; }}

    /* 解析 hex 为 rgb，生成深浅两色做渐变 */
    var r = parseInt(baseColor.slice(1,3),16);
    var g = parseInt(baseColor.slice(3,5),16);
    var b = parseInt(baseColor.slice(5,7),16);

    /* 浅一点的颜色（用于渐变第二段） */
    function lighten(hex, amt) {{
        var rr = Math.min(255, parseInt(hex.slice(1,3),16) + amt);
        var gg = Math.min(255, parseInt(hex.slice(3,5),16) + amt);
        var bb = Math.min(255, parseInt(hex.slice(5,7),16) + amt);
        return '#' + rr.toString(16).padStart(2,'0') + gg.toString(16).padStart(2,'0') + bb.toString(16).padStart(2,'0');
    }}
    var lightColor = lighten(baseColor, 40);

    /* 应用渐变背景 —— 只通过动态 style 控制 .on 状态，不污染关闭状态 */
    var grad = 'linear-gradient(135deg,' + baseColor + ',' + lightColor + ')';

    /* 清除之前可能残留的内联 background */
    el.style.background = '';
    el.style.boxShadow = '';

    /* 通过动态 style 覆盖 .on 状态样式 */
    var styleId = '_egg9_' + _egg9CurrentTarget.elId;
    var existing = document.getElementById(styleId);
    if (existing) existing.remove();

    var dynStyle = document.createElement('style');
    dynStyle.id = styleId;
    dynStyle.textContent =
        '.' + _egg9CurrentTarget.cssClass + '.on {{' +
            'background:' + grad + '!important;' +
            'box-shadow:0 0 12px ' + hexToRgba(baseColor, 0.35) + '!important;' +
        '}}' +
        '.' + _egg9CurrentTarget.cssClass + ':hover:not(.on) {{' +
            'box-shadow:0 0 10px ' + hexToRgba(baseColor, 0.25) + ', inset 0 1px 3px rgba(0,0,0,0.15);' +
        '}}';
    document.head.appendChild(dynStyle);

    /* 关闭面板 */
    closeEgg9Panel();

    /* 视觉反馈：按钮闪烁一下 */
    el.style.transition = 'none';
    el.style.transform = 'scale(1.08)';
    setTimeout(function() {{
        el.style.transition = '';
        el.style.transform = '';
    }}, 180);

    showToast('\\u2728 \\u989C\\u8272\\u5DF2\\u81EA\\u5B9A\\u4E49', 'success');
}}

function hexToRgba(hex, alpha) {{
    var r = parseInt(hex.slice(1,3),16), g = parseInt(hex.slice(3,5),16), b = parseInt(hex.slice(5,7),16);
    return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
}}

/** 刷新登录页面状态 */
async function refreshLoginPage() {{
    var btn = document.getElementById('btnRefreshLogin');
    if (btn.classList.contains('spinning')) return;
    /* 点击图标旋转 */
    var ico = document.getElementById('refreshIcon');
    ico.classList.remove('click-spin'); void ico.offsetWidth; ico.classList.add('click-spin');
    setTimeout(() => ico.classList.remove('click-spin'), 500);
    btn.classList.add('spinning');
    btn.disabled = true;
    try {{
        await renderPlatformCards();
        await loadPlatformData();
        showToast('\\u5237\\u65B0\\u6210\\u529F \\u2705', 'success');
    }} catch(e) {{
        showToast('\\u5237\\u65B0\\u5931\\u8D25: ' + e.message, 'error');
    }} finally {{
        btn.classList.remove('spinning');
        btn.disabled = false;
    }}
}}

/** 刷新发布页平台状态 */
async function refreshPublishPlatforms() {{
    var btn = document.getElementById('btnRefreshPublish');
    if (btn.classList.contains('spinning')) return;
    /* 点击图标旋转 */
    var ico = document.getElementById('refreshPublishIcon');
    ico.classList.remove('click-spin'); void ico.offsetWidth; ico.classList.add('click-spin');
    setTimeout(() => ico.classList.remove('click-spin'), 500);
    btn.classList.add('spinning');
    btn.disabled = true;
    try {{
        await loadPlatformData();
        showToast('\\u5237\\u65B0\\u6210\\u529F \\u2705', 'success');
    }} catch(e) {{
        showToast('\\u5237\\u65B0\\u5931\\u8D25: ' + e.message, 'error');
    }} finally {{
        btn.classList.remove('spinning');
        btn.disabled = false;
    }}
}}

/**
 * 渲染平台账号卡片列表
 * 调用 /api/platforms + /api/accounts/<plat> 获取完整数据
 * 同时预加载账号头像和昵称显示在卡片头部
 */
async function renderPlatformCards() {{
    var container = document.getElementById("platformCards");
    /* E10: 骨架屏加载 */
    showSkeleton("platSkeleton", "cards");
    try {{
        const resp = await fetch("/api/platforms");
        const json = await resp.json();
        if (json.code !== 0) return;

        // 预加载所有已登录平台的账号详情
        var acctMap = {{}};  // plat -> accounts data
        var fetches = json.data.filter(function(p) {{ return p.supported && p.logged_in; }}).map(async function(p) {{
            try {{
                var r = await fetch('/api/accounts/' + p.id);
                var j = await r.json();
                if (j.code === 0 && j.data.accounts.length > 0) acctMap[p.id] = j.data.accounts;
            }} catch(e) {{}}
        }});
        await Promise.all(fetches);

        var html = '';
        for (var idx = 0; idx < json.data.length; idx++) {{
            var p = json.data[idx];
            var pi = PLAT_ICONS[p.id] || {{svg:'<svg viewBox="0 0 48 48" fill="none"><circle cx="24" cy="24" r="16" stroke="rgba(255,255,255,0.3)" stroke-width="2" fill="none"/></svg>'}};
            var sup = p.supported;
            var li = p.logged_in;
            var bCls = !sup ? 'badge-na' : (li ? 'badge-in' : 'badge-out');
            var bTxt = !sup ? '\\u6682\\u4E0D\\u652F\\u6301' : (li ? '\\u5DF2\\u767B\\u5F55 (' + p.account_count + ')' : '\\u672A\\u767B\\u5F55');

            html += '<div class="plat-card" data-plat="' + p.id + '">';
            html += '<div class="pch-wrap"><div class="pch-left">';

            // 已登录时，图标位置显示账号头像（有头像用头像，否则用平台图标）
            var accts = acctMap[p.id];
            if (li && accts && accts.length > 0) {{
                var firstAcct = accts[0];
                var nm = firstAcct.nickname || (firstAcct.name === 'default' ? '\\u9ED8\\u8BA4\\u8D26\\u53F7' : firstAcct.name);
                var fc = nm.charAt(0).toUpperCase();
                if (firstAcct.avatar_url) {{
                    html += '<div class="pch-icon" style="overflow:hidden;position:relative;">';
                    html += pi.svg;
                    html += '<img src="' + firstAcct.avatar_url + '" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;border-radius:12px;" onerror="this.style.display=\\'none\\'">';
                    html += '</div>';
                }} else {{
                    html += '<div class="pch-icon" style="overflow:hidden;">' + pi.svg + '</div>';
                }}
                html += '<div><div class="pch-name">' + p.name + '</div>';
                html += '<div class="pch-nickname">' + nm + '</div></div>';
            }} else {{
                html += '<div class="pch-icon" style="overflow:hidden;">' + (pi.svg || pi.i || '') + '</div>';
                html += '<div><div class="pch-name">' + p.name + '</div></div>';
            }}
            html += '</div>';
            html += '<span class="pch-badge ' + bCls + '">' + bTxt + '</span></div>';

            // 已登录 -> 账号列表 / 未登录 -> 提示 / 不支持 -> 灰色提示
            if (li && sup) {{
                html += '<div class="acct-list" id="accts-' + p.id + '">';
                // 直接使用预加载的账号数据渲染，避免二次请求
                if (accts && accts.length > 0) {{
                    html += renderAcctItems(p.id, accts);
                }} else {{
                    html += '<div style="padding:8px;color:rgba(255,255,255,0.3);font-size:12px;">\\u52A0\\u8F7D\\u4E2D...</div>';
                }}
                html += '</div>';
            }} else if (!li && sup) {{
                html += '<div class="no-acct-hint">\\u5C1A\\u672A\\u767B\\u5F55\\u8D26\\u53F7</div>';
            }} else {{
                html += '<div class="no-acct-hint">\\u8BE5\\u5E73\\u53F0\\u6682\\u4E0D\\u652F\\u6301\\u81EA\\u52A8\\u53D1\\u5E03</div>';
            }}

            // 底部操作按钮（仅支持的平台显示）
            if (sup) {{
                var dis = curLoginSid ? ' disabled title="\\u5DF2\\u6709\\u767B\\u5F55\\u8FDB\\u884C\\u4E2D"' : '';
                var btnTxt = li ? '+ \\u6DFB\\u52A0\\u8D26\\u53F7' : '\\u626B\\u7801\\u767B\\u5F55';
                html += '<div class="pca-actions">';
                html += '<button class="btn-login-card" onclick="startLogin(\\'' + attrEscape(p.id) + '\\',\\'' + attrEscape(p.name) + '\\')"' + dis + '>' + btnTxt + '</button>';
                html += '</div>';
            }}
            html += '</div>';  // end plat-card
        }}

        container.innerHTML = html;

        // 异步检测已登录平台的 cookie 是否有效（不阻塞 UI）
        json.data.filter(function(p) {{ return p.supported && p.logged_in; }}).forEach(function(p) {{
            setTimeout(function() {{ checkPlatformCookie(p.id); }}, 500);
        }});

    }} catch(e) {{
        container.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:30px;color:#f87171;">\\u274C \\u52A0\\u8F7D\\u5931\\u8D25: ' + e.message + '</div>';
    }}
}}

/** 异步检测平台 cookie 是否有效，过期则更新 UI */
async function checkPlatformCookie(platform) {{
    try {{
        var r = await fetch('/api/check-cookie/' + platform);
        var j = await r.json();
        if (j.code === 0 && j.data && !j.data.valid) {{
            markPlatformExpired(platform, j.data.reason || 'Cookie\\u5DF2\\u8FC7\\u671F');
        }}
    }} catch(e) {{
        // 检测失败静默处理，不改变登录状态
        console.warn('[cookie-check] \\u68C0\\u6D4B\\u5931\\u8D25: ' + platform, e);
    }}
}}

/** 将指定平台标记为过期状态 */
function markPlatformExpired(platform, reason) {{
    var card = document.querySelector('.plat-card[data-plat="' + platform + '"]');
    if (!card) return;
    // 更新徽章
    var badge = card.querySelector('.pch-badge');
    if (badge) {{
        badge.textContent = '\\u8FC7\\u671F';
        badge.className = 'pch-badge badge-expired';
    }}
    // 添加过期提示（避免重复添加）
    var actions = card.querySelector('.pca-actions');
    if (actions && !actions.querySelector('.cookie-expired-warn')) {{
        var warn = document.createElement('div');
        warn.className = 'cookie-expired-warn';
        warn.textContent = '\\u26A0\\uFE0F ' + reason;
        warn.style.cssText = 'color:#fbbf24;font-size:11px;margin-bottom:6px;';
        actions.insertBefore(warn, actions.firstChild);
        // 弹出全局通知
        showToast('\\u26A0\\uFE0F ' + (platformData.find(function(p){{return p.id===platform}})||{{name:platform}}).name + '\\u767B\\u5F55\\u5DF2\\u8FC7\\u671F\\uFF0C\\u8BF7\\u91CD\\u65B0\\u767B\\u5F55', 'warn');
    }}
}}

/** 手动检测所有已登录平台的 Cookie 是否有效 */
var _autoCheckTimer = null;

function checkAllCookies() {{
    var btn = document.getElementById('btnCheckCookies');
    if (btn) {{ btn.textContent = '\\u23F3 \\u68C0\\u6D4B\\u4E2D...'; btn.disabled = true; }}
    // 逐个检测（避免并发浏览器实例冲突）
    var loggedIn = platformData.filter(function(p) {{ return p.supported && p.logged_in; }});
    var i = 0;
    function next() {{
        if (i >= loggedIn.length) {{
            if (btn) {{ btn.textContent = '\\u2705 \\u68C0\\u6D4B\\u5B8C\\u6210'; btn.disabled = false;
                setTimeout(function(){{ btn.textContent = '\\uD83D\\uDD0D \\u68C0\\u6D4B\\u767B\\u5F55\\u72B6\\u6001'; }}, 2000); }}
            return;
        }}
        checkPlatformCookie(loggedIn[i].id).then(function() {{
            i++;
            setTimeout(next, 600);
        }});
    }}
    next();
    if (loggedIn.length === 0 && btn) {{
        btn.textContent = '\\uD83D\\uDD0D \\u68C0\\u6D4B\\u767B\\u5F55\\u72B6\\u6001'; btn.disabled = false;
        showToast('\\u6682\\u65E0\\u5DF2\\u767B\\u5F55\\u5E73\\u53F0', 'info');
    }}
}}

/** 启动 30 秒自动检测定时器 */
function startAutoCookieCheck() {{
    stopAutoCookieCheck();
    _autoCheckTimer = setInterval(function() {{
        // 仅在登录管理页可见时执行
        var loginPage = document.getElementById('page-login');
        if (loginPage && loginPage.classList.contains('active')) {{
            var loggedIn = platformData.filter(function(p) {{ return p.supported && p.logged_in; }});
            if (loggedIn.length > 0) {{
                // 静默检测（不锁按钮）
                var j = 0;
                function nextSilent() {{
                    if (j >= loggedIn.length) return;
                    checkPlatformCookie(loggedIn[j].id);
                    j++;
                    if (j < loggedIn.length) setTimeout(nextSilent, 800);
                }}
                nextSilent();
            }}
        }}
    }}, 30000);
}}

/** 停止自动检测 */
function stopAutoCookieCheck() {{
    if (_autoCheckTimer) {{ clearInterval(_autoCheckTimer); _autoCheckTimer = null; }}
}}

/** 渲染账号列表项 HTML */
function renderAcctItems(plat, accounts) {{
    var h = '';
    for (var k = 0; k < accounts.length; k++) {{
        var a = accounts[k];
        var nm = a.nickname || (a.name === 'default' ? '\\u9ED8\\u8BA4\\u8D26\\u53F7' : a.name);
        var firstChar = nm.charAt(0).toUpperCase();
        var avatarHtml = a.avatar_url
            ? '<img src="' + a.avatar_url + '" style="width:28px;height:28px;border-radius:50%;object-fit:cover;" onerror="this.style.display=\\'none\\';this.nextElementSibling.style.display=\\'\\'"><div class="acct-avatar" style="display:none">' + firstChar + '</div>'
            : '<div class="acct-avatar">' + firstChar + '</div>';
        var uidHint = a.user_id ? '<div class="acct-time">ID: ' + a.user_id + '</div>' : '';
        h += '<div class="acct-item">';
        h += '<div class="acct-info">';
        h += avatarHtml;
        h += '<div class="acct-detail">';
        h += '<div class="acct-name">' + nm + '</div>';
        h += uidHint;
        h += '<div class="acct-time">\\u767B\\u5F55\\u4E8E ' + a.modified + '</div>';
        h += '</div></div>';
        h += '<button class="btn-logout-sm" onclick="doLogout(\\'' + attrEscape(plat) + '\\',\\'' + attrEscape(a.name) + '\\',event)">\\u9000\\u51FA</button>';
        h += '</div>';
    }}
    return h;
}}

/** 加载单个平台的账号详细信息（用于刷新单个平台） */
async function loadAcctDetail(plat) {{
    try {{
        var r = await fetch('/api/accounts/' + plat);
        var j = await r.json();
        if (j.code !== 0) return;
        var c = document.getElementById('accts-' + plat);
        if (!c) return;
        if (j.data.total === 0) {{ c.innerHTML = '<div class="no-acct-hint">\\u65E0\\u8D26\\u53F7\\u4FE1\\u606F</div>'; return; }}
        c.innerHTML = renderAcctItems(plat, j.data.accounts);
    }} catch(e) {{ console.warn('loadAcctDetail error:', plat, e); }}
}}

/**
 * 启动扫码登录流程（异步会话模式）
 */
async function startLogin(platform, platName) {{
    if (curLoginSid || loginPollTimer) {{
        showToast('\\u26A0\\uFE0F \\u6709\\u767B\\u5F55\\u8FDB\\u884C\\u4E2D\\uFF0C\\u8BF7\\u5148\\u5B8C\\u6210');
        return;
    }}

    document.getElementById('lmTitle').textContent = platName + ' \\u767B\\u5F55';
    document.getElementById('loginModal').style.display = 'flex';
    document.getElementById('loginModal').classList.add('show');
    document.getElementById('lmQrArea').style.display = 'none';
    document.getElementById('lmRetryBtn').style.display = 'none';

    setLmUI('browser_opening', '\\u6B63\\u5728\\u542F\\u52A8\\u6D4F\\u89C8\\u5668...', '\\u23F3');
    curLoginPlat = platform;

    try {{
        var resp = await fetch('/api/login/start/' + platform, {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{account: 'default'}}),
        }});
        var json = await resp.json();

        if (json.code !== 0) {{
            closeLoginModal();
            showToast(json.msg || '\\u542F\\u52A8\\u5931\\u8D25', 'error');
            return;
        }}

        curLoginSid = json.data.session_id;
        pollLoginStatus();

    }} catch(e) {{
        closeLoginModal();
        showToast('\\u7F51\\u7EDC\\u9519\\u8BEF: ' + e.message, 'error');
    }}
}}

/** 轮询登录状态（setTimeout 递归，避免 setInterval 请求风暴） */
function pollLoginStatus() {{
    if (!curLoginSid) return;

    loginPollTimer = setTimeout(async function() {{
        if (!curLoginSid) {{ loginPollTimer = null; return; }}

        try {{
            var r = await fetch('/api/login/status/' + curLoginSid);
            var j = await r.json();
            if (j.code !== 0) {{ pollLoginStatus(); return; }}

            var d = j.data;
            updateLmUI(d.status, d.message, d.qrcode_base64 || '');

            if (d.status === 'success') {{
                loginPollTimer = null;
                curLoginSid = null;
                document.getElementById('lmRetryBtn').style.display = 'none';
                showToast(d.message || '\\u767B\\u5F55\\u6210\\u5295 \\u2705', 'success');
                setTimeout(function() {{ renderPlatformCards(); loadPlatformData(); }}, 1200);

            }} else if (d.status === 'failed') {{
                loginPollTimer = null;
                curLoginSid = null;
                document.getElementById('lmRetryBtn').style.display = 'inline-block';
                showToast(d.message || '\\u767B\\u5F55\\u5931\\u8D25', 'error');
            }} else {{
                // 还在等待（browser_opening / waiting_scan / scanned），继续轮询
                pollLoginStatus();
            }}
        }} catch(e) {{
            console.warn('poll error:', e);
            pollLoginStatus();  // 网络错误后继续轮询
        }}
    }}, 2000);  // 每 2 秒轮询一次
}}

/** 更新弹窗 UI */
function updateLmUI(status, msg, qrBase64) {{
    var icons = {{
        'success':      '\\u2705',
        'failed':       '\\u274C',
        'waiting_scan': '\\uD83D\\uDCF1',
        'scanned':      '\\u2713',
    }};
    setLmUI(status, msg, icons[status] || '\\u23F3', qrBase64 || '');
}}

function setLmUI(status, text, icon, qrBase64) {{
    var body = document.getElementById('lmBody');
    body.className = '';
    body.style.cssText = 'text-align:center;min-height:200px;display:flex;flex-direction:column;align-items:center;justify-content:center;';
    if (status === 'success') body.classList.add('lm-success');
    else if (status === 'failed') body.classList.add('lm-failed');

    // \\u6709\\u4E8C\\u7EF4\\u7801\\u65F6\\u5C55\\u793A\\u4E8C\\u7EF4\\u7801\\u56FE\\u7247
    if (qrBase64 && (status === 'waiting_scan' || status === 'browser_opening')) {{
        var pName = document.getElementById('lmTitle').textContent.replace(' \\u767B\\u5F55', '');
        body.innerHTML = '<img src="' + qrBase64 + '" alt="QR" style="max-width:220px;border-radius:12px;border:2px solid rgba(255,255,255,0.2);margin-bottom:12px;">'
                       + '<p style="color:rgba(255,255,255,0.7);font-size:14px;">' + text + '</p>'
                       + '<p style="color:rgba(255,255,255,0.4);font-size:12px;margin-top:6px;">\\u8BF7\\u4F7F\\u7528' + pName + 'APP\\u626B\\u63CF\\u4E0A\\u65B9\\u4E8C\\u7EF4\\u7801</p>';
    }} else {{
        var isSpinning = (status !== 'success' && status !== 'failed');
        var cls = isSpinning ? 'spin-icon' : '';
        body.innerHTML = '<div id="lmStatusIcon" class="' + cls + '" style="font-size:48px;">' + icon + '</div>'
                       + '<p id="lmStatusText" style="color:rgba(255,255,255,0.7);font-size:14px;margin-top:12px;">' + text + '</p>';
    }}
}}

/** 关闭登录弹窗 */
function closeLoginModal() {{
    document.getElementById('loginModal').style.display = 'none';
    document.getElementById('loginModal').classList.remove('show');
    if (loginPollTimer) {{ clearTimeout(loginPollTimer); loginPollTimer = null; }}
    curLoginSid = null;
    curLoginPlat = null;
}}

/** 重新扫码 */
function retryLogin() {{
    var p = curLoginPlat;
    var n = document.getElementById('lmTitle').textContent.replace(' \\u767B\\u5F55', '');
    closeLoginModal();
    setTimeout(function() {{ startLogin(p, n); }}, 300);
}}

/**
 * 退出登录（删除 cookie 文件）
 */
async function doLogout(platform, account, evt) {{
    evt.stopPropagation();

    var pd = platformData.find(function(x) {{ return x.id === platform; }});
    var pName = pd ? pd.name : platform;

    if (!confirm('\\u786E\\u5B9A\\u9000\\u51FA ' + pName + ' \\u7684\\u8D26\\u53F7\\u300C' + account + '\\u300D\\uFF1F')) return;

    try {{
        var r = await fetch('/api/logout/' + platform, {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{account: account}}),
        }});
        var j = await r.json();

        if (j.code === 0) {{
            showToast(j.msg, 'success');
            renderPlatformCards();
            loadPlatformData();
        }} else {{
            showToast(j.msg || '\\u9000\\u51FA\\u5931\\u8D25', 'error');
        }}
    }} catch(e) {{
        showToast('\\u7F51\\u7EDC\\u9519\\u8BEF: ' + e.message, 'error');
    }}
}}

// \\u6267\\u884C\\u53D1\\u5E03\\uFF08\\u8C03\\u7528\\u540E\\u7AEF API\\uFF09
// ============================================================
async function doPublish() {{
    // ---- \\u53C2\\u6570\\u6821\\u9A8C ----
    if (!selectedVideo) {{
        showToast("\\u8BF7\\u5148\\u9009\\u62E9\\u89C6\\u9891\\u6587\\u4EF6","error");
        return;
    }}
    const title = document.getElementById("titleInput").value.trim();
    if (!title) {{
        showToast("\\u8BF7\\u8F93\\u5165\\u89C6\\u9891\\u6807\\u9898","error");
        return;
    }}
    if (selectedPlatforms.length === 0) {{
        showToast("\\u8BF7\\u81F3\\u5C11\\u9009\\u62E9\\u4E00\\u4E2A\\u53D1\\u5E03\\u5E73\\u53F0","error");
        return;
    }}

    // ---- \\u6536\\u96C6\\u6807\\u7B7E ----
    const tags = [];
    document.querySelectorAll("#tagsRow .tag-pill.selected").forEach(el => {{
        let t = el.textContent.trim();
        const emojis = ["\\uD83D\\uDD25","\\u2728","\\uD83D\\uDCA1","\\uD83C\\uDF1F","\\uD83C\\uDFAF","\\uD83D\\uDCAA"];
        emojis.forEach(e => {{ if (t.startsWith(e)) t = t.slice(e.length+1).trim(); }});
        if (t) tags.push(t);
    }});

    // ---- \\u5B9A\\u65F6\\u53D1\\u5E03\\u65F6\\u95F4 ----
    let scheduleTime = "";
    const schedToggle = document.getElementById("schedToggle");
    if (schedToggle.classList.contains("on")) {{
        scheduleTime = document.getElementById("datetimePicker").value.replace("T", " ");
    }}

    // ---- \\u63CF\\u8FF0 ----
    const desc = document.getElementById("descInput").value.trim();

    // ---- B站分区等平台特定参数 ----
    const platformExtra = {{}};
    if (selectedPlatforms.includes("bilibili")) {{
        platformExtra["bilibili"] = {{ tid: getSelectedBiliTid() }};
    }}

    // ---- \\u663E\\u793A\\u8FDB\\u5EA6\\u9762\\u677F ----
    document.getElementById("progressPanel").style.display = "block";

    const progressList = document.getElementById("progressList");
    progressList.innerHTML = "";
    selectedPlatforms.forEach(pid => {{
        const pname = platformData.find(p=>p.id==pid)?.name || pid;
        progressList.innerHTML += `
            <div class="progress-item" id="prog-${{pid}}">
                <div class="pi-left">
                    <span>${{pname}}</span>
                </div>
                <span class="pi-status pending" id="status-${{pid}}">\\u7B49\\u5F85\\u4E2D...</span>
            </div>`;
    }});

    // ---- \\u7981\\u7528\\u6309\\u94AE\\u9632\\u6B62\\u91CD\\u590D\\u70B9\\u51FB ----
    const btn = document.getElementById("publishBtn");
    btn.disabled = true;
    btn.querySelector(".btn-text").textContent = "\\u23F3 \\u6B63\\u5728\\u53D1\\u5E03...";
    // 移除平台按钮弹跳动画 -- 发布过程中不需要额外的视觉消耗
    document.querySelectorAll(".platform-btn").forEach(function(b) {{ b.classList.remove("p-bounce", "p-shrink"); }});

    try {{
        const resp = await fetch("/api/upload", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{
                video: selectedVideo,
                title: title,
                desc: desc,
                tags: tags,
                platforms: selectedPlatforms,
                schedule_time: scheduleTime,
                platform_extra: platformExtra,
            }}),
        }});
        const result = await resp.json();

        if (result.code === 0) {{
            showToast(`\\u5DF2\\u63D0\\u4EA4\\u5230 ${{result.data.total}} \\u4E2A\\u5E73\\u53F0\\u53D1\\u5E03\\u4EFB\\u52A1`, "success");
            startProgressPolling(selectedPlatforms);
            // 发布提交后清除视频选择（标题/描述保留供复用）
            clearPublishState();

        }} else {{
            showToast(result.msg || "\\u53D1\\u5E03\\u8BF7\\u6C42\\u5931\\u8D25", "error");
            btn.disabled = false;
            btn.querySelector(".btn-text").textContent = "\\uD83D\\uDE80 \\u4E00\\u952E\\u53D1\\u5E03\\u5230\\u9009\\u4E2D\\u5E73\\u53F0";
        }}

    }} catch (err) {{
        console.error("\\u53D1\\u5E03\\u8BF7\\u6C42\\u51FA\\u9519:", err);
        showToast(`\\u53D1\\u5E03\\u5931\\u8D25: ${{err.message}}`, "error");
        btn.disabled = false;
        btn.querySelector(".btn-text").textContent = "\\uD83D\\uDE80 \\u4E00\\u952E\\u53D1\\u5E03\\u5230\\u9009\\u4E2D\\u5E73\\u53F0";
    }}
}}

// ============================================================
// \\u8F6E\\u8BE2\\u4E0A\\u4F20\\u8FDB\\u5EA6
// ============================================================
function startProgressPolling(platforms) {{
    let pollCount = 0;
    const maxPolls = 180;

    async function poll() {{
        pollCount++;
        try {{
            const resp = await fetch("/api/status");
            const result = await resp.json();
            const statuses = result.data || {{}};
            let successCount = 0;
            let allDone = true;

            platforms.forEach(pid => {{
                const st = statuses[pid];
                const el = document.getElementById(`status-${{pid}}`);
                if (!el) return;

                if (st) {{
                    if (st.status === "uploading") {{
                        el.className = "pi-status uploading";
                        el.textContent = st.msg || "\\u6B63\\u5728\\u4E0A\\u4F20...";
                        allDone = false;
                        var piItem = document.getElementById("prog-" + pid);
                        if (piItem) piItem.classList.add("pi-uploading");
                    }} else if (st.status === "success") {{
                        el.className = "pi-status success";
                        el.textContent = st.msg || "\\u2705 \\u53D1\\u5E03\\u6210\\u529F";
                        successCount++;
                        clearUploadingMark(pid);
                    }} else if (st.status === "error") {{
                        el.className = "pi-status error";
                        el.textContent = st.msg || "\\u274C \\u5931\\u8D25";
                        successCount++;
                        clearUploadingMark(pid);
                    }} else {{
                        allDone = false;
                    }}
                }} else {{
                    allDone = false;
                }}
            }});

            if (allDone || pollCount >= maxPolls) {{
                const btn = document.getElementById("publishBtn");
                btn.disabled = false;
                btn.querySelector(".btn-text").textContent = "\\uD83D\\uDE80 \\u4E00\\u952E\\u53D1\\u5E03\\u5230\\u9009\\u4E2D\\u5E73\\u53F0";

                if (allDone) {{
                    publishedCount += successCount;
                    updateStatusBar();
                    showToast(`\\u53D1\\u5E03\\u5B8C\\u6210\\uFF01\\u6210\\u529F ${{successCount}}/${{platforms.length}}`, "success");
                    if (successCount > 0) fireConfetti(80);
                }}
                return;  // 停止轮询
            }}
            // 请求完成且未结束 → 安排下一次
            setTimeout(poll, 1500);
        }} catch(e) {{
            // 网络错误 → 延长间隔后重试
            if (pollCount < maxPolls) {{
                setTimeout(poll, 3000);
            }}
        }}
    }}

    // 首次立即发起
    poll();
}}

// ============================================================
// Toast 提示
// ============================================================
function showToast(msg, type="info") {{
    const toast = document.getElementById("toast");
    toast.textContent = msg;
    toast.className = `toast ${{type}} show`;
    setTimeout(() => toast.classList.remove("show"), 2800);
}}

// ============================================================
// 加载平台数据（初始化）
// ============================================================
async function loadPlatformData() {{
    try {{
        const resp = await fetch("/api/platforms");
        const result = await resp.json();
        if (result.code === 0) {{
            platformData = result.data;
            renderPlatformGrid();
            updateStatusBar();
        }}
    }} catch(err) {{
        console.error("加载平台数据失败:", err);
        // 使用默认兜底数据
        platformData = [
            {{id:"douyin",name:"抖音",logged_in:false,supported:true}},
            {{id:"kuaishou",name:"快手",logged_in:false,supported:true}},
            {{id:"xhs",name:"小红书",logged_in:false,supported:true}},
            {{id:"bilibili",name:"B站",logged_in:false,supported:true}},
            {{id:"tencent",name:"视频号",logged_in:false,supported:true}},
            {{id:"tiktok",name:"TikTok",logged_in:false,supported:true}},
            {{id:"youtube",name:"YouTube",logged_in:false,supported:false}},
            {{id:"instagram",name:"Instagram",logged_in:false,supported:false}},
            {{id:"x",name:"X",logged_in:false,supported:false}},
        ];
        renderPlatformGrid();
        updateStatusBar();
    }}
}}

// ============================================================
// 自定义下拉菜单组件（替代原生 select，支持透明模糊背景）
// ============================================================
class CustomSelect {{
    constructor(selEl) {{
        this.sel = selEl;
        this.isOpen = false;
        this.options = [];
        this.selectedIndex = 0;
        this._build();
        this._bindEvents();
    }}

    _build() {{
        // 收集 option
        const opts = this.sel.querySelectorAll('option');
        opts.forEach((o, i) => {{
            this.options.push({{ value: o.value, text: o.textContent, selected: o.selected }});
            if (o.selected) this.selectedIndex = i;
        }});

        // 判断小尺寸
        const isSmall = this.sel.classList.contains('hist-filter-select');
        const inheritStyle = this.sel.getAttribute('style') || '';

        // 创建容器
        this.wrap = document.createElement('div');
        this.wrap.className = 'custom-select-wrap' + (isSmall ? ' sm' : '');
        this.wrap.style.cssText = inheritStyle.includes('width') ? 'width:' + inheritStyle.match(/width\\s*:\\s*([^;]+)/)?.[1] : (this.sel.style.width || '');

        // 创建触发器
        this.trigger = document.createElement('div');
        this.trigger.className = 'custom-select-trigger';
        this.trigger.textContent = this.options[this.selectedIndex]?.text || '';
        this.trigger.tabIndex = 0;
        this.trigger.setAttribute('role', 'listbox');
        this.trigger.setAttribute('aria-label', this.sel.id || 'dropdown');

        // 创建面板
        this.panel = document.createElement('div');
        this.panel.className = 'custom-select-panel';
        this.options.forEach((opt, i) => {{
            const div = document.createElement('div');
            div.className = 'custom-select-option' + (i === this.selectedIndex ? ' selected' : '');
            div.textContent = opt.text;
            div.dataset.index = i;
            this.panel.appendChild(div);
        }});

        // 组装
        this.wrap.appendChild(this.trigger);
        this.wrap.appendChild(this.panel);
        this.sel.parentNode.insertBefore(this.wrap, this.sel);
        this.sel.style.display = 'none';
        this.wrap.appendChild(this.sel);
    }}

    _bindEvents() {{
        // 点击触发器
        this.trigger.addEventListener('click', (e) => {{
            e.stopPropagation();
            this.toggle();
        }});

        // 键盘
        this.trigger.addEventListener('keydown', (e) => {{
            if (e.key === 'Enter' || e.key === ' ') {{ e.preventDefault(); this.toggle(); }}
            if (e.key === 'Escape') this.close();
            if (e.key === 'ArrowDown') {{ e.preventDefault(); this._moveSelection(1); }}
            if (e.key === 'ArrowUp') {{ e.preventDefault(); this._moveSelection(-1); }}
        }});

        // 选项点击
        this.panel.addEventListener('click', (e) => {{
            const opt = e.target.closest('.custom-select-option');
            if (!opt) return;
            this._select(parseInt(opt.dataset.index));
            this.close();
        }});

        // 点击外部关闭已由全局事件处理（initCustomSelects 中）
    }}

    toggle() {{
        this.isOpen ? this.close() : this.open();
    }}

    open() {{
        this.isOpen = true;
        this.trigger.classList.add('open');
        // 关闭其他已打开的下拉菜单
        Object.values(customSelects).forEach(function(cs) {{
            if (cs !== this && cs.isOpen) cs.close();
        }}.bind(this));
        // 自动检测：如果下拉会超出视口底部，改为向上弹出
        const rect = this.wrap.getBoundingClientRect();
        // 用选项数量估算面板高度（每个选项约36px，最大240px）
        const panelHeight = Math.min(this.options.length * 36, 240);
        const spaceBelow = window.innerHeight - rect.bottom;
        const spaceAbove = rect.top;
        if (spaceBelow < panelHeight + 8 && spaceAbove > panelHeight + 8) {{
            this.wrap.classList.add('dropup');
        }} else {{
            this.wrap.classList.remove('dropup');
        }}
        this.panel.classList.add('open');
        // 滚动到选中项
        const selOpt = this.panel.querySelector('.custom-select-option.selected');
        if (selOpt) selOpt.scrollIntoView({{ block: 'nearest' }});
    }}

    close() {{
        this.isOpen = false;
        this.trigger.classList.remove('open');
        this.panel.classList.remove('open');
        this.wrap.classList.remove('dropup');
    }}

    _select(index) {{
        if (index < 0 || index >= this.options.length) return;
        this.selectedIndex = index;
        this.trigger.textContent = this.options[index].text;
        // 更新面板高亮
        this.panel.querySelectorAll('.custom-select-option').forEach((el, i) => {{
            el.classList.toggle('selected', i === index);
        }});
        // 同步到原生 select 并触发 change
        this.sel.value = this.options[index].value;
        this.sel.dispatchEvent(new Event('change', {{ bubbles: true }}));
    }}

    _moveSelection(dir) {{
        let next = this.selectedIndex + dir;
        if (next < 0) next = this.options.length - 1;
        if (next >= this.options.length) next = 0;
        this._select(next);
    }}

    // 外部更新选项（如 B站分区动态加载）
    updateOptions(newOptions) {{
        this.options = newOptions;
        this.selectedIndex = 0;
        this.trigger.textContent = newOptions[0]?.text || '';
        // 如果面板打开，先关闭再重建（避免动画 bug）
        if (this.isOpen) this.close();
        // 重建面板
        this.panel.innerHTML = '';
        newOptions.forEach((opt, i) => {{
            const div = document.createElement('div');
            div.className = 'custom-select-option' + (i === 0 ? ' selected' : '');
            div.textContent = opt.text;
            div.dataset.index = i;
            this.panel.appendChild(div);
        }});
        // 同步原生 select
        this.sel.innerHTML = '';
        newOptions.forEach(opt => {{
            const o = document.createElement('option');
            o.value = opt.value;
            o.textContent = opt.text;
            this.sel.appendChild(o);
        }});
    }}

    setValue(val) {{
        const idx = this.options.findIndex(o => o.value === val);
        if (idx >= 0) this._select(idx);
    }}
}}

// 初始化所有自定义下拉
const customSelects = {{}};
function initCustomSelects() {{
    document.querySelectorAll('select').forEach(sel => {{
        if (sel.id) {{
            customSelects[sel.id] = new CustomSelect(sel);
        }}
    }});
    // 全局点击：关闭所有打开的下拉菜单
    document.addEventListener('click', function(e) {{
        Object.values(customSelects).forEach(function(cs) {{
            if (cs.isOpen && !cs.wrap.contains(e.target)) {{
                cs.close();
            }}
        }});
    }});
}}

// ============================================================
// E1: 发布按钮波纹 Ripple - 多层波纹
// ============================================================
function initRipple() {{
    const btn = document.getElementById("publishBtn");
    if (!btn) return;
    btn.addEventListener("click", function(e) {{
        // 创建两层波纹，一快一慢
        for (var r = 0; r < 2; r++) {{
            const ripple = document.createElement("span");
            ripple.className = "ripple";
            const rect = btn.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height) * 2;
            ripple.style.width = ripple.style.height = size + "px";
            ripple.style.left = (e.clientX - rect.left - size/2) + "px";
            ripple.style.top = (e.clientY - rect.top - size/2) + "px";
            if (r === 1) {{
                ripple.style.animationDuration = "1.2s";
                ripple.style.background = "radial-gradient(circle, rgba(129,140,248,0.3) 0%, transparent 70%)";
            }}
            btn.appendChild(ripple);
            setTimeout(((el) => () => el.remove())(ripple), r === 0 ? 800 : 1200);
        }}
    }});
}}

// ============================================================
// E2: 卡片 3D 悬浮倾斜
// ============================================================
/* RAF 节流：卡片3D倾斜 */
var _card3DRafId = null;
var _card3DPending = null;

function initCard3D() {{
    document.querySelectorAll(".nav-card").forEach(function(card) {{
        card.addEventListener("mousemove", function(e) {{
            _card3DPending = {{ el: card, e: e }};
            if (!_card3DRafId) {{
                _card3DRafId = requestAnimationFrame(function() {{
                    var p = _card3DPending;
                    if (!p || !p.el) return;
                    var rect = p.el.getBoundingClientRect();
                    var x = (p.e.clientX - rect.left) / rect.width;
                    var y = (p.e.clientY - rect.top) / rect.height;
                    var rY = (x - 0.5) * 24;
                    var rX = (0.5 - y) * 24;
                    p.el.style.transform = "perspective(600px) rotateX(" + rX + "deg) rotateY(" + rY + "deg) translateY(-10px) scale(1.02)";
                    _card3DRafId = null;
                }});
            }}
        }});
        card.addEventListener("mouseleave", function() {{
            if (_card3DRafId) {{ cancelAnimationFrame(_card3DRafId); _card3DRafId = null; }}
            _card3DPending = null;
            this.style.transform = "";
        }});
    }});
}}

// ============================================================
// E3: Confetti 撒花效果 - 更炫更多形状
// ============================================================
function fireConfetti(count) {{
    count = count || 100;
    var container = document.getElementById("confetti-container");
    if (!container) return;
    var colors = ["#6366f1","#8b5cf6","#22c55e","#f59e0b","#ef4444","#3b82f6","#ec4899","#14b8a6","#fbbf24","#34d399"];
    var shapes = ["circle","rect","star","strip"];
    for (var i = 0; i < count; i++) {{
        (function(idx) {{
            var piece = document.createElement("div");
            piece.className = "confetti-piece";
            piece.style.left = Math.random() * 100 + "%";
            var c = colors[Math.floor(Math.random() * colors.length)];
            piece.style.backgroundColor = c;
            var shape = shapes[Math.floor(Math.random() * shapes.length)];
            var w, h, br;
            if (shape === "circle") {{ w = 6 + Math.random()*8; h = w; br = "50%"; }}
            else if (shape === "star") {{ w = 10 + Math.random()*8; h = w; br = "2px"; piece.style.boxShadow = "0 0 6px " + c; }}
            else if (shape === "strip") {{ w = 3 + Math.random()*4; h = 14 + Math.random()*12; br = "2px"; }}
            else {{ w = 6 + Math.random()*10; h = 8 + Math.random()*12; br = "2px"; }}
            piece.style.width = w + "px";
            piece.style.height = h + "px";
            piece.style.borderRadius = br;
            var fallDur = 2 + Math.random() * 2.5;
            var swayDur = 1 + Math.random() * 1.5;
            piece.style.animation = "confettiFall " + fallDur + "s ease-out forwards, confettiSway " + swayDur + "s ease-in-out " + Math.ceil(fallDur * 1000 / (swayDur * 1000)) + " times";
            piece.style.animationDelay = (Math.random() * 0.6) + "s";
            container.appendChild(piece);
            setTimeout(function() {{ piece.remove(); }}, 5500);
        }})(i);
    }}
}}

// ============================================================
// E4: 鼠标跟随光晕
// ============================================================
/* RAF 节流：鼠标跟随光晕（使用 transform 定位，避免 left/top 触发布局重排） */
var _glowRafId = null;
var _glowPending = null;

function initCursorGlow() {{
    var glow = document.getElementById("cursor-glow");
    if (!glow) return;
    glow.style.opacity = "0";
    var visible = false;
    var hideTimer = null;

    document.addEventListener("mousemove", function(e) {{
        _glowPending = {{ x: e.clientX, y: e.clientY }};
        if (!_glowRafId) {{
            _glowRafId = requestAnimationFrame(function() {{
                var p = _glowPending;
                if (p) {{
                    // 用 transform 定位，避免 left/top 触发布局重排
                    glow.style.transform = 'translate(calc(' + p.x + 'px - 50%), calc(' + p.y + 'px - 50%))';
                }}
                _glowRafId = null;
            }});
        }}
        if (!visible) {{
            glow.style.transition = "opacity 0.3s";
            glow.style.opacity = "1";
            visible = true;
        }}
        clearTimeout(hideTimer);
        hideTimer = setTimeout(function() {{ glow.style.opacity = "0"; visible = false; }}, 1500);
    }});
    document.addEventListener("mouseleave", function() {{
        if (_glowRafId) {{ cancelAnimationFrame(_glowRafId); _glowRafId = null; }}
        _glowPending = null;
        glow.style.opacity = "0";
    }});
}}

// ============================================================
// E5: 标题打字机效果 + E11 彩蛋（点击重放）
// ============================================================
var _twAnimating = false;  // 防止重复触发

function initTypewriter() {{
    var el = document.getElementById("typewriter-title");
    if (!el) return;
    var text = "\\uD83D\\uDE80 Tujue AutoSend";
    var idx = 0;
    el.innerHTML = '<span class="typewriter-cursor"></span>';
    function typeChar() {{
        if (idx < text.length) {{
            el.innerHTML = text.substring(0, idx + 1) + '<span class="typewriter-cursor"></span>';
            idx++;
            setTimeout(typeChar, 80 + Math.random() * 60);
        }} else {{
            el.innerHTML = text + '<span class="typewriter-cursor"></span>';
            setTimeout(function() {{
                el.innerHTML = text;
                _twAnimating = false;
            }}, 3000);
        }}
    }}
    _twAnimating = true;
    setTimeout(typeChar, 400);

    /* E11: 点击彩蛋 - 逐字删除后重新打字 */
    el.addEventListener('click', function() {{
        if (_twAnimating) return;
        _twAnimating = true;
        var currentText = "\\uD83D\\uDE80 Tujue AutoSend";
        var delIdx = currentText.length;
        el.innerHTML = currentText + '<span class="typewriter-cursor"></span>';
        /* 逐字删除阶段 */
        function deleteChar() {{
            if (delIdx > 0) {{
                delIdx--;
                el.innerHTML = currentText.substring(0, delIdx) + '<span class="typewriter-cursor"></span>';
                setTimeout(deleteChar, 45 + Math.random() * 30);
            }} else {{
                /* 删完了，稍停后重新打字 */
                el.innerHTML = '<span class="typewriter-cursor"></span>';
                setTimeout(function() {{
                    var typeIdx = 0;
                    function retype() {{
                        if (typeIdx < currentText.length) {{
                            typeIdx++;
                            el.innerHTML = currentText.substring(0, typeIdx) + '<span class="typewriter-cursor"></span>';
                            setTimeout(retype, 80 + Math.random() * 60);
                        }} else {{
                            el.innerHTML = currentText + '<span class="typewriter-cursor"></span>';
                            setTimeout(function() {{
                                el.innerHTML = currentText;
                                _twAnimating = false;
                            }}, 3000);
                        }}
                    }}
                    retype();
                }}, 300);
            }}
        }}
        deleteChar();
    }});
}}

// ============================================================
// E6: 进度条流光（CSS驱动，只需添加 class）
// ============================================================
function markUploading(pid) {{
    var item = document.getElementById("prog-" + pid);
    if (item) item.classList.add("pi-uploading");
}}
function clearUploadingMark(pid) {{
    var item = document.getElementById("prog-" + pid);
    if (item) item.classList.remove("pi-uploading");
}}

// ============================================================
// E7: 平台选中弹跳（在 renderPlatformGrid 中触发）
// ============================================================

// ============================================================
// E8: Toast 弹簧弹出（已通过 CSS 实现） ==========

// ============================================================
// E9: 数字滚动计数 - 弹性缓动+脉冲
// ============================================================
function animateNumber(el, targetVal) {{
    if (!el || el.dataset.animating === "true") return;
    el.dataset.animating = "true";
    var startVal = parseInt(el.textContent) || 0;
    var duration = 700;  /* longer for more visible effect */
    var startTime = performance.now();
    el.style.transition = "transform 0.15s ease";
    
    function step(now) {{
        var p = Math.min((now - startTime) / duration, 1);
        /* easeOutElastic - bouncy feel */
        var ep;
        if (p === 0) ep = 0;
        else if (p === 1) ep = 1;
        else {{ var s = 1.2; ep = Math.pow(2, -10*p) * Math.sin((p - s/4) * (2*Math.PI)/s) + 1; }}
        el.textContent = Math.round(startVal + (targetVal - startVal) * ep);
        /* pulse scale on significant change */
        if (Math.abs(targetVal - startVal) > 0 && p < 0.5) {{
            el.style.transform = "scale(1.2)";
        }} else {{
            el.style.transform = "scale(1)";
        }}
        if (p < 1) {{
            requestAnimationFrame(step);
        }} else {{
            el.textContent = targetVal;
            el.style.transform = "scale(1)";
            el.dataset.animating = "false";
        }}
    }}
    requestAnimationFrame(step);
}}

/* 重写 updateStatusBar 加入数字滚动 */
var _origUpdateStatusBar = undefined;

// ============================================================
// E10: 骨架屏加载状态
// ============================================================
function showSkeleton(containerId, type) {{
    /* type: 'cards' | 'list' | 'single' */
    var c = document.getElementById(containerId);
    if (!c) return;
    var html = "";
    if (type === "cards") {{
        html = '<div style="grid-column:1/-1;display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px;">';
        for (var i = 0; i < 4; i++) {{
            html += '<div class="skeleton-card"><div class="skeleton-circle"></div><div class="skeleton-text medium"></div><div class="skeleton-text short"></div></div>';
        }}
        html += '</div>';
    }} else if (type === "list") {{
        for (var i = 0; i < 3; i++) {{
            html += '<div style="padding:16px;border-radius:12px;background:rgba(20,22,30,0.42);border:1px solid rgba(255,255,255,0.08);margin-bottom:10px;">';
            html += '<div class="skeleton-text medium"></div><div class="skeleton-text short"></div></div>';
        }}
    }} else {{
        html = '<div class="skeleton-text" style="margin:20px auto;width:200px;"></div>';
    }}
    c.innerHTML = html;
}}

// ============================================================
// 自定义平台图标管理（localStorage 存储，带配额检查）
// ============================================================
var PLATFORM_NAMES = {{
    douyin:"抖音", kuaishou:"快手", xhs:"小红书", bilibili:"B站",
    tencent:"视频号", tiktok:"TikTok", youtube:"YouTube", instagram:"Instagram", x:"X"
}};

function getPlatformIcon(pid) {{
    var custom = localStorage.getItem("platIcon_" + pid);
    if (custom) return '<img src="' + custom + '" style="width:28px;height:28px;border-radius:50%;object-fit:cover;">';
    /* Fallback to PLAT_ICONS SVG if available, else text */
    if (typeof PLAT_ICONS !== 'undefined' && PLAT_ICONS[pid]) return PLAT_ICONS[pid].svg;
    return '<span style="font-size:14px;font-weight:700;color:rgba(255,255,255,0.7);">' + (pid.charAt(0).toUpperCase()) + '</span>';
}}

function renderCustomIconGrid() {{
    var grid = document.getElementById("customIconGrid");
    if (!grid) return;
    var html = "";
    Object.keys(PLATFORM_NAMES).forEach(function(pid) {{
        var hasCustom = !!localStorage.getItem("platIcon_" + pid);
        html += '<div class="icon-item' + (hasCustom ? ' has-custom' : '') + '" onclick="triggerIconUpload(\\'' + attrEscape(pid) + '\\')">';
        html += '<div class="ii-preview">' + getPlatformIcon(pid) + '</div>';
        html += '<span class="ii-name">' + PLATFORM_NAMES[pid] + '</span>';
        if (hasCustom) {{
            html += '<span class="ii-remove" onclick="event.stopPropagation();removePlatIcon(\\'' + attrEscape(pid) + '\\')" title="恢复默认">x</span>';
        }}
        html += '</div>';
    }});
    grid.innerHTML = html;
}}

function triggerIconUpload(platId) {{
    var input = document.createElement("input");
    input.type = "file";
    input.accept = "image/png,image/jpeg,image/svg+xml,image/gif,image/webp";
    input.onchange = function(e) {{
        var file = e.target.files[0];
        if (!file) return;
        if (file.size > 200 * 1024) {{ showToast("图标文件不能超过 200KB", "error"); return; }}
        var reader = new FileReader();
        reader.onload = function(ev) {{
            try {{
                localStorage.setItem("platIcon_" + platId, ev.target.result);
                renderCustomIconGrid();
                showToast(PLATFORM_NAMES[platId] + " 图标已更新", "success");
            }} catch (err) {{
                if (err.name === 'QuotaExceededError' || err.code === 22) {{
                    showToast("存储空间不足，请先清理部分图标", "error");
                }} else {{
                    showToast("图标保存失败: " + err.message, "error");
                }}
            }}
        }};
        reader.readAsDataURL(file);
    }};
    input.click();
}}

function removePlatIcon(platId) {{
    localStorage.removeItem("platIcon_" + platId);
    renderCustomIconGrid();
    showToast(PLATFORM_NAMES[platId] + " 已恢复默认小动物", "success");
}}

function resetAllIcons() {{
    Object.keys(PLATFORM_NAMES).forEach(function(pid) {{
        localStorage.removeItem("platIcon_" + pid);
    }});
    renderCustomIconGrid();
    showToast("所有平台图标已恢复为默认小动物", "success");
}}

// ============================================================
// 页面加载完成后初始化
// ============================================================
document.addEventListener("DOMContentLoaded", () => {{
    /* clearAllUsageTraces() 已移除 — 不应在每次启动时清除用户数据（cookies/settings/history） */
    loadPlatformData();
    initUploadZone();
    initCustomSelects();
    renderCustomIconGrid();
    /* 壁纸初始化 */
    startWPCarousel();
    loadWallpapers();
    /* 新增动画初始化 */
    initRipple();
    initCard3D();
    initCursorGlow();
    initTypewriter();
    /* 彩蛋：9连击初始化 */
    initEgg9Clicker('schedToggle', 'schedToggle', 'toggle-switch');
    initEgg9Clicker('toggleAutoRetry', 'toggleAutoRetry', 'toggle-switch-sm');

    /* 新手引导：首次启动检测（仅标记，不弹窗） */
    checkFirstLaunch();

    /* 渲染引导入口按钮（设置页进入时也会重新渲染，这里做初始渲染） */
    try {{ if (typeof renderGuideEntry === 'function') renderGuideEntry(); }} catch(e) {{ console.warn('[guide] renderGuideEntry error:', e); }}
    try {{ if (typeof renderEggGuideEntry === 'function') renderEggGuideEntry(); }} catch(e) {{ console.warn('[egg-guide] renderEggGuideEntry error:', e); }}
}});

// ============================================================
// 新手引导（Onboarding Guide）—— 轻量版
// ============================================================

var GUIDE_KEY = "tujue_onsboarding_v2";
var _guideStep = -1;
var _guideSteps = null;
var _guideActive = false;

function getGuideSteps() {{
    return [
        /* ====== 核心功能（首页卡片） ====== */

        {{ step: 0, target: ".nc-publish", title: "📤 一键发布",
            desc: "最常用的功能——选择视频、填写标题、勾选平台，一键同时发布到多个平台。支持快手、小红书、B站等。",
            pos: "below", pageId: "page-home" }},

        {{ step: 1, target: ".nc-login", title: "🔑 登录管理",
            desc: "首次使用需在此登录各平台账号。点击后出现二维码，手机扫码即可完成登录。",
            pos: "above", pageId: "page-home" }},

        {{ step: 2, target: ".nc-settings", title: "⚙️ 系统设置",
            desc: "浏览器模式、并发数、自动重试等功能在此配置。一般使用默认值即可。",
            pos: "above", pageId: "page-home" }},

        {{ step: 3, target: ".nc-history", title: "📋 发布历史",
            desc: "所有发布记录保存在此。可查看状态、搜索记录、对失败的任务进行重试。",
            pos: "above", pageId: "page-home" }},

        /* ====== 进入发布页详解 ====== */

        {{ step: 4, target: ".nc-publish", title: "进入发布页 →",
            desc: "现在带你看看发布页面的具体操作流程。",
            pos: "below", pageId: "page-home", action: function(){{ goToPage('page-publish'); }},
            noSpotlight: true }},

        {{ step: 5, target: "#uploadZone", title: "🎬 选择视频",
            desc: "点击或拖拽视频到这里。支持 mp4 / mov / avi / mkv / webm。",
            pos: "right", pageId: "page-publish" }},

        {{ step: 6, target: "#publishBtn", title: "🚀 一键发布",
            desc: "选好视频、填好标题、勾完平台后点击此按钮开始！下方会显示上传进度。",
            pos: "above", pageId: "page-publish" }},

        {{ step: 7, target: "#schedRow", title: "⏰ 定时发布",
            desc: "不想立刻发布？开启开关设置时间，到点自动发送。",
            pos: "above", pageId: "page-publish" }},

        /* ====== 完成 ====== */

        {{ step: 8, target: null, title: "✨ 准备就绪！",
            desc: "你已经了解了全部核心功能。祝你发布顺利！",
            pos: "center", pageId: "page-home", isLast: true }}
    ];
}}

/* 启动引导 —— 从设置页或首次启动调用 */
function startGuide() {{
    goHome();  /* 先回到首页 */
    _guideSteps = getGuideSteps();
    _guideStep = -1;
    _guideActive = true;
    buildProgressDots();

    var overlay   = document.getElementById("guide-overlay");
    var progress  = document.getElementById("guideProgress");
    overlay.style.display = "block";
    progress.style.display = "flex";

    nextGuideStep();
}}

/* 下一步 */
function nextGuideStep() {{
    if (!_guideActive || !_guideSteps) return;
    _guideStep++;

    if (_guideStep >= _guideSteps.length) {{ endGuide(); return; }}

    var s = _guideSteps[_guideStep];

    /* 页面切换：如果目标页面不是当前激活的，先切过去 */
    var curPage = document.querySelector(".page-home.active") ? "page-home" :
                  document.querySelector(".page-section.active") ?
                      document.querySelector(".page-section.active").id : "";

    if (s.pageId && curPage !== s.pageId) {{
        goHome();
        if (s.action) {{ s.action(); }}
        else if (s.pageId !== 'page-home') {{ goToPage(s.pageId); }}
        /* 等待页面渲染 + DOM 稳定后再定位 */
        setTimeout(function(){{ showGuideStep(s); }}, 500);
    }} else {{
        showGuideStep(s);
    }}
}}

/* 显示单步 —— 先滚动到位，RAF 后再精确计算位置 */
function showGuideStep(s) {{
    var spotlight = document.getElementById("guide-spotlight");
    var tooltip   = document.getElementById("guideTooltip");

    /* 更新内容 */
    document.getElementById("guideStepNum").textContent =
        Math.min(_guideStep + 1, _guideSteps.length);
    document.getElementById("guideTitleText").textContent = s.title;
    document.getElementById("guideDesc").innerHTML = s.desc;

    /* 按钮状态 */
    var btnNext = document.getElementById("guideBtnNext");
    if (s.isLast) {{
        btnNext.textContent = "开始使用 ✅";
        btnNext.className = "guide-btn guide-btn-done";
        btnNext.onclick = endGuide;
    }} else {{
        btnNext.textContent = "下一步 →";
        btnNext.className = "guide-btn guide-btn-next";
        btnNext.onclick = nextGuideStep;
    }}

    updateProgressDots();

    if (!s.target) {{
        /* 无目标 → 居中显示 */
        spotlight.style.display = "none";
        tooltip.style.display = "block";
        tooltip.style.left = "50%"; tooltip.style.top = "50%";
        tooltip.style.transform = "translate(-50%,-50%)";
        tooltip.className = "guide-tooltip visible";
        return;
    }}

    var el = document.querySelector(s.target);
    if (!el) {{
        spotlight.style.display = "none";
        tooltip.style.display = "block";
        tooltip.style.left = "50%"; tooltip.style.top = "45%";
        tooltip.style.transform = "translate(-50%,-50%)";
        tooltip.className = "guide-tooltip visible";
        return;
    }}

    /* 如果不需要聚光灯高亮（纯过渡步骤），只显示气泡 */
    if (s.noSpotlight) {{
        spotlight.style.display = "none";
        tooltip.style.display = "block";
        tooltip.className = "guide-tooltip visible guide-" + (s.pos || "below");
        positionTooltip(tooltip, el.getBoundingClientRect(), s.pos);
        return;
    }}

    /* 先把元素滚到视野内（instant 不触发动画避免卡顿） */
    el.scrollIntoView({{ behavior: "instant", block: "center" }});

    /* 等 layout 稳定后再获取坐标并定位 */
    requestAnimationFrame(function() {{
        var rect = el.getBoundingClientRect();
        var pad = 10;

        /* 聚光灯 */
        spotlight.style.display = "block";
        spotlight.style.left   = (rect.left - pad) + "px";
        spotlight.style.top    = (rect.top - pad) + "px";
        spotlight.style.width  = (rect.width + pad * 2) + "px";
        spotlight.style.height = (rect.height + pad * 2) + "px";

        /* 气泡 */
        tooltip.style.display = "block";
        tooltip.className = "guide-tooltip visible guide-" + (s.pos || "below");
        positionTooltip(tooltip, rect, s.pos);
    }});
}}

/* 气泡定位逻辑（独立函数方便复用） */
function positionTooltip(tooltip, rect, pos) {{
    var vw = window.innerWidth, vh = window.innerHeight;
    /* 强制 display:block 以便测量 */
    var th = tooltip.offsetHeight || 140;
    var tw = tooltip.offsetWidth || 260;

    switch(pos || "below") {{
        case "below":
            var left = Math.max(8, Math.min(rect.left, vw - tw - 8));
            tooltip.style.left = left + "px";
            tooltip.style.top = (rect.bottom + 14) + "px";
            break;
        case "above":
            var leftA = Math.max(8, Math.min(rect.left, vw - tw - 8));
            tooltip.style.left = leftA + "px";
            tooltip.style.top = (rect.top - th - 14) + "px";
            break;
        case "right":
            tooltip.style.left = (rect.right + 18) + "px";
            var topR = Math.max(8, Math.min(rect.top, vh - th - 8));
            tooltip.style.top = topR + "px";
            break;
        case "left":
            var rightL = vw - rect.left + 18;
            tooltip.style.right = rightL + "px";
            tooltip.style.left = "auto";
            var topL = Math.max(8, Math.min(rect.top, vh - th - 8));
            tooltip.style.top = topL + "px";
            break;
        default:
            tooltip.style.left = Math.max(8, Math.min(rect.left, vw - tw - 8)) + "px";
            tooltip.style.top = (rect.bottom + 14) + "px";
    }}
}}

/* 结束引导 */
function endGuide() {{
    _guideActive = false;
    document.getElementById("guide-overlay").style.display = "none";
    document.getElementById("guide-spotlight").style.display = "none";
    document.getElementById("guideTooltip").style.display = "none";
    document.getElementById("guideProgress").style.display = "none";

    localStorage.setItem(GUIDE_KEY, JSON.stringify({{ seen: true, at: Date.now() }}));

    goHome();
}}

/* 进度点 */
function buildProgressDots() {{
    var c = document.getElementById("guideProgress");
    c.innerHTML = "";
    for (var i = 0; i < _guideSteps.length; i++) {{
        (function(idx){{
            var dot = document.createElement("div");
            dot.className = "guide-dot";
            dot.onclick = function() {{ jumpToStep(idx); }};
            c.appendChild(dot);
        }})(i);
    }}
}}
function updateProgressDots() {{
    document.querySelectorAll(".guide-dot").forEach(function(d, i) {{
        d.className = "guide-dot" +
            (i < _guideStep ? " done" : i === _guideStep ? " active" : "");
    }});
}}
function jumpToStep(idx) {{
    if (idx < 0 || idx >= _guideSteps.length || !_guideActive) return;
    _guideStep = idx - 1;
    nextGuideStep();
}}

/* 首次启动检测 —— 仅标记不弹窗，由设置按钮或首次手动触发 */
function checkFirstLaunch() {{
    try {{
        var data = JSON.parse(localStorage.getItem(GUIDE_KEY));
        if (data && data.seen) return;  /* 已看过 */
    }} catch(e) {{}}
    /* 首次启动：仅做标记，不弹窗。用户可在设置中主动打开 */
    localStorage.setItem(GUIDE_KEY, JSON.stringify({{ firstLaunch: true, at: Date.now() }}));
}}

/* 清除所有使用痕迹（打包发布版本调用，确保全新体验） */
function clearAllUsageTraces() {{
    /* 1. 清除 localStorage */
    var keysToRemove = [];
    for (var i = 0; i < localStorage.length; i++) {{
        var k = localStorage.key(i);
        if (k && (k.indexOf('tujue_') === 0 || k.indexOf('platIcon_') === 0)) {{
            keysToRemove.push(k);
        }}
    }}
    keysToRemove.forEach(function(k) {{ localStorage.removeItem(k); }});

    /* 2. 通知后端清除 cookies / settings / history */
    fetch('/api/reset/all', {{ method: 'POST' }}).catch(function() {{}});

    console.log('[clean] 已清除 ' + keysToRemove.length + ' 项前端痕迹 + 后端数据');
}}

/* 在设置页显示「新手引导」入口按钮（已改为硬编码，此函数保留兼容） */
function renderGuideEntry() {{
    /* 按钮已在 HTML 中硬编码渲染，无需动态操作 */
}}

// ============================================================
// 彩蛋引导（Easter Egg Guide）—— 发现隐藏功能
// ============================================================

var EGG_GUIDE_KEY = "tujue_egg_guide_v1";
var _eggGuideStep = -1;
var _eggGuideSteps = null;
var _eggGuideActive = false;

function getEggGuideSteps() {{
    return [
        /* ====== 交互类彩蛋 ====== */

        {{ step: 0, target: "#typewriter-title", title: "🎆 标题打字机",
            desc: "点击首页顶部的「🚀 Tujue AutoSend」标题！文字会逐个删除，然后重新打出来。像魔术一样 ✨",
            hint: "💡 试着点点看！",
            pos: "below", pageId: "page-home" }},

        {{ step: 1, target: "#sunOrb", title: "☀️ 小太阳爆炸",
            desc: "在登录页找到弧形轨道上的小太阳，**双击**它！会触发粒子爆炸特效，然后自动跳回首页。超解压 💥",
            hint: "👆 快速双击！",
            pos: "right", pageId: "page-login" }},

        {{ step: 2, target: "#schedToggle", title: "🎨 9连击变色",
            desc: "在发布页的「定时发布」开关上，**快速连续点击9下**（1.2秒内）！会弹出隐藏的颜色选择器，可以自定义按钮颜色 🌈",
            hint: "👆 点快点！像连招一样：哒哒哒哒哒哒哒哒哒",
            pos: "above", pageId: "page-publish" }},

        /* ====== 视觉效果类（被动触发） ====== */

        {{ step: 3, target: ".nc-publish", title: "✨ 卡片3D倾斜",
            desc: "把鼠标悬停在首页的任意卡片上，卡片会跟随鼠标产生3D倾斜效果。像操控一块魔法板 🔮",
            hint: "🖱️ 把鼠标在卡片上移动试试",
            pos: "below", pageId: "page-home", noSpotlight: true }},

        {{ step: 4, target: null, title: "🌟 鼠标光晕",
            desc: "移动鼠标时，屏幕上会有一个淡紫色光晕跟随你的光标。像萤火虫一样跟着你飞 🧚",
            hint: "🖱️ 动动鼠标看看周围...",
            pos: "center", pageId: "page-home", noSpotlight: true }},

        {{ step: 5, target: "#publishBtn", title: "🎊 发布成功撒花",
            desc: "当所有平台都发布成功时，屏幕会飘落五彩纸屑（Confetti）！形状有圆形、方形、星形、长条... 每次都不一样 🎉",
            hint: "完成一次全成功发布就能看到！",
            pos: "above", pageId: "page-publish", noSpotlight: true }},

        /* ====== 完成 ====== */

        {{ step: 6, target: null, title: "🏆 彩蛋猎人！",
            desc: "恭喜你发现了所有隐藏功能！这些小彩蛋是我们为你准备的惊喜。继续探索吧，也许还有更多秘密等着你发现... 🥚✨",
            pos: "center", pageId: "page-home", isLast: true }}
    ];
}}

function startEggGuide() {{
    goHome();
    _eggGuideSteps = getEggGuideSteps();
    _eggGuideStep = -1;
    _eggGuideActive = true;
    buildEggProgressDots();

    var overlay   = document.getElementById("egg-guide-overlay");
    var progress  = document.getElementById("egg-guide-progress");
    overlay.style.display = "block";
    progress.style.display = "flex";

    nextEggGuideStep();
}}

function nextEggGuideStep() {{
    if (!_eggGuideActive || !_eggGuideSteps) return;
    _eggGuideStep++;

    if (_eggGuideStep >= _eggGuideSteps.length) {{ endEggGuide(); return; }}

    var s = _eggGuideSteps[_eggGuideStep];

    var curPage = document.querySelector(".page-home.active") ? "page-home" :
                  document.querySelector(".page-section.active") ?
                      document.querySelector(".page-section.active").id : "";

    if (s.pageId && curPage !== s.pageId) {{
        goHome();
        if (s.action) {{ s.action(); }}
        else if (s.pageId !== 'page-home') {{ goToPage(s.pageId); }}
        setTimeout(function(){{ showEggGuideStep(s); }}, 500);
    }} else {{
        showEggGuideStep(s);
    }}
}}

function showEggGuideStep(s) {{
    var spotlight = document.getElementById("egg-guide-spotlight-gold");
    var tooltip   = document.getElementById("egg-guide-tooltip");

    /* 更新内容 */
    document.getElementById("eggStepNum").textContent =
        Math.min(_eggGuideStep + 1, _eggGuideSteps.length);
    document.getElementById("eggTitleText").textContent = s.title;
    document.getElementById("eggDesc").innerHTML = s.desc;

    /* 提示条 */
    var hintEl = document.getElementById("eggHintBar");
    if (hintEl) {{
        hintEl.style.display = s.hint ? 'block' : 'none';
        if (hintEl && s.hint) hintEl.textContent = s.hint;
    }}

    /* 按钮 */
    var btnNext = document.getElementById("eggBtnNext");
    if (s.isLast) {{
        btnNext.textContent = "阿金牛逼(｀∀´)Ψ";
        btnNext.className = "egg-guide-btn egg-guide-btn-done";
        btnNext.onclick = endEggGuide;
    }} else {{
        btnNext.textContent = "下一个彩蛋 →";
        btnNext.className = "egg-guide-btn egg-guide-btn-next";
        btnNext.onclick = nextEggGuideStep;
    }}

    updateEggProgressDots();

    if (!s.target) {{
        spotlight.style.display = "none";
        tooltip.style.display = "block";
        tooltip.style.left = "50%"; tooltip.style.top = "50%";
        tooltip.style.transform = "translate(-50%,-50%)";
        tooltip.className = "egg-guide-tooltip visible";
        return;
    }}

    var el = document.querySelector(s.target);
    if (!el) {{
        spotlight.style.display = "none";
        tooltip.style.display = "block";
        tooltip.style.left = "50%"; tooltip.style.top = "45%";
        tooltip.style.transform = "translate(-50%,-50%)";
        tooltip.className = "egg-guide-tooltip visible";
        return;
    }}

    if (s.noSpotlight) {{
        spotlight.style.display = "none";
        tooltip.style.display = "block";
        tooltip.className = "egg-guide-tooltip visible egg-" + (s.pos || "below");
        positionEggTooltip(tooltip, el.getBoundingClientRect(), s.pos);
        return;
    }}

    el.scrollIntoView({{ behavior: "instant", block: "center" }});

    requestAnimationFrame(function() {{
        var rect = el.getBoundingClientRect();
        var pad = 10;

        spotlight.style.display = "block";
        spotlight.style.left   = (rect.left - pad) + "px";
        spotlight.style.top    = (rect.top - pad) + "px";
        spotlight.style.width  = (rect.width + pad * 2) + "px";
        spotlight.style.height = (rect.height + pad * 2) + "px";

        tooltip.style.display = "block";
        tooltip.className = "egg-guide-tooltip visible egg-" + (s.pos || "below");
        positionEggTooltip(tooltip, rect, s.pos);
    }});
}}

function positionEggTooltip(tooltip, rect, pos) {{
    var vw = window.innerWidth, vh = window.innerHeight;
    var th = tooltip.offsetHeight || 150;
    var tw = tooltip.offsetWidth || 260;

    switch(pos || "below") {{
        case "below":
            var left = Math.max(8, Math.min(rect.left, vw - tw - 8));
            tooltip.style.left = left + "px";
            tooltip.style.top = (rect.bottom + 14) + "px";
            break;
        case "above":
            var leftA = Math.max(8, Math.min(rect.left, vw - tw - 8));
            var topA = rect.top - th - 14;
            /* 边界检测：上方空间不够时 fallback 到下方或居中 */
            if (topA < 8) topA = rect.bottom + 14;
            if (topA + th > vh - 8) topA = (vh - th) / 2;
            tooltip.style.left = leftA + "px";
            tooltip.style.top = topA + "px";
            tooltip.style.right = "auto";
            break;
        case "right":
            tooltip.style.left = (rect.right + 18) + "px";
            var topR = Math.max(8, Math.min(rect.top, vh - th - 8));
            tooltip.style.top = topR + "px";
            break;
        case "left":
            var rightL = vw - rect.left + 18;
            tooltip.style.right = rightL + "px";
            tooltip.style.left = "auto";
            var topL = Math.max(8, Math.min(rect.top, vh - th - 8));
            tooltip.style.top = topL + "px";
            break;
        default:
            tooltip.style.left = Math.max(8, Math.min(rect.left, vw - tw - 8)) + "px";
            tooltip.style.top = (rect.bottom + 14) + "px";
    }}
}}

function endEggGuide() {{
    _eggGuideActive = false;
    document.getElementById("egg-guide-overlay").style.display = "none";
    document.getElementById("egg-guide-spotlight-gold").style.display = "none";
    document.getElementById("egg-guide-tooltip").style.display = "none";
    document.getElementById("egg-guide-progress").style.display = "none";

    localStorage.setItem(EGG_GUIDE_KEY, JSON.stringify({{ seen: true, at: Date.now() }}));

    goHome();

    /* 结束时撒一小波彩蛋庆祝 */
    setTimeout(function() {{ fireConfetti(30); }}, 300);
}}

function buildEggProgressDots() {{
    var c = document.getElementById("egg-guide-progress");
    c.innerHTML = "";
    for (var i = 0; i < _eggGuideSteps.length; i++) {{
        (function(idx){{
            var dot = document.createElement("div");
            dot.className = "egg-dot";
            dot.onclick = function() {{ jumpToEggStep(idx); }};
            c.appendChild(dot);
        }})(i);
    }}
}}
function updateEggProgressDots() {{
    document.querySelectorAll(".egg-dot").forEach(function(d, i) {{
        d.className = "egg-dot" +
            (i < _eggGuideStep ? " done" : i === _eggGuideStep ? " active" : "");
    }});
}}
function jumpToEggStep(idx) {{
    if (idx < 0 || idx >= _eggGuideSteps.length || !_eggGuideActive) return;
    _eggGuideStep = idx - 1;
    nextEggGuideStep();
}}

/* 在设置页显示「彩蛋引导」入口按钮（已改为硬编码，此函数保留兼容） */
function renderEggGuideEntry() {{
    /* 按钮已在 HTML 中硬编码渲染，无需动态操作 */
}}
</script>

<!-- ========== 彩蛋：9连击颜色选择器遮罩层 ========== -->
<div id="egg9Overlay" class="egg9-overlay" onclick="closeEgg9Panel(event)">
    <div class="egg9-panel" onclick="event.stopPropagation()">
        <div class="egg9-title">🎨 自定义按钮颜色</div>
        <div class="egg9-subtitle">你发现了隐藏功能！</div>
        <div id="egg9TargetName" class="egg9-target-name"></div>
        <div id="egg9Swatches" class="egg9-swatches"></div>
        <div class="egg9-custom-row">
            <input type="color" id="egg9CustomColor" value="#6366f1">
            <span>或选择自定义颜色</span>
        </div>
        <div class="egg9-actions">
            <button class="egg9-btn egg9-btn-cancel" onclick="closeEgg9Panel()">取消</button>
            <button class="egg9-btn egg9-btn-apply" onclick="applyEgg9Color()">应用颜色</button>
        </div>
    </div>
</div>

</body>
</html>'''

    # 写入文件（仅替换两个图片占位符，不影响其他 {} 字符）
    final_html = html.replace('__BG1__', bg1).replace('__BG2__', bg2)
    # 关键修复：将模板中的 {{ }} 转为正确的 CSS/JS 花括号 { }
    # （base64 编码不含 {} 字符，可安全全局替换）
    final_html = final_html.replace('{{', '{').replace('}}', '}')
    # 使用 errors='replace' 确保不写入非法 UTF-8 序列
    with open('gui.html', 'w', encoding='utf-8', errors='replace') as f:
        f.write(final_html)
    
    print(f"[OK] gui.html 已生成 ({len(html)} 字符)")


if __name__ == "__main__":
    build()
