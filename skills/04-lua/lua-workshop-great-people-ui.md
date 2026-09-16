# Great People UI 美化模式（来源：Real Great People）

从工坊 Mod `900089445`（Real Great People, by Infixo）提炼的伟人界面重做模式，包含三页标签式面板、过滤器、规划器、传记展开等完整 UI 技巧。

---

## 源文件

| 文件 | 角色 |
|------|------|
| `UI/greatpeoplepopup.xml` | 布局定义：PanelInstance、PastRecruitmentInstance、PlannerInstance 等 |
| `UI/greatpeoplepopup.lua` | 主逻辑：标签页、过滤器、传记展开、招募进度、规划器 |
| `UI/civilopediapage_greatperson.lua` | 文明百科伟人页面的图标查找回退 |
| `RealGreatPeople_Icons.xml` | 为每个伟人注册独立 160px 图标 Atlas |

---

## 模式一：三标签页弹出面板

### 1.1 结构概览

整个面板作为弹出窗口（Popup）而非 PartialScreen，通过 `QueuePopup` + `RenderAtCurrentParent=true` 层叠在游戏顶部。

```
PopupContainer (Anchor="C,C" Size="parent,768")
  ├── PeopleScroller     (Tab 1: 当前伟人列表)
  │   ├── PeopleStack    (StackGrowth="Right", 每页宽 212px)
  │   └── ScrollBar      (水平滚动)
  ├── RecruitedArea      (Tab 2: 已招募历史)
  │   ├── 过滤器 (ClassNamePull + CivLeaderPull)
  │   ├── RecruitedScroller / RecruitedStack
  │   └── Total 标签
  ├── PlannerArea        (Tab 3: 伟人规划器)
  │   ├── 五大 GP 类别按钮 + 当前类图标/名称
  │   └── PlannerScroller / PlannerStack (StackGrowth="Right")
  └── TabContainer       (标签按钮)
```

### 1.2 标签系统完整模版

```lua
-- 常量
local TAB_SIZE   = 170;
local TAB_PADDING = 10;

-- 标签按钮 Instance Manager
local m_tabButtonIM = InstanceManager:new("TabButtonInstance", "Button", Controls.TabContainer);
local m_tabs  :table;
local m_numTabs :number = 0;

-- 创建标签系统
m_tabs = CreateTabs( Controls.TabContainer, 42, 34, UI.GetColorValueFromHexLiteral(0xFF331D05) );

-- 添加标签（每一页一个标签 + 一个回调函数）
function AddTabInstance( buttonText:string, callbackFunc:ifunction )
    local kInstance = m_tabButtonIM:GetInstance();
    kInstance.Button:SetText(Locale.Lookup(buttonText));
    kInstance.Button:RegisterCallback( Mouse.eMouseEnter, function() UI.PlaySound("Main_Menu_Mouse_Over"); end);
    m_tabs.AddTab( kInstance.Button, callbackFunc );
    m_numTabs = m_numTabs + 1;
    return kInstance;
end

-- 使用时
m_pTab1 = AddTabInstance("LOC_GREAT_PEOPLE_TAB_GREAT_PEOPLE",     OnTab1Click);
m_pTab2 = AddTabInstance("LOC_GREAT_PEOPLE_TAB_PREVIOUSLY_RECRUITED", OnTab2Click);
m_pTab3 = AddTabInstance("LOC_GAMESUMMARY_OVERVIEW",              OnTab3Click);

-- 调整标签容器尺寸
function ResizeTabContainer()
    if m_numTabs > 0 then
        local desiredSize = (TAB_SIZE * m_numTabs) + (TAB_PADDING * (m_numTabs - 1));
        Controls.TabContainer:SetSizeX(desiredSize);
    end
end

-- 标签回调模版
function OnTab1Click( uiSelectedButton:table )
    ResetTabButtons();
    SetTabButtonsSelected(uiSelectedButton);
    -- 控制每个标签页特有的 UI 元素显隐
    Controls.ClassNamePull:SetHide( true );
    Controls.CivLeaderPull:SetHide( true );
    Refresh(RefreshTab1Content);   -- 动态切换 refresh 函数
end
```

### 1.3 动态 Refresh 函数切换

```lua
local m_RefreshFunc :ifunction = nil;

function Refresh( newRefreshFunc:ifunction )
    if newRefreshFunc ~= nil then
        m_RefreshFunc = newRefreshFunc;
    end
    if m_RefreshFunc ~= nil then
        m_RefreshFunc();
    end
end
```

---

## 模式二：过滤器下拉菜单

### 2.1 伟人类别过滤器

```lua
local m_filterClassID :number = -1;   -- -1 = 全部

function PopulateClassNamePull()
    Controls.ClassNamePull:ClearEntries();

    -- 添加 "全部" 选项
    local controlTable = {};
    Controls.ClassNamePull:BuildEntry( "InstanceOne", controlTable );
    local sAllText = Locale.Lookup("LOC_ROUTECHOOSER_FILTER_ALL").." "..Locale.Lookup("LOC_GREAT_PEOPLE_TAB_GREAT_PEOPLE");
    controlTable.Button:LocalizeAndSetText( sAllText );
    controlTable.Button:RegisterCallback( Mouse.eLClick, function() ClassNameClicked(-1, sAllText); end );

    -- 遍历数据库添加每个类别
    for classInfo in GameInfo.GreatPersonClasses() do
        local classID = classInfo.Index;
        local className = classInfo.IconString.." "..Locale.Lookup(classInfo.Name);
        local controlTable = {};
        Controls.ClassNamePull:BuildEntry( "InstanceOne", controlTable );
        controlTable.Button:LocalizeAndSetText( className );
        controlTable.Button:RegisterCallback( Mouse.eLClick, function() ClassNameClicked(classID, className); end );
    end

    Controls.ClassNamePull:GetButton():LocalizeAndSetText( sAllText );
    m_filterClassID = -1;
    Controls.ClassNamePull:CalculateInternals();
end

function ClassNameClicked(classID:number, className:string)
    if m_filterClassID == classID then return; end   -- 相同不刷新
    Controls.ClassNamePull:GetButton():LocalizeAndSetText( className );
    m_filterClassID = classID;
    Refresh();
end
```

### 2.2 文明/领袖过滤器

```lua
function PopulateCivLeaderPull()
    Controls.CivLeaderPull:ClearEntries();

    -- "全部" + "本地玩家" + 所有已遇见的文明
    local controlAll = {};
    Controls.CivLeaderPull:BuildEntry( "InstanceOne", controlAll );
    -- ...
    local players:table = Game.GetPlayers();
    for _, pPlayer in ipairs(players) do
        if pPlayer and pPlayer:IsAlive() and pPlayer:IsMajor() then
            if pPlayer:GetDiplomacy():HasMet(Game.GetLocalPlayer()) then
                local playerConfig = PlayerConfigurations[pPlayer:GetID()];
                local name = Locale.Lookup(GameInfo.Civilizations[playerConfig:GetCivilizationTypeID()].Name)
                    .." - "..Locale.Lookup(playerConfig:GetPlayerName());
                -- BuildEntry + RegisterCallback ...
            end
        end
    end
    Controls.CivLeaderPull:CalculateInternals();
end
```

**关键：自定义 PullDown 时用 `ClearEntries()` → 逐个 `BuildEntry()` → 最后 `CalculateInternals()`。**

---

## 模式三：可展开/收起区域（Biography）

### 3.1 Toggle 模式

```lua
local m_activeBiographyID :number = -1;   -- 同时只允许一个展开

function OnBiographyClick( individualID )
    -- 如果已有一个展开的且不是当前点击的，先关闭
    if m_activeBiographyID ~= -1 and individualID ~= m_activeBiographyID then
        OnBiographyClick( m_activeBiographyID );
    end

    local instance = m_kGreatPeople[individualID];
    local isShowingBiography = not instance.BiographyArea:IsHidden();

    -- 三区域互斥显示：Biography / MainInfo / RecruitInfo
    instance.BiographyArea:SetHide( isShowingBiography );
    instance.MainInfo:SetHide( not isShowingBiography );
    instance.FadedBackground:SetHide( isShowingBiography );
    instance.BiographyOpenButton:SetHide( not isShowingBiography );

    if isShowingBiography then
        m_activeBiographyID = -1;
    else
        m_activeBiographyID = individualID;
        -- 从 m_kData 中获取传记文本
        local kBiographyText = ...;
        instance.BiographyText:SetText( table.concat(kBiographyText, "[NEWLINE][NEWLINE]"));
        instance.BiographyScroll:CalculateSize();
    end
end
```

### 3.2 XML 布局关键点

传记区域用 `GridButton` 做"返回"按钮，套在 `ScrollPanel` 里：

```xml
<Container ID="BiographyArea" Offset="-2,105" Size="215,510">
    <ScrollPanel ID="BiographyScroll" Offset="8,10" Size="parent,parent-12" Vertical="1">
        <Label ID="BiographyText" Offset="15,0" WrapWidth="185" />
        <ScrollBar ... Style="ScrollVerticalBarAlt" />
    </ScrollPanel>
    <GridButton ID="BiographyBackButton" Anchor="C,B" AnchorSide="I,O"
        Offset="0,20" Size="parent-40,28" String="LOC_GREAT_PEOPLE_BACK" />
</Container>
```

---

## 模式四：伟人图标查找 + 回退机制

### 4.1 图标查找链条

先找伟人专属肖像，找不到则用通用类别肖像：

```lua
local portrait = "ICON_" .. individualData.GreatPersonIndividualType;
textureOffsetX, textureOffsetY, textureSheet = IconManager:FindIconAtlas(portrait, 160);
if textureSheet == nil then
    -- 回退到通类图标
    portrait = "ICON_GENERIC_" .. classData.GreatPersonClassType .. "_" .. individualData.Gender;
    portrait = portrait:gsub("_CLASS","_INDIVIDUAL");
end
local isValid = instance.Portrait:SetIcon(portrait);
```

### 4.2 图标 Atlas 注册（一个伟人一个 Atlas）

```xml
<IconTextureAtlases>
    <Row Name="ICON_ATLAS_GREAT_PERSON_INDIVIDUAL_ABDUS_SALAM" IconSize="160"
         IconsPerRow="1" IconsPerColumn="1" Filename="RGP_ABDUS_SALAM.dds" />
    <!-- ...每个伟人一个 Atlas... -->
</IconTextureAtlases>
<IconDefinitions>
    <Row Name="ICON_GREAT_PERSON_INDIVIDUAL_ABDUS_SALAM"
         Atlas="ICON_ATLAS_GREAT_PERSON_INDIVIDUAL_ABDUS_SALAM" Index="0" />
    <!-- ... -->
</IconDefinitions>
```

---

## 模式五：规划器（Era-Based Overview）

### 5.1 按时代分列展示全部伟人

```lua
local m_kOverviewClasses = {
    GREAT_PERSON_CLASS_GENERAL  = true,
    GREAT_PERSON_CLASS_ADMIRAL  = true,
    GREAT_PERSON_CLASS_ENGINEER = true,
    GREAT_PERSON_CLASS_MERCHANT = true,
    GREAT_PERSON_CLASS_SCIENTIST= true,
};

-- 第一遍：为每个时代创建一个 EraInstance
local kEraInstances = {};
for era in GameInfo.Eras() do
    if m_kOverviewEras[era.EraType] then
        local eraInstance = m_plannerIM:GetInstance();
        eraInstance.EraStack:DestroyAllChildren();
        eraInstance.EraName:SetText( Locale.ToUpper(Locale.Lookup(era.Name)) );
        eraInstance.CurrentEra:SetHide( era.Index ~= eCurrentEra );
        kEraInstances[ era.EraType ] = eraInstance;
    end
end

-- 第二遍：遍历所有伟人，归入对应时代
for gp in GameInfo.GreatPersonIndividuals() do
    if gp.GreatPersonClassType == m_plannerSelection then
        local instance = {};
        ContextPtr:BuildInstanceForControl("PlannerInstance", instance,
            kEraInstances[gp.EraType].EraStack);
        -- 设置头像、名称、效果、状态标记...
    end
end
```

### 5.2 状态标记

每个伟人有四个状态图标（右上角）：
- `Current` — 当前可招募（`GreatPersonIsBeingRecruited()`
- `Claimed` — 已被本玩家招募
- `NoAvail` — 已被他人招募
- `Priority` — 被玩家手动标记/选择

### 5.3 获取未来伟人效果文本

因为游戏只提供 current/past timeline，未来伟人的效果需要手动解析：

```lua
function GetEffectText(greatPerson :table)
    local greatPersonType = greatPerson.GreatPersonIndividualType;
    local active_ability = {};
    for row in GameInfo.GreatPersonIndividualActionModifiers() do
        if row.GreatPersonIndividualType == greatPersonType then
            local text = GetModifierText(row.ModifierId, "Summary");
            if text then table.insert(active_ability, text); end
        end
    end
    local passive_ability = {};
    for row in GameInfo.GreatPersonIndividualBirthModifiers() do
        if row.GreatPersonIndividualType == greatPersonType then
            local text = GetModifierText(row.ModifierId, "Summary");
            if text then table.insert(passive_ability, text); end
        end
    end
    -- 组装文本...
end
```

**必须 include: `include("GameEffectsText");` 才能使用 `GetModifierText()`。**

---

## 模式六：玩家配置持久化

```lua
-- 保存状态到玩家配置
function GreatPersonSetSelected(sGP:string, isSelected:boolean)
    local sData = ( isSelected and "1" or "0");
    PlayerConfigurations[Game.GetLocalPlayer()]:SetValue("RGP_"..sGP, sData);
end

-- 读取状态
function GreatPersonIsSelected(sGP:string)
    local sData = PlayerConfigurations[Game.GetLocalPlayer()]:GetValue("RGP_"..sGP);
    return sData == "1";
end
```

**注意：** `PlayerConfigurations:SetValue/GetValue` 只能存字符串，存储语义需自行转换。

---

## 模式七：热加载支持

```lua
local RELOAD_CACHE_ID = "GreatPeoplePopup";

-- OnInit: hotload 时读取缓存
function OnInit( isHotload:boolean )
    LateInitialize();
    if isHotload then
        LuaEvents.GameDebug_GetValues(RELOAD_CACHE_ID);
    end
end

-- OnShutdown: 保存当前状态到缓存
function OnShutdown()
    LuaEvents.GameDebug_AddValue(RELOAD_CACHE_ID, "isHidden", ContextPtr:IsHidden());
    LuaEvents.GameDebug_AddValue(RELOAD_CACHE_ID, "isPreviousTab",
        (m_tabs.selectedControl == Controls.ButtonPreviouslyRecruited));
end

-- OnGameDebugReturn: 恢复缓存的状态
function OnGameDebugReturn( context, contextTable )
    if context ~= RELOAD_CACHE_ID then return; end
    local isHidden = contextTable["isHidden"];
    if not isHidden then
        if contextTable["isPreviousTab"] then
            m_tabs.SelectTab( Controls.ButtonPreviouslyRecruited );
        else
            m_tabs.SelectTab( Controls.ButtonGreatPeople );
        end
    end
end
```

---

## 模式八：Open/Close 规范

```lua
function Open()
    if (Game.GetLocalPlayer() == -1) then return end

    PopulateClassNamePull();
    PopulateCivLeaderPull();

    if not UIManager:IsInPopupQueue(ContextPtr) then
        local kParameters = {};
        kParameters.RenderAtCurrentParent = true;
        kParameters.InputAtCurrentParent = true;
        kParameters.AlwaysVisibleInQueue = true;
        UIManager:QueuePopup(ContextPtr, PopupPriority.Low, kParameters);
        UI.PlaySound("UI_Screen_Open");
    end

    Refresh();

    -- 调整 Vignette 高度以兼容 TopPanel
    if not RefreshYields() then
        Controls.Vignette:SetSizeY(m_TopPanelConsideredHeight);
    end

    Controls.ScreenAnimIn:SetToBeginning();
    Controls.ScreenAnimIn:Play();
end

function Close()
    if not ContextPtr:IsHidden() then
        UI.PlaySound("UI_Screen_Close");
    end
    if UIManager:DequeuePopup(ContextPtr) then
        LuaEvents.GreatPeople_CloseGreatPeople();
    end
end
```

---

## 事件监听速查

| 事件 | 用途 |
|------|------|
| `Events.LocalPlayerChanged` | 切换玩家时刷新 |
| `Events.LocalPlayerTurnBegin` | 每回合开始刷新（面板打开时） |
| `Events.LocalPlayerTurnEnd` | 热座模式自动关闭 |
| `Events.GreatPeoplePointsChanged` | 任何玩家伟人点数变化时刷新 |
| `Events.UnitGreatPersonActivated` | 伟人激活时显示世界文字 |
| `LuaEvents.LaunchBar_OpenGreatPeoplePopup` | LaunchBar 按钮打开 |
| `LuaEvents.NotificationPanel_OpenGreatPeoplePopup` | 通知面板打开 |
| `LuaEvents.LaunchBar_CloseGreatPeoplePopup` | 外部关闭请求 |

---

## 关键 include 清单

```lua
include("InstanceManager");
include("TabSupport");
include("SupportFunctions");
include("Civ6Common");          -- DifferentiateCiv
include("ModalScreen_PlayerYieldsHelper");
include("GameCapabilities");
include("GameEffectsText");      -- GetModifierText
```

---

## XML 配合

### XML 文件

| 文件 | 路径 |
|------|------|
| 主面板布局 | `UI/greatpeoplepopup.xml` |
| 伟人图标注册 | `RealGreatPeople_Icons.xml` |

### 核心控件 ID 对照表

| 控件 ID | 控件类型 | 用途 |
|---------|---------|------|
| `PopupContainer` | Container | 面板根容器，`Anchor="C,C" Size="parent,768"` |
| `TabContainer` | Container | 标签按钮容器（TabSupport 挂载点） |
| `PeopleScroller` | ScrollPanel | Tab1 伟人横向滚动区，`Vertical="0"` |
| `PeopleStack` | Stack | 伟人卡片水平堆叠，`StackGrowth="Right"` |
| `RecruitedArea` | Box | Tab2 已招募历史背景 |
| `RecruitedScroller` | ScrollPanel | 已招募列表滚动区 |
| `RecruitedStack` | Stack | 已招募行堆叠，`StackGrowth="Down"` |
| `ClassNamePull` | PullDown | 伟人类别下拉过滤器 |
| `CivLeaderPull` | PullDown | 文明/领袖下拉过滤器 |
| `PlannerArea` | Box | Tab3 规划器背景 |
| `PlannerScroller` | ScrollPanel | 规划器横向滚动区 |
| `PlannerStack` | Stack | 时代列水平堆叠 |
| `ModalFrame` | Container | 模态框容器，`Style="ModalScreenWide"` |
| `Vignette` | Container | 暗角遮罩，`Style="FullScreenVignetteConsumer"` |

### Instance 对照表

| Instance Name | 对应模式 | 用途 |
|--------------|---------|------|
| `PanelInstance` | 模式三/四 | 单个伟人卡片（肖像+效果+招募进度） |
| `PastRecruitmentInstance` | 模式一 Tab2 | 已招募伟人行 |
| `PastEffectInstance` | 模式一 Tab2 | 已招募伟人的效果图标 |
| `EffectInstance` | 模式三 | 当前伟人效果条目 |
| `RecruitInstance` | 模式三 | 招募进度条（各文明竞争） |
| `TabButtonInstance` | 模式一 | 标签按钮 |
| `EraInstance` | 模式五 | 规划器中一个时代列 |
| `PlannerInstance` | 模式五 | 规划器中单个伟人条目 |

### 可复用模板：三页标签面板框架

```xml
<Context>
  <Container ID="Vignette" Style="FullScreenVignetteConsumer" />
  <Container ID="PopupContainer" Anchor="C,C" Size="parent,768">
    <!-- 标签容器 -->
    <Container Anchor="C,T" Offset="0,30" Size="400,61">
      <Image Anchor="C,C" Size="439,27" Texture="Controls_TabLedge2_Fill" StretchMode="Tile" />
      <Grid Anchor="C,T" Size="580,61" Texture="Controls_TabLedge2"
            SliceCorner="194,18" SliceSize="52,26" SliceTextureSize="438,61">
        <Container ID="TabContainer" Anchor="C,T" Offset="0,13" Size="0,34"/>
      </Grid>
    </Container>
    <Container ID="ModalFrame" Style="ModalScreenWide" />
  </Container>
</Context>
```
