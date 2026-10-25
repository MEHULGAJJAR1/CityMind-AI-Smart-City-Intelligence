import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
def test_health():
    r = client.get('/health')
    assert r.status_code == 200 and r.json()['status'] == 'ok'
def test_requires_auth():
    assert client.get('/api/v1/alerts').status_code == 401
def test_scenario_requires_auth():
    assert client.post('/api/v1/scenarios', json={'demand_change_pct':10,'capacity_change_pct':10}).status_code == 401
