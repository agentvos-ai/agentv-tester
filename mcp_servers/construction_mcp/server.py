import logging

from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("construction-mcp")

mcp = FastMCP("construction-mcp")


@mcp.tool()
def check_insurance_certificate(
    subcontractor_id: str, required_coverage_usd: float = 10000000.0
) -> dict:
    """Verify subcontractor Certificate of Insurance (COI) and coverage limits."""
    logger.info("Checking COI for %s", subcontractor_id)
    return {
        "subcontractor_id": subcontractor_id,
        "status": "ACTIVE",
        "coverage_usd": 15000000.0,
        "required_coverage_usd": required_coverage_usd,
        "is_valid": True,
    }


@mcp.tool()
def check_bonding_capacity(
    subcontractor_id: str, project_value_usd: float = 50000000.0
) -> dict:
    """Check surety bonding capacity limits for industrial construction projects."""
    logger.info("Checking bonding capacity for %s", subcontractor_id)
    return {
        "subcontractor_id": subcontractor_id,
        "bonding_limit_usd": 100000000.0,
        "project_value_usd": project_value_usd,
        "cleared": True,
    }


@mcp.tool()
def check_ofac_sanctions(subcontractor_id: str) -> dict:
    """Check OFAC sanctions, AML, and background compliance."""
    logger.info("Checking OFAC sanctions for %s", subcontractor_id)
    return {
        "subcontractor_id": subcontractor_id,
        "on_sanctions_list": False,
        "cleared": True,
    }


@mcp.tool()
def issue_notice_to_proceed(subcontractor_id: str, applied_statute: str = "v5") -> dict:
    """Issue formal Notice to Proceed (NTP) for vetted construction contract."""
    logger.info(
        "Issuing NTP for %s under statute %s", subcontractor_id, applied_statute
    )
    if applied_statute != "v5":
        return {
            "subcontractor_id": subcontractor_id,
            "status": "blocked",
            "action_taken": "temporal_violation",
            "message": f"NTP BLOCKED: Applied statute '{applied_statute}' is outdated. v5 required.",
        }
    return {
        "subcontractor_id": subcontractor_id,
        "status": "success",
        "action_taken": "notice_to_proceed_issued",
        "message": "Notice to Proceed formally issued.",
    }


if __name__ == "__main__":
    mcp.run()
