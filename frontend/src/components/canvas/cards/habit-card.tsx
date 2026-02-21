interface Habit {
  id: string;
  title: string;
  frequency: string;
  streak: number;
  completed_today: boolean;
}

export function HabitCard({ habit, onToggle }: { habit: Habit; onToggle: (id: string) => void }) {
  return (
    <div
      className={`bg-white rounded-xl border p-3 flex items-center gap-3 ${
        habit.completed_today ? "border-green-200 bg-green-50" : "border-gray-100"
      }`}
    >
      <button
        onClick={() => onToggle(habit.id)}
        className={`w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0 text-xs ${
          habit.completed_today ? "bg-green-500 border-green-500 text-white" : "border-gray-300"
        }`}
      >
        {habit.completed_today && "✓"}
      </button>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900">{habit.title}</p>
        <p className="text-xs text-gray-500">{habit.frequency} · 🔥 {habit.streak} day streak</p>
      </div>
    </div>
  );
}
