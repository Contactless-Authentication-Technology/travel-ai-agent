from fastapi import FastAPI

from router import agent_run
from schemas import AgentRunRequest, AgentRunResponse


app = FastAPI(title="Agent API")

@app.post("/agent/run", response_model=AgentRunResponse)
def agent_run_endpoint(payload: AgentRunRequest) -> AgentRunResponse:
    return agent_run(payload)

