"""Build the mountain zones.

    blender -b --factory-startup -P tools/village/build_mountain.py -- --zone forest|ridge|plateau|summit|all [--render all|name,..] [--export] [--samples N] [--res WxH]
"""
import math
import os
import sys
import time

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build      # noqa: E402
import mountain   # noqa: E402

OUT = os.path.join(build.ROOT, "assets", "mountain")


def args():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    o = {"zone": "all", "render": "", "export": False, "backface": False, "samples": 64, "res": "1280x720", "out": os.path.join(OUT, "renders")}
    i = 0
    while i < len(a):
        k = a[i].lstrip("-")
        if k in ("export", "backface"):
            o[k] = True
            i += 1
        else:
            o[k] = a[i + 1]
            i += 2
    return o


def add_fog(scene, fog):
    """Render-only mist. In the game this is the engine's fog, not geometry."""
    centre, radius, density, squash = fog
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=radius, location=centre)
    ob = bpy.context.active_object
    ob.name = "_Fog"
    ob.scale = (1, 1, squash)
    mat = bpy.data.materials.new("_fog")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Density"].default_value = density
    vol.inputs["Color"].default_value = (0.93, 0.96, 1.0, 1)
    vol.inputs["Anisotropy"].default_value = 0.3
    nt.links.new(vol.outputs["Volume"], nt.nodes["Material Output"].inputs["Volume"])
    ob.data.materials.append(mat)
    scene.cycles.volume_bounces = 1
    scene.cycles.volume_step_rate = 4.0


def build_zone(name, o):
    t0 = time.time()
    build.clean()
    scene = bpy.context.scene
    mats = build.make_materials()
    build.setup_world(scene)
    Z = mountain.ZONES[name]()
    tris = {}
    for key, (mesh, mat) in Z.out.items():
        ob = mesh.to_object(key)
        ob.data.materials.append(mats[mat])
        tris[key] = mesh.tri_count()
    print("ZONE", name, "TOTAL", sum(tris.values()), {k.split("_", 1)[1]: v for k, v in tris.items()}, "build %.1fs" % (time.time() - t0))
    if o["export"]:
        os.makedirs(OUT, exist_ok=True)
        for ob in scene.objects:
            ob.select_set(ob.type == "MESH" and not ob.name.startswith("_"))
        path = os.path.join(OUT, name + ".glb")
        bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_yup=True, export_apply=True)
        print("EXPORTED", name, os.path.getsize(path) // 1024, "KB")
    if o["render"]:
        if o["backface"]:
            build.paint_backfaces(mats)
        if Z.fog and not o["backface"]:
            add_fog(scene, Z.fog)
        build.setup_render(scene, int(o["samples"]), o["res"])
        names = list(Z.cameras) if o["render"] == "all" else [n for n in o["render"].split(",") if n in Z.cameras]
        os.makedirs(o["out"], exist_ok=True)
        for n in names:
            pos, look, lens = Z.cameras[n]
            x, y, z = pos
            if z is None:
                z = Z.h(x, y) + 1.65
            cam = bpy.data.cameras.new(n)
            cam.lens = lens
            cam.clip_start, cam.clip_end = 0.1, 8000
            ob = bpy.data.objects.new("cam_" + n, cam)
            scene.collection.objects.link(ob)
            ob.location = (x, y, z)
            ob.rotation_euler = (Vector(look) - Vector((x, y, z))).to_track_quat("-Z", "Y").to_euler()
            scene.camera = ob
            scene.render.filepath = os.path.join(o["out"], name + "_" + n + ".jpg")
            t1 = time.time()
            bpy.ops.render.render(write_still=True)
            print("RENDERED", name, n, "%.0fs" % (time.time() - t1))


def main():
    o = args()
    for name in (list(mountain.ZONES) if o["zone"] == "all" else o["zone"].split(",")):
        build_zone(name, o)


if __name__ == "__main__":
    main()
