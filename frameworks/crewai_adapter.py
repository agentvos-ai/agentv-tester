from typing import Dict, Any
from crewai import Agent, Task, Crew, Process
from langchain_core.tools import StructuredTool
from core.base_framework import BaseFrameworkAdapter, RunnableAgent
from core.registry import register_framework
from core.errors import AgentExecutionError


@register_framework("crewai")
class CrewAIAdapter(BaseFrameworkAdapter):
    """
    Adapter for CrewAI agents.
    """

    def build_agent(self, system_prompt: str) -> RunnableAgent:
        # 1. Prepare Tools
        tools = [
            StructuredTool.from_function(func=fn, name=name, description=desc)
            for name, fn, desc in self.shim_tools
        ]

        # 2. Create Agent
        agent = Agent(
            role="Specialist",
            goal="Execute the assigned task accurately.",
            backstory=system_prompt,
            tools=tools,
            verbose=True,
            allow_delegation=False,
        )

        return CrewAIRunnable(agent)


class CrewAIRunnable(RunnableAgent):
    def __init__(self, agent: Agent):
        self.agent = agent

    def run(
        self, task_str: str, context: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        try:
            task = Task(
                description=task_str,
                agent=self.agent,
                expected_output="Detailed final response.",
            )
            crew = Crew(agents=[self.agent], tasks=[task], process=Process.sequential)
            result = crew.kickoff()
            return {"output": str(result), "tool_calls": []}
        except Exception as e:
            raise AgentExecutionError(f"CrewAI execution failed: {str(e)}") from e
