# TEX / DDS（Beta：LeaderFallback）格式说明

本工具 Beta 阶段新增 `Textures/` 输出，用于把“最终渲染出来的 PNG”（IMG）进一步生成 Civ6 可用的纹理资产：
- `Textures/<Name>.dds`
- `Textures/<Name>.tex`

当前 Beta 覆盖两类：
- UI 图标/切片纹理（`IconTextureAtlases` + 总督 NORMAL/SELECTED）：使用 ModBuddy 常见的 `AssetObjects..TextureInstance`（`UISliceTexture`）。
- 领袖外交前景 fallback（`LeaderFallback.xlp` 的 `FALLBACK_NEUTRAL_*`）：目前仍使用工具内置的 TextureAsset（后续如需与 ModBuddy 完全一致，可再对齐到 TextureInstance）。

## 生成触发方式
- 在“工程总览”中生成 `IMG/图片生成清单.txt` 或 `Textures/纹理生成清单.txt`，会输出 PNG（IMG）+ 纹理（Textures）。
- “生成所有文件”同样会输出 PNG（IMG）+ 纹理（Textures）。

## Textures 不进入 civ6proj
`Textures/` 属于生成物目录，`.civ6proj` 预览/生成会排除：
- 不写入 `Folder Include="Textures\"` 
- 不写入 `Content Include="Textures\..."`

## .tex 文件（XML）关键约束
`.tex` 是 ModBuddy 纹理描述文件（XML），用于描述对应 `.dds` 的导入/导出设置与资源引用。

### UI 图标 / UISliceTexture（TextureInstance）
对 `IconTextureAtlases` 输出的 `ICON_*_<size>.png`（以及总督 NORMAL/SELECTED）会生成同名 `.tex`，结构参考：
- 根节点：`<AssetObjects..TextureInstance>`
- `m_ClassName text="UISliceTexture"`
- `m_SourceFilePath text="//civ6/main/<工程文件夹>\IMG\<Name>.png"`
- `m_DataFiles -> DDS -> m_RelativePath text="<Name>.dds"`
- 默认不使用 mip：`bUseMips=false`，`m_NumMipMaps=0`

### LeaderFallback（当前 Beta）
本工具当前生成的约束：
- `m_ClassName` 固定为 `Leader_Fallback`
- `m_Name` 与文件名一致（例如 `FALLBACK_NEUTRAL_SIQI_AMORIS`）
- `m_ResourceName` 指向同名 `.dds`（例如 `FALLBACK_NEUTRAL_SIQI_AMORIS.dds`）
- `m_SourceFilePath` 指向同名 PNG（例如 `//civ6/main/<工程文件夹>\IMG\FALLBACK_NEUTRAL_....png`）
- 像素格式：`R8G8B8A8_UNORM`
- 压缩：`NONE`
- `bUseMips=1`，`MipMapLevels` 与实际 `.dds` mip 数一致
- 宽高：默认 `960x960`

说明：当前 Beta 在 `.tex` 的 `m_MipMapData` 中只写入了第 0 级（顶层）信息；如果后续验证需要逐级列出所有 mip 的尺寸/偏移，本工具会再扩展。

## .dds 文件关键约束
本工具输出的 `.dds`：
- 使用 DX10 头（`DDS_HEADER` + `DDS_HEADER_DXT10`）
- `DXGI_FORMAT = R8G8B8A8_UNORM (28)`
- 资源维度：2D Texture
- 数据为未压缩 RGBA8（每像素 4 字节），按 mip 从大到小顺序依次写入
- mip 生成规则：每级宽高按 `floor(w/2)`, `floor(h/2)` 缩小；Beta 默认最小缩到 `3x3`（与示例一致）

如果你后续希望：
- mip 最小缩到 `1x1`，或
- 改为 BC 压缩（例如 BC3/BC7），
可以在 Beta 后续迭代再加。
