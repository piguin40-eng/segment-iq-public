from dental_lab.progress import result_file_groups


def files(*paths):
    return [{'path':path,'name':path.rsplit('/',1)[-1],'size':1} for path in paths]


def test_latest_complete_preview_and_exports_are_not_mixed_with_older_attempts():
    old='Intentos/01/outputs/Inferior_independiente/'
    new='Intentos/03/outputs/Inferior_independiente/'
    rows=result_file_groups(files(old+'Vista_propia.png',new+'Vista_propia.png',
        old+'Primaria_SUP_PROPIA.stl',new+'Primaria_SUP_PROPIA.stl',
        new+'Supra_SUP_PROPIA.stl',new+'08_SUP_propia.blend',
        'Intentos/03/work/inf_independiente/Primaria_final.stl',
        old+'03_Diseno.blend',new+'03_Diseno.blend','Propuesta_para_revision.zip'))
    preview=[r for r in rows if r['display_group']=='preview']
    assert len(preview)==1 and preview[0]['path']==new+'Vista_propia.png'
    assert 'intento 3' in preview[0]['proposal_label']
    primary=[r['path'] for r in rows if r['display_group']=='principal']
    assert primary==[new+'Primaria_SUP_PROPIA.stl',new+'Supra_SUP_PROPIA.stl',new+'08_SUP_propia.blend','Propuesta_para_revision.zip']
    assert [r['path'] for r in rows if r['display_group']=='stage']==[new+'03_Diseno.blend']
    assert next(r for r in rows if r['path'].endswith('/Primaria_final.stl'))['display_group']=='technical'


def test_published_proposal_wins_over_attempt_number():
    root='Inferior_independiente/'
    rows=result_file_groups(files('Intentos/03/outputs/'+root+'Vista_propia.png',root+'Vista_propia.png',root+'Primaria_SUP_PROPIA.stl'))
    assert [r['path'] for r in rows if r['display_group']=='preview']==[root+'Vista_propia.png']
    assert [r['path'] for r in rows if r['display_group']=='principal']==[root+'Primaria_SUP_PROPIA.stl']


def test_intermediate_working_stl_is_never_a_final_download():
    rows=result_file_groups(files('Intentos/01/work/inf_independiente/Primaria_sin_retenciones.stl'))
    assert all(r['display_group']=='technical' for r in rows)
