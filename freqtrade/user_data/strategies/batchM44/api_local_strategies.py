"""Local authenticated strategy files only; independent of the trading engine."""
import ast
import hashlib
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from freqtrade.rpc.api_server.deps import get_config

router = APIRouter()
lock = threading.Lock()
NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,79}$")

class Save(BaseModel):
    content: str = Field(max_length=300000)
    revision: str | None = None

class Create(BaseModel):
    name: str
    source: str | None = None

def root(config):
    if config.get('dry_run') is not True:
        raise HTTPException(403, 'Trình sửa chỉ hoạt động khi dry_run=true.')
    return (Path(config['user_data_dir']) / 'strategies').resolve()

def target(name, config):
    if not NAME.fullmatch(name) or name.startswith('__'):
        raise HTTPException(422, 'Tên chỉ gồm chữ, số, dấu gạch dưới và bắt đầu bằng chữ.')
    base = root(config)
    p = base / (name + '.py')
    if p.is_symlink() or p.resolve().parent != base:
        raise HTTPException(403, 'Không cho phép đường dẫn liên kết.')
    return p

def validate(content, name):
    try:
        tree = ast.parse(content)
        compile(tree, '<strategy>', 'exec')
    except (SyntaxError, ValueError) as e:
        raise HTTPException(422, f'Lỗi cú pháp dòng {getattr(e, "lineno", 0)}: {e}')
    if not any(isinstance(n, ast.ClassDef) and n.name == name for n in tree.body):
        raise HTTPException(422, f'Cần một class {name} trùng tên tệp.')

def read(p):
    if not p.is_file():
        raise HTTPException(404, 'Không tìm thấy chiến lược.')
    b = p.read_bytes()
    return {'name': p.stem, 'content': b.decode('utf-8-sig'), 'revision': hashlib.sha256(b).hexdigest()}

@router.get('')
def listing(config=Depends(get_config)):
    base = root(config)
    return {'strategies': sorted(p.stem for p in base.glob('*.py') if not p.is_symlink() and NAME.fullmatch(p.stem)),
            'protected': ['StarterFutures'], 'engine': '2026.9', 'mode': 'backtest / paper only'}

@router.get('/{name}')
def get(name: str, config=Depends(get_config)):
    return read(target(name, config))

@router.post('')
def create(req: Create, config=Depends(get_config)):
    p = target(req.name, config)
    if req.source:
        src = read(target(req.source, config))['content']
        tree = ast.parse(src)
        cls = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == req.source), None)
        if cls is None:
            raise HTTPException(422, 'Class nguồn không trùng tên tệp.')
        # Replace the class declaration only, preserving its indicators and imports.
        lines = src.splitlines(keepends=True)
        lines[cls.lineno - 1] = re.sub(r'\bclass\s+' + re.escape(req.source) + r'\b', 'class ' + req.name, lines[cls.lineno - 1], count=1)
        content = ''.join(lines)
    else:
        content = '''"""Mẫu nghiên cứu: chưa có tín hiệu vào lệnh. Chỉ backtest/paper."""
from freqtrade.strategy import IStrategy
from pandas import DataFrame

class NAME(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "15m"
    can_short = True
    startup_candle_count = 200
    minimal_roi = {"0": 0.04}
    stoploss = -0.02

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        return dataframe

    def leverage(self, pair, current_time, current_rate, proposed_leverage, max_leverage, entry_tag, side, **kwargs):
        return 1.0
'''.replace('class NAME(', 'class ' + req.name + '(')
    validate(content, req.name)
    with lock:
        try:
            with p.open('x', encoding='utf-8', newline='\n') as f:
                f.write(content)
        except FileExistsError:
            raise HTTPException(409, 'Tên đã tồn tại. Hãy chọn tên khác.')
    return read(p)

@router.put('/{name}')
def save(name: str, req: Save, config=Depends(get_config)):
    p = target(name, config)
    if name == 'StarterFutures':
        raise HTTPException(409, 'StarterFutures đang dùng cho paper. Hãy tạo bản sao để sửa.')
    validate(req.content, name)
    with lock:
        before = read(p)
        if not req.revision or req.revision != before['revision']:
            raise HTTPException(409, 'Tệp đã thay đổi. Tải lại trước khi lưu để tránh ghi đè.')
        backup = root(config).parent / 'strategy_editor_backups' / name
        backup.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        (backup / (stamp + '.py')).write_bytes(p.read_bytes())
        temp = p.with_suffix('.py.editor-tmp')
        try:
            with temp.open('w', encoding='utf-8', newline='\n') as f:
                f.write(req.content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp, p)
        finally:
            temp.unlink(missing_ok=True)
    return read(p)
