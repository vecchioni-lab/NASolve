import test from 'node:test';
import assert from 'node:assert/strict';
import {recipeRows, geometrySnapshots, autoCamera, groupSnapshots, labelLayout, ratio, keyOf, number, projector, rowValues, scopeKey, visibleAtoms} from '../src/nasolve/metal/web/core.mjs';
const key = (name, residue='1', altloc='') => ({chain_id:'A',residue_id:residue,component_id:'DF',model_id:'1',atom_name:name,altloc,insertion_code:'',segment_id:'',symmetry:'x,y,z'});
const atoms = [
 {key:key('S1'),xyz:[0,0,0]}, {key:key('C1'),xyz:[1,0,0]},
 {key:key('S1','2'),xyz:[0,1,1]}, {key:key('S1','1','B'),xyz:[0,0,2]}
];
const scene = {dataset_id:'one',structure_id:'model',hypothesis_id:'mixed',geometry_id:'hash',
 atoms,nodes:[{node_id:'donor',atom:atoms[0]}],site_atoms:{pair:[atoms[0].key]}};
test('exact atom identity survives property order but distinguishes alternate and residue',()=>{
 assert.equal(keyOf(atoms[0].key),keyOf(Object.fromEntries(Object.entries(atoms[0].key).reverse())));
 assert.notEqual(keyOf(atoms[0].key),keyOf(atoms[2].key));
 assert.notEqual(keyOf(atoms[0].key),keyOf(atoms[3].key));
});
test('view expansion retains exact membership and never changes the recipe',()=>{
 const before=JSON.stringify(scene);
 assert.deepEqual(visibleAtoms(scene,'pair','site'),[atoms[0]]);
 assert.deepEqual(visibleAtoms(scene,'pair','residues'),atoms.slice(0,2));
 assert.deepEqual(visibleAtoms(scene,null,'residues'),atoms.slice(0,2));
 assert.deepEqual(visibleAtoms(scene,'pair','model'),atoms);
 assert.equal(JSON.stringify(scene),before);
});
test('3D projection exposes depth under rotation and zoom preserves camera center',()=>{
 const camera={zoom:1,yaw:0,pitch:0};
 const front=projector(atoms,camera,600,400), rotated=projector(atoms,{...camera,yaw:90},600,400);
 assert.equal(front([0,0,0])[0],front([0,0,2])[0]);
 assert.notEqual(rotated([0,0,0])[0],rotated([0,0,2])[0]);
 const zoomed=projector(atoms,{...camera,zoom:2},600,400);
 assert.ok(Math.abs(zoomed([0,0,0])[0]-300-2*(front([0,0,0])[0]-300))<1e-10);
 assert.deepEqual(atoms[0].xyz,[0,0,0]);
});
test('absent anomalous/reference values remain absent; actual zero is rendered',()=>{
 assert.equal(number(null),'—');assert.equal(number(undefined),'—');assert.equal(number(0),'0.000');
 const row={dataset_id:'one',hypothesis_id:'mixed',result_id:'reference',data:{node_id:'m1',candidate:{element:'Au',occupancy:.6,reported_b_A2:21}}};
 assert.deepEqual(rowValues(row).slice(6),['0.60','21.00','—','—','—','—']);
});
test('camera keys cannot collide across dataset or geometry identity',()=>{
 assert.notEqual(scopeKey(scene),scopeKey({...scene,dataset_id:'two'}));
 assert.notEqual(scopeKey(scene),scopeKey({...scene,geometry_id:'new-hash'}));
});

test('an unassigned selected scatterer stays visible without joining a recipe site',()=>{
 const before=JSON.stringify(scene), selected=keyOf(atoms[2].key);
 assert.deepEqual(visibleAtoms(scene,'pair','site',selected),[atoms[0],atoms[2]]);
 assert.deepEqual(visibleAtoms(scene,null,'residues',selected),atoms.slice(0,3));
 assert.equal(JSON.stringify(scene),before);
});


test('automatic orientation opens an edge-on plane and fits the available viewport',()=>{
 const edge=[[-5,0,-2],[-5,0,2],[5,0,-2],[5,0,2]].map(xyz=>({xyz}));
 const c=autoCamera(edge), p=projector(edge,c,800,400), points=edge.map(a=>p(a.xyz));
 assert.ok(Math.max(...points.map(a=>a[0]))-Math.min(...points.map(a=>a[0]))>500);
 assert.ok(Math.max(...points.map(a=>a[1]))-Math.min(...points.map(a=>a[1]))>150);
 const pan=projector(edge,{...c,panX:30,panY:-20},800,400);
 assert.ok(Math.abs(pan(edge[0].xyz)[0]-p(edge[0].xyz)[0]-30)<1e-9);
 assert.ok(Math.abs(pan(edge[0].xyz)[1]-p(edge[0].xyz)[1]+20)<1e-9);
 const roll=projector(edge,{...c,roll:90},800,400);
 assert.notDeepEqual(roll(edge[0].xyz),p(edge[0].xyz));
});
test('snapshot boxes share actual trials and retain source aliases without duplicate metals',()=>{
 const r=(result,node,trial='same',dataset='one')=>({row_id:result+node+dataset,dataset_id:dataset,structure_id:'s',hypothesis_id:'h',result_id:result,data:{trial_id:trial,node_id:node,element:'Ag'}});
 const groups=groupSnapshots([r('profile','m1'),r('profile','m2'),r('scan','m1'),r('scan','m2'),r('profile','m1','same','two')]);
 assert.equal(groups.length,2);assert.equal(groups[0].sites.length,2);
 assert.equal(groups[0].sites[0].rows.length,2);assert.deepEqual(groups[0].sources,['profile','scan']);
 assert.equal(ratio({f_double_prime:4,reference_f_double_prime:2}),2);
 assert.equal(ratio({f_double_prime:4,reference_f_double_prime:0}),null);
});
test('labels disappear when distant and do not overlap at close range',()=>{
 const items=[{key:'a',x:50,y:50,element:'N',name:'N3',priority:1},{key:'b',x:51,y:50,element:'Ag',name:'AG',priority:2}];
 assert.deepEqual(labelLayout(items,3,200,150),[]);
 const labels=labelLayout(items,40,200,150);assert.ok(labels.length);
 for(let i=0;i<labels.length;i++)for(let j=i+1;j<labels.length;j++) {
   const a=labels[i],b=labels[j];assert.ok(a.x+a.width<=b.x||b.x+b.width<=a.x||a.y+a.height<=b.y||b.y+b.height<=a.y);
 }
 assert.ok(labels.some(l=>l.text==='AG'));
});


test('recipe inspection keeps a donor-centred zero angle and exact atom order',()=>{
 const s={nodes:[{node_id:'m',atom:atoms[0]},{node_id:'d1',atom:atoms[1]},{node_id:'d2',atom:atoms[2]}],
  restraints:[{restraint_id:'angle',kind:'angle',node_ids:['m','d1','d2'],target:0,sigma:3,enabled:false}]};
 const before=JSON.stringify(s),rows=recipeRows(s);
 assert.equal(rows[0].vertex,'d1');assert.equal(rows[0].target,0);assert.equal(rows[0].enabled,false);
 assert.deepEqual(rows[0].keys,atoms.slice(0,3).map(a=>a.key));assert.equal(JSON.stringify(s),before);
});
test('one geometry table retains distinct trial groups and cross-dataset boundaries',()=>{
 const r=(trial,node,dataset='one')=>({row_id:trial+node+dataset,dataset_id:dataset,structure_id:'s',hypothesis_id:'h',result_id:'scan',data:{trial_id:trial,node_id:node}});
 const groups=geometrySnapshots([r('a','m1'),r('a','m2'),r('b','m1'),r('b','m2'),r('a','m1','two')]);
 assert.equal(groups.length,2);assert.equal(groups[0].trials.length,2);
 assert.equal(groups[0].trials[0].sites.length,2);assert.equal(groups[1].trials.length,1);
});
