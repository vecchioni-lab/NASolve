"""Source-bound local inspection; only explicit user actions launch native tools."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time

from .materialize import _json, _source
from .recipe import RecipeError, canonical

MAPS = {
 'map-2mfo-dfc.mtz': ('2mFo-DFc', 'TWOFOFC', 'PHITWOFOFC', 1., '#779bce', False),
 'map-mfo-dfc.mtz': ('mFo-DFc', 'FOFC', 'PHIFOFC', 3., '#75b994', True),
 'map-anomalous.mtz': ('Anomalous', 'ANOM', 'PHANOM', 3., '#c2a1d8', False),
}


class Inspections:
    def __init__(self):
        self.profiles={}
        self.cache={}
        self.lock=threading.Lock()

    def add(self, run, scene, geometry, geometry_ref, rows):
        scope={k:scene[k] for k in ('dataset_id','structure_id','hypothesis_id')}
        gid=scene['geometry_id']
        resources=geometry['files'] if geometry['kind']=='metal-xyz-trial' else {}
        dictionaries=[ref for name,ref in resources.items() if name.endswith('.cif')]
        if not dictionaries and geometry['kind']!='metal-xyz-trial':
            dictionaries=[ref for ref in geometry['inputs']['restraints'] if ref['relative_path'].endswith('.cif')]
        base=dict(run=Path(run), scope=scope, model=scene['model'], dictionaries=dictionaries,
                  maps=[dict(source=ref, stage='XYZ geometry', filename=name) for name,ref in geometry['files'].items() if name in MAPS])
        self.profiles[canonical([scope,gid])]=base
        for row in rows:
            if any(row[k]!=v for k,v in scope.items()):continue
            ref=row['data'].get('trial_manifest');tid=row['data'].get('trial_id')
            if not ref or not tid or canonical([scope,tid]) in self.profiles:continue
            trial=_json(_source(ref,run))
            if trial['parent']['manifest']['sha256'] != geometry_ref['sha256']:
                raise RecipeError('Inspection trial belongs to a different geometry')
            aggregate=None
            groups=scene.get('chemistry',{}).get('metal_groups',[])
            if groups:
                from .fdp_count import summarize_count
                result=_json(_source(trial['files']['result.json'],run))
                declared={f'recipe-group-{i+1}':dict(nodes=nodes,representation='explicit-sites') for i,nodes in enumerate(groups)}
                try:aggregate=summarize_count(result,declared)
                except RecipeError as exc:aggregate=dict(status='UNAVAILABLE',reason=str(exc))
            self.profiles[canonical([scope,tid])]=dict(base, aggregate=aggregate, model=trial['files']['final.pdb'],
                maps=base['maps']+[dict(source=ref,stage='Frozen f″ trial',filename=name) for name,ref in trial['files'].items() if name in MAPS])

    def summary(self, scene, trial):
        key=trial or scene['geometry_id'];scope={k:scene[k] for k in ('dataset_id','structure_id','hypothesis_id')}
        profile=self.profiles.get(canonical([scope,key]))
        if not profile:return None
        return dict(id=key,model=profile['model'],aggregate=profile.get('aggregate'),maps=[dict(type=MAPS[m['filename']][0],stage=m['stage'],source=m['source'],sigma=MAPS[m['filename']][3]) for m in profile['maps']],
                    note='Ordinary maps: XYZ endpoint. Anomalous map: selected frozen f″ trial. Model-assisted phases; not independent validation.')

    def perform(self, action, scene, center_key):
        if not scene or not scene.get('inspection'):raise RecipeError('Select a saved candidate first')
        scope={k:scene[k] for k in ('dataset_id','structure_id','hypothesis_id')}
        profile=self.profiles[canonical([scope,scene['inspection']['id']])]
        if any(scene[k]!=v for k,v in profile['scope'].items()):raise RecipeError('Inspection scope changed')
        atoms=scene['atoms']
        if center_key is None:
            node=next((n for n in scene['nodes'] if n['kind']=='metal' and n.get('atom')),None)
            center_key=node['atom']['key'] if node else atoms[0]['key']
        atom=next((a for a in atoms if a['key']==center_key),None)
        if atom is None:raise RecipeError('Map centre must be an exact atom in this candidate')
        # Verify source bytes again at the action boundary, including cached previews.
        model=_source(profile['model'],profile['run'])
        maps=[dict(m,raw=_source(m['source'],profile['run'])) for m in profile['maps']]
        dictionaries=[_source(ref,profile['run']) for ref in profile['dictionaries']]
        with self.lock:
            if action=='maps':
                if not maps:raise RecipeError('No captured maps for this saved candidate')
                key=canonical([scope,scene['inspection'],atom['key']])
                if key not in self.cache:
                    if len(self.cache)>=8:self.cache.pop(next(iter(self.cache)))
                    try:self.cache[key]=self._maps(maps,atom['xyz'])
                    except subprocess.TimeoutExpired as exc:raise RecipeError('Map preview timed out; use Coot for this candidate') from exc
                return self.cache[key]
            if action=='coot':return self._coot(profile,model,maps,dictionaries,atom['xyz'])
        raise RecipeError('Unknown inspection action')

    def _maps(self, maps, centre):
        from ..config import load_config
        from ..phenix_runtime import discover_phenix
        native=discover_phenix(load_config())
        with tempfile.TemporaryDirectory(prefix='nasolve-map-preview-') as tmp:
            root=Path(tmp);entries=[]
            for m in maps:
                (root/m['filename']).write_bytes(m['raw'])
                typ,amp,phase,sigma,colour,difference=MAPS[m['filename']]
                entries.append(dict(filename=m['filename'],type=typ,labels=[amp,phase],sigma=sigma,colour=colour,difference=difference,source=m['source'],stage=m['stage']))
            (root/'request.json').write_text(canonical(dict(centre=centre,maps=entries)))
            worker=Path(__file__).with_name('_map_preview_native.py')
            done=subprocess.run([str(native.executables['phenix.python']),str(worker),str(root)],cwd=root,env=dict(native.environment,PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,timeout=45)
            if done.returncode:raise RecipeError('Map preview failed; inspect this candidate in Coot. '+done.stderr[-300:])
            return _json((root/'preview.json').read_bytes())

    def _coot(self, profile, model, maps, dictionaries, centre):
        from ..config import load_config
        from ..coot_runtime import discover_coot
        coot=discover_coot(load_config())
        root=Path(tempfile.mkdtemp(prefix='nasolve-metal-coot-'));(root/'backups').mkdir()
        (root/'model.pdb').write_bytes(model);names=[];entries=[]
        for i,raw in enumerate(dictionaries):
            name=f'dictionary_{i:03d}.cif';(root/name).write_bytes(raw);names.append(name)
        for m in maps:
            (root/m['filename']).write_bytes(m['raw'])
            typ,amp,phase,sigma,colour,diff=MAPS[m['filename']]
            entries.append(dict(filename=m['filename'],labels=[amp,phase],sigma=sigma,difference=diff,title=typ+' · '+m['stage']))
        title=' / '.join(profile['scope'].values())+' · inspection copy'
        script=coot_script(names,entries,centre,title)
        (root/'open.py').write_text(script)
        command=[str(coot.executable),'--no-state-script','--no-startup-scripts','--no-guano','--script',str(root/'open.py')]
        with (root/'coot.log').open('w') as log:
            process=subprocess.Popen(command,cwd=root,env=dict(os.environ,COOT_BACKUP_DIR=str(root/'backups'),PYTHONDONTWRITEBYTECODE='1'),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        status='LAUNCHED'
        for _ in range(80):
            if (root/'loaded.json').is_file():
                try:loaded=_json((root/'loaded.json').read_bytes())
                except RecipeError:time.sleep(.1);continue
                if loaded['status']=='ERROR':raise RecipeError('Coot could not load the inspection copy: '+loaded.get('error','unknown error'))
                status=loaded['status'];break
            if process.poll() is not None:raise RecipeError('Coot exited before loading; inspect '+str(root/'coot.log'))
            time.sleep(.1)
        receipt=dict(status=status,pid=process.pid,version=coot.version,working_directory=str(root),model_source=profile['model'],maps=[{k:v for k,v in m.items() if k!='raw'} for m in maps])
        (root/'launch.json').write_text(canonical(receipt));return receipt


def coot_script(dictionaries, maps, centre, title):
    return "import coot,json,traceback\n"+"config="+repr(dict(dictionaries=dictionaries,maps=maps,centre=centre,title=title))+"\n"+'''
receipt={'status':'LOADING','maps':[]}
try:
 for name in config['dictionaries']:coot.read_cif_dictionary(name)
 model=coot.read_pdb('model.pdb')
 if model<0:raise ValueError('Model could not be loaded')
 coot.set_molecule_name(model,config['title']);coot.set_main_window_title(config['title'])
 for m in config['maps']:
  amp,phase=m['labels']
  if not coot.valid_labels(m['filename'],amp,phase,'',False):raise ValueError('Missing exact map labels')
  imap=coot.make_and_draw_map(m['filename'],amp,phase,'',0,int(m['difference']))
  if imap<0:raise ValueError('Map could not be loaded')
  coot.set_molecule_name(imap,m['title']);coot.set_contour_level_in_sigma(imap,m['sigma'])
  if m['filename']=='map-anomalous.mtz':coot.set_map_colour(imap,.76,.63,.85)
  elif not m['difference']:coot.set_map_colour(imap,.47,.61,.81)
  receipt['maps'].append(dict(m,molecule=imap))
 coot.set_rotation_centre(*config['centre']);coot.set_zoom(28.)
 receipt.update(status='READY',model=model)
except Exception as exc:receipt.update(status='ERROR',error=str(exc),traceback=traceback.format_exc())
with open('loaded.json','w') as handle:json.dump(receipt,handle,indent=2)
'''
