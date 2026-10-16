import React from 'react';
import { Inbox, UserCheck, AlertOctagon, CheckSquare, Layers } from 'lucide-react';

export default function QuickViewsTabs({ activeView, onViewChange, stats }) {
  const tabs = [
    { id: '', label: 'All Items', icon: Layers },
    { id: 'assigned_to_me', label: 'Assigned to Me', icon: UserCheck },
    { id: 'unassigned_urgent', label: 'Unassigned Urgent', icon: AlertOctagon, highlight: true },
    { id: 'awaiting_my_approval', label: 'Awaiting My Approval', icon: CheckSquare, leadOnly: true },
  ];

  return (
    <div className="flex items-center space-x-1 border-b border-slate-800 pb-px mb-6 overflow-x-auto">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const isActive = activeView === tab.id;

        return (
          <button
            key={tab.id}
            onClick={() => onViewChange(tab.id)}
            className={`flex items-center space-x-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-all whitespace-nowrap ${
              isActive
                ? 'border-emerald-500 text-emerald-400 bg-emerald-500/5'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            <Icon className={`w-4 h-4 ${tab.highlight && !isActive ? 'text-rose-400' : ''}`} />
            <span>{tab.label}</span>
            {tab.leadOnly && (
              <span className="text-[10px] font-mono uppercase bg-amber-500/10 text-amber-400 border border-amber-500/20 px-1 rounded">
                Lead
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
