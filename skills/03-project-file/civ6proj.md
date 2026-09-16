# .civ6proj — ModBuddy 工程文件

## 生成方式

ModBuddy 自动生成 → 手工补充文件列表和 Actions。本文给出可读版模板。

---

## 完整模板

```xml
<?xml version="1.0" encoding="utf-8"?>
<Project xmlns="http://schemas.microsoft.com/developer/msbuild/2003" ToolsVersion="12.0" DefaultTargets="Default">
  <PropertyGroup>
    <Configuration Condition=" '$(Configuration)' == '' ">Default</Configuration>
    <Name>LOC_{MODNAME}_NAME</Name>
    <Guid>{GUID}</Guid>
    <ProjectGuid>{GUID}</ProjectGuid>
    <ModVersion>1</ModVersion>
    <Teaser>LOC_{MODNAME}_DESCRIPTION</Teaser>
    <Description>LOC_{MODNAME}_DESCRIPTION</Description>
    <Authors>{作者}</Authors>
    <AffectsSavedGames>true</AffectsSavedGames>
    <SupportsSinglePlayer>true</SupportsSinglePlayer>
    <SupportsMultiplayer>true</SupportsMultiplayer>
    <SupportsHotSeat>true</SupportsHotSeat>
    <CompatibleVersions>1.2,2.0</CompatibleVersions>
```

### 依赖声明（AssociationData）

```xml
    <AssociationData><![CDATA[<Associations>
      <Dependency type="Dlc" title="Expansion: Rise and Fall" id="1B28771A-C749-434B-9053-D1380C553DE9" />
      <Dependency type="Dlc" title="Expansion: Gathering Storm" id="4873eb62-8ccc-4574-b784-dda455e74e68" />
      <Dependency type="Mod" title="{依赖Mod名}" id="{GUID}" />
    </Associations>]]></AssociationData>
```

> DLC id 固定：R&F=`1B28771A-C749-434B-9053-D1380C553DE9`，GS=`4873eb62-8ccc-4574-b784-dda455e74e68`。

### 菜单阶段动作（FrontEndActions）

```xml
    <FrontEndActionData><![CDATA[<FrontEndActions>
      <UpdateDatabase id="UpdateDatabase">
        <File>Data/{ModName}_Configs.sql</File>
      </UpdateDatabase>
      <UpdateText id="UpdateText">
        <File>Text/{ModName}_Text_CN.sql</File>
      </UpdateText>
      <UpdateIcons id="UpdateIcons">
        <Properties>
          <LoadOrder>1000</LoadOrder>
        </Properties>
        <File>Icons/{ModName}_Icons.xml</File>
      </UpdateIcons>
      <UpdateColors id="UpdateColors">
        <File>Data/{ModName}_Colors.sql</File>
      </UpdateColors>
      <UpdateArt id="UpdateArt">
        <File>(Mod Art Dependency File)</File>
      </UpdateArt>
    </FrontEndActions>]]></FrontEndActionData>
```

### 游戏内动作（InGameActions）

```xml
    <InGameActionData><![CDATA[<InGameActions>
      <UpdateColors id="UpdateColors">
        <File>Data/{ModName}_Colors.sql</File>
      </UpdateColors>
      <UpdateText id="UpdateText">
        <File>Text/{ModName}_Text_CN.sql</File>
      </UpdateText>
      <UpdateIcons id="UpdateIcons">
        <Properties>
          <LoadOrder>1000</LoadOrder>
        </Properties>
        <File>Icons/{ModName}_Icons.xml</File>
      </UpdateIcons>
      <UpdateArt id="UpdateArt">
        <File>(Mod Art Dependency File)</File>
      </UpdateArt>
      <UpdateDatabase id="UpdateDatabase">
        <Properties>
          <LoadOrder>9999</LoadOrder>
        </Properties>
        <File>Data/{ModName}_Civilizations.sql</File>
        <File>Data/{ModName}_Leaders.sql</File>
        <File>Data/{ModName}_Districts.sql</File>
        <File>Data/{ModName}_Buildings.sql</File>
        <File>Data/{ModName}_Units.sql</File>
        <File>Data/{ModName}_UnitAbilities.sql</File>
        <File>Data/{ModName}_UnitPromotions.sql</File>
        <File>Data/{ModName}_Improvements.sql</File>
        <File>Data/{ModName}_Governors.sql</File>
        <File>Data/{ModName}_Policies.sql</File>
        <File>Data/{ModName}_Projects.sql</File>
        <File>Data/{ModName}_Modifiers.sql</File>
        <File>Data/{ModName}_Moments.sql</File>
      </UpdateDatabase>
```

> `LoadOrder` 按需设定：依赖已有表的写大值（如 9999）保证最后加载；自建新表的写 `-1` 保证最先加载。多文件写多个 `<File>`。临时表在文件内 `CREATE TEMP TABLE` / `DROP TABLE` 即可。
> Lua 相关动作（AddGameplayScripts / AddUserInterfaces / ImportFiles）在 Lua skill 中补充。

### 嵌入的本地化文本（Mod 名/描述）

```xml
    <LocalizedTextData><![CDATA[<LocalizedText>
      <Text id="LOC_{MODNAME}_NAME">
        <zh_Hans_CN>{Mod中文名}</zh_Hans_CN>
      </Text>
      <Text id="LOC_{MODNAME}_DESCRIPTION">
        <zh_Hans_CN>{Mod简介}</zh_Hans_CN>
      </Text>
    </LocalizedText>]]></LocalizedTextData>
  </PropertyGroup>
```

### 构建输出

```xml
  <PropertyGroup Condition=" '$(Configuration)' == 'Default' ">
    <OutputPath>.</OutputPath>
  </PropertyGroup>
```

### 文件清单（ItemGroup）

```xml
  <ItemGroup>
    <Content Include="Data\{ModName}_Buildings.sql">
      <SubType>Content</SubType>
    </Content>
    <Content Include="Data\{ModName}_Civilizations.sql">
      <SubType>Content</SubType>
    </Content>
    <Content Include="Data\{ModName}_Colors.sql">
      <SubType>Content</SubType>
    </Content>
    <Content Include="Data\{ModName}_Configs.sql">
      <SubType>Content</SubType>
    </Content>
    <!-- ... 其余 Data/ SQL 文件 ... -->
    <Content Include="Icons\{ModName}_Icons.xml">
      <SubType>Content</SubType>
    </Content>
    <Content Include="Text\{ModName}_Text_CN.sql">
      <SubType>Content</SubType>
    </Content>
    <!-- ... Scripts/ UI/ Import/ 等 ... -->
  </ItemGroup>
```

### 文件夹声明

```xml
  <ItemGroup>
    <Folder Include="Data\" />
    <Folder Include="Icons\" />
    <Folder Include="Text\" />
    <Folder Include="Scripts\" />
    <Folder Include="UI\" />
    <Folder Include="Import\" />
    <Folder Include="Platforms\" />
    <Folder Include="Platforms\Windows\" />
    <Folder Include="Platforms\Windows\Audio\" />
    <Folder Include="ArtDefs\" />
    <Folder Include="XLPs\" />
  </ItemGroup>
  <Import Project="$(MSBuildLocalExtensionPath)Civ6.targets" />
</Project>
```

> Guid / ProjectGuid 随机生成，ModBuddy 首次打开时自动填充。

---

## 自动化流程

1. 从 `06-naming.md` 推导文件结构（有哪些 Data/ 文件）
2. 从 `configs.md` 确认 FrontEndActions 的 Configs 路径
3. 从 `colors.md` 确认 Colors.sql 路径
4. 从 `icons.md` 确认 Icons.xml 路径
5. 按标准顺序排列 InGameActions 的 UpdateDatabase 文件列表
6. 如有 Lua 文件，追加 AddGameplayScripts / AddUserInterfaces / ImportFiles
7. 文件清单（ItemGroup）与 Action 中引用的文件保持一致
