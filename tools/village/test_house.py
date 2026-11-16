"""Close-up check of the house generator: blender -b --factory-startup -P tools/village/test_house.py -- out.jpg"""
import os, sys, math
import bpy
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build, house
from meshkit import Mesh, hexc, T, R

build.clean()
scene = bpy.context.scene
mats = build.make_materials()
build.setup_world(scene)
m = Mesh()
m.box((80, 80, 0.2), hexc("#86b34c"), M=T(0, 0, -0.2), grad=1.0)
specs = [dict(seed=3, w=7.5, d=6, floors=2), dict(seed=8, w=6, d=5.2, floors=1, pitch=1.35, door_wall="gable"),
         dict(seed=12, w=9, d=6.5, floors=2, sign="inn")]
xs = [-10, 0, 11]
for sp, x in zip(specs, xs):
    h, info = house.build_house(**sp)
    rot = 90 if sp.get("door_wall") == "gable" else 0
    m.merge(h, M=T(x, 0, 0) @ R("Z", rot))
ob = m.to_object("test"); ob.data.materials.append(mats["village_vcol"])
print("TRIS", m.tri_count())
cam = bpy.data.cameras.new("c"); cam.lens = 28
co = bpy.data.objects.new("c", cam); scene.collection.objects.link(co)
view = os.environ.get("VIEW", "front")
pos = {"front": (4, -19, 1.7), "close": (-13, -9, 1.7), "high": (14, -18, 9)}[view]
look = {"front": (0.5, 0, 4), "close": (-9, 0, 3.2), "high": (0, 0, 3)}[view]
co.location = pos
co.rotation_euler = (Vector(look) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
scene.camera = co
build.setup_render(scene, 64, "1280x720")
scene.render.filepath = sys.argv[sys.argv.index("--") + 1]
bpy.ops.render.render(write_still=True)
