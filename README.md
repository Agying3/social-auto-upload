# Tujue AutoSend - 图决自动发

> **social-auto-upload** 的 **GUI 桌面版 Fork** — 一键多平台视频自动发布工具

基于 [dreammis/social-auto-upload](https://github.com/dreammis/social-auto-upload) 开发，在原有 CLI / Agent 能力之上，新增 **桌面图形界面** 和 **单文件 EXE 打包**，让非技术用户也能开箱即用。

<img src="media/show/tkupload.gif" alt="demo" width="800"/>

## ✨ 与上游版本的区别

| 特性 | 上游 (social-auto-upload) | 本项目 (Tujue AutoSend) |
|------|--------------------------|------------------------|
| 使用方式 | CLI / Python 脚本 / AI Agent | **桌面 GUI 应用（双击即用）** |
| 前端 | Web 版（已归档） | **pywebview 原生桌面窗口** |
| 后端 | sau_cli.py | **Flask REST API + pywebview** |
| 打包分发 | 需要自己配 Python 环境 | **单文件 EXE (~130MB)，无需安装** |
| 登录管理 | 终端扫码 | **内置浏览器弹窗 + GUI 状态反馈** |
| 多账号 | 命令行 --account 参数 | **可视化平台卡片，一键登录/切换** |
| 定时发布 | CLI 参数 | **GUI 日期时间选择器** |
| 数据存储 | 项目目录 cookies/ | **%APPDATA%/TujueAutoSend（用户数据隔离）** |

## 支持的平台

| 平台 | 视频上传 | 图文上传 | 登录方式 | 状态 |
|------|:--------:|:--------:|----------|:----:|
| 抖音 | ✅ | ✅ | 浏览器扫码 | ✅ 稳定 |
| 快手 | ✅ | ✅ | 浏览器扫码 | ✅ 稳定 |
| 小红书 | ✅ | ✅ | 浏览器扫码 | ✅ 稳定 |
| B站 (Bilibili) | ✅ | ❌ | 浏览器扫码 | ✅ 稳定 |
| 视频号 | ✅ | ❌ | 浏览器扫码 | ✅ 可用 |
| TikTok | ✅ | ❌ | 浏览器扫码 | ⚠️ 需 Firefox |
| YouTube | 🔲 占位 | 🔲 占位 | — | 🚧 开发中 |
| Instagram | 🔲 占位 | 🔲 占位 | — | 🚧 开发中 |
| X (Twitter) | 🔲 占位 | 🔲 占位 | — | 🚧 开发中 |

## 快速开始

### 方式 A：直接使用打包好的 EXE（推荐）

1. 从 [Releases](../../releases) 下载 `TujueAutoSend.exe`
2. 双击运行
3. 点击「登录管理」→ 扫码登录各平台 → 回到「发布页」选视频发布

> 无需安装 Python、无需配置环境，Windows 10+ 即可运行。

### 方式 B：从源码运行

```bash
# 1. 克隆仓库
git clone https://github.com/YOUR_USERNAME/auto-send.git
cd auto-send

# 2. 创建虚拟环境（Python 3.12）
python -m venv venv
venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 安装浏览器驱动
playwright install chromium
patchright install chromium

# 5. 启动应用
python app.py
```

### 配置说明

首次运行前，复制配置模板：

```bash
cp conf.example.py conf.py
```

`conf.py` 中可调整：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `LOCAL_CHROME_PATH` | Chromium 路径（留空则自动检测） | 自动检测 |
| `LOCAL_CHROME_HEADLESS` | 是否无头模式 | `False`（GUI 模式需要可见浏览器） |
| `DEBUG_MODE` | 调试模式 | `False` |
| `XHS_SERVER` | 小红书服务地址 | `http://127.0.0.1:11901` |

## 项目结构

```
auto-send/
├── app.py                 # 入口：创建 pywebview 窗口，启动 Flask
├── backend.py             # Flask 后端：API 端点、登录/上传逻辑调度
├── build_gui.py           # 构建脚本：生成 gui.html（模板 → SPA）
├── gui.html               # 前端产物（由 build_gui.py 生成，不要手动改）
├── conf.py                # 运行时配置（.gitignore 忽略，需自行创建）
├── conf.example.py        # 配置模板
├── tujue.ico              # 应用图标
├── tujue.spec             # PyInstaller 打包配置
│
├── uploader/              # 各平台上传模块
│   ├── douyin_uploader/   #   抖音（最完善）
│   ├── ks_uploader/       #   快手
│   ├── xiaohongshu_uploader/#  小红书
│   ├── bilibili_uploader/ #   B站（biliup + 浏览器混合方案）
│   ├── tencent_uploader/  #   视频号
│   └── tk_uploader/       #   TikTok（Firefox）
│
├── utils/                 # 公共工具
│   ├── log.py             #   日志（loguru）
│   ├── files_times.py     #   文件路径管理
│   └── login_qrcode.py    #   二维码回调处理
│
├── media/                 # README 用到的图片资源
├── static/                # 静态资源（图标等）
├── examples/              # 上传示例脚本
├── docs/                  # 详细文档
└── skills/                # AI Agent Skill 定义
```

## 打包为 EXE

```bash
venv\Scripts\activate
pyinstaller tujue.spec --noconfirm
```

产物位于 `dist/TujueAutoSend.exe`（约 130 MB）。

打包注意事项：
- 需要 PyInstaller 6.x，`console=False`, `upx=False`
- 排除 `Crypto/pycryptodome`（避免 .pyd 解压损坏）
- `runtime_tmpdir` 需指向有足够空间的磁盘
- 打包前确保无旧进程占用 EXE

## 技术栈

| 组件 | 技术 |
|------|------|
| 桌面窗口 | [pywebview](https://github.com/r0x0r/pywebview)（系统 WebView2） |
| 后端 API | [Flask](https://flask.palletsprojects.com/) |
| 浏览器自动化 | [patchright](https://github.com/Aetheron/patchright)（反检测增强版 Playwright） |
| B站上传 | [biliup](https://github.com/biliup/biliup)（CLI + 自动安装） |
| 前端 | 原生 HTML/CSS/JS（SPA 单文件，构建系统生成） |
| 打包 | PyInstaller onefile |

## 核心功能

- **一键多平台发布**：选择视频/图文 → 填写标题描述 → 勾选目标平台 → 一键发布
- **扫码登录管理**：各平台独立登录状态，cookie 本地持久化
- **定时发布**：支持设置延迟发布时间
- **实时状态反馈**：发布进度、成功/失败 toast 提示
- **壁纸轮播**：GUI 背景支持透明度 + 自定义壁纸轮播

## 致谢

- [dreammis/social-auto-upload](https://github.com/dreammis/social-auto-upload) — 上游核心项目，提供全平台浏览器自动化能力
- [patchright](https://github.com/Aetheron/patchright) — 反检测浏览器驱动
- [biliup](https://github.com/biliup/biliup) — B站上传基础能力
- [pywebview](https://github.com/r0x0r/pywebview) — 轻量级桌面窗口方案

## License

[MIT](LICENSE)

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=dreammis/social-auto-upload&type=Date)](https://star-history.com/#dreammis/social-auto-upload&Date)
