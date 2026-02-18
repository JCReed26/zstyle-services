import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { LangGraphAgent } from "@copilotkit/runtime/langgraph";
import { NextRequest } from "next/server";
import { aguiMiddleware } from "@/app/api/copilotkit/ag-ui-middleware";

const LANGGRAPH_URL = process.env.LANGGRAPH_DEPLOYMENT_URL || "http://localhost:8123";
const LANGSMITH_KEY = process.env.LANGSMITH_API_KEY || "";

// exec_func_coach — primary orchestrator with AG-UI middleware
const execFuncCoachAgent = new LangGraphAgent({
  deploymentUrl: LANGGRAPH_URL,
  graphId: "exec_func_coach",
  langsmithApiKey: LANGSMITH_KEY,
});
execFuncCoachAgent.use(...aguiMiddleware);

// personal_assistant — email, calendar, task management
const personalAssistantAgent = new LangGraphAgent({
  deploymentUrl: LANGGRAPH_URL,
  graphId: "personal_assistant",
  langsmithApiKey: LANGSMITH_KEY,
});

// health_agent — fitness coach + nutritionist
const healthAgentAgent = new LangGraphAgent({
  deploymentUrl: LANGGRAPH_URL,
  graphId: "health_agent",
  langsmithApiKey: LANGSMITH_KEY,
});

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    endpoint: "/api/copilotkit",
    serviceAdapter: new ExperimentalEmptyAdapter(),
    runtime: new CopilotRuntime({
      agents: {
        exec_func_coach: execFuncCoachAgent,
        personal_assistant: personalAssistantAgent,
        health_agent: healthAgentAgent,
      },
    }),
  });

  return handleRequest(req);
};
