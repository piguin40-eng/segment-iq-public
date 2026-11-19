"""Recognise explicit, bounded lab constraints without executing model/document code."""
import re
import unicodedata


def normalized(text):
    text=''.join(c for c in unicodedata.normalize('NFKD', text.lower()) if not unicodedata.combining(c))
    return re.sub(r'\blabarra\b','la barra',text)


def effective_feedback(history):
    """A general criterion mirrored to this case by one save is one adjustment."""
    rows=sorted(history.get('feedback',[]),key=lambda r:r['created'])
    result=[]
    for row in rows:
        body=' '.join(normalized(row['text']).split('ejecucion asociada:')[0].split())
        duplicate=next((i for i,old in enumerate(result)
            if 'general' in {row.get('case_id'),old.get('case_id')} and row.get('case_id')!=old.get('case_id')
            and row.get('author','').lower()==old.get('author','').lower()
            and abs(row['created']-old['created'])<=5
            and body==' '.join(normalized(old['text']).split('ejecucion asociada:')[0].split())),None)
        if duplicate is not None:
            if row.get('case_id')!='general':result[duplicate]=row
        else:result.append(row)
    return result


def observation_intents(text):
    """Bind direction and amount to each dimension, not to unrelated words in a note.

    A repeated qualitative request within one observation is one adjustment.
    Unknown clauses remain visible even when another clause is supported.
    """
    text = normalized(text).split('ejecucion asociada:')[0]
    clauses = re.split(r'(?<!\d)[.,;!\n]+|[.,](?!\d)|\s+y\s+(?=(?:por ultimo|centr|baj|reduc|aument|sub|proteg|la |el |los |las ))', text)
    intents = {}; pending = []
    for clause in clauses:
        clause = clause.strip()
        if not clause: continue
        recognized = False
        shape_clause=bool(re.search(r'bisel|visel|chaflan|piramid|contorno|terminacion|barra.*(?:fina|estrecha)',clause))
        if shape_clause and (re.search(r'\bno\s+(?:\w+\s+){0,2}(?:reduc|quit|elimin|suav|afin|estrech|hacer)',clause) or re.search(r'\d+(?:[.,]\d+)?\s*mm',clause)):
            pending.append(clause);continue
        if re.search(r'(?:linea|terminacion|margen|contorno)',clause) and re.search(r'continu|sin picos|suav|redonde',clause):
            intents['smooth_margin']=True;recognized=True
        if re.search(r'piramid|pico|cresta',clause) and re.search(r'reduc|quit|elimin|suav|aplan|sin ',clause) and not re.search(r'\bno\s+(?:reduc|quit|elimin)',clause):
            if re.search(r'superior|arriba|barra|piramid',clause):intents['smooth_roof']=True;recognized=True
        if re.search(r'\b(?:bisel|visel|chaflan)\b',clause) and re.search(r'barra|terminacion|final|margen|apoy',clause):
            if re.search(r'\b(?:sin|no)\b',clause):pending.append(clause)
            else:intents['cervical_bevel']=True
            recognized=True
        if re.search(r'barra\s+(?:mas\s+)?(?:fina|estrecha)|(?:afinar|estrechar)\s+(?:la\s+)?barra',clause):
            if re.search(r'\bno\s+(?:\w+\s+)?(?:afin|estrech)',clause):pending.append(clause)
            else:intents['slimmer_bar']=True
            recognized=True
        if re.search(r'implante|conexion|interfa[sc]', clause) and re.search(r'centr|(?:en|por) (?:el )?medio|ambos lados|mismo espacio', clause):
            if re.search(r'\bno\s+(?:debes?\s+)?centr|\bno\s+(?:(?:deben?|deberian?)\s+)?pas\w*\s+por\s+(?:el\s+)?medio', clause):
                pending.append(clause)
                continue
            intents['center_connections'] = True
            recognized = True
        if re.search(r'chimenea|interfa[sc]e|conexion', clause) and re.search(r'proteg|protej|perimetro', clause):
            intents['protect_connections'] = True; recognized = True
        if re.search(r'detect\w*.*chimenea',clause):
            intents['protect_connections'] = True; recognized = True
        if re.search(r'conexion|interfase',clause) and re.search(r'direct\w*.*implante|implante.*direct',clause):
            intents['protect_connections'] = True; recognized = True
        regional = bool(re.search(r'\b(zona|pieza|distal|izquierda|derecha|anterior|posterior)\b', clause))
        for dimension, noun in [('height', r'(?:altura|barra|metal|primaria)'), ('width', r'(?:anchura|ancho|profundidad)')]:
            # The adjective immediately beside the dimension has priority over
            # "más soporte a la supra" or "menos zirconio" elsewhere in a note.
            lower = rf'(?:(?:baj\w*|reduc\w*|menos|menor)\s+(?:\w+\s+){{0,3}}{noun}\b|{noun}\s+(?:\w+\s+){{0,2}}(?:mas\s+baj\w*|demasiad\w*\s+alt\w*|muy\s+alt\w*|menos\s+alt\w*))'
            higher = rf'(?:(?:aument\w*|subir|mayor|mas)\s+(?:\w+\s+){{0,2}}{noun}\b|{noun}\s+(?:mas\s+alt\w*|mayor))'
            less_match = re.search(lower, clause)
            if dimension == 'height' and not less_match:
                less_match = re.search(r'demasiad\w*\s+altura(?:\s+\w+){0,3}\s+(?:metal|barra|primaria)\b',clause)
            more_match = re.search(higher, clause)
            # "más baja la barra" is a reduction, not an increase.
            if more_match and re.search(r'baj|reduc', more_match[0]): more_match = None
            if not less_match and not more_match: continue
            if regional:
                pending.append(clause); recognized = True; continue
            if re.search(r'\bno\s+(?:\w+\s+){0,2}(?:baj|reduc|aument|sub)', clause):
                pending.append(clause); recognized = True; continue
            if less_match and more_match and not (set(range(*less_match.span())) & set(range(*more_match.span()))):
                pending.append(clause); recognized = True; continue
            match = less_match or more_match
            # Only numbers attached to the matched adjustment, never the later
            # minimum wall thickness (e.g. "bajar barra; supra mínimo 0.8 mm").
            amount_match = re.match(r'\s*(?:(?:de|del|la|el|barra|metal|primaria|altura|en|unos|aproximadamente)\s+)*(\d+(?:[.,]\d+)?)\s*mm\b', clause[match.end():])
            amount = float(amount_match[1].replace(',', '.')) if amount_match else .5
            if not 0 < amount <= 1.5:
                pending.append(clause); recognized = True; continue
            intents[dimension] = (-1 if less_match else 1) * (amount if dimension == 'height' else 5.)
            recognized = True
        if not recognized: pending.append(clause)
    return intents, list(dict.fromkeys(pending))

def regional_and_thickness(text):
    text=text.lower()
    anterior=bool(re.search(r'altura|alto|alta',text) and re.search(r'm[aá]s|mayor|aument',text) and 'anterior' in text)
    minimum=re.search(r'(?:grosor|espesor)\s+m[ií]nimo[^\d]{0,20}(\d+(?:[.,]\d+)?)\s*mm\b',text)
    thickness=float(minimum[1].replace(',','.')) if minimum else None
    if thickness is not None and not .3<=thickness<=3:
        thickness=None
    return anterior,thickness

def requested_rules(history):
    anterior=[];thickness=[];anterior_delta=1.;height_goal=None;height_goal_feedback=None
    for row in effective_feedback(history):
        if row.get('status') not in {'correction','rejected'}:continue
        a,t=regional_and_thickness(row['text'])
        if a:
            if height_goal=='homogeneous':anterior_delta=1.
            height_goal='anterior_higher';height_goal_feedback=row['id']
            anterior.append(row['id'])
            for sentence in re.split(r'(?<=[.!?])\s+|\n',row['text'].lower()):
                if 'anterior' not in sentence or not re.search(r'altura|alto|alta',sentence):continue
                match=re.search(r'(\d+(?:[.,]\d+)?)\s*mm\b',sentence)
                if match and not re.search(r'grosor|espesor',sentence):
                    amount=float(match[1].replace(',','.'))
                    if not 0<amount<=3:raise ValueError('El aumento anterior solicitado debe medirse; supera el intervalo de adaptación automática de 0 a 3 mm.')
                    anterior_delta=amount
        text=normalized(row['text'])
        uniform=re.search(r'\bmisma altura\b|\baltura\s+(?:aproximadamente\s+)?(?:uniforme|homogenea)\b',text)
        negated=uniform and re.search(r'\bno\b[^.;\n]{0,45}$',text[:uniform.start()])
        if uniform and not negated:
            anterior=[];anterior_delta=0.
            height_goal='homogeneous';height_goal_feedback=row['id']
        if t is not None:thickness.append((row['id'],t))
    return {'anterior_feedback_ids':anterior,'anterior_delta_mm':anterior_delta,'minimum_supra_mm':thickness[-1][1] if thickness else None,
            'minimum_feedback_ids':[id for id,_ in thickness],
            'height_goal':height_goal,'height_goal_feedback_id':height_goal_feedback}


def shape_rules(history):
    selected={};narrowing=0.
    for row in effective_feedback(history):
        if row.get('status') not in {'correction','rejected'}:continue
        intents,_=observation_intents(row['text'])
        if intents.get('slimmer_bar'):narrowing=min(.8,narrowing+.2)
        for key in ('smooth_margin','smooth_roof','cervical_bevel','slimmer_bar'):
            if intents.get(key):selected[key]=row['id']
    return {'smooth_margin':bool(selected.get('smooth_margin')),
            'smooth_roof':bool(selected.get('smooth_roof')),
            'cervical_bevel_mm':.2 if selected.get('cervical_bevel') else 0.,
            'bar_narrowing_per_side_mm':narrowing,
            'feedback_ids':selected}
