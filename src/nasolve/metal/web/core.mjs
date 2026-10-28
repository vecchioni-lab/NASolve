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
export function projector(atoms, camera, width, height) {
  if (!atoms.length) return () => [width/2, height/2, 0];
  const low = [0,1,2].map(i => Math.min(...atoms.map(a => a.xyz[i])));
  const high = [0,1,2].map(i => Math.max(...atoms.map(a => a.xyz[i])));
  const center = low.map((v,i) => (v + high[i])/2);
  const radius = Math.max(1, ...atoms.map(a => Math.hypot(...a.xyz.map((v,i) => v-center[i]))));
  const scale = Math.min(width, height) * .38 / radius * camera.zoom;
  const yaw = camera.yaw*Math.PI/180, pitch = camera.pitch*Math.PI/180;
  return xyz => {
    const [x,y,z] = xyz.map((v,i) => v-center[i]);
    const xx = x*Math.cos(yaw) + z*Math.sin(yaw), zz = -x*Math.sin(yaw) + z*Math.cos(yaw);
    return [width/2 + xx*scale, height/2 - (y*Math.cos(pitch)-zz*Math.sin(pitch))*scale,
      y*Math.sin(pitch)+zz*Math.cos(pitch)];
  };
}
