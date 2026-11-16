"""Build the village scene in Blender.

    blender -b --factory-startup -P tools/village/build.py -- [--render name,name|all] [--export] [--samples N] [--only terrain,...]
"""
import math
import os
import sys
import time

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "assets", "village")

import world  # noqa: E402


def args():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    o = {"render": "", "export": False, "backface": False, "samples": 64, "only": "", "res": "1280x720", "out": os.path.join(OUT, "renders")}
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


def clean():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def make_materials():
    mats = {}
    for name, rough, emit in [("village_vcol", 0.88, 0.0), ("village_cloud", 1.0, 0.55), ("village_glow", 0.6, 1.6)]:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        nt = mat.node_tree
        bsdf = nt.nodes.get("Principled BSDF")
        attr = nt.nodes.new("ShaderNodeVertexColor")
        attr.layer_name = "Col"
        nt.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = rough
        for nm in ("Specular IOR Level", "Specular"):
            if nm in bsdf.inputs:
                bsdf.inputs[nm].default_value = 0.15
        if emit > 0:
            nt.links.new(attr.outputs["Color"], bsdf.inputs["Emission Color"])
            bsdf.inputs["Emission Strength"].default_value = emit
        mats[name] = mat
    return mats


def setup_world(scene):
    w = bpy.data.worlds.new("Sky")
    scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes["Background"]
    sky = nt.nodes.new("ShaderNodeTexSky")
    types = [e.identifier for e in sky.bl_rna.properties["sky_type"].enum_items]
    pick = next((t for t in ("MULTIPLE_SCATTERING", "NISHITA", "SINGLE_SCATTERING") if t in types), types[0])
    sky.sky_type = pick
    elev, rot = math.radians(38), math.radians(-128)     # sun in the south-east, lighting the village front
    for prop, val in (("sun_elevation", elev), ("sun_rotation", rot), ("sun_size", math.radians(1.2)),
                      ("sun_intensity", 0.35), ("altitude", 800), ("air_density", 1.0),
                      ("aerosol_density", 0.6), ("dust_density", 0.6), ("ozone_density", 1.0), ("sun_disc", False)):
        if hasattr(sky, prop):
            try:
                setattr(sky, prop, val)
            except Exception:
                pass
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = float(os.environ.get("SKY", 0.1))
    # an explicit sun gives crisp, controllable stylised shadows
    sd = bpy.data.lights.new("Sun", "SUN")
    sd.energy = float(os.environ.get('SUN', 3.0))
    sd.angle = math.radians(2.0)
    sd.color = (1.0, 0.955, 0.87)
    so = bpy.data.objects.new("Sun", sd)
    scene.collection.objects.link(so)
    d = Vector((math.cos(elev) * math.sin(-rot), math.cos(elev) * math.cos(-rot), math.sin(elev)))
    so.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    return d


CAMERAS = {
    # name: (position, look-at, lens mm)
    "overview": ((95, -150, 95), (0, 0, 14), 32),
    "entrance": ((0.5, -96, None), (2, -30, 14), 24),
    "plaza": ((-11, -4, None), (14, 6, 12.5), 22),
    "plaza_north": ((2, -8, None), (8, 60, 60), 20),
    "top_down_valley": ((6, 70, None), (-4, -40, 2), 24),
    "gate": ((1, 58, None), (4, 100, 34), 22),
    "stage": ((4.5, -3.5, None), (14, -1, 11), 26),
    "rota": ((-14, -38, None), (-24, -26, 6.5), 24),
    "caelum": ((8, 62, None), (22, 71, 19.5), 24),
    "street": ((1, -44, None), (3, 10, 20), 24),
}


def add_camera(scene, name):
    pos, look, lens = CAMERAS[name]
    x, y, z = pos
    if z is None:
        z = world.height(x, y) + 1.65            # eye height: this is a first-person game
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.clip_start, cam.clip_end = 0.1, 6000
    ob = bpy.data.objects.new("cam_" + name, cam)
    scene.collection.objects.link(ob)
    ob.location = (x, y, z)
    ob.rotation_euler = (Vector(look) - Vector((x, y, z))).to_track_quat("-Z", "Y").to_euler()
    return ob


def setup_render(scene, samples, res):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = os.environ.get('NODENOISE') is None
    scene.cycles.max_bounces = 4
    scene.cycles.diffuse_bounces = 2
    w, h = (int(v) for v in res.split("x"))
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 90
    vs = scene.view_settings
    for vt in ("Khronos PBR Neutral", "Standard"):
        try:
            vs.view_transform = vt
            break
        except TypeError:
            continue
    vs.exposure = 0.0


def main():
    o = args()
    t0 = time.time()
    clean()
    scene = bpy.context.scene
    mats = make_materials()
    setup_world(scene)
    only = set(filter(None, o["only"].split(",")))

    def want(k):
        return not only or k in only

    built = {}

    def put(name, mesh, mat="village_vcol"):
        ob = mesh.to_object(name)
        ob.data.materials.append(mats[mat])
        built[name] = mesh.tri_count()

    if want("terrain"):
        put("Terrain", world.build_terrain())
    if want("mountains"):
        put("Mountains", world.build_mountains())
    if want("clouds"):
        put("Clouds", world.build_clouds(), "village_cloud")
    if want("village"):
        try:
            import layout
        except ImportError:
            layout = None
        if layout:
            for name, (mesh, mat) in layout.build_all().items():
                put(name, mesh, mat)

    total = sum(built.values())
    print("TRIS", {k: v for k, v in built.items()}, "TOTAL", total, "build %.1fs" % (time.time() - t0))

    if o["export"]:
        os.makedirs(OUT, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "village.blend"))
        for ob in scene.objects:
            ob.select_set(ob.type == "MESH")
        bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "village.glb"), export_format="GLB", use_selection=True,
                                  export_yup=True, export_apply=True)
        print("EXPORTED", os.path.getsize(os.path.join(OUT, "village.glb")) // 1024, "KB")

    if o["backface"]:                       # paint faces seen from behind in magenta (game engines cull them)
        for mat in mats.values():
            nt = mat.node_tree
            geo = nt.nodes.new("ShaderNodeNewGeometry")
            mixn = nt.nodes.new("ShaderNodeMixShader")
            em = nt.nodes.new("ShaderNodeEmission")
            em.inputs["Color"].default_value = (1, 0, 1, 1)
            em.inputs["Strength"].default_value = 3
            outn = nt.nodes["Material Output"]
            bsdf = nt.nodes["Principled BSDF"]
            nt.links.new(geo.outputs["Backfacing"], mixn.inputs[0])
            nt.links.new(bsdf.outputs[0], mixn.inputs[1])
            nt.links.new(em.outputs[0], mixn.inputs[2])
            nt.links.new(mixn.outputs[0], outn.inputs["Surface"])

    if o["render"]:
        setup_render(scene, int(o["samples"]), o["res"])
        names = list(CAMERAS) if o["render"] == "all" else o["render"].split(",")
        os.makedirs(o["out"], exist_ok=True)
        for n in names:
            scene.camera = add_camera(scene, n)
            scene.render.filepath = os.path.join(o["out"], n + ".jpg")
            t1 = time.time()
            bpy.ops.render.render(write_still=True)
            print("RENDERED", n, "%.0fs" % (time.time() - t1))


if __name__ == "__main__":
    main()
