"use client";

import { useAgent } from "@copilotkit/react-core/v2";

interface EmailSummary {
  id: string;
  subject: string;
  from_address: string;
  summary: string;
  action_required: boolean;
}

interface CalendarBlock {
  id: string;
  title: string;
  start: string;
  end: string;
  type: string;
}

interface Automation {
  id: string;
  name: string;
  cron: string;
  last_run: string | null;
  enabled: boolean;
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-center py-6 text-gray-400 border-2 border-dashed rounded-xl text-sm">
      {message}
    </div>
  );
}

export function PersonalAssistantCanvas() {
  const { agent } = useAgent();
  const pa = agent.state?.personal_assistant ?? { calendar: [], emails: [], tasks: [], automations: [] };
  const emails: EmailSummary[] = pa.emails ?? [];
  const calendar: CalendarBlock[] = pa.calendar ?? [];
  const automations: Automation[] = pa.automations ?? [];

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Personal Assistant</h1>

      <section>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Email Digest</h2>
        <div className="space-y-2">
          {emails.length === 0 ? (
            <EmptyState message="No email digest yet — ask your assistant to triage your inbox" />
          ) : emails.map((email) => (
            <div key={email.id} className="bg-white rounded-xl border border-gray-100 p-4">
              <div className="flex items-start justify-between">
                <p className="text-sm font-medium text-gray-900">{email.subject}</p>
                {email.action_required && (
                  <span className="text-xs bg-red-50 text-red-600 px-2 py-0.5 rounded-full flex-shrink-0 ml-2">Action</span>
                )}
              </div>
              <p className="text-xs text-gray-500 mt-1">{email.from_address}</p>
              <p className="text-xs text-gray-600 mt-2">{email.summary}</p>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">This Week</h2>
        <div className="space-y-2">
          {calendar.length === 0 ? (
            <EmptyState message="No time blocks yet — ask your assistant to plan your week" />
          ) : calendar.map((block) => (
            <div key={block.id} className="bg-white rounded-xl border border-gray-100 p-3 flex items-center gap-3">
              <div className="w-1 h-10 bg-blue-400 rounded-full flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-gray-900">{block.title}</p>
                <p className="text-xs text-gray-500">{block.start} → {block.end}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Automations</h2>
        <div className="space-y-2">
          {automations.length === 0 ? (
            <EmptyState message="No automations configured yet" />
          ) : automations.map((auto) => (
            <div key={auto.id} className="bg-white rounded-xl border border-gray-100 p-3 flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-900">{auto.name}</p>
                <p className="text-xs text-gray-500">{auto.cron} · Last run: {auto.last_run ?? "Never"}</p>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded-full ${auto.enabled ? "bg-green-50 text-green-600" : "bg-gray-100 text-gray-400"}`}>
                {auto.enabled ? "Active" : "Paused"}
              </span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
