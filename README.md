# LSL Recorder

一个面向 EEG、眼动、marker 及其他 Lab Streaming Layer（LSL）数据源的轻量桌面采集工具。

## 功能

- 自动发现可见的 LSL streams，不依赖写死的设备名称。
- 在 stream 列表中勾选即连接，取消勾选即断开。
- 一键开始和停止多个已连接 streams，并为每个 stream 分别保存 CSV。
- 三个独立波形图可分别选择 channel，Y 轴随当前可见数据自动缩放。
- 保存 session manifest，以及在异常退出后保留尚未确认保存的数据。
- 提供无需硬件的多 stream 模拟器。

## 直接使用 Windows EXE

正式版本会发布在 [GitHub Releases](https://github.com/georgez9/mne-lsl/releases)。下载
`LSLRecorder.exe` 后可直接运行，无需安装 Python。录制文件默认写入：

```text
Documents\LSL Recorder\Data
```

日志写入 `Documents\LSL Recorder\logs`。也可在 GUI 中选择其他输出目录，或通过
`LSL_RECORDER_DATA_DIR` 环境变量覆盖默认数据目录。

## 从源码运行

推荐使用 Conda：

```powershell
conda env create -f environment.yml
conda activate mne-lsl
python -m lsl_gui
```

也可以执行 `run_lsl_gui.bat`。基本流程为：发现 streams → 勾选连接 → 开始读取 →
停止读取 → 保存。取消勾选会断开对应 stream。

## 无硬件测试

双击 `run_demo.bat`，它会启动模拟 streams 并打开 GUI。也可以分别运行：

```powershell
python scripts/simulate_lsl_streams.py
python -m lsl_gui
```

GUI 中会出现 `Demo-EEG`、`Demo-Aux` 和 `Demo-Events` 三个可独立连接的逻辑 stream，
用于测试多流连接、三通道波形选择、录制、保存与断开。

## 测试与构建

```powershell
python -m unittest discover -s tests -v
python -m pip install -r requirements-build.txt
.\scripts\build_release.ps1 -Python python
```

构建产物位于 `dist/`，不会提交到 Git。完整发布步骤见
[docs/release-guide.md](docs/release-guide.md)。

## 仓库目录

```text
.github/workflows/  CI 与 tag 发布流程
build_tools/        PyInstaller 入口和 spec
docs/               共享与发布文档
lsl_gui/            正式应用源码
scripts/            模拟器和构建脚本
tests/              无硬件单元测试
```

本地采集数据、`legacy/`、`plan/`、IDE 配置、环境目录和构建产物均被 Git 忽略。具体规则见
[docs/repository-policy.md](docs/repository-policy.md)。

## License

本项目使用 [MIT License](LICENSE)。第三方组件继续遵循各自许可证，相关说明见
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
