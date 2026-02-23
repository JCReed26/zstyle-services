"use client";

import { useState } from "react";
import { CopilotChat } from "@copilotkit/react-core/v2";
import { useFrontendTool } from "@copilotkit/react-core/v2";
import { z } from "zod";
import { TabNav, AgentTab } from "@/components/tab-nav";
import { CoachCanvas } from "@/components/canvas/coach-canvas";
import { PersonalAssistantCanvas } from "@/components/canvas/personal-assistant-canvas";
import { HealthCanvas } from "@/components/canvas/health-canvas";

const AGENT_GRAPH_IDS: Record<AgentTab, string> = {
  coach: "exec_func_coach",
  personal_assistant: "personal_assistant",
  health: "health_agent",
};

export function AppLayout() {
  const [activeTab, setActiveTab] = useState<AgentTab>("coach");

  useFrontendTool({
    name: "switchTab",
    description: "Switch the active tab to redirect the user to a specialized agent.",
    parameters: z.object({ tab: z.enum(["coach", "personal_assistant", "health"]) }),
    handler: async ({ tab }: { tab: AgentTab }) => {
      setActiveTab(tab);
      return `Switched to ${tab} tab`;
    },
  });

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      <TabNav activeTab={activeTab} onTabChange={setActiveTab} />
      <div className="flex flex-1 overflow-hidden">
        <div className="flex-1 overflow-auto p-6">
          {activeTab === "coach" && <CoachCanvas />}
          {activeTab === "personal_assistant" && <PersonalAssistantCanvas />}
          {activeTab === "health" && <HealthCanvas />}
        </div>
        <div className="w-96 border-l border-gray-200 bg-white flex flex-col relative">
          {(Object.keys(AGENT_GRAPH_IDS) as AgentTab[]).map((tab) => (
            <div
              key={tab}
              className={`flex-1 flex flex-col ${activeTab === tab ? "h-full" : "hidden h-0"}`}
            >
              <CopilotChat agentId={AGENT_GRAPH_IDS[tab]} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export { AppLayout as ExampleLayout };
