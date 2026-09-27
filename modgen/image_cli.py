"""CLI for template-driven image preparation; Pillow/PSD imports stay lazy."""
import json
from pathlib import Path


def run(args):
    from ModTools_5_4.project import art_images as art
    try:
        if args.image_operation=='inspect-psd':
            result=art.inspect_psd(args.source,args.out,replace=args.replace)
        elif args.image_operation=='extract-psd':
            result=art.extract_psd(args.source,args.out,args.layer,channel=args.channel,mode=args.mode,replace=args.replace)
        elif args.image_operation=='render':
            result=art.render_recipe(args.recipe,args.out,replace=args.replace)
        else:
            result=art.check_image(art._open(Path(args.source)),args.kind,args.size)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0 if result.get('ok',True) else 1
    except (ValueError,KeyError,TypeError,OSError) as exc:
        print(json.dumps({'ok':False,'error':str(exc)},ensure_ascii=False))
        return 1


def register(subparsers):
    parser=subparsers.add_parser('image',help='PSD 模板提取、头像/历史时刻/图标配方合成与像素检查')
    sub=parser.add_subparsers(dest='image_operation',required=True)
    for name in ('inspect-psd','extract-psd','render','check'):
        command=sub.add_parser(name)
        command.add_argument('recipe' if name=='render' else 'source')
        if name!='check':
            command.add_argument('--out',required=True)
            command.add_argument('--replace',action='store_true')
        else:
            command.add_argument('--kind',choices=('white','grayscale','leader','district','moment'),required=True)
            command.add_argument('--size',type=int,nargs=2)
        if name=='extract-psd':
            command.add_argument('--layer',action='append',required=True,help='inspect 输出的图层编号，可重复')
            command.add_argument('--channel',choices=('rgba','alpha','luminance'),default='rgba')
            command.add_argument('--mode',choices=('pixels','composite'),default='pixels')
        command.set_defaults(func=run)
