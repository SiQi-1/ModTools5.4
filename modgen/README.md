# modgen

文明6 Mod 工程(.CIV) 生成与校验工具。规则与 ModTools 5.4 编辑器一致，纯标准库实现，不依赖 PyQt。

> AI Agent 请阅读 [AGENTS.md](AGENTS.md)（必读）。

## 用途

让 AI（或脚本）生成"编辑器能直接打开、正确导出"的 .CIV 条目：
- `generate`：意图参数 → 合规条目（Type/LOC/默认值/子表骨架自动生成）
- `validate`：条目/工程规则校验（ERROR 硬错误 / WARNING 建议）
- `merge`：条目合并进工程（同 type 去重，自动备份 .bak）

## 安装/运行

```bash
# 无需安装，仓库根目录下直接运行
python -m modgen.cli generate 区域 --name "测试区域" --abbr TEST --prefix SIQI --infix 35
python -m modgen.cli validate 工程.CIV
python -m modgen.cli merge 工程.CIV 区域 --entry entry.json
```

## 结构

```
modgen/
├── AGENTS.md                 # AI Agent 必读说明
├── cli.py                    # generate / validate / merge 命令
├── rules.py                  # 命名/结构规则（与 GUI 一致）
├── generator.py              # generate 核心
├── validator.py              # 校验（errors + warnings）
├── merger.py                 # 合并进 .CIV（自动备份）
├── schema_store.py           # 加载 entry_schemas.json
├── schemas/entry_schemas.json# 条目结构 schema（提取产物，提交 git）
├── tools/extract_schemas.py  # 从 ModTools 源码+fixture 重新提取 schema
└── tests/test_modgen.py      # 回归测试（fixture 全过 + 真实错误抓取）
```

## 测试

```bash
python -m unittest discover -s modgen/tests -v
```

## schema 更新

编辑器字段变化后：`python modgen/tools/extract_schemas.py`（需 PyQt 环境，offscreen）。
