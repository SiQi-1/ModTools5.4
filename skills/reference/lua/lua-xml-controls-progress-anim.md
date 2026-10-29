# Civ6 ForgeUI XML 控件参考 — 进度条/动画

> 分册：由 [lua-xml-controls.md](lua-xml-controls.md) 按主题拆出；覆盖 五、进度条控件、六、动画控件。触发：写 Meter、TextureBar、Alpha/Slide/FlipAnim 时。

## 五、进度条控件

## 9. Meter

圆形/弧形进度填充条。填充形状完全由纹理决定（环形、弧形、圆点）。

### 静态显示属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `Texture` | 纹理名 | 填充纹理（决定填充形状） |
| `Percent` | `"0"`~`"1"` | 初始填充比例 |
| `Color` | `R,G,B,A` | 填充色染色 |

### 动画/交互属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `Speed` | 浮点 | 动画速度。`"0"`=瞬间跳变，`"1.0"`=正常过渡 |
| `Follow` | `0`/`1` | `1`=平滑追赶动画（从当前值过渡到新值） |

```xml
<!-- 科技进度环（平滑动画） -->
<Meter ID="ProgressMeter" Size="56,56" Anchor="C,C"
       Texture="ResearchPanel_Meter" Percent="0"
       Speed="1.0" Follow="1" />

<!-- 回合计时器（瞬间跳变） -->
<Meter ID="TurnTimerMeter" Size="95,95" Anchor="C,C"
       Texture="ActionPanel_TurnTimerFill" Speed="0" />
```

Lua：`Controls.ProgressMeter:SetPercent(0.75)`

## 19. TextureBar

方向性填充条。纹理沿指定方向拉伸表示进度——矩形定向填充。

### 静态显示属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `Texture` | 纹理名 | 填充纹理 |
| `TextureOffset` | `"X,Y"` | 纹理帧偏移（PNG/DDS 像素行向下） |
| `Direction` | `"Right"`/`"Up"` | 填充方向：左→右 / 下→上 |
| `Percent` | `"0"`~`"1"` | 填充比例 |

### 动画/交互属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `Speed` | 整数 | 动画速度。`"0"`=瞬间跳变 |

```xml
<!-- 水平进度条 -->
<TextureBar ID="Progress" Direction="Right" Size="295,22"
            Texture="Espionage_ProgressBar" TextureOffset="0,22"
            Speed="0" Percent="1.0" />

<!-- 垂直填充 -->
<TextureBar ID="TouristsFill" Direction="Up" Size="52,52"
            Texture="Tourism_Meter" TextureOffset="0,52" Speed="0" />
```

### Meter vs TextureBar

| | Meter | TextureBar |
|------|-------|------------|
| 填充形状 | 圆形/弧形（纹理决定） | 矩形定向拉伸 |
| 典型场景 | 科技进度环、血条 | 水平进度条、旅游业绩 |

---

## 六、动画控件

## 15. AlphaAnim

透明度动画——淡入/淡出。

### 静态显示属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `AlphaBegin`（或 `AlphaStart`） | `"0"`~`"1"` | 起始透明度 |
| `AlphaEnd` | `"0"`~`"1"` | 目标透明度 |
| `Function` | `"Root"` | 缓动函数。`"Root"`=减速缓出 |

### 动画/交互属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `Speed` | 整数 | 越大越快。`"2"`=快速，`"10"`=极快 |
| `Cycle` | `"Once"`/`"Bounce"` | 播放一次 / 来回循环 |
| `Pause` | 浮点 | 播放前延迟秒数（如 `".6"`） |
| `ShowOnMouseOut` | `0`/`1` | `1`=鼠标离开时自动反向播放（按钮高亮专用） |
| `Stopped` | `0`/`1` | `1`=初始暂停，等 Lua `:Play()` |

## 16. SlideAnim

位移动画——平移滑入/滑出。

### 静态显示属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `Begin`（或 `Start`） | `"X,Y"` | 起始偏移量 |
| `End`（或 `EndOffset`） | `"X,Y"` | 目标偏移量 |
| `Function` | `"Root"`/`"OutQuint"`/`"OutQuad"` | 缓动函数 |

### 动画/交互属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `Speed` / `Cycle` / `Pause` / `Stopped` | 同 AlphaAnim | |

```xml
<SlideAnim ID="TurnBlockerSlide" Begin="0,30" End="0,0"
           Speed="1" Cycle="Once" Function="OutQuint" Stopped="1" />
<!-- 从下方 30px 滑入到位 -->
```

## 17. FlipAnim

精灵表帧序列动画——逐帧播放。

### 静态显示属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `Texture` | 纹理名 | 精灵表纹理 |
| `FrameCount` | 整数 | 总帧数 |
| `Columns` | 整数 | 每行列数。行数 = FrameCount / Columns |
| `Size` | `"W,H"` | 每帧显示尺寸 |

### 动画/交互属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `Speed` | 整数 | 帧速。`"10"`=中速，`"30"`=高速 |
| `Cycle` | `"OneBounce"` | 播完倒播回来 |
| `EndPause` | 整数 | 播完暂停秒数再循环 |
| `Color` | `R,G,B,A` | 染色叠加 |
| `Stopped` | `0`/`1` | `1`=初始暂停 |

```xml
<FlipAnim ID="GearAnim" Texture="CivicPanel_MeterFrameAnim"
          FrameCount="3" Columns="3" Speed="10" Size="40,40" Stopped="1" />

<FlipAnim Texture="AdvisorRecAnim22" Size="26,26" Anchor="C,C"
          FrameCount="12" Columns="4" Speed="14"
          EndPause="3" Color="255,255,255,200" />
```

### 动画 Lua 控制

```lua
Controls.MyAnim:SetToBeginning()  -- 重置到头
Controls.MyAnim:Play()            -- 正向播放
Controls.MyAnim:Reverse()         -- 设为反向
Controls.MyAnim:IsHidden()        -- 查询是否隐藏
Controls.MyAnim:IsReversing()     -- 查询是否正在反向播放
```

---

