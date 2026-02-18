"use client";

import { useAgent } from "@copilotkit/react-core/v2";
import { GoalCard } from "./cards/goal-card";
import { HabitCard } from "./cards/habit-card";

interface Goal {
  id: string;
  title: string;
  description: string;
  category: string;
  progress: number;
}

interface Habit {
  id: string;
  title: string;
  frequency: string;
  streak: number;
  completed_today: boolean;
}

interface VisionBoard {
  goals: Goal[];
  habits: Habit[];
  lifestyle_theme: string;
}

export function CoachCanvas() {
  const { agent } = useAgent();
  const visionBoard: VisionBoard = agent.state?.vision_board ?? {
    goals: [],
    habits: [],
    lifestyle_theme: "My Lifestyle",
  };

  const handleToggle = (id: string) => {
    const updated = visionBoard.habits.map((h) =>
      h.id === id ? { ...h, completed_today: !h.completed_today } : h
    );
    agent.setState({ vision_board: { ...visionBoard, habits: updated } });
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{visionBoard.lifestyle_theme}</h1>
        <p className="text-gray-500 text-sm mt-1">Your personalized lifestyle vision board</p>
      </div>

      <section>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Goals</h2>
        {visionBoard.goals.length === 0 ? (
          <div className="text-center py-8 text-gray-400 border-2 border-dashed rounded-xl text-sm">
            Tell your Coach to set up your first goals
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {visionBoard.goals.map((goal) => <GoalCard key={goal.id} goal={goal} />)}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Daily Habits</h2>
        {visionBoard.habits.length === 0 ? (
          <div className="text-center py-6 text-gray-400 border-2 border-dashed rounded-xl text-sm">
            Ask your Coach to add habits to track
          </div>
        ) : (
          <div className="space-y-2">
            {visionBoard.habits.map((habit) => (
              <HabitCard key={habit.id} habit={habit} onToggle={handleToggle} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
