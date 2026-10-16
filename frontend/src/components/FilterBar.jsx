import React from 'react';
import { Search, Plus, Filter, X } from 'lucide-react';

export default function FilterBar({
  searchQuery,
  onSearchChange,
  selectedTeam,
  onTeamChange,
  selectedStatus,
  onStatusChange,
  selectedPriority,
  onPriorityChange,
  teams,
  onOpenCreate,
  canCreate,
}) {
  const hasActiveFilters = selectedTeam || selectedStatus || selectedPriority || searchQuery;

  const handleClearFilters = () => {
    onSearchChange('');
    onTeamChange('');
    onStatusChange('');
    onPriorityChange('');
  };

  return (
    <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-6 bg-slate-900/40 p-3.5 rounded-xl border border-slate-800/80">
      {/* Search Input */}
      <div className="relative flex-1 min-w-[240px]">
        <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search by title, description or incident ID..."
          className="w-full pl-9 pr-4 py-2 bg-slate-900 border border-slate-800 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition-colors"
        />
        {searchQuery && (
          <button
            onClick={() => onSearchChange('')}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Dropdown Filters */}
      <div className="flex flex-wrap items-center gap-2">
        {/* Team Dropdown */}
        <select
          value={selectedTeam}
          onChange={(e) => onTeamChange(e.target.value)}
          className="bg-slate-900 border border-slate-800 text-slate-300 text-xs rounded-lg px-3 py-2 focus:outline-none focus:border-emerald-500"
        >
          <option value="">All Teams</option>
          {teams.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>

        {/* Status Dropdown */}
        <select
          value={selectedStatus}
          onChange={(e) => onStatusChange(e.target.value)}
          className="bg-slate-900 border border-slate-800 text-slate-300 text-xs rounded-lg px-3 py-2 focus:outline-none focus:border-emerald-500"
        >
          <option value="">All Statuses</option>
          <option value="Open">Open</option>
          <option value="In Progress">In Progress</option>
          <option value="Awaiting Approval">Awaiting Approval</option>
          <option value="Resolved">Resolved</option>
          <option value="Closed">Closed</option>
        </select>

        {/* Priority Dropdown */}
        <select
          value={selectedPriority}
          onChange={(e) => onPriorityChange(e.target.value)}
          className="bg-slate-900 border border-slate-800 text-slate-300 text-xs rounded-lg px-3 py-2 focus:outline-none focus:border-emerald-500"
        >
          <option value="">All Priorities</option>
          <option value="urgent">Urgent</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>

        {hasActiveFilters && (
          <button
            onClick={handleClearFilters}
            className="px-2.5 py-2 text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors flex items-center space-x-1"
            title="Reset filters"
          >
            <X className="w-3.5 h-3.5" />
            <span>Reset</span>
          </button>
        )}

        {/* Create Button */}
        <button
          onClick={onOpenCreate}
          disabled={!canCreate}
          className={`ml-2 px-3.5 py-2 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-colors shadow-sm ${
            canCreate
              ? 'bg-emerald-600 hover:bg-emerald-500 text-white'
              : 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-800'
          }`}
          title={!canCreate ? 'Viewer role cannot create items' : 'Create new work item'}
        >
          <Plus className="w-4 h-4" />
          <span>New Work Item</span>
        </button>
      </div>
    </div>
  );
}
