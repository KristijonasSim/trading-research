"""Paper profiles backed by native Freqtrade configuration, RPC and a separate service.

The service always starts with CLI --dry-run. No Docker socket or process launcher API.
"""
import importlib
import json
import secrets
import sqlite3
import sys
import threading
import time
from copy import deepcopy
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from freqtrade.rpc.api_server.deps import get_config
from freqtrade.rpc.api_server.api_local_strategies import NAME
from freqtrade.rpc.api_server.api_runs import digest, run_path, verify_run
from freqtrade.rpc.api_server.api_studio import storage, write_check
from freqtrade.rpc.api_server import paper_history

router = APIRouter()
paper_lock = threading.RLock()
WORKER_URL = 'http://research-paper:8080/api/v1'
PAIRS = {'BTC/USDT:USDT', 'ETH/USDT:USDT'}


def paper_root(config):
    if config.get('dry_run') is not True or any(config.get('exchange', {}).get(k) for k in ('key', 'secret', 'password')):
        raise HTTPException(403, 'Paper workspace yêu cầu dry_run=true và không có khóa giao dịch.')
    p = storage(config) / 'paper'
    p.mkdir(exist_ok=True)
    return p


def validate_recipe(cfg):
    ex = cfg.get('exchange', {})
    if cfg.get('dry_run') is not True or cfg.get('trading_mode') != 'futures' or cfg.get('margin_mode') != 'isolated':
        raise HTTPException(409, 'Chỉ cho phép paper Binance Futures isolated.')
    if ex.get('name') != 'binance' or any(ex.get(k) for k in ('key', 'secret', 'password')):
        raise HTTPException(409, 'Cấu hình paper không được có khóa giao dịch sàn.')
    if not ex.get('pair_whitelist') or not set(ex['pair_whitelist']).issubset(PAIRS):
        raise HTTPException(409, 'Bộ cài hiện tại chỉ dùng BTC/ETH USDT-M.')
    if not str(cfg.get('strategy', '')).startswith('FPPaper') or cfg.get('initial_state') not in ('stopped','paused'):
        raise HTTPException(409, 'Cấu hình phải dùng lớp paper 1x và không tự mở lệnh khi khởi động.')
    from freqtrade.configuration.config_validation import validate_config_schema
    from freqtrade.exceptions import ConfigurationError
    try:
        validate_config_schema(cfg)
    except ConfigurationError as error:
        raise HTTPException(409, 'Cấu hình chưa đạt schema Freqtrade: ' + str(error))


def api_config(config):
    p = paper_root(config) / 'api.json'
    if not p.exists():
        api = deepcopy(config['api_server'])
        api.update(enabled=True, listen_ip_address='0.0.0.0', listen_port=8080,
                   jwt_secret_key=secrets.token_hex(32), ws_token=secrets.token_urlsafe(32))
        api['CORS_origins'] = sorted(set(api.get('CORS_origins', []) + [
            f'http://{host}:{port}' for host in ('localhost', '127.0.0.1') for port in (8090, 8091, 8095)]))
        write_check(p, api)
    return json.loads(p.read_text(encoding='utf-8'))


def config_for(config, source, folder, strategy, label):
    if source.get('exchange', {}).get('name') != 'binance' or source.get('trading_mode') != 'futures' or source.get('margin_mode') != 'isolated':
        raise HTTPException(409, 'Hồ sơ nguồn phải là Binance Futures isolated.')
    cfg = deepcopy(source)
    if cfg.get('stake_amount') != 'unlimited':
        cfg['stake_amount'] = float(cfg['stake_amount'])
    cfg['max_open_trades'] = int(cfg['max_open_trades'])
    cfg['dry_run_wallet'] = float(cfg['dry_run_wallet'])
    for key in ('timerange', 'timeframe_detail', 'backtest_cache', 'enable_protections', 'export'):
        cfg.pop(key, None)
    cfg.update(dry_run=True, trading_mode='futures', margin_mode='isolated', stake_currency='USDT',
               strategy=strategy, strategy_path=str(folder / 'strategies'), recursive_strategy_search=False,
               user_data_dir=str(folder), datadir=str(folder / 'data'),
               db_url='sqlite:///' + str(folder / 'paper.sqlite'),
               logfile=str(folder / 'logs/paper.log'), initial_state='stopped',
               bot_name='FreqPilot paper · ' + label + ' #' + uuid4().hex[:8], force_entry_enable=False,
               api_server=api_config(config), internals={'process_throttle_secs': 5},
               pairlists=[{'method': 'StaticPairList'}])
    cfg['exchange'] = {'name': 'binance', 'key': '', 'secret': '',
                       'pair_whitelist': source['exchange']['pair_whitelist'], 'pair_blacklist': []}
    validate_recipe(cfg)
    for child in ('strategies', 'data', 'logs'):
        (folder / child).mkdir(parents=True, exist_ok=True)
    return cfg


IDLE_SOURCE = '''from freqtrade.strategy import IStrategy
class FPPaperIdle(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '15m'
    can_short = True
    startup_candle_count = 200
    minimal_roi = {'0': 0.04}
    stoploss = -0.02
    def populate_indicators(self, dataframe, metadata): return dataframe
    def populate_entry_trend(self, dataframe, metadata):
        dataframe['enter_long'] = 0
        dataframe['enter_short'] = 0
        return dataframe
    def populate_exit_trend(self, dataframe, metadata):
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0
        return dataframe
    def leverage(self, *args, **kwargs): return 1.0
'''


def bootstrap(config):
    """Run before the dedicated native worker, never start entries on service boot."""
    root = paper_root(config)
    active = root / 'active/config.json'
    active.parent.mkdir(exist_ok=True)
    if active.exists():
        cfg = json.loads(active.read_text(encoding='utf-8'))
        validate_recipe(cfg)
        if cfg['strategy'] != 'FPPaperIdle':
            owner = next((p for p in (root / 'profiles').glob('*/record.json')
                          if json.loads(p.read_text())['wrapper'] == cfg['strategy']), None)
            if owner is None:
                raise HTTPException(409, 'Không tìm thấy hồ sơ của cấu hình paper đang chọn.')
            verify_profile(owner.parent.name, config)
        # Preserve exit management across a worker restart, without resuming entries.
        database = Path(cfg['db_url'].removeprefix('sqlite:///'))
        if not database.resolve().is_relative_to(root.resolve()):
            raise HTTPException(409, 'Database paper phải nằm trong workspace riêng.')
        count = 0
        if database.is_file():
            with closing(sqlite3.connect(database.as_uri()+'?mode=ro', uri=True)) as conn:
                if conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trades'").fetchone():
                    count = conn.execute('SELECT count(*) FROM trades WHERE is_open=1').fetchone()[0]
        cfg['initial_state'] = 'paused' if count else 'stopped'
        validate_recipe(cfg)
        write_check(active, cfg)
        return active
    from freqtrade.rpc.api_server.api_runs import reproducible_config
    folder = root / 'idle'
    cfg = config_for(config, reproducible_config(config, {}, 'FPPaperIdle'), folder, 'FPPaperIdle', 'chưa chọn hồ sơ')
    (folder / 'strategies/FPPaperIdle.py').write_text(IDLE_SOURCE, encoding='utf-8')
    write_check(active, cfg)
    return active


def profile_path(uid, config):
    import re
    if not re.fullmatch(r'[0-9a-f]{32}', uid):
        raise HTTPException(422, 'Mã hồ sơ paper không hợp lệ.')
    p = paper_root(config) / 'profiles' / uid
    if p.is_symlink() or not (p / 'record.json').is_file():
        raise HTTPException(404, 'Không có hồ sơ paper này.')
    return p


def profile_visibility(uid, config):
    """Mutable UI state, kept outside the frozen profile record and source hashes."""
    path = profile_path(uid, config) / 'visibility.json'
    if path.is_symlink():
        raise HTTPException(409, 'Trạng thái hiển thị hồ sơ không hợp lệ.')
    if not path.exists():
        return {'archived': False, 'archived_at': None}
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise HTTPException(409, 'Không đọc được trạng thái hiển thị hồ sơ.')
    if not isinstance(value, dict) or type(value.get('archived')) is not bool:
        raise HTTPException(409, 'Trạng thái hiển thị hồ sơ không hợp lệ.')
    return {'archived': value['archived'], 'archived_at': value.get('archived_at')}


def set_profile_visibility(uid, config, archived):
    path = profile_path(uid, config) / 'visibility.json'
    profile_visibility(uid, config)
    value = {'archived': archived,
             'archived_at': datetime.now(timezone.utc).isoformat() if archived else None}
    write_check(path, value)
    return value


def load_paper_base(name, folder):
    """Import fresh local helpers after native reload_config in the paper process."""
    if not NAME.fullmatch(name):
        raise RuntimeError('Invalid strategy name')
    profiles = Path(folder).resolve().parent.parent
    for key, module in list(sys.modules.items()):
        filename = getattr(module, '__file__', None)
        if filename and not Path(filename).name.startswith('FPPaper_') and Path(filename).resolve().is_relative_to(profiles):
            sys.modules.pop(key, None)
    sys.path.insert(0, str(folder))
    try:
        return getattr(importlib.import_module(name), name)
    finally:
        sys.path.remove(str(folder))


class PreparePaper(BaseModel):
    run_id: str
    label: str = Field(default='', max_length=70)


@router.post('/paper/profiles')
def prepare_paper(req: PreparePaper, config=Depends(get_config)):
    with paper_lock:
        paper_root(config)
        if not verify_run(req.run_id, config)['valid']:
            raise HTTPException(409, 'Gói backtest không còn khớp hash.')
        origin = run_path(req.run_id, config)
        run = json.loads((origin / 'record.json').read_text(encoding='utf-8'))
        uid = uuid4().hex
        folder = paper_root(config) / 'profiles' / uid
        stratdir = folder / 'strategies'
        stratdir.mkdir(parents=True)
        with ZipFile(origin / 'artifact.zip') as archive:
            frozen = json.loads(archive.read('inputs.json'))
            if run['strategy'] != frozen['strategy'] or run['revision'] != frozen['revision']:
                raise HTTPException(409, 'Thông tin hồ sơ không khớp gói lưu.')
            for name in frozen['files']:
                if not name.startswith('inputs/strategies/'):
                    continue
                relative = name.removeprefix('inputs/strategies/')
                path = stratdir / relative
                if not path.resolve().is_relative_to(stratdir.resolve()) or path.suffix not in ('.py', '.json'):
                    raise HTTPException(409, 'Đường dẫn mã trong gói không hợp lệ.')
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(archive.read(name))
            source = frozen['config']
        wrapper = 'FPPaper_' + uid[:16]
        wrapper_code = f'''from pathlib import Path
from freqtrade.rpc.api_server.api_paper import load_paper_base
Base = load_paper_base({run['strategy']!r}, Path(__file__).parent)
class {wrapper}(Base):
    # Paper policy: inherited signals stay intact; leverage is always capped to 1x.
    def leverage(self, *args, **kwargs): return 1.0
'''
        (stratdir / (wrapper + '.py')).write_text(wrapper_code, encoding='utf-8')
        parameter_file = stratdir / (run['strategy'] + '.json')
        if parameter_file.exists():
            params = json.loads(parameter_file.read_text(encoding='utf-8-sig'))
            params['strategy_name'] = wrapper
            write_check(stratdir / (wrapper + '.json'), params)
        label = req.label.strip() or run['strategy']
        cfg = config_for(config, source, folder, wrapper, label)
        write_check(folder / 'config.json', cfg)
        warnings = []
        summary = run.get('summary', {})
        if summary.get('total_trades', 0) < 30:
            warnings.append('Backtest có ít hơn 30 lệnh, chưa đủ kết luận chất lượng.')
        if summary.get('profit_total_abs', 0) <= 0:
            warnings.append('Backtest chưa có lãi. Paper là thí nghiệm quan sát, không phải khuyến nghị triển khai.')
        warnings.append('Kiểm tra lookahead/warmup và kết quả ngoài mẫu trước khi đánh giá. Paper dùng dữ liệu công khai hiện tại, không phải đoạn backtest cũ.')
        record = {'id': uid, 'run_id': req.run_id, 'strategy': run['strategy'], 'wrapper': wrapper,
                  'label': label, 'revision': run['revision'], 'created_at': datetime.now(timezone.utc).isoformat(),
                  'engine': '2026.9', 'dry_run': True, 'leverage': 1, 'summary': summary,
                  'settings': {'pairs': cfg['exchange']['pair_whitelist'], 'timeframe': cfg['timeframe'],
                               'wallet': cfg['dry_run_wallet'], 'stake': cfg['stake_amount'],
                               'max_open_trades': cfg['max_open_trades'], 'fee': cfg.get('fee')},
                  'source_hashes': {p.relative_to(folder).as_posix(): digest(p) for p in stratdir.rglob('*') if p.is_file()},
                  'config_sha256': digest(folder / 'config.json'), 'warnings': warnings}
        if run.get('preset'):record['preset']=run['preset']
        if frozen.get('optimization'):
            record['optimization'] = frozen['optimization']
            if frozen['optimization'].get('mode') == 'train':
                warnings.append('Báo cáo nguồn chỉ chạy lại tập học của phiên tối ưu, chưa phải kiểm định ngoài mẫu.')
        write_check(folder / 'record.json', record)
        return record


def verify_profile(uid, config):
    p = profile_path(uid, config)
    record = json.loads((p / 'record.json').read_text(encoding='utf-8'))
    if not (p / 'config.json').is_file() or digest(p / 'config.json') != record['config_sha256']:
        raise HTTPException(409, 'Cấu hình hồ sơ đã đổi. Chuẩn bị hồ sơ mới thay vì sửa bản đang lưu.')
    cfg = json.loads((p / 'config.json').read_text(encoding='utf-8'))
    validate_recipe(cfg)
    for name, expected in record['source_hashes'].items():
        path = p / name
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(p.resolve()) or digest(path) != expected:
            raise HTTPException(409, 'Mã của hồ sơ paper đã thay đổi.')
    return cfg, record


def native(method, path, config):
    auth = api_config(config)
    try:
        response = requests.request(method, WORKER_URL + path,
                                    auth=(auth['username'], auth['password']), timeout=8)
        if response.status_code >= 400:
            raise HTTPException(503, 'Paper API chưa sẵn sàng: HTTP ' + str(response.status_code))
        return response.json()
    except requests.RequestException:
        raise HTTPException(503, 'Chưa kết nối được dịch vụ paper nghiên cứu (8095).')


def checked_native(config):
    current = native('GET', '/show_config', config)
    if current.get('dry_run') is not True or current.get('trading_mode') != 'futures' or current.get('margin_mode') != 'isolated' or not current.get('strategy', '').startswith('FPPaper'):
        raise HTTPException(409, 'Dịch vụ đích không phải worker paper FreqPilot đã cấu hình.')
    return current


@router.get('/paper')
def paper_status(config=Depends(get_config)):
    with paper_lock:
        return _paper_status(config)


def _paper_status(config):
    root = paper_root(config)
    profiles = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((root / 'profiles').glob('*/record.json'), key=lambda p: p.stat().st_mtime, reverse=True)]
    for profile in profiles:
        try:
            verify_profile(profile['id'], config)
            profile['valid'] = True
        except (HTTPException, OSError) as error:
            profile.update(valid=False, error=str(getattr(error, 'detail', error)))
        try:
            profile.update(profile_visibility(profile['id'], config))
        except HTTPException as error:
            profile.update(valid=False, archived=False, archived_at=None, error=error.detail)
    try:
        current = checked_native(config)
        positions = native('GET', '/status', config)
        active = next((r for r in profiles if r['wrapper'] == current['strategy']), None)
        result = {'online': True, 'state': current['state'], 'active_profile': active['id'] if active else None,
                'native_strategy': current['strategy'], 'open_trades': len(positions), 'profiles': profiles,
                'dry_run': True, 'url_port': 8095}
    except HTTPException as error:
        current = None
        result = {'online': False, 'error': error.detail, 'state': 'unavailable', 'profiles': profiles,
                'open_trades': None, 'active_profile': None, 'url_port': 8095}
    try:
        paper_history.observe(config, result, current)
    except HTTPException as error:
        result['history_error'] = error.detail
    return result


@router.post('/paper/profiles/{uid}/archive')
def archive_profile(uid: str, config=Depends(get_config)):
    with paper_lock:
        _, record = verify_profile(uid, config)
        current = checked_native(config)
        if current['strategy'] == record['wrapper']:
            raise HTTPException(409, 'Hồ sơ đang được worker chọn. Hãy chọn hồ sơ khác trước khi lưu trữ.')
        return set_profile_visibility(uid, config, True)


@router.post('/paper/profiles/{uid}/restore')
def restore_profile(uid: str, config=Depends(get_config)):
    with paper_lock:
        return set_profile_visibility(uid, config, False)


@router.get('/paper/history')
def paper_timeline(profile_id: str | None = None, strategy: str | None = None,
                   before: int | None = None, limit: int = 30, config=Depends(get_config)):
    return paper_history.history(config, profile_id, strategy, before, limit)


def reload_stopped(cfg, config):
    # A new bot_name is observable from the new FreqtradeBot config only. This is
    # a native lifecycle barrier, rather than trusting an immediate /stop response.
    cfg = deepcopy(cfg)
    cfg['initial_state'] = 'stopped'
    cfg['bot_name'] = cfg['bot_name'].rsplit(' #',1)[0] + ' #' + uuid4().hex[:8]
    validate_recipe(cfg)
    write_check(paper_root(config) / 'active/config.json', cfg)
    native('POST', '/reload_config', config)
    deadline = time.monotonic() + 55
    while time.monotonic() < deadline:
        try:
            actual = checked_native(config)
            if actual['bot_name'] == cfg['bot_name'] and actual['strategy'] == cfg['strategy'] and actual['state'] == 'stopped':
                return actual
        except HTTPException:
            pass
        time.sleep(.5)
    raise HTTPException(503, 'Worker đang nạp cấu hình hoặc gặp lỗi. Xem log dịch vụ; không tự gửi lại lệnh bật.')


@router.post('/paper/profiles/{uid}/start')
@paper_history.audited('start')
def start_paper(uid: str, config=Depends(get_config)):
    with paper_lock:
        cfg, record = verify_profile(uid, config)
        if profile_visibility(uid, config)['archived']:
            raise HTTPException(409, 'Hãy hiện lại hồ sơ đã lưu trữ trước khi bật paper.')
        current = checked_native(config)
        if current['strategy'] != record['wrapper']:
            if native('GET', '/status', config):
                raise HTTPException(409, 'Còn vị thế paper đang mở. Tạm dừng vào lệnh và chờ thoát trước khi đổi hồ sơ.')
            # Reload the OLD recipe, with its OLD database, into STOPPED first.
            old = json.loads((paper_root(config) / 'active/config.json').read_text(encoding='utf-8'))
            reload_stopped(old, config)
            if native('GET', '/status', config):
                native('POST', '/pause', config)
                raise HTTPException(409, 'Có vị thế phát sinh trước khi dừng. Đã giữ hồ sơ cũ ở chế độ chỉ quản lý thoát lệnh.')
            reload_stopped(cfg, config)
        native('POST', '/start', config)
        return paper_status(config)


@router.post('/paper/pause')
@paper_history.audited('pause')
def pause_paper(config=Depends(get_config)):
    with paper_lock:
        checked_native(config)
        native('POST', '/pause', config)
        return paper_status(config)


@router.post('/paper/stop')
@paper_history.audited('stop')
def stop_paper(config=Depends(get_config)):
    with paper_lock:
        checked_native(config)
        if native('GET', '/status', config):
            raise HTTPException(409, 'Còn vị thế mở. Dùng tạm dừng vào lệnh để tiếp tục quản lý thoát lệnh.')
        cfg = json.loads((paper_root(config) / 'active/config.json').read_text(encoding='utf-8'))
        reload_stopped(cfg, config)
        if native('GET', '/status', config):
            native('POST', '/pause', config)
            raise HTTPException(409, 'Vị thế vừa phát sinh; đã chuyển sang chỉ quản lý thoát lệnh.')
        return paper_status(config)


@router.post('/paper/connection')
def paper_connection(config=Depends(get_config)):
    current = checked_native(config)
    auth = native('POST', '/token/login', config)
    return {'botName': current['bot_name'].rsplit(' #',1)[0], 'apiPort': 8095,
            'accessToken': auth['access_token'], 'refreshToken': auth['refresh_token'], 'autoRefresh': True}


if __name__ == '__main__':
    config = json.loads(Path('/freqtrade/user_data/config.json').read_text(encoding='utf-8-sig'))
    config['user_data_dir'] = Path('/freqtrade/user_data')
    bootstrap(config)
