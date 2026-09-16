# Icons — 图标定义（XML）

## 涉及文件

| 文件 | 内容 |
|------|------|
| `Icons/<ModName>_Icons.xml` | IconTextureAtlases + IconDefinitions + IconAliases |

## 结构

```xml
<?xml version='1.0' encoding='utf-8'?>
<GameData>
  <IconTextureAtlases>
    <!-- 每个实体一种 Atlas，定义各尺寸纹理文件 -->
  </IconTextureAtlases>
  <IconDefinitions>
    <!-- 每个实体一个 Icon，指向 Atlas + Index -->
  </IconDefinitions>
  <IconAliases>
    <!-- 别名（可选，如总督晋升图标指向 FILL） -->
  </IconAliases>
</GameData>
```

---

## 一、IconTextureAtlases

```xml
<Row Name="ATLAS_DISTRICT_SIQI_{SHORT}" IconSize="22" Filename="ICON_DISTRICT_SIQI_{SHORT}_22"/>
<Row Name="ATLAS_DISTRICT_SIQI_{SHORT}" IconSize="32" Filename="ICON_DISTRICT_SIQI_{SHORT}_32"/>
<Row Name="ATLAS_DISTRICT_SIQI_{SHORT}" IconSize="38" Filename="ICON_DISTRICT_SIQI_{SHORT}_38"/>
<Row Name="ATLAS_DISTRICT_SIQI_{SHORT}" IconSize="50" Filename="ICON_DISTRICT_SIQI_{SHORT}_50"/>
<Row Name="ATLAS_DISTRICT_SIQI_{SHORT}" IconSize="80" Filename="ICON_DISTRICT_SIQI_{SHORT}_80"/>
<Row Name="ATLAS_DISTRICT_SIQI_{SHORT}" IconSize="128" Filename="ICON_DISTRICT_SIQI_{SHORT}_128"/>
<Row Name="ATLAS_DISTRICT_SIQI_{SHORT}" IconSize="256" Filename="ICON_DISTRICT_SIQI_{SHORT}_256"/>
```

每个 Row = Atlas 在不同尺寸下的纹理文件。`IconSize` 为正方形像素边长。

---

## 二、IconDefinitions

```xml
<Row Name="ICON_DISTRICT_SIQI_{SHORT}" Atlas="ATLAS_DISTRICT_SIQI_{SHORT}" Index="0"/>
```

| 属性 | 说明 |
|------|------|
| Name | 图标标识（SQL 中 `ICON_xxx` 引用此值） |
| Atlas | 指向上方定义的 Atlas |
| Index | 图集内索引（单图标 = 0，共用图集时递增） |

> 政策卡可**共用已有图集**（`ICON_ATLAS_POLICIES`），通过不同 `Index` 区分：
> ```xml
> <Row Name="ICON_POLICY_SIQI_{SHORT}" Atlas="ICON_ATLAS_POLICIES" Index="0"/>
> ```

---

## 三、IconAliases（可选）

```xml
<Row Name="ICON_GOVERNOR_SIQI_{SHORT}_PROMOTION" OtherName="ICON_GOVERNOR_SIQI_{SHORT}_FILL"/>
```

> 总督晋升图标别名指向上方图标，避免重复定义。

---

## 四、图标尺寸参考

### 文明
| 尺寸 | 使用场景 |
|------|---------|
| 22, 30, 32, 36, 44, 45, 48, 50, 64, 80, 128, 200, 256 | 文明选择 / 百科 / 外交等 |

### 领袖
| 尺寸 | 使用场景 |
|------|---------|
| 32, 45, 48, 50, 55, 64, 80, 256 | 领袖选择 / 外交头像 / 载入画面 |

### 区域
| 尺寸 | 使用场景 |
|------|---------|
| 22, 32, 38, 50, 80, 128, 256 | 科技树 / 市政树 / 建造菜单 / 百科 |

### 建筑
| 尺寸 | 使用场景 |
|------|---------|
| 32, 38, 50, 80, 128, 256 | 建造菜单 / 城市面板 / 百科 |

### 改良
| 尺寸 | 使用场景 |
|------|---------|
| 38, 50, 80, 256 | 地块图标 / 建造者菜单 / 百科 |

### 单位（普通）
| 尺寸 | 使用场景 |
|------|---------|
| 22, 32, 38, 50, 80, 128, 256 | 单位面板 / 建造菜单 / 百科 |

### 单位（肖像）
| 尺寸 | 使用场景 |
|------|---------|
| 38, 50, 70, 95, 200, 256 | 单位详情面板 / 伟人面板 |

> 命名模板：`ICON_UNIT_SIQI_{SHORT}_PORTRAIT_{SIZE}`，Atlas 加 `_PORTRAIT` 后缀。

### 总督（普通）
| 尺寸 | 使用场景 |
|------|---------|
| 22, 32, 64 | 总督面板 / 指派界面 |

### 总督（填充/FILL）
| 尺寸 | 使用场景 |
|------|---------|
| 22, 32 | 总督晋升图标（通过 Alias 引用） |

### 总督（槽位/SLOT）
| 尺寸 | 使用场景 |
|------|---------|
| 22, 32 | 总督槽位图标 |

### 项目
| 尺寸 | 使用场景 |
|------|---------|
| 30, 32, 38, 50, 70, 80, 256 | 项目面板 / 建造菜单 / 百科 |

### 政策卡
| 说明 |
|------|
| 复用已有图集 `ICON_ATLAS_POLICIES`，只需定义 `IconDefinitions` 的 Index。无需新建 Atlas。 |

---

## 五、历史时刻插图（Moment）

命名格式：`Moment_{Type首字母大写其余小写}`（无 `.dds` 后缀）。

如 `BUILDING_SQ_B0037_1` → `Moment_Building_Sq_B0037_1`，`UNIT_SQ_U0037_1` → `Moment_Unit_Sq_U0037_1`。

```sql
INSERT INTO MomentIllustrations (MomentIllustrationType, MomentDataType, GameDataType, Texture) VALUES
('MOMENT_ILLUSTRATION_UNIQUE_BUILDING', 'MOMENT_DATA_BUILDING', 'BUILDING_SIQI_{SHORT}', 'Moment_Building_Siq_{SHORT}'),
('MOMENT_ILLUSTRATION_UNIQUE_UNIT',     'MOMENT_DATA_UNIT',     'UNIT_SIQI_{SHORT}',     'Moment_Unit_Siq_{SHORT}');
```

常用 `MomentIllustrationType`：`MOMENT_ILLUSTRATION_UNIQUE_BUILDING`、`MOMENT_ILLUSTRATION_UNIQUE_UNIT`、`MOMENT_ILLUSTRATION_UNIQUE_DISTRICT`、`MOMENT_ILLUSTRATION_UNIQUE_IMPROVEMENT`。

表的定义来自 Expansion2 Schema，无 Expansion2 的 Mod 不能使用。

---

## 六、生成流程

1. 扫描所有 SQL 文件中的 `ICON_` 引用
2. 按类型归类，为每个 `ICON_xxx` 生成对应的 Atlas（按尺寸表）和 IconDefinition
3. 总督额外生成 FILL + SLOT 变体，并用 IconAliases 链接 PROMOTION → FILL
4. 单位额外生成 PORTRAIT 变体
5. 政策卡共用 `ICON_ATLAS_POLICIES`，不建新 Atlas
