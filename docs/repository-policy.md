# 公开仓库内容规范

## 应提交到 Git

- `lsl_gui/`：正式应用源码。
- `tests/`：无需真实设备或受试者数据的自动化测试。
- `scripts/`：模拟器、构建和维护脚本。
- `build_tools/`：PyInstaller 入口及可复现 spec。
- `licenses/`：随二进制分发所需的已审核 native dependency 许可文本。
- `.github/workflows/`：CI 和 GitHub Release workflow。
- `docs/`、`README.md`、`CONTRIBUTING.md`、`CHANGELOG.md`：面向使用者的文档。
- `environment.yml`、`requirements*.txt`：公开依赖声明。
- `.gitignore`、`.gitattributes`、`.editorconfig`：仓库一致性配置。
- 根目录 `.bat`：不包含绝对路径或凭据的 Windows 入口。

## 仅留本地，不提交

- `Data/`、`data/`、`outputs/`、`logs/`：EEG、眼动、marker 与运行输出。
- `.pending/`、`*.csv.part`、普通 `*.csv`：采集文件和未完成记录。
- `legacy/`：旧 notebook、旧设备脚本及历史设备标识，仅作本地参考。
- `plan/`：实现笔记、内部计划和可能包含本机路径的过程材料。
- `build/`、`dist/`、`*.exe`、`*.sha256`：本地构建产物；EXE 只发布到 Release。
- `.idea/`、`.vscode/`、`__pycache__/`、`.ipynb_checkpoints/`：工具状态。
- `.venv/`、`venv/`、`env/`：本地 Python 环境。
- `.env*`、`settings.json`、credentials、keys、tokens 和数据库文件。

只有经过匿名化、授权和人工检查的小型测试 fixture 才能放入 `tests/fixtures/`。

## 发布前的 Git 历史检查

`.gitignore` 只影响新的提交，不能清除旧 commit 中已经出现的 notebook 输出、本机路径、
设备标识或 IDE 文件。首次公开前应审计完整 Git 历史；若历史中存在不适合公开的内容，
优先创建一个只包含已审核当前快照的干净公开仓库。重写现有远端历史属于破坏性操作，
必须单独确认并通知所有协作者。
