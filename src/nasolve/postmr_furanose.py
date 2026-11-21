"""One source-qualified internal sugar substitution after ordinary scaffold construction."""
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from .cif_acquisition_preparation import _freeze
from .cif_attachment_profiles import inspect_attachment_profile
from .cif_attachment_sites import _site
from .cif_base_displacement import POLICY_ID as BASE_B_POLICY
from .cif_dictionary_sites import _SNAPSHOT_FILES, _need, _read
from .cif_dictionary_store import resolve_dictionary_snapshot
from .cif_fana_component import _load
from .cif_furanose_bridge import prepare_furanose_bridge_seed, read_furanose_bridge_seed
from .cif_repair_attempt import _root
from .cif_whole_furanose import prepare_base_anchored_furanose_from_model

DIRECTORY = 'PostMR/Coot/furanose'
_LOCKED = 'two-o-four-c-methylene-furanose-phosphate-v1'
_FIT = dict(endpoint_weight=1000.0, max_base_displacement=2.0)


@dataclass(frozen=True)
class FuranoseInput:
    site: str
    code: str
    entry_id: str
    source_authority: str
    snapshot: Path
    files: dict[str, bytes]
    host: Path
    host_bytes: bytes
    workbook: Path
    workbook_bytes: bytes

    def verify_source(self, path, authority):
        _need(authority == self.source_authority and _read(path) == self.files['entry/source.cif'],
              'Furanose construction differs from the selected chemical source or its authority')

    def verify(self):
        _need(all(_read(self.snapshot/name) == data for name, data in self.files.items())
              and _read(self.host) == self.host_bytes and _read(self.workbook) == self.workbook_bytes,
              'Selected furanose construction inputs changed')


def capture_substitution(selection, consumer):
    """Read only the declared qualified snapshot, host dictionary and NARestraints workbook."""
    _need(isinstance(selection, dict) and set(selection) == {'site','snapshot','host_dictionary','workbook'},
          'A furanose substitution needs a site, qualified snapshot, host dictionary and workbook')
    site = _site(selection['site'])
    directory = _root(selection['snapshot'])
    saved = resolve_dictionary_snapshot(directory)
    _need(saved['qualification_current'] and saved['manifest']['consumer'] == consumer,
          'Furanose construction requires a dictionary qualified for the selected consumer')
    code = saved['manifest']['request']['component']
    host, workbook = (Path(selection[k]).absolute() for k in ('host_dictionary','workbook'))
    choice = FuranoseInput(site, code, saved['entry_id'], saved['manifest']['request']['source_authority'],
                          directory, {n:_read(directory/n) for n in _SNAPSHOT_FILES},
                          host, _read(host), workbook, _read(workbook))
    profile = inspect_attachment_profile(saved['source'], code, workbook=workbook)
    _need(profile['topology_status'] == 'MATCH' and profile['matched_profile'] == _LOCKED,
          'This construction requires the source-declared 2′-O,4′-C bridged furanose')
    _need(resolve_dictionary_snapshot(directory)['manifest'] == saved['manifest'],
          'Qualified furanose dictionary changed during selection')
    choice.verify()
    return choice


def build_substitution(choice, frame, prepared, run, report):
    """Install the verified base-anchored seed on the phosphate-prepared Coot frame."""
    choice.verify()
    root = run/DIRECTORY
    root.mkdir(exist_ok=False)
    _freeze(root/'snapshot', choice.files, ['entry'])
    saved = resolve_dictionary_snapshot(root/'snapshot')
    with TemporaryDirectory(prefix='furanose-placement-', dir=root) as temporary:
        temp = Path(temporary)
        host, workbook = temp/'host.cif', temp/'Ligands.xlsx'
        host.write_bytes(choice.host_bytes)
        workbook.write_bytes(choice.workbook_bytes)
        prepare_base_anchored_furanose_from_model(
            saved['source'], saved['dictionary'], host, workbook, frame, temp/'placement',
            code=choice.code, site=choice.site, postmr_report=report)
        prepare_furanose_bridge_seed(temp/'placement', root/'seed', **_FIT, inherit_equivalent_base_b=True)
    choice.verify()
    with prepared.open('xb') as handle:
        handle.write(_read(root/'seed/model.pdb'))


def read_substitution(root):
    """Recover the original qualified component and the exact two ports used in the model."""
    root = _root(root)
    _need({p.name for p in root.iterdir()} == {'snapshot','seed'}, 'Unexpected furanose construction members')
    _need({p.name for p in (root/'snapshot').iterdir()} == {'resolution.json','entry'},
          'Unexpected furanose dictionary snapshot members')
    original = resolve_dictionary_snapshot(root/'snapshot')
    seed = read_furanose_bridge_seed(root/'seed')
    placement = root/'seed/placement'
    placed = _load(placement/'placement.json')
    code = original['manifest']['request']['component']
    _need(original['qualification_current'] and seed['component'] == placed['component'] == code
          and _read(placement/'source.cif') == _read(original['source'])
          and _read(placement/'numerical.cif') == _read(original['dictionary'])
          and placed['source_profile'] == _LOCKED and 'ordinary_backbone' in placed
          and 'phosphate_leaving_atom' in placed and 'base_frame_source' in placed,
          'Furanose seed differs from the qualified source, ordinary partners or mapped base')
    _need(seed['config'] == dict(_FIT, base_b_policy=BASE_B_POLICY),
          'Furanose seed differs from the supported fit and displacement policy')
    return dict(snapshot=original, model=root/'seed/model.pdb', host_frame=placement/'frame.pdb',
                context=placed['context'], workbook=placement/'Ligands.xlsx', code=code)
