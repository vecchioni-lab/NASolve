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
