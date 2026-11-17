"""Discard unused pump UV and share equal translated pump geometry, without decimation."""
import bpy, json, hashlib
from pathlib import Path
from mathutils import Vector

HERE=Path(__file__).resolve().parent

def optimize():
    a=bpy.data.objects['LOTION complete white pump']; b=bpy.data.objects['WASH complete white pump']
    if a.data is b.data:
        return {'alreadyShared':True,'meshUsers':a.data.users}
    assert len(a.data.vertices)==len(b.data.vertices)
    assert len(a.data.polygons)==len(b.data.polygons)
    assert all(tuple(p.vertices)==tuple(q.vertices) and p.use_smooth==q.use_smooth
               and p.material_index==q.material_index for p,q in zip(a.data.polygons,b.data.polygons))
    before={o.name:[o.matrix_world@v.co for v in o.data.vertices] for o in (a,b)}
    maximum_centered_error=max(((va.co+Vector((.7,0,0)))-(vb.co-Vector((.7,0,0)))).length
                               for va,vb in zip(a.data.vertices,b.data.vertices))
    assert maximum_centered_error<2e-6, maximum_centered_error
    removed={}
    for o,cx in [(a,-.7),(b,.7)]:
        removed[o.name]=[layer.name for layer in o.data.uv_layers]
        for layer in list(o.data.uv_layers): o.data.uv_layers.remove(layer)
        for v in o.data.vertices: v.co.x-=cx
        o.location.x+=cx
        o.data.update()
    b.data=a.data; a.data.name='Shared complete white ribbed pump with real outlet and connector'
    bpy.context.view_layer.update()
    after_errors={o.name:max(((o.matrix_world@v.co)-p).length for v,p in zip(o.data.vertices,before[o.name])) for o in (a,b)}
    assert all(v<2e-6 for v in after_errors.values())
    return {'sameTopologyAndSmoothing':True,'maximumCenteredCoordinateError':maximum_centered_error,
            'maximumWorldCoordinateErrors':after_errors,'removedUnusedUV':removed,
            'sharedMeshUsers':a.data.users,'logicalWhitePumpObjects':2,'decimationUsed':False,
            'geometryDifferenceIsFloat32TranslationRounding':True}

if __name__=='__main__':
    bpy.ops.wm.open_mainfile(filepath=str(HERE/'poster-084-v3.blend'))
    scene=bpy.context.scene; scene.frame_set(1); bpy.context.view_layer.update()
    report=optimize()
    root_names=['Body','Pump','Label','LogoInk','NameInk']
    bpy.ops.object.select_all(action='DESELECT')
    for name in root_names:
        root=bpy.data.objects[name]; root.select_set(True)
        for child in root.children_recursive: child.select_set(True)
    glb=HERE.parents[3]/'packaging-assets/poster-084-v3.glb'
    before=glb.stat().st_size
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,
                              export_yup=True,export_extras=True,export_animations=False)
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.file.pack_all(); bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'poster-084-v3.blend'),compress=True)
    report.update(glbBeforeBytes=before,glbAfterBytes=glb.stat().st_size,
                  glbSha256=hashlib.sha256(glb.read_bytes()).hexdigest())
    (HERE/'mesh-optimization.json').write_text(json.dumps(report,indent=2)+'\n')
    build=json.loads((HERE/'build-verification.json').read_text())
    build.update(glbBytes=glb.stat().st_size,glbSha256=report['glbSha256'],meshOptimization=report)
    (HERE/'build-verification.json').write_text(json.dumps(build,ensure_ascii=False,indent=2)+'\n')
    print('SOFT_BODY_MESH_OPTIMIZED',json.dumps(report))
