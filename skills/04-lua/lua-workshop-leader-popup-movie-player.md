# BIK 播片/视频播放器 UI（来源：工坊 3665503799 Black Shores / 3549419242 BAIE）

## 做什么
在游戏内创建一个可以播放 BIK 格式视频的全屏叠加层，支持播放完成后自动关闭、ESC/任意键关闭、暂停/恢复模组背景音乐。

---

## 一、XML 视频容器

```xml
<Context>
    <!-- 视频背景遮罩 -->
    <Container ID="BS_VideoContainer" Size="parent,parent"
               Anchor="C,C" Hidden="1">
        <Box Size="parent,parent" Color="0,0,0,255"/>
        <!-- 电影控件 -->
        <Movie ID="BS_Movie" Anchor="C,C" Size="1280,720"
               Texture="MovieFrame" Loop="0"/>
    </Container>
</Context>
```

### Movie 控件关键属性
| 属性 | 说明 |
|------|------|
| `Texture="MovieFrame"` | 必须，否则 SetMovie 无效 |
| `Loop="0"` | 不循环播放 |
| `Anchor="C,C"` | 居中播放 |
| `Size="1280,720"` | 视频分辨率适配 |

---

## 二、播放/停止控制

### 来源：Black Shores (3665503799) 总督/领袖播片

```lua
-- 暂停/恢复模组背景音乐
UI.PauseModCivMusic()
UI.ResumeModCivMusic()

function BSPlayMovies(params)
    -- params = { playerID, govType, leaderType }
    if params.playerID ~= localPlayerID then return end

    -- 暂停背景音乐
    UI.PauseModCivMusic()

    -- 显示视频层
    if ContextPtr:IsHidden() then
        ContextPtr:SetHide(false)
    end
    ContextPtr:SetInputHandler(OnInputHandler, true)
    Controls.BS_VideoContainer:SetShow(true)

    -- 构造视频路径
    local moviePath = nil
    if params.govType then
        moviePath = "BS_Governor_Movies_" .. params.govType .. ".bik"
    elseif params.leaderType then
        moviePath = "BS_Leader_Movies_" .. params.leaderType .. ".bik"
    end

    -- 加载并播放
    local isLoaded = Controls.BS_Movie:SetMovie(moviePath)
    if isLoaded then
        Controls.BS_Movie:Play()
    else
        Close()  -- 加载失败则关闭
    end
end

function Close()
    if not ContextPtr:IsHidden() then
        ContextPtr:SetHide(true)
        ContextPtr:SetInputHandler(nil, false)
        if Controls.BS_Movie then
            Controls.BS_Movie:Stop()
            Controls.BS_Movie:Pause()
        end
        if Controls.BS_VideoContainer then
            Controls.BS_VideoContainer:SetShow(false)
        end
    end
    UI.ResumeModCivMusic()
end
```

---

## 三、播放完成 / 用户打断 回调

```lua
-- 注册电影结束回调
Controls.BS_Movie:SetMovieFinishedCallback(OnMovieExitOrFinished)

function OnMovieExitOrFinished()
    Close()
end

-- 输入拦截：ESC 或任意鼠标键退出
function OnInputHandler(pInputStruct)
    if ContextPtr:IsHidden() then return false end

    local uiMsg = pInputStruct:GetMessageType()

    -- ESC 键退出
    if uiMsg == KeyEvents.KeyUp and pInputStruct:GetKey() == Keys.VK_ESCAPE then
        Close()
        return true
    end

    -- 任意鼠标按键退出（左/右/中键）
    if (uiMsg == MouseEvents.LButtonUp or
        uiMsg == MouseEvents.RButtonUp or
        uiMsg == MouseEvents.MButtonUp or
        uiMsg == MouseEvents.PointerUp) then
        Close()
        return true
    end

    return true  -- 拦截所有其他输入
end
```

---

## 四、初始化设置

```lua
function Initialize()
    -- 检查是否有需要播片的领袖
    local hasLeader = false
    for _, playerID in ipairs(PlayerManager.GetAliveMajorIDs()) do
        if HasTrait(playerID) then
            hasLeader = true
            break
        end
    end
    if not hasLeader then return end

    -- 视频层初始隐藏
    Controls.BS_VideoContainer:SetShow(false)
    Controls.BS_Movie:SetMovieFinishedCallback(OnMovieExitOrFinished)
    ContextPtr:SetHide(true)

    -- 接收外部播片请求
    LuaEvents.BSPlayMovies.Add(BSPlayMovies)
end
Events.LoadGameViewStateDone.Add(Initialize)
```

---

## 五、触发播片的时机

### 来自 Gameplay Lua（通过 LuaEvent）

```lua
-- 在 GP 端触发
ReportingEvents.SendLuaEvent('BSPlayMovies', {
    playerID = playerID,
    govType = "KQ",
    -- leaderType = 1
})
```

### 来自其他 UI（通过 LuaEvent）

```lua
LuaEvents.BSPlayMovies({
    playerID = localPlayerID,
    leaderType = 2
})
```

---

## 六、视频文件要求

| 项目 | 说明 |
|------|------|
| 格式 | **BIK**（Bink Video，RAD Game Tools） |
| 路径 | Mod 的 Platforms/Windows 目录下，相对路径 |
| 命名 | `BS_Governor_Movies_KQ.bik` 等 |
| 循环 | 通过 `Loop="0"` 控制不循环 |

视频文件放在 Mod 项目的 `Platforms/Windows/` 或对应平台目录即可被加载。

---

## 七、完整模板

```lua
-- MoviePlayer.lua
local localPlayerID = Game.GetLocalPlayer()

function PlayMyMovie(movieName)
    UI.PauseModCivMusic()

    if ContextPtr:IsHidden() then ContextPtr:SetHide(false) end
    ContextPtr:SetInputHandler(OnInputHandler, true)
    Controls.MovieContainer:SetShow(true)

    if Controls.MyMovie:SetMovie(movieName .. ".bik") then
        Controls.MyMovie:Play()
    else
        CloseMovie()
    end
end

function CloseMovie()
    if not ContextPtr:IsHidden() then
        ContextPtr:SetHide(true)
        ContextPtr:SetInputHandler(nil, false)
        Controls.MyMovie:Stop()
        Controls.MovieContainer:SetShow(false)
    end
    UI.ResumeModCivMusic()
end

function OnMovieFinished()
    CloseMovie()
end

function OnInputHandler(pInputStruct)
    if ContextPtr:IsHidden() then return false end
    if pInputStruct:GetMessageType() == KeyEvents.KeyUp
       and pInputStruct:GetKey() == Keys.VK_ESCAPE then
        CloseMovie()
        return true
    end
    return true
end

function Initialize()
    Controls.MovieContainer:SetShow(false)
    Controls.MyMovie:SetMovieFinishedCallback(OnMovieFinished)
    ContextPtr:SetHide(true)
    LuaEvents.PlayMyMovie.Add(PlayMyMovie)
end
Events.LoadGameViewStateDone.Add(Initialize)
```

---

## XML 配合

### 用到的 XML 文件

| 来源 Mod | XML 文件路径 | 作用 |
|----------|------------|------|
| Black Shores (3665503799) | `UI/UI_Civ_BS.xml` | 视频容器 + Movie 控件 |
| BAIE (3549419242) | `UI/XXX.xml`（推断） | 类似的播片面板 |

### 控件 ID 对照

| XML 控件 ID | 类型 | Lua 角色 |
|------------|------|---------|
| `BS_VideoContainer` | `Container` | 视频全屏叠加层根容器，`SetShow(true/false)` |
| `BS_Movie` | `Movie` | BIK 播放控件，`SetMovie()` + `Play()` / `Stop()` |

### 完整 XML

```xml
<Context>
    <Container ID="BS_VideoContainer" Anchor="C,C"
               Size="parent,parent" Offset="0,0">
        <Movie ID="BS_Movie" Size="parent,parent"
               StretchMode="UniformToFill"/>
    </Container>
</Context>
```

如需带黑色背景遮罩的版本：

```xml
<Context>
    <Container ID="BS_VideoContainer" Size="parent,parent"
               Anchor="C,C" Hidden="1">
        <Box Size="parent,parent" Color="0,0,0,255"/>
        <Movie ID="BS_Movie" Anchor="C,C" Size="1280,720"
               Texture="MovieFrame" Loop="0"/>
    </Container>
</Context>
```

### 可复用 XML

- **Movie 控件**：`Texture="MovieFrame"` 是必须的属性，否则 `SetMovie()` 无效
- 视频文件存放于 `Platforms/Windows/` 目录（BIK 格式）
- Context 初始 `Hidden="1"` 或 `Container` 初始 `Hidden="1"`，由 Lua 在播片时显示
- 作为独立 Context 注册到 modinfo（AddUserInterfaces）
