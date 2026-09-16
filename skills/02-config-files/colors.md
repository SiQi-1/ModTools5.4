# Colors + PlayerColors

## 涉及文件

| 文件 | 内容 |
|------|------|
| `Data/<ModName>_Colors.sql` | 自定义颜色定义 + 玩家颜色绑定 |

---

## 一、Colors（自定义颜色）

自定义颜色用 RGB 格式 `"R,G,B,255"`（Alpha 固定 255），注释标注十六进制 `#RRGGBB`。

```sql
INSERT OR REPLACE INTO Colors (Type, Color) VALUES
('COLOR_PLAYER_SIQI_{SHORT}_PRIMARY',   '156,106,31,255'),   -- 琥珀棕 #9C6A1F
('COLOR_PLAYER_SIQI_{SHORT}_SECONDARY', '230,180,80,255'),   -- 暖金   #E6B450
('COLOR_PLAYER_SIQI_{SHORT}_ACCENT',    '245,235,200,255');  -- 浅奶油 #F5EBC8
```

> 也可直接引用已有标准颜色：`"COLOR_STANDARD_ORANGE_LT"`、`"COLOR_STANDARD_BROWN_DK"` 等，见第三节。

---

## 二、PlayerColors（绑定领袖）

```sql
INSERT OR REPLACE INTO PlayerColors
		(
			Type,
			Usage,

			PrimaryColor,
			SecondaryColor,

			Alt1PrimaryColor,
			Alt1SecondaryColor,

			Alt2PrimaryColor,
			Alt2SecondaryColor,

			Alt3PrimaryColor,
			Alt3SecondaryColor
		)
VALUES
		(
			"LEADER_SIQI_{SHORT}",
			"Unique",

			"COLOR_STANDARD_ORANGE_LT",
			"COLOR_STANDARD_BROWN_DK",

			"COLOR_STANDARD_BROWN_DK",
			"COLOR_STANDARD_ORANGE_LT",

			"COLOR_STANDARD_RED_DK",
			"COLOR_STANDARD_ORANGE_DK",

			"COLOR_STANDARD_ORANGE_DK",
			"COLOR_STANDARD_RED_DK"
		);
```

> 示例配色仅供参考，实际根据主题挑选。可直接用标准颜色（`COLOR_STANDARD_xxx`）或自定义颜色（`COLOR_PLAYER_SIQI_xxx`）。
> Alt 变体规律：Alt1 = PRIMARY ↔ SECONDARY 互换；Alt2 = PRIMARY + ACCENT；Alt3 = SECONDARY + ACCENT。

| 列 | 说明 |
|---|------|
| Type | `LEADER_SIQI_{SHORT}` — 绑定领袖（官方绑定文明时写 `CIVILIZATION_xxx`） |
| Usage | `Unique` = 仅此领袖使用；`Minor` = 城邦用；`Major` = 文明通用 |
| PrimaryColor / SecondaryColor | 主配色 |
| Alt1PrimaryColor / Alt1SecondaryColor | 备选 1（爵士乐边界风格切换） |
| Alt2PrimaryColor / Alt2SecondaryColor | 备选 2 |
| Alt3PrimaryColor / Alt3SecondaryColor | 备选 3 |

> **Alt 变体规律（0032 格式）：**
> - Alt1 = PRIMARY ↔ SECONDARY 互换
> - Alt2 = PRIMARY + ACCENT
> - Alt3 = SECONDARY + ACCENT

---

## 三、官方标准颜色引用

可直接在 Color 列中引用，不用写 RGB：

| 颜色 | 色值 | 外观 |
|------|------|------|
| `COLOR_STANDARD_WHITE_LT` | — | 白 |
| `COLOR_STANDARD_WHITE_DK` | — | 暗白 |
| `COLOR_STANDARD_RED_LT` | — | 红 |
| `COLOR_STANDARD_RED_DK` | — | 深红 |
| `COLOR_STANDARD_ORANGE_LT` | — | 橙 |
| `COLOR_STANDARD_ORANGE_DK` | — | 深橙 |
| `COLOR_STANDARD_YELLOW_LT` | — | 黄 |
| `COLOR_STANDARD_YELLOW_MD` | — | 中黄 |
| `COLOR_STANDARD_YELLOW_DK` | — | 深黄 |
| `COLOR_STANDARD_GREEN_LT` | — | 绿 |
| `COLOR_STANDARD_GREEN_DK` | — | 深绿 |
| `COLOR_STANDARD_BLUE_LT` | — | 蓝 |
| `COLOR_STANDARD_BLUE_DK` | — | 深蓝 |
| `COLOR_STANDARD_PURPLE_LT` | — | 紫 |
| `COLOR_STANDARD_PURPLE_DK` | — | 深紫 |
| `COLOR_STANDARD_MAGENTA_LT` | — | 品红 |
| `COLOR_STANDARD_MAGENTA_DK` | — | 深品红 |
| `COLOR_STANDARD_AQUA_LT` | — | 青 |
| `COLOR_STANDARD_AQUA_DK` | — | 深青 |
| `COLOR_STANDARD_BROWN_LT` | — | 棕 |
| `COLOR_STANDARD_BROWN_DK` | — | 深棕 |

> 自定义颜色用 RGB 格式：`"R,G,B,255"`（Alpha 固定 255），注释标注十六进制 `#RRGGBB`。
