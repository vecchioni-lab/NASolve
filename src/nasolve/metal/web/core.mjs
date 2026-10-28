// Pure presentation helpers. Scientific navigation remains in the Python controller.
export const keyOf = key => JSON.stringify(Object.keys(key).sort().map(k => [k, key[k]]));
export const atomLabel = key => `${key.chain_id || '∅'}:${key.residue_id}${key.insertion_code} ${key.component_id} ${key.atom_name}${key.altloc ? ` (${key.altloc})` : ''}`;
export const number = (value, digits = 3) => typeof value === 'number' && Number.isFinite(value) ? value.toFixed(digits) : '—';
export function rowValues(row) {
  const d = row.data, a = d.candidate || d;
  return [row.dataset_id, row.structure_id, row.hypothesis_id, row.result_id, d.node_id, a.element,
    number(a.occupancy, 2), number(a.b_iso ?? a.reported_b_A2, 2), number(d.f_prime),
    number(d.f_double_prime), number(d.reference_f_double_prime), number(d.wavelength_A, 5)];
}
export function scopeKey(scene) {
  return scene ? [scene.dataset_id, scene.structure_id, scene.hypothesis_id, scene.geometry_id].join('/') : '';
}
export function visibleAtoms(scene, site, mode, focusedKey = null) {
  const keys = site ? scene.site_atoms[site] : scene.nodes.filter(n => n.atom).map(n => n.atom.key);
  const selected = new Set((keys || []).map(keyOf));
  if (mode === 'model') return scene.atoms;
  if (focusedKey) selected.add(focusedKey);
  const focused = scene.atoms.filter(a => selected.has(keyOf(a.key)));
  if (mode === 'site' || !focused.length) return focused;
  // Context expansion is visual only. It does not add atoms to the site/recipe.
  const residues = new Set(focused.map(a => keyOf({...a.key, atom_name:''})));
  return scene.atoms.filter(a => residues.has(keyOf({...a.key, atom_name:''})));
}
const dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0);
const identity=()=>[[1,0,0],[0,1,0],[0,0,1]];
export function autoCamera(atoms) {
  // Principal axes are a viewing aid only. No molecular coordinates are edited.
  const mean=[0,1,2].map(i=>atoms.reduce((s,a)=>s+a.xyz[i],0)/Math.max(1,atoms.length));
  const cov=[0,1,2].map(i=>[0,1,2].map(j=>atoms.reduce((s,a)=>s+(a.xyz[i]-mean[i])*(a.xyz[j]-mean[j]),0)));
  const v=identity();
  for(let iter=0;iter<32;iter++) {
    let p=0,q=1;for(const [a,b] of [[0,2],[1,2]])if(Math.abs(cov[a][b])>Math.abs(cov[p][q]))[p,q]=[a,b];
    if(Math.abs(cov[p][q])<1e-10)break;
    const angle=.5*Math.atan2(2*cov[p][q],cov[q][q]-cov[p][p]),c=Math.cos(angle),s=Math.sin(angle);
    const app=cov[p][p],aqq=cov[q][q],apq=cov[p][q];
    for(let k=0;k<3;k++)if(k!==p&&k!==q){const a=cov[k][p],b=cov[k][q];cov[k][p]=cov[p][k]=c*a-s*b;cov[k][q]=cov[q][k]=s*a+c*b;}
    cov[p][p]=c*c*app-2*s*c*apq+s*s*aqq;cov[q][q]=s*s*app+2*s*c*apq+c*c*aqq;cov[p][q]=cov[q][p]=0;
    for(let k=0;k<3;k++){const a=v[k][p],b=v[k][q];v[k][p]=c*a-s*b;v[k][q]=s*a+c*b;}
  }
  const order=[0,1,2].sort((a,b)=>cov[b][b]-cov[a][a]);
  const basis=order.map(i=>v.map(row=>row[i]));
  const [a,b]=basis;basis[2]=[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
  return {basis,zoom:1,yaw:0,pitch:0,roll:0,panX:0,panY:0,context:'residues',mode:'rotate'};
}
export function projector(atoms, camera, width, height) {
  if (!atoms.length) return Object.assign(()=>[width/2,height/2,0],{scale:0});
  const angles=['yaw','pitch','roll'].map(k=>(camera[k]||0)*Math.PI/180), [yaw,pitch,roll]=angles;
  const basis=camera.basis||identity();
  const turn=xyz=>{
    let [x,y,z]=basis.map(axis=>dot(xyz,axis));
    [x,z]=[x*Math.cos(yaw)+z*Math.sin(yaw),-x*Math.sin(yaw)+z*Math.cos(yaw)];
    [y,z]=[y*Math.cos(pitch)-z*Math.sin(pitch),y*Math.sin(pitch)+z*Math.cos(pitch)];
    return [x*Math.cos(roll)-y*Math.sin(roll),x*Math.sin(roll)+y*Math.cos(roll),z];
  };
  const points=atoms.map(a=>turn(a.xyz));
  const low=[0,1,2].map(i=>Math.min(...points.map(p=>p[i]))), high=[0,1,2].map(i=>Math.max(...points.map(p=>p[i])));
  const center=low.map((v,i)=>(v+high[i])/2);
  const scale=Math.max(1,Math.min((width-72)/Math.max(2,high[0]-low[0]),(height-72)/Math.max(2,high[1]-low[1])))*(camera.zoom||1);
  return Object.assign(xyz=>{const p=turn(xyz);return [width/2+(p[0]-center[0])*scale+(camera.panX||0),height/2-(p[1]-center[1])*scale+(camera.panY||0),p[2]-center[2]];},{scale});
}
export const ratio = d => typeof d.f_double_prime==='number' && d.reference_f_double_prime>0 ? d.f_double_prime/d.reference_f_double_prime : null;
export function groupSnapshots(rows) {
  const groups=new Map();
  for(const row of rows) {
    const d=row.data, key=JSON.stringify([row.dataset_id,row.structure_id,row.hypothesis_id,d.trial_id||['report',row.result_id]]);
    if(!groups.has(key))groups.set(key,{key,trial_id:d.trial_id||null,dataset_id:row.dataset_id,structure_id:row.structure_id,hypothesis_id:row.hypothesis_id,sources:[],sites:[]});
    const group=groups.get(key);if(!group.sources.includes(row.result_id))group.sources.push(row.result_id);
    const siteKey=JSON.stringify([d.node_id,d.key||d.candidate?.key]);
    let site=group.sites.find(s=>s.key===siteKey);
    if(!site){site={key:siteKey,rows:[]};group.sites.push(site);}site.rows.push(row);
  }
  return [...groups.values()];
}
export function labelLayout(items, pixelsPerA, width, height) {
  if(pixelsPerA<12)return [];
  const placed=[];
  for(const item of [...items].sort((a,b)=>b.priority-a.priority)) {
    const text=pixelsPerA>=28?item.name:item.element, w=text.length*6.4+4,h=15;
    for(const [dx,dy] of [[10,-17],[10,4],[-w-10,-17],[-w-10,4],[0,-30]]) {
      const box={...item,text,x:item.x+dx,y:item.y+dy,width:w,height:h};
      if(box.x<3||box.y<3||box.x+w>width-3||box.y+h>height-3)continue;
      if(placed.some(b=>box.x<b.x+b.width+4&&box.x+w+4>b.x&&box.y<b.y+b.height+3&&box.y+h+3>b.y))continue;
      // Keep labels clear of other visible ligand/metal atoms, too.
      if(items.some(a=>a.key!==item.key&&a.x>box.x-5&&a.x<box.x+w+5&&a.y>box.y-5&&a.y<box.y+h+5))continue;
      placed.push(box);break;
    }
  }
  return placed;
}
