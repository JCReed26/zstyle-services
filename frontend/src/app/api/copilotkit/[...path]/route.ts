import { CopilotRuntime, createCopilotEndpoint } from "@copilotkit/runtime/v2";
import { LangGraphAgent } from "@copilotkit/runtime/langgraph";
import { NextRequest } from "next/server";

const LANGGRAPH_URL =
  process.env.LANGGRAPH_DEPLOYMENT_URL || "http://localhost:8123";
const LANGSMITH_KEY = process.env.LANGSMITH_API_KEY || "";

const runtime = new CopilotRuntime({
  agents: {
    exec_func_coach: new LangGraphAgent({
      deploymentUrl: LANGGRAPH_URL,
      graphId: "exec_func_coach",
      langsmithApiKey: LANGSMITH_KEY,
    }),
    personal_assistant: new LangGraphAgent({
      deploymentUrl: LANGGRAPH_URL,
      graphId: "personal_assistant",
      langsmithApiKey: LANGSMITH_KEY,
    }),
    health_agent: new LangGraphAgent({
      deploymentUrl: LANGGRAPH_URL,
      graphId: "health_agent",
      langsmithApiKey: LANGSMITH_KEY,
    }),
  },
});

const app = createCopilotEndpoint({ runtime, basePath: "/api/copilotkit" });

export async function GET(request: NextRequest) {
  return app.fetch(request);
}

export async function POST(request: NextRequest) {
  return app.fetch(request);
}
