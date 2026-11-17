"""Actual Metal/Cycles studio and identical-pose physical decorative-surface shadow control."""
import bpy, json
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

HERE=Path(__file__).resolve().parent; OUT=HERE/'previews'; OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(HERE/'poster-085-v3.blend'))
scene=bpy.context.scene; scene.frame_set(1)
root_names=['Body','Pump','TubeCap','Label','LogoInk','NameInk']
products=[o for n in root_names for o in bpy.data.objects[n].children_recursive if o.type=='MESH']
for o in list(scene.objects):
    if o.type in {'CAMERA','LIGHT'} or o.name=='Daily Hair physical studio ground':
        bpy.data.objects.remove(o,do_unlink=True)
scene.render.engine='CYCLES'; scene.cycles.samples=96; scene.cycles.use_denoising=True
scene.cycles.seed=85; scene.cycles.use_animated_seed=False
scene.cycles.max_bounces=14; scene.cycles.transmission_bounces=12; scene.cycles.transparent_max_bounces=16
scene.render.resolution_x=1400; scene.render.resolution_y=1400; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.render.image_settings.color_mode='RGB'
scene.view_settings.view_transform='AgX'; scene.view_settings.look='AgX - Medium High Contrast'
prefs=bpy.context.preferences.addons['cycles'].preferences; prefs.compute_device_type='METAL'; prefs.get_devices()
assert any(d.type=='METAL' for d in prefs.devices)
for device in prefs.devices: device.use=device.type=='METAL'
scene.cycles.device='GPU'
world=bpy.data.worlds.new('Daily Hair neutral warm reflection studio'); world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.72,.76,.80,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.25; scene.world=world
mat=bpy.data.materials.new('Daily Hair warm grey seamless backdrop'); mat.use_nodes=True
p=mat.node_tree.nodes['Principled BSDF']; p.inputs['Base Color'].default_value=(.18,.145,.12,1); p.inputs['Roughness'].default_value=.86
p.inputs['Emission Color'].default_value=(.29,.25,.22,1); p.inputs['Emission Strength'].default_value=.18
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.005)); floor=bpy.context.object
floor.name='Daily Hair physical studio ground'; floor.data.materials.append(mat)

def area(name,position,width,height,energy,color):
    bpy.ops.object.light_add(type='AREA',location=position); o=bpy.context.object
    o.name=name; o.data.shape='RECTANGLE'; o.data.size=width; o.data.size_y=height
    o.data.energy=energy; o.data.color=color
    o.rotation_euler=(Vector((0,0,2.2))-o.location).to_track_quat('-Z','Y').to_euler()

area('Daily Hair tall left window',(-4,-3,4.5),1.0,4.2,480,(1,.98,.93))
area('Daily Hair right edge strip',(2.5,1.2,4.2),.55,4,300,(1,1,.98))
area('Daily Hair rear transmission softbox',(1.5,3,5.5),2,3,380,(1,1,.98))
area('Daily Hair soft frontal fill',(0,-5,4),4,4,65,(1,1,1))
bpy.ops.object.camera_add(); camera=bpy.context.object; camera.name='Daily Hair review camera'
camera.data.type='ORTHO'; camera.data.clip_end=200; scene.camera=camera

def project_bounds(objects):
    points=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
    coords=[world_to_camera_view(scene,camera,p) for p in points]
    return [[min(p.x for p in coords),min(p.y for p in coords)],
            [max(p.x for p in coords),max(p.y for p in coords)]]

def frame_product(frame,direction):
    scene.frame_set(frame); bpy.context.view_layer.update()
    points=[o.matrix_world@v.co for o in products for v in o.data.vertices]
    low=Vector([min(p[i] for p in points) for i in range(3)]); high=Vector([max(p[i] for p in points) for i in range(3)])
    floor.location.z=low.z-.005
    target=(low+high)/2; camera.location=target+Vector(direction)
    camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler(); bpy.context.view_layer.update()
    inv=camera.matrix_world.inverted(); local=[inv@p for p in points]
    dx=max(p.x for p in local)-min(p.x for p in local); dy=max(p.y for p in local)-min(p.y for p in local)
    center=Vector(((max(p.x for p in local)+min(p.x for p in local))/2,
                   (max(p.y for p in local)+min(p.y for p in local))/2,0))
    camera.location+=camera.rotation_euler.to_matrix()@center
    camera.data.ortho_scale=max(dy,dx)*1.20; bpy.context.view_layer.update()
    bounds=project_bounds(products)
    assert all(.02<v<.98 for row in bounds for v in row),bounds
    return {'frame':frame,'camera':list(camera.location),'rotation':list(camera.rotation_euler),
            'orthoScale':camera.data.ortho_scale,'projectedBounds':bounds,
            'containerBounds':{o.name:project_bounds([o]) for o in bpy.data.objects['Body'].children}}

poses=[]; shadow_control={}
for name,frame,direction in [('closed',1,(.8,-10,1.2)),('half',31,(.8,-10,1.2)),
                              ('expanded',61,(.8,-10,1.2))]:
    info=frame_product(frame,direction); scene.render.filepath=str(OUT/f'Daily-Hair-Blender-{name}.png')
    bpy.ops.render.render(write_still=True); info['name']=name; poses.append(info)
    if name=='half':
        label_objects=[o for o in bpy.data.objects['Label'].children if o.type=='MESH']
        before={o.name:o.visible_shadow for o in label_objects}
        assert all(before.values())
        for o in label_objects: o.visible_shadow=False
        scene.render.filepath=str(OUT/'Daily-Hair-shadow-control.png'); bpy.ops.render.render(write_still=True)
        for o in label_objects: o.visible_shadow=before[o.name]
        shadow_control={'frame':31,'seed':85,'camera':info['camera'],'rotation':info['rotation'],
                        'orthoScale':info['orthoScale'],'onlyChangedProperty':'Only both thin physical decorative surfaces visible_shadow; four original transparent ink planes remain shadow-disabled',
                        'shadowOn':f'previews/Daily-Hair-Blender-half.png',
                        'shadowOff':'previews/Daily-Hair-shadow-control.png',
                        'containerBounds':info['containerBounds']}

for frame in [1,31,61]:
    frame_product(frame,(.8,-10,1.2))
    camera.keyframe_insert(data_path='location',frame=frame)
    camera.keyframe_insert(data_path='rotation_euler',frame=frame)
    camera.data.keyframe_insert(data_path='ortho_scale',frame=frame)
    floor.keyframe_insert(data_path='location',frame=frame)
scene.frame_set(1)
for screen in bpy.data.screens:
    for a in screen.areas:
        if a.type=='VIEW_3D':
            a.spaces.active.region_3d.view_perspective='CAMERA'
            a.spaces.active.overlay.show_overlays=False; a.spaces.active.shading.type='MATERIAL'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.file.pack_all(); bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'poster-085-v3.blend'),compress=True)
(HERE/'render-verification.json').write_text(json.dumps({'engine':'Cycles','device':'Metal','samples':96,
    'resolution':[1400,1400],'poses':poses,'physicalLabelShadowControl':shadow_control,
    'transparentInkShadowDisabled':True,'visualReviewPending':True,'browserVerifiedSeparately':False},indent=2)+'\n')
print('DAILY_HAIR_CYCLES_RENDERS_COMPLETE')
