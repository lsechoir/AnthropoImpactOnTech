from typing import Annotated, Literal, TypeVar
import numpy.typing as npt

import numpy as np
import yeadon
import yaml
from math import pi


# From [https://stackoverflow.com/questions/71109838/numpy-typing-with-specific-shape-and-datatype]
DType = TypeVar("DType", bound=np.generic)
Vec2 = Annotated[npt.NDArray[DType], Literal[2]]
Vec3 = Annotated[npt.NDArray[DType], Literal[3]]
Mat3x3 = Annotated[npt.NDArray[DType], Literal[3, 3]]


O = np.zeros(3)


def format_vec(vec):
    return ("{} " * len(vec)).format(*vec)[:-1]  # fancy


def format_mat(mat: Mat3x3, leading=""):
    return (
        f"{leading}{mat[0, 0]} {mat[0, 1]} {mat[0, 2]}\n"
        f"{leading}{mat[1, 0]} {mat[1, 1]} {mat[1, 2]}\n"
        f"{leading}{mat[2, 0]} {mat[2, 1]} {mat[2, 2]}"
    )


class BioModMarker:
    def __init__(self, label: str, parent: str, position: Vec3, technical: int, anatomical: int, axestoremove: str):
        self.label = label
        self.parent = parent
        self.position = position
        self.technical = technical
        self.anatomical = anatomical
        self.axestoremove = axestoremove

    def __str__(self):
        mod = f"\tmarker {self.label}\n"
        mod += f"\t\tparent {self.parent}\n"
        mod += f"\t\tposition {format_vec(self.position)}\n"
        if self.technical is not None:
            mod += f"\t\ttechnical {self.technical}\n"
        if self.anatomical is not None:
            mod += f"\t\tanatomical {self.anatomical}\n"
        if self.axestoremove:
            mod += f"\t\taxestoremove {self.axestoremove}\n"
        mod += "\tendmarker"

        return mod


def parse_markers(parent: str, markers_desc: dict[dict]):
    markers = []
    for label in markers_desc:
        position = markers_desc[label]["position"]
        technical = markers_desc[label]["technical"] if "technical" in markers_desc[label] else None
        anatomical = markers_desc[label]["anatomical"] if "anatomical" in markers_desc[label] else None
        axestoremove = markers_desc[label]["axestoremove"] if "axestoremove" in markers_desc[label] else None
        markers.append(BioModMarker(label, parent, position, technical, anatomical, axestoremove))

    return markers


class BioModSegment:
    def __init__(
        self,
        label: str,
        parent: str,
        rt: Vec3,
        xyz: Vec3,
        translations: str,
        rotations: str,
        com: Vec3,
        mass: float,
        inertia: Mat3x3,
        rangesQ: list[Vec2],
        mesh: list[Vec3],
        meshfile: str,
        meshcolor: Vec3,
        meshscale: Vec3,
        meshrt: Vec3,
        meshxyz: Vec3,
        patch: list[Vec3],
        markers: list[BioModMarker],
    ):
        self.label = label
        self.parent = parent
        self.rt = rt
        self.xyz = xyz
        self.translations = translations
        self.rotations = rotations
        self.com = com
        self.mass = mass
        self.inertia = inertia
        self.rangesQ = rangesQ
        self.mesh = mesh
        self.meshfile = meshfile
        self.meshcolor = meshcolor
        self.meshscale = meshscale
        self.meshrt = meshrt
        self.meshxyz = meshxyz
        self.patch = patch
        self.markers = markers

    def __str__(self):
        mod = f"segment {self.label}\n"
        if self.parent:
            mod += f"\tparent {self.parent}\n"
        mod += f"\trt {format_vec(self.rt)} xyz {format_vec(self.xyz)}\n"
        if self.translations:
            mod += f"\ttranslations {self.translations}\n"
        if self.rotations:
            mod += f"\trotations {self.rotations}\n"
        if self.rangesQ:
            mod += f"\trangesQ\n"
            for r in self.rangesQ:
                mod += f"\t\t{format_vec(r)}\n"
        mod += f"\tcom {format_vec(self.com)}\n"
        mod += f"\tmass {self.mass}\n"
        mod += f"\tinertia\n" + format_mat(self.inertia, leading="\t\t") + "\n"
        if self.meshfile:
            mod += f"\tmeshfile {self.meshfile}\n"
        elif self.mesh:
            for m in self.mesh:
                mod += f"\tmesh {format_vec(m)}\n"
        if self.meshcolor:
            mod += f"\tmeshcolor {format_vec(self.meshcolor)}\n"
        if self.meshscale:
            mod += f"\tmeshscale {format_vec(self.meshscale)}\n"
        if self.meshrt and self.meshxyz:
            mod += f"\tmeshrt {format_vec(self.meshrt)} xyz {format_vec(self.meshxyz)}\n"
        if self.patch:
            for p in self.patch:
                mod += f"\tpatch {format_vec(p)}\n"
        mod += "endsegment"

        if self.markers:
            mod += "\n\n"
            for i, m in enumerate(self.markers):
                mod += str(m)
                if i < len(self.markers) - 1:
                    mod += "\n\n"

        return mod


class Pelvis(BioModSegment):
    def __init__(
        self,
        human: yeadon.Human,
        label: str = "",
        rt: Vec3 = O,
        translations: str = "",
        rotations: str = "",
        rangesQ: list[Vec2] = None,
        mesh: list[Vec3] = [(0, 0, 0)],
        meshfile: str = None,
        meshcolor: Vec3 = None,
        meshscale: Vec3 = None,
        meshrt: Vec3 = None,
        meshxyz: Vec3 = None,
        patch: list[Vec3] = None,
        markers: dict[dict] = {},
    ):
        label = label or Pelvis.__name__
        parent = None

        xyz = Pelvis.get_origin(human)
        com = O
        mass = human.P.mass
        inertia = human.P.rel_inertia
        meshscale = Pelvis.adapted_meshscale(human)
        markers = parse_markers(label, markers)

        BioModSegment.__init__(
            self,
            label=label,
            parent=parent,
            rt=rt,
            xyz=xyz,
            translations=translations,
            rotations=rotations,
            com=com,
            mass=mass,
            inertia=inertia,
            rangesQ=rangesQ,
            mesh=mesh,
            meshfile=meshfile,
            meshcolor=meshcolor,
            meshscale=meshscale,
            meshrt=meshrt,
            meshxyz=meshxyz,
            patch=patch,
            markers=markers,
        )

    @staticmethod
    def adapted_meshscale(human: yeadon.Human):
        m_x = (human.meas.get("Ls1w")) / 0.288
        m_y = (human.meas.get("Ls4d")) / 0.158
        m_z = (human.meas.get("Ls2L")) / 0.154
        return [m_x, m_y, m_z]

    @staticmethod
    def get_origin(human: yeadon.Human) -> Vec3:
        """Get the origin of the Pelvis in the global frame centered at Pelvis' COM."""
        return O


class Thorax(BioModSegment):
    def __init__(
        self,
        human: yeadon.Human,
        label: str = "",
        parent: str = Pelvis.__name__,
        rt: Vec3 = O,
        rotations: str = "",
        rangesQ: list[Vec2] = None,
        mesh: list[Vec3] = [(0, 0, 0)],
        meshfile: str = None,
        meshcolor: Vec3 = None,
        meshscale: Vec3 = None,
        meshrt: Vec3 = None,
        meshxyz: Vec3 = None,
        patch: list[Vec3] = None,
        markers: dict[dict] = {},
    ):
        label = label or Thorax.__name__

        xyz = Thorax.get_origin(human) - Pelvis.get_origin(human)
        translations = ""

        mass, com_global, inertia_global = human.combine_inertia(("T", "s3", "s4"))
        com = np.asarray(com_global - human.P.center_of_mass).reshape(3) - Thorax.get_origin(human)
        meshscale = Thorax.adapted_meshscale(human)
        markers = parse_markers(label, markers)

        BioModSegment.__init__(
            self,
            label=label,
            parent=parent,
            rt=rt,
            xyz=xyz,
            translations=translations,
            rotations=rotations,
            com=com,
            mass=mass,
            inertia=inertia_global,  # I can do this because the systems of coordinates are aligned.
            rangesQ=rangesQ,
            mesh=mesh,
            meshfile=meshfile,
            meshcolor=meshcolor,
            meshscale=meshscale,
            meshrt=meshrt,
            meshxyz=meshxyz,
            patch=patch,
            markers=markers,
        )

    @staticmethod
    def adapted_meshscale(human):
        m_x = (human.meas.get("Ls3w")) / 0.316
        m_y = (human.meas.get("Ls4d")) / 0.158
        m_z = (human.meas.get("Ls5L") - human.meas.get("Ls2L")) / 0.366
        return [m_x, m_y, m_z]

    @staticmethod
    def get_origin(human: yeadon.Human) -> Vec3:
        """Get the origin of the Thorax in the global frame centered at Pelvis' COM."""
        return np.asarray(human.T.pos - human.P.center_of_mass).reshape(3)


class Head(BioModSegment):
    def __init__(
        self,
        human: yeadon.Human,
        label: str = "",
        parent: str = Thorax.__name__,
        rt: Vec3 = O,
        rotations: str = "",
        rangesQ: list[Vec2] = None,
        mesh: list[Vec3] = [(0, 0, 0)],
        meshfile: str = None,
        meshcolor: Vec3 = None,
        meshscale: Vec3 = None,
        meshrt: Vec3 = None,
        meshxyz: Vec3 = None,
        patch: list[Vec3] = None,
        markers: dict[dict] = {},
    ):
        label = label or Head.__name__

        xyz = Head.get_origin(human) - Thorax.get_origin(human)
        translations = ""

        mass, com_global, inertia_global = human.combine_inertia(("s5", "s6", "s7"))
        com = np.asarray(com_global - human.P.center_of_mass).reshape(3) - Head.get_origin(human)
        meshscale = Head.adapted_meshscale(human)
        markers = parse_markers(label, markers)

        BioModSegment.__init__(
            self,
            label=label,
            parent=parent,
            rt=rt,
            xyz=xyz,
            translations=translations,
            rotations=rotations,
            com=com,
            mass=mass,
            inertia=inertia_global,  # I can do this because the systems of coordinates are aligned.
            rangesQ=rangesQ,
            mesh=mesh,
            meshfile=meshfile,
            meshcolor=meshcolor,
            meshscale=meshscale,
            meshrt=meshrt,
            meshxyz=meshxyz,
            patch=patch,
            markers=markers,
        )

    @staticmethod
    def adapted_meshscale(human: yeadon.Human):
        m_x = ((human.meas.get("Ls7p")) / pi) / 0.185
        m_y = ((human.meas.get("Ls7p")) / pi) / 0.185
        m_z = (human.meas.get("Ls8L")) / 0.277
        return [m_x, m_y, m_z]

    @staticmethod
    def get_origin(human: yeadon.Human) -> Vec3:
        """Get the origin of the Head in the global frame centered at Pelvis' COM."""
        length = human.C.solids[0].height + human.C.solids[1].height
        dir = human.C.end_pos - human.C.pos
        dir = dir / np.linalg.norm(dir)
        pos = human.C.pos + length * dir
        return np.asarray(pos - human.P.center_of_mass).reshape(3)


class LeftUpperArm(BioModSegment):
    def __init__(
        self,
        human: yeadon.Human,
        label: str = "",
        parent: str = Thorax.__name__,
        rt: Vec3 = O,
        rotations: str = "",
        rangesQ: list[Vec2] = None,
        mesh: list[Vec3] = [(0, 0, 0)],
        meshfile: str = None,
        meshcolor: Vec3 = None,
        meshscale: Vec3 = None,
        meshrt: Vec3 = None,
        meshxyz: Vec3 = None,
        patch: list[Vec3] = None,
        markers: dict[dict] = {},
    ):
        label = label or LeftUpperArm.__name__

        xyz = LeftUpperArm.get_origin(human) - Thorax.get_origin(human)
        translations = ""

        com = np.asarray(human.A1.rel_center_of_mass).reshape(3)
        mass = human.A1.mass
        inertia = human.A1.rel_inertia
        meshscale = LeftUpperArm.adapted_meshscale(human)
        markers = parse_markers(label, markers)

        BioModSegment.__init__(
            self,
            label=label,
            parent=parent,
            rt=rt,
            xyz=xyz,
            translations=translations,
            rotations=rotations,
            com=com,
            mass=mass,
            inertia=inertia,
            rangesQ=rangesQ,
            mesh=mesh,
            meshfile=meshfile,
            meshcolor=meshcolor,
            meshscale=meshscale,
            meshrt=meshrt,
            meshxyz=meshxyz,
            patch=patch,
            markers=markers,
        )

    @staticmethod
    def adapted_meshscale(human: yeadon.Human):
        m_x = ((human.meas.get("La1p")) / pi) / 0.097
        m_y = ((human.meas.get("La1p")) / pi) / 0.097
        m_z = (human.meas.get("La2L")) / 0.26
        return [m_x, m_y, m_z]

    @staticmethod
    def get_origin(human: yeadon.Human) -> Vec3:
        """Get the origin of the LeftUpperArm in the global frame centered at Pelvis' COM."""
        return np.asarray(human.A1.pos - human.P.center_of_mass).reshape(3)


class LeftForearm(BioModSegment):
    def __init__(
        self,
        human: yeadon.Human,
        label: str = "",
        parent: str = LeftUpperArm.__name__,
        rt: Vec3 = O,
        rotations: str = "",
        rangesQ: list[Vec2] = None,
        mesh: list[Vec3] = [(0, 0, 0)],
        meshfile: str = None,
        meshcolor: Vec3 = None,
        meshscale: Vec3 = None,
        meshrt: Vec3 = None,
        meshxyz: Vec3 = None,
        patch: list[Vec3] = None,
        markers: dict[dict] = {},
    ):
        label = label or LeftForearm.__name__

        xyz = LeftForearm.get_origin(human) - LeftUpperArm.get_origin(human)
        translations = ""

        # using Segment to have rel_inertia
        segment = yeadon.segment.Segment("", O.reshape(3, 1), np.eye(3), human.A2.solids[:2], O, False)
        mass = segment.mass
        com = np.asarray(segment.rel_center_of_mass).reshape(3)
        inertia = segment.rel_inertia
        meshscale = LeftForearm.adapted_meshscale(human)
        markers = parse_markers(label, markers)

        BioModSegment.__init__(
            self,
            label=label,
            parent=parent,
            rt=rt,
            xyz=xyz,
            translations=translations,
            rotations=rotations,
            com=com,
            mass=mass,
            inertia=inertia,
            rangesQ=rangesQ,
            mesh=mesh,
            meshfile=meshfile,
            meshcolor=meshcolor,
            meshscale=meshscale,
            meshrt=meshrt,
            meshxyz=meshxyz,
            patch=patch,
            markers=markers,
        )

    @staticmethod
    def adapted_meshscale(human: yeadon.Human):
        m_x = ((human.meas.get("La3p")) / pi) / 0.09
        m_y = ((human.meas.get("La3p")) / pi) / 0.09
        m_z = (human.meas.get("La4L") - human.meas.get("La2L")) / 0.248
        return [m_x, m_y, m_z]

    @staticmethod
    def get_origin(human: yeadon.Human) -> Vec3:
        """Get the origin of the LeftForearm in the global frame centered at Pelvis' COM."""
        return np.asarray(human.A2.pos - human.P.center_of_mass).reshape(3)


class LeftHand(BioModSegment):
    def __init__(
        self,
        human: yeadon.Human,
        label: str = "",
        parent: str = LeftForearm.__name__,
        rt: Vec3 = O,
        rotations: str = "",
        rangesQ: list[Vec2] = None,
        mesh: list[Vec3] = [(0, 0, 0)],
        meshfile: str = None,
        meshcolor: Vec3 = None,
        meshscale: Vec3 = None,
        meshrt: Vec3 = None,
        meshxyz: Vec3 = None,
        patch: list[Vec3] = None,
        markers: dict[dict] = {},
    ):
        label = label or LeftHand.__name__

        xyz = LeftHand.get_origin(human) - LeftForearm.get_origin(human)
        translations = ""

        # using Segment to have rel_inertia
        segment = yeadon.segment.Segment("", O.reshape(3, 1), np.eye(3), human.A2.solids[2:], O, False)
        mass = segment.mass
        com = np.asarray(segment.rel_center_of_mass).reshape(3)
        inertia = segment.rel_inertia
        meshscale = LeftHand.adapted_meshscale(human)
        markers = parse_markers(label, markers)

        BioModSegment.__init__(
            self,
            label=label,
            parent=parent,
            rt=rt,
            xyz=xyz,
            translations=translations,
            rotations=rotations,
            com=com,
            mass=mass,
            inertia=inertia,
            rangesQ=rangesQ,
            mesh=mesh,
            meshfile=meshfile,
            meshcolor=meshcolor,
            meshscale=meshscale,
            meshrt=meshrt,
            meshxyz=meshxyz,
            patch=patch,
            markers=markers,
        )

    @staticmethod
    def adapted_meshscale(human: yeadon.Human):
        m_x = (human.meas.get("La5w")) / 0.098
        m_y = (human.meas.get("La5w")) / 0.098
        m_z = human.meas.get("La7L") / 0.177
        return [m_x, m_y, m_z]

    @staticmethod
    def get_origin(human: yeadon.Human):
        """Get the origin of the LeftHand in the global frame centered at Pelvis' COM."""
        length = human.A2.solids[0].height + human.A2.solids[1].height
        dir = human.A2.end_pos - human.A2.pos
        dir = dir / np.linalg.norm(dir)
        pos = human.A2.pos + length * dir
        return np.asarray(pos - human.P.center_of_mass).reshape(3)


class RightUpperArm(BioModSegment):
    def __init__(
        self,
        human: yeadon.Human,
        label: str = "",
        parent: str = Thorax.__name__,
        rt: Vec3 = O,
        rotations: str = "",
        rangesQ: list[Vec2] = None,
        mesh: list[Vec3] = [(0, 0, 0)],
        meshfile: str = None,
        meshcolor: Vec3 = None,
        meshscale: Vec3 = None,
        meshrt: Vec3 = None,
        meshxyz: Vec3 = None,
        patch: list[Vec3] = None,
        markers: dict[dict] = {},
    ):
        label = label or RightUpperArm.__name__

        xyz = RightUpperArm.get_origin(human) - Thorax.get_origin(human)
        translations = ""
        com = np.asarray(human.B1.rel_center_of_mass).reshape(3)
        mass = human.B1.mass
        inertia = human.B1.rel_inertia
        meshscale = RightUpperArm.adapted_meshscale(human)
        markers = parse_markers(label, markers)

        BioModSegment.__init__(
            self,
            label=label,
            parent=parent,
            rt=rt,
            xyz=xyz,
            translations=translations,
            rotations=rotations,
            com=com,
            mass=mass,
            inertia=inertia,
            rangesQ=rangesQ,
            mesh=mesh,
            meshfile=meshfile,
            meshcolor=meshcolor,
            meshscale=meshscale,
            meshrt=meshrt,
            meshxyz=meshxyz,
            patch=patch,
            markers=markers,
        )

    @staticmethod
    def adapted_meshscale(human: yeadon.Human):
        m_x = ((human.meas.get("Lb1p")) / pi) / 0.097
        m_y = ((human.meas.get("Lb1p")) / pi) / 0.097
        m_z = human.meas.get("Lb2L") / 0.26
        return [m_x, m_y, m_z]

    @staticmethod
    def get_origin(human: yeadon.Human) -> Vec3:
        """Get the origin of the RightUpperArm in the global frame centered at Pelvis' COM."""
        return np.asarray(human.B1.pos - human.P.center_of_mass).reshape(3)


class RightForearm(BioModSegment):
    def __init__(
        self,
        human: yeadon.Human,
        label: str = "",
        parent: str = RightUpperArm.__name__,
        rt: Vec3 = O,
        rotations: str = "",
        rangesQ: list[Vec2] = None,
        mesh: list[Vec3] = [(0, 0, 0)],
        meshfile: str = None,
        meshcolor: Vec3 = None,
        meshscale: Vec3 = None,
        meshrt: Vec3 = None,
        meshxyz: Vec3 = None,
        patch: list[Vec3] = None,
        markers: dict[dict] = {},
    ):
        label = label or RightForearm.__name__

        xyz = RightForearm.get_origin(human) - RightUpperArm.get_origin(human)
        translations = ""

        # using Segment to have rel_inertia
        segment = yeadon.segment.Segment("", O.reshape(3, 1), np.eye(3), human.B2.solids[:2], O, False)
        mass = segment.mass
        com = np.asarray(segment.rel_center_of_mass).reshape(3)
        inertia = segment.rel_inertia
        meshscale = RightForearm.adapted_meshscale(human)
        markers = parse_markers(label, markers)

        BioModSegment.__init__(
            self,
            label=label,
            parent=parent,
            rt=rt,
            xyz=xyz,
            translations=translations,
            rotations=rotations,
            com=com,
            mass=mass,
            inertia=inertia,
            rangesQ=rangesQ,
            mesh=mesh,
            meshfile=meshfile,
            meshcolor=meshcolor,
            meshscale=meshscale,
            meshrt=meshrt,
            meshxyz=meshxyz,
            patch=patch,
            markers=markers,
        )

    @staticmethod
    def adapted_meshscale(human: yeadon.Human):
        m_x = ((human.meas.get("Lb3p")) / pi) / 0.09
        m_y = ((human.meas.get("Lb3p")) / pi) / 0.09
        m_z = (human.meas.get("Lb4L") - human.meas.get("La2L")) / 0.248
        return [m_x, m_y, m_z]

    @staticmethod
    def get_origin(human: yeadon.Human) -> Vec3:
        """Get the origin of the RightForearm in the global frame centered at Pelvis' COM."""
        return np.asarray(human.B2.pos - human.P.center_of_mass).reshape(3)


class RightHand(BioModSegment):
    def __init__(
        self,
        human: yeadon.Human,
        label: str = "",
        parent: str = RightForearm.__name__,
        rt: Vec3 = O,
        rotations: str = "",
        rangesQ: list[Vec2] = None,
        mesh: list[Vec3] = [(0, 0, 0)],
        meshfile: str = None,
        meshcolor: Vec3 = None,
        meshscale: Vec3 = None,
        meshrt: Vec3 = None,
        meshxyz: Vec3 = None,
        patch: list[Vec3] = None,
        markers: dict[dict] = {},
    ):
        label = label or RightHand.__name__

        xyz = RightHand.get_origin(human) - RightForearm.get_origin(human)
        translations = ""

        # using Segment to have rel_inertia
        segment = yeadon.segment.Segment("", O.reshape(3, 1), np.eye(3), human.B2.solids[2:], O, False)
        mass = segment.mass
        com = np.asarray(segment.rel_center_of_mass).reshape(3)
        inertia = segment.rel_inertia
        meshscale = RightHand.adapted_meshscale(human)
        markers = parse_markers(label, markers)

        BioModSegment.__init__(
            self,
            label=label,
            parent=parent,
            rt=rt,
            xyz=xyz,
            translations=translations,
            rotations=rotations,
            com=com,
            mass=mass,
            inertia=inertia,
            rangesQ=rangesQ,
            mesh=mesh,
            meshfile=meshfile,
            meshcolor=meshcolor,
            meshscale=meshscale,
            meshrt=meshrt,
            meshxyz=meshxyz,
            patch=patch,
            markers=markers,
        )

    @staticmethod
    def adapted_meshscale(human: yeadon.Human):
        m_x = human.meas.get("Lb5w") / 0.098
        m_y = human.meas.get("Lb5w") / 0.098
        m_z = human.meas.get("Lb7L") / 0.177
        return [m_x, m_y, m_z]

    @staticmethod
    def get_origin(human: yeadon.Human):
        """Get the origin of the RightHand in the global frame centered at Pelvis' COM."""
        length = human.B2.solids[0].height + human.B2.solids[1].height
        dir = human.B2.end_pos - human.B2.pos
        dir = dir / np.linalg.norm(dir)
        pos = human.B2.pos + length * dir
        return np.asarray(pos - human.P.center_of_mass).reshape(3)


class LeftThigh(BioModSegment):
    def __init__(
        self,
        human: yeadon.Human,
        label: str = "",
        parent: str = Pelvis.__name__,
        rt: Vec3 = O,
        rotations: str = "",
        rangesQ: list[Vec2] = None,
        mesh: list[Vec3] = [(0, 0, 0)],
        meshfile: str = None,
        meshcolor: Vec3 = None,
        meshscale: Vec3 = None,
        meshrt: Vec3 = None,
        meshxyz: Vec3 = None,
        patch: list[Vec3] = None,
        markers: dict[dict] = {},
    ):
        label = label or LeftThigh.__name__

        xyz = LeftThigh.get_origin(human) - Pelvis.get_origin(human)
        translations = ""
        com = np.asarray(human.J1.rel_center_of_mass).reshape(3)
        mass = human.J1.mass
        inertia = human.J1.rel_inertia
        meshscale = LeftThigh.adapted_meshscale(human)
        markers = parse_markers(label, markers)

        BioModSegment.__init__(
            self,
            label=label,
            parent=parent,
            rt=rt,
            xyz=xyz,
            translations=translations,
            rotations=rotations,
            com=com,
            mass=mass,
            inertia=inertia,
            rangesQ=rangesQ,
            mesh=mesh,
            meshfile=meshfile,
            meshcolor=meshcolor,
            meshscale=meshscale,
            meshrt=meshrt,
            meshxyz=meshxyz,
            patch=patch,
            markers=markers,
        )

    @staticmethod
    def adapted_meshscale(human: yeadon.Human):
        m_x = ((human.meas.get("Lj2p")) / pi) / 0.174
        m_y = ((human.meas.get("Lj2p")) / pi) / 0.174
        m_z = human.meas.get("Lj3L") / 0.4135
        return [m_x, m_y, m_z]

    @staticmethod
    def get_origin(human: yeadon.Human) -> Vec3:
        """Get the origin of the LeftTigh in the global frame centered at Pelvis' COM."""
        return np.asarray(human.J1.pos - human.P.center_of_mass).reshape(3)


class LeftShank(BioModSegment):
    def __init__(
        self,
        human: yeadon.Human,
        label: str = "",
        parent: str = LeftThigh.__name__,
        rt: Vec3 = O,
        rotations: str = "",
        rangesQ: list[Vec2] = None,
        mesh: list[Vec3] = [(0, 0, 0)],
        meshfile: str = None,
        meshcolor: Vec3 = None,
        meshscale: Vec3 = None,
        meshrt: Vec3 = None,
        meshxyz: Vec3 = None,
        patch: list[Vec3] = None,
        markers: dict[dict] = {},
    ):
        label = label or LeftShank.__name__

        xyz = LeftShank.get_origin(human) - LeftThigh.get_origin(human)
        translations = ""

        # using Segment to have rel_inertia
        segment = yeadon.segment.Segment("", O.reshape(3, 1), np.eye(3), human.J2.solids[:2], O, False)
        mass = segment.mass
        com = np.asarray(segment.rel_center_of_mass).reshape(3)
        inertia = segment.rel_inertia
        meshscale = LeftShank.adapted_meshscale(human)
        markers = parse_markers(label, markers)

        BioModSegment.__init__(
            self,
            label=label,
            parent=parent,
            rt=rt,
            xyz=xyz,
            translations=translations,
            rotations=rotations,
            com=com,
            mass=mass,
            inertia=inertia,
            rangesQ=rangesQ,
            mesh=mesh,
            meshfile=meshfile,
            meshcolor=meshcolor,
            meshscale=meshscale,
            meshrt=meshrt,
            meshxyz=meshxyz,
            patch=patch,
            markers=markers,
        )

    @staticmethod
    def adapted_meshscale(human: yeadon.Human):
        m_x = ((human.meas.get("Lj4p")) / pi) / 0.121
        m_y = ((human.meas.get("Lj4p")) / pi) / 0.121
        m_z = (human.meas.get("Lj5L") - human.meas.get("Lj3L")) / 0.3815
        return [m_x, m_y, m_z]

    @staticmethod
    def get_origin(human: yeadon.Human) -> Vec3:
        """Get the origin of the LeftShank in the global frame centered at Pelvis' COM."""
        return np.asarray(human.J2.pos - human.P.center_of_mass).reshape(3)


class LeftFoot(BioModSegment):
    def __init__(
        self,
        human: yeadon.Human,
        label: str = "",
        parent: str = LeftShank.__name__,
        rt: Vec3 = O,
        rotations: str = "",
        rangesQ: list[Vec2] = None,
        mesh: list[Vec3] = [(0, 0, 0)],
        meshfile: str = None,
        meshcolor: Vec3 = None,
        meshscale: Vec3 = None,
        meshrt: Vec3 = None,
        meshxyz: Vec3 = None,
        patch: list[Vec3] = None,
        markers: dict[dict] = {},
    ):
        label = label or LeftFoot.__name__

        xyz = LeftFoot.get_origin(human) - LeftShank.get_origin(human)
        translations = ""

        # using Segment to have rel_inertia
        segment = yeadon.segment.Segment("", O.reshape(3, 1), np.eye(3), human.J2.solids[2:], O, False)
        mass = segment.mass
        com = np.asarray(segment.rel_center_of_mass).reshape(3)
        inertia = segment.rel_inertia
        meshscale = LeftFoot.adapted_meshscale(human)
        markers = parse_markers(label, markers)

        BioModSegment.__init__(
            self,
            label=label,
            parent=parent,
            rt=rt,
            xyz=xyz,
            translations=translations,
            rotations=rotations,
            com=com,
            mass=mass,
            inertia=inertia,
            rangesQ=rangesQ,
            mesh=mesh,
            meshfile=meshfile,
            meshcolor=meshcolor,
            meshscale=meshscale,
            meshrt=meshrt,
            meshxyz=meshxyz,
            patch=patch,
            markers=markers,
        )

    @staticmethod
    def adapted_meshscale(human: yeadon.Human):
        m_x = ((human.meas.get("Lj6p")) / (2 * pi)) / 0.04806479281375239
        # m_x = (human.meas.get('Lj9L') - human.meas.get('Lj6L')) / 0.188
        m_y = human.meas.get("Lj6d") / 0.121
        # m_y = ((human.meas.get('Lj8w')) / pi) / 0.06
        m_z = (human.meas.get("Lj9L")) / 0.208
        return [m_x, m_y, m_z]

    @staticmethod
    def get_origin(human: yeadon.Human):
        """Get the origin of the LeftFoot in the global frame centered at Pelvis' COM."""
        length = human.J2.solids[0].height + human.J2.solids[1].height
        dir = human.J2.end_pos - human.J2.pos
        dir = dir / np.linalg.norm(dir)
        pos = human.J2.pos + length * dir
        return np.asarray(pos - human.P.center_of_mass).reshape(3)


class RightThigh(BioModSegment):
    def __init__(
        self,
        human: yeadon.Human,
        label: str = "",
        parent: str = Pelvis.__name__,
        rt: Vec3 = O,
        rotations: str = "",
        rangesQ: list[Vec2] = None,
        mesh: list[Vec3] = [(0, 0, 0)],
        meshfile: str = None,
        meshcolor: Vec3 = None,
        meshscale: Vec3 = None,
        meshrt: Vec3 = None,
        meshxyz: Vec3 = None,
        patch: list[Vec3] = None,
        markers: dict[dict] = {},
    ):
        label = label or RightThigh.__name__

        xyz = RightThigh.get_origin(human) - Pelvis.get_origin(human)
        translations = ""
        com = np.asarray(human.K1.rel_center_of_mass).reshape(3)
        mass = human.K1.mass
        inertia = human.K1.rel_inertia
        meshscale = RightThigh.adapted_meshscale(human)
        markers = parse_markers(label, markers)

        BioModSegment.__init__(
            self,
            label=label,
            parent=parent,
            rt=rt,
            xyz=xyz,
            translations=translations,
            rotations=rotations,
            com=com,
            mass=mass,
            inertia=inertia,
            rangesQ=rangesQ,
            mesh=mesh,
            meshfile=meshfile,
            meshcolor=meshcolor,
            meshscale=meshscale,
            meshrt=meshrt,
            meshxyz=meshxyz,
            patch=patch,
            markers=markers,
        )

    @staticmethod
    def adapted_meshscale(human: yeadon.Human):
        m_x = ((human.meas.get("Lk2p")) / pi) / 0.174
        m_y = ((human.meas.get("Lk2p")) / pi) / 0.174
        m_z = human.meas.get("Lk3L") / 0.4135
        return [m_x, m_y, m_z]

    @staticmethod
    def get_origin(human: yeadon.Human) -> Vec3:
        """Get the origin of the RightTigh in the global frame centered at Pelvis' COM."""
        return np.asarray(human.K1.pos - human.P.center_of_mass).reshape(3)


class RightShank(BioModSegment):
    def __init__(
        self,
        human: yeadon.Human,
        label: str = "",
        parent: str = RightThigh.__name__,
        rt: Vec3 = O,
        rotations: str = "",
        rangesQ: list[Vec2] = None,
        mesh: list[Vec3] = [(0, 0, 0)],
        meshfile: str = None,
        meshcolor: Vec3 = None,
        meshscale: Vec3 = None,
        meshrt: Vec3 = None,
        meshxyz: Vec3 = None,
        patch: list[Vec3] = None,
        markers: dict[dict] = {},
    ):
        label = label or RightShank.__name__

        xyz = RightShank.get_origin(human) - RightThigh.get_origin(human)
        translations = ""

        # using Segment to have rel_inertia
        segment = yeadon.segment.Segment("", O.reshape(3, 1), np.eye(3), human.K2.solids[:2], O, False)
        mass = segment.mass
        com = np.asarray(segment.rel_center_of_mass).reshape(3)
        inertia = segment.rel_inertia
        meshscale = RightShank.adapted_meshscale(human)
        markers = parse_markers(label, markers)

        BioModSegment.__init__(
            self,
            label=label,
            parent=parent,
            rt=rt,
            xyz=xyz,
            translations=translations,
            rotations=rotations,
            com=com,
            mass=mass,
            inertia=inertia,
            rangesQ=rangesQ,
            mesh=mesh,
            meshfile=meshfile,
            meshcolor=meshcolor,
            meshscale=meshscale,
            meshrt=meshrt,
            meshxyz=meshxyz,
            patch=patch,
            markers=markers,
        )

    @staticmethod
    def adapted_meshscale(human: yeadon.Human):
        m_x = ((human.meas.get("Lk4p")) / pi) / 0.121
        m_y = ((human.meas.get("Lk4p")) / pi) / 0.121
        m_z = (human.meas.get("Lk5L") - human.meas.get("Lj3L")) / 0.3815
        return [m_x, m_y, m_z]

    @staticmethod
    def get_origin(human: yeadon.Human) -> Vec3:
        """Get the origin of the RightShank in the global frame centered at Pelvis' COM."""
        return np.asarray(human.K2.pos - human.P.center_of_mass).reshape(3)


class RightFoot(BioModSegment):
    def __init__(
        self,
        human: yeadon.Human,
        label: str = "",
        parent: str = RightShank.__name__,
        rt: Vec3 = O,
        rotations: str = "",
        rangesQ: list[Vec2] = None,
        mesh: list[Vec3] = [(0, 0, 0)],
        meshfile: str = None,
        meshcolor: Vec3 = None,
        meshscale: Vec3 = None,
        meshrt: Vec3 = None,
        meshxyz: Vec3 = None,
        patch: list[Vec3] = None,
        markers: dict[dict] = {},
    ):
        label = label or RightFoot.__name__

        xyz = RightFoot.get_origin(human) - RightShank.get_origin(human)
        translations = ""

        # using Segment to have rel_inertia
        segment = yeadon.segment.Segment("", O.reshape(3, 1), np.eye(3), human.K2.solids[2:], O, False)
        mass = segment.mass
        com = np.asarray(segment.rel_center_of_mass).reshape(3)
        inertia = segment.rel_inertia
        meshscale = RightFoot.adapted_meshscale(human)
        markers = parse_markers(label, markers)

        BioModSegment.__init__(
            self,
            label=label,
            parent=parent,
            rt=rt,
            xyz=xyz,
            translations=translations,
            rotations=rotations,
            com=com,
            mass=mass,
            inertia=inertia,
            rangesQ=rangesQ,
            mesh=mesh,
            meshfile=meshfile,
            meshcolor=meshcolor,
            meshscale=meshscale,
            meshrt=meshrt,
            meshxyz=meshxyz,
            patch=patch,
            markers=markers,
        )

    @staticmethod
    def adapted_meshscale(human: yeadon.Human):
        m_x = ((human.meas.get("Lk6p")) / (2 * pi)) / 0.04933803235848756
        # m_x = (human.meas.get('Lj9L') - human.meas.get('Lj6L')) / 0.188
        m_y = (human.meas.get("Lk6d")) / 0.122
        # m_y = ((human.meas.get('Lj8w')) / pi) / 0.06
        m_z = (human.meas.get("Lk9L")) / 0.2
        return [m_x, m_y, m_z]

    @staticmethod
    def get_origin(human: yeadon.Human):
        """Get the origin of the RightFoot in the global frame centered at Pelvis' COM."""
        length = human.K2.solids[0].height + human.K2.solids[1].height
        dir = human.K2.end_pos - human.K2.pos
        dir = dir / np.linalg.norm(dir)
        pos = human.K2.pos + length * dir
        return np.asarray(pos - human.P.center_of_mass).reshape(3)


class Thighs(BioModSegment):
    """The tighs of a human if they must remain together."""

    def __init__(
        self,
        human: yeadon.Human,
        label: str = "",
        parent: str = Pelvis.__name__,
        rt: Vec3 = O,
        rotations: str = "",
        rangesQ: list[Vec2] = None,
        mesh: list[Vec3] = [(0, 0, 0)],
        meshfile: str = None,
        meshcolor: Vec3 = None,
        meshscale: Vec3 = None,
        meshrt: Vec3 = None,
        meshxyz: Vec3 = None,
        patch: list[Vec3] = None,
        markers: dict[dict] = {},
    ):
        label = label or Thighs.__name__
        xyz = Thighs.get_origin(human) - Pelvis.get_origin(human)
        translations = ""

        mass, com_global, inertia = human.combine_inertia(("J1", "K1"))
        com = np.asarray(com_global - human.P.center_of_mass).reshape(3) - Thighs.get_origin(human)
        m_x, m_y, m_z = np.array(RightThigh.adapted_meshscale(human)) + np.array(LeftThigh.adapted_meshscale(human))
        meshscale = [np.array(m_x / 2), m_y / 2, m_z / 2]
        markers = parse_markers(label, markers)

        BioModSegment.__init__(
            self,
            label=label,
            parent=parent,
            rt=rt,
            xyz=xyz,
            translations=translations,
            rotations=rotations,
            com=com,
            mass=mass,
            inertia=inertia,  # I can do this because the systems of coordinates are aligned.
            rangesQ=rangesQ,
            mesh=mesh,
            meshfile=meshfile,
            meshcolor=meshcolor,
            meshscale=meshscale,
            meshrt=meshrt,
            meshxyz=meshxyz,
            patch=patch,
            markers=markers,
        )

    @staticmethod
    def get_origin(human: yeadon.Human) -> Vec3:
        """Get the origin of the Tighs in the global frame centered at Pelvis' COM."""
        return np.asarray(human.P.pos - human.P.center_of_mass).reshape(3)


class Shanks(BioModSegment):
    """The shanks of a human if they must remain together."""

    def __init__(
        self,
        human: yeadon.Human,
        label: str = "",
        parent: str = Thighs.__name__,
        rt: Vec3 = O,
        rotations: str = "",
        rangesQ: list[Vec2] = None,
        mesh: list[Vec3] = [(0, 0, 0)],
        meshfile: str = None,
        meshcolor: Vec3 = None,
        meshscale: Vec3 = None,
        meshrt: Vec3 = None,
        meshxyz: Vec3 = None,
        patch: list[Vec3] = None,
        markers: dict[dict] = {},
    ):
        label = label or Shanks.__name__
        xyz = Shanks.get_origin(human) - Thighs.get_origin(human)
        translations = ""

        mass, com_global, inertia = human.combine_inertia(("j3", "j4", "k3", "k4"))
        com = np.asarray(com_global - human.P.center_of_mass).reshape(3) - Shanks.get_origin(human)
        m_x, m_y, m_z = np.array(RightShank.adapted_meshscale(human)) + np.array(LeftShank.adapted_meshscale(human))
        meshscale = [m_x / 2, m_y / 2, m_z / 2]
        markers = parse_markers(label, markers)

        BioModSegment.__init__(
            self,
            label=label,
            parent=parent,
            rt=rt,
            xyz=xyz,
            translations=translations,
            rotations=rotations,
            com=com,
            mass=mass,
            inertia=inertia,  # I can do this because the systems of coordinates are aligned.
            rangesQ=rangesQ,
            mesh=mesh,
            meshfile=meshfile,
            meshcolor=meshcolor,
            meshscale=meshscale,
            meshrt=meshrt,
            meshxyz=meshxyz,
            patch=patch,
            markers=markers,
        )

    @staticmethod
    def get_origin(human: yeadon.Human) -> Vec3:
        """Get the origin of the ShanksAndFeet in the global frame centered at Pelvis' COM."""
        return np.asarray((human.J2.pos + human.K2.pos) / 2.0 - human.P.center_of_mass).reshape(3)


class Feet(BioModSegment):
    """The shanks and feet of a human if they must remain together."""

    def __init__(
        self,
        human: yeadon.Human,
        label: str = "",
        parent: str = Shanks.__name__,
        rt: Vec3 = O,
        rotations: str = "",
        rangesQ: list[Vec2] = None,
        mesh: list[Vec3] = [(0, 0, 0)],
        meshfile: str = None,
        meshcolor: Vec3 = None,
        meshscale: Vec3 = None,
        meshrt: Vec3 = None,
        meshxyz: Vec3 = None,
        patch: list[Vec3] = None,
        markers: dict[dict] = {},
    ):
        label = label or Feet.__name__

        xyz = Feet.get_origin(human) - Shanks.get_origin(human)
        translations = ""

        mass, com_global, inertia = human.combine_inertia(("j5", "j6", "j7", "j8", "k5", "k6", "k7", "k8"))
        com = np.asarray(com_global - human.P.center_of_mass).reshape(3) - Feet.get_origin(human)
        m_x, m_y, m_z = np.array(RightFoot.adapted_meshscale(human)) + np.array(LeftFoot.adapted_meshscale(human))
        meshscale = [m_x / 2, m_y / 2, m_z / 2]
        parse_markers(label, markers)

        BioModSegment.__init__(
            self,
            label=label,
            parent=parent,
            rt=rt,
            xyz=xyz,
            translations=translations,
            rotations=rotations,
            com=com,
            mass=mass,
            inertia=inertia,  # I can do this because the systems of coordinates are aligned.
            rangesQ=rangesQ,
            mesh=mesh,
            meshfile=meshfile,
            meshcolor=meshcolor,
            meshscale=meshscale,
            meshrt=meshrt,
            meshxyz=meshxyz,
            patch=patch,
            markers=markers,
        )

    @staticmethod
    def get_origin(human: yeadon.Human) -> Vec3:
        """Get the origin of the Feet in the global frame centered at Pelvis' COM."""
        length = (
            human.J2.solids[0].height
            + human.J2.solids[1].height
            + human.K2.solids[0].height
            + human.K2.solids[1].height
        ) / 2.0
        dir_J = human.K2.end_pos - human.K2.pos
        dir_K = human.K2.end_pos - human.K2.pos
        dir = (dir_J + dir_K) / 2.0
        dir = dir / np.linalg.norm(dir)
        pos = (human.J2.pos + human.K2.pos) / 2.0 + length * dir
        return np.asarray(pos - human.P.center_of_mass).reshape(3)


class BioModHuman:
    def __init__(self, human: yeadon.Human, gravity: Vec3 = None, **segments_options):
        self.gravity = gravity
        self.pelvis = Pelvis(human, **segments_options[Pelvis.__name__] if Pelvis.__name__ in segments_options else {})
        self.thorax = Thorax(
            human,
            parent=self.pelvis.label,
            **segments_options[Thorax.__name__] if Thorax.__name__ in segments_options else {},
        )
        self.head = Head(
            human,
            parent=self.thorax.label,
            **segments_options[Head.__name__] if Head.__name__ in segments_options else {},
        )
        self.right_upper_arm = RightUpperArm(
            human,
            parent=self.thorax.label,
            **segments_options[RightUpperArm.__name__] if RightUpperArm.__name__ in segments_options else {},
        )
        self.right_forearm = RightForearm(
            human,
            parent=self.right_upper_arm.label,
            **segments_options[RightForearm.__name__] if RightForearm.__name__ in segments_options else {},
        )
        self.right_hand = RightHand(
            human,
            parent=self.right_forearm.label,
            **segments_options[RightHand.__name__] if RightHand.__name__ in segments_options else {},
        )
        self.left_upper_arm = LeftUpperArm(
            human,
            parent=self.thorax.label,
            **segments_options[LeftUpperArm.__name__] if LeftUpperArm.__name__ in segments_options else {},
        )
        self.left_forearm = LeftForearm(
            human,
            parent=self.left_upper_arm.label,
            **segments_options[LeftForearm.__name__] if LeftForearm.__name__ in segments_options else {},
        )
        self.left_hand = LeftHand(
            human,
            parent=self.left_forearm.label,
            **segments_options[LeftHand.__name__] if LeftHand.__name__ in segments_options else {},
        )
        self.right_thigh = RightThigh(
            human,
            parent=self.pelvis.label,
            **segments_options[RightThigh.__name__] if RightThigh.__name__ in segments_options else {},
        )
        self.right_shank = RightShank(
            human,
            parent=self.right_thigh.label,
            **segments_options[RightShank.__name__] if RightShank.__name__ in segments_options else {},
        )
        self.right_foot = RightFoot(
            human,
            parent=self.right_shank.label,
            **segments_options[RightFoot.__name__] if RightFoot.__name__ in segments_options else {},
        )
        self.left_thigh = LeftThigh(
            human,
            parent=self.pelvis.label,
            **segments_options[LeftThigh.__name__] if LeftThigh.__name__ in segments_options else {},
        )
        self.left_shank = LeftShank(
            human,
            parent=self.left_thigh.label,
            **segments_options[LeftShank.__name__] if LeftShank.__name__ in segments_options else {},
        )
        self.left_foot = LeftFoot(
            human,
            parent=self.left_shank.label,
            **segments_options[LeftFoot.__name__] if LeftFoot.__name__ in segments_options else {},
        )

    def __str__(self):
        biomod = "version 4\n\nroot_actuated 0\nexternal_forces 0\n\n"
        if self.gravity:
            biomod += f"gravity {format_vec(self.gravity)}\n\n"
        biomod += f"{self.pelvis}\n\n"
        biomod += f"{self.thorax}\n\n"
        biomod += f"{self.head}\n\n"
        biomod += f"{self.right_upper_arm}\n\n"
        biomod += f"{self.right_forearm}\n\n"
        biomod += f"{self.right_hand}\n\n"
        biomod += f"{self.left_upper_arm}\n\n"
        biomod += f"{self.left_forearm}\n\n"
        biomod += f"{self.left_hand}\n\n"
        biomod += f"{self.right_thigh}\n\n"
        biomod += f"{self.right_shank}\n\n"
        biomod += f"{self.right_foot}\n\n"
        biomod += f"{self.left_thigh}\n\n"
        biomod += f"{self.left_shank}\n\n"
        biomod += f"{self.left_foot}\n"

        return biomod


class BioModHumanFusedLegs:
    def __init__(self, human: yeadon.Human, gravity: Vec3 = None, **segments_options):
        self.gravity = gravity
        self.pelvis = Pelvis(human, **segments_options[Pelvis.__name__] if Pelvis.__name__ in segments_options else {})
        self.thorax = Thorax(
            human,
            parent=self.pelvis.label,
            **segments_options[Thorax.__name__] if Thorax.__name__ in segments_options else {},
        )
        self.head = Head(
            human,
            parent=self.thorax.label,
            **segments_options[Head.__name__] if Head.__name__ in segments_options else {},
        )
        self.right_upper_arm = RightUpperArm(
            human,
            parent=self.thorax.label,
            **segments_options[RightUpperArm.__name__] if RightUpperArm.__name__ in segments_options else {},
        )
        self.right_forearm = RightForearm(
            human,
            parent=self.right_upper_arm.label,
            **segments_options[RightForearm.__name__] if RightForearm.__name__ in segments_options else {},
        )
        self.right_hand = RightHand(
            human,
            parent=self.right_forearm.label,
            **segments_options[RightHand.__name__] if RightHand.__name__ in segments_options else {},
        )
        self.left_upper_arm = LeftUpperArm(
            human,
            parent=self.thorax.label,
            **segments_options[LeftUpperArm.__name__] if LeftUpperArm.__name__ in segments_options else {},
        )
        self.left_forearm = LeftForearm(
            human,
            parent=self.left_upper_arm.label,
            **segments_options[LeftForearm.__name__] if LeftForearm.__name__ in segments_options else {},
        )
        self.left_hand = LeftHand(
            human,
            parent=self.left_forearm.label,
            **segments_options[LeftHand.__name__] if LeftHand.__name__ in segments_options else {},
        )
        self.thighs = Thighs(
            human,
            parent=self.pelvis.label,
            **segments_options[Thighs.__name__] if Thighs.__name__ in segments_options else {},
        )
        self.shanks = Shanks(
            human,
            parent=self.thighs.label,
            **segments_options[Shanks.__name__] if Shanks.__name__ in segments_options else {},
        )
        self.feet = Feet(
            human,
            parent=self.shanks.label,
            **segments_options[Feet.__name__] if Feet.__name__ in segments_options else {},
        )

    def __str__(self):
        biomod = "version 4\n\nroot_actuated 0\nexternal_forces 0\n\n"
        if self.gravity:
            biomod += f"gravity {format_vec(self.gravity)}\n\n"
        biomod += f"{self.pelvis}\n\n"
        biomod += f"{self.thorax}\n\n"
        biomod += f"{self.head}\n\n"
        biomod += f"{self.right_upper_arm}\n\n"
        biomod += f"{self.right_forearm}\n\n"
        biomod += f"{self.right_hand}\n\n"
        biomod += f"{self.left_upper_arm}\n\n"
        biomod += f"{self.left_forearm}\n\n"
        biomod += f"{self.left_hand}\n\n"
        biomod += f"{self.thighs}\n\n"
        biomod += f"{self.shanks}\n\n"
        biomod += f"{self.feet}\n\n"

        return biomod


def parse_biomod_options(filename):
    Human = BioModHuman
    human_options = {}
    segments_options = {}

    if not filename:
        return Human, human_options, segments_options

    with open(filename) as f:
        biomod_options = yaml.safe_load(f.read())

    if "Human" in biomod_options:
        human_options = biomod_options["Human"]
        del biomod_options["Human"]
        if "fused" in human_options:
            if human_options["fused"]:
                Human = BioModHumanFusedLegs
            del human_options["fused"]

    segments_options = biomod_options

    # TODO: have segments_options be more defined to be able to clean BioModHuman's __init__
    return Human, human_options, segments_options


if __name__ == "__main__":
    # import argparse

    DEBUG_FLAG = False

    if DEBUG_FLAG:

        class Arguments:
            def __init__(self):
                self.meas = "/home/lim/Documents/Stage_Lisa/AnthropoImpactOnTech/Models/KaFu.txt"
                self.bioModOptions = ["tech_opt.yml"]

        args = Arguments()

    else:
        import argparse

        parser = argparse.ArgumentParser(description="Convert yeadon human model to bioMod.")
        parser.add_argument("meas", help="measurement file of the human")
        parser.add_argument("--bioModOptions", nargs=1, help="option file for the bioMod")
        args = parser.parse_args()

    bioModOptions = args.bioModOptions[0] if args.bioModOptions else None

    human = yeadon.Human(args.meas)

    BioHuman, human_options, segments_options = parse_biomod_options(bioModOptions)

    biohuman = BioHuman(human, **human_options, **segments_options)

    print(biohuman)
