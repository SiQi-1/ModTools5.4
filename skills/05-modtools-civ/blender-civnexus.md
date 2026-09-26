# Blender / CivNexus6 模型与动画交换

适用：CN6 导入导出、NA2 动画参考、FGX 制作路线。单张立绘和平面纸片先读 [领袖美术](leader-art.md)。

## 工具边界

Sukritact 的 Nexus-Buddy-2-Blender-Scripts 提供 CN6 导入、CN6 导出和 NA2 导入三个 Blender 脚本。CN6 是 Blender 与 CivNexus6 的交换环节；插件不等于直接在 ModTools 生成 FGX 或完成 Cooker 构建。

- 导出脚本署名 Deliverator，导入脚本署名 Deliverator、Sukritact。
- 上游标称 Blender 2.8+，README 说明 3.x / 4.x 可用；通用动画兼容性未验证；2026-09-25 在 Blender 4.5.2 用本机现有插件完成了单网格静态 CN6 样板导出。
- 动画导入前先加载模型/骨架，确认所选对象和骨架匹配。NA2 不替代模型接线。

## 交换与排错

1. 明确目标对象、原模型来源、修改范围、Blender 版本，保留原文件。
2. 按上游说明安装用户自行获取的插件，加载 CN6 模型，需要动画时再导入 NA2。
3. 核对材质槽、UV、骨架、权重和坐标变换，再导出 CN6。
4. 用 CivNexus6 完成转换，补齐 GEO / AST / MTL / XLP / ArtDef 引用。
5. 经 SDK Cooker 构建，在游戏验证比例、姿态、材质、动画和模型绑定。

所审阅脚本含材质索引、最多八个骨骼影响和总和 255 的量化权重处理。导出失败应查该版本代码及具体输入，不能在 ModTools 中猜测修补二进制。能导入 Blender 不证明游戏动作状态正确。

已生成工程可用 [资源与 Cooker 检查](art-cook-validation.md)。当前通用 CLI 不解析 FGX 骨架、重建模型或执行 Blender。独立自建样板的已验证路径、DDS 排错和边界见 [自建静态模型](../civ6-landmarks/references/custom-model-prototype.md)。

## 来源与版本

[来源 S1](../../THIRD_PARTY_NOTICES.md)：[Sukritact/Nexus-Buddy-2-Blender-Scripts](https://github.com/Sukritact/Nexus-Buddy-2-Blender-Scripts)，派生自 Deliverator 的 Civilization-Blender-Scripts。本次提交：0a39dfbecdf23971f3df146765858a1f0e15505f；读取 README.md、Blender-2.8-Addons/io_import_cn6.py、io_export_cn6.py、io_import_na2.py。

该提交没有 LICENSE 或脚本授权声明。本项目仅提供引用和工作流，不分发插件源码。再分发时应核对上游许可。

## 已有 BLP 的复原证据

从已烤制 BLP 提取几何与从 Blender 制作源模型是不同入口。按 [美术解包与复原验收](art-unpack.md) 核对多子网格、骨架、UV、类名和 pantry 同名遮蔽；千川白浪移交包的历史成功率不作为本项目复现结果。
