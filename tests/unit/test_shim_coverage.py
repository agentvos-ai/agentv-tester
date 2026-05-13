import pytest
from core.errors import ShimError
from shims.registry import ShimRegistry


@pytest.fixture
def registry():
    reg = ShimRegistry(
        enabled_shims=["git", "database", "filesystem", "rest_api", "hitl"]
    )
    yield reg
    reg.shutdown_all()


def test_git_coverage():
    from shims.s01_git import GitShim

    shim = GitShim()
    shim.setup()
    shim.reset()
    assert shim.name == "git"
    assert shim.description

    # Test real git operations
    shim.clone("main")
    tx_files = {"test.py": "print('hello')"}
    msg = shim.commit("main", tx_files, "feat: add test")
    assert "Committed as" in msg

    shim.push("main", "main")
    pr_id = shim.create_pr("main", "dev", "main", "New PR")
    assert pr_id == "PR-1"

    # Test diff
    r = shim.list_branches("main")
    assert "main" in r
    assert "dev" in r

    shim.get_tool_specs()
    with pytest.raises(ShimError):
        shim.clone("bad")
    with pytest.raises(ShimError):
        shim.commit("bad", {}, "m")
    with pytest.raises(ShimError):
        shim.list_branches("bad")

    shim.shutdown()


def test_rest_api_coverage():
    from shims.s02_rest_api import RestApiShim

    shim = RestApiShim()
    shim.reset()
    assert shim.name == "rest_api"

    # 1. GET existing (static)
    res = shim.get("/v1/credit_score")
    assert res["status"] == 200
    assert res["body"]["score"] == 750

    # 2. POST (Dynamic)
    res = shim.post("/v1/transactions", {"amount": 500.0})
    assert res["status"] == 201
    tx_id = res["body"]["id"]

    # 3. GET (Dynamic with path param)
    res = shim.get(f"/v1/transactions/{tx_id}")
    assert res["status"] == 200
    assert res["body"]["amount"] == 500.0

    # 4. 404
    res = shim.get("/v1/missing")
    assert res["status"] == 404

    shim.get_tool_specs()


def test_database_coverage():
    from shims.s03_database import DatabaseShim

    shim = DatabaseShim()
    shim.reset()
    assert shim.name == "database"

    # Test real SQLite queries
    shim.query("SELECT * FROM accounts")
    shim.insert("accounts", {"id": 10, "name": "new", "balance": 0.0})
    shim.update("accounts", {"balance": 100.0}, "id = 10")

    # Test dynamic introspection
    schema = shim.schema_describe()
    assert "accounts" in schema
    assert "id (INTEGER)" in schema["accounts"] or "id (INT)" in schema["accounts"]

    shim.get_tool_specs()
    shim.shutdown()


def test_filesystem_coverage():
    from shims.s11_filesystem import FilesystemShim

    shim = FilesystemShim()
    shim.reset()
    assert shim.name == "filesystem"

    shim.write_file("test.txt", "content")
    assert shim.read_file("test.txt") == "content"

    files = shim.list_files(".")
    assert "test.txt" in files

    shim.delete_file("test.txt")
    with pytest.raises(ShimError):
        shim.read_file("test.txt")

    shim.get_tool_specs()
    shim.shutdown()


def test_hitl_coverage():
    from shims.s20_hitl import HitlShim

    shim = HitlShim()
    shim.reset()
    assert shim.name == "hitl"

    rid = shim.request_human_review("Urgent task", {"priority": "high"})
    res = shim.get_review_status(rid)
    assert res["status"] == "PENDING"

    # It should stay PENDING until advanced
    for _ in range(5):
        assert shim.get_review_status(rid)["status"] == "PENDING"

    shim.submit_human_decision(rid, "Approved")
    res = shim.get_review_status(rid)
    assert res["status"] == "APPROVED"

    shim.get_tool_specs()
    with pytest.raises(ShimError):
        shim.get_review_status("missing")


def test_knowledge_base_coverage():
    from shims.s04_knowledge_base import KnowledgeBaseShim

    shim = KnowledgeBaseShim()
    shim.reset()
    assert shim.name == "knowledge_base"

    # Search
    results = shim.search("fraud")
    assert "fraud_policy_v1" in results

    # Fetch
    content = shim.fetch_doc("fraud_policy_v1")
    assert "transactions above $10,000" in content

    # Topics
    topics = shim.list_topics()
    assert "Compliance" in topics

    shim.shutdown()


def test_support_desk_coverage():
    from shims.s05_support_desk import SupportDeskShim

    shim = SupportDeskShim()
    shim.reset()
    assert shim.name == "support_desk"

    tid = shim.create_ticket("Test Ticket", "Test Description")
    assert tid.startswith("TKT-")

    msg = shim.update_ticket(tid, "Added a comment")
    assert "Comment added" in msg

    tickets = shim.list_open_tickets()
    assert any(t["id"] == tid for t in tickets)

    shim.resolve_ticket(tid, "Fixed it")
    tickets = shim.list_open_tickets()
    assert not any(t["id"] == tid for t in tickets)

    shim.shutdown()


def test_iot_coverage():
    from shims.s09_iot import IotShim

    shim = IotShim()
    shim.reset()
    assert shim.name == "iot"

    devices = shim.list_devices()
    assert len(devices) >= 2

    res = shim.read_sensor("sensor-01")
    assert res["reading"] > 0

    msg = shim.send_command("actuator-01", "TURN ON")
    assert "ON" in msg

    shim.shutdown()


def test_security_coverage():
    from shims.s10_security import SecurityShim

    shim = SecurityShim()
    shim.reset()
    assert shim.name == "security"

    token = shim.authenticate("admin", "secret")
    assert len(token) == 16

    assert shim.check_permission(token, "vault", "write") is True

    token2 = shim.authenticate("user", "pass")
    assert shim.check_permission(token2, "vault", "write") is False

    msg = shim.rotate_secret("api_key")
    assert "rotated successfully" in msg

    logs = shim.get_audit_log()
    assert len(logs) > 0

    shim.shutdown()


def test_email_coverage():
    from shims.s12_email import EmailShim

    shim = EmailShim()
    shim.reset()
    assert shim.name == "email"

    msg = shim.send_email("test@corp.com", "agent@enterprise.com", "Hi", "Hello world")
    assert "sent" in msg

    inbox = shim.list_inbox("agent@enterprise.com")
    assert len(inbox) >= 2  # 1 seeded + 1 sent

    # Find the 'Hi' message
    msg = next(m for m in inbox if m["subject"] == "Hi")
    msg_id = msg["id"]
    content = shim.read_email(msg_id)
    assert content["subject"] == "Hi"
    assert content["body"] == "Hello world"

    shim.shutdown()


def test_calendar_coverage():
    from shims.s13_calendar import CalendarShim

    shim = CalendarShim()
    shim.reset()
    assert shim.name == "calendar"

    msg = shim.create_event("Meeting", "2025-07-01 12:00", "2025-07-01 13:00", "Lobby")
    assert "scheduled" in msg

    events = shim.list_events("2025-07-01")
    assert len(events) == 1

    eid = events[0]["id"]
    msg = shim.delete_event(eid)
    assert "cancelled" in msg

    shim.shutdown()


def test_payment_coverage():
    from shims.s14_payment import PaymentShim

    shim = PaymentShim()
    shim.reset()
    assert shim.name == "payment"

    bal_before = shim.get_balance("CUSTOMER-001")
    msg = shim.process_payment("SYSTEM", "CUSTOMER-001", 100.0, "Bonus")
    assert "successful" in msg

    bal_after = shim.get_balance("CUSTOMER-001")
    assert bal_after == bal_before + 100.0

    history = shim.list_transactions("CUSTOMER-001")
    assert len(history) == 1

    shim.shutdown()


def test_compliance_coverage():
    from shims.s19_compliance import ComplianceShim

    shim = ComplianceShim()
    shim.reset()
    assert shim.name == "compliance"

    msg = shim.perform_check("RES-1", "AML", {"amount": 5000})
    assert "PASSED" in msg

    msg = shim.perform_check("RES-2", "AML", {"amount": 20000})
    assert "WARNING" in msg

    audit = shim.get_audit_trail()
    assert len(audit) == 2

    shim.shutdown()


def test_workflow_coverage():
    from shims.s18_workflow import WorkflowShim

    shim = WorkflowShim()
    shim.reset()
    assert shim.name == "workflow"

    wid = shim.start_workflow("TEST", {"step": 1})
    assert wid.startswith("WF-")

    msg = shim.update_workflow(wid, {"step": 2}, "ADVANCE")
    assert "updated" in msg

    status = shim.get_workflow_status(wid)
    assert status["state"]["step"] == 2
    assert len(status["history"]) == 2

    shim.shutdown()


def test_vector_db_coverage():
    from shims.s07_vector_db import VectorDbShim

    shim = VectorDbShim()
    shim.reset()
    assert shim.name == "vector_db"

    # Upsert
    shim.upsert("test_coll", [1.0, 0.0, 0.0], {"name": "x-axis"})
    shim.upsert("test_coll", [0.0, 1.0, 0.0], {"name": "y-axis"})

    # Query
    results = shim.query_similar("test_coll", [0.9, 0.1, 0.0], limit=1)
    assert len(results) == 1
    assert results[0]["metadata"]["name"] == "x-axis"
    assert results[0]["score"] > 0.9

    shim.shutdown()


def test_search_coverage():
    from shims.s16_search import SearchShim
    from shims.s04_knowledge_base import KnowledgeBaseShim

    # Setup KB first so search can find it
    kb = KnowledgeBaseShim()
    kb.reset()

    shim = SearchShim()
    shim.reset()
    assert shim.name == "search"

    # Web search
    web_res = shim.web_search("AML")
    assert len(web_res) > 0
    assert "AML" in web_res[0]["title"]

    # Internal search
    int_res = shim.internal_search("fraud")
    assert len(int_res) > 0
    assert "Fraud" in int_res[0]["title"]

    shim.shutdown()
    kb.shutdown()
