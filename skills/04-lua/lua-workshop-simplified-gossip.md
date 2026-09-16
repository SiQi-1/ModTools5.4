# lua-workshop-simplified-gossip — 外交情报流言简化

从工坊 Mod **Simplified Gossip (1126451168)** 提炼。通过覆盖 `DiplomacyActionView` 中流言显示函数，替换 Instance 模板实现带图标分类的简化流言展示。

---

## 快速索引

| 模式 | 适用场景 |
|------|---------|
| include() 覆盖 UI 文件函数 | 修改外交面板流言显示逻辑 |
| 自定义 Instance 模板替换 | 改变流言条目的视觉布局（加图标） |
| GossipManager API | 获取特定玩家/回合范围内的流言数据 |
| GameInfo.Gossips GroupType | 获取流言类型对应的图标分类 |
| Events.LoadGameViewStateDone 广播 | 通知其他 Mod 本 Mod 已加载 |

---

## 一、架构概览

```
DiplomacyActionView.xml (原版)
  ├─ Instance "IntelGossipHistoryPanelEntry" (无图标版)
  └─ Instance "IntelGossipHistoryPanel" (流言面板)

DiplomacyActionView_FF16.xml (替换文件)
  ├─ Instance "IntelGossipHistoryPanelEntry" (覆盖: 带图标版)
  │    ├─ Image ID="Icon"  (新增: 流言分类图标)
  │    ├─ Label ID="GossipText" (WrapWidth 调整)
  │    └─ Label ID="NewIndicator"
  └─ Instance "IntelGossipHistoryPanel" (覆盖: 与处理逻辑匹配)

DiplomacyActionView_FF16.lua (替换文件)
  └─ include("DiplomacyActionView_Expansion2")
       └─ 覆盖 OnActivateIntelGossipHistoryPanel()
            ├─ InstanceManager:new("IntelGossipHistoryPanelEntry_Override", ...)
            ├─ Game.GetGossipManager():GetRecentVisibleGossipStrings()
            └─ GameInfo.Gossips[type].GroupType → ICON_GOSSIP_xxx
```

---

## 二、核心覆盖模式

### 2.1 include() 链

```lua
-- DiplomacyActionView_FF16.lua
include("DiplomacyActionView_Expansion2");

-- 创建新的 InstanceManager，使用覆盖后的 XML 模板
local ms_IntelGossipHistoryPanelEntryIM :table = InstanceManager:new(
    "IntelGossipHistoryPanelEntry_Override",  -- XML Instance Name
    "Background"                               -- 根控件 ID
);
```

### 2.2 覆盖函数

```lua
function OnActivateIntelGossipHistoryPanel(gossipInstance:table)
    local intelSubPanel = gossipInstance;
    local selectedPlayerDiplomaticAI = ms_SelectedPlayer:GetDiplomaticAI();
    local localPlayerDiplomacy = ms_LocalPlayer:GetDiplomacy();

    ms_IntelGossipHistoryPanelEntryIM:ResetInstances();

    local bAddedLastTenTurnsItem = false;
    local bAddedOlderItem = false;

    local gossipManager = Game.GetGossipManager();
    local iCurrentTurn = Game.GetCurrentGameTurn();

    -- 只显示最近 100 回合的流言（避免性能问题）
    local earliestTurn = iCurrentTurn - 100;
    local gossipStringTable = gossipManager:GetRecentVisibleGossipStrings(
        earliestTurn, ms_LocalPlayerID, ms_SelectedPlayerID
    );

    for i, currTable:table in ipairs(gossipStringTable) do
        local gossipString = currTable[1];
        local gossipTurn = currTable[2];
        local kGossipData:table = GameInfo.Gossips[currTable[3]];

        if (gossipString ~= nil) then
            local item;
            if ((iCurrentTurn - gossipTurn) <= 10) then
                item = ms_IntelGossipHistoryPanelEntryIM:GetInstance(
                    intelSubPanel.LastTenTurnsStack
                );
                bAddedLastTenTurnsItem = true;
                -- 标记本回合/上回合的流言为"新"
                if((iCurrentTurn - 1) <= gossipTurn) then
                    item.NewIndicator:SetHide(false);
                else
                    item.NewIndicator:SetHide(true);
                end
            else
                item = ms_IntelGossipHistoryPanelEntryIM:GetInstance(
                    intelSubPanel.OlderStack
                );
                item.NewIndicator:SetHide(true);
                bAddedOlderItem = true;
            end

            if (item ~= nil) then
                -- 核心改动：根据 GroupType 设置分类图标
                item.Icon:SetIcon("ICON_GOSSIP_" .. kGossipData.GroupType);

                -- 如果图标不可见则调整文本偏移
                if(not item.Icon:IsVisible()) then
                    item.Icon:SetHide(false);
                    item.GossipText:SetOffsetX(45);
                end

                item.GossipText:SetText(gossipString);
                AutoSizeGrid(item:GetTopControl(), item.GossipText, 25, 37);
            end
        else
            break;
        end
    end

    -- 空状态占位
    if (not bAddedLastTenTurnsItem) then
        local item = ms_IntelGossipHistoryPanelEntryIM:GetInstance(
            intelSubPanel.LastTenTurnsStack
        );
        item.GossipText:LocalizeAndSetText("LOC_DIPLOMACY_GOSSIP_ITEM_NO_RECENT");
        item.NewIndicator:SetHide(true);
        AutoSizeGrid(item:GetTopControl(), item.GossipText, 25, 37);
    end

    if (not bAddedOlderItem) then
        intelSubPanel.OlderHeader:SetHide(true);
    else
        intelSubPanel.OlderHeader:SetHide(false);
    end
end
```

---

## 三、XML Instance 模板替换

### 3.1 原版（无图标）

```xml
<Instance Name="IntelGossipHistoryPanelEntry">
    <Grid ID="Background" Texture="Controls_GossipBubble" Size="450,37" ...>
        <Label ID="GossipText" WrapWidth="parent-30" Offset="17,0" ... />
        <Label ID="NewIndicator" String="[ICON_New]" Anchor="R,T" Hidden="1"/>
    </Grid>
</Instance>
```

### 3.2 覆盖版（带图标）

```xml
<Instance Name="IntelGossipHistoryPanelEntry">
    <Grid ID="Background" Texture="Controls_GossipBubble" Size="450,37" ...>
        <Image ID="Icon" Offset="20,7" Size="22,22" IconSize="22" Icon=""/>
        <Label ID="GossipText" WrapWidth="parent-55" Offset="45,0" ... />
        <Label ID="NewIndicator" String="[ICON_New]" Anchor="R,T" Hidden="1"/>
    </Grid>
</Instance>
```

**关键差异：**
- 新增 `<Image ID="Icon">` — 显示流言分类图标
- `GossipText` WrapWidth 从 `parent-30` 改为 `parent-55`，Offset 从 `17,0` 改为 `45,0`（给图标让位）

---

## 四、GossipManager API

### 4.1 获取流言数据

```lua
local gossipManager = Game.GetGossipManager();
local gossipStringTable = gossipManager:GetRecentVisibleGossipStrings(
    earliestTurn,    -- 起始回合（如 iCurrentTurn - 100）
    localPlayerID,   -- 本地玩家 ID
    targetPlayerID   -- 目标玩家 ID
);

-- 返回格式：table of {gossipString, gossipTurn, gossipTypeIndex}
for i, currTable in ipairs(gossipStringTable) do
    local gossipString = currTable[1];   -- 已本地化的流言文本
    local gossipTurn   = currTable[2];   -- 发生的回合号
    local gossipType   = currTable[3];   -- Gossips 表的 Type 索引（用于查 GroupType）
end
```

### 4.2 查流言分类图标

```lua
local kGossipData = GameInfo.Gossips[gossipType];  -- 流言类型索引
local groupType  = kGossipData.GroupType;           -- 如 "WONDER", "WAR", "CITY", "DIPLOMACY" 等
local iconName   = "ICON_GOSSIP_" .. groupType;     -- 如 "ICON_GOSSIP_WONDER"
item.Icon:SetIcon(iconName);
```

**GroupType 常见值：**
- `CITY` — 城市相关
- `WONDER` — 奇观
- `WAR` — 战争
- `DIPLOMACY` — 外交
- `GREAT_PEOPLE` — 伟人
- `RELIGION` — 宗教
- `TECH` — 科技
- `CIVIC` — 市政
- `GOVERNMENT` — 政体
- `ESPIONAGE` — 间谍

---

## 五、StatusMessagePanel 简化

该 Mod 额外替换了 `StatusMessagePanel.lua`，简化飘屏消息（移除前缀）：

```lua
include("StatusMessagePanel");

function OnStatusMessage(message:string, displayTime:number, type:number, subType:number)
    if (type == ReportingStatusTypes.GOSSIP) then
        message = message:sub(2);  -- 移除第一个字符（原版流言的标记字符）
        AddGossip(subType, message, displayTime);
    end

    if (type == ReportingStatusTypes.DEFAULT) then
        AddDefault(message, displayTime);
    end

    RealizeMainAreaPosition();
end
```

**注意：** 这里的 `subType` 参数在原版 `Events.StatusMessage` 中为 `nil`，是该 Mod 特有的扩展。

---

## 六、Mod 加载广播

```lua
-- FF16_Config_SG.lua
function BroadcastModInUse()
    LuaEvents.FF16_SimplifiedGossip();
end

function Initialize()
    print("FinalFreak16: Loading Mod - Simplified Gossip.");
    Events.LoadGameViewStateDone.Add(BroadcastModInUse);
end
Initialize();
```

**模式用途：** 通知其他 Mod（如 Notification Log）自己的存在，可用于兼容性判断。

---

## 七、关键模式总结

### 7.1 数据驱动的 UI 列表

```
Game.GetGossipManager():GetRecentVisibleGossipStrings()
  → GameInfo.Gossips[type].GroupType
    → "ICON_GOSSIP_" .. GroupType
      → item.Icon:SetIcon(iconName)
      → item.GossipText:SetText(gossipString)
      → AutoSizeGrid(item, text, minH, maxH)
```

### 7.2 分段显示模式

```lua
if ((iCurrentTurn - gossipTurn) <= 10) then
    -- 放入"最近 10 回合"分区
    item = IM:GetInstance(intelSubPanel.LastTenTurnsStack);
else
    -- 放入"更早"分区
    item = IM:GetInstance(intelSubPanel.OlderStack);
end
```

### 7.3 空状态处理

```lua
if (not bAddedLastTenTurnsItem) then
    local item = IM:GetInstance(intelSubPanel.LastTenTurnsStack);
    item.GossipText:LocalizeAndSetText("LOC_DIPLOMACY_GOSSIP_ITEM_NO_RECENT");
    item.NewIndicator:SetHide(true);
end

if (not bAddedOlderItem) then
    intelSubPanel.OlderHeader:SetHide(true);
end
```

---

## 八、AutoSizeGrid 说明

```lua
AutoSizeGrid(item:GetTopControl(), item.GossipText, 25, 37);
-- 参数: (gridControl, textControl, minHeight, maxHeight)
-- 根据文本实际行数自动调整 Grid 高度
```

---

## 九、设计要点

1. **Instance 覆盖用同名**：XML 中用同名 `<Instance Name="IntelGossipHistoryPanelEntry">` 即可覆盖原版
2. **IM 用新 Name**：如果同时存在旧模板和新模板，`InstanceManager:new("IntelGossipHistoryPanelEntry_Override", ...)` 指定独立名称（虽然该 Mod 未严格这样做——实际直接覆盖了同名 Instance）
3. **性能控制**：`earliestTurn = iCurrentTurn - 100` 限制查询范围，避免后期流言过多
4. **图标兜底**：用 `if(not item.Icon:IsVisible())` 检测图标有效性，无效时手动 `SetHide(false)` 并调整布局偏移
5. **`GetTopControl()`** 返回 Instance 的最外层控件（如 Grid/Container），用于 AutoSizeGrid
6. **LocalPlayerID / SelectedPlayerID**：来自原版 `DiplomacyActionView` 上下文变量，无需自行获取

---

## XML 配合

### XML 文件

| 文件 | 路径 | 角色 |
|------|------|------|
| 原版布局 | `UI/DiplomacyActionView.xml` | 原版外交面板流言区域（被替换） |
| 覆盖布局 | `UI/DiplomacyActionView_FF16.xml` | 带图标分类的流言布局（替换文件） |

**覆盖策略**：`DiplomacyActionView_FF16.xml` 中的同名 Instance（`IntelGossipHistoryPanelEntry`, `IntelGossipHistoryPanel`）自动覆盖原版 XML 中的定义。

### 覆盖版 Instance 关键差异

| 属性 | 原版 | 覆盖版 |
|------|------|--------|
| `IntelGossipHistoryPanelEntry` | 无图标 | 新增 `<Image ID="Icon">` (22x22) |
| `GossipText` WrapWidth | `parent-30` | `parent-55`（给图标让位） |
| `GossipText` Offset | `17,0` | `45,0`（图表在左侧） |
| `NewIndicator` | 保留 `[ICON_New]` | 不变 |

### Instance 对照表

| Instance Name | 用途 | 关键子控件 |
|--------------|------|----------|
| `IntelGossipHistoryPanelEntry` | 单条流言条目 | `Icon`(22x22 分类图标), `GossipText`(文本), `NewIndicator`(新标记) |
| `IntelGossipHistoryPanel` | 流言历史面板 | `LastTenTurnsStack`(最近10回合), `OlderHeader`(更早标题), `OlderStack`(更早条目) |

### 覆盖版 XML 结构

```xml
<Context>
  <!-- 带图标的流言条目（覆盖同名 Instance） -->
  <Instance Name="IntelGossipHistoryPanelEntry">
    <Grid ID="Background" Texture="Controls_GossipBubble" Size="450,37"
          Anchor="C,T" SliceCorner="18,18" SliceTextureSize="36,37">
      <Image ID="Icon" Offset="20,7" Size="22,22" IconSize="22" Icon=""/>
      <Label ID="GossipText" WrapWidth="parent-55" Offset="45,0"
             Style="TextButtonStyle" Anchor="L,C"/>
      <Label ID="NewIndicator" String="[ICON_New]" Anchor="R,T" Hidden="1"/>
    </Grid>
  </Instance>

  <!-- 流言历史面板（两段式：最近/更早） -->
  <Instance Name="IntelGossipHistoryPanel">
    <Container ID="Top" Size="parent,auto">
      <Stack Anchor="C,T" StackGrowth="Bottom">
        <Container Anchor="C,T" Size="parent-100,20">
          <Label String="LOC_DIPLOMACY_INTEL_LAST_TEN_TURNS"
                 Anchor="C,C" Style="DiplomacyGossipHeader"/>
        </Container>
        <Stack ID="LastTenTurnsStack" Anchor="C,T"/>
        <Container ID="OlderHeader" Anchor="C,T" Size="parent-100,20">
          <Label String="LOC_DIPLOMACY_INTEL_OLDER"
                 Anchor="C,C" Style="DiplomacyGossipHeader"/>
        </Container>
        <Stack ID="OlderStack" Anchor="C,T"/>
      </Stack>
    </Container>
  </Instance>
</Context>
```

### 图标命名规范

`GameInfo.Gossips[type].GroupType` 映射到图标名 `ICON_GOSSIP_<GroupType>`：

| GroupType | 图标名 |
|-----------|--------|
| `CITY` | `ICON_GOSSIP_CITY` |
| `WONDER` | `ICON_GOSSIP_WONDER` |
| `WAR` | `ICON_GOSSIP_WAR` |
| `DIPLOMACY` | `ICON_GOSSIP_DIPLOMACY` |
| `GREAT_PEOPLE` | `ICON_GOSSIP_GREAT_PEOPLE` |
| `RELIGION` | `ICON_GOSSIP_RELIGION` |
| `TECH` | `ICON_GOSSIP_TECH` |
| `CIVIC` | `ICON_GOSSIP_CIVIC` |
| `GOVERNMENT` | `ICON_GOSSIP_GOVERNMENT` |
| `ESPIONAGE` | `ICON_GOSSIP_ESPIONAGE` |
