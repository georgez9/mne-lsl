# 贡献指南

## 开发环境

```powershell
conda env create -f environment.yml
conda activate mne-lsl
```

从 `develop` 创建 `feature/<name>` 或 `bugfix/<name>` 分支，提交信息使用
Conventional Commits，例如 `feat(gui): add marker event view`。

## 提交前检查

```powershell
python -m compileall -q lsl_gui tests scripts build_tools
python -m unittest discover -s tests -v
git diff --check
```

涉及真实设备时，还需分别验证 Unicorn、Tobii 和其他目标 LSL stream 的发现、连接、
停止、保存与断开流程。构建 Windows EXE 时执行：

```powershell
python -m pip install -r requirements-build.txt
.\scripts\build_release.ps1 -Python python
```

## Pull Request

PR 应说明变更目的、测试方式、涉及的 stream 类型，以及是否改变 CSV schema 或 session
manifest。不要提交受试者数据、设备日志、机器路径、设备标识或敏感配置。
