"""Explicit compact observation and replay of native directed ASU repulsion.

This proves captured arithmetic, not neighbour generation, chemical authority or
physical geometry. The identity-only C127 policy remains a separate contract.
"""
from collections import defaultdict
from inspect import getsource
import hashlib
import json
import math

from .cif_captured_geometry import _number, _site, review_captured_geometry
from .cif_candidate_usability import energy_inventory_checks
from .cif_nonbonded_cache_audit import _close, _vector

POLICY_ID = 'cif-native-nonbonded-asu-attribution-v1'
MAX_KERNEL_CALLS = 20000
MAX_PAIRS = 9999
PAIR_COLUMNS = ['kind','i_seq','j_seq','j_sym','vdw_distance']
KERNEL_COLUMNS = ['raw_residual','gradient_0_x','gradient_0_y','gradient_0_z']


def validate_policy(policy, *, enabled):
    if policy is not None and (type(policy) is not str or policy != POLICY_ID or enabled is not True):
        raise ValueError('Require an explicit supported nonbonded capture policy')


def membership_digest(pairs, mappings, cell):
    """Bind ordered rows and exact mappings; multiplicity is never deduplicated."""
    return hashlib.sha256(json.dumps([pairs,mappings,cell],separators=(',',':'),allow_nan=False).encode()).hexdigest()


def capture_asu_pairs(geo, points):
    """Embedded in a fresh isolated native worker; inspect actual energy pairs."""
    from cctbx import geometry_restraints as gr
    from cctbx.array_family import flex
    from cctbx.geometry_restraints import flags
    sites=flex.vec3_double(points);snapshots=[];calls=0;shared=None
    for repeat in range(2):
        energy=geo.energies_sites(sites_cart=sites,flags=flags.flags(default=True),compute_gradients=True,normalization=False)
        nb,fn=energy.nonbonded_proxies,energy.nonbonded_function
        if nb is None or not isinstance(fn,gr.prolsq_repulsion_function):
            raise RuntimeError('Unsupported ASU nonbonded function or pair inventory')
        count=len(nb.simple)+len(nb.asu)
        if count>9999 or calls+count+1>20000:
            raise RuntimeError('Complete ASU pair snapshot exceeds bounded kernel allowance')
        parameters={'class':'prolsq_repulsion_function',**{k:float(getattr(fn,k)) for k in ('c_rep','k_rep','irexp','rexp')}}
        am=nb.asu_mappings();cell=[float(v) for v in am.unit_cell().parameters()]
        pairs=[];kernels=[];mapping={}
        for kind,proxies in [('simple',nb.simple),('asu',nb.asu)]:
            for proxy in proxies:
                if kind=='simple':
                    if proxy.rt_mx_ji is not None:
                        raise RuntimeError('Transformed simple nonbonded proxy is unsupported')
                    i,j=map(int,proxy.i_seqs);image=0
                    restraint=gr.nonbonded_prolsq(sites_cart=sites,proxy=proxy,function=fn)
                else:
                    i,j,image=int(proxy.i_seq),int(proxy.j_seq),int(proxy.j_sym)
                    restraint=gr.nonbonded_prolsq(sites_cart=sites,asu_mappings=am,proxy=proxy,function=fn)
                    for atom,sym in ((i,0),(j,image)):
                        if (atom,sym) not in mapping:
                            rt=am.get_rt_mx(atom,sym)
                            mapping[atom,sym]=[atom,sym,[float(v) for v in rt.r().as_double()],
                                [float(v) for v in rt.t().as_double()],[float(v) for v in am.r_inv_cart(atom,sym)]]
                calls+=1
                gradients=[[float(v) for v in g] for g in restraint.gradients()]
                if gradients[1]!=[-v for v in gradients[0]]:
                    raise RuntimeError('Native pair endpoint gradients are not opposite')
                pairs.append([kind,i,j,image,float(proxy.vdw_distance)])
                kernels.append([float(restraint.residual()),*gradients[0]])
        mappings=[mapping[k] for k in sorted(mapping)]
        observed=(pairs,mappings,cell,parameters)
        if shared is None:shared=observed
        elif observed!=shared:raise RuntimeError('Fixed native ASU membership, mapping or function changed')
        gradient=flex.vec3_double(len(points),(0.,0.,0.));calls+=1
        target=gr.nonbonded_residual_sum(sites_cart=sites,sorted_asu_proxies=nb,gradient_array=gradient,function=fn)
        snapshots.append(dict(membership_sha256=membership_digest(pairs,mappings,cell),
            target=float(energy.target),gradient=[float(v) for v in energy.gradients.as_double()],
            proxy_counts={k:v for k,v in vars(energy).items() if k.startswith('n_') and k.endswith('_proxies') and (v is None or isinstance(v,int))},
            nonbonded_target=float(target),nonbonded_gradient=[float(v) for v in gradient.as_double()],kernels=kernels))
    if points!=[[float(v) for v in p] for p in sites]:raise RuntimeError('ASU capture moved coordinates')
    pairs,mappings,cell,parameters=shared
    return dict(schema_version=1,policy_id='cif-native-nonbonded-asu-attribution-v1',status='RECORDED',normalization=False,
        symmetry_scope='DIRECTED_ASU_AND_IDENTITY_SIMPLE',evaluation_calls=2,pair_kernel_calls=calls,max_pair_kernel_calls=20000,
        pair_columns=['kind','i_seq','j_seq','j_sym','vdw_distance'],kernel_columns=['raw_residual','gradient_0_x','gradient_0_y','gradient_0_z'],
        pairs=pairs,mappings=mappings,unit_cell=cell,function_parameters=parameters,snapshots=snapshots)


def native_asu_worker(base):
    header='try:\n    from iotbx import phil\n';token='    report["energy_inventory"]["status"]="RECORDED"\n'
    if base.count(header)!=1 or base.count(token)!=1 or 'nonbonded_inventory' in base:
        raise ValueError('Unsupported native energy worker for ASU capture')
    helpers=getsource(membership_digest)+'\n'+getsource(capture_asu_pairs)
    return base.replace(header,helpers+'\n'+header).replace(token,token+'    report["nonbonded_inventory"] = capture_asu_pairs(geo, original_sites)\n')


def _need(condition, message='Incomplete or inconsistent directed ASU evidence'):
    if not condition:raise ValueError(message)


def _values(values, length):
    _need(isinstance(values,list) and len(values)==length)
    return [_number(v) for v in values]


def _mv(matrix, vector):
    return [sum(matrix[3*i+j]*vector[j] for j in range(3)) for i in range(3)]


def _mm(left, right):
    return [sum(left[3*i+k]*right[3*k+j] for k in range(3)) for i in range(3) for j in range(3)]


def _transpose(matrix):
    return [matrix[3*j+i] for i in range(3) for j in range(3)]


def _cell_matrices(cell):
    a,b,c,alpha,beta,gamma=_values(cell,6)
    _need(min(a,b,c)>0 and all(0<v<180 for v in (alpha,beta,gamma)), 'Invalid captured unit cell')
    ca,cb,cg=(math.cos(math.radians(v)) for v in (alpha,beta,gamma));sg=math.sin(math.radians(gamma))
    z2=1-cb*cb-((ca-cb*cg)/sg)**2
    _need(z2>0, 'Degenerate captured unit cell')
    o=[a,b*cg,c*cb,0.,b*sg,c*(ca-cb*cg)/sg,0.,0.,c*math.sqrt(z2)]
    f=[1/o[0],-o[1]/(o[0]*o[4]),(o[1]*o[5]-o[2]*o[4])/(o[0]*o[4]*o[8]),
       0.,1/o[4],-o[5]/(o[4]*o[8]),0.,0.,1/o[8]]
    _need(all(math.isfinite(v) for v in o+f))
    return o,f


def _mapped_sites(mappings, cell, points):
    _need(isinstance(mappings,list) and len(mappings)<=2*MAX_PAIRS)
    o,f=_cell_matrices(cell);result={};identity=[1.,0.,0.,0.,1.,0.,0.,0.,1.]
    previous=None
    for row in mappings:
        _need(isinstance(row,list) and len(row)==5)
        i,image,r,t,inverse=row
        _need(type(i) is int and 0<=i<len(points) and type(image) is int and image>=0)
        key=i,image;_need(key not in result and (previous is None or previous<key));previous=key
        r,t,inverse=_values(r,9),_values(t,3),_values(inverse,9)
        rotation=_mm(_mm(o,r),f)
        _need(_vector(_mm(rotation,_transpose(rotation)),identity)
              and _vector(inverse,_transpose(rotation)), 'Symmetry mapping or gradient adjoint is inconsistent')
        rotated=_mv(r,_mv(f,points[i]));mapped=_mv(o,[v+w for v,w in zip(rotated,t)])
        _need(all(math.isfinite(v) for v in mapped))
        result[key]=(mapped,inverse)
    return result


def review_native_asu(native):
    """Replay every observed kernel and directed contribution without native code."""
    from .cif_native_nonbonded import _pair_values
    try:
        review_captured_geometry(native)
        _need(all(energy_inventory_checks(native).values()), 'Require fixed native energy evidence')
        q=native['nonbonded_inventory'];pairs=q['pairs'];snapshots=q['snapshots'];atoms=native['atoms']
        _need(type(q['schema_version']) is int and q['schema_version']==1 and q['policy_id']==POLICY_ID
            and q['status']=='RECORDED' and q['normalization'] is False
            and q['symmetry_scope']=='DIRECTED_ASU_AND_IDENTITY_SIMPLE'
            and type(q['evaluation_calls']) is int and q['evaluation_calls']==2
            and type(q['max_pair_kernel_calls']) is int and q['max_pair_kernel_calls']==MAX_KERNEL_CALLS
            and q['pair_columns']==PAIR_COLUMNS and q['kernel_columns']==KERNEL_COLUMNS
            and isinstance(snapshots,list) and len(snapshots)==2
            and isinstance(pairs,list) and len(pairs)<=MAX_PAIRS)
        _need(type(q['pair_kernel_calls']) is int and q['pair_kernel_calls']==2*(len(pairs)+1)<=MAX_KERNEL_CALLS)
        points=native['geometry']['sites_cart_exact'];mapped=_mapped_sites(q['mappings'],q['unit_cell'],points)
        params=q['function_parameters']
        _need(set(params)=={'class','c_rep','k_rep','irexp','rexp'} and params['class']=='prolsq_repulsion_function'
            and all(_number(params[k])>0 for k in ('c_rep','k_rep','irexp','rexp')))
        digest=membership_digest(pairs,q['mappings'],q['unit_cell']);prepared=[];used=set();asu_started=False
        for proxy_index,row in enumerate(pairs):
            _need(isinstance(row,list) and len(row)==5)
            kind,i,j,image,vdw=row
            _need(kind in ('simple','asu') and type(i) is int and type(j) is int and 0<=i<len(atoms) and 0<=j<len(atoms)
                  and type(image) is int and image>=0 and _number(vdw)>0)
            if kind=='simple':
                _need(not asu_started and image==0 and i!=j)
                a,b=points[i],points[j];weight=1.;mi=mj=None
            else:
                asu_started=True;used.update(((i,0),(j,image)))
                a,mi=mapped[i,0];b,mj=mapped[j,image];weight=1. if image==0 else .5
            distance,residual,raw=_pair_values(a,b,vdw,params)
            _need(all(math.isfinite(v) for v in (distance,residual,*raw)))
            additions=[(i,raw[:3]),(j,raw[3:])] if kind=='simple' else [(i,_mv(mi,raw[:3]))]+([] if image else [(j,_mv(mj,raw[3:]))])
            prepared.append((distance,residual,raw,weight,additions))
        _need(set(mapped)==used, 'Mapping inventory differs from exact observed pair references')
        energy=native['energy_inventory']['snapshots'][-1]
        for snapshot in snapshots:
            _need(snapshot['membership_sha256']==digest and isinstance(snapshot['kernels'],list) and len(snapshot['kernels'])==len(pairs))
            gradient=[0.]*(3*len(atoms));total=0.
            for values,(_,residual,raw,weight,additions) in zip(snapshot['kernels'],prepared):
                values=_values(values,4)
                _need(_close(values[0],residual) and _vector(values[1:],raw[:3]), 'Captured pair kernel differs from mapped coordinates/function')
                total+=weight*residual
                for atom,g in additions:
                    for axis in range(3):gradient[3*atom+axis]+=g[axis]
            for field in ('gradient','nonbonded_gradient'):_values(snapshot[field],3*len(atoms))
            _need(_close(total,_number(snapshot['nonbonded_target'])) and _vector(gradient,snapshot['nonbonded_gradient']),
                  'Directed pair contributions differ from native container')
            _need(snapshot['proxy_counts']==energy['proxy_counts']
                  and type(snapshot['proxy_counts']['n_nonbonded_proxies']) is int
                  and snapshot['proxy_counts']['n_nonbonded_proxies']==len(pairs)
                  and _close(_number(snapshot['target']),energy['target']) and _vector(snapshot['gradient'],energy['gradient'])
                  and _close(total,_number(energy['terms']['nonbonded_residual_sum'])), 'Pair evidence differs from full native manager')
        # Values are independently observed twice, retained rather than replaced by a pass flag.
        for a,b in zip(snapshots[0]['kernels'],snapshots[1]['kernels']):_need(_vector(a,b))
        measurements=[];groups=defaultdict(lambda:dict(pair_count=0,positive_residual_pairs=0,residual=0.))
        for proxy_index,(row,values) in enumerate(zip(pairs,prepared)):
            kind,i,j,image,vdw=row;distance,residual,raw,weight,additions=values
            sites=[_site(atoms[k]) for k in (i,j)];key=tuple(sorted(set(sites)))
            contribution={}
            for atom,g in additions:
                old=contribution.setdefault(atom,[0.,0.,0.])
                for axis in range(3):old[axis]+=g[axis]
            measurements.append(dict(proxy_index=proxy_index,kind=kind,i_seqs=[i,j],image_j=image,
                atoms=[atoms[i]['label'],atoms[j]['label']],sites=sites,distance=distance,vdw_distance=vdw,overlap=vdw-distance,
                raw_residual=residual,residual_weight=weight,residual=weight*residual,
                gradient_norm=math.hypot(*(v for g in contribution.values() for v in g)),coincident=distance==0,
                same_site=len(key)==1,self_image=kind=='asu' and i==j))
            group=groups[key];group['pair_count']+=1;group['positive_residual_pairs']+=residual>0;group['residual']+=weight*residual
        return dict(schema_version=1,policy_id=POLICY_ID,status='REVIEW',analysis_completed=True,pair_count=len(pairs),
            asu_pair_count=sum(r[0]=='asu' for r in pairs),self_image_pair_count=sum(r['self_image'] for r in measurements),
            positive_residual_pairs=sum(r['raw_residual']>0 for r in measurements),total_residual=snapshots[-1]['nonbonded_target'],
            function_parameters=dict(params),measurements=measurements,worst=sorted(measurements,key=lambda r:(-r['residual'],r['proxy_index']))[:20],
            by_site_pair=sorted((dict(sites=list(k),**v) for k,v in groups.items()),key=lambda r:(-r['residual'],r['sites'])),
            pair_sum_and_gradient_replay=True,fixed_manager_repeats=True,native_execution='NOT_RUN',
            symmetry_scope='DIRECTED_ASU_AND_IDENTITY_SIMPLE',chemical_qualification='NOT_ESTABLISHED',geometry_accepted=False,automatic_adoption=False,
            limitations=['Observed directed pair rows retain native image multiplicity; site buckets name source residues, not unique physical contacts.',
                'Native exclusions, mappings and parameters are observations, not independent chemical authority or neighbour reconstruction.',
                'No symmetry-aware covalent optimizer, clashscore, refinement or physical acceptance threshold is established.',
                'Exact receipts, frozen inputs and maintained worker binding require separate validation.'])
    except (KeyError,TypeError,IndexError,OverflowError,ZeroDivisionError) as exc:
        raise ValueError('Incomplete native ASU attribution evidence') from exc
