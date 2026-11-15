"""Cartesian symmetry-image coordinates and gradients over shared ASU variables.

This is coordinate arithmetic, not a restraint policy or native qualification.
The numerical core has no Gemmi/Phenix dependency. The optional crystallographic
factory validates the exact operator against the declared cell and space group.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


def _vector(values):
    if not isinstance(values, (tuple, list)) or len(values) != 3:
        raise ValueError('Require a Cartesian three-vector')
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
        raise ValueError('Require finite Cartesian numbers')
    return tuple(float(v) for v in values)


def _tensor(values):
    if not isinstance(values,(tuple,list)) or len(values)!=6:
        raise ValueError('Require six symmetric Cartesian tensor components')
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in values):
        raise ValueError('Require finite Cartesian tensor components')
    return tuple(float(v) for v in values)


def _dot(a, b):
    try:
        value = math.fsum(x*y for x, y in zip(a, b))
    except (OverflowError, ValueError) as exc:
        raise ValueError('Cartesian arithmetic exceeds finite range') from exc
    if not math.isfinite(value):
        raise ValueError('Cartesian arithmetic exceeds finite range')
    return value


@dataclass(frozen=True)
class CartesianImage:
    """A proper rigid image: x_image = R x_ASU + t; g_ASU = R^T g_image.

    Explicit matrices are trusted numerical inputs, not crystallographic proof.
    Use crystallographic_image for a cell/group/operator membership check.
    """
    rotation: tuple
    translation: tuple

    def __post_init__(self):
        if not isinstance(self.rotation, (tuple, list)) or len(self.rotation) != 3:
            raise ValueError('Require a Cartesian 3 by 3 rotation')
        rotation = tuple(_vector(row) for row in self.rotation)
        translation = _vector(self.translation)
        if max(abs(_dot(a,b)-(1. if i==j else 0.))
               for i,a in enumerate(rotation) for j,b in enumerate(rotation)) > 1e-7:
            raise ValueError('Cartesian image rotation must be orthogonal')
        a,b,c = rotation
        determinant = _dot(a, (b[1]*c[2]-b[2]*c[1], b[2]*c[0]-b[0]*c[2], b[0]*c[1]-b[1]*c[0]))
        if abs(determinant-1.) > 1e-7:
            raise ValueError('Initial DNA image transport requires a proper rotation')
        object.__setattr__(self, 'rotation', rotation)
        object.__setattr__(self, 'translation', translation)

    def apply(self, point):
        point = _vector(point)
        result = tuple(_dot(row,point)+t for row,t in zip(self.rotation,self.translation))
        return _vector(result)

    def rotate_tensor(self, tensor):
        """Return R U R^T in (U11,U22,U33,U12,U13,U23) Cartesian order.

        Translation does not act on a covariance tensor. Units are retained;
        fractional U_star must be converted by the caller first. This arithmetic
        does not validate physical ADPs or choose isotropic/anisotropic flags.
        """
        u11,u22,u33,u12,u13,u23 = _tensor(tensor)
        matrix=((u11,u12,u13),(u12,u22,u23),(u13,u23,u33))
        values=tuple(sum(self.rotation[i][a]*matrix[a][b]*self.rotation[j][b]
                         for a in range(3) for b in range(3))
                     for i,j in ((0,0),(1,1),(2,2),(0,1),(0,2),(1,2)))
        return _tensor(values)

    def pullback(self, gradient):
        """Translation has no derivative; the inverse rotation acts on gradients."""
        gradient = _vector(gradient)
        return tuple(_dot(column,gradient) for column in zip(*self.rotation))

    def inverse(self):
        rotation = tuple(zip(*self.rotation))
        return CartesianImage(rotation, tuple(-_dot(row,self.translation) for row in rotation))


IDENTITY_IMAGE = CartesianImage(((1.,0.,0.),(0.,1.,0.),(0.,0.,1.)),(0.,0.,0.))


def crystallographic_image(cell_parameters, space_group, operator_xyz):
    """Compile one valid group operation plus its exact lattice translation."""
    from .topostitch_periodic import _crystal, _op_key
    gemmi, cell, group = _crystal(cell_parameters,space_group)
    if not isinstance(operator_xyz,str) or not operator_xyz.strip():
        raise ValueError('Require an explicit image operator')
    try:
        op = gemmi.Op(operator_xyz)
    except RuntimeError as exc:
        raise ValueError('Invalid image operator') from exc
    wrapped = gemmi.Op(op.triplet()).wrap()
    if _op_key(wrapped) not in {_op_key(member) for member in group.operations()}:
        raise ValueError('Image operator does not belong to the declared space group')
    orth, frac = cell.orth.mat.tolist(), cell.frac.mat.tolist()
    fractional_rotation = [[v/op.DEN for v in row] for row in op.rot]
    multiply = lambda a,b: tuple(tuple(_dot(row,col) for col in zip(*b)) for row in a)
    rotation = multiply(multiply(orth,fractional_rotation),frac)
    translation = tuple(_dot(row,tuple(v/op.DEN for v in op.tran)) for row in orth)
    return CartesianImage(rotation,translation)


def _references(atom_count, references):
    if type(atom_count) is not int or atom_count < 0:
        raise ValueError('Require a nonnegative atom count')
    rows = tuple(references)
    for row in rows:
        if (not isinstance(row,(tuple,list)) or len(row)!=2 or type(row[0]) is not int
                or not 0<=row[0]<atom_count or not isinstance(row[1],CartesianImage)):
            raise ValueError('Image reference must bind a valid ASU index and CartesianImage')
    return rows


def expand_sites(asu_points, references):
    """Keep every explicit atom/image instance, including repeated ASU indices."""
    points = tuple(_vector(p) for p in asu_points)
    rows = _references(len(points),references)
    return tuple(image.apply(points[index]) for index,image in rows)


def accumulate_image_gradients(atom_count, references, image_gradients):
    """Accumulate every image contribution into its shared ASU variable.

    Repeated indices are intentional. Overwriting them or rotating a gradient
    with R rather than R^T gives the wrong derivative for self-image contacts.
    No constraint, optimizer or movable-atom mask is inferred here.
    """
    rows = _references(atom_count,references)
    gradients = tuple(_vector(g) for g in image_gradients)
    if len(gradients)!=len(rows):
        raise ValueError('Require one gradient per explicit image reference')
    terms = [[[],[],[]] for _ in range(atom_count)]
    for (index,image),gradient in zip(rows,gradients):
        for axis,value in enumerate(image.pullback(gradient)):
            terms[index][axis].append(value)
    try:
        return tuple(_vector(tuple(math.fsum(axis) for axis in atom)) for atom in terms)
    except (OverflowError,ValueError) as exc:
        raise ValueError('Accumulated image gradient exceeds finite range') from exc


@dataclass(frozen=True)
class CoordinateMask:
    """Explicit ASU displacement variables with exact fixed-coordinate anchors.

    This is arithmetic, not permission to move the selected atoms. Identity,
    chemistry, native objective and mask provenance belong to the caller.
    """
    reference: tuple
    indices: tuple
    max_displacement_angstrom: float

    def __post_init__(self):
        points = tuple(_vector(p) for p in self.reference)
        indices = tuple(self.indices)
        if (not points or not indices or len(set(indices)) != len(indices)
                or any(type(i) is not int or not 0 <= i < len(points) for i in indices)):
            raise ValueError('Require distinct explicit movable atom indices')
        bound = self.max_displacement_angstrom
        if type(bound) not in (int,float) or not math.isfinite(bound) or bound <= 0:
            raise ValueError('Require a finite positive displacement bound')
        object.__setattr__(self,'reference',points)
        object.__setattr__(self,'indices',indices)
        object.__setattr__(self,'max_displacement_angstrom',float(bound))

    def expand(self, displacements):
        values = tuple(displacements)
        if len(values) != 3*len(self.indices):
            raise ValueError('Movable displacement count changed')
        points = list(self.reference)
        for j,index in enumerate(self.indices):
            delta = _vector(values[3*j:3*j+3])
            if math.hypot(*delta) > self.max_displacement_angstrom:
                raise ValueError('Movable atom displacement exceeds declared bound')
            points[index] = _vector(tuple(a+b for a,b in zip(self.reference[index],delta)))
        return tuple(points)

    def displacements(self, points):
        points = tuple(_vector(p) for p in points)
        if len(points) != len(self.reference):
            raise ValueError('ASU coordinate count changed')
        selected = set(self.indices)
        if any(p != self.reference[i] for i,p in enumerate(points) if i not in selected):
            raise ValueError('Fixed ASU coordinates changed')
        delta = tuple(a-b for i in self.indices for a,b in zip(points[i],self.reference[i]))
        self.expand(delta)  # Same finite-motion policy in both directions.
        return delta

    def project(self, gradients):
        gradients = tuple(_vector(g) for g in gradients)
        if len(gradients) != len(self.reference):
            raise ValueError('Full ASU gradient count changed')
        return tuple(v for i in self.indices for v in gradients[i])


@dataclass(frozen=True)
class ReferenceFrame:
    """Complete one-to-one coordinate images bound to a caller-owned context.

    Source labels/images stay in the native source order. `order` maps the
    current representative order to that source order; reindexing must retain
    every atom exactly once. This is arithmetic plus binding, not a native
    manager, crystal-membership proof, atom selector or chemistry policy.

    The caller must authenticate the source and recompute its context digest
    (including cell/group and effective model/restraint identity) before use.
    Explicit matrices remain trusted numerical inputs, like CartesianImage;
    use crystallographic_image when compiling a checked crystal operation.
    """
    source_labels: tuple
    images: tuple
    context_sha256: str
    order: tuple | None = None

    def __post_init__(self):
        labels, images = tuple(self.source_labels), tuple(self.images)
        if (not labels or len(labels) > 100000 or len(images) != len(labels)
                or any(not isinstance(s,str) or not s or len(s)>512 for s in labels)
                or len(set(labels)) != len(labels)
                or any(not isinstance(image,CartesianImage) for image in images)):
            raise ValueError('Require complete distinct source labels and one image per atom')
        digest = self.context_sha256
        if (not isinstance(digest,str) or len(digest)!=64
                or any(c not in '0123456789abcdef' for c in digest)):
            raise ValueError('Require an explicit source context SHA-256')
        order = tuple(range(len(labels))) if self.order is None else tuple(self.order)
        self._permutation(order, len(labels))
        object.__setattr__(self,'source_labels',labels)
        object.__setattr__(self,'images',images)
        object.__setattr__(self,'order',order)

    @staticmethod
    def _permutation(order, count):
        if (len(order)!=count or any(type(i) is not int for i in order)
                or set(order)!=set(range(count))):
            raise ValueError('Reference-frame reindexing requires a complete permutation; partial selection is unsupported')

    @property
    def atom_labels(self):
        return tuple(self.source_labels[i] for i in self.order)

    def reindex(self, order):
        """Reorder this complete view explicitly; never delegate/drop its mapping."""
        order=tuple(order);self._permutation(order,len(self.order))
        return ReferenceFrame(self.source_labels,self.images,self.context_sha256,
                              tuple(self.order[i] for i in order))

    def _check(self, values, labels, expected_labels, context_sha256, *, validator=_vector):
        if context_sha256 != self.context_sha256:
            raise ValueError('Reference-frame source context changed')
        if tuple(labels) != expected_labels:
            raise ValueError('Reference-frame atom order or identity changed')
        values=tuple(validator(v) for v in values)
        if len(values)!=len(self.source_labels):
            raise ValueError('Reference-frame values must cover the complete source')
        return values

    def to_source(self, points, *, atom_labels, context_sha256):
        points=self._check(points,atom_labels,self.atom_labels,context_sha256)
        source=[None]*len(points)
        for point,index in zip(points,self.order):
            source[index]=self.images[index].inverse().apply(point)
        return tuple(source)

    def to_representatives(self, points, *, source_labels, context_sha256):
        points=self._check(points,source_labels,self.source_labels,context_sha256)
        return tuple(self.images[i].apply(points[i]) for i in self.order)

    def gradients_to_representatives(self, gradients, *, source_labels, context_sha256):
        gradients=self._check(gradients,source_labels,self.source_labels,context_sha256)
        # x_source = image^-1(x_rep); its transpose Jacobian maps source forces.
        # Translations never act on gradients.
        return tuple(self.images[i].inverse().pullback(gradients[i]) for i in self.order)

    def tensors_to_source(self, tensors, *, atom_labels, context_sha256):
        """Inverse-rotate a complete Cartesian tensor inventory into source order.

        Missing/isotropic flags remain caller-owned; None is not an implicit ADP
        policy. Tensor values use the six-component order in rotate_tensor.
        """
        tensors=self._check(tensors,atom_labels,self.atom_labels,context_sha256,validator=_tensor)
        source=[None]*len(tensors)
        for tensor,index in zip(tensors,self.order):
            source[index]=self.images[index].inverse().rotate_tensor(tensor)
        return tuple(source)

    def tensors_to_representatives(self, tensors, *, source_labels, context_sha256):
        """Rotate complete Cartesian tensors with the same atom binding as sites."""
        tensors=self._check(tensors,source_labels,self.source_labels,context_sha256,validator=_tensor)
        return tuple(self.images[i].rotate_tensor(tensors[i]) for i in self.order)
