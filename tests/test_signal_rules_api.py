from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app


def test_signal_rules_crud(db_session) -> None:
    def _get_db_override():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    client = TestClient(app)

    create_payload = {
        "slug": "test-rule",
        "name": "Test Rule",
        "signal_type": "strong_period_change",
        "params_json": {"mom_threshold_pct": 7},
        "weight": "1.1",
        "enabled": True,
        "description": "rule for tests",
    }
    create_resp = client.post("/signal-rules?actor=tester", json=create_payload)
    assert create_resp.status_code == 200
    rule_id = create_resp.json()["id"]

    list_resp = client.get("/signal-rules")
    assert list_resp.status_code == 200
    assert any(item["id"] == rule_id for item in list_resp.json())

    update_payload = {**create_payload, "name": "Updated Rule", "params_json": {"mom_threshold_pct": 9}}
    update_resp = client.put(f"/signal-rules/{rule_id}?actor=tester", json=update_payload)
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Updated Rule"

    revisions_resp = client.get(f"/signal-rules/{rule_id}/revisions")
    assert revisions_resp.status_code == 200
    revisions = revisions_resp.json()
    assert len(revisions) >= 3

    latest_revision = revisions[0]["id"]
    earliest_revision = revisions[-1]["id"]
    diff_resp = client.get(
        f"/signal-rules/{rule_id}/revisions/{earliest_revision}/diff/{latest_revision}"
    )
    assert diff_resp.status_code == 200
    diff_payload = diff_resp.json()
    assert "changed_fields" in diff_payload
    assert "params_diff" in diff_payload

    timeline_resp = client.get(f"/signal-rules/{rule_id}/timeline")
    assert timeline_resp.status_code == 200
    timeline_payload = timeline_resp.json()
    assert timeline_payload["rule_id"] == rule_id
    assert timeline_payload["total_revisions"] >= 3
    assert isinstance(timeline_payload["timeline"], list)

    timeline_critical_resp = client.get(f"/signal-rules/{rule_id}/timeline?critical_only=true")
    assert timeline_critical_resp.status_code == 200
    critical_timeline = timeline_critical_resp.json()["timeline"]
    assert isinstance(critical_timeline, list)

    impact_preview_resp = client.post(
        f"/signal-rules/{rule_id}/impact-preview?limit_series=50&actor=tester",
        json={"override_params": {"mom_threshold_pct": 12}},
    )
    assert impact_preview_resp.status_code == 200
    impact_payload = impact_preview_resp.json()
    assert impact_payload["rule_id"] == rule_id
    assert "baseline" in impact_payload
    assert "simulated" in impact_payload
    assert "delta" in impact_payload
    assert impact_payload["preview_id"] is not None

    list_previews_resp = client.get(f"/signal-rules/{rule_id}/impact-previews")
    assert list_previews_resp.status_code == 200
    previews = list_previews_resp.json()
    assert len(previews) >= 1

    preview_id = impact_payload["preview_id"]
    get_preview_resp = client.get(f"/signal-rule-impact-previews/{preview_id}")
    assert get_preview_resp.status_code == 200
    assert get_preview_resp.json()["id"] == preview_id

    evaluate_resp = client.post(f"/signal-rule-impact-previews/{preview_id}/evaluate?actor=tester")
    assert evaluate_resp.status_code == 200
    evaluation_payload = evaluate_resp.json()
    assert evaluation_payload["preview_id"] == preview_id
    assert "metrics_json" in evaluation_payload
    assert evaluation_payload["metrics_json"]["evaluation_mode"] == "simulated_vs_simulated_with_same_overrides"

    list_eval_resp = client.get(f"/signal-rule-impact-previews/{preview_id}/evaluations")
    assert list_eval_resp.status_code == 200
    evaluations = list_eval_resp.json()
    assert len(evaluations) >= 1

    evaluation_id = evaluation_payload["id"]
    get_eval_resp = client.get(f"/signal-rule-impact-evaluations/{evaluation_id}")
    assert get_eval_resp.status_code == 200
    assert get_eval_resp.json()["id"] == evaluation_id

    leaderboard_resp = client.get("/signal-rules/impact-accuracy-leaderboard?limit=10")
    assert leaderboard_resp.status_code == 200
    leaderboard_items = leaderboard_resp.json()["items"]
    assert isinstance(leaderboard_items, list)
    assert any(item["rule_id"] == rule_id for item in leaderboard_items)

    trend_resp = client.get(f"/signal-rules/{rule_id}/impact-accuracy-trend?window_size=3&limit=20")
    assert trend_resp.status_code == 200
    trend_payload = trend_resp.json()
    assert trend_payload["rule_id"] == rule_id
    assert isinstance(trend_payload["points"], list)

    alerts_resp = client.get("/signal-rules/impact-accuracy-alerts?min_evaluations=1&error_threshold=0.1")
    assert alerts_resp.status_code == 200
    alerts_items = alerts_resp.json()["items"]
    assert isinstance(alerts_items, list)

    full_dashboard_resp = client.get("/editorial/dashboard/full?recent_limit=5")
    assert full_dashboard_resp.status_code == 200
    full_payload = full_dashboard_resp.json()
    assert "overview" in full_payload
    assert "accuracy_leaderboard" in full_payload
    assert "rule_alerts" in full_payload

    first_create_rev = revisions[-1]["id"]
    rollback_resp = client.post(f"/signal-rules/{rule_id}/rollback/{first_create_rev}?actor=tester")
    assert rollback_resp.status_code == 200
    assert rollback_resp.json()["params_json"]["mom_threshold_pct"] == 7

    delete_resp = client.delete(f"/signal-rules/{rule_id}?actor=tester")
    assert delete_resp.status_code == 200
    app.dependency_overrides.clear()
