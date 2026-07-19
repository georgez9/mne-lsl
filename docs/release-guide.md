# Windows 发布指南

## 本地构建

先激活包含依赖的 Python 环境，然后执行：

```powershell
python -m pip install -r requirements-build.txt
.\scripts\build_release.ps1 -Python python
```

也可以在已激活 Conda 环境后双击 `build_release.bat`。构建脚本会运行测试、生成
`dist/LSLRecorder.exe`、执行无界面 smoke test，并生成 SHA256 和第三方许可文本。

## 发布 GitHub Release

确认代码已经提交并推送后，创建版本 tag：

```powershell
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0
```

`.github/workflows/release.yml` 会在 Windows runner 上重新测试和打包，并保存 Actions
artifact。通过检查后，版本 tag 会把 EXE、SHA256、项目 MIT License 与第三方许可文本
上传到对应 GitHub Release。

## 发布前检查

- 在无 Python 环境的 Windows 机器上验证 EXE。
- 用真实 Unicorn、Tobii 及目标 LSL streams 验证发现、连接、录制和保存。
- 检查 Release 中的 SHA256 是否与下载文件一致。
- 确认根目录 MIT `LICENSE` 的版权信息仍然正确。
- 审计构建生成的 `THIRD_PARTY_LICENSES.txt`，确认包含实际打包依赖的许可文本。
- 如面向较多外部用户，建议购买代码签名证书并在 workflow 中安全配置签名。

未签名 EXE 可能触发 Windows SmartScreen 提示，这是发布流程之外的信任与签名问题。
