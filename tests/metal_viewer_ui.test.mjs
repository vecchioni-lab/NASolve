import test from 'node:test';
import assert from 'node:assert/strict';
import {keyOf, number, projector, rowValues, scopeKey, visibleAtoms} from '../src/nasolve/metal/web/core.mjs';
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
