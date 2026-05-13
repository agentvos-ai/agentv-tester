from unittest.mock import MagicMock
from core.registry import get_agent_class


def test_all_vertical_agents_coverage():
    verticals = {
        "fintech": [
            "fraud_detection_agent",
            "loan_underwriting_agent",
            "portfolio_advisor_agent",
            "regulatory_reporting_agent",
        ],
        "healthcare": [
            "clinical_triage_agent",
            "medication_reconciliation_agent",
            "patient_discharge_agent",
            "prior_auth_agent",
        ],
        "telecom": [
            "churn_prevention_agent",
            "network_fault_agent",
            "provisioning_agent",
            "sla_monitoring_agent",
        ],
    }

    mock_config = MagicMock()
    mock_framework = MagicMock()
    # Mock shims to have get_tool_specs
    mock_shims = {
        name: MagicMock()
        for name in [
            "database",
            "analytics",
            "compliance",
            "notification",
            "ehr",
            "clinical_decision",
            "billing",
            "scheduling",
            "crm",
            "oss_bss",
            "inventory",
            "support_desk",
        ]
    }
    for s in mock_shims.values():
        s.get_tool_specs.return_value = [("tool", lambda x: x, "desc")]

    for vertical, agents in verticals.items():
        for agent_name in agents:
            agent_cls = get_agent_class(agent_name)
            agent = agent_cls(mock_config, mock_framework, mock_shims)

            # Exercise system_prompt
            assert agent.system_prompt is not None

            # Exercise get_tool_specs
            tools = agent.get_tool_specs()
            assert len(tools) > 0

            # Exercise execute (mock runnable)
            agent._runnable = MagicMock()
            agent._runnable.run.return_value = {"output": "ok", "tool_calls": []}
            res = agent.execute({"input": "test", "task_id": "1"})
            assert res["status"] == "success"
