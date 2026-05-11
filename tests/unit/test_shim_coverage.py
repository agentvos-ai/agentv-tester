import pytest
from core.errors import ShimError
from shims.registry import ShimRegistry

@pytest.fixture
def registry():
    reg = ShimRegistry()
    yield reg
    reg.shutdown_all()

def test_git_coverage():
    from shims.s01_git import GitShim
    shim = GitShim()
    shim.reset()
    assert shim.name == "git"
    assert shim.description
    shim.clone("https://main.git")
    shim.commit("main", {"f.txt": "c"}, "msg")
    shim.push("main", "dev")
    shim.create_pr("main", "dev", "main", "PR")
    shim.get_diff("main", "v1", "v2")
    shim.list_branches("main")
    shim.get_tool_specs()
    with pytest.raises(ShimError): shim.clone("bad")
    with pytest.raises(ShimError): shim.commit("bad", {}, "m")
    with pytest.raises(ShimError): shim.create_pr("bad", "s", "t", "T")
    with pytest.raises(ShimError): shim.list_branches("bad")

def test_rest_api_coverage():
    from shims.s02_rest_api import RestApiShim
    shim = RestApiShim()
    shim.reset()
    assert shim.name == "rest_api"
    assert shim.description
    shim.get("/v1/credit_score")
    # Hit branch 51
    shim.post("/v1/transactions", {"name": "test"})
    shim.put("/v1/transactions", {"name": "test2"})
    shim.delete("/v1/transactions")
    shim.patch("/v1/transactions", {"x": 1})
    shim.get("/v1/missing")
    shim.get_tool_specs()

def test_database_coverage():
    from shims.s03_database import DatabaseShim
    shim = DatabaseShim()
    shim.reset()
    assert shim.name == "database"
    assert shim.description
    shim.query("SELECT * FROM accounts")
    shim.insert("accounts", {"id": 10, "name": "new", "balance": 0.0})
    shim.update("accounts", {"balance": 100.0}, "id = 10")
    shim.delete("accounts", "id = 10")
    shim.schema_describe()
    shim.get_tool_specs()
    shim.shutdown()
    shim = DatabaseShim()
    shim.reset()
    with pytest.raises(ShimError): shim.query("INVALID SQL")
    with pytest.raises(ShimError): shim.insert("missing", {"x": 1})
    with pytest.raises(ShimError): shim.update("missing", {"x": 1}, "y=1")
    with pytest.raises(ShimError): shim.delete("missing", "y=1")
    shim.shutdown()

def test_knowledge_base_coverage():
    from shims.s04_knowledge_base import KnowledgeBaseShim
    shim = KnowledgeBaseShim()
    shim.reset()
    assert shim.name == "knowledge_base"
    assert shim.description
    shim.search("compliance")
    # Hit branch 44-47 by searching for content
    shim.search("Manual Review")
    shim.fetch_doc("fraud_policy_v1")
    shim.list_topics()
    shim.get_tool_specs()
    with pytest.raises(ShimError): shim.fetch_doc("missing")

def test_support_desk_coverage():
    from shims.s05_support_desk import SupportDeskShim
    shim = SupportDeskShim()
    shim.reset()
    assert shim.name == "support_desk"
    assert shim.description
    shim.list_open_tickets()
    tid = shim.create_ticket("Title", "Desc")
    shim.update_ticket(tid, "Comment")
    shim.resolve_ticket(tid, "Done")
    shim.get_tool_specs()
    with pytest.raises(ShimError): shim.update_ticket("missing", "x")
    with pytest.raises(ShimError): shim.resolve_ticket("missing", "x")

def test_social_media_coverage():
    from shims.s06_social_media import SocialMediaShim
    shim = SocialMediaShim()
    shim.reset()
    assert shim.name == "social_media"
    assert shim.description
    shim.post("content")
    shim.fetch_feed()
    shim.send_dm("user1", "msg")
    shim.get_mentions()
    shim.get_tool_specs()

def test_vector_db_coverage():
    from shims.s07_vector_db import VectorDbShim
    shim = VectorDbShim()
    shim.reset()
    assert shim.name == "vector_db"
    assert shim.description
    shim.upsert("policies", [0.1, 0.2], {"id": "1"})
    # Hit branch 36-37
    shim.upsert("new_coll", [0.0, 0.0], {"id": "2"})
    shim.query_similar("policies", [0.1, 0.2])
    # Hit branch 61 (norm=0)
    shim.query_similar("policies", [0.0, 0.0])
    # Hit branch 52-53 (empty collection)
    shim.reset()
    assert shim.query_similar("policies", [0.1, 0.2]) == []
    shim.get_tool_specs()
    with pytest.raises(ShimError): shim.query_similar("missing", [0.1])
    with pytest.raises(ShimError): shim.delete_vector("missing", {})

def test_cicd_coverage():
    from shims.s08_cicd import CicdShim
    shim = CicdShim()
    shim.reset()
    assert shim.name == "cicd"
    assert shim.description
    shim.trigger_pipeline("deploy-prod")
    shim.get_status("deploy-prod")
    shim.get_logs("deploy-prod")
    shim.cancel_pipeline("deploy-prod")
    shim.get_tool_specs()
    with pytest.raises(ShimError): shim.trigger_pipeline("missing")
    with pytest.raises(ShimError): shim.get_status("missing")
    with pytest.raises(ShimError): shim.get_logs("missing")
    with pytest.raises(ShimError): shim.cancel_pipeline("missing")

def test_iot_coverage():
    from shims.s09_iot import IotShim
    shim = IotShim()
    shim.reset()
    assert shim.name == "iot"
    assert shim.description
    shim.read_sensor("sensor-01")
    shim.send_command("actuator-01", "ON")
    shim.list_devices()
    shim.subscribe_alert("sensor-01", 30.0)
    shim.get_tool_specs()
    with pytest.raises(ShimError): shim.read_sensor("missing")
    with pytest.raises(ShimError): shim.send_command("missing", "CMD")

def test_security_coverage():
    from shims.s10_security import SecurityShim
    shim = SecurityShim()
    shim.reset()
    assert shim.name == "security"
    assert shim.description
    shim.authenticate("user", "secure_token")
    shim.check_permission("agent-001", "read")
    shim.rotate_secret("db_password")
    shim.get_audit_log()
    shim.get_tool_specs()
    with pytest.raises(ShimError): shim.rotate_secret("")
    with pytest.raises(ShimError): shim.rotate_secret("missing")

def test_filesystem_coverage():
    from shims.s11_filesystem import FilesystemShim
    shim = FilesystemShim()
    shim.reset()
    assert shim.name == "filesystem"
    assert shim.description
    shim.write_file("f.txt", "c")
    shim.read_file("f.txt")
    shim.list_dir(".")
    shim.move("f.txt", "f2.txt")
    # Hit dir deletion (Branch 84)
    shim.write_file("dir/f.txt", "c")
    shim.delete("dir")
    shim.delete("f2.txt")
    shim.get_tool_specs()
    # Hit reset branch 36-37 (exists)
    shim.reset()
    # Hit reset branch (not exists) - by manual delete
    import shutil
    if shim.base_path.exists():
        shutil.rmtree(shim.base_path)
    shim.reset()
    with pytest.raises(ShimError): shim.read_file("missing")
    with pytest.raises(ShimError): shim.move("missing", "x")
    with pytest.raises(ShimError): shim.delete("missing")
    with pytest.raises(ShimError): shim.write_file("../traversal.txt", "c")

def test_email_coverage():
    from shims.s12_email import EmailShim
    shim = EmailShim()
    shim.reset()
    assert shim.name == "email"
    assert shim.description
    shim.send_email("to@test.com", "Sub", "Body")
    shim.list_inbox()
    shim.read_email("msg_1")
    shim.search_emails("Report")
    shim.get_tool_specs()
    with pytest.raises(ShimError): shim.read_email("missing")

def test_calendar_coverage():
    from shims.s13_calendar import CalendarShim
    shim = CalendarShim()
    shim.reset()
    assert shim.name == "calendar"
    assert shim.description
    shim.create_event("Meeting", "2026-05-12T10:00:00", "2026-05-12T11:00:00")
    shim.list_events("2026-05-12")
    shim.find_free_slot("2026-05-12", 30)
    shim.cancel_event("ev_1")
    shim.get_tool_specs()
    with pytest.raises(ShimError): shim.cancel_event("missing")

def test_payment_coverage():
    from shims.s14_payment import PaymentShim
    shim = PaymentShim()
    shim.reset()
    assert shim.name == "payment"
    assert shim.description
    shim.charge(100.0, "USD", "service")
    shim.refund("tx_1001")
    shim.create_subscription("plan1", "cust1")
    shim.get_ledger()
    shim.get_tool_specs()
    with pytest.raises(ShimError): shim.refund("missing")

def test_notification_coverage():
    from shims.s15_notification import NotificationShim
    shim = NotificationShim()
    shim.reset()
    assert shim.name == "notification"
    assert shim.description
    shim.send_sms("123", "msg")
    shim.send_push("user1", "msg")
    shim.send_webhook("https://hook.com", {"x": 1})
    shim.list_sent()
    shim.get_tool_specs()

def test_search_coverage():
    from shims.s16_search import SearchShim
    shim = SearchShim()
    shim.reset()
    assert shim.name == "search"
    assert shim.description
    shim.web_search("Market")
    shim.enterprise_search("Policy")
    shim.news_search("Tech")
    shim.get_tool_specs()

def test_analytics_coverage():
    from shims.s17_analytics import AnalyticsShim
    shim = AnalyticsShim()
    shim.reset()
    assert shim.name == "analytics"
    assert shim.description
    shim.query_metrics("churn_rate")
    shim.create_report("Churn Analysis", ["churn_rate"])
    shim.get_kpi("avg_nps")
    shim.get_kpi("missing")
    shim.forecast("churn_rate", 3)
    shim.get_tool_specs()
    with pytest.raises(ShimError): shim.query_metrics("missing")

def test_workflow_coverage():
    from shims.s18_workflow import WorkflowShim
    shim = WorkflowShim()
    shim.reset()
    assert shim.name == "workflow"
    assert shim.description
    wid = shim.start_workflow("Process", {"data": 1})
    shim.get_workflow_status(wid)
    shim.complete_task(wid, "task1")
    shim.complete_task(wid, "END")
    shim.escalate(wid, "delay")
    shim.get_tool_specs()
    with pytest.raises(ShimError): shim.get_workflow_status("missing")
    with pytest.raises(ShimError): shim.complete_task("missing", "x")
    with pytest.raises(ShimError): shim.escalate("missing", "x")

def test_compliance_coverage():
    from shims.s19_compliance import ComplianceShim
    shim = ComplianceShim()
    shim.reset()
    assert shim.name == "compliance"
    assert shim.description
    shim.check_policy("transaction", {"amount": 60000})
    shim.check_policy("transaction", {"amount": 1000})
    shim.file_report("SAR", {"id": 1})
    shim.get_audit_trail()
    shim.flag_violation("user1", "suspicious")
    shim.get_tool_specs()

def test_hitl_coverage():
    from shims.s20_hitl import HitlShim
    shim = HitlShim()
    shim.reset()
    assert shim.name == "hitl"
    assert shim.description
    rid = shim.request_human_review("Check", {"data": 1})
    # Hit the check_count >= 3 branch
    shim.get_review_status(rid)
    shim.get_review_status(rid)
    shim.get_review_status(rid)
    shim.submit_human_decision(rid, "COMPLETED")
    shim.get_tool_specs()
    with pytest.raises(ShimError): shim.get_review_status("missing")
    with pytest.raises(ShimError): shim.submit_human_decision("missing", "X")
