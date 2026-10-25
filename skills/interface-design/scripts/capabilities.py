"""Read explicit catalog/config inputs; file presence never proves activation."""
from pathlib import Path
import argparse, json, tomllib

def resolve(catalog, configs):
    disabled_paths = set()
    disabled_plugins = set()
    for config in configs:
        for item in config.get('skills',{}).get('config',[]):
            if item.get('enabled') is False and item.get('path'):
                disabled_paths.add(str(Path(item['path']).resolve()))
        for key,value in config.get('plugins',{}).items():
            if isinstance(value,dict) and value.get('enabled') is False:
                disabled_plugins.add(key)
    result = []
    for item in catalog:
        path = Path(item['path'])
        resolved = str(path.resolve())
        disabled = resolved in disabled_paths or str(path.parent.resolve()) in disabled_paths or item.get('plugin_id') in disabled_plugins
        if item['name'] == 'ui_ux_pro':
            status = 'excluded'
        elif disabled:
            status = 'disabled'
        elif not path.is_file():
            status = 'missing'
        elif item.get('catalog_visible') is not True:
            status = 'file_present_activation_unknown'
        elif not configs:
            status = 'catalog_visible_config_unchecked'
        else:
            status = 'available'
        result.append({'name':item['name'],'status':status,'path':str(path)})
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--catalog',type=Path,required=True)
    p.add_argument('--config',type=Path,action='append',default=[])
    a=p.parse_args()
    catalog=json.loads(a.catalog.read_text())
    configs=[tomllib.loads(path.read_text()) for path in a.config]
    print(json.dumps({'capabilities':resolve(catalog,configs),'config_files_checked':len(configs),'automatic_enable':False},ensure_ascii=False,indent=2))

if __name__ == '__main__': main()
