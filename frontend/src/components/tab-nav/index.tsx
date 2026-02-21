"use client";

export type AgentTab = "coach" | "personal_assistant" | "health";

interface TabNavProps {
  activeTab: AgentTab;
  onTabChange: (tab: AgentTab) => void;
}

const TABS: { id: AgentTab; label: string; icon: string }[] = [
  { id: "coach", label: "Coach", icon: "🎯" },
  { id: "personal_assistant", label: "Personal Assistant", icon: "📋" },
  { id: "health", label: "Health", icon: "💪" },
];

export function TabNav({ activeTab, onTabChange }: TabNavProps) {
  return (
    <div className="flex border-b border-gray-200 bg-white px-4">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === tab.id
              ? "border-blue-500 text-blue-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          <span>{tab.icon}</span>
          {tab.label}
        </button>
      ))}
    </div>
  );
}
