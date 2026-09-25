# Steam 创意工坊发布与上传包检查

适用：准备工坊 workspace、核验构建产物、使用煎包 / Jianbao233 的 Civ6WorkshopUploader 发布和更新。

## Workspace 与元数据

~~~text
workspace/
  workshop.json
  image.png          可选预览图
  content/           已构建 Mod，含 .modinfo
  mod_id.txt         首次上传后写入，更新时保留
~~~

参考上传器将顶层 title / description / changeNote 写到 english 语言变体；中文等放 localizations，language 用 schinese 等工具认可的语言名。description 使用 BBCode，不默认支持 Markdown。visibility 可为 private、friends_only、unlisted、public，按发布需求选择。

dependencies 按上传器契约使用 UInt64 整数数组，例如 [1234567890]，不使用字符串 ID。更新已有条目时 title / description / visibility 允许省略或 null，上传器保留对应线上值；dependencies 省略可能清空既有依赖，应显式核对完整依赖列表。tags 为字符串数组，localizations 为带 language 的对象数组。

mod_id.txt 是工坊条目 ID，.modinfo id 是游戏 Mod GUID。更新时保留并核对既有条目 ID；上传失败先确认是否已创建，避免重复新建。

## 本项目只读检查

~~~powershell
python -m modgen.cli workshop check modgen_work/MyMod/workshop --json
python -m modgen.cli workshop check modgen_work/MyMod/workshop --modinfo MyMod.modinfo --json
~~~

content 有多个 modinfo 时用第二种显式选择。检查元数据、GUID、Properties、Files、动作引用、可选 PNG 文件头和已有条目 ID。实际文件未登记时给出警告，核对是否为预期 Cooker 产物；已声明文件缺失不能以“Cooker 会补”放行。

检查不连接 Steam，不验证所有权、线上依赖或实机加载。完整封面内容和上传限制由实际上传器验证。

## 外部上传器接入

保持 EXE、steam_api64.dll、steam_appid.txt 完整，按用户已有版本帮助运行：

~~~powershell
Civ6WorkshopUploader.exe validate -w <workspace>
Civ6WorkshopUploader.exe upload -w <workspace>
~~~

仅在用户要求发布或更新的任务中运行 upload；本次技能整合不发布内容。使用本次构建产物，不混入源码、日志和旧包。

参考版本退出码：0 成功，1 硬错误，validate 的 2 为建议问题。validate 不等于上传成功。失败后先查日志和条目 ID，再决定后续操作，不做无限重试。

上传需 Steam 运行并登录，账号拥有 Civ6。工具自身使用 SDK AppId 404350，条目属于游戏 AppId 289070；不要混改。这是本轮 1.0.0 包的契约，升级后重新核对。

## 交付记录

保留构建版本、工程位置、workspace、条目 ID、可见性和实际验收结果。台账放对应 Mod 的本地工作目录，不进入工具仓库。发布前完成游戏测试和署名核对，上传后核实条目及目标语言。

## 来源

[来源 S5 / S4](../../THIRD_PARTY_NOTICES.md)：煎包 / Jianbao233 的 Civ6WorkshopUploader 1.0.0，参考 README.zh-CN.md、AGENTS.md、docs/workflow.md；千寻瀑（千与千寻瀑）的 civ6-modding/release.md 和交付检查思路。配置类型与更新语义另核对上游 src/ModConfig.cs、src/UploadCommand.cs（提交 17b32062e5663c3e0eedb390ec921f37f9a97ba5）；该补充核对不表示本地包与线上提交完全相同。保留 MIT 许可；未内置上传器、Steam DLL 或自动发布逻辑。
