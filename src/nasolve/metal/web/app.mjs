import {keyOf, atomLabel, number, scopeKey, visibleAtoms, projector, autoCamera, groupSnapshots, geometrySnapshots, recipeRows, labelLayout, ratio} from './core.mjs';

const $ = id => document.getElementById(id);
const make = (tag, text, cls) => { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; if (cls) e.className = cls; return e; };
const svg = (tag, attrs) => { const e = document.createElementNS('http://www.w3.org/2000/svg', tag); for (const [k,v] of Object.entries(attrs)) e.setAttribute(k,v); return e; };
const defaults = () => autoCamera(presentation?.scene ? visibleAtoms(presentation.scene,presentation.view.selection.site_id,'residues',selectedAtom) : []);
const cameras = new Map();
let presentation, selectedAtom = null, selectedRestraint = null, busy = false;
const camera = () => { const key = scopeKey(presentation?.scene); if (!cameras.has(key)) cameras.set(key, defaults()); return cameras.get(key); };
const atomData = row => row?.data.candidate || row?.data;
function message(text, error = false) { $('message').textContent = text; $('message').classList.toggle('error', error); }

async function request(action) {
  if (busy) return;
  busy = true; lockNavigation(true); message('Opening linked saved evidence…');
  try {
    const response = await fetch('view', action ? {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(action), cache:'no-store'} : {cache:'no-store'});
    if (!response.ok) throw new Error('The local viewer could not open this selection. Restart it to reverify sources.');
    const next = await response.json();
    const changed = scopeKey(next.scene) !== scopeKey(presentation?.scene);
    if (changed || next.view.selection.row_id !== presentation?.view.selection.row_id) {
      selectedAtom = next.view.selected_row ? keyOf(atomData(next.view.selected_row).key) : null;
    }
    if(changed)selectedRestraint=null;
    presentation = next;
    render(); message('Verified saved evidence · Read-only');
  } catch (error) {
    message(error.message || 'Local viewer disconnected. Restart it to reconnect.', true);
    if (presentation) renderNavigation();
  } finally { busy = false; lockNavigation(false); }
}
function lockNavigation(value) {
  $('all').disabled = value;
  document.querySelectorAll('#navigation select, #navigation-extra select, #rows button').forEach(e => { e.disabled = value || e.dataset.empty === 'true'; });
}
function action(name, fields = {}) { return {action:name, selection:presentation.view.selection, ...fields}; }
function renderNavigation() {
  const labels = {dataset_id:'Dataset',structure_id:'Structure',hypothesis_id:'Candidate',site_id:'Site group',result_id:'Result set'};
  const root = $('navigation'), extra=$('navigation-extra'); root.replaceChildren();extra.replaceChildren();
  for (const [field,label] of Object.entries(labels)) {
    const wrap = make('label', label), select = make('select'); select.id = field;
    const all = make('option', 'All / none selected'); all.value = ''; select.append(all);
    for (const row of presentation.view.options[field]) { const option = make('option',row.label); option.value = row[field]; select.append(option); }
    select.value = presentation.view.selection[field] || '';
    select.dataset.empty = String(!presentation.view.options[field].length);
    select.disabled = select.dataset.empty === 'true';
    select.addEventListener('change', () => request(action('select',{field,value:select.value || null})));
    wrap.append(select); (['site_id','result_id'].includes(field)?extra:root).append(wrap);
  }
}
function renderRows() {
  const root=$('rows');root.replaceChildren();
  const groups=groupSnapshots(presentation.view.rows);
  $('row-count').textContent=`(${groups.length} snapshots · ${presentation.view.rows.length} source links)`;
  for(const geometry of geometrySnapshots(presentation.view.rows)) {
    const box=make('section',undefined,'snapshot');
    box.append(make('h3',`${geometry.dataset_id} › ${geometry.structure_id} › ${geometry.hypothesis_id}`));
    const table=make('table'),head=make('thead'),hr=make('tr');
    for(const name of ['Trial','Site','Element','Q (occ)','f″ obs (e)','f″ calc (e)','obs / calc'])hr.append(make('th',name));
    head.append(hr);table.append(head);
    const detail=make('details');detail.append(make('summary','B, wavelength and source links'));
    for(const [index,group] of geometry.trials.entries()) {
      const body=make('tbody',undefined,'trial-group');
      for(const [siteIndex,site] of group.sites.entries()) {
        const row=site.rows.find(r=>r.row_id===presentation.view.selection.row_id)||site.rows[0],d=row.data,a=atomData(row);
        const tr=make('tr');tr.classList.toggle('selected',site.rows.some(r=>r.row_id===presentation.view.selection.row_id));tr.dataset.rowId=row.row_id;
        if(siteIndex===0){const trial=make('th',group.trial_id?String(index+1):'Ref');trial.rowSpan=group.sites.length;trial.scope='rowgroup';trial.title=group.trial_id||'Coordinate reference comparison';tr.append(trial);}
        const td=make('td'),button=make('button',d.node_id);
        button.setAttribute('aria-label',`Inspect ${group.dataset_id}, ${d.node_id}, Q ${a.occupancy}, trial ${index+1}`);
        button.setAttribute('aria-pressed',String(tr.classList.contains('selected')));
        button.addEventListener('click',()=>request(action('row',{row_id:row.row_id})));td.append(button);tr.append(td);
        for(const value of [a.element,number(a.occupancy,2),number(d.f_double_prime),number(d.reference_f_double_prime),number(ratio(d),2)])tr.append(make('td',value));
        tr.addEventListener('click',event=>{if(!event.target.closest('button'))request(action('row',{row_id:row.row_id}));});body.append(tr);
      }
      table.append(body);
      const saved=make('details');saved.append(make('summary',`Trial ${index+1} · ${group.trial_id?.slice(0,8)||'Reference'} · ${group.sources.join(', ')}`));
      for(const site of group.sites) {
        const d=site.rows[0].data,a=atomData(site.rows[0]);
        saved.append(make('p',`${d.node_id}: B ${number(a.b_iso??a.reported_b_A2,2)} Å² · λ ${number(d.wavelength_A,5)} Å · f′ ${number(d.f_prime)} e · B policy: ${d.b_calibration?.policy||'original model B (legacy)'}`,'scope'));
        for(const row of site.rows) {const b=make('button',`${row.result_id} / ${d.node_id}`);b.addEventListener('click',()=>request(action('row',{row_id:row.row_id})));saved.append(b);}
        if(d.settings)fold(saved,`${d.node_id} fit settings`,d.settings);
      }
      detail.append(saved);
    }
    const scroll=make('div',undefined,'table-scroll');scroll.append(table);box.append(scroll,detail);root.append(box);
  }
  if(!groups.length)root.append(make('p','No saved rows in this scope. Pending points remain in the reports.','muted'));
  $('result-note').textContent='Each table is one geometry; numbered row groups keep all metals from the same trial together. f″ obs is the fitted value; f″ calc is the wavelength reference. The ratio is descriptive, not a correction or ranking. — means absent.';
  const pending=$('pending');pending.replaceChildren();
  for(const detail of presentation.view.details.filter(d=>d.report)) {
    const report=detail.report;
    if(report.pending||report.failure)pending.append(make('p',`${detail.dataset_id} / ${detail.result_id}: ${report.pending??0} pending points${report.failure?'; saved failure — see report':''}.`,'pending'));
    fold(pending,`${detail.dataset_id} / ${detail.result_id} · Full saved report`,report);
  }
}
function values(root, entries) {
  const dl = make('dl');
  for (const [key,value] of entries) { dl.append(make('dt',key),make('dd',value)); }
  root.append(dl);
}
function fold(root, title, data) { const details=make('details'); details.append(make('summary',title),make('pre',JSON.stringify(data,null,2))); root.append(details); }
function renderInspector() {
  const root = $('inspector'); root.replaceChildren();
  const row = presentation.view.selected_row, scene = presentation.scene;
  if (row) {
    const d = row.data, a = atomData(row);
    root.append(make('h3','Selected result'),make('p',`${row.dataset_id} / ${row.structure_id} / ${row.hypothesis_id} / ${row.result_id}`, 'scope'));
    root.append(make('p',`${d.node_id} · ${a.element} · ${atomLabel(a.key)}`, 'scope'));
    values(root, [['Q (occ)',number(a.occupancy)],['Refined f″ (e)',number(d.f_double_prime)],['Expected f″ (e)',number(d.reference_f_double_prime)]]);
    const secondary=make('details');secondary.append(make('summary','B, f′ and wavelength'));values(secondary,[['B (Å²)',number(a.b_iso??a.reported_b_A2)],['Fixed f′ (e)',number(d.f_prime)],['λ (Å)',number(d.wavelength_A,5)]]);root.append(secondary);
    values(root,[['f″ obs / calc',number(ratio(d),2)]]);
    if(d.b_calibration)fold(root,'Applied environmental B assumption',d.b_calibration);
    else if(d.f_double_prime!==undefined)root.append(make('p','Legacy trial: original model B was retained. Environmental B has not been applied to this saved fit.','note'));
    if (d.occupancy_vector) fold(root,'Complete trial occupancy vector',d.occupancy_vector);
    if (d.warning) root.append(make('p',d.warning,'note'));
    if (d.reference) {
      root.append(make('p','Human reference: coordinates, q and ADP snapshot. Stored anomalous values are ignored; reference coordinates are not overlaid.', 'note'));
      values(root,[['Reference Q (occ)',number(d.reference.occupancy)],['Reference B (Å²)',number(d.reference.reported_b_A2)],['Displacement (Å)',number(d.cartesian_displacement_A)]]);
    }
    fold(root,'Exact saved row and provenance',row);
  } else root.append(make('p','Select a result row to inspect its trial values and source.', 'muted'));
  const atom = scene?.atoms.find(a => keyOf(a.key) === selectedAtom);
  if (atom) {
    root.append(make('h3','Coordinate atom'), make('p',atomLabel(atom.key),'scope'));
    root.append(make('p','Values from the candidate geometry model; the selected trial may use a different fixed q.', 'muted'));
    values(root,[['Element',atom.element],['XYZ (Å)',atom.xyz.map(v=>number(v)).join(', ')],['Model Q (occ)',number(atom.occupancy)],['Model B (Å²)',number(atom.b_iso)],['ANISOU',atom.anisou ? 'Present' : 'Absent']]);
    fold(root,'Exact atom identity and state',atom);
  }
  if (scene) {
    for(const [kind,title] of [['metal','Metal sites'],['donor','Coordinating ligand atoms'],['atom','Other recipe atoms']]) {
      const nodes=scene.nodes.filter(n=>n.atom&&n.kind===kind);if(!nodes.length)continue;
      root.append(make('h3',title,kind==='metal'?'metal-heading':''));const list=make('div',undefined,'atom-list '+kind);
      for(const node of nodes){const button=make('button',`${node.node_id}: ${atomLabel(node.atom.key)}`);button.setAttribute('aria-pressed',String(keyOf(node.atom.key)===selectedAtom));button.addEventListener('click',()=>{selectedAtom=keyOf(node.atom.key);drawScene();renderInspector();});list.append(button);}root.append(list);
    }
    const environment=make('details');environment.append(make('summary','Environmental B preparation · preview'));
    environment.append(make('p','After XYZ is fixed: estimate metal B from connected nucleobases or donor atoms, then freeze it through the occupancy sweep. This preview does not alter saved trials.','muted'));
    for(const item of scene.b_environment||[]) {
      environment.append(make('p',`${item.node_id} · ${item.policy}: ${item.status==='UNAVAILABLE'?item.reason:number(item.applied_b_A2,2)+' Å²; separate base means '+item.base_means_A2.map(v=>number(v,2)).join(' / ')}`,'scope'));
      if(item.atoms && new Set(item.atoms.map(a=>a.b_A2)).size===1)environment.append(make('p','All contributing atoms have the same B. Check whether this parent still carries template values before quantitative use.','note'));
      if(item.atoms)fold(environment,`${item.node_id} / ${item.policy} · contributing atoms`,item);
    }
    root.append(environment);

    fold(root,'Geometry source', {geometry_id:scene.geometry_id,model:scene.model,status:scene.status});
  }
}
function renderRecipe() {
  const scene=presentation.scene, root=$('recipe');root.replaceChildren();
  const rows=recipeRows(scene),active=rows.filter(r=>r.enabled);
  $('recipe-title').textContent=scene ? `Coordination recipe · ${scene.recipe?.name||'Saved recipe'} · ${active.length} active terms` : 'Coordination recipe';
  if(!scene)return;
  if(!active.length)root.append(make('p','No active coordination restraints. This geometry has no recipe guardrails.','note'));
  const clear=make('button','Clear highlight');clear.addEventListener('click',()=>{selectedRestraint=null;drawScene();renderRecipe();});root.append(clear);
  const table=make('table'),head=make('thead'),hr=make('tr');
  for(const label of ['Term / ordered atoms','Current','Target','σ'])hr.append(make('th',label));head.append(hr);table.append(head);
  const body=make('tbody');
  for(const row of rows) {
    const tr=make('tr');tr.classList.toggle('selected',row.restraint_id===selectedRestraint);
    const td=make('td'),button=make('button',`${row.kind==='angle'?'Angle':'Distance'} · ${row.node_ids.join(' – ')}${row.enabled?'':' · off'}`);
    button.title=row.labels.join(' → ');button.setAttribute('aria-pressed',String(row.restraint_id===selectedRestraint));
    button.addEventListener('click',()=>{selectedRestraint=row.restraint_id;drawScene();renderRecipe();});td.append(button);
    if(row.vertex)td.append(make('div',`Vertex: ${row.vertex}`,'muted'));tr.append(td);
    for(const value of [row.measured,row.target,row.sigma])tr.append(make('td',`${number(value,row.kind==='angle'?1:3)} ${row.unit==='degree'?'°':'Å'}`));body.append(tr);
  }
  table.append(body);const scroll=make('div',undefined,'table-scroll');scroll.append(table);root.append(scroll);
  const selected=rows.find(r=>r.restraint_id===selectedRestraint);
  if(selected){root.append(make('p',selected.labels.join(' → '),'scope'));if(selected.status!=='resolved')root.append(make('p',`Status: ${selected.status}`,'note'));}
  root.append(make('p','Targets are hypotheses. The middle atom is the angle vertex; displayed angles are not converted to a metal-centred convention.','muted'));
  fold(root,'Sets, exact terms and target sources',{recipe:scene.recipe,terms:scene.restraints});
}
function syncCamera() {
  const c=camera();$('zoom').value=c.zoom;$('context').value=c.context;$('camera-mode').value=c.mode;
}
function fitCamera() {
  const c=camera(), scene=presentation.scene;
  const fitted=autoCamera(scene?visibleAtoms(scene,presentation.view.selection.site_id,c.context,selectedAtom):[]);
  Object.assign(c,fitted,{context:c.context,mode:c.mode});syncCamera();drawScene();
}
function drawScene() {
  const root=$('scene'),scene=presentation?.scene;root.replaceChildren();
  if(!scene){root.append(make('p','Choose a candidate or open a result row to see its verified coordinates.','empty'));$('geometry-status').textContent='No candidate selected';return;}
  const c=camera(),atoms=visibleAtoms(scene,presentation.view.selection.site_id,c.context,selectedAtom);
  $('geometry-status').textContent=`${scene.dataset_id} / ${scene.hypothesis_id} · Geometry awaiting review · ${atoms.length} of ${scene.atoms.length} atoms`;
  if(!atoms.length){root.append(make('p','No atoms in this view context. Choose Whole model.','empty'));return;}
  const width=root.clientWidth,height=root.clientHeight,project=projector(atoms,c,width,height);
  const canvas=svg('svg',{viewBox:`0 0 ${width} ${height}`,role:'group','aria-label':'Candidate coordinates, display connectivity and saved distance restraints'});
  const inventory=new Map(atoms.map(a=>[keyOf(a.key),a])),nodes=new Map(scene.nodes.filter(n=>n.atom).map(n=>[n.node_id,n.atom]));
  const metals=new Set(scene.nodes.filter(n=>n.kind==='metal'&&n.atom).map(n=>keyOf(n.atom.key)));
  const ligands=new Set(scene.nodes.filter(n=>n.kind==='donor'&&n.atom).map(n=>keyOf({...n.atom.key,atom_name:''})));
  const donors=new Set(scene.nodes.filter(n=>n.kind==='donor'&&n.atom).map(n=>keyOf(n.atom.key)));
  for(const connection of scene.connections||[]) {
    const pair=connection.keys.map(k=>inventory.get(keyOf(k)));if(pair.some(a=>!a))continue;
    const [a,b]=pair.map(a=>project(a.xyz));
    const line=svg('line',{x1:a[0],y1:a[1],x2:b[0],y2:b[1],stroke:'#a8b5c5','stroke-opacity':connection.source==='distance_display_only'?.25:.4,'stroke-width':1});
    const title=svg('title',{});title.textContent=connection.source==='distance_display_only'?'Distance-based display contact; not a restraint':'Captured component bond';line.append(title);canvas.append(line);
  }
  for(const r of scene.restraints.filter(r=>r.enabled&&r.kind==='distance'&&r.status==='resolved')) {
    const endpoints=r.node_ids.map(n=>nodes.get(n)).map(a=>a&&inventory.get(keyOf(a.key)));if(endpoints.some(a=>!a))continue;
    const [a,b]=endpoints.map(a=>project(a.xyz));const line=svg('line',{x1:a[0],y1:a[1],x2:b[0],y2:b[1],stroke:'#80bbfa','stroke-width':1.6,'stroke-dasharray':'3 5'});
    const title=svg('title',{});title.textContent=`${r.restraint_id}: target ${r.target} ± ${r.sigma} ${r.unit}`;line.append(title);canvas.append(line);
  }
  const picked=scene.restraints.find(r=>r.restraint_id===selectedRestraint);
  if(picked) {
    const ends=picked.node_ids.map(id=>nodes.get(id)).map(a=>a&&inventory.get(keyOf(a.key)));
    const pairs=picked.kind==='angle'?[[0,1],[1,2]]:[[0,1]];
    for(const [i,j] of pairs)if(ends[i]&&ends[j]){const [a,b]=[ends[i],ends[j]].map(a=>project(a.xyz));canvas.append(svg('line',{x1:a[0],y1:a[1],x2:b[0],y2:b[1],stroke:'#ffc18c','stroke-width':2.5,'stroke-dasharray':picked.enabled?'5 4':'2 5'}));}
  }
  const labels=[];
  for(const atom of [...atoms].sort((a,b)=>project(a.xyz)[2]-project(b.xyz)[2])) {
    const key=keyOf(atom.key),[x,y]=project(atom.xyz),chosen=key===selectedAtom,metal=metals.has(key),donor=donors.has(key);
    const circle=svg('circle',{cx:x,cy:y,r:metal?8:chosen?6:donor?4.8:2.6,fill:metal?'#d0b4ee':chosen?'#ffc18c':donor?'#80bbfa':'#7c8796',stroke:chosen?'#ffe0bb':metal?'#edddff':'#202329','stroke-width':chosen?2:1.2,tabindex:0,role:'button','aria-label':atomLabel(atom.key),class:'svg-atom'});
    const title=svg('title',{});title.textContent=atomLabel(atom.key);circle.append(title);
    const pick=()=>{selectedAtom=key;drawScene();renderInspector();};circle.addEventListener('click',event=>{if(!dragMoved)pick();event.stopPropagation();});
    circle.addEventListener('keydown',event=>{if(['Enter',' '].includes(event.key)){event.preventDefault();pick();}});canvas.append(circle);
    if(metal||ligands.has(keyOf({...atom.key,atom_name:''})))labels.push({key,x,y,element:atom.element,name:atom.key.atom_name,priority:metal?3:chosen?2:donor?1:0,metal});
  }
  for(const item of labelLayout(labels,project.scale,width,height)) {
    const label=svg('text',{x:item.x,y:item.y+11,fill:item.metal?'#dfc7fa':'#c0ccdb','fill-opacity':.8,'font-size':11,'pointer-events':'none'});label.textContent=item.text;canvas.append(label);
  }
  root.append(canvas);
}
function render(){ $('campaign').textContent=presentation.campaign_label;renderNavigation();renderRows();renderRecipe();syncCamera();drawScene();renderInspector(); }
$('all').addEventListener('click',()=>request({action:'reset'}));
$('toggle-inspector').addEventListener('click',()=>{const hidden=$('workbench').classList.toggle('no-inspector');$('toggle-inspector').textContent=hidden?'Show details':'Hide details';$('toggle-inspector').setAttribute('aria-expanded',String(!hidden));drawScene();});
$('zoom').addEventListener('input',()=>{camera().zoom=Number($('zoom').value);drawScene();});
$('camera-mode').addEventListener('change',()=>{camera().mode=$('camera-mode').value;});
$('context').addEventListener('change',()=>{camera().context=$('context').value;fitCamera();});
$('fit').addEventListener('click',fitCamera);
let drag=null,dragMoved=false;
$('scene').addEventListener('pointerdown',event=>{if(event.button!==0)return;drag={x:event.clientX,y:event.clientY,...camera(),mode:event.shiftKey?'pan':camera().mode};dragMoved=false;});
window.addEventListener('pointermove',event=>{
  if(!drag)return;const dx=event.clientX-drag.x,dy=event.clientY-drag.y;if(Math.hypot(dx,dy)<4&&!dragMoved)return;dragMoved=true;
  const c=camera();
  if(drag.mode==='pan'){c.panX=drag.panX+dx;c.panY=drag.panY+dy;}
  else if(drag.mode==='roll')c.roll=drag.roll+dx*.5;
  else{c.yaw=drag.yaw+dx*.5;c.pitch=drag.pitch+dy*.5;}
  syncCamera();drawScene();
});
window.addEventListener('pointerup',()=>{drag=null;});window.addEventListener('pointercancel',()=>{drag=null;});
$('scene').addEventListener('wheel',event=>{event.preventDefault();camera().zoom=Math.min(5,Math.max(.15,camera().zoom*Math.exp(-event.deltaY*.002)));syncCamera();drawScene();},{passive:false});
$('scene').addEventListener('keydown',event=>{
  if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key)||event.target!==$('scene'))return;
  event.preventDefault();const c=camera(),dx=event.key==='ArrowLeft'?-1:event.key==='ArrowRight'?1:0,dy=event.key==='ArrowUp'?-1:event.key==='ArrowDown'?1:0;
  if(c.mode==='pan'||event.shiftKey){c.panX+=dx*15;c.panY+=dy*15;}else if(c.mode==='roll')c.roll+=(dx||dy)*5;else{c.yaw+=dx*5;c.pitch+=dy*5;}drawScene();
});
new ResizeObserver(()=>{if(presentation)drawScene();}).observe($('scene'));
request();
