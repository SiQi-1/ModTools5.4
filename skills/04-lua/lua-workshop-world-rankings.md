# lua-workshop-world-rankings — UI 文件替换 + 函数覆盖模式

从 Better World Rankings (Infxo) 提炼的 UI 增强模式：通过 `include()` 复用原版 UI，仅替换目标函数。

---

## 快速索引

| 模式 | 适用场景 |
|------|---------|
| 函数覆盖（cache + redefine） | 增强原版 UI 的特定步骤（数据采集/行填充/列格式化） |
| DLC 分文件加载 | Base / XP1 / XP2 各自独立的 XML + Lua |
| 数据增强采集 | 在 Gather 阶段追加自定义字段 |
| 实例行内容增强 | 在 Populate 阶段写入额外控件 |
| 全替换（忽略原版） | 完全重写某个展示逻辑 |

---

## 一、核心架构：分文件加载

```
Base/WorldRankings_Base_BWR.lua   → include("WorldRankings"); include("WorldRankings_BWR")
XP2/WorldRankings_Expansion2_BWR.lua → include("WorldRankings_Expansion2"); include("WorldRankings_BWR")
WorldRankings_BWR.lua              → 实际修改逻辑（被 Base 和 XP2 共用）
```

**原理**：游戏根据 DLC 加载不同入口文件，但都 `include("WorldRankings_BWR")` 复用同一套修改逻辑。

### 模板

```lua
-- Base 入口（Base/MyModScreen_Base.lua）
include("MyModScreen");        -- 原版 Base 逻辑
include("MyModScreen_Mod");    -- Mod 增强

-- XP2 入口（XP2/MyModScreen_XP2.lua）
include("MyModScreen_Expansion2");  -- 原版 XP2 逻辑
include("MyModScreen_Mod");        -- Mod 增强（同一个文件）

-- Mod 增强（MyModScreen_Mod.lua）
-- Cache base functions
BASE_GatherData = GatherData;
BASE_PopulateRow = PopulateRow;

-- 重新定义
function GatherData()
    local data = BASE_GatherData();
    -- 追加自定义字段...
    return data;
end

function PopulateRow(instance, rowData)
    BASE_PopulateRow(instance, rowData);
    -- 写入额外控件...
end
```

---

## 二、函数覆盖模式（Function Hooking）

### 2.1 基本覆盖

```lua
-- 1. 缓存原版函数
BASE_PopulateRow = PopulateRow;

-- 2. 重新定义（先调原版，再做自己的事）
function PopulateRow(instance, playerData)
    BASE_PopulateRow(instance, playerData);
    -- 添加额外字段
    instance.ExtraField:SetText("[COLOR_Culture]" .. tostring(playerData.ExtraValue) .. "[ENDCOLOR]");
    instance.ExtraIcon:SetText(playerData.HasFlag and "[ICON_CheckSuccess]" or "[ICON_CheckFail]");
end
```

### 2.2 全量替换（不调原版）

适用于需要完全改变展示逻辑的场景。Better World Rankings 对 Score 页做了全替换，实现"始终显示详细分类分数"。

```lua
-- 不缓存原版，直接覆盖
function PopulateScoreInstance(instance, playerData)
    -- 完全自定义逻辑
    PopulatePlayerInstanceShared(instance, playerData.PlayerID);
    instance.Score:SetText(playerData.PlayerScore);
    ResizeLocalPlayerBorder(instance, 75 + 9);

    -- 遍历分数分类，默认 7 个可见 + 其余汇入 tooltip
    local detailsText = "";
    for i, category in ipairs(playerData.Categories) do
        local info = GameInfo.ScoringCategories[category.CategoryID];
        local tt = Locale.Lookup(info.Name) .. ": " .. category.CategoryScore;
        local slot = tScoresMap[info.CategoryType];
        if slot then
            instance[slot[1]]:SetText(slot[2] .. tostring(category.CategoryScore));
            instance[slot[1]]:SetToolTipString(tt);
            instance[slot[1]]:SetHide(false);
        else
            if #detailsText > 0 then detailsText = detailsText .. "[NEWLINE]"; end
            detailsText = detailsText .. tt;
        end
    end
    if #detailsText > 0 then
        instance.ScoreX:SetToolTipString(detailsText);
        instance.ScoreX:SetHide(false);
    end
end
```

### 2.3 XML 实例扩展

在 XML 中覆盖原版 Instance（同名），增加新的控件子元素。原版 Lua 的 `BuildInstanceForControl("OverallInstance", ...)` 会自动加载覆盖后的 XML Instance。

```xml
<!-- 覆盖原版 OverallInstance，在原基础上增加 HasCapital/Line1/Line2 -->
<Instance Name="OverallPlayerInstance">
    <Container ID="CivIconBackingFaded" Size="36,70">
        <!-- 原版结构保留... -->
        <!-- 新增字段 -->
        <Label ID="HasCapital" Hidden="true" Offset="21,21" Style="FontNormalMedium14"
               String="[ICON_Capital]" ToolTip="LOC_WORLD_RANKINGS_DOMINATION_HAS_ORIGINAL_CAPITAL"/>
        <Label ID="Line1" Anchor="C,B" Offset="0,-21" String="Line1" Style="FontNormal14"/>
        <Label ID="Line2" Anchor="C,B" Offset="0,-36" String="Line2" Style="FontNormal14"/>
    </Container>
</Instance>
```

---

## 三、数据增强采集（Gather 阶段）

在采集阶段追加自定义字段，供后续 Populate 使用。

```lua
function GatherCultureData()
    -- 先获取原版数据
    local data = BASE_GatherCultureData();
    local localPlayer = Game.GetLocalPlayer();
    local playerCulture = Players[localPlayer]:GetCulture();

    for _, teamData in ipairs(data) do
        for _, playerData in ipairs(teamData.PlayerData) do
            local playerID = playerData.PlayerID;

            -- 追加字段
            playerData.CulturePerTurn = Round(Players[playerID]:GetCulture():GetCultureYield(), 0);
            playerData.ToolTip = playerCulture:GetTouristsFromTooltip(playerID);
            playerData.TourismBoost = CalculateTourismBoost(playerID);  -- 自定义计算
            playerData.TradeRoute = CheckTradeRoute(localPlayer, playerID);
            playerData.OpenBorders = Players[localPlayer]:GetDiplomacy():HasOpenBordersFrom(playerID);
            playerData.CulturalDominance = playerCulture:IsDominantOver(playerID);
        end
    end
    return data;
end
```

---

## 四、胜利类型适配

Better World Rankings 根据胜利类型显示不同的数据格式（科学/文化/征服/宗教/外交），核心模式：通过 TiebreakSummary 文本推断胜利类型。

```lua
-- 推断胜利类型
local function DetectVictoryType()
    for _, playerData in pairs(teamData.PlayerData) do
        if     string.match(playerData.SecondTiebreakSummary, "ICON_Science") then return "VICTORY_TECHNOLOGY";
        elseif string.match(playerData.SecondTiebreakSummary, "ICON_Culture") then return "VICTORY_CULTURE";
        elseif string.match(playerData.SecondTiebreakSummary, "ICON_Faith") then return "VICTORY_RELIGIOUS";
        elseif string.match(playerData.FirstTiebreakSummary, "/") then return "VICTORY_DIPLOMATIC";
        else
            local digits = string.match(playerData.FirstTiebreakSummary, '%d+');
            if digits and tonumber(digits) > 20 then return "VICTORY_CONQUEST"; end
        end
    end
    return "";
end

-- 按胜利类型设置格式和颜色
if     victoryType == "VICTORY_TECHNOLOGY" then
    instance.Line1:SetText(tostring(score1));
    instance.Line2:SetText("[COLOR_Science]" .. tostring(score2) .. "[ENDCOLOR]");
elseif victoryType == "VICTORY_CULTURE" then
    instance.Line1:SetText("[COLOR_Tourism]" .. tostring(score1) .. "[ENDCOLOR]");
    instance.Line2:SetText("[COLOR_Culture]" .. tostring(score2) .. "[ENDCOLOR]");
elseif victoryType == "VICTORY_CONQUEST" then
    local hasCapital, numCaptured = CheckOriginalCapitals(playerID);
    instance.HasCapital:SetHide(not hasCapital);
    instance.Line1:SetText(tostring(numCaptured));
    instance.Line1:SetToolTipString(Locale.Lookup("LOC_WORLD_RANKINGS_DOMINATION_SUMMARY", numCaptured));
    instance.Line2:SetText("[COLOR_Military]" .. tostring(score2) .. "[ENDCOLOR]");
-- ... 其余类型
end
```

---

## 五、实例尺寸动态调整

当数据量变化时，动态调整容器高度。

```lua
local SIZE_OVERALL_BG_HEIGHT = 95;
local SIZE_OVERALL_INSTANCE = 75;

function PopulateOverallInstance(instance, victoryType, typeText)
    BASE_PopulateOverallInstance(instance, victoryType, typeText);

    -- 根据玩家数量动态调整高度（每行最多 9 个图标）
    local numIcons = PlayerManager.GetAliveMajorsCount() - 1;
    local numRows = math.floor(numIcons / 9);
    if numIcons > numRows * 9 then numRows = numRows + 1; end
    instance.ButtonBG:SetSizeY(SIZE_OVERALL_BG_HEIGHT + SIZE_OVERALL_INSTANCE * numRows);
end
```

---

## 六、关键 API 速查

### 旅游/文化数据

| API | 说明 |
|-----|------|
| `Players[pid]:GetCulture():GetCultureYield()` | 文化产出 |
| `Players[pid]:GetCulture():GetTouristsFrom(otherPID)` | 来自某玩家的游客数 |
| `Players[pid]:GetCulture():GetStaycationers()` | 国内游客数 |
| `playerCulture:GetTouristsFromTooltip(pid)` | 游客来源 tooltip 文本 |
| `playerCulture:IsDominantOver(pid)` | 是否对该文明文化支配 |
| `Players[pid]:GetStats():GetTourism()` | 总旅游业绩 |
| `Players[pid]:GetStats():GetNumBuildingsOfType(index)` | 拥有某建筑数量 |

### 外交/贸易

| API | 说明 |
|-----|------|
| `Players[pid]:GetDiplomacy():HasOpenBordersFrom(other)` | 是否收到开放边界 |
| `Players[pid]:GetDiplomacy():HasMet(other)` | 是否已遇见 |
| `city:GetTrade():HasTradeRouteFrom(pid)` | 城市是否有某玩家的贸易路线 |

### 历史数据

| API | 说明 |
|-----|------|
| `Game.GetHistoryManager():GetAllMomentsData()` | 所有历史时刻 |
| `Game.GetHistoryManager():GetMomentData(id)` | 单个时刻数据 |
| `Game.GetEras():GetCurrentEra()` | 当前时代 |

---

## 七、常见模式速查

| 模式 | 实现方式 |
|------|---------|
| 在原版行后追加字段 | `BASE_PopulateXxx(instance, data);` 后调用 `instance.NewField:SetText(...)` |
| 完全替换一行 | 不调 BASE 函数，全量自定义 |
| XML 实例扩展 | 同名 Instance 中追加新控件 |
| 采集阶段加数据 | `data = BASE_Gather();` 后遍历追加字段 |
| 解析 tooltip 文本 | `string.match` 提取数字和关键词 |
| DLC 兼容 | Base/XP2 分别入口，共用修改文件 |
| 语言无关判断 | 用 `ICON_` 前缀匹配而非硬编码文本 |

---

## 八、注意事项

1. **`include()` 路径是相对根目录的**，不带 `.lua` 后缀
2. **XML 同名 Instance 会自动覆盖原版**，Mod 的 XML 在加载顺序中靠后
3. **Base 和 XP2 的 Instance 定义可能不同**，XP2 版可能有额外的控件/尺寸，需要分文件覆盖
4. **通过 tooltip 文本推断游戏状态是不稳定的 hack**，如有 API 应优先使用 API
5. **`Players[pid]:GetCities():Members()` 遍历城市**是常用遍历方式

---

## XML 配合

### XML 文件

| 文件 | 路径 | 角色 |
|------|------|------|
| Base 版布局 | `Base/WorldRankings.xml` | Vanilla/R&F 排名界面 |
| XP2 版布局 | `XP2/WorldRankings.xml` | GS 排名界面（增加外交等） |
| 修改逻辑 | `WorldRankings_BWR.lua` | 共用增强逻辑（被 Base/XP2 入口 include） |

### 核心控件 ID 对照表

| 控件 ID | 控件类型 | 用途 |
|---------|---------|------|
| `SlideAnim` (Style="RundownAnimBG") | SlideAnim | 全局背景动画 |
| `TabHeader` | Container | 标签头容器 |
| `TabContainer` | Container | Tab 按钮挂载点 |
| `ExpandExtraTabs` / `ExtraTabStack` | Button / Stack | 溢出 Tab 折叠显示 |
| `CloseButton` | Button | 关闭按钮 |
| `OverallView` | Container | 总览页（含 `OverallViewScrollbar` / `OverallViewStack`） |
| `ScoreView` | Container | 分数排名页（含 `ScoreViewHeader` / `ScoreViewScrollbar` / `ScoreViewStack`） |
| `ScienceView` | Container | 科技排名页（含 `ScienceViewHeader` / `ScienceViewScrollbar` / `ScienceViewStack`） |
| `CultureView` | Container | 文化排名页（含 `TourismForOne` / `CultureViewScrollbar` / `CultureViewStack`） |
| `DominationView` | Container | 征服排名页 |
| `ReligionView` | Container | 宗教排名页 |
| `GenericView` | Container | 通用排名页（Mod 扩展） |
| `ScoreDetailsButton` / `ScoreDetailsCheck` | GridButton / CheckBox | 分数详情开关 |

### Instance 体系

| Instance Name | 用途 |
|--------------|------|
| `TabInstance` | 标签按钮（`Selection` 选中指示器） |
| `ExtraTabInstance` | 溢出标签按钮 |
| `GenericHeaderInstance` / `ScienceHeaderInstance` / `CultureHeaderInstance` | 各页顶部顾问头像+说明 |
| `CivilizationIconInstance` | 文明图标行（含 `LocalPlayer` 标记+`CivName`） |
| `OverallInstance` | 总览页胜率条目（Banner + VictoryIcon + PlayerStack） |
| `OverallPlayerInstance` | 总览页子玩家条目（CivIcon + Line1/Line2/HasCapital） |
| `ScoreTeamInstance` / `ScoreInstance` | 分数页队伍/玩家行（Score1~7 + ScoreX） |
| `ScienceTeamInstance` / `ScienceInstance` | 科技页三段进度条行 |
| `CultureTeamInstance` / `CultureInstance` | 文化页旅游详情行（DomesticTourists + VisitingUs + TourismBoost） |
| `DominationTeamInstance` / `DominationInstance` | 征服页首都捕获行 |
| `DominatedCapitalInstance` | 被征服首都图标 |
| `ReligionTeamInstance` / `ReligionInstance` | 宗教页皈依文明行 |
| `ConvertedReligionInstance` | 已皈依文明图标 |
| `GenericTeamInstance` / `GenericInstance` | 通用排名行 |
| `TeamTooltipInstance` | 队伍 Tooltip（LeaderIcon + LeaderName） |

### 关键子控件对照（OverallPlayerInstance 覆盖版）

| 子控件 | 原版 | BWR 扩展 |
|--------|------|---------|
| `CivIconFaded` | 文明图标 | 保留 |
| `LocalPlayer` | You 箭头 | 保留 |
| `HasCapital` | 无 | 新增：首都标记 `[ICON_Capital]` |
| `Line1` | 无 | 新增：第一行数据 |
| `Line2` | 无 | 新增：第二行数据 |

### 可复用模板：同名 Instance 覆盖原版

```xml
<Context>
  <Include File="CivilizationIcon" />
  <!-- 覆盖同名 Instance，在原基础上追加新控件 -->
  <Instance Name="OverallPlayerInstance">
    <Container ID="CivIconBackingFaded" Size="36,70">
      <!-- 保留原版结构 -->
      <Image Anchor="C,T" Size="36,36" Texture="CircleBacking36">
        <Image ID="CivIconFaded" Anchor="C,C" Size="36,36" Texture="CivSymbols36"/>
        <Container ID="LocalPlayer">
          <Image Offset="-4,-5" Size="44,45" Texture="Controls_CircleRimSmall"/>
          <Image Offset="0,-3" Size="35,10" Texture="Controls_YouArrowSmall"/>
        </Container>
        <MakeInstance Name="CivilizationIconBar36"/>
        <Image ID="TeamRibbon" Size="44,44" Anchor="C,B" Offset="0,-9" Texture="TeamRibbon44"/>
        <!-- 新增字段 -->
        <Label ID="HasCapital" Hidden="true" Offset="21,21" Style="FontNormalMedium14" String="[ICON_Capital]"/>
        <Label ID="Line1" Anchor="C,B" Offset="0,-21" String="Line1" Style="FontNormal14"/>
        <Label ID="Line2" Anchor="C,B" Offset="0,-36" String="Line2" Style="FontNormal14"/>
      </Image>
    </Container>
  </Instance>
</Context>
```
