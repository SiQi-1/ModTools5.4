# 上下文内弹出编辑层（来源：工坊 2066679333）

## 做什么
在同一 UI Context 内（不弹新窗口），通过一个半透明遮罩 + 居中编辑面板实现"弹出式"数值/选项编辑。点击主 UI 中的条目时，覆盖层出现，编辑完成后消失。

## 如何挂载到官方UI

这是 Context 内部的自定义控件，不需要挂载到官方 UI。

## 关键 Lua 代码

### 弹出层显示/隐藏

```lua
-- 显示弹出层
function AttachValueEdit(rootControl, dealItemID)
    -- 1. 清除之前的编辑状态
    ClearValueEdit();

    local pDealItem = pDeal:FindItemByID(dealItemID);
    if pDealItem:HasPossibleValues() or pDealItem:HasPossibleAmounts() then
        g_ValueEditDealItemControlTable = FindIconInstanceFromControl(rootControl);
        g_ValueEditDealItemID = dealItemID;
        ReAttachValueEdit();  -- 在遮罩上显示编辑控件
    end
end

-- 隐藏弹出层
function ClearValueEdit()
    SetHideValueText(g_ValueEditDealItemControlTable, false);  -- 恢复原条目文字
    g_ValueEditDealItemControlTable = nil;
    g_ValueEditDealItemID = -1;
end
```

### 鼠标点击非弹出区域关闭

```lua
function InputHandler(pInputStruct)
    local uiMsg = pInputStruct:GetMessageType();
    if uiMsg == KeyEvents.KeyUp then
        return KeyHandler(pInputStruct:GetKey());
    end
    -- 任何鼠标按键松开时，关闭弹出层
    if uiMsg == MouseEvents.LButtonUp or uiMsg == MouseEvents.RButtonUp then
        ClearValueEdit();
    end
    return false;
end
```

### 弹出内容：数量编辑（整数步进）

```lua
function ReAttachValueEdit()
    -- 隐藏/显示对应的编辑区域
    ms_AgreementOptionIM:ResetInstances();
    Controls.ValueEditIconGrid:SetHide(false);
    Controls.ValueAmountEditBoxContainer:SetHide(false);

    -- 标题
    Controls.ValueEditHeaderLabel:SetText(Locale.Lookup("LOC_DIPLOMACY_DEAL_HOW_MANY"));

    -- 显示当前数量和图标
    SetIconToSize(Controls.ValueEditIcon, GetItemTypeIcon(pDealItem));
    Controls.ValueEditAmountText:SetText(tostring(pDealItem:GetAmount()));

    -- 编辑框 + 左右微调按钮
    Controls.ValueAmountEditBox:SetText(tostring(pDealItem:GetAmount()));
    Controls.ValueEditButton:RegisterCallback(Mouse.eLClick, function()
        OnValueEditButton(itemID);
    end);
    Controls.ValueAmountEditLeftButton:RegisterCallback(Mouse.eLClick, function()
        OnValueAmountEditDelta(itemID, -1);
    end);
    Controls.ValueAmountEditRightButton:RegisterCallback(Mouse.eLClick, function()
        OnValueAmountEditDelta(itemID, 1);
    end);

    Controls.ValueEditPopupBackground:SetHide(false);  -- 显示遮罩
end

function OnValueAmountEditDelta(dealItemID, delta)
    local iNewAmount = tonumber(Controls.ValueAmountEditBox:GetText() or 0) + delta;
    iNewAmount = clip(iNewAmount, 1, pDealItem:GetMaxAmount());
    Controls.ValueAmountEditBox:SetText(tostring(iNewAmount));
end
```

### 弹出内容：选项列表（协议/目标选择）

```lua
function ShowAgreementOptionPopup(agreementType, agreementTurns, fromPlayerId)
    ms_AgreementOptionIM:ResetInstances();
    Controls.ValueEditIconGrid:SetHide(true);       -- 隐藏图标+数量
    Controls.ValueAmountEditBoxContainer:SetHide(true); -- 隐藏编辑框

    -- 动态生成选项列表
    for i, entry in ipairs(possibleValues) do
        local instance = ms_AgreementOptionIM:GetInstance();
        instance.AgreementOptionLabel:SetText(szDisplayName);
        instance.AgreementOptionButton:RegisterCallback(Mouse.eLClick, function()
            OnSelectAgreementOption(agreementType, agreementTurns, ...);
        end);
    end

    Controls.ValueEditPopupBackground:SetHide(false);
end
```

### 确认/返回按钮

```lua
Controls.ValueEditButton:RegisterCallback(Mouse.eLClick, OnAgreementBackButton);

function OnAgreementBackButton()
    if not ms_bDontUpdateOnBack then
        UpdateDealPanel(g_LocalPlayer);
        UpdateProposedWorkingDeal();
    end
    Controls.ValueEditPopupBackground:SetHide(true);
end
```

## XML 控件定义

### 遮罩层 + 弹出框

```xml
<!-- 半透明黑色遮罩，拦截所有鼠标事件 -->
<Box ID="ValueEditPopupBackground" Size="parent,parent" Color="0,0,0,200"
     ConsumeMouse="1" Hidden="1">

  <!-- 居中弹出框 -->
  <Grid ID="ValueEditPopup" Style="DiplomacyInfoWindowGrid"
        Anchor="C,T" Size="300,auto" AutoSizePadding="0,13" Offset="0,200">

    <Stack StackPadding="4">
      <!-- 标题 -->
      <Grid Size="parent,38" Style="DiplomacyTitleBarGrid">
        <Label ID="ValueEditHeaderLabel" Anchor="C,C" Style="DiplomacyIntelHeader"/>
      </Grid>

      <!-- 可滚动选项区域 -->
      <ScrollPanel ID="ValueEditScrollPanel" Size="parent,200" Vertical="1">
        <ScrollBar ... />
        <Stack ID="ValueEditStack" Anchor="C,T" StackPadding="4">
          <!-- 图标+当前值 区域 -->
          <GridButton ID="ValueEditIconGrid" Style="ButtonDraggableGrid"
                      Size="auto,56" Anchor="C,T">
            <Stack Anchor="C,T" StackGrowth="Right">
              <Container Size="44,parent">
                <Image ID="ValueEditIcon" Size="44,44" Anchor="C,C"/>
                <Label ID="ValueEditAmountText" Style="FontNormalBold12" Anchor="R,B"/>
              </Container>
            </Stack>
          </GridButton>

          <!-- 数值编辑框 + 左右箭头 -->
          <Container ID="ValueAmountEditBoxContainer" Size="155,34" Anchor="C,T">
            <EditBox ID="ValueAmountEditBox" Style="FontNormalBold16"
                     NumberInput="1" Size="parent-5,parent" Anchor="C,C"/>
            <Button ID="ValueAmountEditLeftButton" Style="ArrowButtonLeft" ... />
            <Button ID="ValueAmountEditRightButton" Style="ArrowButtonRight" ... />
          </Container>
        </Stack>
      </ScrollPanel>

      <!-- 确认/返回按钮 -->
      <GridButton ID="ValueEditButton" Anchor="C,B" Size="200,41"
                  Style="MainButton" String="LOC_BACK"/>
    </Stack>
  </Grid>
</Box>
```

### 选项条目 Instance

```xml
<Instance Name="AgreementOptionInstance">
  <GridButton ID="AgreementOptionButton" Style="ButtonDraggableGrid"
              Size="280,56" Anchor="C,T">
    <Stack Anchor="L,C" StackGrowth="Right">
      <Image ID="AgreementOptionIcon" Anchor="L,C" Size="38,38"/>
      <Label ID="AgreementOptionLabel" Anchor="L,C" Offset="4,0"
             Style="FontNormal16" WrapWidth="220"/>
    </Stack>
  </GridButton>
</Instance>
```

## 数据刷新机制

- 弹出层显示时，底层主面板的数据**不会刷新**（避免弹出层状态丢失）
- 编辑确认后才同步数据：
  ```lua
  OnValueEditButton(itemID) → pDealItem:SetAmount(newAmount) → UpdateDealPanel()
  ```
- 取消编辑（返回按钮）时根据 `ms_bDontUpdateOnBack` 决定是否刷新

## 应用场景

- 交易面板中修改物品数量/选项
- 任何需要"点击条目→编辑参数→确认关闭"的 UI 流程
- 替代系统 PopupDialog（系统 PopupDialog 在某些模式下不可用，如 Leader 模式）

## XML 配合

### 涉及的关键 XML 文件

| 文件 | 路径 | 用途 |
|------|------|------|
| `DiplomacyDealView.xml` | Mod 根目录 | 主 Context，含弹出层遮罩+编辑面板+选项实例 |

### 核心控件 ID 对照表

| 控件 ID | 类型 | 用途 |
|---------|------|------|
| **弹出遮罩层** | | |
| `ValueEditPopupBackground` | Box | 半透明遮罩（Color="0,0,0,200", ConsumeMouse="1", Hidden="1"），覆盖整个屏幕 |
| `ValueEditPopup` | Grid | 居中弹出框（Anchor="C,T", Size="300,auto", Offset="0,200"） |
| `ValueEditHeaderLabel` | Label | 弹出框标题 |
| `ValueEditScrollPanel` | ScrollPanel | 可滚动内容区 |
| `ValueEditStack` | Stack | 内容垂直布局 |
| **数量编辑** | | |
| `ValueEditIconGrid` | GridButton | 图标+当前值展示区 |
| `ValueEditIcon` | Image | 物品图标 |
| `ValueEditAmountText` | Label | 当前数量文本 |
| `ValueAmountEditBoxContainer` | Container | 数值编辑区容器 |
| `ValueAmountEditBox` | EditBox | 数值输入框（NumberInput="1"） |
| `ValueAmountEditLeftButton` | Button | 减量按钮 |
| `ValueAmountEditRightButton` | Button | 增量按钮 |
| **确认/返回** | | |
| `ValueEditButton` | GridButton | 确认/返回按钮（Style="MainButton"） |
| **选项列表** | | |
| `AgreementOptionInstance` | Instance | 选项条目模板 |
| `AgreementOptionButton` | GridButton | 选项按钮 |
| `AgreementOptionIcon` | Image | 选项图标（Size="38,38"） |
| `AgreementOptionLabel` | Label | 选项文本（WrapWidth="220"） |

### 可复用 XML 模板

```xml
<!-- 弹出遮罩 + 编辑面板 -->
<Box ID="PopupBackground" Size="parent,parent" Color="0,0,0,200" ConsumeMouse="1" Hidden="1">
    <Grid ID="PopupPanel" Style="DiplomacyInfoWindowGrid" Anchor="C,T" Size="300,auto" AutoSizePadding="0,13" Offset="0,200">
        <Stack StackPadding="4">
            <!-- 标题栏 -->
            <Grid Size="parent, 38" Style="DiplomacyTitleBarGrid">
                <Label ID="PopupHeaderLabel" Anchor="C,C" Style="DiplomacyIntelHeader" Offset="0,2"/>
            </Grid>

            <!-- 滚动内容 -->
            <ScrollPanel ID="PopupScrollPanel" Size="parent,200" Vertical="1" AutoScollbar="1">
                <Stack ID="PopupContentStack" Anchor="C,T" StackPadding="4">
                    <!-- 图标 + 当前值 -->
                    <GridButton ID="ItemIconGrid" Style="ButtonDraggableGrid" Size="auto,56" Anchor="C,T">
                        <Stack Anchor="C,T" StackGrowth="Right">
                            <Container Size="44, parent">
                                <Image ID="ItemIcon" Size="44,44" Anchor="C,C"/>
                                <Label ID="ItemAmountText" Style="FontNormalBold12" Anchor="R,B"/>
                            </Container>
                        </Stack>
                    </GridButton>

                    <!-- 数值编辑框 + 左右箭头 -->
                    <Container ID="AmountEditContainer" Size="155,34" Anchor="C,T">
                        <EditBox ID="AmountEditBox" Style="FontNormalBold16" NumberInput="1" Size="parent-5,parent" Anchor="C,C"/>
                        <Button ID="AmountEditLeftButton" Style="ArrowButtonLeft" Anchor="L,C" AnchorSide="O,I"/>
                        <Button ID="AmountEditRightButton" Style="ArrowButtonRight" Anchor="R,C" AnchorSide="O,I"/>
                    </Container>
                </Stack>
            </ScrollPanel>

            <!-- 确认按钮 -->
            <GridButton ID="ConfirmButton" Anchor="C,B" Size="200,41" Style="MainButton" String="LOC_BACK"/>
        </Stack>
    </Grid>
</Box>

<!-- 选项条目 Instance -->
<Instance Name="OptionEntryInstance">
    <GridButton ID="OptionButton" Style="ButtonDraggableGrid" Size="280,56" Anchor="C,T">
        <Stack Anchor="L,C" StackGrowth="Right">
            <Image ID="OptionIcon" Anchor="L,C" Size="38,38"/>
            <Label ID="OptionLabel" Anchor="L,C" Offset="4,0" Style="FontNormal16" WrapWidth="220"/>
        </Stack>
    </GridButton>
</Instance>
```
