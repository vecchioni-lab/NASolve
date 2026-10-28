"""Local read-only presentation of a verified workbench snapshot.

The browser renders coordinates and requests navigation from the existing Python
controller. It has no artifact, job, editing, or checkpoint-writing endpoint.
"""
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
import json
from pathlib import Path
import secrets

from .context import parse_pdb
from .chemistry import dictionaries, display_connections
from .environment import calibrate_b
from .materialize import _json, _source
from .recipe import RecipeError, canonical
from .workbench import Workbench, _fields, open_workbench


@dataclass(frozen=True)
class Viewer:
    workbench: Workbench
    _scenes: str = field(repr=False)

    def present(self, selection=None):
        if selection is None:
            selection = self.workbench.initial_selection()
            rows = self.workbench.to_dict()['rows']
            if rows:
                selection = self.workbench.select_row(selection, rows[0]['row_id'])
            else:
                selection = self._defaults(selection)
        view = self.workbench.view(selection)
        scene = next((s for s in json.loads(self._scenes) if all(
            s[k] == selection[k] for k in ('dataset_id','structure_id','hypothesis_id'))), None)
        catalog = self.workbench.to_dict()['catalog']
        return dict(kind='metal-workbench-presentation', schema_version=1,
                    campaign_label=catalog['label'], catalog_id=catalog['catalog_id'], view=view, scene=scene)

    def _defaults(self, selection):
        # Catalog order is a browsing convenience, never a scientific ranking.
        for field in ('dataset_id','structure_id','hypothesis_id'):
            view=self.workbench.view(selection)
            if selection[field] is None and view['options'][field]:
                selection=self.workbench.select(selection,field,view['options'][field][0][field])
        return selection

    def navigate(self, message):
        if not isinstance(message, dict):
            raise RecipeError('Require a navigation object')
        action = message.get('action')
        if action == 'reset':
            _fields(message, {'action'}, 'reset')
            selection = self.workbench.initial_selection()
        elif action == 'select':
            _fields(message, {'action','selection','field','value'}, 'select')
            selection = self.workbench.select(message['selection'], message['field'], message['value'])
            if message['value'] is not None and message['field'] in {'dataset_id','structure_id','hypothesis_id'}:
                selection = self._defaults(selection)
        elif action == 'row':
            _fields(message, {'action','selection','row_id'} | ({'site_id'} if 'site_id' in message else set()), 'row')
            selection = self.workbench.select_row(message['selection'], message['row_id'], site_id=message.get('site_id'))
        else:
            raise RecipeError('Unsupported navigation action')
        return self.present(selection)


def open_viewer(catalog, mounts):
    """Replay all scientific evidence, then freeze checked coordinates/overlays.

    The existing workbench schema is unchanged. Scenes are presentation values,
    with exact atom keys, saved terms and separately marked display connectivity.
    """
    workbench = open_workbench(catalog, mounts)
    scenes = []
    for dataset in workbench.to_dict()['catalog']['datasets']:
        root = Path(mounts[dataset['dataset_id']]).expanduser().resolve()
        for structure in dataset['structures']:
            run = root / structure['run']['relative_path']
            for hypothesis in structure['hypotheses']:
                geometry = _json(_source(hypothesis['geometry'], run))
                raw = _source(geometry['files']['model'], run)
                model = parse_pdb(raw)
                preview = _json(_source(geometry['files']['preview'], run))
                states = model.to_dict()['atomic_state']
                atoms = [dict(atom.to_dict(), **{k:v for k,v in state.items() if k != 'key'})
                         for atom, state in zip(model.snapshot.atoms, states)]
                resources=[(ref['relative_path'],_source(ref,run)) for ref in geometry['inputs']['restraints']]
                chemistry={};chemistry_note=None
                try:chemistry=dictionaries(resources)
                except RecipeError as exc:chemistry_note=str(exc)
                parent=_json(_source(geometry['parent']['manifest'],run))
                preparation=[]
                for site in parent['sites']:
                    for policy in ('base-mean','donor-mean'):
                        try:
                            report,_=calibrate_b(raw,parent['sites'],preview,[site['node_id']],policy,resources=resources)
                            preparation.append(dict(status='PREVIEW_ONLY',**report['sites'][0]))
                        except RecipeError as exc:
                            preparation.append(dict(node_id=site['node_id'],policy=policy,status='UNAVAILABLE',reason=str(exc)))
                scenes.append(dict(dataset_id=dataset['dataset_id'], structure_id=structure['structure_id'],
                    hypothesis_id=hypothesis['hypothesis_id'], geometry_id=geometry['geometry_id'],
                    model=geometry['files']['model'], status=geometry['status'], atoms=atoms,
                    nodes=preview['nodes'], restraints=preview['restraints'],
                    connections=display_connections(atoms,chemistry),connectivity_note=chemistry_note,
                    b_environment=preparation,
                    site_atoms={s['site_id']:s['atoms'] for s in hypothesis['sites']}))
    return Viewer(workbench, canonical(scenes))


def assets():
    """Fixed packaged assets only; never resolve an HTTP path on the filesystem."""
    root = files('nasolve.metal').joinpath('web')
    return {name: (root.joinpath(name or 'index.html').read_bytes(), mime) for name, mime in
            [('', 'text/html; charset=utf-8'), ('style.css','text/css; charset=utf-8'),
             ('app.mjs','text/javascript; charset=utf-8'), ('core.mjs','text/javascript; charset=utf-8')]}


def _message(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise RecipeError('Duplicate navigation field')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique)


def create_server(viewer, *, port=0):
    """Return a caller-owned loopback server; selection is per request/tab."""
    if type(port) is not int or not 0 <= port <= 65535:
        raise RecipeError('Port must be an integer from 0 to 65535')
    static = assets()
    base_path = '/' + secrets.token_urlsafe(32) + '/'

    class Handler(BaseHTTPRequestHandler):
        # The capability URL and unpublished identifiers must not enter access logs.
        def log_message(self, *args):
            pass

        def reply(self, status, data, mime='application/json; charset=utf-8'):
            self.send_response(status)
            for name, value in {
                'Content-Type':mime, 'Content-Length':str(len(data)), 'Cache-Control':'no-store',
                'X-Content-Type-Options':'nosniff', 'Referrer-Policy':'no-referrer',
                'Content-Security-Policy':"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'",
            }.items():
                self.send_header(name,value)
            self.end_headers()
            self.wfile.write(data)

        def reject(self, status, message):
            self.reply(status, canonical({'error':message}).encode())

        def route(self, *, post=False):
            host = '127.0.0.1:' + str(self.server.server_address[1])
            origins = self.headers.get_all('Origin', [])
            if (self.headers.get_all('Host', []) != [host] or
                    origins not in ([], ['http://' + host]) or (post and not origins)):
                self.reject(403, 'Local same-origin access required')
                return None
            if not self.path.startswith(base_path):
                self.reject(404, 'Unknown viewer resource')
                return None
            return self.path[len(base_path):]

        def do_GET(self):
            name = self.route()
            if name is None:
                return
            if name in static:
                self.reply(200, *static[name])
            elif name == 'view':
                self.reply(200, canonical(viewer.present()).encode())
            else:
                self.reject(404, 'Unknown viewer resource')

        def do_POST(self):
            name = self.route(post=True)
            if name is None:
                return
            if name != 'view':
                self.reject(404, 'Unknown viewer resource'); return
            if self.headers.get('Content-Type') != 'application/json':
                self.reject(415, 'Require application/json'); return
            try:
                lengths = self.headers.get_all('Content-Length', [])
                if len(lengths) != 1 or self.headers.get('Transfer-Encoding'):
                    raise ValueError
                length = int(lengths[0])
                if length < 0:
                    raise ValueError
            except ValueError:
                self.reject(400, 'Require a valid content length'); return
            if length > 16384:
                self.reject(413, 'Navigation request too large'); return
            try:
                value = viewer.navigate(_message(self.rfile.read(length)))
            except (RecipeError, ValueError, TypeError, RecursionError):
                self.reject(400, 'Invalid navigation request'); return
            self.reply(200, canonical(value).encode())

        def setup(self):
            super().setup()
            self.connection.settimeout(10)

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    server.base_path = base_path
    server.url = 'http://127.0.0.1:' + str(server.server_address[1]) + base_path
    return server


def serve(viewer, *, port=0):
    with create_server(viewer, port=port) as server:
        print('Metal workbench: ' + server.url, flush=True)
        print('Verified saved snapshot; no jobs or scientific edits. Stop with Ctrl-C.', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0
