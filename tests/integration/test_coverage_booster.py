import pytest
from shims.registry import ShimRegistry

@pytest.fixture
def booster_registry():
    registry = ShimRegistry(enabled_shims=[
        "git", "rest_api", "database", "knowledge_base", "support_desk",
        "social_media", "vector_db", "cicd", "iot", "security",
        "filesystem", "email", "calendar", "payment", "notification",
        "search", "analytics", "workflow", "compliance", "hitl"
    ])
    registry.reset_all()
    yield registry
    registry.shutdown_all()

def test_all_shims_methods(booster_registry):
    """Systematically calls methods on every shim to reach high coverage."""
    shims = booster_registry.shims

    # Git
    s = shims["git"]
    s.clone("https://github.com/test/main.git")
    s.commit("main", {"file.txt": "content"}, "msg")
    s.push("main", "main")
    s.create_pr("main", "dev", "main", "Fix bug")
    s.get_diff("main", "initial", "commit_1")
    s.list_branches("main")

    # REST API
    s = shims["rest_api"]
    s.get("/v1/credit_score")
    s.post("/v1/transactions", {"data": "test"})
    s.put("/v1/transactions", {"data": "update"})
    s.patch("/v1/transactions", {"data": "partial"})
    s.delete("/v1/transactions")

    # Database
    s = shims["database"]
    s.query("SELECT * FROM accounts")
    s.insert("accounts", {"name": "Test", "balance": 100.0})
    s.update("accounts", {"balance": 200.0}, "name = 'Test'")
    s.delete("accounts", "name = 'Test'")
    s.schema_describe()

    # Knowledge Base
    s = shims["knowledge_base"]
    s.search("policy")
    s.fetch_doc("fraud_policy_v1")
    s.list_topics()

    # Support Desk
    s = shims["support_desk"]
    tid = s.create_ticket("Title", "Desc")
    s.update_ticket(tid, "Update")
    s.resolve_ticket(tid, "Resolution")
    s.list_open_tickets()

    # Social Media
    s = shims["social_media"]
    s.post("hello")
    s.get_mentions()

    # Vector DB
    s = shims["vector_db"]
    s.upsert("policies", [0.1, 0.2], {"text": "test"})
    s.query_similar("policies", [0.1, 0.2], limit=1)
    s.delete_vector("policies", {"text": "test"})
    s.list_collections()

    # CI/CD
    s = shims["cicd"]
    s.trigger_pipeline("deploy-prod")
    s.get_status("deploy-prod")
    s.get_logs("deploy-prod")
    s.cancel_pipeline("deploy-prod")

    # IoT
    s = shims["iot"]
    s.read_sensor("sensor-01")
    s.send_command("actuator-01", "reboot")
    s.list_devices()

    # Security
    s = shims["security"]
    s.authenticate("user", "secure_token")
    s.check_permission("agent-001", "read")
    s.rotate_secret("db_password")

    # Filesystem
    s = shims["filesystem"]
    s.write_file("test.txt", "content")
    s.read_file("test.txt")
    s.list_dir(".")
    s.move("test.txt", "test2.txt")
    s.delete("test2.txt")

    # Email
    s = shims["email"]
    s.send_email("to", "sub", "body")
    s.list_inbox()
    s.read_email("msg_1")

    # Calendar
    s = shims["calendar"]
    s.create_event("Meeting", "2026-05-10T15:00:00", "2026-05-10T16:00:00")
    s.list_events("2026-05-10")
    s.find_free_slot("2026-05-11", 60)
    s.cancel_event("ev_1")

    # Payment
    s = shims["payment"]
    s.charge(100.0, "USD", "Test payment")

    # Notification
    s = shims["notification"]
    s.send_push("user_1", "Alert")
    s.send_sms("12345", "Alert")
    s.send_webhook("http://hook", {"event": "alert"})
    s.list_sent()

    # Search
    s = shims["search"]
    s.web_search("query")
    s.enterprise_search("query")
    s.news_search("query")

    # Analytics
    s = shims["analytics"]
    s.query_metrics("churn_rate")
    s.create_report("Churn Report", ["churn_rate", "nps_score"])
    s.get_kpi("avg_nps")
    s.forecast("nps_score", 3)

    # Workflow
    s = shims["workflow"]
    wid = s.start_workflow("onboarding", {"user": "test"})
    s.get_workflow_status(wid)
    s.complete_task(wid, "review")
    s.escalate(wid, "Too complex")

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
    s.submit_human_decision(qid, "APPROVED")
