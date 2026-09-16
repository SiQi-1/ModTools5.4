# lua-workshop-loading-screen — 加载界面替换模式

从工坊 Mod Better Loading Screen (1579019534) 提炼。完全替换游戏默认加载界面，展示领袖/Civ 特质详情、自定义布局和纹理。

---

## 快速索引

| 技术点 | 说明 |
|--------|------|
| **替换加载界面** | 同名 XML/Lua 文件，游戏自动加载 Mod 版本 |
| **生命周期** | Show → LoadScreenContentReady → LoadGameViewStateDone |
| **自适应布局** | `UIManager:GetScreenSizeVal()` + 动态偏移计算 |
| **特质展示** | `GetLeaderUniqueTraits()` + `GetCivilizationUniqueTraits()` + InstanceManager |
| **Dawn of Man 语音** | `UI.SetSoundSwitchValue()` + `UI.PlaySound("Play_DawnOfMan_Speech")` |
| **Input 处理** | `InputContext.Loading` / `InputContext.Ready` + ESC/快捷键监听 |

---

## 一、替换策略：同名文件覆盖

游戏加载 `.modinfo` 中 `FrontEndActions` 和 `InGameActions` 的 ImportFiles。当 Mod 提供同名 UI 文件（`loadscreen.lua` / `loadscreen.xml`）时，Mod 的版本自动替换原版。无需额外 import 配置。

**关键前提：文件必须放在 `UI/` 目录下，且文件名与原版一致。**

```
Mod/
├── UI/
│   ├── loadscreen.lua     -- 替换 Base/Assets/UI/loadscreen.lua
│   └── loadscreen.xml     -- 替换 Base/Assets/UI/loadscreen.xml
└── Icons/
    └── FontIconsRMI.xml   -- 自定义图标（可选）
```

---

## 二、生命周期事件流

```
游戏启动 / 加载存档
    │
    ▼
OnShow()
    ├─ m_isLoadComplete = false
    ├─ 隐藏 Portrait, Banner, BackgroundImage
    ├─ 清除按钮回调（防止误操作）
    └─ LuaEvents.Lower_State_Transition("LoadScreen")
         │
         ▼ 等待游戏数据就绪
OnLoadScreenContentReady()
    ├─ 获取本地玩家（兼容 Hotseat）
    ├─ 设置背景图、肖像、文明名、领袖名
    ├─ 生成特质列表（UA + UU + UB/UD/UI）
    ├─ 播放 Dawn of Man 语音
    └─ 自适应布局计算
         │
         ▼ 等待加载完成
OnLoadGameViewStateDone()
    ├─ m_isLoadComplete = true
    ├─ 显示 "开始游戏" 按钮（单人模式）
    └─ 或自动跳过（重连 / 多人 / WorldBuilder）
```

---

## 三、Initialize 注册

```lua
function Initialize()
    -- 设置输入上下文（loading 阶段不响应游戏操作）
    Input.SetActiveContext(InputContext.Loading);

    ContextPtr:SetInitHandler(OnInit);
    ContextPtr:SetShowHandler(OnShow);
    ContextPtr:SetHideHandler(OnHide);

    Events.LoadScreenContentReady.Add(OnLoadScreenContentReady);
    Events.LoadGameViewStateDone.Add(OnLoadGameViewStateDone);
    Events.BeforeMultiplayerInviteProcessing.Add(
        OnBeforeMultiplayerInviteProcessing);

    UI.SetExitOnClose(true);
end
Initialize();
```

---

## 四、OnShow / OnHide

```lua
-- ===========================================================================
-- UI Event: 加载界面显示时触发
-- ===========================================================================
function OnShow()
    m_isLoadComplete = false;
    m_isResyncLoad  = UI.IsResyncLoadInProgress();

    UIManager:SetUICursor(1);              -- 显示光标
    Controls.FadeAnim:SetToBeginning();
    Controls.ActivateButton:SetHide(true);  -- 隐藏"开始"按钮
    Controls.LoadingContainer:SetHide(false);-- 显示"请等待"文字

    -- 数据尚未就绪，先隐藏所有画像元素
    Controls.BackgroundImage:SetHide(true);
    Controls.Banner:SetHide(true);
    Controls.Portrait:SetHide(true);

    ClearButtonCallbacks();

    LuaEvents.Lower_State_Transition("LoadScreen");
end

-- ===========================================================================
-- UI Event: 加载界面隐藏时触发
-- ===========================================================================
function OnHide()
    UIManager:SetUICursor(0);              -- 隐藏光标（进入游戏）
end
```

---

## 五、OnLoadScreenContentReady — 内容构建

### 5.1 获取本地玩家（兼容 Hotseat + 多人）

```lua
function OnLoadScreenContentReady()
    if GameConfiguration:IsWorldBuilderEditor() then
        return;    -- WorldBuilder 不需要加载界面
    end

    -- 优先 Network，因为 Game.GetLocalPlayer() 可能未就绪
    local localPlayer = Network.GetLocalPlayerID();

    -- Hotseat：找到第一个被占用的 Slot 的人类玩家
    if GameConfiguration.IsHotseat() then
        local maxPlayers = MapConfiguration.GetMaxMajorPlayers();
        for playerID = 0, maxPlayers - 1, 1 do
            local pPlayerConfig = PlayerConfigurations[playerID];
            local slotStatus = pPlayerConfig:GetSlotStatus();
            if slotStatus == SlotStatus.SS_TAKEN then
                localPlayer = playerID;
                break;
            end
        end
    end

    -- 获取玩家颜色
    local primaryColor, secondaryColor = UI.GetPlayerColors(localPlayer);
end
```

### 5.2 加载背景和肖像

```lua
-- 优先使用 LoadingInfo 表（MOD 可定义的自定义加载信息）
local playerConfig = PlayerConfigurations[localPlayer];
local leaderType = playerConfig:GetLeaderTypeName();
local loadingInfo = GameInfo.LoadingInfo[leaderType];

-- 背景图
local backgroundTexture;
if loadingInfo and loadingInfo.BackgroundImage then
    backgroundTexture = loadingInfo.BackgroundImage;
else
    backgroundTexture = leaderType .. "_BACKGROUND";
end
Controls.BackgroundImage:SetTexture(backgroundTexture);

-- 肖像
local portraitName;
if loadingInfo and loadingInfo.ForegroundImage then
    portraitName = loadingInfo.ForegroundImage;
else
    portraitName = leaderType .. "_NEUTRAL";
end
Controls.Portrait:SetTexture(portraitName);

-- 文明名
Controls.CivName:SetText(
    Locale.ToUpper(Locale.Lookup(playerConfig:GetCivilizationDescription())));
```

### 5.3 领袖名 + 领袖/时代描述

```lua
local kLeader = GameInfo.Leaders[leaderType];
if kLeader ~= nil then
    local leaderName = Locale.ToUpper(Locale.Lookup(kLeader.Name));
    Controls.LeaderName:SetText(leaderName);

    -- 领袖描述（LOC_LOADING_INFO_<LeaderType>）
    local details = "LOC_LOADING_INFO_" .. leaderType;
    if Locale.HasTextKey(details) then
        leaderInfoText = details;
    end
end

-- 优先 LoadingInfo 表中定义的文本
if loadingInfo then
    if loadingInfo.EraText   then eraInfoText   = loadingInfo.EraText;   end
    if loadingInfo.LeaderText then leaderInfoText = loadingInfo.LeaderText; end
end

-- 设置文本（LocalizeAndSetText 会在设置前先本地化）
if eraInfoText then
    Controls.EraInfo:LocalizeAndSetText(eraInfoText);
    Controls.EraInfo:SetHide(false);
end
if leaderInfoText then
    Controls.LeaderInfo:LocalizeAndSetText(leaderInfoText);
    Controls.LeaderInfo:SetHide(false);
end
```

### 5.4 Civ Logo

```lua
local civType = playerConfig:GetCivilizationTypeName();
local iconName = "ICON_" .. civType;

Controls.LogoContainer:SetColor(primaryColor);
Controls.Logo:SetColor(secondaryColor);
Controls.Logo:SetIcon(iconName);
Controls.Logo:SetHide(false);
```

### 5.5 自适应肖像定位

```lua
-- 动态计算肖像容器宽度，使其在 Banner 左侧占据屏幕一半（减去 ribbon 偏移）
local ribbonRunsPastCenter = 80;
local screenWidth, screenHeight = UIManager:GetScreenSizeVal();
local backgroundWidth, backgroundHeight = Controls.BackgroundImage:GetSizeVal();
local minWidth = math.min(backgroundWidth, screenWidth);
Controls.PortraitContainer:SetSizeX((minWidth * 0.5) - ribbonRunsPastCenter);
```

---

## 六、Dawn of Man 语音播放

```lua
local bPlayDOM = true;
if loadingInfo then
    bPlayDOM = loadingInfo.PlayDawnOfManAudio;    -- 可能为 false
end
if m_isResyncLoad then
    bPlayDOM = false;    -- 重连时跳过
end

if bPlayDOM then
    local dawnOfManLeaderID = leaderID;
    local dawnOfManEraHash = startEra.Hash;

    -- 允许 LoadingInfo 覆盖语音用的 Leader/Era
    if loadingInfo and loadingInfo.DawnOfManLeaderId then
        dawnOfManLeaderID = loadingInfo.DawnOfManLeaderId;
    end
    if loadingInfo and loadingInfo.DawnOfManEraId then
        dawnOfManEraHash = DB.MakeHash(loadingInfo.DawnOfManEraId);
    end

    -- 设置音频开关值（决定语音内容/语气）
    UI.SetSoundSwitchValue("Leader_Screen_Civilization",
        UI.GetCivilizationSoundSwitchValueByLeader(dawnOfManLeaderID));
    UI.SetSoundSwitchValue("Civilization",
        UI.GetCivilizationSoundSwitchValueByLeader(dawnOfManLeaderID));
    UI.SetSoundSwitchValue("Era_DawnOfMan",
        UI.GetEraSoundSwitchValue(dawnOfManEraHash));

    UI.PlaySound("Play_DawnOfMan_Speech");
end
```

---

## 七、特质列表（UA + UU + UB/UD/UI）

### 7.1 收集特质

```lua
-- 从领袖和文明两个维度收集独特特质
local uniqueAbilities, uniqueUnits, uniqueBuildings;
uniqueAbilities, uniqueUnits, uniqueBuildings =
    GetLeaderUniqueTraits(leaderType, true);

local CivUniqueAbilities, CivUniqueUnits, CivUniqueBuildings =
    GetCivilizationUniqueTraits(civType, true);

-- 合并表格
for i, v in ipairs(CivUniqueAbilities)  do table.insert(uniqueAbilities, v) end
for i, v in ipairs(CivUniqueUnits)      do table.insert(uniqueUnits, v)     end
for i, v in ipairs(CivUniqueBuildings)  do table.insert(uniqueBuildings, v) end
```

### 7.2 渲染特质条目（UA）

```lua
for _, item in ipairs(uniqueAbilities) do
    local instance = {};
    ContextPtr:BuildInstanceForControl("IconInfoInstance", instance,
                                       Controls.FeaturesStack);

    -- 图标用 Civ Logo
    instance.Icon:SetIcon("ICON_" .. civType);
    instance.TextStack:SetOffsetX(SIZE_BUILDING_ICON + 4);

    -- 标题
    if item.Name ~= nil and item.Name ~= "NONE" then
        local headerText = Locale.ToUpper(Locale.Lookup(item.Name));
        instance.Header:SetText(headerText);
    else
        instance.Header:SetShow(false);
    end

    -- 描述
    if item.Description ~= nil and item.Description ~= "NONE" then
        instance.Description:SetText(Locale.Lookup(item.Description));
        instance.Icon:SetToolTipString(Locale.Lookup(item.Description));
    else
        instance.Description:SetShow(false);
    end
end
```

### 7.3 渲染特质条目（UU — 含解锁科技/市政）

```lua
for _, item in ipairs(uniqueUnits) do
    local instance = {};
    ContextPtr:BuildInstanceForControl("IconInfoInstance", instance,
                                       Controls.FeaturesStack);

    instance.Icon:SetIcon("ICON_" .. item.Type);
    instance.TextStack:SetOffsetX(SIZE_BUILDING_ICON + 4);
    instance.Header:SetText(Locale.ToUpper(Locale.Lookup(item.Name)));

    -- 拼接解锁条件
    local itemInfo = GameInfo.Units[item.Type];
    local sDescription = string.format("[ICON_GoingTo] %s",
        Locale.Lookup("LOC_TECH_KEY_AVAILABLE"));
    if itemInfo.PrereqCivic ~= nil then
        sDescription = GetUnlockCivicDesc(itemInfo.PrereqCivic);
    end
    if itemInfo.PrereqTech ~= nil then
        sDescription = GetUnlockTechDesc(itemInfo.PrereqTech);
    end
    sDescription = sDescription .. "[NEWLINE]"
                   .. Locale.Lookup(item.Description);
    -- 去重连续的 [NEWLINE]
    sDescription = string.gsub(sDescription,
                               "%[NEWLINE%]%[NEWLINE%]", "[NEWLINE]");
    instance.Description:SetText(sDescription);
    instance.Icon:SetToolTipString(sDescription);
end
```

### 7.4 渲染特质条目（UB/UD/UI — 含解锁条件）

```lua
for _, item in ipairs(uniqueBuildings) do
    -- item.Type 可能是 Building / District / Improvement 类型
    local instance = {};
    ContextPtr:BuildInstanceForControl("IconInfoInstance", instance,
                                       Controls.FeaturesStack);
    instance.Icon:SetSizeVal(38, 38);
    instance.Icon:SetIcon("ICON_" .. item.Type);
    instance.TextStack:SetOffsetX(SIZE_BUILDING_ICON + 4);
    instance.Header:SetText(Locale.ToUpper(Locale.Lookup(item.Name)));

    -- 查找解锁条件（三个表逐个尝试）
    local itemInfo = GameInfo.Buildings[item.Type];
    if itemInfo == nil then itemInfo = GameInfo.Districts[item.Type]; end
    if itemInfo == nil then itemInfo = GameInfo.Improvements[item.Type]; end

    local sDescription = string.format("[ICON_GoingTo] %s",
        Locale.Lookup("LOC_TECH_KEY_AVAILABLE"));
    if itemInfo.PrereqCivic ~= nil then
        sDescription = GetUnlockCivicDesc(itemInfo.PrereqCivic);
    end
    if itemInfo.PrereqTech ~= nil then
        sDescription = GetUnlockTechDesc(itemInfo.PrereqTech);
    end
    sDescription = sDescription .. "[NEWLINE]"
                   .. Locale.Lookup(item.Description);
    sDescription = string.gsub(sDescription,
                               "%[NEWLINE%]%[NEWLINE%]", "[NEWLINE]");
    instance.Description:SetText(sDescription);
    instance.Icon:SetToolTipString(sDescription);
end
```

### 7.5 解锁条件辅助函数

```lua
function GetUnlockCivicDesc(sCivic)
    local civicInfo = GameInfo.Civics[sCivic];
    local eraInfo = GameInfo.Eras[civicInfo.EraType];
    return string.format("[ICON_GoingToPink] %s (%s)",
        Locale.Lookup(civicInfo.Name), Locale.Lookup(eraInfo.Name));
end

function GetUnlockTechDesc(sTech)
    local techInfo = GameInfo.Technologies[sTech];
    local eraInfo = GameInfo.Eras[techInfo.EraType];
    return string.format("[ICON_GoingToBlue] %s (%s)",
        Locale.Lookup(techInfo.Name), Locale.Lookup(eraInfo.Name));
end
```

---

## 八、OnLoadGameViewStateDone — 激活"开始"按钮

```lua
function OnLoadGameViewStateDone()
    m_isLoadComplete = true;
    UIManager:SetUICursor(0);      -- 隐藏光标

    -- 重连 / 多人 / WorldBuilder → 自动跳过
    if m_isResyncLoad
       or GameConfiguration.IsAnyMultiplayer()
       or GameConfiguration:IsWorldBuilderEditor() then
        OnActivateButtonClicked();
    else
        -- 单人模式：显示 "开始游戏" 按钮
        local strGameButtonName;
        if GameConfiguration.IsSavedGame() then
            strGameButtonName = Locale.Lookup("LOC_CONTINUE_GAME");
        else
            strGameButtonName = Locale.Lookup("LOC_BEGIN_GAME");
        end
        Controls.StartLabelButton:SetText(strGameButtonName);
        Controls.ActivateButton:SetHide(false);      -- 显示按钮
        Controls.LoadingContainer:SetHide(true);      -- 隐藏 "请等待"
        Controls.FadeAnim:SetToBeginning();
        Controls.FadeAnim:Play();                     -- 淡入动画
        UI.PlaySound("Game_Begin_Button_Appear");

        Input.SetActiveContext(InputContext.Ready);

        -- 自动化测试模式下自动继续
        if Automation.IsAutoStartEnabled() then
            OnActivateButtonClicked();
        end
    end

    RegisterButtonCallbacks();
    ContextPtr:SetInputHandler(OnInput);
    Events.InputActionTriggered.Add(OnInputActionTriggered);
end
```

---

## 九、OnActivateButtonClicked — 进入游戏

```lua
function OnActivateButtonClicked()
    -- 释放大纹理内存
    Controls.BackgroundImage:UnloadTexture();
    Controls.Portrait:UnloadTexture();

    -- 关闭加载界面声音
    Events.LoadScreenClose();
    UI.PlaySound("STOP_SPEECH_DAWNOFMAN");
    UI.StartStopMenuMusic(false);
    UI.PlaySound("Game_Begin_Button_Click");
    UI.PlaySound("Set_View_3D");

    UIManager:DequeuePopup(ContextPtr);
    Input.SetActiveContext(InputContext.World);

    -- 恢复默认 Lens
    if UILens.IsPlayerLensSetToActive() then
        UILens.SetActive("Default");
    end

    UI.SetExitOnClose(false);

    -- PlayByCloud 模式：触发云通知检查
    if GameConfiguration.IsPlayByCloud() then
        local kandoConnected = FiraxisLive.IsFiraxisLiveLoggedIn();
        if kandoConnected then
            FiraxisLive.CheckForCloudNotifications();
        end
    end
end
```

---

## 十、Input 处理（ESC + 快捷键）

```lua
-- ESC 键处理
function OnInput(uiMsg, wParam, lParam)
    if uiMsg == KeyEvents.KeyUp then
        if wParam == Keys.VK_ESCAPE then
            if m_isLoadComplete then
                OnActivateButtonClicked();
                return true;
            end
        end
    end
    return false;    -- 不消费其他输入
end

-- 快捷键（回车 / 空格 等）
local m_actionHotkeyStartGame    = Input.GetActionId("StartGame");
local m_actionHotkeyStartGameAlt = Input.GetActionId("StartGameAlt");

function OnInputActionTriggered(actionId)
    if actionId == m_actionHotkeyStartGame
       or actionId == m_actionHotkeyStartGameAlt then
        if m_isLoadComplete then
            OnActivateButtonClicked();
        end
    end
end
```

---

## 十一、重新加载处理（isReload）

```lua
function OnInit(isReload)
    if isReload then
        OnShow();
        OnLoadScreenContentReady();
        OnLoadGameViewStateDone();
    end
end
```

---

## 十二、XML 布局结构

```xml
<Context Name="LoadScreen">
    <Box ID="Background" Color="0,0,0,255" Anchor="C,C"
         Size="parent,parent" ConsumeMouse="1">

        <!-- 保底文字（背景图加载失败时显示） -->
        <TextButton ID="FallbackMessage" Anchor="C,C"
                    Align="center" Style="FontFlair20"
                    Color="200,200,200,255"
                    String="{LOC_LOADING_PLEASE_WAIT:upper}"/>

        <Image ID="BackgroundImage" Anchor="C,C" StretchMode="Auto">
            <Group Size="parent,parent" Clip="1">
                <!-- 左侧肖像 -->
                <Container Anchor="C,T" Size="1,parent">
                    <Container ID="PortraitContainer" Anchor="L,T"
                               Offset="80,0">
                        <Image ID="Portrait" Anchor="C,T"
                               StretchMode="Auto" />
                    </Container>
                </Container>

                <!-- 中央 Banner -->
                <Image ID="Banner" Anchor="C,C" Offset="-220,6"
                       Size="600,parent-80"
                       Texture="Controls_BannerWideTint" Alpha="0.8">
                    <!-- Logo + 文字栈 -->
                    <Container Anchor="C,C" Offset="45,0"
                               Size="parent,parent-100">
                        <Image ID="LogoContainer" Anchor="C,C"
                               Size="256,256"
                               Texture="CircleBacking256" Alpha="0.4">
                            <Image ID="Logo" Anchor="C,C"
                                   Size="200,200"
                                   Texture="CivSymbols200" Alpha="0.5" />
                        </Image>
                        <Stack ID="MainStack" Anchor="C,T"
                               StackGrowth="Down" StackPadding="10">
                            <Label ID="CivName" Style="FontFlair20" />
                            <Label ID="EraInfo" WrapWidth="500"
                                   Style="DawnText" />
                            <Label ID="LeaderName" Style="FontFlair20" />
                            <Label ID="LeaderInfo" WrapWidth="500"
                                   Style="DawnText" />

                            <!-- 特质滚动区 -->
                            <ScrollPanel ID="FeaturesScrollPanel">
                                <Stack ID="FeaturesStack"
                                       StackGrowth="Down" Padding="15"/>
                                <ScrollBar Style="ScrollVerticalBarHighContrast" />
                            </ScrollPanel>
                        </Stack>
                    </Container>

                    <!-- "请等待" 文字（加载中显示） -->
                    <Container ID="LoadingContainer" Anchor="C,B"
                               Offset="0,50" Size="parent,parent">
                        <Label Anchor="C,B"
                               String="{LOC_LOADING_PLEASE_WAIT:upper}"
                               Color="200,200,200,255"/>
                    </Container>

                    <!-- "开始游戏" 按钮（淡入动画） -->
                    <AlphaAnim ID="FadeAnim" Anchor="C,C"
                               AlphaBegin="0" AlphaEnd="1"
                               Cycle="Once" Speed=".5"
                               Stopped="0" Pause="1" Function="Root">
                        <Container Anchor="C,B" Offset="0,50"
                                   Size="300,130">
                            <TextButton ID="StartLabelButton"
                                        Anchor="C,C" Offset="0,8"
                                        Style="FontFlair20"
                                        Color="20,20,20,255" />
                            <Button ID="ActivateButton"
                                    Anchor="C,C"
                                    Size="80,80"
                                    Texture="Shell_BeginButton"
                                    StateOffsetIncrement="0,80"/>
                        </Container>
                    </AlphaAnim>
                </Image>
            </Group>
        </Image>
    </Box>

    <!-- Instance: 带图标+文字的特质条目 -->
    <Instance Name="IconInfoInstance">
        <Container ID="Top" Size="230,auto">
            <Image ID="Icon" Size="38,38" Offset="-6,-5" />
            <Stack ID="TextStack" Offset="36,0"
                   StackGrowth="Bottom" StackPadding="4">
                <Label ID="Header" WrapWidth="460"
                       Style="FontFlair16" />
                <Label ID="Description" WrapWidth="460"
                       Style="DawnText" />
            </Stack>
        </Container>
    </Instance>
</Context>
```

---

## 十三、关键要点速查

### 13.1 核心 API

| API | 用途 |
|-----|------|
| `Network.GetLocalPlayerID()` | 获取本地玩家 ID（比 `Game.GetLocalPlayer()` 更早就绪） |
| `UI.GetPlayerColors(playerID)` | 获取玩家主色/辅色 |
| `UI.SetSoundSwitchValue(key, value)` | 设置 Dawn of Man 语音参数 |
| `UI.PlaySound("Play_DawnOfMan_Speech")` | 播放 Dawn of Man 语音 |
| `UI.PlaySound("STOP_SPEECH_DAWNOFMAN")` | 停止 Dawn of Man 语音 |
| `UI.SetExitOnClose(bool)` | 关闭加载界面后是否退出游戏 |
| `UIManager:GetScreenSizeVal()` | 获取屏幕宽高（自适应布局） |
| `Input.SetActiveContext(InputContext.Loading)` | 设置加载阶段输入上下文 |
| `Input.SetActiveContext(InputContext.Ready)` | 设置就绪阶段输入上下文 |
| `Input.SetActiveContext(InputContext.World)` | 进入游戏世界输入上下文 |
| `Automation.IsAutoStartEnabled()` | 检测自动化测试模式 |
| `GameConfiguration.IsPlayByCloud()` | 检测 PBC 模式 |

### 13.2 纹理查找优先级

```
GameInfo.LoadingInfo[leaderType].BackgroundImage
    → leaderType .. "_BACKGROUND"
GameInfo.LoadingInfo[leaderType].ForegroundImage
    → leaderType .. "_NEUTRAL"
GameInfo.LoadingInfo[leaderType].EraText
    → GameInfo.Eras[era].Description
GameInfo.LoadingInfo[leaderType].LeaderText
    → "LOC_LOADING_INFO_" .. leaderType
```

### 13.3 按钮回调注册/清除

```lua
function RegisterButtonCallbacks()
    Controls.ActivateButton:RegisterCallback(Mouse.eMouseEnter, function()
        UI.PlaySound("Main_Menu_Mouse_Over");
    end);
    Controls.ActivateButton:RegisterCallback(Mouse.eLClick,
        OnActivateButtonClicked);
    Controls.StartLabelButton:RegisterCallback(Mouse.eLClick,
        OnActivateButtonClicked);
end

function ClearButtonCallbacks()
    Controls.ActivateButton:ClearCallback(Mouse.eLClick);
    Controls.ActivateButton:ClearCallback(Mouse.eMouseEnter);
    Controls.StartLabelButton:ClearCallback(Mouse.eLClick);
end
```

### 13.4 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 背景/肖像不显示 | `GameInfo.LoadingInfo` 中无此领袖条目 | 确保 Leader 有对应纹理，或使用默认格式 `LEADER_X_BACKGROUND` |
| Dawn of Man 无声音 | SoundSwitch 值未正确设置 | 检查 `DawnOfManLeaderId` / `DawnOfManEraId` 字段 |
| 新游戏时 ListenHistory 缺失 | `OnLoadComplete` 只对存档触发 | `OnLoadScreenClose` 在新游戏和存档都触发，在此绑定事件 |
| 特质列表不完整 | 某些特质可能来自 ThirdParty 表 | 检查数据库所有三个 UniqueTraits 源表 |
| 按钮始终不显示 | `LoadGameViewStateDone` 未触发或自动化跳过 | 检查 `Automation.IsAutoStartEnabled()` |

---

## XML 配合

### XML 文件

| 文件 | 路径 | 角色 |
|------|------|------|
| 加载界面布局 | `UI/loadscreen.xml` | 完全替换原版加载界面 |

**同名文件替换**：`UI/loadscreen.xml` 放在 Mod 中即可自动替换 `Base/Assets/UI/loadscreen.xml`。

### 核心控件 ID 对照表

| 控件 ID | 控件类型 | 用途 |
|---------|---------|------|
| `Background` | Box | 全屏黑底容器，`Color="0,0,0,255"` |
| `FallbackMessage` | TextButton | 保底文字（背景图加载失败时显示） |
| `BackgroundImage` | Image | 领袖背景图，`StretchMode="Auto"` |
| `PortraitContainer` | Container | 左侧肖像区 |
| `Portrait` | Image | 领袖肖像/剪影 |
| `Banner` | Image | 中央横幅，`Texture="Controls_BannerWideTint" Alpha="0.8"` |
| `BannerShadow` | Grid | 横幅阴影 |
| `BannerBarLeft` / `BannerBarRight` | Image | 横幅左右竖条 |
| `LogoContainer` | Image | 文明 logo 圆形背景（256px） |
| `Logo` | Image | 文明符号（200px） |
| `MainStack` | Stack | 中央文字栈（`CivName` → `EraInfo` → `LeaderName` → `LeaderInfo` → `FeaturesScrollPanel`） |
| `CivName` | Label | 文明名称 |
| `EraInfo` | Label | 时代/领袖描述（上段） |
| `LeaderName` | Label | 领袖名称 |
| `LeaderInfo` | Label | 领袖描述（下段） |
| `FeaturesScrollPanel` | ScrollPanel | 特质列表滚动区 |
| `FeaturesStack` | Stack | 特质条目堆叠 |
| `LoadingContainer` | Container | "请等待"文字容器（加载中显示） |
| `FadeAnim` | AlphaAnim | "开始游戏"按钮淡入动画 |
| `ActivateButton` | Button | 开始游戏按钮（圆形 80x80） |
| `StartLabelButton` | TextButton | 开始游戏文字按钮 |

### Instance 对照表

| Instance Name | 用途 | 子控件 |
|--------------|------|--------|
| `TextInfoInstance` | 纯文本特质（Header + Description Stack） | `Header`, `Description` |
| `IconInfoInstance` | 带图标特质（Icon + TextStack） | `Icon` + `TextStack` → `Header`, `Description` |

### 可复用模板：带图标特质条目

```xml
<Instance Name="IconInfoInstance">
  <Container ID="Top" Size="230,auto">
    <Image ID="Icon" Size="38,38" Offset="-6,-5" />
    <Stack ID="TextStack" Offset="36,0" StackGrowth="Bottom" StackPadding="4">
      <Label ID="Header" WrapWidth="460" Style="FontFlair16" String="$Header$"/>
      <Label ID="Description" WrapWidth="460" Style="DawnText" String="$Description$"/>
    </Stack>
  </Container>
</Instance>
```

### 全屏遮罩 + 开始按钮淡入模板

```xml
<Box ID="Background" Color="0,0,0,255" Anchor="C,C" Size="parent,parent" ConsumeMouse="1">
  <TextButton ID="FallbackMessage" Anchor="C,C" Align="center"
              Style="FontFlair20" SmallCaps="24" SmallCapsType="EveryWord"
              String="{LOC_LOADING_PLEASE_WAIT:upper}" Color="200,200,200,255"/>
  <Image ID="BackgroundImage" Anchor="C,C" StretchMode="Auto">
    <!-- 左右肖像 + 中央 Banner -->
    <Container Anchor="C,T" Size="1,parent">
      <Container ID="PortraitContainer" Anchor="L,T" Offset="80,0">
        <Image ID="Portrait" Anchor="C,T" StretchMode="Auto" />
      </Container>
    </Container>
    <Image ID="Banner" Anchor="C,C" Offset="-220,6" Size="600,parent-80"
           Texture="Controls_BannerWideTint" Alpha="0.8">
      <!-- 加载文字区 -->
      <Container ID="LoadingContainer" Anchor="C,B" Offset="0,50">
        <Label Anchor="C,B" String="{LOC_LOADING_PLEASE_WAIT:upper}" .../>
      </Container>
      <!-- 淡入开始按钮 -->
      <AlphaAnim ID="FadeAnim" AlphaBegin="0" AlphaEnd="1" Speed=".5" Stopped="0" Pause="1">
        <Button ID="ActivateButton" Anchor="C,C" Size="80,80"
                Texture="Shell_BeginButton" StateOffsetIncrement="0,80"/>
        <TextButton ID="StartLabelButton" Anchor="C,C" Offset="0,8"
                    String="{LOC_START:upper}" Style="FontFlair20"/>
      </AlphaAnim>
    </Image>
  </Image>
</Box>
```
