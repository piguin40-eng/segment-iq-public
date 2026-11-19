import json,sys
from pathlib import Path
from types import SimpleNamespace
import pytest
from test_core import client
from dental_lab.learning_geometry import geometry_chunks,measure_geometry,snapshot_case_learning


def test_geometry_ingestion_indexes_measured_mesh_not_only_filename(client):
    import trimesh
    c,app=client;app.state.settings.geometry_python=sys.executable
    source=c.post('/api/upload',files={'file':('reference.stl',trimesh.creation.box([2,3,4]).export(file_type='stl'))}).json()['id']
    app.state.ingest.process(source)
    report=json.loads((app.state.settings.data/'derived'/source/'geometry.json').read_text())
    assert report['watertight'] and report['signed_volume']==pytest.approx(24)
    assert not report['geometry_exported']
    hits=app.state.rag.search('reference signed_volume',semantic=False)
    assert any(r['source_id']==source and r['kind']=='geometria_medida' for r in hits)


def test_blend_reader_disables_embedded_execution_and_checks_hash(tmp_path,monkeypatch):
    settings=SimpleNamespace(app=tmp_path,blender='blender',geometry_python=sys.executable)
    source={'path':str(tmp_path/'reference.blend'),'name':'Finished.blend','sha256':'expected'}
    commands=[]
    def process(command,**kwargs):
        commands.append(command)
        Path(command[-1]).write_text(json.dumps({'source_sha256':'wrong'}))
    monkeypatch.setattr('dental_lab.learning_geometry.subprocess.run',process)
    with pytest.raises(ValueError,match='cambiado'):measure_geometry(settings,source,tmp_path/'derived')
    assert '--disable-autoexec' in commands[0] and '--factory-startup' in commands[0]
    assert commands[0].index('--disable-autoexec')<commands[0].index('--python')


def test_explicit_case_examples_are_pinned_beyond_rag_first_four_without_copying_meshes(client,tmp_path):
    c,app=client;s=app.state.settings;db=app.state.store
    ids=[c.post('/api/upload',files={'file':(f'stage{i}.blend',f'geometry{i}'.encode())}).json()['id'] for i in range(7)]
    document=c.post('/api/upload',files={'file':('history.py',b'print("reference only")')}).json()['id']
    attachments=[{'id':sid} for sid in ids+[document]]
    history={'feedback':[{'case_id':'other','attachments':attachments},{'case_id':'case','attachments':attachments}]}
    last=db.one('SELECT * FROM sources WHERE id=?',(ids[-1],))
    folder=s.data/'derived'/last['id'];folder.mkdir()
    (folder/'geometry.json').write_text(json.dumps({'source_sha256':last['sha256'],'format':'BLEND'}))
    workspace=tmp_path/'workspace';workspace.mkdir()
    records=snapshot_case_learning(s,db,history,'case',workspace)
    assert len(records)==8
    assert records[-2]['local_measurements'].endswith('.geometry.json')
    assert records[-1]['local_document'].endswith('.reference.txt')
    assert not list(workspace.rglob('*.blend')) and not list(workspace.rglob('*.py'))
    assert (workspace/'Aprendizajes_caso.json').is_file()


def test_scene_index_records_modifier_value_without_claiming_gap_or_approval():
    source={'name':'CementGap.blend'}
    report={'format':'BLEND','object_count':1,'unit_system':'METRIC','unit_scale':.001,
        'objects':[{'name':'CuttingTool','type':'MESH','modifiers':[{'type':'SOLIDIFY','thickness':.14,'offset':0}]}]}
    chunks=geometry_chunks(source,report)
    assert any('0.14' in row['text'] and 'SOLIDIFY' in row['text'] for row in chunks)
    assert all('no es una nueva segmentación ni aprobación' in row['text'] for row in chunks)


def test_hidden_scene_objects_use_stored_transforms_and_do_not_invent_constraint_positions():
    import importlib.util,numpy as np
    spec=importlib.util.spec_from_file_location('learning_reader',Path(__file__).parents[1]/'engine/inspect_learning_geometry.py')
    reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
    basis=np.eye(4);basis[:3,3]=[10,20,30]
    parent=SimpleNamespace(matrix_basis=basis,parent=None,constraints=[])
    child=SimpleNamespace(matrix_world=np.zeros((4,4)),matrix_basis=np.eye(4),matrix_parent_inverse=np.eye(4),parent=parent,parent_type='OBJECT',constraints=[])
    assert reader.stored_matrix(child)==pytest.approx(basis)
    child.constraints=['unresolved']
    assert reader.stored_matrix(child) is None
