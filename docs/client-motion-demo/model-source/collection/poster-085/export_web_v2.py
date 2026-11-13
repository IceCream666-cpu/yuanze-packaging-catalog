from pathlib import Path
import bpy,json
scene=bpy.context.scene;scene.frame_set(1)
base=Path(bpy.data.filepath).parent.parent
roots=['Body','Pump','TubeCap','Label','LogoInk','NameInk']
bpy.ops.object.select_all(action='DESELECT')
for name in roots:
 root=bpy.data.objects[name];root.select_set(True)
 for o in root.children_recursive:
  o.select_set(True)
  if name=='Label':o.visible_shadow=True
  if name in ('LogoInk','NameInk'):o.visible_shadow=False
assert len([o for o in bpy.context.selected_objects if o.type=='MESH'])==90
out=base.parents[2]/'packaging-assets/poster-085-v2.glb'
bpy.ops.export_scene.gltf(filepath=str(out),export_format='GLB',use_selection=True,export_yup=True,export_extras=True,export_animations=False,export_apply=True)
bpy.ops.wm.save_as_mainfile(filepath=str(base/'poster-085-v2.blend'),compress=True)
# Keep the approved studio lighting and camera, omit scene background from the homepage cutout.
for n in ['Physical shadow receiving ground','Seamless curved studio backdrop']:bpy.data.objects[n].hide_render=True
scene.render.resolution_x=1600;scene.render.resolution_y=2000;scene.render.resolution_percentage=100
scene.render.image_settings.color_mode='RGBA';scene.render.image_settings.color_depth='8';scene.render.film_transparent=True
scene.cycles.samples=128;scene.cycles.use_denoising=True
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='METAL';prefs.get_devices()
for d in prefs.devices:d.use=d.type=='METAL'
scene.cycles.device='GPU'
scene.render.filepath=str(base.parents[2]/'featured-assets/poster-085.png')
bpy.ops.render.render(write_still=True)
print('WEB MODEL AND FEATURED READY',out)
