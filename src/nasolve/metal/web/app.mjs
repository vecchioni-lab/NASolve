import {keyOf, atomLabel, number, rowValues, scopeKey, visibleAtoms, projector} from './core.mjs';

const $ = id => document.getElementById(id);
const make = (tag, text, cls) => { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; if (cls) e.className = cls; return e; };
const svg = (tag, attrs) => { const e = document.createElementNS('http://www.w3.org/2000/svg', tag); for (const [k,v] of Object.entries(attrs)) e.setAttribute(k,v); return e; };
const defaults = () => ({zoom:1, yaw:-25, pitch:20, context:'residues'});
const cameras = new Map();
let presentation, selectedAtom = null, busy = false;
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
    presentation = next;
    render(); message('Saved snapshot verified at opening. Navigation is read-only.');
  } catch (error) {
    message(error.message || 'Local viewer disconnected. Restart it to reconnect.', true);
    if (presentation) renderNavigation();
  } finally { busy = false; lockNavigation(false); }
}
function lockNavigation(value) {
  $('all').disabled = value;
  document.querySelectorAll('#navigation select, #rows button').forEach(e => { e.disabled = value || e.dataset.empty === 'true'; });
}
function action(name, fields = {}) { return {action:name, selection:presentation.view.selection, ...fields}; }
function renderNavigation() {
  const labels = {dataset_id:'Dataset',structure_id:'Structure',hypothesis_id:'Candidate',site_id:'Site group',result_id:'Result set'};
  const root = $('navigation'); root.replaceChildren();
  for (const [field,label] of Object.entries(labels)) {
    const wrap = make('label', label), select = make('select'); select.id = field;
    const all = make('option', 'All / none selected'); all.value = ''; select.append(all);
    for (const row of presentation.view.options[field]) { const option = make('option',row.label); option.value = row[field]; select.append(option); }
    select.value = presentation.view.selection[field] || '';
    select.dataset.empty = String(!presentation.view.options[field].length);
    select.disabled = select.dataset.empty === 'true';
    select.addEventListener('change', () => request(action('select',{field,value:select.value || null})));
    wrap.append(select); root.append(wrap);
  }
}
function renderRows() {
  const root = $('rows'); root.replaceChildren();
  $('row-count').textContent = `(${presentation.view.rows.length})`;
  for (const row of presentation.view.rows) {
    const tr = make('tr'); tr.classList.toggle('selected', row.row_id === presentation.view.selection.row_id); tr.dataset.rowId = row.row_id;
    rowValues(row).forEach((value, index) => {
      const td = make('td');
      if (!index) {
        const button = make('button',value); button.setAttribute('aria-label', `Open ${row.dataset_id}, ${row.structure_id}, ${row.hypothesis_id}, ${row.result_id}, ${row.data.node_id}, occupancy ${atomData(row).occupancy}`);
        button.setAttribute('aria-pressed', String(row.row_id === presentation.view.selection.row_id));
        button.addEventListener('click', () => request(action('row',{row_id:row.row_id}))); td.append(button);
      } else td.textContent = value;
      tr.append(td);
    });
    // The full row is a pointer target; its first cell is the keyboard equivalent.
    tr.addEventListener('click', event => { if (!event.target.closest('button')) request(action('row',{row_id:row.row_id})); });
    root.append(tr);
  }
  if (!root.children.length) { const tr=make('tr'), td=make('td','No saved rows in this scope. Check the reports below for pending scan points.'); td.colSpan=12; tr.append(td); root.append(tr); }
  $('result-note').textContent = 'Reference-comparison rows show candidate q and B; reference values are in the inspector. — means absent, never zero. f′ is fixed in f″ trials.';
  const pending = $('pending'); pending.replaceChildren();
  for (const detail of presentation.view.details.filter(d => d.report)) {
    const report = detail.report;
    if (report.pending || report.failure) pending.append(make('p', `${detail.dataset_id} / ${detail.result_id}: ${report.pending ?? 0} pending points${report.failure ? '; saved failure — see report' : ''}.`, 'pending'));
    const fold = make('details'), summary = make('summary', `${detail.dataset_id} / ${detail.result_id} · Full saved report`);
    fold.append(summary, make('pre',JSON.stringify(report,null,2))); pending.append(fold);
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
    values(root, [['Occupancy q',number(a.occupancy)],['Reported B (Å²)',number(a.b_iso ?? a.reported_b_A2)],['Fixed f′ (e)',number(d.f_prime)],['Refined f″ (e)',number(d.f_double_prime)],['Reference f″ (e)',number(d.reference_f_double_prime)],['Wavelength (Å)',number(d.wavelength_A,5)]]);
    if (d.occupancy_vector) fold(root,'Complete trial occupancy vector',d.occupancy_vector);
    if (d.warning) root.append(make('p',d.warning,'note'));
    if (d.reference) {
      root.append(make('p','Human reference: coordinates, q and ADP snapshot. Stored anomalous values are ignored; reference coordinates are not overlaid.', 'note'));
      values(root,[['Reference q',number(d.reference.occupancy)],['Reference B (Å²)',number(d.reference.reported_b_A2)],['Displacement (Å)',number(d.cartesian_displacement_A)]]);
    }
    fold(root,'Exact saved row and provenance',row);
  } else root.append(make('p','Select a result row to inspect its trial values and source.', 'muted'));
  const atom = scene?.atoms.find(a => keyOf(a.key) === selectedAtom);
  if (atom) {
    root.append(make('h3','Coordinate atom'), make('p',atomLabel(atom.key),'scope'));
    root.append(make('p','Values from the candidate geometry model; the selected trial may use a different fixed q.', 'muted'));
    values(root,[['Element',atom.element],['XYZ (Å)',atom.xyz.map(v=>number(v)).join(', ')],['Model q',number(atom.occupancy)],['Model B (Å²)',number(atom.b_iso)],['ANISOU',atom.anisou ? 'Present' : 'Absent']]);
    fold(root,'Exact atom identity and state',atom);
  }
  if (scene) {
    root.append(make('h3','Recipe atoms'));
    const list = make('div',undefined,'atom-list');
    for (const node of scene.nodes.filter(n=>n.atom)) {
      const button=make('button',`${node.node_id}: ${atomLabel(node.atom.key)}`);
      button.setAttribute('aria-pressed',String(keyOf(node.atom.key)===selectedAtom));
      button.addEventListener('click',()=>{selectedAtom=keyOf(node.atom.key);drawScene();renderInspector();});list.append(button);
    }
    root.append(list);
    fold(root,'Saved restraint terms (distances and angles)',scene.restraints);
    fold(root,'Geometry source', {geometry_id:scene.geometry_id,model:scene.model,status:scene.status});
  }
}
function syncCamera() {
  const c = camera(); for (const k of ['zoom','yaw','pitch','context']) $(k).value = c[k];
}
function drawScene() {
  const root = $('scene'), scene = presentation?.scene; root.replaceChildren();
  if (!scene) { root.append(make('p','Choose a candidate or open a result row to see its verified coordinates.','empty')); $('geometry-status').textContent='No candidate selected'; return; }
  const c = camera(), atoms = visibleAtoms(scene,presentation.view.selection.site_id,c.context,selectedAtom);
  $('geometry-status').textContent = `${scene.dataset_id} / ${scene.hypothesis_id} · ${scene.status === "GEOMETRY_REVIEW" ? "Geometry awaiting review" : scene.status} · ${atoms.length} of ${scene.atoms.length} atoms`;
  if (!atoms.length) { root.append(make('p','No atoms in this view context. Choose Whole model.','empty')); return; }
  const width=root.clientWidth, height=root.clientHeight, project=projector(atoms,c,width,height);
  const canvas=svg('svg',{viewBox:`0 0 ${width} ${height}`,role:'group','aria-label':'Candidate atom coordinates and saved distance restraints'});
  const inventory=new Map(atoms.map(a=>[keyOf(a.key),a]));
  const nodes=new Map(scene.nodes.filter(n=>n.atom).map(n=>[n.node_id,n.atom]));
  const siteKeys=new Set((presentation.view.selection.site_id ? scene.site_atoms[presentation.view.selection.site_id] : scene.nodes.filter(n=>n.atom).map(n=>n.atom.key)).map(keyOf));
  for (const r of scene.restraints.filter(r=>r.enabled && r.kind==='distance' && r.status==='resolved')) {
    const endpoints=r.node_ids.map(n=>nodes.get(n)).map(a=>a && inventory.get(keyOf(a.key)));
    if (endpoints.some(a=>!a)) continue;
    const [a,b]=endpoints.map(a=>project(a.xyz));
    const line=svg('line',{x1:a[0],y1:a[1],x2:b[0],y2:b[1],stroke:'#80bbfa','stroke-width':1.5,'stroke-dasharray':'3 5'});
    const title=svg('title',{});title.textContent=`${r.restraint_id}: target ${r.target} ± ${r.sigma} ${r.unit}`;line.append(title);canvas.append(line);
  }
  const nodeLabels=new Map(scene.nodes.filter(n=>n.atom).map(n=>[keyOf(n.atom.key),n.node_id]));
  for (const atom of [...atoms].sort((a,b)=>project(a.xyz)[2]-project(b.xyz)[2])) {
    const key=keyOf(atom.key), [x,y]=project(atom.xyz), chosen=key===selectedAtom, site=siteKeys.has(key);
    const circle=svg('circle',{cx:x,cy:y,r:chosen?7:site?5:2.8,fill:chosen?'#ffc18c':site?'#80bbfa':'#7c8796',stroke:chosen?'#ffe0bb':'#202329','stroke-width':1.3,tabindex:0,role:'button','aria-label':atomLabel(atom.key),class:'svg-atom'});
    const title=svg('title',{});title.textContent=atomLabel(atom.key);circle.append(title);
    const pick=()=>{selectedAtom=key;drawScene();renderInspector();};
    circle.addEventListener('click',event=>{if(!dragMoved) pick();event.stopPropagation();});
    circle.addEventListener('keydown',event=>{if(['Enter',' '].includes(event.key)){event.preventDefault();pick();}});canvas.append(circle);
    if (nodeLabels.has(key) || chosen) { const label=svg('text',{x:x+9,y:y-8,fill:chosen?'#ffc18c':'#d7e6fa','font-size':11,'pointer-events':'none'});label.textContent=`${nodeLabels.get(key)||''} ${atom.element}`.trim();canvas.append(label); }
  }
  root.append(canvas);
}
function render() { $('campaign').textContent=presentation.campaign_label;renderNavigation();renderRows();syncCamera();drawScene();renderInspector(); }
$('all').addEventListener('click',()=>request({action:'reset'}));
$('toggle-inspector').addEventListener('click',()=>{const hidden=$('workbench').classList.toggle('no-inspector');$('toggle-inspector').textContent=hidden?'Show inspector':'Hide inspector';$('toggle-inspector').setAttribute('aria-expanded',String(!hidden));drawScene();});
for (const k of ['zoom','yaw','pitch']) $(k).addEventListener('input',()=>{camera()[k]=Number($(k).value);drawScene();});
$('context').addEventListener('change',()=>{camera().context=$('context').value;drawScene();});
$('fit').addEventListener('click',()=>{const context=camera().context;Object.assign(camera(),defaults(),{context});syncCamera();drawScene();});
let drag=null, dragMoved=false;
$('scene').addEventListener('pointerdown',event=>{if(event.button!==0)return;drag={x:event.clientX,y:event.clientY,yaw:camera().yaw,pitch:camera().pitch};dragMoved=false;});
window.addEventListener('pointermove',event=>{if(!drag)return;const dx=event.clientX-drag.x,dy=event.clientY-drag.y;if(Math.hypot(dx,dy)<4&&!dragMoved)return;dragMoved=true;camera().yaw=((drag.yaw+dx*.5+540)%360)-180;camera().pitch=Math.max(-89,Math.min(89,drag.pitch+dy*.5));syncCamera();drawScene();});
window.addEventListener('pointerup',()=>{drag=null;});
window.addEventListener('pointercancel',()=>{drag=null;});
new ResizeObserver(()=>{if(presentation)drawScene();}).observe($('scene'));
request();
