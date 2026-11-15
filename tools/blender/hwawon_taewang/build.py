"""화원태왕타운 단지 모델 생성 v2 (Blender Python, bpy).

실행:
  python3 build.py --tex <텍스처 폴더> --out <출력 폴더> [--render <폴더>] [--views a,b] [--only apt]

X = 동쪽, Y = 북쪽, Z = 위. 단위 m.
"""
import argparse
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import apartments  # noqa: E402


def setup_render(samples):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 5
    sc.cycles.transparent_max_bounces = 12
    try:
        sc.view_settings.view_transform = "Filmic"
        sc.view_settings.look = "Medium High Contrast"
    except Exception:
        pass
    sc.view_settings.exposure = 0.0
    world = bpy.data.worlds.new("World")
    sc.world = world
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes.get("Background")
    sky = nt.nodes.new("ShaderNodeTexSky")
    for t in ("MULTIPLE_SCATTERING", "NISHITA", "HOSEK_WILKIE"):
        try:
            sky.sky_type = t
            break
        except Exception:
            continue
    for k, v in (("sun_elevation", math.radians(52)), ("sun_rotation", math.radians(200)),
                 ("sun_intensity", 1.0), ("sun_size", math.radians(1.2)), ("altitude", 50.0),
                 ("air_density", 1.0), ("aerosol_density", 1.6), ("dust_density", 1.6), ("ozone_density", 1.0)):
        try:
            setattr(sky, k, v)
        except Exception:
            pass
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.11


def camera(name, loc, target=None, lens=24, ortho=None, heading=None, pitch=0.0):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_end = 3000
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    ob = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    if heading is not None:      # 방위각(북=0, 시계방향)과 올려다보는 각도
        h = math.radians(heading)
        d = Vector((math.sin(h) * math.cos(math.radians(pitch)), math.cos(h) * math.cos(math.radians(pitch)),
                    math.sin(math.radians(pitch))))
    else:
        d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


def render(cam, path, w, h):
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.resolution_x = w
    sc.render.resolution_y = h
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tex", required=True)
    ap.add_argument("--out", default="")
    ap.add_argument("--render", default="")
    ap.add_argument("--views", default="")
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--res", default="1600x900")
    ap.add_argument("--only", default="")
    args = ap.parse_args(sys.argv[1:])
    lib.TEX_DIR = os.path.abspath(args.tex)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    cols = {}
    for nm in ("Buildings", "Ground", "Props", "Trees", "Cars", "Context"):
        cols[nm] = bpy.data.collections.new(nm)
        sc.collection.children.link(cols[nm])

    M = apartments.materials()
    plates = {str(no): lib.mat_tex(f"Plate_{no}", f"plate_{no}", rough=0.5) for no in range(101, 110)}
    infos = [apartments.build_apartment(bd, cols["Buildings"], M, plates) for bd in apartments.BUILDINGS]
    apartments.add_numbers(infos, cols["Buildings"])

    if args.only != "apt":
        import site_build
        import props
        stalls = site_build.build(infos, cols)
        props.build(infos, stalls, cols)
    else:
        mb = lib.MeshBuilder()
        mb.flat([Vector((-300, -300)), Vector((300, -300)), Vector((300, 300)), Vector((-300, 300))], 0,
                lib.mat_tex("Asphalt", "asphalt"), tile=6.0)
        mb.build("TestGround", cols["Ground"])

    stats = dict(objects=len(bpy.data.objects), tris=0)
    for ob in bpy.data.objects:
        if ob.type == "MESH":
            stats["tris"] += sum(len(p.vertices) - 2 for p in ob.data.polygons)
    print("STATS", stats)

    if args.out:
        os.makedirs(args.out, exist_ok=True)
        blend = os.path.abspath(os.path.join(args.out, "hwawon_taewang.blend"))
        glb = os.path.abspath(os.path.join(args.out, "hwawon_taewang.glb"))
        bpy.ops.file.pack_all()
        bpy.ops.wm.save_as_mainfile(filepath=blend)
        bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", export_apply=True,
                                  export_image_format="JPEG", export_jpeg_quality=85)
        print("saved", blend, glb)

    if args.render:
        setup_render(args.samples)
        os.makedirs(args.render, exist_ok=True)
        w, h = (int(v) for v in args.res.split("x"))
        g = lib.geo
        eye = 2.4   # 거리뷰 촬영 차량 카메라 높이쯤
        views = {
            "aerial": lambda: camera("Cam_Aerial", (-150, -185, 125), (15, -5, 14), lens=30),
            "top": lambda: camera("Cam_Top", (8, 5, 400), (8, 5.01, 0), ortho=255),
            # 네이버 거리뷰와 같은 자리, 같은 방향
            "lotE_nw": lambda: camera("Cam_lotE_nw", (*g(128.4922046, 35.8025299), eye), heading=312, pitch=14, lens=15),
            "lotE_e": lambda: camera("Cam_lotE_e", (*g(128.4922046, 35.8025299), eye), heading=95, pitch=14, lens=15),
            "lotE_s": lambda: camera("Cam_lotE_s", (*g(128.4922046, 35.8025299), eye), heading=190, pitch=14, lens=15),
            "south_st": lambda: camera("Cam_south", (*g(128.4920293, 35.8020481), eye), heading=320, pitch=14, lens=15),
            "gate": lambda: camera("Cam_gate", (*g(128.4912501, 35.8020918) + Vector((0, -3)), eye), heading=8, pitch=12, lens=15),
            "back_gate": lambda: camera("Cam_back", (*g(128.4925448, 35.8027675) + Vector((4, 4)), eye), heading=235, pitch=12, lens=15),
            "west_lot": lambda: camera("Cam_west", (*g(128.4906776, 35.8028257), eye), heading=20, pitch=14, lens=15),
            "center": lambda: camera("Cam_center", (*g(128.4915795, 35.802767), eye), heading=140, pitch=12, lens=15),
        }
        want = [v for v in args.views.split(",") if v] or list(views)
        for k in want:
            render(views[k](), os.path.abspath(os.path.join(args.render, f"{k}.png")), w, h)
            print("rendered", k)


if __name__ == "__main__":
    main()
