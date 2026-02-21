"use client";

import { useAgent } from "@copilotkit/react-core/v2";
import { BarChart } from "@/components/generative-ui/charts/bar-chart";

interface WorkoutDay {
  day: string;
  workout_type: string;
  duration_min: number;
}

interface StravaStats {
  recent_run_km: number;
  recent_ride_km: number;
  ytd_run_km: number;
  last_synced: string;
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-center py-6 text-gray-400 border-2 border-dashed rounded-xl text-sm">
      {message}
    </div>
  );
}

export function HealthCanvas() {
  const { agent } = useAgent({ agentId: "health_agent" });
  const health = agent.state?.health ?? { weekly_plan: [], strava_stats: null, meal_plan: null };
  const stravaStats: StravaStats | null = health.strava_stats ?? null;
  const weeklyPlan: WorkoutDay[] = health.weekly_plan ?? [];
  const mealPlan: Record<string, string[]> | null = health.meal_plan ?? null;

  const stravaChartData = stravaStats ? [
    { label: "Recent Run (km)", value: stravaStats.recent_run_km },
    { label: "Recent Ride (km)", value: stravaStats.recent_ride_km },
    { label: "YTD Run (km)", value: stravaStats.ytd_run_km },
  ] : [];

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Health</h1>

      <section>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Strava Stats</h2>
        {stravaStats ? (
          <BarChart title="Activity Summary" description="Your recent and year-to-date stats" data={stravaChartData} />
        ) : (
          <EmptyState message="Connect Strava to see your fitness stats" />
        )}
      </section>

      <section>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Weekly Plan</h2>
        {weeklyPlan.length === 0 ? (
          <EmptyState message="Ask your Fitness Coach to build your weekly workout plan" />
        ) : (
          <div className="grid grid-cols-7 gap-2">
            {weeklyPlan.map((day) => (
              <div key={day.day} className="bg-white rounded-xl border border-gray-100 p-3 text-center">
                <p className="text-xs font-semibold text-gray-500 uppercase">{day.day.slice(0, 3)}</p>
                <p className="text-sm font-medium text-gray-900 mt-1">{day.workout_type}</p>
                <p className="text-xs text-gray-400 mt-1">{day.duration_min}min</p>
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">This Week&apos;s Meals</h2>
        {!mealPlan ? (
          <EmptyState message="Ask your Nutritionist to create a meal plan" />
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(mealPlan).map(([day, meals]) => (
              <div key={day} className="bg-white rounded-xl border border-gray-100 p-3">
                <p className="text-xs font-semibold text-gray-500 uppercase mb-2">{day}</p>
                {meals.map((meal, i) => (
                  <p key={i} className="text-xs text-gray-700">• {meal}</p>
                ))}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
