import React from 'react';
import { UserCheck, AlertCircle, Clock, ChevronRight, CheckCircle2, ShieldAlert } from 'lucide-react';

export default function WorkItemList({
  items,
  totalCount,
  hasMore,
  onLoadMore,
  isLoadingMore,
  onSelectItem,
  selectedItemId,
  onClaimItem,
  isClaimingId,
  canClaim,
}) {
  const getStatusBadge = (status) => {
    switch (status) {
      case 'Open':
        return 'bg-sky-500/10 text-sky-400 border-sky-500/20';
      case 'In Progress':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      case 'Awaiting Approval':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/20 ring-1 ring-purple-500/20';
      case 'Resolved':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'Closed':
        return 'bg-slate-700/30 text-slate-400 border-slate-700/50';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  const getPriorityBadge = (priority) => {
    switch (priority) {
      case 'urgent':
        return 'bg-rose-500/10 text-rose-400 border-rose-500/30 animate-pulse';
      case 'high':
        return 'bg-orange-500/10 text-orange-400 border-orange-500/20';
      case 'medium':
        return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20';
      case 'low':
        return 'bg-slate-700/20 text-slate-400 border-slate-700/30';
      default:
        return 'bg-slate-800 text-slate-400';
    }
  };

  const getTypeBadge = (type) => {
    switch (type) {
      case 'incident':
        return 'bg-rose-950/40 text-rose-300 border-rose-800/50';
      case 'payment':
        return 'bg-emerald-950/40 text-emerald-300 border-emerald-800/50';
      case 'compliance':
        return 'bg-indigo-950/40 text-indigo-300 border-indigo-800/50';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  if (!items || items.length === 0) {
    return (
      <div className="bg-slate-900/30 border border-slate-800 rounded-xl p-12 text-center">
        <AlertCircle className="w-8 h-8 text-slate-600 mx-auto mb-3" />
        <h3 className="text-sm font-semibold text-slate-300">No work items found</h3>
        <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
          No work items match the current query and filters. Try adjusting your search or switching to another view.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {/* Items Count Summary */}
      <div className="text-xs text-slate-400 px-1 flex items-center justify-between pb-1">
        <span>
          Showing <span className="font-semibold text-slate-200">{items.length}</span> of{' '}
          <span className="font-semibold text-slate-200">{totalCount || items.length}</span> items
        </span>
        <span className="font-mono text-[11px] text-slate-500">Indexed cursor pagination</span>
      </div>

      {/* Item Cards */}
      <div className="space-y-2">
        {items.map((item) => {
          const isSelected = item.id === selectedItemId;
          const isClaiming = isClaimingId === item.id;
          const isUnassigned = !item.assignee_id;

          return (
            <div
              key={item.id}
              onClick={() => onSelectItem(item)}
              className={`p-4 rounded-xl border transition-all cursor-pointer flex flex-col md:flex-row md:items-center justify-between gap-3 ${
                isSelected
                  ? 'bg-slate-800/90 border-emerald-500/50 shadow-md ring-1 ring-emerald-500/20'
                  : 'bg-slate-900/60 border-slate-800/90 hover:border-slate-700 hover:bg-slate-900'
              }`}
            >
              {/* Left Column: Title & Metadata */}
              <div className="space-y-1.5 flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`text-[11px] font-semibold uppercase px-2 py-0.5 rounded border ${getTypeBadge(item.type)}`}>
                    {item.type}
                  </span>
                  <span className={`text-[11px] font-semibold uppercase px-2 py-0.5 rounded border ${getPriorityBadge(item.priority)}`}>
                    {item.priority}
                  </span>
                  <span className={`text-[11px] font-semibold px-2 py-0.5 rounded border ${getStatusBadge(item.status)}`}>
                    {item.status}
                  </span>
                  {/* Concurrency Version Tag */}
                  <span
                    className="text-[10px] font-mono bg-slate-800 text-slate-400 border border-slate-700 px-1.5 py-0.5 rounded"
                    title="Optimistic Locking Version counter"
                  >
                    v{item.version}
                  </span>
                </div>

                <h3 className="text-sm font-semibold text-slate-100 truncate pr-2">
                  {item.title}
                </h3>

                <p className="text-xs text-slate-400 line-clamp-1">
                  {item.description || 'No description provided.'}
                </p>

                <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 pt-1">
                  <span>Team: <span className="text-slate-300 font-medium">{item.team?.name || item.team_id}</span></span>
                  <span>•</span>
                  <span>Created: <span className="text-slate-400 font-mono">{new Date(item.created_at).toLocaleDateString()}</span></span>
                </div>
              </div>

              {/* Right Column: Assignee & Action */}
              <div className="flex items-center justify-between md:justify-end space-x-3 shrink-0 pt-2 md:pt-0 border-t md:border-t-0 border-slate-800">
                <div className="text-right">
                  {item.assignee ? (
                    <div className="flex items-center space-x-2">
                      <div className="w-6 h-6 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-semibold text-slate-300">
                        {item.assignee.full_name?.charAt(0) || 'U'}
                      </div>
                      <span className="text-xs text-slate-300 font-medium">{item.assignee.full_name}</span>
                    </div>
                  ) : (
                    <span className="text-xs text-amber-400/80 font-medium bg-amber-500/5 border border-amber-500/20 px-2 py-1 rounded">
                      Unassigned
                    </span>
                  )}
                </div>

                {/* Quick Atomic Claim Button for Unassigned */}
                {isUnassigned && canClaim && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onClaimItem(item.id);
                    }}
                    disabled={isClaiming}
                    className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded-lg transition-colors flex items-center space-x-1 shadow-sm disabled:opacity-50"
                    title="Atomic Claim (Race-condition safe)"
                  >
                    <UserCheck className="w-3.5 h-3.5" />
                    <span>{isClaiming ? 'Claiming...' : 'Claim'}</span>
                  </button>
                )}

                <ChevronRight className="w-4 h-4 text-slate-600" />
              </div>
            </div>
          );
        })}
      </div>

      {/* Keyset Cursor Pagination Button */}
      {hasMore && (
        <div className="pt-4 text-center">
          <button
            onClick={onLoadMore}
            disabled={isLoadingMore}
            className="px-5 py-2.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-semibold rounded-xl transition-all shadow-sm hover:border-slate-600 disabled:opacity-50 flex items-center space-x-2 mx-auto"
          >
            <Clock className={`w-3.5 h-3.5 ${isLoadingMore ? 'animate-spin' : ''}`} />
            <span>{isLoadingMore ? 'Loading Next Page...' : 'Load More Items (Cursor Keyset)'}</span>
          </button>
        </div>
      )}
    </div>
  );
}
