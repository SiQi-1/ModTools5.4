"""Original-size PNG texture declarations; generation remains in ModTools."""
from pathlib import Path
from .merger import load_civ, save_civ
from ModTools_5_4.project.ui_textures import texture_entries, validate_ui_textures

def import_manifest(civ, manifest, *, png_dir=None, replace=False, dry_run=False):
    """Validate the whole batch, merge by name, then save once with one backup."""
    from .html_ui import manifest_entries

    incoming = manifest_entries(manifest, png_dir)
    path = Path(civ)
    project = load_civ(path)
    workspace = project.get('workspace')
    if not isinstance(workspace, dict):
        raise ValueError('workspace 不是对象')
    art = workspace.setdefault('美术', {})
    if not isinstance(art, dict):
        raise ValueError('美术工作区不是对象')
    entries = texture_entries(art)
    if entries is None:
        entries = []
    if not isinstance(entries, list) or any(not isinstance(entry, dict) for entry in entries):
        raise ValueError('独立 UI 纹理列表格式错误')
    updated = [dict(entry) for entry in entries]
    # Validate source paths after merging so --replace can repair a moved project.
    positions = {str(entry.get('name') or '').casefold(): i for i, entry in enumerate(updated)}
    added, replaced = [], []
    for entry in incoming:
        key = entry['name'].casefold()
        if key in positions:
            if not replace:
                raise ValueError(f"纹理名称已存在：{entry['name']}；需要更新时显式使用 --replace")
            updated[positions[key]] = entry
            replaced.append(entry['name'])
        else:
            positions[key] = len(updated)
            updated.append(entry)
            added.append(entry['name'])
    errors = validate_ui_textures(updated)
    if errors:
        raise ValueError('\n'.join(errors))
    data = art.setdefault('data', {}) if 'data' in art or not art else art
    if not isinstance(data, dict):
        raise ValueError('美术 data 不是对象')
    data['ui_textures'] = updated
    if not dry_run:
        save_civ(path, project)
    return {'ok': True, 'dry_run': dry_run, 'added': added, 'replaced': replaced,
            'count': len(incoming), 'total': len(updated), 'entries': incoming}


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
