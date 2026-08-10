from unittest.mock import MagicMock, PropertyMock, patch

import verticals  # noqa: F401
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
        "construction": [
            "epc_subcontractor_vetting_agent",
        ],
    }

    mock_config = MagicMock()
    mock_framework = MagicMock()
    # Mock shims to have get_tool_specs
    all_shim_names = [
        "database",
        "analytics",
        "compliance",
        "notification",
        "insurance",
        "bonding",
        "sanctions",
        "notice_to_proceed",
        "ehr",
        "clinical_decision",
        "billing",
        "scheduling",
        "crm",
        "oss_bss",
        "inventory",
        "support_desk",
        "rest_api",
        "git",
        "vector_db",
        "knowledge_base",
        "workflow",
        "hitl",
        "email",
        "filesystem",
        "social_media",
        "iot",
        "cicd",
        "calendar",
        "payment",
        "search",
    ]
    mock_shims = {name: MagicMock() for name in all_shim_names}
    for s in mock_shims.values():
        s.get_tool_specs.return_value = [("tool", lambda x: x, "desc")]

    for agents in verticals.values():
        for agent_name in agents:
            agent_cls = get_agent_class(agent_name)
            agent = agent_cls(mock_config, mock_framework, mock_shims)

            # Exercise system_prompt
            assert agent.system_prompt is not None

            # Exercise get_tool_specs
            tools = agent.get_tool_specs()
            assert len(tools) > 0

            # Exercise execute (mock runnable)
            # Mock schema property to bypass validation in coverage test
            with patch.object(
                agent_cls, "input_schema", new_callable=PropertyMock
            ) as mock_schema:
                mock_schema.return_value = MagicMock()

                agent._runnable = MagicMock()
                agent._runnable.run.return_value = {"output": "ok", "tool_calls": []}
                res = agent.execute(
                    {
                        "input_data": {
                            "transaction_id": "T1",
                            "account_id": "A1",
                            "amount": 10.0,
                            "patient_id": "P1",
                            "symptoms": ["none"],
                            "node_id": "N1",
                            "fault_type": "none",
                        },
                        "task_id": "1",
                    }
                )
                assert res["status"] == "success"
