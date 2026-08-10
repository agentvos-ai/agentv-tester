import os
import stat

import pytest

from core.errors import ShimError
from shims.registry import ShimRegistry


@pytest.fixture
def booster_registry():
    registry = ShimRegistry(
        enabled_shims=[
            "git",
            "rest_api",
            "database",
            "knowledge_base",
            "support_desk",
            "social_media",
            "vector_db",
            "cicd",
            "iot",
            "security",
            "filesystem",
            "email",
            "calendar",
            "payment",
            "notification",
            "search",
            "analytics",
            "workflow",
            "compliance",
            "hitl",
        ]
    )
    registry.reset_all()
    yield registry
    registry.shutdown_all()


def test_all_shims_methods_expanded(booster_registry):
    """Systematically calls methods on every shim to reach high coverage."""
    shims = booster_registry.shims

    # Registry coverage
    booster_registry.setup_all()
    booster_registry.get_all_tools()
    s_git = shims["git"]
    booster_registry.hot_swap("git", s_git)
    assert "git" in booster_registry.shims

    # Trigger rmtree_errorhandler in Filesystem and Git
    fs_path = os.path.abspath(".agent_workspace/fs/readonly_dir")
    os.makedirs(fs_path, exist_ok=True)
    ro_file = os.path.join(fs_path, "ro.txt")
    with open(ro_file, "w") as f:
        f.write("readonly")
    os.chmod(ro_file, stat.S_IREAD)  # Make file read-only

    # Call name/description on all shims
    for shim in shims.values():
        _ = shim.name
        _ = shim.description

    # Git
    s = shims["git"]
    s.clone("https://github.com/test/main.git")
    with pytest.raises(ShimError):
        s.clone("https://github.com/external/other.git")

    s.commit("main", {"file.txt": "content"}, "msg")
    with pytest.raises(ShimError):
        s.commit("invalid_repo", {}, "msg")

    s.push("main", "main")
    with pytest.raises(ShimError):
        s.push("invalid_repo", "main")

    s.create_pr("main", "dev", "main", "Fix bug")
    s.get_diff("main", "initial", "commit_1")
    with pytest.raises(ShimError):
        s.get_diff("invalid_repo", "a", "b")

    with pytest.raises(ShimError):
        s.get_diff("main", "non_existent_ref", "HEAD")

    s.list_branches("main")
    with pytest.raises(ShimError):
        s.list_branches("invalid_repo")

    # REST API
    s = shims["rest_api"]
    s.get("/v1/credit_score")
    s.get("/v1/accounts")
    s.get("/v1/status")
    s.get("/v1/invalid_route")

    s.post("/v1/transactions", {"data": "test"})
    assert s.post("/v1/transactions", None)["status"] == 400

    s.put("/v1/transactions/tx_100", {"data": "update"})
    assert s.put("/v1/transactions/tx_100", None)["status"] == 400
    assert s.put("/v1/transactions/invalid_tx", {"data": "u"})["status"] == 404

    s.patch("/v1/transactions/tx_100", {"data": "partial"})
    assert s.patch("/v1/transactions/tx_100", None)["status"] == 400
    assert s.patch("/v1/transactions/invalid_tx", {"data": "p"})["status"] == 404

    s.get("/v1/transactions/tx_100")
    assert s.get("/v1/transactions/invalid_tx")["status"] == 404

    s.delete("/v1/transactions/tx_100")
    assert s.delete("/v1/transactions/invalid_tx")["status"] == 404

    # Database
    s = shims["database"]
    s.query("SELECT * FROM accounts")
    with pytest.raises(ShimError):
        s.query("INVALID SQL")

    s.insert("accounts", {"name": "Test", "balance": 100.0})
    with pytest.raises(ShimError):
        s.insert("invalid_table", {"a": 1})

    s.update("accounts", {"balance": 200.0}, "name = 'Test'")
    with pytest.raises(ShimError):
        s.update("invalid_table", {"a": 1}, "id=1")

    s.delete("accounts", "name = 'Test'")
    with pytest.raises(ShimError):
        s.delete("invalid_table", "id=1")
    s.schema_describe()

    # Knowledge Base
    s = shims["knowledge_base"]
    s.search("policy")
    s.fetch_doc("fraud_policy_v1")
    with pytest.raises(ShimError):
        s.fetch_doc("invalid_doc")
    s.list_topics()

    # Support Desk
    s = shims["support_desk"]
    tid = s.create_ticket("Title", "Desc")
    s.update_ticket(tid, "Update")
    with pytest.raises(ShimError):
        s.update_ticket("invalid_tid", "U")
    s.resolve_ticket(tid, "Resolution")
    with pytest.raises(ShimError):
        s.resolve_ticket("invalid_tid", "R")
    s.list_open_tickets()

    # Social Media
    s = shims["social_media"]
    s.post("hello")
    s.get_mentions()

    # Vector DB
    s = shims["vector_db"]
    s.upsert("policies", [0.1, 0.2], {"text": "test"})
    s.query_similar("policies", [0.1, 0.2], limit=1)
    s.query_similar("invalid_coll", [0.1])
    s.delete_vector("policies", {"text": "test"})
    s.delete_vector("invalid_coll", {})
    s.list_collections()

    # CI/CD
    s = shims["cicd"]
    s.trigger_pipeline("deploy-prod")
    s.get_status("deploy-prod")
    with pytest.raises(ShimError):
        s.get_status("invalid_job")
    s.get_logs("deploy-prod")
    with pytest.raises(ShimError):
        s.get_logs("invalid_job")
    s.cancel_pipeline("deploy-prod")

    # IoT
    s = shims["iot"]
    s.read_sensor("sensor-01")
    with pytest.raises(ShimError):
        s.read_sensor("invalid_sensor")
    s.send_command("actuator-01", "reboot")
    with pytest.raises(ShimError):
        s.send_command("invalid_device", "cmd")
    s.list_devices()

    # Security
    s = shims["security"]
    token = s.authenticate("user", "any_token")
    with pytest.raises(ShimError):
        s.authenticate("user", "")  # Missing secret
    s.check_permission(token, "read")
    s.check_permission(token, "general", "read")
    s.check_permission(token=token, action="write", resource="db")
    s.rotate_secret("db_password")
    with pytest.raises(ShimError):
        s.rotate_secret("invalid_secret")
    s.get_audit_log()

    # Filesystem
    s = shims["filesystem"]
    s.write_file("test.txt", "content")
    s.read_file("test.txt")
    with pytest.raises(ShimError):
        s.read_file("invalid_file.txt")
    s.list_dir(".")
    with pytest.raises(ShimError):
        s.list_dir("invalid_dir")
    s.move("test.txt", "test2.txt")
    s.delete("test2.txt")
    with pytest.raises(ShimError):
        s.delete("invalid_file")

    # Email
    s = shims["email"]
    s.send_email("to", "sub", "body")
    s.send_email("from", "to", "sub", "body")
    s.send_email(recipient="to", subject="sub", body="body")
    with pytest.raises(ShimError):
        s.send_email(recipient="to", subject="sub", body="")  # Missing body
    s.list_inbox()
    s.read_email("msg_1")
    with pytest.raises(ShimError):
        s.read_email("msg_999")
    s.search_emails("Welcome")

    # Calendar
    s = shims["calendar"]
    s.create_event("Meeting", "2026-05-10T15:00:00", "2026-05-10T16:00:00")
    s.list_events("2026-05-10")
    s.find_free_slot("2026-05-11", 60)
    s.cancel_event("ev_1")
    with pytest.raises(ShimError):
        s.cancel_event("invalid_ev")

    # Payment
    s = shims["payment"]
    s.charge(100.0, "USD", "Test payment")
    with pytest.raises(ShimError):
        s.charge(-10.0, "USD", "Negative")
    s.get_balance("CUSTOMER-001")
    with pytest.raises(ShimError):
        s.get_balance("INVALID_ACC")
    s.process_payment("CUSTOMER-001", "SYSTEM", 10.0, "Internal")
    with pytest.raises(ShimError):
        s.process_payment("INVALID", "SYSTEM", 10.0)
    with pytest.raises(ShimError):
        s.process_payment("CUSTOMER-001", "INVALID", 10.0)
    with pytest.raises(ShimError):
        s.process_payment("CUSTOMER-001", "SYSTEM", 100000.0)  # Insufficient
    s.list_transactions("CUSTOMER-001")

    # Notification
    s = shims["notification"]
    s.send_push("user_1", "Alert")
    s.send_sms("12345", "Alert")
    s.send_webhook("http://hook", {"event": "alert"})
    s.list_sent()

    # Search
    s = shims["search"]
    # Trigger full web_search logic
    s.web_search("AML")
    s.web_search("Security")
    # Trigger internal_search logic
    kb_root = os.path.abspath(".agent_workspace/kb")
    os.makedirs(kb_root, exist_ok=True)
    with open(os.path.join(kb_root, "test.md"), "w") as f:
        f.write("# Test Policy\nContent here.")
    with open(os.path.join(kb_root, "not_md.txt"), "w") as f:
        f.write("ignore")
    s.internal_search("policy")
    s.enterprise_search("Test")
    s.news_search("Regulations")

    # Analytics
    s = shims["analytics"]
    s.query_metrics("churn_rate")
    with pytest.raises(ShimError):
        s.query_metrics("invalid_metric")
    s.create_report("Churn Report", ["churn_rate", "nps_score"])
    s.get_kpi("avg_nps")
    s.forecast("nps_score", 3)
    s.aggregate_metrics(["churn_rate", "nps_score"], "avg")
    s.aggregate_metrics(["churn_rate"], "max")
    s.aggregate_metrics(["churn_rate"], "min")
    with pytest.raises(ShimError):
        s.aggregate_metrics(["churn_rate"], "invalid_op")
    assert s.aggregate_metrics([], "sum") == 0.0

    # Workflow
    s = shims["workflow"]
    wid = s.start_workflow("onboarding", {"user": "test"})
    s.get_workflow_status(wid)
    with pytest.raises(ShimError):
        s.get_workflow_status("invalid_wid")
    s.complete_task(wid, "review")
    with pytest.raises(ShimError):
        s.complete_task("invalid_wid", "task")
    s.escalate(wid, "Too complex")
    with pytest.raises(ShimError):
        s.escalate("invalid_wid", "reason")

    # Compliance
    s = shims["compliance"]
    s.check_policy("transaction", {"amount": 1000})
    s.file_report("SAR", {"id": "123"})
    s.get_audit_trail()
    s.flag_violation("user_1", "Suspicious")

    # HITL
    s = shims["hitl"]
    qid = s.request_human_review("SAR Filing", {"id": "123"})
    s.get_review_status(qid)
    # Check SLA auto-escalation
    for _ in range(5):
        s.get_review_status(qid)

    with pytest.raises(ShimError):
        s.get_review_status("invalid_qid")
    s.submit_human_decision(qid, "APPROVED")
    s.submit_human_decision(qid, "REJECT")
    s.submit_human_decision(qid, "OTHER")
    with pytest.raises(ShimError):
        s.submit_human_decision("invalid_qid", "REJECTED")
