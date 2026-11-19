import sqlite3,json,time,uuid
from contextlib import contextmanager

SCHEMA='''
CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY,name TEXT NOT NULL,path TEXT NOT NULL,sha256 TEXT UNIQUE NOT NULL,kind TEXT NOT NULL,status TEXT NOT NULL,detail TEXT NOT NULL DEFAULT '',created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS chunks(id INTEGER PRIMARY KEY,source_id TEXT NOT NULL REFERENCES sources(id),text TEXT NOT NULL,start REAL,end REAL,frame TEXT,kind TEXT NOT NULL,vector TEXT);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(text,content='chunks',content_rowid='id',tokenize='unicode61 remove_diacritics 2');
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN INSERT INTO chunks_fts(rowid,text) VALUES(new.id,new.text); END;
CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN INSERT INTO chunks_fts(chunks_fts,rowid,text) VALUES('delete',old.id,old.text); END;
CREATE TABLE IF NOT EXISTS feedback(id TEXT PRIMARY KEY,case_id TEXT NOT NULL,author TEXT NOT NULL,text TEXT NOT NULL,status TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS cases(id TEXT PRIMARY KEY,name TEXT NOT NULL,source_id TEXT NOT NULL REFERENCES sources(id),profile_path TEXT,status TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,kind TEXT NOT NULL,target TEXT NOT NULL,status TEXT NOT NULL,detail TEXT NOT NULL,created REAL NOT NULL,updated REAL NOT NULL);
CREATE TABLE IF NOT EXISTS chats(id TEXT PRIMARY KEY,question TEXT NOT NULL,answer TEXT NOT NULL,citations TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS feedback_details(feedback_id TEXT PRIMARY KEY REFERENCES feedback(id),source_id TEXT REFERENCES sources(id),generation_id TEXT REFERENCES jobs(id),plan_id TEXT REFERENCES jobs(id));
CREATE TABLE IF NOT EXISTS feedback_attachments(feedback_id TEXT REFERENCES feedback(id),source_id TEXT REFERENCES sources(id),PRIMARY KEY(feedback_id,source_id));
CREATE TABLE IF NOT EXISTS plan_context(job_id TEXT PRIMARY KEY REFERENCES jobs(id),feedback_ids TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS segment_options(job_id TEXT PRIMARY KEY REFERENCES jobs(id),fresh_start INTEGER NOT NULL DEFAULT 0);
'''

class Store:
    def __init__(self,data):
        self.path=data/'knowledge.sqlite3'
        with self.db() as db:db.executescript(SCHEMA)

    @contextmanager
    def db(self):
        db=sqlite3.connect(self.path,timeout=30);db.row_factory=sqlite3.Row
        db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA foreign_keys=ON')
        try:yield db;db.commit()
        except:db.rollback();raise
        finally:db.close()

    def rows(self,sql,args=()):
        with self.db() as db:return [dict(x) for x in db.execute(sql,args)]

    def one(self,sql,args=()):
        rows=self.rows(sql,args);return rows[0] if rows else None

    def execute(self,sql,args=()):
        with self.db() as db:db.execute(sql,args)

    def job(self,kind,target):
        id=uuid.uuid4().hex;now=time.time()
        self.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?)',(id,kind,target,'queued','',now,now));return id

    def update_job(self,id,status,detail=''):
        self.execute('UPDATE jobs SET status=?,detail=?,updated=? WHERE id=?',(status,detail,time.time(),id))

    def queue_segment(self,case_id,connection=None,*,fresh_start=False):
        if connection is None:
            with self.db() as db:
                db.execute('BEGIN IMMEDIATE')
                return self.queue_segment(case_id,db,fresh_start=fresh_start)
        db=connection
        if not db.execute('SELECT id FROM cases WHERE id=?',(case_id,)).fetchone():
            raise ValueError('Caso no encontrado')
        if db.execute("SELECT id FROM jobs WHERE kind='segment' AND target=? AND status IN ('queued','running')",(case_id,)).fetchone():
            raise ValueError('Ya hay una segmentación en curso. Puedes guardar observaciones mientras termina.')
        id=uuid.uuid4().hex;now=time.time()
        db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?)',(id,'segment',case_id,'queued','Preparación automática del STL en cola',now,now))
        ids=[r['id'] for r in db.execute("SELECT id FROM feedback WHERE case_id IN (?, 'general') ORDER BY created DESC",(case_id,))]
        db.execute('INSERT INTO plan_context VALUES(?,?)',(id,json.dumps(ids)))
        db.execute('INSERT INTO segment_options VALUES(?,?)',(id,int(bool(fresh_start))))
        db.execute("UPDATE cases SET status='queued' WHERE id=?",(case_id,))
        return id

    def queue_plan(self,case_id,connection=None):
        if connection is None:
            with self.db() as db:
                db.execute('BEGIN IMMEDIATE')
                return self.queue_plan(case_id,db)
        db=connection
        if db.execute("SELECT id FROM jobs WHERE kind='plan' AND target=? AND status IN ('queued','running')",(case_id,)).fetchone():
            raise ValueError('Ya hay una revisión en curso. Puedes guardar la corrección y pedir otra revisión cuando termine.')
        id=uuid.uuid4().hex;now=time.time()
        db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?)',(id,'plan',case_id,'queued','',now,now))
        # Freeze which observations existed when the technician requested this revision.
        ids=[r['id'] for r in db.execute("SELECT id FROM feedback WHERE case_id IN (?, 'general') ORDER BY created DESC",(case_id,))]
        db.execute('INSERT INTO plan_context VALUES(?,?)',(id,json.dumps(ids)))
        return id

    def feedback_rows(self):
        rows=self.rows('SELECT f.*,d.generation_id,d.plan_id FROM feedback f LEFT JOIN feedback_details d ON d.feedback_id=f.id ORDER BY f.created DESC')
        attachments=self.rows('SELECT a.feedback_id,s.id,s.name,s.status FROM feedback_attachments a JOIN sources s ON s.id=a.source_id')
        for row in rows:row['attachments']=[a for a in attachments if a['feedback_id']==row['id']]
        return rows

    def add_chunks(self,source_id,chunks):
        with self.db() as db:
            db.execute('DELETE FROM chunks WHERE source_id=?',(source_id,))
            for c in chunks:
                db.execute('INSERT INTO chunks(source_id,text,start,end,frame,kind,vector) VALUES(?,?,?,?,?,?,?)',(source_id,c['text'],c.get('start'),c.get('end'),c.get('frame'),c['kind'],json.dumps(c['vector']) if c.get('vector') is not None else None))
