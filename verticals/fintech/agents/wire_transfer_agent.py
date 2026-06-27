from typing import Type
from pydantic import BaseModel, Field
from core.mcp_agent import BaseMCPAgent
from core.registry import register_agent


class WireTransferInput(BaseModel):
    account_id: str = Field(..., description="The source account ID.")
    payee_account: str = Field(..., description="The destination payee account ID.")
    amount: float = Field(..., description="Amount to transfer.")
    currency: str = Field("USD", description="Currency of transfer.")
    memo: str = Field(..., description="Reason/memo for transfer.")


class WireTransferOutput(BaseModel):
    status: str = Field(..., description="Status of the transfer execution.")
    transfer_id: str = Field(
        default="", description="The unique transfer ID if successful."
    )
    error: str = Field(default="", description="Error details if the transfer failed.")


@register_agent("wire_transfer_agent")
class WireTransferAgent(BaseMCPAgent):
    """
    LangChain ReAct-style agent that manages wire transfer processing.
    Connects to the finance-mcp server to validate payee, check limits, check sanctions, and execute transfers.
    """

    mcp_server_script = "mcp_servers/finance_mcp/server.py"

    @property
    def system_prompt(self) -> str:
        return """You are an AI Wire Transfer Processing Agent. You process wire transfer requests.
To process a transfer, you MUST:
1. Retrieve the balance of the source account.
2. Validate the payee account and routing number.
3. Check the sanctions list for the payee. If flagged, you MUST reject the transfer.
4. Check the account transaction limit for the amount.
5. If all checks pass, call `initiate_wire_transfer`.
Perform all calls systematically and explain the outcomes of each step.
"""

    @property
    def input_schema(self) -> Type[BaseModel]:
        return WireTransferInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return WireTransferOutput
