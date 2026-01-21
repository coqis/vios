# 更新日志

???+ note "更新命令"
    ``` console
    $ quark udpate
    ```

<!-- 本日志遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 规范，   -->
<!-- 并采用 [语义化版本](https://semver.org/lang/zh-CN/)。 -->

<!-- ### ✨ 新增（Added）
- 新增 XXX 功能
- 支持 YYY 接口 / 模块

### 🔧 变更（Changed）
- 优化 ZZZ 算法性能
- 调整 API 返回字段结构

### 🐛 修复（Fixed）
- 修复在高并发情况下的崩溃问题
- 修复 Windows 环境下路径解析错误

### ⚠️ 废弃（Deprecated）
- 标记旧版 API `/v1/old-api` 为废弃 -->

---


### [**2026-01-19**] sysinfo
- ✨**每次**server启动时，更新`usr.sysinfo`字段（记录python库版本信息）。
- ✨**glib**(`glib/__init__.py`)中增加采样函数`sample_waveform`以方便修改诸如失真计算等逻辑
