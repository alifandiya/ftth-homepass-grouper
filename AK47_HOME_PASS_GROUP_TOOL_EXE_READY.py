"""
GUI Grouping Homepassed Berdasarkan Boundary FAT - Advanced v6 Modern UI No Flicker
--------------------------------------------------------------
Fungsi utama:
1. Upload file KMZ.
2. Preview daftar folder di dalam KMZ, lalu pilih folder Homepassed, Boundary FAT, dan FAT referensi.
3. Membaca titik Homepassed dari folder yang dipilih.
4. Membaca polygon Boundary FAT dari folder yang dipilih, termasuk inner boundary/hole.
5. Auto naming polygon Boundary FAT berdasarkan placemark FAT di dalam polygon atau FAT terdekat dari tepi polygon.
6. Mengelompokkan titik Homepassed menjadi HP COVER, HP MULTI BOUNDARY, atau HP UNCOVER.
7. Folder HP COVER memakai kode setelah titik terakhir; jika prefix/FDT lebih dari satu, dibuat hierarki prefix -> kode.
8. Optimasi pengecekan titik dengan bounding box filter sebelum point-in-polygon.
9. Membuat output KMZ tanpa laporan Excel/CSV Ringkasan dan Detail Homepassed.
10. Tombol buka folder output setelah proses selesai.

Cara menjalankan:
    python homepassed_boundary_fat_gui_prototype.py

Catatan:
- Tidak membutuhkan library eksternal.
- Menggunakan tkinter bawaan Python.
"""

from __future__ import annotations

import os
import sys
import platform
import subprocess
import tempfile
import threading
import zipfile
import copy
import math
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
import xml.etree.ElementTree as ET

import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk


APP_ICON_FILE = "LOGO_APLIKASI_ALL_SIZE.ico"
APP_USER_MODEL_ID = "AK47.HomePass.GroupTool"


def resource_path(relative_path: str) -> str:
    """Ambil path resource agar aman saat run dari .py maupun .exe PyInstaller."""
    base_path = getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)
    return str(Path(base_path) / relative_path)


KML_NS = "http://www.opengis.net/kml/2.2"
GX_NS = "http://www.google.com/kml/ext/2.2"
ATOM_NS = "http://www.w3.org/2005/Atom"

ET.register_namespace("", KML_NS)
ET.register_namespace("gx", GX_NS)
ET.register_namespace("atom", ATOM_NS)

Coord = Tuple[float, float]
BBox = Tuple[float, float, float, float]  # min_lon, min_lat, max_lon, max_lat

STATUS_COVER = "HP COVER"
STATUS_MULTI = "HP MULTI BOUNDARY"
STATUS_UNCOVER = "HP UNCOVER"

DUPLICATE_MERGE = "Gabungkan boundary dengan nama sama"
DUPLICATE_SPLIT_BY_PATH = "Pisahkan nama duplikat berdasarkan path"

BOUNDARY_NAME_ORIGINAL = "Pakai nama asli polygon"
BOUNDARY_NAME_AUTO_FAT = "Auto: pakai placemark FAT di dalam/dekat polygon"


@dataclass
class HomepassedPoint:
    name: str
    lon: float
    lat: float
    placemark: ET.Element
    source_path: str


@dataclass
class ReferencePoint:
    name: str
    lon: float
    lat: float
    placemark: ET.Element
    source_path: str


@dataclass
class PolygonGeometry:
    outer_ring: List[Coord]
    inner_rings: List[List[Coord]] = field(default_factory=list)
    bbox: Optional[BBox] = None


@dataclass
class BoundaryPolygon:
    name: str
    folder_path: str
    placemark: ET.Element
    polygons: List[PolygonGeometry] = field(default_factory=list)
    bbox: Optional[BBox] = None
    original_name: str = ""
    naming_source: str = "ORIGINAL"
    naming_distance_m: Optional[float] = None
    naming_reference: str = ""
    naming_candidates: List[str] = field(default_factory=list)


@dataclass
class GroupResult:
    homepassed: HomepassedPoint
    status: str
    group_key: str
    boundary_name: str
    boundary_path: str
    matched_boundaries: List[str]
    group_path: List[str] = field(default_factory=list)
    boundary_original_name: str = ""
    boundary_naming_source: str = ""
    boundary_naming_distance_m: Optional[float] = None


# -----------------------------------------------------------------------------
# KML / KMZ helpers
# -----------------------------------------------------------------------------


def local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def qname(name: str) -> str:
    return f"{{{KML_NS}}}{name}"


def norm_text(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def child_text(element: ET.Element, child_name: str, default: str = "") -> str:
    child = element.find(qname(child_name))
    if child is None or child.text is None:
        return default
    return child.text.strip()


def set_child_text(parent: ET.Element, child_name: str, text: str) -> ET.Element:
    child = ET.SubElement(parent, qname(child_name))
    child.text = text
    return child


def iter_child_elements(parent: ET.Element, child_local_name: str) -> Iterable[ET.Element]:
    for child in list(parent):
        if local_name(child.tag) == child_local_name:
            yield child


def iter_descendants(parent: ET.Element, descendant_local_name: str) -> Iterable[ET.Element]:
    for element in parent.iter():
        if local_name(element.tag) == descendant_local_name:
            yield element


def read_kml_from_kmz(kmz_path: str) -> Tuple[ET.ElementTree, ET.Element, str, List[Tuple[str, bytes]]]:
    """Return ElementTree, root, main kml name, and non-kml files for repackaging."""
    with zipfile.ZipFile(kmz_path, "r") as zf:
        names = zf.namelist()
        kml_names = [n for n in names if n.lower().endswith(".kml")]
        if not kml_names:
            raise ValueError("File KMZ tidak memiliki file .kml di dalamnya.")

        main_kml = "doc.kml" if "doc.kml" in kml_names else kml_names[0]
        kml_bytes = zf.read(main_kml)
        extra_files: List[Tuple[str, bytes]] = []
        for name in names:
            if name != main_kml and not name.endswith("/"):
                try:
                    extra_files.append((name, zf.read(name)))
                except Exception:
                    pass

    root = ET.fromstring(kml_bytes)
    tree = ET.ElementTree(root)
    return tree, root, main_kml, extra_files


def find_document(root: ET.Element) -> ET.Element:
    if local_name(root.tag) == "Document":
        return root
    for element in root.iter():
        if local_name(element.tag) == "Document":
            return element
    return root


def placemark_has_geometry(pm: ET.Element, geom_name: str) -> bool:
    return any(local_name(element.tag) == geom_name for element in pm.iter())


def parse_coordinates_text(text: str) -> List[Coord]:
    coords: List[Coord] = []
    if not text:
        return coords
    for raw in text.replace("\n", " ").replace("\t", " ").split():
        parts = raw.split(",")
        if len(parts) < 2:
            continue
        try:
            lon = float(parts[0])
            lat = float(parts[1])
            coords.append((lon, lat))
        except ValueError:
            continue
    return coords


def parse_point(pm: ET.Element) -> Optional[Coord]:
    for point in iter_descendants(pm, "Point"):
        coord_el = point.find(qname("coordinates"))
        if coord_el is not None and coord_el.text:
            coords = parse_coordinates_text(coord_el.text)
            if coords:
                return coords[0]
    return None


def ring_bbox(ring: Sequence[Coord]) -> Optional[BBox]:
    if not ring:
        return None
    lons = [p[0] for p in ring]
    lats = [p[1] for p in ring]
    return (min(lons), min(lats), max(lons), max(lats))


def merge_bboxes(boxes: Sequence[Optional[BBox]]) -> Optional[BBox]:
    valid = [box for box in boxes if box is not None]
    if not valid:
        return None
    return (
        min(box[0] for box in valid),
        min(box[1] for box in valid),
        max(box[2] for box in valid),
        max(box[3] for box in valid),
    )


def bbox_contains_point(bbox: Optional[BBox], point: Coord) -> bool:
    if bbox is None:
        return True
    min_lon, min_lat, max_lon, max_lat = bbox
    lon, lat = point
    return min_lon <= lon <= max_lon and min_lat <= lat <= max_lat


def first_coordinates_under(parent: ET.Element) -> List[Coord]:
    for coord_el in iter_descendants(parent, "coordinates"):
        coords = parse_coordinates_text(coord_el.text or "")
        if len(coords) >= 3:
            return coords
    return []


def parse_polygon_geometries(pm: ET.Element) -> List[PolygonGeometry]:
    """Parse polygon outer rings and inner holes from a Placemark."""
    polygons: List[PolygonGeometry] = []
    for polygon in iter_descendants(pm, "Polygon"):
        outer_ring: List[Coord] = []
        inner_rings: List[List[Coord]] = []

        for child in polygon.iter():
            lname = local_name(child.tag)
            if lname == "outerBoundaryIs" and not outer_ring:
                outer_ring = first_coordinates_under(child)
            elif lname == "innerBoundaryIs":
                inner = first_coordinates_under(child)
                if inner:
                    inner_rings.append(inner)

        if len(outer_ring) >= 3:
            polygons.append(
                PolygonGeometry(
                    outer_ring=outer_ring,
                    inner_rings=inner_rings,
                    bbox=ring_bbox(outer_ring),
                )
            )
    return polygons


def get_folder_paths(root: ET.Element) -> List[str]:
    """Return all folder paths for preview and dropdown selection."""
    paths: List[str] = []
    doc = find_document(root)

    def walk(folder: ET.Element, parent_parts: List[str]) -> None:
        current_name = child_text(folder, "name", "Tanpa Nama")
        current_parts = parent_parts + [current_name]
        current_path = "/".join(part for part in current_parts if part)
        if current_path:
            paths.append(current_path)
        for sub in iter_child_elements(folder, "Folder"):
            walk(sub, current_parts)

    for folder in iter_child_elements(doc, "Folder"):
        walk(folder, [])

    # Fallback untuk struktur KML yang tidak rapi.
    if not paths:
        for folder in iter_descendants(root, "Folder"):
            name = child_text(folder, "name", "Tanpa Nama")
            if name:
                paths.append(name)

    return sorted(dict.fromkeys(paths), key=lambda value: value.lower())


def folder_matches(current_name: str, current_path: str, target: str) -> bool:
    return norm_text(current_name) == norm_text(target) or norm_text(current_path) == norm_text(target)


def collect_matching_folder_placemarks(root: ET.Element, folder_name_or_path: str) -> List[Tuple[ET.Element, str]]:
    """
    Ambil semua Placemark di dalam folder yang namanya/path-nya sama dengan input.
    Placemark pada subfolder ikut diambil.
    """
    target = folder_name_or_path.strip()
    output: List[Tuple[ET.Element, str]] = []

    def walk_folder(folder: ET.Element, path_parts: List[str]) -> None:
        current_name = child_text(folder, "name", "Tanpa Nama")
        current_path = "/".join(path_parts + [current_name]) if current_name else "/".join(path_parts)

        if folder_matches(current_name, current_path, target):
            for pm in iter_descendants(folder, "Placemark"):
                output.append((pm, current_path))
            return

        for sub in iter_child_elements(folder, "Folder"):
            walk_folder(sub, path_parts + [current_name])

    doc = find_document(root)
    for folder in iter_child_elements(doc, "Folder"):
        walk_folder(folder, [])

    # Fallback: cari semua folder secara langsung.
    if not output:
        for folder in iter_descendants(root, "Folder"):
            current_name = child_text(folder, "name", "Tanpa Nama")
            current_path = current_name
            if folder_matches(current_name, current_path, target):
                for pm in iter_descendants(folder, "Placemark"):
                    output.append((pm, current_path))

    return output


def collect_boundaries(root: ET.Element, boundary_folder_name: str) -> List[BoundaryPolygon]:
    raw = collect_matching_folder_placemarks(root, boundary_folder_name)
    boundaries: List[BoundaryPolygon] = []
    for pm, folder_path in raw:
        if not placemark_has_geometry(pm, "Polygon"):
            continue
        name = child_text(pm, "name", "BOUNDARY_TANPA_NAMA")
        polygons = parse_polygon_geometries(pm)
        if not polygons:
            continue
        boundaries.append(
            BoundaryPolygon(
                name=name,
                folder_path=folder_path,
                placemark=pm,
                polygons=polygons,
                bbox=merge_bboxes([poly.bbox for poly in polygons]),
                original_name=name,
            )
        )
    return boundaries


def collect_homepassed(root: ET.Element, homepassed_folder_name: str) -> List[HomepassedPoint]:
    raw = collect_matching_folder_placemarks(root, homepassed_folder_name)
    points: List[HomepassedPoint] = []
    for pm, folder_path in raw:
        if not placemark_has_geometry(pm, "Point"):
            continue
        point = parse_point(pm)
        if point is None:
            continue
        name = child_text(pm, "name", "HOMEPASSED_TANPA_NAMA")
        points.append(HomepassedPoint(name=name, lon=point[0], lat=point[1], placemark=pm, source_path=folder_path))
    return points


def collect_reference_points(root: ET.Element, reference_folder_name: str) -> List[ReferencePoint]:
    """Ambil placemark titik referensi FAT yang dipakai untuk menamai polygon Boundary FAT."""
    raw = collect_matching_folder_placemarks(root, reference_folder_name)
    points: List[ReferencePoint] = []
    for pm, folder_path in raw:
        if not placemark_has_geometry(pm, "Point"):
            continue
        point = parse_point(pm)
        if point is None:
            continue
        name = child_text(pm, "name", "FAT_TANPA_NAMA")
        points.append(ReferencePoint(name=name, lon=point[0], lat=point[1], placemark=pm, source_path=folder_path))
    return points


# -----------------------------------------------------------------------------
# Geometry helpers
# -----------------------------------------------------------------------------


def point_on_segment(point: Coord, a: Coord, b: Coord, eps: float = 1e-10) -> bool:
    px, py = point
    ax, ay = a
    bx, by = b
    cross = (px - ax) * (by - ay) - (py - ay) * (bx - ax)
    if abs(cross) > eps:
        return False
    dot = (px - ax) * (px - bx) + (py - ay) * (py - by)
    return dot <= eps


def point_in_ring(point: Coord, ring: List[Coord]) -> bool:
    """Ray casting. Titik di garis ring dianggap masuk ring."""
    x, y = point
    inside = False
    n = len(ring)
    if n < 3:
        return False

    for i in range(n):
        a = ring[i]
        b = ring[(i + 1) % n]
        if point_on_segment(point, a, b):
            return True
        xi, yi = a
        xj, yj = b
        intersects = ((yi > y) != (yj > y)) and (x < ((xj - xi) * (y - yi) / ((yj - yi) or 1e-30) + xi))
        if intersects:
            inside = not inside
    return inside


def polygon_contains_point(poly: PolygonGeometry, point: Coord) -> bool:
    if not bbox_contains_point(poly.bbox, point):
        return False
    if not point_in_ring(point, poly.outer_ring):
        return False
    # Jika titik berada di innerBoundaryIs/hole, titik dianggap tidak ter-cover.
    for inner in poly.inner_rings:
        if bbox_contains_point(ring_bbox(inner), point) and point_in_ring(point, inner):
            return False
    return True


def boundary_contains_point(boundary: BoundaryPolygon, point: Coord) -> bool:
    if not bbox_contains_point(boundary.bbox, point):
        return False
    return any(polygon_contains_point(poly, point) for poly in boundary.polygons)


def boundary_centroid(boundary: BoundaryPolygon) -> Coord:
    """Centroid sederhana berbasis rata-rata vertex outer ring; cukup untuk tie-break auto naming."""
    coords: List[Coord] = []
    for poly in boundary.polygons:
        coords.extend(poly.outer_ring)
    if not coords:
        if boundary.bbox:
            return ((boundary.bbox[0] + boundary.bbox[2]) / 2, (boundary.bbox[1] + boundary.bbox[3]) / 2)
        return (0.0, 0.0)
    return (sum(p[0] for p in coords) / len(coords), sum(p[1] for p in coords) / len(coords))


def distance_m(a: Coord, b: Coord) -> float:
    """Jarak haversine antarkoordinat dalam meter."""
    lon1, lat1 = a
    lon2, lat2 = b
    radius = 6371008.8
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    h = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.asin(min(1.0, math.sqrt(h)))


def lonlat_to_local_xy(point: Coord, ref_lat: float) -> Tuple[float, float]:
    """Proyeksi lokal ringan untuk hitung jarak titik ke segmen pada area kecil."""
    lon, lat = point
    radius = 6371008.8
    x = math.radians(lon) * radius * math.cos(math.radians(ref_lat))
    y = math.radians(lat) * radius
    return x, y


def point_to_segment_distance_m(point: Coord, a: Coord, b: Coord) -> float:
    ref_lat = (point[1] + a[1] + b[1]) / 3.0
    px, py = lonlat_to_local_xy(point, ref_lat)
    ax, ay = lonlat_to_local_xy(a, ref_lat)
    bx, by = lonlat_to_local_xy(b, ref_lat)
    dx = bx - ax
    dy = by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    qx = ax + t * dx
    qy = ay + t * dy
    return math.hypot(px - qx, py - qy)


def ring_edge_distance_m(point: Coord, ring: Sequence[Coord]) -> float:
    if len(ring) < 2:
        return float("inf")
    return min(point_to_segment_distance_m(point, ring[i], ring[(i + 1) % len(ring)]) for i in range(len(ring)))


def boundary_edge_distance_m(point: Coord, boundary: BoundaryPolygon) -> float:
    distances: List[float] = []
    for poly in boundary.polygons:
        distances.append(ring_edge_distance_m(point, poly.outer_ring))
        for inner in poly.inner_rings:
            distances.append(ring_edge_distance_m(point, inner))
    return min(distances) if distances else float("inf")


def assign_boundary_names_from_references(
    boundaries: List[BoundaryPolygon],
    reference_points: List[ReferencePoint],
    edge_threshold_m: float,
) -> Dict[str, int]:
    """
    Auto naming Boundary FAT.

    Prioritas:
    1. FAT point yang berada di dalam polygon.
    2. Jika tidak ada, FAT point terdekat dari tepi polygon dengan jarak <= edge_threshold_m.
    3. Jika tetap tidak ada, pakai fallback unik agar folder HP COVER tidak tergabung sebagai AREA semua.
    """
    stats = {"inside": 0, "near_edge": 0, "unmatched": 0, "multi_inside": 0, "duplicate_reference": 0}
    used_reference_names: set[str] = set()

    for idx, boundary in enumerate(boundaries, start=1):
        if not boundary.original_name:
            boundary.original_name = boundary.name

        centroid = boundary_centroid(boundary)
        inside = [ref for ref in reference_points if boundary_contains_point(boundary, (ref.lon, ref.lat))]
        boundary.naming_candidates = [ref.name for ref in inside]

        selected: Optional[ReferencePoint] = None
        source = ""
        distance_value: Optional[float] = None

        if inside:
            if len(inside) > 1:
                stats["multi_inside"] += 1
            unused_inside = [ref for ref in inside if ref.name not in used_reference_names]
            pool = unused_inside or inside
            selected = min(pool, key=lambda ref: distance_m((ref.lon, ref.lat), centroid))
            source = "FAT_INSIDE_POLYGON" if len(inside) == 1 else "FAT_INSIDE_POLYGON_MULTI_SELECTED"
            distance_value = 0.0
            stats["inside"] += 1
        else:
            candidates = sorted(
                (boundary_edge_distance_m((ref.lon, ref.lat), boundary), ref)
                for ref in reference_points
            )
            within_threshold = [(dist, ref) for dist, ref in candidates if dist <= edge_threshold_m]
            unused_within = [(dist, ref) for dist, ref in within_threshold if ref.name not in used_reference_names]
            if unused_within:
                distance_value, selected = unused_within[0]
            elif within_threshold:
                distance_value, selected = within_threshold[0]
                stats["duplicate_reference"] += 1

            if selected is not None:
                source = "FAT_NEAREST_EDGE"
                stats["near_edge"] += 1
                boundary.naming_candidates = [f"{selected.name} ({distance_value:.2f} m)"]

        if selected is not None:
            boundary.name = selected.name
            boundary.naming_reference = selected.name
            boundary.naming_source = source
            boundary.naming_distance_m = distance_value
            used_reference_names.add(selected.name)
        else:
            boundary.name = f"UNMATCHED_BOUNDARY_{idx:03d}_{sanitize_filename(boundary.original_name)}"
            boundary.naming_reference = "-"
            boundary.naming_source = "UNMATCHED_KEEP_UNIQUE_FALLBACK"
            boundary.naming_distance_m = None
            stats["unmatched"] += 1

    return stats


def set_or_create_child_text(parent: ET.Element, child_name: str, text: str) -> None:
    child = parent.find(qname(child_name))
    if child is None:
        child = ET.SubElement(parent, qname(child_name))
    child.text = text


def copy_boundary_placemark_with_resolved_name(boundary: BoundaryPolygon) -> ET.Element:
    pm = copy.deepcopy(boundary.placemark)
    # Pada output KMZ, nama polygon hanya memakai karakter setelah titik terakhir.
    # Contoh: XXX.A01 atau FDT1.A01 menjadi A01.
    set_or_create_child_text(pm, "name", output_boundary_display_name(boundary.name))
    return pm


# -----------------------------------------------------------------------------
# Grouping and output builders
# -----------------------------------------------------------------------------


def split_after_last_dot(name: str) -> Tuple[str, str]:
    """Pisahkan nama FAT menjadi prefix dan kode setelah titik terakhir.

    Contoh:
    - FDT1.A01 -> (FDT1, A01)
    - FDT2.A01 -> (FDT2, A01)
    - XXX.A01  -> (XXX, A01)
    - A01      -> ("", A01)
    """
    value = (name or "").strip()
    if "." not in value:
        return "", value or "Tanpa_Nama"
    prefix, suffix = value.rsplit(".", 1)
    prefix = prefix.strip()
    suffix = suffix.strip()
    return prefix, suffix or value


def output_boundary_display_name(name: str) -> str:
    """Nama placemark polygon pada output: hanya kode setelah titik terakhir.

    Contoh:
    - XXX.A01  -> A01
    - FDT1.A01 -> A01
    - A01      -> A01
    """
    return split_after_last_dot(name)[1]


def detect_multi_prefix_mode(boundaries: Sequence[BoundaryPolygon]) -> bool:
    """Aktifkan hierarki parent->child bila ada lebih dari satu prefix sebelum titik."""
    prefixes = {split_after_last_dot(boundary.name)[0] for boundary in boundaries if split_after_last_dot(boundary.name)[0]}
    return len(prefixes) > 1


def output_folder_path_from_name(name: str, use_prefix_hierarchy: bool) -> List[str]:
    """Tentukan path folder output dari nama boundary/FAT yang sudah resolved.

    Aturan:
    - Jika prefix/FDT lebih dari satu: FDT1.A01 -> [FDT1, A01].
    - Jika prefix/FDT tidak lebih dari satu: XXX.A01 -> [A01].
    - Jika tidak ada titik: A01 -> [A01].
    """
    prefix, suffix = split_after_last_dot(name)
    if use_prefix_hierarchy and prefix:
        return [prefix, suffix]
    return [suffix]


def output_folder_path_for_boundary(boundary: BoundaryPolygon, duplicate_mode: str, use_prefix_hierarchy: bool) -> List[str]:
    path = output_folder_path_from_name(boundary.name, use_prefix_hierarchy)
    if duplicate_mode == DUPLICATE_SPLIT_BY_PATH:
        # Tetap hormati opsi split duplikat, tetapi letakkan path asli sebagai level paling depan.
        # Pada mode normal, pengguna cukup memakai opsi gabungkan agar hasil HP COVER menjadi FDT -> A01.
        path_tail = boundary.folder_path.replace("/", " - ").strip()
        if path_tail:
            return [path_tail] + path
    return path


def output_boundary_source_folder_path(boundary: BoundaryPolygon, duplicate_mode: str, use_prefix_hierarchy: bool) -> List[str]:
    """Tentukan folder untuk BOUNDARY FAT SOURCE saja.

    Permintaan output:
    - Multi FDT/prefix: BOUNDARY FAT SOURCE -> FDT1, FDT2, dst.
      Polygon langsung menjadi Placemark di dalam folder FDT, tidak dibuat
      subfolder A01/A02 lagi.
    - Single prefix/tanpa prefix: polygon langsung berada di BOUNDARY FAT SOURCE.

    Nama placemark polygon tetap memakai kode setelah titik terakhir melalui
    copy_boundary_placemark_with_resolved_name(), contoh FDT1.A01 -> A01.
    """
    prefix, _suffix = split_after_last_dot(boundary.name)
    path: List[str] = []

    if use_prefix_hierarchy and prefix:
        path = [prefix]

    if duplicate_mode == DUPLICATE_SPLIT_BY_PATH:
        path_tail = boundary.folder_path.replace("/", " - ").strip()
        if path_tail:
            return [path_tail] + path

    return path


def make_group_key_from_path(path: Sequence[str]) -> str:
    return "/".join(part for part in path if part) or "Tanpa_Nama"


def get_or_create_nested_folder(parent: ET.Element, path: Sequence[str], cache: Dict[Tuple[str, ...], ET.Element]) -> ET.Element:
    current = parent
    current_key: Tuple[str, ...] = tuple()
    for raw_part in path:
        part = (raw_part or "Tanpa_Nama").strip() or "Tanpa_Nama"
        next_key = current_key + (part,)
        if next_key not in cache:
            folder = ET.SubElement(current, qname("Folder"))
            set_child_text(folder, "name", part)
            cache[next_key] = folder
        current = cache[next_key]
        current_key = next_key
    return current


def make_group_key(boundary: BoundaryPolygon, mode: str, use_prefix_hierarchy: bool) -> str:
    return make_group_key_from_path(output_folder_path_for_boundary(boundary, mode, use_prefix_hierarchy))


def group_homepassed(
    homepassed: List[HomepassedPoint],
    boundaries: List[BoundaryPolygon],
    duplicate_mode: str,
) -> List[GroupResult]:
    results: List[GroupResult] = []
    use_prefix_hierarchy = detect_multi_prefix_mode(boundaries)
    for hp in homepassed:
        point = (hp.lon, hp.lat)
        matched = [b for b in boundaries if boundary_contains_point(b, point)]
        matched_paths = [f"{b.folder_path}/{b.name}" for b in matched]

        if not matched:
            results.append(
                GroupResult(
                    homepassed=hp,
                    status=STATUS_UNCOVER,
                    group_key="UNCOVER",
                    boundary_name="-",
                    boundary_path="-",
                    matched_boundaries=[],
                    group_path=["UNCOVER"],
                )
            )
            continue

        first = matched[0]
        if len(matched) > 1:
            results.append(
                GroupResult(
                    homepassed=hp,
                    status=STATUS_MULTI,
                    group_key="MULTI_BOUNDARY",
                    boundary_name=first.name,
                    boundary_path=first.folder_path,
                    matched_boundaries=matched_paths,
                    group_path=["MULTI_BOUNDARY"],
                    boundary_original_name=first.original_name,
                    boundary_naming_source=first.naming_source,
                    boundary_naming_distance_m=first.naming_distance_m,
                )
            )
            continue

        results.append(
            GroupResult(
                homepassed=hp,
                status=STATUS_COVER,
                group_key=make_group_key(first, duplicate_mode, use_prefix_hierarchy),
                boundary_name=first.name,
                boundary_path=first.folder_path,
                matched_boundaries=matched_paths,
                group_path=output_folder_path_for_boundary(first, duplicate_mode, use_prefix_hierarchy),
                boundary_original_name=first.original_name,
                boundary_naming_source=first.naming_source,
                boundary_naming_distance_m=first.naming_distance_m,
            )
        )
    return results


def sanitize_filename(name: str) -> str:
    cleaned = []
    for ch in name:
        if ch.isalnum() or ch in " ._-()[]":
            cleaned.append(ch)
        else:
            cleaned.append("_")
    value = "".join(cleaned).strip()
    return value or "Tanpa_Nama"


def copy_style_like_elements(input_doc: ET.Element, output_doc: ET.Element) -> None:
    """Copy style/schema elements so styleUrl in placemarks still works."""
    allowed = {
        "Style",
        "StyleMap",
        "Schema",
        "LookAt",
        "Camera",
        "Region",
        "NetworkLinkControl",
    }
    for child in list(input_doc):
        lname = local_name(child.tag)
        if lname in allowed:
            output_doc.append(copy.deepcopy(child))


def build_output_kml(
    input_root: ET.Element,
    results: List[GroupResult],
    boundaries: List[BoundaryPolygon],
    include_boundaries: bool,
    output_name: str,
    duplicate_mode: str,
) -> ET.ElementTree:
    root = ET.Element(qname("kml"))
    doc = ET.SubElement(root, qname("Document"))
    set_child_text(doc, "name", output_name)

    input_doc = find_document(input_root)
    copy_style_like_elements(input_doc, doc)

    cover_folder = ET.SubElement(doc, qname("Folder"))
    set_child_text(cover_folder, "name", STATUS_COVER)

    multi_folder = ET.SubElement(doc, qname("Folder"))
    set_child_text(multi_folder, "name", STATUS_MULTI)

    uncover_folder = ET.SubElement(doc, qname("Folder"))
    set_child_text(uncover_folder, "name", STATUS_UNCOVER)

    grouped: Dict[Tuple[str, ...], List[GroupResult]] = {}
    for item in results:
        if item.status == STATUS_COVER:
            group_path = tuple(item.group_path or [item.group_key])
            grouped.setdefault(group_path, []).append(item)
        elif item.status == STATUS_MULTI:
            multi_folder.append(copy.deepcopy(item.homepassed.placemark))
        else:
            uncover_folder.append(copy.deepcopy(item.homepassed.placemark))

    cover_cache: Dict[Tuple[str, ...], ET.Element] = {}
    for group_path in sorted(grouped.keys(), key=lambda v: make_group_key_from_path(v).lower()):
        folder = get_or_create_nested_folder(cover_folder, group_path, cover_cache)
        for item in sorted(grouped[group_path], key=lambda r: r.homepassed.name.lower()):
            folder.append(copy.deepcopy(item.homepassed.placemark))

    if include_boundaries:
        # Boundary FAT/polygon tidak dibuat subfolder kode lagi.
        # Output yang diinginkan untuk multi FDT/prefix:
        # BOUNDARY FAT SOURCE -> FDT1 -> Placemark A01, A02, dst.
        # BOUNDARY FAT SOURCE -> FDT2 -> Placemark A01, A03, dst.
        # Jadi setelah folder FDT1/FDT2 tidak ada folder A01/A02 lagi.
        source_folder = ET.SubElement(doc, qname("Folder"))
        set_child_text(source_folder, "name", "BOUNDARY FAT SOURCE")

        use_prefix_hierarchy = detect_multi_prefix_mode(boundaries)
        boundary_cache: Dict[Tuple[str, ...], ET.Element] = {}
        sorted_boundaries = sorted(
            boundaries,
            key=lambda b: (
                make_group_key_from_path(
                    output_boundary_source_folder_path(b, duplicate_mode, use_prefix_hierarchy)
                ).lower(),
                output_boundary_display_name(b.name).lower(),
            ),
        )
        for boundary in sorted_boundaries:
            boundary_path = output_boundary_source_folder_path(boundary, duplicate_mode, use_prefix_hierarchy)
            folder = get_or_create_nested_folder(source_folder, boundary_path, boundary_cache)
            folder.append(copy_boundary_placemark_with_resolved_name(boundary))

    try:
        ET.indent(root, space="  ")
    except AttributeError:
        pass
    return ET.ElementTree(root)


def write_kmz(kml_tree: ET.ElementTree, output_kmz_path: str, extra_files: List[Tuple[str, bytes]]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        kml_path = os.path.join(tmp, "doc.kml")
        kml_tree.write(kml_path, encoding="utf-8", xml_declaration=True)
        with zipfile.ZipFile(output_kmz_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(kml_path, "doc.kml")
            for name, data in extra_files:
                if name.lower().endswith(".kml"):
                    continue
                zf.writestr(name, data)



# Laporan Ringkasan/Detail Homepassed berbentuk CSV/XLSX sengaja dinonaktifkan.
# Output proses sekarang hanya membuat KMZ grouping agar tidak menghasilkan file seperti:
# - <nama input> RINGKASAN HOMEPASSED.csv
# - <nama input> DETAIL HOMEPASSED.csv
# - <nama input> LAPORAN HOMEPASSED.xlsx


def detect_duplicate_boundaries(boundaries: List[BoundaryPolygon]) -> Dict[str, List[str]]:
    data: Dict[str, List[str]] = {}
    for boundary in boundaries:
        data.setdefault(boundary.name, []).append(boundary.folder_path)
    return {name: paths for name, paths in data.items() if len(paths) > 1}


def process_kmz(
    kmz_path: str,
    output_dir: str,
    homepassed_folder: str,
    boundary_folder: str,
    duplicate_mode: str,
    include_boundaries: bool,
    reference_fat_folder: str = "",
    boundary_naming_mode: str = BOUNDARY_NAME_ORIGINAL,
    edge_threshold_m: float = 5.0,
    progress_callback=None,
) -> Dict[str, object]:
    def log(message: str) -> None:
        if progress_callback:
            progress_callback(message)

    if not os.path.isfile(kmz_path):
        raise FileNotFoundError("File KMZ input tidak ditemukan.")
    if not output_dir:
        raise ValueError("Folder output belum dipilih.")
    os.makedirs(output_dir, exist_ok=True)

    log("Membaca file KMZ...")
    _, root, _, extra_files = read_kml_from_kmz(kmz_path)

    log("Mengambil titik Homepassed...")
    homepassed = collect_homepassed(root, homepassed_folder)
    if not homepassed:
        raise ValueError(f"Tidak ditemukan titik pada folder '{homepassed_folder}'. Cek nama/path folder input.")

    log("Mengambil polygon Boundary FAT...")
    boundaries = collect_boundaries(root, boundary_folder)
    if not boundaries:
        raise ValueError(f"Tidak ditemukan polygon pada folder '{boundary_folder}'. Cek nama/path folder input.")

    boundary_naming_stats = {"inside": 0, "near_edge": 0, "unmatched": 0, "multi_inside": 0, "duplicate_reference": 0}
    total_reference_points = 0
    if boundary_naming_mode == BOUNDARY_NAME_AUTO_FAT:
        if not reference_fat_folder:
            raise ValueError("Folder referensi FAT wajib dipilih jika mode auto naming boundary aktif.")
        log("Mengambil placemark FAT referensi untuk auto naming boundary...")
        reference_points = collect_reference_points(root, reference_fat_folder)
        total_reference_points = len(reference_points)
        if not reference_points:
            raise ValueError(f"Tidak ditemukan titik FAT referensi pada folder '{reference_fat_folder}'.")
        log(f"Auto naming Boundary FAT dari {total_reference_points} titik FAT referensi dengan toleransi tepi {edge_threshold_m:g} meter...")
        boundary_naming_stats = assign_boundary_names_from_references(boundaries, reference_points, edge_threshold_m)
        log(
            "Hasil auto naming boundary: "
            f"inside={boundary_naming_stats['inside']}, "
            f"near_edge={boundary_naming_stats['near_edge']}, "
            f"unmatched={boundary_naming_stats['unmatched']}."
        )

    log("Mengelompokkan Homepassed berdasarkan Boundary FAT dengan bounding box filter...")
    results = group_homepassed(homepassed, boundaries, duplicate_mode)
    use_prefix_hierarchy = detect_multi_prefix_mode(boundaries)
    foldering_mode = "FDT_PREFIX_HIERARCHY" if use_prefix_hierarchy else "SUFFIX_AFTER_LAST_DOT"

    cover_count = sum(1 for r in results if r.status == STATUS_COVER)
    uncover_count = sum(1 for r in results if r.status == STATUS_UNCOVER)
    multi_boundary_count = sum(1 for r in results if r.status == STATUS_MULTI)
    duplicate_boundaries = detect_duplicate_boundaries(boundaries)

    stem = sanitize_filename(Path(kmz_path).stem)
    output_kmz = os.path.join(output_dir, f"{stem} HOMEPASSED GROUPING.kmz")
    log("Membuat output KMZ...")
    kml_tree = build_output_kml(
        input_root=root,
        results=results,
        boundaries=boundaries,
        include_boundaries=include_boundaries,
        output_name=f"{stem} - Homepassed by Boundary FAT",
        duplicate_mode=duplicate_mode,
    )
    write_kmz(kml_tree, output_kmz, extra_files)

    log("Laporan Ringkasan/Detail Homepassed CSV/XLSX dinonaktifkan sesuai permintaan.")

    return {
        "total_homepassed": len(homepassed),
        "total_boundaries": len(boundaries),
        "total_reference_fat": total_reference_points,
        "boundary_naming_stats": boundary_naming_stats,
        "foldering_mode": foldering_mode,
        "cover_count": cover_count,
        "uncover_count": uncover_count,
        "multi_boundary_count": multi_boundary_count,
        "duplicate_boundaries": duplicate_boundaries,
        "output_kmz": output_kmz,
        "output_dir": output_dir,
        "results": results,
    }

# -----------------------------------------------------------------------------
# Modern GUI (CustomTkinter)
# -----------------------------------------------------------------------------

try:
    import customtkinter as ctk
except ImportError as exc:  # pragma: no cover - runtime dependency guard
    message = (
        "customtkinter belum terpasang.\n\n"
        "Jalankan perintah ini di Command Prompt/Terminal:\n"
        "python -m pip install customtkinter\n\n"
        "Setelah itu jalankan ulang aplikasi."
    )
    try:
        root_dep = tk.Tk()
        root_dep.withdraw()
        messagebox.showerror("Dependency belum terpasang", message)
        root_dep.destroy()
    except Exception:
        pass
    print(message)
    try:
        input("\nTekan Enter untuk keluar...")
    except Exception:
        pass
    raise SystemExit(1) from exc

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# Membantu tampilan lebih tajam dan ukuran lebih akurat di Windows high-DPI.
if platform.system().lower() == "windows":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

LANG_INDONESIA = "Indonesia"
LANG_ENGLISH = "English"
LANG_MANDARIN = "中文（普通话）"
GUI_LANGUAGES = [LANG_INDONESIA, LANG_ENGLISH, LANG_MANDARIN]

TEXT = {
    LANG_INDONESIA: {
        "title": "FTTH Automation - Homepassed Boundary Grouping v6",
        "app_title": "📡 AK-47 FTTH Automation",
        "app_subtitle": "Homepassed Boundary Grouping • Modern UI",
        "configuration": "📌 KONFIGURASI",
        "language": "Bahasa GUI",
        "browse_kmz": "📁 Browse KMZ File",
        "file_empty": "Belum ada file dipilih",
        "file_selected": "Dipilih: {filename}",
        "output_folder": "Folder Output",
        "browse_output": "Pilih Folder",
        "open_output": "Buka Output",
        "folders_title": "Pilih Folder KML",
        "homepassed_folder": "Folder Homepassed",
        "boundary_folder": "Folder Boundary FAT",
        "reference_folder": "Folder Referensi FAT",
        "settings_title": "Parameter Grouping",
        "boundary_naming": "Penamaan Boundary",
        "edge_tolerance": "Toleransi tepi FAT (meter)",
        "duplicate_boundary": "Boundary Duplikat",
        "include_boundary": "Sertakan polygon Boundary FAT pada output KMZ",
        "start": "🚀 MULAI PROSES",
        "processing": "Sedang memproses...",
        "clear_log": "Bersihkan Log",
        "summary_title": "📊 Ringkasan Hasil",
        "console_title": "📋 Process Logs & Console",
        "ready": "Siap.",
        "done": "Selesai.",
        "placeholder_load": "-- Load KMZ First --",
        "placeholder_output": "Folder output otomatis di Downloads",
        "naming_auto": "Auto: pakai placemark FAT di dalam/dekat polygon",
        "naming_original": "Pakai nama asli polygon",
        "duplicate_merge": "Gabungkan boundary dengan nama sama",
        "duplicate_split": "Pisahkan nama duplikat berdasarkan path",
        "total_homepassed": "TOTAL HOMEPASSED",
        "total_boundary": "TOTAL BOUNDARY FAT",
        "total_reference": "TOTAL REFERENSI FAT",
        "hp_cover": "HP COVER",
        "hp_multi": "HP MULTI BOUNDARY",
        "hp_uncover": "HP UNCOVER",
        "group_detail": "Detail Kelompok HP COVER",
        "output_kmz": "Output KMZ",
        "copyright": "© 2026 AK-47 Homepassed Grouping Tool. All rights reserved.",
        "select_kmz_title": "Pilih file KMZ",
        "select_output_title": "Pilih folder output",
        "input_incomplete": "Input belum lengkap",
        "invalid_input": "Input tidak valid",
        "no_kmz": "Pilih file KMZ terlebih dahulu.",
        "no_output": "Pilih folder output terlebih dahulu.",
        "no_hp_boundary": "Folder Homepassed dan Boundary FAT wajib diisi/dipilih.",
        "no_reference": "Folder Referensi FAT wajib diisi/dipilih untuk auto naming boundary.",
        "invalid_edge": "Toleransi tepi FAT harus berupa angka meter, contoh: 5 atau 7.5",
        "preview_success": "Preview folder KMZ berhasil: {count} folder ditemukan.",
        "preview_failed_title": "Preview gagal",
        "preview_failed": "Gagal membaca folder KMZ: {error}",
        "folder_not_found_title": "Folder tidak ditemukan",
        "folder_not_found": "Folder output belum tersedia atau tidak ditemukan.",
        "open_failed_title": "Gagal membuka folder",
        "open_failed": "Folder tidak bisa dibuka otomatis: {error}",
        "process_failed_title": "Proses gagal",
        "success_title": "Proses selesai",
        "success_message": "Grouping berhasil dibuat.\n\nHP COVER          : {cover}\nHP MULTI BOUNDARY : {multi}\nHP UNCOVER        : {uncover}\n\nOutput tersimpan di:\n{output_dir}",
        "start_log": "Mulai proses grouping...",
        "no_report": "Laporan Ringkasan/Detail Homepassed CSV/XLSX tidak dibuat.",
        "fdt_mode": "Mode folder output: multi-prefix terdeteksi. HP COVER dibuat hierarki Prefix/FDT -> kode, sedangkan BOUNDARY FAT SOURCE hanya sampai Prefix/FDT tanpa subfolder kode.",
        "suffix_mode": "Mode folder output: single-prefix/normal, nama folder memakai karakter setelah titik terakhir.",
    },
    LANG_ENGLISH: {
        "title": "FTTH Automation - Homepassed Boundary Grouping v6",
        "app_title": "📡 AK-47 FTTH Automation",
        "app_subtitle": "Homepassed Boundary Grouping • Modern UI",
        "configuration": "📌 CONFIGURATION",
        "language": "GUI Language",
        "browse_kmz": "📁 Browse KMZ File",
        "file_empty": "No file selected",
        "file_selected": "Selected: {filename}",
        "output_folder": "Output Folder",
        "browse_output": "Select Folder",
        "open_output": "Open Output",
        "folders_title": "Select KML Folders",
        "homepassed_folder": "Homepassed Folder",
        "boundary_folder": "Boundary FAT Folder",
        "reference_folder": "Reference FAT Folder",
        "settings_title": "Grouping Parameters",
        "boundary_naming": "Boundary Naming",
        "edge_tolerance": "FAT edge tolerance (meters)",
        "duplicate_boundary": "Duplicate Boundary",
        "include_boundary": "Include Boundary FAT polygons in KMZ output",
        "start": "🚀 START PROCESSING",
        "processing": "Processing...",
        "clear_log": "Clear Log",
        "summary_title": "📊 Result Summary",
        "console_title": "📋 Process Logs & Console",
        "ready": "Ready.",
        "done": "Done.",
        "placeholder_load": "-- Load KMZ First --",
        "placeholder_output": "Output folder defaults to Downloads",
        "naming_auto": "Auto: use FAT placemark inside/near polygon",
        "naming_original": "Use original polygon name",
        "duplicate_merge": "Merge boundaries with the same name",
        "duplicate_split": "Split duplicate names by path",
        "total_homepassed": "TOTAL HOMEPASSED",
        "total_boundary": "TOTAL BOUNDARY FAT",
        "total_reference": "TOTAL REFERENCE FAT",
        "hp_cover": "HP COVER",
        "hp_multi": "HP MULTI BOUNDARY",
        "hp_uncover": "HP UNCOVER",
        "group_detail": "HP COVER Group Detail",
        "output_kmz": "Output KMZ",
        "copyright": "© 2026 AK-47 Homepassed Grouping Tool. All rights reserved.",
        "select_kmz_title": "Select KMZ file",
        "select_output_title": "Select output folder",
        "input_incomplete": "Incomplete input",
        "invalid_input": "Invalid input",
        "no_kmz": "Select a KMZ file first.",
        "no_output": "Select an output folder first.",
        "no_hp_boundary": "Homepassed Folder and Boundary FAT Folder must be filled/selected.",
        "no_reference": "Reference FAT Folder must be filled/selected for auto boundary naming.",
        "invalid_edge": "FAT edge tolerance must be a number in meters, for example: 5 or 7.5",
        "preview_success": "KMZ folder preview completed: {count} folders found.",
        "preview_failed_title": "Preview failed",
        "preview_failed": "Failed to read KMZ folders: {error}",
        "folder_not_found_title": "Folder not found",
        "folder_not_found": "The output folder is not available or was not found.",
        "open_failed_title": "Failed to open folder",
        "open_failed": "The folder could not be opened automatically: {error}",
        "process_failed_title": "Process failed",
        "success_title": "Process completed",
        "success_message": "Grouping was created successfully.\n\nHP COVER          : {cover}\nHP MULTI BOUNDARY : {multi}\nHP UNCOVER        : {uncover}\n\nOutput saved to:\n{output_dir}",
        "start_log": "Starting grouping process...",
        "no_report": "Homepassed Summary/Detail CSV/XLSX reports were not created.",
        "fdt_mode": "Output folder mode: multiple prefixes detected. HP COVER uses Prefix/FDT -> code hierarchy, while BOUNDARY FAT SOURCE stops at Prefix/FDT without code subfolders.",
        "suffix_mode": "Output folder mode: single-prefix/normal. Folder names use the characters after the last dot.",
    },
    LANG_MANDARIN: {
        "title": "FTTH Automation - Homepassed Boundary Grouping v6",
        "app_title": "📡 AK-47 FTTH Automation",
        "app_subtitle": "Homepassed Boundary 分组 • 现代界面",
        "configuration": "📌 配置",
        "language": "界面语言",
        "browse_kmz": "📁 浏览 KMZ 文件",
        "file_empty": "尚未选择文件",
        "file_selected": "已选择：{filename}",
        "output_folder": "输出文件夹",
        "browse_output": "选择文件夹",
        "open_output": "打开输出",
        "folders_title": "选择 KML 文件夹",
        "homepassed_folder": "Homepassed 文件夹",
        "boundary_folder": "Boundary FAT 文件夹",
        "reference_folder": "参考 FAT 文件夹",
        "settings_title": "分组参数",
        "boundary_naming": "Boundary 命名",
        "edge_tolerance": "FAT 边缘容差（米）",
        "duplicate_boundary": "重复 Boundary",
        "include_boundary": "在 KMZ 输出中包含 Boundary FAT 多边形",
        "start": "🚀 开始处理",
        "processing": "处理中...",
        "clear_log": "清空日志",
        "summary_title": "📊 结果汇总",
        "console_title": "📋 处理日志与控制台",
        "ready": "就绪。",
        "done": "完成。",
        "placeholder_load": "-- 请先加载 KMZ --",
        "placeholder_output": "输出文件夹默认在 Downloads",
        "naming_auto": "自动：使用多边形内部/附近的 FAT 标记点",
        "naming_original": "使用原始多边形名称",
        "duplicate_merge": "合并同名 boundary",
        "duplicate_split": "按路径拆分重复名称",
        "total_homepassed": "HOMEPASSED 总数",
        "total_boundary": "BOUNDARY FAT 总数",
        "total_reference": "参考 FAT 总数",
        "hp_cover": "HP COVER",
        "hp_multi": "HP MULTI BOUNDARY",
        "hp_uncover": "HP UNCOVER",
        "group_detail": "HP COVER 分组明细",
        "output_kmz": "输出 KMZ",
        "copyright": "© 2026 AK-47 Homepassed 分组工具。保留所有权利。",
        "select_kmz_title": "选择 KMZ 文件",
        "select_output_title": "选择输出文件夹",
        "input_incomplete": "输入不完整",
        "invalid_input": "输入无效",
        "no_kmz": "请先选择 KMZ 文件。",
        "no_output": "请先选择输出文件夹。",
        "no_hp_boundary": "必须填写/选择 Homepassed 文件夹和 Boundary FAT 文件夹。",
        "no_reference": "自动 boundary 命名需要填写/选择参考 FAT 文件夹。",
        "invalid_edge": "FAT 边缘容差必须是米单位数字，例如：5 或 7.5",
        "preview_success": "KMZ 文件夹预览完成：找到 {count} 个文件夹。",
        "preview_failed_title": "预览失败",
        "preview_failed": "读取 KMZ 文件夹失败：{error}",
        "folder_not_found_title": "未找到文件夹",
        "folder_not_found": "输出文件夹尚不可用或未找到。",
        "open_failed_title": "打开文件夹失败",
        "open_failed": "无法自动打开文件夹：{error}",
        "process_failed_title": "处理失败",
        "success_title": "处理完成",
        "success_message": "分组已成功生成。\n\nHP COVER          : {cover}\nHP MULTI BOUNDARY : {multi}\nHP UNCOVER        : {uncover}\n\n输出保存到：\n{output_dir}",
        "start_log": "开始分组处理...",
        "no_report": "未创建 Homepassed 汇总/明细 CSV/XLSX 报告。",
        "fdt_mode": "输出文件夹模式：检测到多个 prefix。HP COVER 使用 Prefix/FDT -> code 层级，BOUNDARY FAT SOURCE 只到 Prefix/FDT，不再创建 code 子文件夹。",
        "suffix_mode": "输出文件夹模式：单 prefix/普通模式，文件夹名使用最后一个点之后的字符。",
    },
}

PROCESS_LOG_TRANSLATIONS = {
    "Membaca file KMZ": {LANG_ENGLISH: "Reading KMZ file...", LANG_MANDARIN: "正在读取 KMZ 文件..."},
    "Mengambil titik Homepassed": {LANG_ENGLISH: "Reading Homepassed points...", LANG_MANDARIN: "正在读取 Homepassed 点..."},
    "Mengambil polygon Boundary FAT": {LANG_ENGLISH: "Reading Boundary FAT polygons...", LANG_MANDARIN: "正在读取 Boundary FAT 多边形..."},
    "Mengambil placemark FAT referensi": {LANG_ENGLISH: "Reading reference FAT placemarks for boundary auto-naming...", LANG_MANDARIN: "正在读取用于 boundary 自动命名的参考 FAT 标记点..."},
    "Mengelompokkan Homepassed": {LANG_ENGLISH: "Grouping Homepassed by Boundary FAT using the bounding-box filter...", LANG_MANDARIN: "正在使用边界框过滤器按 Boundary FAT 对 Homepassed 进行分组..."},
    "Membuat output KMZ": {LANG_ENGLISH: "Creating KMZ output...", LANG_MANDARIN: "正在生成 KMZ 输出..."},
    "Laporan Ringkasan/Detail": {LANG_ENGLISH: "Homepassed Summary/Detail CSV/XLSX reports are disabled as requested.", LANG_MANDARIN: "已按要求禁用 Homepassed 汇总/明细 CSV/XLSX 报告。"},
}


class HomepassedBoundaryGUI(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.configure_dynamic_window()
        self.apply_app_icon()
        self.configure(fg_color=("#F2F4F7", "#151515"))

        self.kmz_path_var = tk.StringVar()
        self.output_dir_var = tk.StringVar(value=str(Path.home() / "Downloads"))
        self.homepassed_folder_var = tk.StringVar(value="Homepased")
        self.boundary_folder_var = tk.StringVar(value="BOUNDARY FAT")
        self.reference_fat_folder_var = tk.StringVar(value="FAT")
        self.edge_threshold_var = tk.StringVar(value="5")
        self.language_var = tk.StringVar(value=LANG_INDONESIA)
        self.status_var = tk.StringVar(value=self.t("ready"))
        self.include_boundaries_var = tk.BooleanVar(value=True)

        self.boundary_naming_mode = BOUNDARY_NAME_AUTO_FAT
        self.duplicate_mode = DUPLICATE_MERGE
        self.kml_folders: List[str] = []
        self.last_output_dir: Optional[str] = None
        self.output_kmz_path: str = ""

        self.title(self.t("title"))
        self._build_ui()
        self.apply_language()
        self.reset_summary_cards()


    def apply_app_icon(self) -> None:
        """Pasang icon aplikasi untuk window, taskbar, dan EXE build."""
        try:
            if platform.system().lower() == "windows":
                try:
                    import ctypes
                    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
                except Exception:
                    pass

            icon_path = resource_path(APP_ICON_FILE)
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception:
            # Icon tidak boleh membuat aplikasi gagal running.
            pass

    def configure_dynamic_window(self) -> None:
        """Atur ukuran awal window secara dinamis untuk laptop 14 inch dan monitor lain."""
        screen_w = max(1, self.winfo_screenwidth())
        screen_h = max(1, self.winfo_screenheight())

        # Sisakan ruang untuk taskbar/dock agar bagian bawah aplikasi tidak terpotong.
        usable_w = max(760, screen_w - 40)
        usable_h = max(540, screen_h - 90)

        target_w = int(screen_w * 0.92)
        target_h = int(screen_h * 0.86)

        # Batas nyaman: cukup lega untuk 1366x768, tidak kebesaran di monitor besar.
        target_w = min(max(target_w, 920), 1280, usable_w)
        target_h = min(max(target_h, 600), 820, usable_h)

        if screen_w <= 1366:
            target_w = min(target_w, usable_w)
        if screen_h <= 800:
            target_h = min(target_h, usable_h)

        min_w = min(target_w, 900)
        min_h = min(target_h, 560)

        pos_x = max(0, (screen_w - target_w) // 2)
        pos_y = max(0, (screen_h - target_h) // 2)

        self.geometry(f"{target_w}x{target_h}+{pos_x}+{pos_y}")
        self.minsize(min_w, min_h)
        self.screen_width = screen_w
        self.screen_height = screen_h

    def responsive_metrics(self) -> Dict[str, int]:
        """Ukuran komponen dibuat adaptif berdasarkan tinggi/lebar layar."""
        screen_w = getattr(self, "screen_width", self.winfo_screenwidth())
        screen_h = getattr(self, "screen_height", self.winfo_screenheight())
        current_w = max(1, self.winfo_width())
        current_h = max(1, self.winfo_height())

        compact_width = screen_w <= 1366 or current_w <= 1120
        compact_height = screen_h <= 800 or current_h <= 700

        return {
            "outer_pad": 10 if compact_width or compact_height else 15,
            "left_width": 340 if compact_width else 390,
            "folder_height": 165 if compact_height else 235,
            "settings_height": 165 if compact_height else 220,
            "log_height": 150 if compact_height else 220,
        }

    def apply_responsive_layout(self) -> None:
        """Perbarui ukuran widget saat window di-resize."""
        if not hasattr(self, "left_panel"):
            return
        metrics = self.responsive_metrics()
        try:
            self.left_panel.configure(width=metrics["left_width"])
            self.folder_frame.configure(height=metrics["folder_height"])
            self.settings_frame.configure(height=metrics["settings_height"])
            self.log_text.configure(height=metrics["log_height"])
        except Exception:
            # Jangan sampai resize event membuat aplikasi gagal jalan.
            pass

    def on_window_resize(self, event: tk.Event) -> None:
        if event.widget is self:
            self.apply_responsive_layout()

    def t(self, key: str) -> str:
        return TEXT.get(self.language_var.get(), TEXT[LANG_INDONESIA]).get(key, key)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        metrics = self.responsive_metrics()
        pad = metrics["outer_pad"]

        self.left_panel = ctk.CTkFrame(self, width=metrics["left_width"], corner_radius=18)
        self.left_panel.grid(row=0, column=0, sticky="ns", padx=pad, pady=pad)
        self.left_panel.grid_propagate(False)

        self.right_panel = ctk.CTkFrame(self, corner_radius=18)
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(0, pad), pady=pad)
        self.right_panel.grid_columnconfigure(0, weight=1)
        self.right_panel.grid_rowconfigure(2, weight=1)
        self.right_panel.grid_rowconfigure(3, weight=1)

        self.footer_label = ctk.CTkLabel(self, text="", font=("Segoe UI", 10), text_color=("#667085", "#A0A0A0"))
        self.footer_label.grid(row=1, column=0, columnspan=2, sticky="ew", padx=pad, pady=(0, max(6, pad - 5)))

        self.setup_left_panel()
        self.setup_right_panel()
        self.apply_responsive_layout()
        self.bind("<Configure>", self.on_window_resize)

    def setup_left_panel(self) -> None:
        self.lbl_app_title = ctk.CTkLabel(self.left_panel, text="", font=("Segoe UI", 20, "bold"))
        self.lbl_app_title.pack(pady=(18, 0), padx=16, anchor="w")
        self.lbl_app_subtitle = ctk.CTkLabel(self.left_panel, text="", font=("Segoe UI", 11), text_color=("#667085", "#A0A0A0"))
        self.lbl_app_subtitle.pack(pady=(0, 16), padx=16, anchor="w")

        header_row = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        header_row.pack(fill="x", padx=16, pady=(0, 10))
        self.lbl_configuration = ctk.CTkLabel(header_row, text="", font=("Segoe UI", 14, "bold"))
        self.lbl_configuration.pack(side="left")
        self.language_menu = ctk.CTkOptionMenu(
            header_row,
            values=GUI_LANGUAGES,
            variable=self.language_var,
            width=135,
            command=self.on_language_change,
        )
        self.language_menu.pack(side="right")

        self.btn_upload = ctk.CTkButton(
            self.left_panel,
            text="",
            command=self.browse_kmz,
            font=("Segoe UI", 13, "bold"),
            height=40,
            corner_radius=10,
        )
        self.btn_upload.pack(fill="x", padx=16, pady=(0, 8))

        self.lbl_file_status = ctk.CTkLabel(
            self.left_panel,
            text="",
            font=("Segoe UI", 11, "italic"),
            text_color=("#667085", "#A0A0A0"),
            anchor="w",
        )
        self.lbl_file_status.pack(fill="x", padx=16, pady=(0, 12))

        output_card = ctk.CTkFrame(self.left_panel, corner_radius=12)
        output_card.pack(fill="x", padx=16, pady=(0, 12))
        self.lbl_output_folder = ctk.CTkLabel(output_card, text="", font=("Segoe UI", 11, "bold"))
        self.lbl_output_folder.pack(anchor="w", padx=12, pady=(10, 4))
        self.entry_output_dir = ctk.CTkEntry(output_card, textvariable=self.output_dir_var, height=34)
        self.entry_output_dir.pack(fill="x", padx=12, pady=(0, 8))
        output_btn_row = ctk.CTkFrame(output_card, fg_color="transparent")
        output_btn_row.pack(fill="x", padx=12, pady=(0, 10))
        self.btn_output_dir = ctk.CTkButton(output_btn_row, text="", command=self.browse_output_dir, height=32)
        self.btn_output_dir.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.btn_open_output = ctk.CTkButton(output_btn_row, text="", command=self.open_output_folder, height=32, state="disabled")
        self.btn_open_output.pack(side="right", fill="x", expand=True, padx=(5, 0))

        self.folder_frame = ctk.CTkScrollableFrame(self.left_panel, label_text="", label_font=("Segoe UI", 12, "bold"), height=self.responsive_metrics()["folder_height"])
        self.folder_frame.pack(fill="x", padx=16, pady=(0, 12))

        self.lbl_homepassed = ctk.CTkLabel(self.folder_frame, text="", font=("Segoe UI", 11), anchor="w")
        self.lbl_homepassed.pack(fill="x", padx=5, pady=(4, 2))
        self.cb_homepassed = ctk.CTkOptionMenu(self.folder_frame, values=[self.t("placeholder_load")], variable=self.homepassed_folder_var, corner_radius=8)
        self.cb_homepassed.pack(fill="x", padx=5, pady=(0, 10))

        self.lbl_boundary = ctk.CTkLabel(self.folder_frame, text="", font=("Segoe UI", 11), anchor="w")
        self.lbl_boundary.pack(fill="x", padx=5, pady=(0, 2))
        self.cb_boundary = ctk.CTkOptionMenu(self.folder_frame, values=[self.t("placeholder_load")], variable=self.boundary_folder_var, corner_radius=8)
        self.cb_boundary.pack(fill="x", padx=5, pady=(0, 10))

        self.lbl_reference = ctk.CTkLabel(self.folder_frame, text="", font=("Segoe UI", 11), anchor="w")
        self.lbl_reference.pack(fill="x", padx=5, pady=(0, 2))
        self.cb_reference = ctk.CTkOptionMenu(self.folder_frame, values=[self.t("placeholder_load")], variable=self.reference_fat_folder_var, corner_radius=8)
        self.cb_reference.pack(fill="x", padx=5, pady=(0, 10))

        self.settings_frame = ctk.CTkScrollableFrame(self.left_panel, label_text="", label_font=("Segoe UI", 12, "bold"), height=self.responsive_metrics()["settings_height"])
        self.settings_frame.pack(fill="x", padx=16, pady=(0, 10))

        self.lbl_boundary_naming = ctk.CTkLabel(self.settings_frame, text="", font=("Segoe UI", 11), anchor="w")
        self.lbl_boundary_naming.pack(fill="x", padx=5, pady=(4, 2))
        self.boundary_naming_menu = ctk.CTkOptionMenu(
            self.settings_frame,
            values=[],
            command=self.on_boundary_naming_change,
            corner_radius=8,
        )
        self.boundary_naming_menu.pack(fill="x", padx=5, pady=(0, 10))

        self.lbl_edge_tolerance = ctk.CTkLabel(self.settings_frame, text="", font=("Segoe UI", 11), anchor="w")
        self.lbl_edge_tolerance.pack(fill="x", padx=5, pady=(0, 2))
        self.entry_edge = ctk.CTkEntry(self.settings_frame, textvariable=self.edge_threshold_var, height=34)
        self.entry_edge.pack(fill="x", padx=5, pady=(0, 10))

        self.lbl_duplicate_boundary = ctk.CTkLabel(self.settings_frame, text="", font=("Segoe UI", 11), anchor="w")
        self.lbl_duplicate_boundary.pack(fill="x", padx=5, pady=(0, 2))
        self.duplicate_menu = ctk.CTkOptionMenu(
            self.settings_frame,
            values=[],
            command=self.on_duplicate_change,
            corner_radius=8,
        )
        self.duplicate_menu.pack(fill="x", padx=5, pady=(0, 10))

        self.chk_include_boundaries = ctk.CTkCheckBox(self.settings_frame, text="", variable=self.include_boundaries_var)
        self.chk_include_boundaries.pack(fill="x", padx=5, pady=(2, 8))

        self.btn_process = ctk.CTkButton(
            self.left_panel,
            text="",
            command=self.start_process,
            font=("Segoe UI", 14, "bold"),
            fg_color="#2EA44F",
            hover_color="#22863A",
            height=44,
            corner_radius=10,
        )
        self.btn_process.pack(fill="x", padx=16, pady=(2, 8))

        utility_row = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        utility_row.pack(fill="x", padx=16, pady=(0, 8))
        self.btn_clear_log = ctk.CTkButton(utility_row, text="", command=self.clear_log, height=32, fg_color=("#667085", "#4A4A4A"))
        self.btn_clear_log.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.lbl_status = ctk.CTkLabel(
            utility_row,
            textvariable=self.status_var,
            font=("Segoe UI", 10),
            text_color=("#667085", "#A0A0A0"),
            width=150,
            anchor="e",
        )
        self.lbl_status.pack(side="right", padx=(5, 0))

        self.progress_bar = ctk.CTkProgressBar(self.left_panel, orientation="horizontal", mode="determinate")
        self.progress_bar.pack(fill="x", padx=16, pady=(0, 14))
        self.progress_bar.set(0)

    def setup_right_panel(self) -> None:
        self.lbl_summary_title = ctk.CTkLabel(self.right_panel, text="", font=("Segoe UI", 16, "bold"))
        self.lbl_summary_title.grid(row=0, column=0, sticky="w", padx=18, pady=(16, 8))

        self.cards_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.cards_frame.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 12))
        for col in range(3):
            self.cards_frame.grid_columnconfigure(col, weight=1)

        self.card_cover = self.make_stat_card(self.cards_frame, 0)
        self.card_multi = self.make_stat_card(self.cards_frame, 1)
        self.card_uncover = self.make_stat_card(self.cards_frame, 2)

        self.main_result_frame = ctk.CTkFrame(self.right_panel, corner_radius=12)
        self.main_result_frame.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 12))
        self.main_result_frame.grid_columnconfigure(0, weight=1)
        self.main_result_frame.grid_rowconfigure(1, weight=1)

        self.lbl_group_detail = ctk.CTkLabel(self.main_result_frame, text="", font=("Segoe UI", 12, "bold"))
        self.lbl_group_detail.grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))
        self.summary_scroll = ctk.CTkScrollableFrame(self.main_result_frame, height=120)
        self.summary_scroll.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.summary_scroll.grid_columnconfigure(0, weight=1)

        self.console_frame = ctk.CTkFrame(self.right_panel, corner_radius=12)
        self.console_frame.grid(row=3, column=0, sticky="nsew", padx=18, pady=(0, 14))
        self.console_frame.grid_columnconfigure(0, weight=1)
        self.console_frame.grid_rowconfigure(1, weight=1)

        self.lbl_console_title = ctk.CTkLabel(self.console_frame, text="", font=("Segoe UI", 13, "bold"))
        self.lbl_console_title.grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))
        self.log_text = ctk.CTkTextbox(self.console_frame, font=("Consolas", 11), corner_radius=10, border_width=1, height=self.responsive_metrics()["log_height"])
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        self.output_path_label = ctk.CTkLabel(self.right_panel, text="", font=("Segoe UI", 10), text_color=("#667085", "#A0A0A0"), anchor="w")
        self.output_path_label.grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 12))

    def make_stat_card(self, parent: ctk.CTkFrame, column: int) -> Dict[str, ctk.CTkLabel]:
        card = ctk.CTkFrame(parent, corner_radius=14)
        card.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 6, 0 if column == 2 else 6))
        title_label = ctk.CTkLabel(card, text="", font=("Segoe UI", 11, "bold"), text_color=("#667085", "#A0A0A0"))
        title_label.pack(anchor="w", padx=12, pady=(10, 0))
        value_label = ctk.CTkLabel(card, text="0", font=("Segoe UI", 26, "bold"))
        value_label.pack(anchor="w", padx=12, pady=(0, 10))
        return {"title": title_label, "value": value_label}

    # ------------------------------------------------------------------
    # Language and UI helpers
    # ------------------------------------------------------------------
    def on_language_change(self, _value: str) -> None:
        self.apply_language()

    def apply_language(self) -> None:
        self.title(self.t("title"))
        self.lbl_app_title.configure(text=self.t("app_title"))
        self.lbl_app_subtitle.configure(text=self.t("app_subtitle"))
        self.lbl_configuration.configure(text=self.t("configuration"))
        self.btn_upload.configure(text=self.t("browse_kmz"))
        if not self.kmz_path_var.get().strip():
            self.lbl_file_status.configure(text=self.t("file_empty"))
        self.lbl_output_folder.configure(text=self.t("output_folder"))
        self.btn_output_dir.configure(text=self.t("browse_output"))
        self.btn_open_output.configure(text=self.t("open_output"))
        self.folder_frame.configure(label_text=self.t("folders_title"))
        self.lbl_homepassed.configure(text=self.t("homepassed_folder"))
        self.lbl_boundary.configure(text=self.t("boundary_folder"))
        self.lbl_reference.configure(text=self.t("reference_folder"))
        self.settings_frame.configure(label_text=self.t("settings_title"))
        self.lbl_boundary_naming.configure(text=self.t("boundary_naming"))
        self.lbl_edge_tolerance.configure(text=self.t("edge_tolerance"))
        self.lbl_duplicate_boundary.configure(text=self.t("duplicate_boundary"))
        self.chk_include_boundaries.configure(text=self.t("include_boundary"))
        self.btn_process.configure(text=self.t("start"))
        self.btn_clear_log.configure(text=self.t("clear_log"))
        self.lbl_summary_title.configure(text=self.t("summary_title"))
        self.lbl_group_detail.configure(text=self.t("group_detail"))
        self.lbl_console_title.configure(text=self.t("console_title"))
        self.footer_label.configure(text=self.t("copyright"))
        self.status_var.set(self.t("ready") if self.progress_bar.get() == 0 else self.status_var.get())
        self.card_cover["title"].configure(text=self.t("hp_cover"))
        self.card_multi["title"].configure(text=self.t("hp_multi"))
        self.card_uncover["title"].configure(text=self.t("hp_uncover"))
        self.sync_mode_optionmenus()
        self.sync_folder_optionmenus()

    def sync_mode_optionmenus(self) -> None:
        naming_values = [self.t("naming_auto"), self.t("naming_original")]
        self.boundary_naming_menu.configure(values=naming_values)
        self.boundary_naming_menu.set(self.t("naming_auto") if self.boundary_naming_mode == BOUNDARY_NAME_AUTO_FAT else self.t("naming_original"))

        duplicate_values = [self.t("duplicate_merge"), self.t("duplicate_split")]
        self.duplicate_menu.configure(values=duplicate_values)
        self.duplicate_menu.set(self.t("duplicate_merge") if self.duplicate_mode == DUPLICATE_MERGE else self.t("duplicate_split"))

    def sync_folder_optionmenus(self) -> None:
        values = self.kml_folders if self.kml_folders else [self.t("placeholder_load")]
        self.cb_homepassed.configure(values=values)
        self.cb_boundary.configure(values=values)
        self.cb_reference.configure(values=values)
        if not self.kml_folders:
            self.cb_homepassed.set(self.t("placeholder_load"))
            self.cb_boundary.set(self.t("placeholder_load"))
            self.cb_reference.set(self.t("placeholder_load"))

    def on_boundary_naming_change(self, value: str) -> None:
        self.boundary_naming_mode = BOUNDARY_NAME_AUTO_FAT if value == self.t("naming_auto") else BOUNDARY_NAME_ORIGINAL

    def on_duplicate_change(self, value: str) -> None:
        self.duplicate_mode = DUPLICATE_MERGE if value == self.t("duplicate_merge") else DUPLICATE_SPLIT_BY_PATH

    def translate_process_log(self, message: str) -> str:
        if self.language_var.get() == LANG_INDONESIA:
            return message
        for prefix, translations in PROCESS_LOG_TRANSLATIONS.items():
            if message.startswith(prefix):
                return translations.get(self.language_var.get(), message)
        return message

    # ------------------------------------------------------------------
    # File and process actions
    # ------------------------------------------------------------------
    def browse_kmz(self) -> None:
        path = filedialog.askopenfilename(
            title=self.t("select_kmz_title"),
            filetypes=[("KMZ files", "*.kmz"), ("All files", "*.*")],
        )
        if path:
            self.kmz_path_var.set(path)
            filename = os.path.basename(path)
            self.lbl_file_status.configure(text=self.t("file_selected").format(filename=filename), text_color="#2EA44F")
            if not self.output_dir_var.get().strip():
                self.output_dir_var.set(str(Path(path).parent))
            self.load_folder_preview()

    def browse_output_dir(self) -> None:
        path = filedialog.askdirectory(title=self.t("select_output_title"))
        if path:
            self.output_dir_var.set(path)

    def load_folder_preview(self) -> None:
        kmz_path = self.kmz_path_var.get().strip()
        if not kmz_path:
            messagebox.showwarning(self.t("input_incomplete"), self.t("no_kmz"))
            return
        try:
            _, root, _, _ = read_kml_from_kmz(kmz_path)
            folders = get_folder_paths(root)
            self.kml_folders = folders
            self.sync_folder_optionmenus()
            self.auto_select_common_folders(folders)
            self.append_log(self.t("preview_success").format(count=len(folders)))
            self.progress_bar.set(0.08)
        except Exception as exc:
            messagebox.showerror(self.t("preview_failed_title"), self.t("preview_failed").format(error=exc))
            self.append_log(self.t("preview_failed").format(error=exc))

    def auto_select_common_folders(self, folders: List[str]) -> None:
        lower_map = {folder.lower(): folder for folder in folders}
        for key, folder in lower_map.items():
            if "homepased" in key or "homepassed" in key or key.rsplit("/", 1)[-1] in {"hp", "homepased", "homepassed"}:
                self.homepassed_folder_var.set(folder)
                self.cb_homepassed.set(folder)
                break
        for key, folder in lower_map.items():
            if "boundary" in key and "fat" in key:
                self.boundary_folder_var.set(folder)
                self.cb_boundary.set(folder)
                break
        for key, folder in lower_map.items():
            tail = key.rsplit("/", 1)[-1]
            if tail == "fat" or ("fat" in tail and "boundary" not in tail):
                self.reference_fat_folder_var.set(folder)
                self.cb_reference.set(folder)
                break

    def open_output_folder(self) -> None:
        target = self.last_output_dir or self.output_dir_var.get().strip()
        if not target or not os.path.isdir(target):
            messagebox.showwarning(self.t("folder_not_found_title"), self.t("folder_not_found"))
            return
        try:
            system = platform.system().lower()
            if system == "windows":
                os.startfile(target)  # type: ignore[attr-defined]
            elif system == "darwin":
                subprocess.Popen(["open", target])
            else:
                subprocess.Popen(["xdg-open", target])
        except Exception as exc:
            messagebox.showerror(self.t("open_failed_title"), self.t("open_failed").format(error=exc))

    def clear_log(self) -> None:
        self.log_text.delete("1.0", "end")
        self.reset_summary_cards()
        self.output_path_label.configure(text="")
        self.progress_bar.set(0)
        self.status_var.set(self.t("ready"))

    def set_status_text(self, text: str) -> None:
        """Keep the status label short so the left panel does not resize/flicker."""
        clean = " ".join(str(text).split())
        if len(clean) > 34:
            clean = clean[:31] + "..."
        self.status_var.set(clean or self.t("ready"))

    def append_log(self, text: str) -> None:
        # Avoid update_idletasks() here. Forced redraw on every log/progress
        # message makes CustomTkinter recalculate layout repeatedly and can
        # cause visible flicker while the worker thread is running.
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")
        self.set_status_text(text)

    def update_progress_from_message(self, message: str) -> None:
        progress = None
        if message.startswith("Membaca file KMZ"):
            progress = 0.12
        elif message.startswith("Mengambil titik Homepassed"):
            progress = 0.25
        elif message.startswith("Mengambil polygon Boundary FAT"):
            progress = 0.38
        elif message.startswith("Mengambil placemark FAT referensi"):
            progress = 0.48
        elif message.startswith("Auto naming Boundary FAT"):
            progress = 0.58
        elif message.startswith("Hasil auto naming boundary"):
            progress = 0.64
        elif message.startswith("Mengelompokkan Homepassed"):
            progress = 0.72
        elif message.startswith("Membuat output KMZ"):
            progress = 0.88
        elif message.startswith("Laporan Ringkasan/Detail"):
            progress = 0.96
        if progress is not None:
            self.progress_bar.set(progress)

    def handle_progress_message(self, message: str) -> None:
        self.update_progress_from_message(message)
        self.append_log(self.translate_process_log(message))

    def start_process(self) -> None:
        kmz_path = self.kmz_path_var.get().strip()
        output_dir = self.output_dir_var.get().strip()
        homepassed_folder = self.homepassed_folder_var.get().strip()
        boundary_folder = self.boundary_folder_var.get().strip()
        reference_fat_folder = self.reference_fat_folder_var.get().strip()

        if not kmz_path:
            messagebox.showwarning(self.t("input_incomplete"), self.t("no_kmz"))
            return
        if not output_dir:
            messagebox.showwarning(self.t("input_incomplete"), self.t("no_output"))
            return
        if not homepassed_folder or not boundary_folder or homepassed_folder.startswith("--") or boundary_folder.startswith("--"):
            messagebox.showwarning(self.t("input_incomplete"), self.t("no_hp_boundary"))
            return
        if self.boundary_naming_mode == BOUNDARY_NAME_AUTO_FAT and (not reference_fat_folder or reference_fat_folder.startswith("--")):
            messagebox.showwarning(self.t("input_incomplete"), self.t("no_reference"))
            return
        try:
            edge_threshold_m = float(self.edge_threshold_var.get().strip().replace(",", "."))
        except ValueError:
            messagebox.showwarning(self.t("invalid_input"), self.t("invalid_edge"))
            return

        include_boundaries = self.include_boundaries_var.get()
        duplicate_mode = self.duplicate_mode
        boundary_naming_mode = self.boundary_naming_mode

        self.log_text.delete("1.0", "end")
        self.reset_summary_cards()
        self.output_path_label.configure(text="")
        self.progress_bar.set(0.05)
        self.btn_process.configure(state="disabled", text=self.t("processing"))
        self.btn_open_output.configure(state="disabled")
        self.set_status_text(self.t("processing"))
        self.append_log(self.t("start_log"))

        # Freeze all UI values before starting the worker thread.
        # Tk/CustomTkinter variables should not be read directly from
        # a background thread.
        worker = threading.Thread(
            target=self._run_process_worker,
            args=(
                kmz_path,
                output_dir,
                homepassed_folder,
                boundary_folder,
                reference_fat_folder,
                duplicate_mode,
                include_boundaries,
                boundary_naming_mode,
                edge_threshold_m,
            ),
            daemon=True,
        )
        worker.start()

    def _run_process_worker(
        self,
        kmz_path: str,
        output_dir: str,
        homepassed_folder: str,
        boundary_folder: str,
        reference_fat_folder: str,
        duplicate_mode: str,
        include_boundaries: bool,
        boundary_naming_mode: str,
        edge_threshold_m: float,
    ) -> None:
        try:
            result = process_kmz(
                kmz_path=kmz_path,
                output_dir=output_dir,
                homepassed_folder=homepassed_folder,
                boundary_folder=boundary_folder,
                duplicate_mode=duplicate_mode,
                include_boundaries=include_boundaries,
                reference_fat_folder=reference_fat_folder,
                boundary_naming_mode=boundary_naming_mode,
                edge_threshold_m=edge_threshold_m,
                progress_callback=lambda msg: self.after(0, self.handle_progress_message, msg),
            )
            self.after(0, self._show_result, result)
        except Exception as exc:
            detail = traceback.format_exc()
            err = f"GAGAL: {exc}"
            self.after(0, self.append_log, err)
            self.after(0, self.append_log, detail)
            self.after(0, lambda err=err: messagebox.showerror(self.t("process_failed_title"), err))
        finally:
            self.after(0, lambda: self.btn_process.configure(state="normal", text=self.t("start")))

    # ------------------------------------------------------------------
    # Result rendering
    # ------------------------------------------------------------------
    def reset_summary_cards(self) -> None:
        self.card_cover["value"].configure(text="0")
        self.card_multi["value"].configure(text="0")
        self.card_uncover["value"].configure(text="0")
        for child in self.summary_scroll.winfo_children():
            child.destroy()
        self.add_summary_row(self.t("total_homepassed"), "-")
        self.add_summary_row(self.t("total_boundary"), "-")
        self.add_summary_row(self.t("total_reference"), "-")

    def add_summary_row(self, label: str, value: object) -> None:
        row = ctk.CTkFrame(self.summary_scroll, fg_color="transparent")
        row.pack(fill="x", padx=4, pady=3)
        lbl = ctk.CTkLabel(row, text=str(label), font=("Segoe UI", 11), anchor="w")
        lbl.pack(side="left", fill="x", expand=True)
        val = ctk.CTkLabel(row, text=str(value), font=("Segoe UI", 11, "bold"), anchor="e")
        val.pack(side="right")

    def _show_result(self, result: Dict[str, object]) -> None:
        self.card_cover["value"].configure(text=str(result["cover_count"]))
        self.card_multi["value"].configure(text=str(result["multi_boundary_count"]))
        self.card_uncover["value"].configure(text=str(result["uncover_count"]))

        for child in self.summary_scroll.winfo_children():
            child.destroy()
        self.add_summary_row(self.t("total_homepassed"), result["total_homepassed"])
        self.add_summary_row(self.t("total_boundary"), result["total_boundaries"])
        self.add_summary_row(self.t("total_reference"), result.get("total_reference_fat", 0))
        self.add_summary_row(self.t("hp_cover"), result["cover_count"])
        self.add_summary_row(self.t("hp_multi"), result["multi_boundary_count"])
        self.add_summary_row(self.t("hp_uncover"), result["uncover_count"])

        counts: Dict[str, int] = {}
        for item in result["results"]:  # type: ignore[index]
            if item.status == STATUS_COVER:
                counts[item.group_key] = counts.get(item.group_key, 0) + 1
        for key in sorted(counts.keys(), key=lambda v: v.lower()):
            self.add_summary_row(key, counts[key])

        naming_stats = result.get("boundary_naming_stats", {})
        if naming_stats:
            self.append_log(
                f"Boundary auto-naming: inside={naming_stats.get('inside', 0)}, "
                f"near_edge={naming_stats.get('near_edge', 0)}, "
                f"unmatched={naming_stats.get('unmatched', 0)}, "
                f"multi_inside={naming_stats.get('multi_inside', 0)}, "
                f"duplicate_ref={naming_stats.get('duplicate_reference', 0)}"
            )

        foldering_mode = result.get("foldering_mode", "-")
        if foldering_mode == "FDT_PREFIX_HIERARCHY":
            self.append_log(self.t("fdt_mode"))
        elif foldering_mode == "SUFFIX_AFTER_LAST_DOT":
            self.append_log(self.t("suffix_mode"))

        duplicate_boundaries = result.get("duplicate_boundaries", {})
        if duplicate_boundaries:
            self.append_log("Duplicate boundary warning:")
            for name, paths in duplicate_boundaries.items():
                self.append_log(f"- {name}: {len(paths)} polygon | {' | '.join(paths)}")

        self.last_output_dir = str(result["output_dir"])
        self.output_kmz_path = str(result["output_kmz"])
        self.output_path_label.configure(text=f"{self.t('output_kmz')}: {self.output_kmz_path}")
        self.btn_open_output.configure(state="normal")
        self.progress_bar.set(1.0)
        self.set_status_text(self.t("done"))
        self.append_log(self.t("done"))
        self.append_log(f"{self.t('output_kmz')}: {self.output_kmz_path}")
        self.append_log(self.t("no_report"))
        messagebox.showinfo(
            self.t("success_title"),
            self.t("success_message").format(
                cover=result["cover_count"],
                multi=result["multi_boundary_count"],
                uncover=result["uncover_count"],
                output_dir=result["output_dir"],
            ),
        )


if __name__ == "__main__":
    app = HomepassedBoundaryGUI()
    app.mainloop()
