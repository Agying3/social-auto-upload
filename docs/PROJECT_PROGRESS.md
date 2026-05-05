# Tujue AutoSend - 项目进度文档

> 最后更新：2026-04-30

---

## 一、项目概述

**Tujue AutoSend** 是一款多平台视频一键发布桌面工具，基于 [social-auto-upload](https://github.com/dreammis/social-auto-upload) 二次开发。

用户在 GUI 界面选择视频文件、填写标题/描述/标签、勾选目标平台，点击发布后程序自动调用浏览器完成各平台的上传和发布全流程。

| 维度 | 说明 |
|------|------|
| 技术栈 | Python + Flask 后端 + pywebview 桌面前端 |
| 前端 | `build_gui.py` 生成 `gui.html`（单文件 SPA，4 页面） |
| 后端 | `backend.py`（24 个 API 端点，~1524 行） |
| 打包 | PyInstaller 6.20.0 --onefile，产物 `TujueAutoSend.exe`（~130 MB） |
| 数据存储 | `%APPDATA%/TujueAutoSend/`（cookies、settings、logs、uploads） |
| 自动化引擎 | patchright（防风控替代 playwright）+ Chromium |

---

## 二、已完成/完善的功能

### 2.1 核心发布流程（6 个平台可用）

| 平台 | 状态 | 上传方式 | 浏览器引擎 | 备注 |
|------|------|----------|-----------|------|
| 抖音 | ✅ 可用 | 浏览器自动化 | patchright + Chromium | 支持 headless=False |
| 快手 | ✅ 可用 | 浏览器自动化 | patchright + Chromium | 2026-04-30 修复发布按钮选择器 |
| 小红书 | ✅ 可用 | 浏览器自动化 | patchright + Chromium | |
| B站 | ✅ 可用 | 浏览器自动化 | patchright + Chromium | stream_gears API 已被封，改用浏览器 |
| 视频号 | ✅ 可用 | 浏览器自动化 | patchright + Chromium | Wujie 微前端 + Shadow DOM |
| TikTok | ✅ 可用 | 浏览器自动化 | playwright + Firefox | 独立使用 Firefox |

### 2.2 GUI 界面（4 页面 SPA）

| 页面 | 功能 |
|------|------|
| 首页 | 壁纸轮播背景（6 秒切换）、3D 卡片导航 |
| 发布页 | 视频选择、标题/描述/标签填写、平台多选、一键发布 |
| 账号页 | 各平台账号管理、扫码登录、Cookie 有效性检查 |
| 设置页 | 通用设置、缓存清理、配置导入导出 |

### 2.3 后端 API（24 个端点）

- **上传相关**：`/api/upload`（核心发布）、`/api/upload/video`（视频上传）、`/api/status`（状态查询）、`/api/diagnose/upload`（诊断）
- **登录相关**：`/api/login/start/<platform>`（启动扫码）、`/api/login/status/<session_id>`（查询状态）、`/api/check-cookie/<platform>`（Cookie 检查）、`/api/logout/<platform>`（退出登录）
- **平台信息**：`/api/platforms`（平台列表）、`/api/accounts/<platform>`（账号列表）、`/api/bilibili/zones`（B站分区）
- **历史/设置**：`/api/history`（CRUD）、`/api/settings`（读写）、`/api/cache/clear`（清缓存）、`/api/config/export` + `/import`（配置导入导出）

### 2.4 本次（4 月 30 日）修复的关键问题

#### 快手发布
- **发布按钮选择器修复**：快手更新了 DOM，发布按钮从 `<button>` 改为 `<div class="_button-primary_xxx">`，位于 `div[class*='edit-section-btns']` 容器内（y≈1189 需滚动可见）
- **上传超时增大**：从 120 秒增加到 600 秒（支持大视频上传）
- **上传超时终止**：视频未上传完直接报错终止，不再继续点发布
- **microSupport 弹窗处理**：定期检测并关闭创作者服务弹窗

#### B站发布（前期修复）
- **投稿按钮只点一次**：加 `publish_clicked` 标志位，防止重复点击
- **7 种成功信号检测**：Toast 提示、表单重置、按钮消失、再次投稿按钮、URL 跳转等
- **本地草稿弹窗处理**：自动关闭
- **封面必填检测**：上传后检查封面状态，空则用 opencv 截取第一帧
- **分区选择器**：前端双级分区选择器 + 后端 API

#### 通用健壮性
- **`print()` → `logging`**：EXE 中 `console=False` 模式 `sys.stdout` 为 None，`print()` 会导致线程静默死亡
- **`json=` → `json_data=`**：`requests_post_internal()` 参数名修复
- **uploads 目录迁移到 G 盘**：避免 C 盘空间不足（C 盘仅 0.6GB 可用）
- **`runtime_tmpdir` 设为 G 盘**：onefile 解压临时目录
- **PyInstaller 排除 pycryptodome**：.pyd 文件解压损坏
- **UPX 压缩关闭**：`upx=False` 防止 .pyd 损坏

---

## 三、常见问题与踩坑记录

### 3.1 平台相关

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 快手发布按钮找不到 | 快手改了 DOM，按钮不是 `<button>` 而是自定义 `<div>` | 用 `div[class*='edit-section-btns'] div[class*='button-primary']` 选择器 |
| 快手 microSupport 弹窗拦截操作 | 创作者服务通知弹窗遮挡页面 | 定期检测 `#microSupport .ant-modal-wrap` 并关闭 |
| B站投稿工具停用 | stream_gears API 被封 | 改用 patchright 浏览器自动化 |
| B站投稿按钮只能点一次 | 旧代码循环点击导致重复上传 | 加标志位只点一次 |
| B站 `set_input_files` 浏览器崩溃 | bcc-upload-wrapper 组件不支持 | 改用 `file_chooser` 事件方式 |
| 视频号 Wujie Shadow DOM | 元素在 Shadow DOM 中 | 用 `page.evaluate()` + JS `click()` |
| 抖音 shepherd 引导弹窗 | 新用户引导遮挡操作 | `_dismiss_guide_popups()` 关闭 |
| Cookie 频繁失效 | 平台会话过期 | 每次发布前检查有效性，失效提示重新登录 |

### 3.2 构建与打包

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| EXE 启动失败 | C 盘空间不足（onefile 解压 ~300MB） | `runtime_tmpdir` 设为 G 盘 |
| EXE 中线程静默死亡 | `console=False` 模式 `print()` 在 None stdout 上抛异常 | 全部替换为 `logging.info/warning/error` |
| .pyd 文件解压损坏 | Crypto/pycryptodome 被间接依赖 | PyInstaller excludes 列表中排除 |
| `_MEI*` 临时目录残留 | EXE 崩溃后未清理 | 手动清理 `G:\Tujue\auto-send\_tmp\_MEI*` |
| EXE 文件被锁无法写入 | 上一个 EXE 进程还在运行 | 打包前杀掉所有 TujueAutoSend 进程 |

### 3.3 前端（build_gui.py → gui.html）

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| JS 全部失效（函数未定义） | 花括号不匹配或多余 `}}` | 修改后用脚本检查花括号计数 |
| `setInterval` + `async` 请求风暴 | fetch 极快时产生大量并发请求 | 改用 `setTimeout` 递归 |
| onclick 中的单引号转义 | Python → JS 转义链路问题 | Python 中写 `\\'` |
| 非 BMP emoji 损坏 | 构建链路编码问题 | 改用 ASCII 标识或 Unicode 转义 |

---

## 四、当前不足与已知问题

### 4.1 稳定性

- **平台 DOM 脆弱**：所有平台的上传/发布流程依赖浏览器 DOM 选择器，平台前端一更新就可能失效（如快手发布按钮）
- **没有自动回归测试**：无法在平台更新后及时发现选择器失效
- **大视频上传不稳定**：快手/B站上传 100MB+ 视频时偶尔超时或失败，网络波动影响大
- **发布成功检测不完美**：部分平台（快手、视频号）的成功检测依赖 URL 跳转或弹窗提示，容易漏检

### 4.2 架构

- **build_gui.py 过于庞大**（143KB / 3331 行）：整个前端 HTML/CSS/JS 作为 Python 模板字符串嵌入，难以维护和调试
- **两套冗余系统**：`backend.py` + `gui.html`（当前使用）和 `sau_backend.py` + `sau_frontend/`（Vue3 SPA，未使用）共存
- **代码质量参差**：百家号和 TikTok 上传器仍为旧式（继承 `object`），未按 BaseVideoUploader 重构
- **根目录杂乱**：~70 个 `_debug_*`、`_check_*`、`_diag_*`、`_test_*` 临时脚本未清理
- **单线程发布**：多平台发布是顺序执行（逐个上传），不是真正并发

### 4.3 功能缺失

- **没有图文笔记发布**：快手和小红书的 Note 上传器有代码但未在 GUI 中暴露
- **没有定时发布**：部分平台（快手、B站）支持定时发布但 GUI 没有入口
- **没有批量发布**：一次只能发布一个视频
- **没有发布模板**：每次都要重新填标题/描述/标签
- **没有发布数据统计**：没有成功率、耗时分析等数据看板
- **没有错误重试 UI**：发布失败后只能全部重新发布

### 4.4 用户体验

- **C 盘空间敏感**：EXE 启动需要解压 300MB，C 盘 < 1GB 时会失败
- **启动速度慢**：onefile 模式启动需 5-10 秒解压
- **Cookie 过期感知差**：Cookie 失效后用户才知道，没有自动刷新机制
- **没有进度反馈**：大视频上传时用户只能看到"上传中"，没有进度条

---

## 五、下一步计划

### P0 - 必须修复（稳定性）

- [ ] **建立选择器健康检查机制**：每次发布前用诊断脚本验证各平台关键选择器是否仍然有效
- [ ] **完善快手发布成功检测**：当前只检测 URL 跳转和页面文字，需要增加更多信号
- [ ] **增加上传进度反馈**：读取浏览器上传进度条，展示给用户
- [ ] **清理根目录临时文件**：删除所有 `_debug_*`、`_check_*`、`_diag_*` 脚本

### P1 - 功能增强

- [ ] **图文笔记发布**：快手/小红书 Note 上传器接入 GUI
- [ ] **定时发布 UI**：为支持定时发布的平台增加时间选择器
- [ ] **批量发布**：支持一次选择多个视频文件，排队发布
- [ ] **发布模板**：保存/加载标题/描述/标签模板
- [ ] **重试失败平台**：发布结果页增加"仅重试失败平台"按钮

### P2 - 架构优化

- [ ] **前端重构**：从 build_gui.py 模板字符串迁移到独立的前端项目（可复用 sau_frontend）
- [ ] **并发发布**：多平台同时上传（需注意浏览器实例数量控制）
- [ ] **统一上传器接口**：百家号和 TikTok 按需重构为 BaseVideoUploader 子类
- [ ] **自动化测试**：为核心流程编写 E2E 测试（至少覆盖 Cookie 检查 + 上传启动 + 发布按钮点击）
- [ ] **日志和监控**：结构化日志 + 发布成功率统计 + 耗时分析

### P3 - 长期规划

- [ ] **YouTube/Instagram/X 接入**：当前为占位平台（`supported: False`）
- [ ] **自动 Cookie 刷新**：定期检查并自动续期
- [ ] **多账号支持**：同一平台同时维护多个账号
- [ ] **云端同步**：配置和 Cookie 云端备份
- [ ] **发布数据分析**：各平台流量统计、最佳发布时间推荐

---

## 六、技术栈详情

### 后端核心依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| patchright | 1.58.2 | 防风控浏览器自动化（兼容 playwright API） |
| playwright | 1.52.0 | TikTok 使用（Firefox） |
| flask | 3.1.1 | Web 框架 |
| flask-cors | 6.0.0 | 跨域支持 |
| pywebview | 6.2.1 | 桌面窗口 |
| loguru | 0.7.3 | 日志（部分模块使用） |
| opencv-python | 4.13.0 | 视频封面截取 |
| PyInstaller | 6.20.0 | EXE 打包 |
| biliup | 0.4.98 | B站上传（API 已被封，仅保留依赖） |

### 项目文件结构

```
g:\Tujue\auto-send\
├── app.py                    # 主入口（161 行）
├── backend.py                # Flask 后端（1524 行，24 个 API）
├── build_gui.py              # GUI 构建器（3331 行，生成 gui.html）
├── gui.html                  # 生成的 SPA 前端（638KB）
├── tujue.spec                # PyInstaller 打包配置
├── conf.py                   # 全局配置
├── uploader/                 # 各平台上传器
│   ├── base_video.py         # 基类
│   ├── bilibili_uploader/    # B站（~2600 行）
│   ├── douyin_uploader/      # 抖音（~1500 行）
│   ├── ks_uploader/          # 快手（~1100 行）
│   ├── tencent_uploader/     # 视频号（~1700 行）
│   ├── xiaohongshu_uploader/ # 小红书（~850 行）
│   ├── tk_uploader/          # TikTok（~320 行）
│   └── baijiahao_uploader/   # 百家号（~700 行，旧式）
├── cookies/                  # Cookie 存储（Playwright storage_state JSON）
├── sau_frontend/             # Vue3 前端（未使用，备用）
├── sau_backend/              # 独立后端（仅 README）
├── examples/                 # 7 平台使用示例
├── tests/                    # 测试（覆盖不足）
├── skills/                   # 各平台 SKILL 文档
└── docs/                     # 文档
```

---

*本文档由 AI 助手根据代码分析和开发日志自动生成，如有遗漏请补充。*
