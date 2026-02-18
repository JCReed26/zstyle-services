interface Goal {
  id: string;
  title: string;
  description: string;
  category: string;
  progress: number;
}

export function GoalCard({ goal }: { goal: Goal }) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
      <div className="flex items-start justify-between mb-2">
        <h3 className="font-semibold text-gray-900 text-sm">{goal.title}</h3>
        <span className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full flex-shrink-0 ml-2">
          {goal.category}
        </span>
      </div>
      <p className="text-xs text-gray-500 mb-3">{goal.description}</p>
      <div className="flex items-center gap-2">
        <div className="flex-1 bg-gray-100 rounded-full h-1.5">
          <div className="bg-blue-500 h-1.5 rounded-full" style={{ width: `${goal.progress}%` }} />
        </div>
        <span className="text-xs text-gray-500">{goal.progress}%</span>
      </div>
    </div>
  );
}
