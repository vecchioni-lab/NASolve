import test from 'node:test';
import assert from 'node:assert/strict';
import {setImmediate as settle} from 'node:timers/promises';

test('inspection controls enable after navigation and apply explicit display levels',async t=>{
 class Element {
  children=[];dataset={};events={};disabled=false;value='';textContent='';
  classList={toggle(){},contains(){return false;},add(){}};
  append(...items){this.children.push(...items);}
  prepend(...items){this.children.unshift(...items);}
  replaceChildren(...items){this.children=items;}
  setAttribute(){}
  addEventListener(name,fn){this.events[name]=fn;}
  async fire(name){await this.events[name]?.({});}
 }
 const nodes=new Map();const get=id=>{if(!nodes.has(id))nodes.set(id,new Element());return nodes.get(id);};
 const original={document:globalThis.document,window:globalThis.window,ResizeObserver:globalThis.ResizeObserver,fetch:globalThis.fetch};
 t.after(()=>{for(const [key,value] of Object.entries(original)){if(value===undefined)delete globalThis[key];else globalThis[key]=value;}});
 globalThis.document={getElementById:get,createElement:()=>new Element(),createElementNS:()=>new Element(),querySelectorAll:()=>[]};
 globalThis.window={addEventListener(){}};globalThis.ResizeObserver=class{observe(){}};
 const shown={campaign_label:'Saved test',scene:{dataset_id:'one',structure_id:'s',hypothesis_id:'h',geometry_id:'g',atoms:[],nodes:[],restraints:[],site_atoms:{},inspection:{id:'trial',maps:[{type:'mFo-DFc',sigma:3,stage:'XYZ geometry',labels:['FOFC','PHIFOFC'],source:{anchor:'run',relative_path:'maps/diff.mtz',sha256:'a'.repeat(64)}}]}},view:{selection:{dataset_id:'one',structure_id:'s',hypothesis_id:'h',site_id:null,result_id:null,row_id:null},options:Object.fromEntries(['dataset_id','structure_id','hypothesis_id','site_id','result_id'].map(k=>[k,[]])),rows:[],details:[],selected_row:null}};
 const calls=[];
 globalThis.fetch=async(kind,options)=>{
  if(kind==='view')return {ok:true,json:async()=>shown};
  const request=JSON.parse(options.body);calls.push({kind,request});
  return {ok:true,json:async()=>kind==='coot'?{status:'READY',version:'test'}:{note:'Display only.',radius_A:6,spacing_A:.6,layers:[{type:'mFo-DFc',level_sigma:-request.sigma_levels['mFo-DFc'],segments:[],truncated:false}]}};
 };
 await import('../src/nasolve/metal/web/app.mjs');await settle();
 assert.equal(get('load-maps').disabled,false);
 assert.equal(get('open-coot').disabled,false);
 const level=get('map-level-controls').children[0].children[0];level.value='1.5';await level.fire('input');
 await get('apply-map-levels').fire('click');
 assert.deepEqual(calls.at(-1),{kind:'maps',request:{selection:shown.view.selection,center_key:null,sigma_levels:{'mFo-DFc':1.5}}});
 assert.match(get('map-note').textContent,/-1.5σ/);
 assert.equal(get('apply-map-levels').disabled,false);
 await get('open-coot').fire('click');assert.equal(calls.at(-1).request.sigma_levels['mFo-DFc'],1.5);
 const invalid=get('map-level-controls').children[0].children[0];invalid.value='0';await invalid.fire('input');
 const count=calls.length;await get('apply-map-levels').fire('click');assert.equal(calls.length,count);assert.match(get('message').textContent,/positive sigma/);
 await get('reset-map-levels').fire('click');await settle();assert.equal(calls.at(-1).request.sigma_levels['mFo-DFc'],3);
 assert.equal(shown.scene.inspection.maps[0].sigma,3);
});
