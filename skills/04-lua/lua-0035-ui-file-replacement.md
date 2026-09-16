# UI 文件替换技术（来源：18.0 BoostUnlockedPopup）

## 做什么
通过 `include()` 链覆盖游戏原生 UI 文件中的函数，实现核心 UI 行为的定制化替换——不是通过 Hook 或 Patch，而是利用 Lua 的 `include()` 加载机制，先加载原文件，再重定义目标函数。这是 Civ 6 Mod UI 修改中最常用的"文件替换"模式之一。

## 涉及文件

| 文件 | 角色 |
|------|------|
| `18.0/UI/Replacement/BoostUnlockedPopup_Core.lua` | 替换实现（200 行） |
| 游戏原生 `BoostUnlockedPopup.lua` | 被替换的源文件 |
| `18.0/UI/Arknights_Cute_Leaders_18_UI.lua` | WorldTracker UI（同模组，不同系统） |

## 技术原理

### include() 覆盖机制

游戏加载 UI 文件时，实际加载的是 `Replacements/` 下的同名文件。替换文件必须：
1. 先 `include("原始文件名")` — 加载游戏原版文件（所有原始函数定义）
2. 保存原始函数引用：`local BASE_ShowTechBoost = ShowTechBoost`
3. 重定义同名函数：`function ShowTechBoost(...) ... end`
4. 在自定义逻辑中调用 `BASE_ShowTechBoost(...)` 保留原有的部分行为

### 文件替换配置

在 ModBuddy 工程文件中配置 InGameActions：
```xml
<InGameActions>
    <ReplaceUIScript id="BoostUnlockedPopup" 
        file="UI/Replacement/BoostUnlockedPopup_Core.lua" />
</InGameActions>
```

或通过 `.modinfo`：
```xml
<ReplaceUIScript>
    <LuaContext>BoostUnlockedPopup</LuaContext>
    <LuaReplace>UI/Replacement/BoostUnlockedPopup_Core.lua</LuaReplace>
</ReplaceUIScript>
```

## 实现详解

### 原始函数保存

```lua
include("BoostUnlockedPopup");  -- 先加载原版，获得所有原始函数和变量

local BASE_ShowTechBoost = ShowTechBoost  -- 保存原始 ShowTechBoost
local BASE_ShowCivicBoost = ShowCivicBoost  -- 保存原始 ShowCivicBoost
```

### 条件路由

替换函数的第一层逻辑是**条件路由**——判断是否属于自定义触发源，不是则回退到原始行为：

```lua
function ShowTechBoost(techIndex, iTechProgress, eSource)
    -- 条件 1：本地玩家必须有 PROPERTY_SIQI_ASTGENNE
    if not Siqi_HasTraitProperty(Game.GetLocalPlayer(), PROPERTY_SIQI_ASTGENNE) then
        BASE_ShowTechBoost(techIndex, iTechProgress, eSource)
        return
    end
    -- 条件 2：只在 GoodyHut 来源时覆盖
    if eSource ~= BoostSources.BOOST_SOURCE_GOODYHUT then
        BASE_ShowTechBoost(techIndex, iTechProgress, eSource)
        return
    end
    -- 自定义逻辑...
end
```

### 自定义行为修改

当条件满足时，执行与原版相似的逻辑但做定制修改：

**1. 修改来源文本：**
```lua
-- 原版只显示 "LOC_TECH_BOOST_GOODYHUT"
-- 替换版判断 GoodyHut 标记区分来源
local XINGSHU = localPlayer:GetProperty("PROPERTY_SIQI_ASTGENNE_GRANT_RANDOM_TECHNOLOGY_BOOST_GOODY_HUT_USED")
if XINGSHU then
    msgString = Locale.Lookup("LOC_SIQI_UI_TEXT_00180021")  -- 自定义来源文本
else
    msgString = Locale.Lookup("LOC_TECH_BOOST_GOODYHUT")    -- 系统原版文本
end
```

**2. 弹窗后清理标记：**
```lua
-- 弹窗显示完毕后，重置 GoodyHut 标记为 false
OnSetProperty_FalseXingShu(Game.GetLocalPlayer())
-- → UI.RequestPlayerOperation → GameEvents.SiqiUbikaPropertyFalse
-- → GP: pPlayer:SetProperty('PROPERTY_SIQI_ASTGENNE_GRANT_RANDOM_TECHNOLOGY_BOOST_GOODY_HUT_USED', false)
```

## ShowTechBoost vs ShowCivicBoost 对称实现

两者完全对称，仅差异：

| 项目 | ShowTechBoost | ShowCivicBoost |
|------|--------------|----------------|
| 领袖检查 | `PROPERTY_SIQI_ASTGENNE` | `PROPERTY_SIQI_ASTESIA` |
| 来源标记 | `XINGSHU` → `PROPERTY_SIQI_ASTGENNE_GRANT_RANDOM_TECHNOLOGY_BOOST_GOODY_HUT_USED` | `XINGHUI` → `PROPERTY_SIQI_ASTESIA_GRANT_RANDOM_CIVIC_BOOST_GOODY_HUT_USED` |
| 纹理主题 | `BoostPopup_GlowTech` / `ResearchPanel_*` | `BoostPopup_GlowCivic` / `CivicPanel_*` |
| 图标 | `[ICON_TechBoosted]` | `[ICON_CivicBoosted]` |
| 进度对象 | `playerTechs:GetResearchCost/Progress` | `playerCulture:GetCultureCost/Progress` |
| 音效 | `Receive_Tech_Boost` | `Receive_Culture_Boost` |
| 清理函数 | `OnSetProperty_FalseXingShu` | `OnSetProperty_FalseXingHui` |

## 模式总结

### 标准 UI 文件替换模板

```lua
-- 1. 加载原始文件
include("TargetGameUIFile")

-- 2. 加载自定义支持
include("MyMod_Supports.lua")

-- 3. 保存需要覆盖的原始函数
local BASE_TargetFunction = TargetFunction

-- 4. 重新定义
function TargetFunction(...)
    -- 条件路由
    if not ShouldCustomize() then
        BASE_TargetFunction(...)
        return
    end
    -- 自定义逻辑（可复用原版的大部分代码结构）
    -- ...
end
```

### 常见替换目标

| 游戏 UI 文件 | 常见替换目的 |
|-------------|------------|
| `BoostUnlockedPopup` | 自定义尤里卡/鼓舞来源显示 |
| `EndGameMenu` | 自定义胜利/失败界面 |
| `TopPanel` | 顶部栏资源显示修改 |
| `LaunchBar` | 单位命令条修改 |
| `ProductionPanel` | 生产面板修改 |
| `GreatWorksOverview` | 巨作界面修改 |

## XML 配合

### 文件路径

| 文件 | 用途 |
|------|------|
| `UI/Replacement/BoostUnlockedPopup_Core.lua` | 替换实现（本身无 XML，纯 Lua include 覆盖） |
| 游戏原生 `BoostUnlockedPopup.xml` | 被替换的目标 UI 文件（无需自己提供，游戏自带） |
| `.modinfo` 的 `<InGameActions>` | 注册 ReplaceUIScript 映射关系 |
| `Arknights_Cute_Leaders_18_Configs.sql` | GameCapabilities 属性注册 |
| `Arknights_Cute_Leaders_18_Modifiers.sql` | 尤里卡/鼓舞触发相关 Modifier 链 |

### .modinfo 配置（核心）

```xml
<InGameActions>
    <UpdateDatabase id="Configs">
        <File>Arknights_Cute_Leaders_18_Configs.sql</File>
    </UpdateDatabase>
    <ReplaceUIScript id="BoostUnlockedPopup">
        <LuaContext>BoostUnlockedPopup</LuaContext>
        <LuaReplace>UI/Replacement/BoostUnlockedPopup_Core.lua</LuaReplace>
    </ReplaceUIScript>
</InGameActions>
```

**关键说明：** `LuaContext` 必须与游戏原生 UI 文件名**完全一致**（不含路径和扩展名）。`LuaReplace` 指向替换文件的自有路径。

### 替换配置对照表

| 配置字段 | 值 | 说明 |
|---------|-----|------|
| `LuaContext` | `BoostUnlockedPopup` | 游戏原生 UI 文件（位于游戏安装目录 UI/ 下） |
| `LuaReplace` | `UI/Replacement/BoostUnlockedPopup_Core.lua` | 替换文件路径（相对于 Mod 根目录） |
| `id` | `BoostUnlockedPopup` | 自定义标识，同项目内唯一 |

### SQL 配合 — 需要的 Property 定义

替换逻辑依赖以下 Player Property（由 SQL Modifier 写入）：

```sql
-- Configs.sql / Modifiers.sql 中定义
PROPERTY_SIQI_ASTGENNE             -- Astgenne 领袖标记（控制 ShowTechBoost 路由）
PROPERTY_SIQI_ASTESIA              -- Astesia 领袖标记（控制 ShowCivicBoost 路由）
PROPERTY_SIQI_ASTGENNE_GRANT_RANDOM_TECHNOLOGY_BOOST_GOODY_HUT_USED  -- 尤里卡来源标记
PROPERTY_SIQI_ASTESIA_GRANT_RANDOM_CIVIC_BOOST_GOODY_HUT_USED        -- 鼓舞来源标记
```

### 文件依赖关系

```
.modinfo (ReplaceUIScript 注册)
    │
    ▼
UI/Replacement/BoostUnlockedPopup_Core.lua
    │  include("BoostUnlockedPopup")     ← 游戏原生（Mod 不提供）
    │  include("Arknights_Cute_Leaders_18_Support.lua")
    │
    ├── 覆盖 ShowTechBoost()
    │     └── 检查 PROPERTY_SIQI_ASTGENNE → 自定义来源文本 → 清理标记
    │
    └── 覆盖 ShowCivicBoost()
          └── 检查 PROPERTY_SIQI_ASTESIA → 自定义来源文本 → 清理标记
```

### 注意事项

1. **不需要提供 XML 文件**：被替换的是游戏原生的 BoostUnlockedPopup.xml，Mod 只替换 .lua
2. **Include 必须在替换文件中**：`include("BoostUnlockedPopup")` 负责加载原生的所有 UI 控件，所以原生的 XML 控件可直接使用
3. **InGameActions 注册顺序**：`ReplaceUIScript` 必须在 `<UpdateDatabase>` 之后，确保 SQL 定义的 Property 已存在
4. **多 Mod 冲突**：如果多个 Mod 替换同一 UI 文件，最后加载的胜出。建议检查兼容性

## 设计要点

1. **保留原始行为**：非目标玩家/非目标场景 必须调用 `BASE_` 回退，否则破坏其他文明体验
2. **BASE_ 命名约定**：原始函数引用使用 `BASE_` 前缀，清晰区分
3. **双条件守卫**：玩家检查 + 来源检查，两层过滤
4. **GP 交互通过 EXECUTE_SCRIPT**：弹窗关闭后需要通知 GP 端清理标记
5. **文件必须包含完整实现**：不能依赖"部分覆盖"，必须完整复制原版逻辑结构
6. **注意全局变量污染**：原文件的全局变量会保留，注意命名冲突
