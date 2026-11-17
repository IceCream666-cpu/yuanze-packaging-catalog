"""Render and save an actual Cycles studio, including a paired carrier shadow check."""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

HERE=Path(__file__).resolve().parent;OUT=HERE/'previews';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(HERE/'poster-056-v2.blend'))
scene=bpy.context.scene;scene.frame_set(1)
root_names=['Overcap','PumpAssembly','Body','PaperLabel','LogoPrint','ProductPrint']
products=[o for name in root_names for o in bpy.data.objects[name].children_recursive if o.type=='MESH']
for o in list(scene.objects):
    if o.type in {'CAMERA','LIGHT'} or o.name=='Golden physical studio ground':bpy.data.objects.remove(o,do_unlink=True)
scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True
scene.cycles.max_bounces=12;scene.cycles.transmission_bounces=10;scene.cycles.transparent_max_bounces=12
scene.render.resolution_x=1200;scene.render.resolution_y=1500;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB'
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='METAL';prefs.get_devices()
assert any(d.type=='METAL' for d in prefs.devices)
for device in prefs.devices:device.use=device.type=='METAL'
scene.cycles.device='GPU'
world=bpy.data.worlds.new('Golden neutral reflection studio');world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.70,.69,.64,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.38;scene.world=world
mat=bpy.data.materials.new('Golden warm limestone backdrop');mat.use_nodes=True
p=mat.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=(.67,.65,.54,1);p.inputs['Roughness'].default_value=.83
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.005));floor=bpy.context.object;floor.name='Golden physical studio ground';floor.data.materials.append(mat)
def area(name,position,width,height,energy,color):
    bpy.ops.object.light_add(type='AREA',location=position);o=bpy.context.object;o.name=name;o.data.shape='RECTANGLE';o.data.size=width;o.data.size_y=height;o.data.energy=energy;o.data.color=color
    o.rotation_euler=(Vector((0,0,2.6))-o.location).to_track_quat('-Z','Y').to_euler()
area('Golden left window key',(-3.5,-4.5,5),1.8,4,550,(1,.97,.92))
area('Golden narrow polished edge strip',(3,-2,5),.55,5,280,(1,1,.98))
area('Golden rear transmission softbox',(1,3,6),2,4,500,(1,.98,.92))
area('Golden gentle frontal fill',(0,-5,4),4,4,65,(1,1,1))
bpy.ops.object.camera_add();camera=bpy.context.object;camera.name='Golden Face Oil review camera';camera.data.type='ORTHO';camera.data.clip_end=200;scene.camera=camera
def frame_product(frame,direction):
    scene.frame_set(frame);bpy.context.view_layer.update()
    points=[o.matrix_world@v.co for o in products for v in o.data.vertices]
    low=Vector([min(p[i] for p in points) for i in range(3)]);high=Vector([max(p[i] for p in points) for i in range(3)])
    target=(low+high)/2;camera.location=target+Vector(direction)
    camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
    inv=camera.matrix_world.inverted();local=[inv@p for p in points]
    dx=max(p.x for p in local)-min(p.x for p in local);dy=max(p.y for p in local)-min(p.y for p in local)
    center=Vector(((max(p.x for p in local)+min(p.x for p in local))/2,(max(p.y for p in local)+min(p.y for p in local))/2,0))
    camera.location+=camera.rotation_euler.to_matrix()@center
    camera.data.ortho_scale=max(dy,dx*1.25)*1.20;bpy.context.view_layer.update()
    projected=[world_to_camera_view(scene,camera,p) for p in points]
    assert all(.02<p.x<.98 and .02<p.y<.98 for p in projected),'Clipped product'
    return {'frame':frame,'camera':list(camera.location),'orthoScale':camera.data.ortho_scale,'projectedBounds':[[min(p.x for p in projected),min(p.y for p in projected)],[max(p.x for p in projected),max(p.y for p in projected)]]}
poses=[]
for name,frame,direction in [('closed',1,(2.1,-10,1.1)),('half',31,(1.4,-10,1.0)),('expanded',61,(1.6,-10,1.0)),('rotated',61,(5.5,-10,1.7))]:
    info=frame_product(frame,direction);scene.render.filepath=str(OUT/f'Golden-Face-Oil-Blender-{name}.png')
    bpy.ops.render.render(write_still=True);info['name']=name;poses.append(info)
    if name=='half':
        for o in bpy.data.objects['PaperLabel'].children_recursive:o.visible_shadow=False
        scene.render.filepath=str(OUT/'Golden-Face-Oil-shadow-control.png');bpy.ops.render.render(write_still=True)
        for o in bpy.data.objects['PaperLabel'].children_recursive:o.visible_shadow=True
for frame in [1,31,61]:
    frame_product(frame,(2.1,-10,1.1));camera.keyframe_insert(data_path='location',frame=frame);camera.keyframe_insert(data_path='rotation_euler',frame=frame);camera.data.keyframe_insert(data_path='ortho_scale',frame=frame)
scene.frame_set(1)
for screen in bpy.data.screens:
    for a in screen.areas:
        if a.type=='VIEW_3D':a.spaces.active.region_3d.view_perspective='CAMERA';a.spaces.active.overlay.show_overlays=False;a.spaces.active.shading.type='MATERIAL'
bpy.context.preferences.filepaths.save_version=0;bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'poster-056-v2.blend'),compress=True)
(HERE/'render-verification.json').write_text(json.dumps({'engine':'Cycles','device':'Metal','samples':64,'resolution':[1200,1500],'poses':poses,'pairedCarrierShadowControlRendered':True,'transparentInkShadowDisabled':True,'visualReviewPending':True,'browserVerifiedSeparately':False},indent=2)+'\n')
