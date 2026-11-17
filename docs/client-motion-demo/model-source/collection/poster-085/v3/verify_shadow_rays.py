"""Actual Blender geometric light visibility from empty container surfaces."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(HERE/'poster-085-v3.blend'))
scene=bpy.context.scene;scene.frame_set(31);bpy.context.view_layer.update()
lamp=bpy.data.objects['Daily Hair tall left window'];light=lamp.matrix_world.translation
casters=[o for o in bpy.data.objects['Label'].children if o.type=='MESH']
assert len(casters)==2 and all(o.visible_shadow for o in casters)
assert all(not o.visible_shadow for n in ['LogoInk','NameInk'] for o in bpy.data.objects[n].children)
def cast(o,p,d,distance):
 inv=o.matrix_world.inverted();hit,q,n,i=o.ray_cast(inv@p,(inv.to_3x3()@d).normalized(),distance=distance)
 return hit,o.matrix_world@q if hit else None
receivers={'bottle':bpy.data.objects['Empty tall cylinder | ivory rounded heel and hollow threaded neck'],
 'tube':bpy.data.objects['Empty flexible tube | sealed tail and open dispensing nozzle']}
samples={}
for name,ob in receivers.items():
 hits=[];tested=0
 # Cast from in front to the actual receiver; then test visibility toward the real key-light center.
 cx=(.64 if name=='bottle' else -.72)+.5
 for iz in range(30):
  z=(.76+iz*1.65/29) if name=='bottle' else (.55+iz*1.4/29)
  width=.42 if name=='bottle' else .24
  for ix in range(31):
   x=cx-width+2*width*ix/30
   hit,p=cast(ob,Vector((x,-1,z)),Vector((0,1,0)),2)
   if not hit:continue
   tested+=1;direction=(light-p).normalized();origin=p+direction*.0001;distance=(light-origin).length
   for caster in casters:
    blocked,q=cast(caster,origin,direction,distance)
    if blocked:
     hits.append({'receiver':list(p),'occluder':caster.name,'point':list(q)});break
 assert hits,(name,'No actual physical label blocks key light from the container')
 samples[name]={'tested':tested,'occludedByPhysicalDecoration':len(hits),'examples':hits[::max(1,len(hits)//5)][:5]}
report={'passed':True,'frame':31,'actualLamp':lamp.name,'lampWorldLocation':list(light),
 'method':'Actual surface ray hits followed by actual key-light-center segment intersections with physical Label meshes. Area-light penumbra is separately evaluated by the Cycles on/off render.',
 'casters':[o.name for o in casters],'receivers':samples,'fourTransparentInkPlanesShadowDisabled':True,
 'sourceSaved':False,'renderImagesChanged':False}
(HERE/'shadow-ray-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('085_SHADOW_RAYS_VERIFIED',json.dumps({n:{k:v for k,v in d.items() if k!='examples'} for n,d in samples.items()}))
