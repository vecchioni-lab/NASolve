"""Bounded display-only density contours from exact captured complex coefficients.

Run under the discovered Phenix Python. No fitting, scaling of observations,
coefficient generation, coordinate editing or site interpretation is performed.
"""
import itertools
import json
import math
from pathlib import Path
import sys


def contours(values, origin, spacing, level, limit=24000):
    n=len(values);segments={};clipped=False
    offsets=((0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1))
    tetra=((0,1,2,6),(0,2,3,6),(0,3,7,6),(0,7,4,6),(0,4,5,6),(0,5,1,6))
    for i,j,k in itertools.product(range(n-1),repeat=3):
        pos=[(origin[0]+(i+a)*spacing,origin[1]+(j+b)*spacing,origin[2]+(k+c)*spacing) for a,b,c in offsets]
        val=[values[i+a][j+b][k+c] for a,b,c in offsets]
        if min(val)>=level or max(val)<level:continue
        for t in tetra:
            points=[]
            for a,b in itertools.combinations(t,2):
                if (val[a]<level)==(val[b]<level):continue
                f=(level-val[a])/(val[b]-val[a]);points.append(tuple(pos[a][x]+f*(pos[b][x]-pos[a][x]) for x in range(3)))
            if len(points)<3:continue
            if len(points)==4:
                centre=[sum(p[x] for p in points)/4 for x in range(3)]
                u=[points[0][x]-centre[x] for x in range(3)]
                other=[points[1][x]-centre[x] for x in range(3)]
                normal=[u[1]*other[2]-u[2]*other[1],u[2]*other[0]-u[0]*other[2],u[0]*other[1]-u[1]*other[0]]
                v=[normal[1]*u[2]-normal[2]*u[1],normal[2]*u[0]-normal[0]*u[2],normal[0]*u[1]-normal[1]*u[0]]
                norm=math.sqrt(sum(x*x for x in v))/max(1e-20,math.sqrt(sum(x*x for x in u)))
                points.sort(key=lambda p:math.atan2(sum((p[x]-centre[x])*v[x] for x in range(3))/max(norm,1e-20),sum((p[x]-centre[x])*u[x] for x in range(3))))
            for a,b in zip(points,points[1:]+points[:1]):
                a=tuple(round(x,4) for x in a);b=tuple(round(x,4) for x in b)
                if a!=b:segments[tuple(sorted((a,b)))]=[a,b]
                if len(segments)>=limit:return list(segments.values()),True
    return list(segments.values()),clipped


def main(root):
    from iotbx import reflection_file_reader
    from phenix import phenix_info
    import hashlib
    request=json.loads((root/'request.json').read_text());centre=request['centre'];spacing=.6;radius=6.;n=21
    origin=[x-radius for x in centre];layers=[]
    for m in request['maps']:
        arrays=reflection_file_reader.any_reflection_file(str(root/m['filename'])).as_miller_arrays()
        matches=[a for a in arrays if a.is_complex_array() and a.info().labels==m['labels']]
        if len(matches)!=1:raise ValueError('Exact complex map labels not found')
        coeff=matches[0];uc=coeff.unit_cell()
        density=coeff.fft_map(resolution_factor=.25).apply_sigma_scaling().real_map_unpadded()
        values=[[[float(density.eight_point_interpolation(uc.fractionalize([origin[0]+i*spacing,origin[1]+j*spacing,origin[2]+k*spacing]))) for k in range(n)] for j in range(n)] for i in range(n)]
        signs=(1,-1) if m['difference'] else (1,)
        for sign in signs:
            segments,clipped=contours(values,origin,spacing,sign*m['sigma'])
            layers.append(dict(m,level_sigma=sign*m['sigma'],colour=m['colour'] if sign>0 else '#ce8790',segments=segments,truncated=clipped))
    result=dict(kind='metal-density-preview',schema_version=1,centre=centre,radius_A=radius,spacing_A=spacing,
                normalization='whole_cell_sigma',layers=layers,
                native_version='-'.join(str(v) for v in phenix_info.version_and_release_tag() if v),
                worker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                note='Coarse local display contours; symmetry-periodic interpolation. Use Coot for full-resolution map inspection. No map-derived atom counts.')
    (root/'preview.json').write_text(json.dumps(result,allow_nan=False,separators=(',',':')))

if __name__=='__main__':main(Path(sys.argv[1]))
