# modifier-city — 城市（成长/住房/宜居度/忠诚度/人口）类 EffectType — 注意事项/速查

> 分册：由 [modifier-city.md](modifier-city.md) 按主题拆出；覆盖 注意事项。触发：实现前核对注意事项、溯源与枚举时。

## 注意事项/速查

## 注意事项

1. **命名一致性**：`EFFECT_ADJUST_CITY_IDENTITY_*` 系列使用 `IDENTITY`（游戏内部命名），但 UI 中显示为"忠诚度（Loyalty）"。注意 `MODIFIER_EMERGENCY_TARGET_CITY_GRANT_LOYALTY` 使用了 `LOYALTY` 而非 `IDENTITY`，属命名不一致但实际效果相同。

2. **`EFFECT_ADJUST_CITY_PROPERTY`**：仅 `MODIFIER_SINGLE_CITY_ADJUST_PROPERTY` 可用（`MODIFIER_PLAYER_CITIES_ADJUST_PROPERTY` 和 `MODIFIER_DISTRICTS_ADJUST_CITY_PROPERTY` 不存在）。`Key` 参数为自定义字符串，无官方枚举约束。使用时需确保 Lua 或后续逻辑能正确读取该 Key。

3. **`EFFECT_GRANT_PRODUCTION_IN_CITY` vs `EFFECT_PURCHASE_PRODUCTION_IN_CITY`**：
   - `_GRANT_` = 给免费生产力（一次性注入进度）
   - `_PURCHASE_` = 允许用金币购买（本身不给生产力，花费两倍金币）
   - 两者通常搭配使用（如伟人大工）。

4. **`EFFECT_ADJUST_PLAYER_BAN_CITY_PRODUCTION`**：`DistrictType` 隐藏参数来源为 Modding Companion，暂无官方实例。`BuildingType` 参数未经验证，有效性存疑。

5. **`EFFECT_ADJUST_CITY_HAPPINESS_YIELD`**：`HappinessType` 枚举值 `HAPPINESS_ECSTATIC` / `HAPPINESS_HAPPY` 无独立 .txt 枚举文件，仅可通过数据库查询或 Modding Companion 校验。
