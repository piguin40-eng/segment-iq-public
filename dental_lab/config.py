import json,os,secrets,tempfile
from dataclasses import dataclass,field
from pathlib import Path
from .auth import hash_password
from .platform_paths import install_root,blender_default

@dataclass
class Settings:
    data: Path
    password: str
    username: str = 'admin'
    password_hash: str = ''
    ollama_url: str = 'http://127.0.0.1:11434'
    model: str = 'qwen3-vl:4b-instruct'
    whisper_model: str = 'small'
    embedding_model: str = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
    semantic: bool = True
    vision: bool = True
    frame_seconds: int = 20
    max_frames: int = 720
    blender: str = field(default_factory=blender_default)
    geometry_python: str = ''
    b4d_root: str = ''
    live_blender: bool = False
    agent_harness: str = 'off'
    codex_executable: str = ''
    agent_timeout_seconds: int = 900
    agent_max_attempts: int = 3
    app: Path = Path(__file__).resolve().parents[1]

    def prepare(self):
        self.data=Path(self.data).resolve()
        for name in ['originals','derived','models','inbox','cases','runs','profiles','logs']:(self.data/name).mkdir(parents=True,exist_ok=True)
        return self

def write_config(path, values):
    """Replace the private config atomically without dropping unrelated settings."""
    fd, temporary = tempfile.mkstemp(prefix='.config-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(values, stream, ensure_ascii=False, indent=2)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def set_login(data, username, password):
    username = username.strip()
    if not 1 <= len(username) <= 80:
        raise ValueError('El usuario debe tener entre 1 y 80 caracteres')
    path = Path(data) / 'config.local.json'
    values = json.loads(path.read_text(encoding='utf-8-sig'))
    values.update(username=username, password_hash=hash_password(password))
    write_config(path, values)


def load():
    root=Path(os.environ.get('DENTAL_LAB_DATA',str(install_root()/'data'))).resolve()
    root.mkdir(parents=True,exist_ok=True);path=root/'config.local.json'
    values=json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else {'password':secrets.token_urlsafe(24)}
    if 'password_hash' not in values or 'username' not in values:
        values.setdefault('username','admin')
        values.setdefault('password_hash',hash_password(values['password']))
        write_config(path,values)
    allowed=set(Settings.__dataclass_fields__)-{'data','app'}
    return Settings(data=root,**{k:v for k,v in values.items() if k in allowed}).prepare()
