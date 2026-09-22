"""Original-size PNG texture declarations; generation remains in ModTools."""
from pathlib import Path
from .merger import load_civ, save_civ
from ModTools_5_4.project.ui_textures import texture_entries, validate_ui_textures

def edit_texture(civ, operation, *, name=None, source=None, replace=False):
    path=Path(civ);project=load_civ(path)
    art=project['workspace'].setdefault('美术', {})
    data=art.setdefault('data', {}) if 'data' in art or not art else art
    entries=texture_entries(art)
    if not isinstance(entries,list):raise ValueError('独立 UI 纹理列表格式错误')
    if operation=='list':return entries
    matches=[i for i,e in enumerate(entries) if str(e.get('name','')).casefold()==str(name).casefold()]
    updated=[dict(e) for e in entries]
    if operation=='add':
        if matches and not replace:raise ValueError('纹理名称已存在；需要更新时显式使用 --replace')
        entry={'name':name,'path':str(Path(source).resolve())}
        errors=validate_ui_textures([entry])
        if errors:raise ValueError('\n'.join(errors))
        if matches:updated[matches[0]]=entry
        else:updated.append(entry)
    elif operation=='remove':
        if not matches:raise ValueError('没有找到该纹理')
        updated.pop(matches[0])
    else:raise ValueError('未知纹理操作')
    data['ui_textures']=updated
    save_civ(path,project)
    return updated
