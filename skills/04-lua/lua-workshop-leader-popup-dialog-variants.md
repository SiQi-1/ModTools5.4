# PopupDialog / PopupDialogInGame 弹窗模式（来源：工坊 3518104864 Carlotta / 3665503799 Black Shores）

## 做什么
在游戏中弹出确认/选择对话框。两种 API 兼容不同场景：
- **PopupDialog**（基类）— 适合退出前提醒/简单确认，可添加多按钮
- **PopupDialogInGame**（游戏内子类）— 适合游戏操作确认，支持 Yes/No 双按钮

## API 对照

| 应用场景 | API | 按钮数 | 示例模式 |
|----------|-----|--------|----------|
| 退休/提示确认 | `PopupDialog:new("InGameTopOptionsMenu")` | 多按钮 | `AddText` + `AddButton` × N + `Open` |
| 操作确认 | `PopupDialogInGame:new("popupName")` | Yes/No | `ShowYesNoDialog(title, callback)` |

---

## 模式一：PopupDialog — 多按钮确认弹窗

### 来源：Carlotta (3518104864) 投资冷却提醒

```lua
include("PopupDialog");

local m_kPopupDialog : table;

function OnConcedeCheck(playerID)
    if Game.GetLocalPlayer() ~= playerID then return end

    if m_kPopupDialog == nil then
        m_kPopupDialog = PopupDialog:new("InGameTopOptionsMenu")
    end

    if (not m_kPopupDialog:IsOpen()) then
        m_kPopupDialog:AddText(   Locale.Lookup("LOC_WARNING_TEXT"))
        m_kPopupDialog:AddButton( Locale.Lookup("LOC_BUTTON_YES"), OnYes, nil, nil, "PopupButtonInstanceGreen")
        m_kPopupDialog:AddButton( Locale.Lookup("LOC_BUTTON_NO"),  OnNo,  nil, nil, "PopupButtonInstanceRed")
        m_kPopupDialog:Open()
        UIManager:QueuePopup(ContextPtr, PopupPriority.Low)
    end
end

function OnYes()
    -- 玩家确认后的逻辑
    LuaEvents.SomeEvent_Trigger()
end

function OnNo()
    -- 取消，通常为空
end
```

### XML 依赖
```xml
<GameData>
    <Include File="PopupDialog"/>
    <MakeInstance Name="PopupDialog" />
</GameData>
```

### 关键点
- `PopupDialog:new("InGameTopOptionsMenu")` 复用游戏的 Options Menu 样式
- `AddButton` 的第 5 个参数是 ButtonInstance 样式名（如 `"PopupButtonInstanceGreen"`）
- 必须检查 `m_kPopupDialog:IsOpen()` 防止重复弹出
- 使用 `UIManager:QueuePopup` 管理弹出层

---

## 模式二：PopupDialogInGame — 内联 Yes/No 弹窗

### 来源：Black Shores (3665503799) 模式切换 / 支援模式

```lua
include("PopupDialog");

local m_kPopupDialogInGame : table = nil;

-- 初始化时创建
function UIInit()
    if not m_kPopupDialogInGame then
        m_kPopupDialogInGame = PopupDialogInGame:new("MyPopupName")
    end
end

-- 使用时弹出
function ShowMyConfirmPopup()
    local confirmTitle = Locale.Lookup("LOC_CONFIRM_TITLE", param1, param2)
    m_kPopupDialogInGame:ShowYesNoDialog(
        confirmTitle,         -- 提示文本（支持格式化）
        OnConfirmCallback     -- Yes 按钮回调
    )
end

function OnConfirmCallback()
    -- 玩家点击确认后执行
    local tParams = {
        PlayerID = localPlayerID,
        OnStart = "MyGameAction"
    }
    UI.RequestPlayerOperation(localPlayerID, PlayerOperations.EXECUTE_SCRIPT, tParams)
end
```

### 关键点
- `PopupDialogInGame:new("popupName")` 的 name 用于去重，同一 name 只创建一次
- `ShowYesNoDialog(title, callback)` — title 是确认文本，callback 是 Yes 回调
- No 按钮自动关闭弹窗，无需额外处理
- 创建时机：在 OnLoadGameViewStateDone 中初始化一次

---

## 模式三：带检查条件的弹出（联动 GameEvents）

```lua
-- 检查冷却时间或资源是否足够
function OnMainButtonClick()
    local pCity = UI.GetHeadSelectedCity()
    if not pCity or pCity:GetOwner() ~= localPlayerID then
        UI.PlaySound('Negative_Click')
        return
    end

    local currentResource = GetPlayerCalculation(localPlayerID)
    local needResource = GetNeededAmount()

    if currentResource < needResource then
        -- 资源不足不弹窗，直接播放拒绝音效
        UI.PlaySound('Negative_Click')
        return
    end

    ShowMyConfirmPopup()
end
```

---

## 选择哪种模式？

| 条件 | 选 PopupDialog | 选 PopupDialogInGame |
|------|---------------|---------------------|
| 需要 3+ 按钮 | 是 | 否（仅 Yes/No） |
| 需要不同按钮样式（绿/红） | 是 | 否 |
| 游戏中期操作确认 | — | 是（更内聚） |
| 回合开始/退出提醒 | 是 | — |
| 需要格式化文本 | 两者皆可 | 两者皆可 |

---

## XML 配合

### 用到的 XML 文件

| 来源 Mod | XML 文件路径 | 作用 |
|----------|------------|------|
| Carlotta (3518104864) | `UI/Additions/Carlotta_Popup.xml` | PopupDialog 外观 + 按钮实例 |
| Black Shores (3665503799) | `UI/XXX.xml`（推断） | PopupDialogInGame 外观 |

### 控件 ID 对照

PopupDialog 和 PopupDialogInGame 是游戏内置系统，使用预设的 UI 模板。自定义部分仅需在 XML 中声明：

| XML 元素 | 类型 | 作用 |
|----------|------|------|
| `<Include File="PopupDialog"/>` | include | 引入 PopupDialog 系统的 UI 模板 |
| `<MakeInstance Name="PopupDialog" />` | 实例化 | 创建 PopupDialog 实例 |
| `PopupButtonInstanceGreen` | 样式名 | 绿色确认按钮样式（游戏内置） |
| `PopupButtonInstanceRed` | 样式名 | 红色取消按钮样式（游戏内置） |

### XML 声明（最小）

```xml
<GameData>
    <Include File="PopupDialog"/>
    <MakeInstance Name="PopupDialog" />
</GameData>
```

对于 PopupDialogInGame 模式，无需额外 XML — 在 Lua 中通过 `PopupDialogInGame:new("popupName")` 动态创建，系统使用内置样式。

### 可复用 XML

- **PopupDialog**：适合需要多按钮（3+）或自定义按钮颜色的场景。XML 声明极小（仅 Include + MakeInstance）
- **PopupDialogInGame**：无需任何 XML。适合 Yes/No 双按钮的游戏内确认弹窗
- 两种模式都不需要自定义 Context/Instance 模板（使用游戏内置 UI 样式）
- 如果不需要，可以不注册到 modinfo（在 Lua 中动态 include + new）
