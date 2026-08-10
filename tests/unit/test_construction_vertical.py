from unittest.mock import MagicMock

import verticals  # noqa: F401
from core.registry import get_agent_class
from mcp_servers.cloudflare_worker_mock import CloudflareWorkerIsolateMock
from shims.s21_insurance import InsuranceShim
from shims.s22_bonding import BondingShim
from shims.s23_sanctions import SanctionsShim
from shims.s24_notice_to_proceed import NoticeToProceedShim


def test_construction_shims():
    """Verify insurance, bonding, sanctions, and notice_to_proceed shims."""
    # 1. Insurance Shim
    ins = InsuranceShim()
    ins.reset()
    assert ins.name == "insurance"
    res_coi = ins.verify_coi("SUB-5012", 10000000.0)
    assert res_coi["is_valid"] is True
    assert len(ins.get_tool_specs()) == 1

    # 2. Bonding Shim
    bond = BondingShim()
    bond.reset()
    assert bond.name == "bonding"
    res_bond = bond.check_bonding("SUB-5012", 50000000.0)
    assert res_bond["cleared"] is True
    assert len(bond.get_tool_specs()) == 1

    # 3. Sanctions Shim
    sanc = SanctionsShim()
    sanc.reset()
    assert sanc.name == "sanctions"
    res_sanc = sanc.check_sanctions("SUB-5012")
    assert res_sanc["cleared"] is True
    assert len(sanc.get_tool_specs()) == 1

    # 4. Notice to Proceed Shim
    ntp = NoticeToProceedShim()
    ntp.reset()
    assert ntp.name == "notice_to_proceed"
    # Happy Path (v5)
    res_ntp_v5 = ntp.issue_ntp("SUB-5012", "v5")
    assert res_ntp_v5["status"] == "success"
    # Fault Path (v4 outdated)
    res_ntp_v4 = ntp.issue_ntp("SUB-5012", "v4")
    assert res_ntp_v4["status"] == "blocked"
    assert res_ntp_v4["action_taken"] == "temporal_violation"


def test_epc_subcontractor_vetting_agent_resolution():
    """Verify resolution and prompt configuration for EPCSubcontractorVettingAgent."""
    agent_cls = get_agent_class("epc_subcontractor_vetting_agent")
    mock_config = MagicMock()
    mock_framework = MagicMock()
    mock_shims = {
        "insurance": InsuranceShim(),
        "bonding": BondingShim(),
        "sanctions": SanctionsShim(),
        "notice_to_proceed": NoticeToProceedShim(),
    }
    agent = agent_cls(mock_config, mock_framework, mock_shims)
    assert "EPC Industrial Construction" in agent.system_prompt
    assert "insurance" in agent.allowed_shims
    assert "bonding" in agent.allowed_shims
    assert "sanctions" in agent.allowed_shims
    assert "notice_to_proceed" in agent.allowed_shims


def test_cloudflare_worker_isolate_mock():
    """Verify Cloudflare Worker isolate mock buffer handling and timeouts."""
    mock_cf = CloudflareWorkerIsolateMock(
        telemetry_endpoint="http://localhost:5000/api/v1/compliance/telemetry"
    )
    # Buffer records
    mock_cf.record_trace_span("check_coi_coverage", 150.0, "ok")
    assert len(mock_cf.buffer) == 1

    # Buffer max size ceiling enforcement (100 spans max)
    for i in range(150):
        mock_cf.record_trace_span(f"op_{i}", 10.0, "ok")

    assert len(mock_cf.buffer) == 100

    # Offline flush handling (fails gracefully without exception)
    flushed = mock_cf.flush_background()
    assert isinstance(flushed, bool)
