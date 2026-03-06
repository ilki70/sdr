from app.agents.nodes import classify_intent, compose_reply, retrieve_context
from app.agents.state import AgentState


async def run_sales_agent(state: AgentState) -> AgentState:
    state = await classify_intent(state)
    state = await retrieve_context(state)
    state = await compose_reply(state)
    return state
