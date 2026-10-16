import React, { useState } from 'react';
import {
  X,
  UserCheck,
  CheckCircle2,
  Clock,
  ArrowRight,
  ShieldCheck,
  Edit2,
  Save,
  MessageSquare,
  AlertTriangle,
  History,
} from 'lucide-react';

const WORKFLOW_STEPS = ['Open', 'In Progress', 'Awaiting Approval', 'Resolved', 'Closed'];

export default function WorkItemDetailDrawer({
  item,
  onClose,
  currentUserRole,
  onClaim,
  isClaiming,
  onTransition,
  isTransitioning,
  onUpdate,
  isUpdating,
  onAddComment,
  isCommenting,
  conflictError,
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(item?.title || '');
  const [editDesc, setEditDesc] = useState(item?.description || '');
  const [editPriority, setEditPriority] = useState(item?.priority || 'medium');
  const [newComment, setNewComment] = useState('');
  const [transitionComment, setTransitionComment] = useState('');

  if (!item) return null;

  const isLeadOrAdmin = currentUserRole === 'Lead' || currentUserRole === 'Admin';
  const isMemberOrAbove = ['Member', 'Lead', 'Admin'].includes(currentUserRole);

  const currentStepIndex = WORKFLOW_STEPS.indexOf(item.status);

  const handleSaveEdit = async () => {
    try {
      await onUpdate(item.id, {
        title: editTitle,
        description: editDesc,
        priority: editPriority,
        version: item.version, // OPTIMISTIC LOCK: Sends client version!
      });
      setIsEditing(false);
    } catch {
      // Error handled by parent rollback / conflict banner
    }
  };

  const handleCommentSubmit = async (e) => {
    e.preventDefault();
    if (!newComment.trim()) return;
    await onAddComment(item.id, newComment);
    setNewComment('');
  };

  return (
    <div className="fixed inset-y-0 right-0 z-40 w-full max-w-xl bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col overflow-hidden animate-in slide-in-from-right duration-300">
      {/* Header */}
      <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
        <div className="flex items-center space-x-2">
          <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
            ID: {item.id.slice(0, 8)}...
          </span>
          <span className="text-xs font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold">
            Version {item.version}
          </span>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Content Body */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Title & Metadata */}
        <div>
          {isEditing ? (
            <div className="space-y-3">
              <input
                type="text"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-slate-100 font-semibold"
              />
              <textarea
                value={editDesc}
                onChange={(e) => setEditDesc(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-200"
              />
              <div className="flex items-center space-x-3">
                <select
                  value={editPriority}
                  onChange={(e) => setEditPriority(e.target.value)}
                  className="bg-slate-950 border border-slate-700 text-xs rounded-lg px-2.5 py-1.5 text-slate-300"
                >
                  <option value="low">Low Priority</option>
                  <option value="medium">Medium Priority</option>
                  <option value="high">High Priority</option>
                  <option value="urgent">Urgent Priority</option>
                </select>

                <button
                  onClick={handleSaveEdit}
                  disabled={isUpdating}
                  className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg flex items-center space-x-1"
                >
                  <Save className="w-3.5 h-3.5" />
                  <span>{isUpdating ? 'Saving...' : 'Save (Version Check)'}</span>
                </button>
                <button
                  onClick={() => setIsEditing(false)}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded-lg"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div>
              <div className="flex items-start justify-between gap-3">
                <h2 className="text-lg font-bold text-slate-100 leading-snug">{item.title}</h2>
                {isMemberOrAbove && (
                  <button
                    onClick={() => {
                      setEditTitle(item.title);
                      setEditDesc(item.description);
                      setEditPriority(item.priority);
                      setIsEditing(true);
                    }}
                    className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors shrink-0"
                    title="Edit Item (Optimistic Lock Test)"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                )}
              </div>
              <p className="text-xs text-slate-300 mt-2 leading-relaxed">
                {item.description || 'No description provided.'}
              </p>
            </div>
          )}
        </div>

        {/* Workflow State Stepper */}
        <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
            Lifecycle Workflow
          </div>
          <div className="flex items-center justify-between relative">
            {WORKFLOW_STEPS.map((step, idx) => {
              const isPast = idx < currentStepIndex;
              const isCurrent = idx === currentStepIndex;

              return (
                <div key={step} className="flex flex-col items-center z-10 text-center flex-1">
                  <div
                    className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                      isCurrent
                        ? 'bg-emerald-500 text-slate-950 ring-4 ring-emerald-500/20'
                        : isPast
                        ? 'bg-emerald-950 text-emerald-400 border border-emerald-600'
                        : 'bg-slate-800 text-slate-500 border border-slate-700'
                    }`}
                  >
                    {isPast ? <CheckCircle2 className="w-4 h-4" /> : idx + 1}
                  </div>
                  <span
                    className={`text-[10px] mt-1.5 font-medium leading-tight max-w-[70px] ${
                      isCurrent ? 'text-emerald-400 font-semibold' : 'text-slate-400'
                    }`}
                  >
                    {step}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Action Controls */}
        <div className="bg-slate-800/40 p-4 rounded-xl border border-slate-800 space-y-3">
          <div className="text-xs font-semibold text-slate-300 flex items-center justify-between">
            <span>Workflow Actions</span>
            <span className="text-[11px] text-slate-400">Your Role: <strong className="text-slate-200">{currentUserRole}</strong></span>
          </div>

          <div className="flex flex-wrap gap-2">
            {/* Atomic Claim */}
            {!item.assignee_id && isMemberOrAbove && (
              <button
                onClick={() => onClaim(item.id)}
                disabled={isClaiming}
                className="px-3.5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg flex items-center space-x-1.5 transition-colors shadow-sm disabled:opacity-50"
              >
                <UserCheck className="w-4 h-4" />
                <span>{isClaiming ? 'Claiming...' : 'Claim Work Item'}</span>
              </button>
            )}

            {/* Transition: Open -> In Progress */}
            {item.status === 'Open' && isMemberOrAbove && (
              <button
                onClick={() => onTransition(item.id, 'In Progress')}
                disabled={isTransitioning}
                className="px-3.5 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 text-xs font-semibold rounded-lg flex items-center space-x-1.5 transition-colors"
              >
                <span>Start Progress</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}

            {/* Transition: In Progress -> Awaiting Approval */}
            {item.status === 'In Progress' && isMemberOrAbove && (
              <button
                onClick={() => onTransition(item.id, 'Awaiting Approval')}
                disabled={isTransitioning}
                className="px-3.5 py-2 bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold rounded-lg flex items-center space-x-1.5 transition-colors shadow-sm"
              >
                <span>Submit for Approval</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}

            {/* Transition: Awaiting Approval -> Resolved (CRITICAL: Lead Only) */}
            {item.status === 'Awaiting Approval' && (
              <button
                onClick={() => onTransition(item.id, 'Resolved')}
                disabled={isTransitioning}
                className={`px-3.5 py-2 text-xs font-semibold rounded-lg flex items-center space-x-1.5 transition-colors shadow-sm ${
                  isLeadOrAdmin
                    ? 'bg-emerald-600 hover:bg-emerald-500 text-white'
                    : 'bg-amber-950/40 border border-amber-600/40 text-amber-300 hover:bg-amber-900/40'
                }`}
                title={!isLeadOrAdmin ? 'Non-Lead approval will be rejected with 403 Forbidden by the server' : 'Approve and mark resolved'}
              >
                <ShieldCheck className="w-4 h-4" />
                <span>Approve &amp; Resolve {!isLeadOrAdmin && '(Lead Only Gate)'}</span>
              </button>
            )}

            {/* Transition: Resolved -> Closed */}
            {item.status === 'Resolved' && (
              <button
                onClick={() => onTransition(item.id, 'Closed')}
                disabled={isTransitioning}
                className={`px-3.5 py-2 text-xs font-semibold rounded-lg flex items-center space-x-1.5 transition-colors shadow-sm ${
                  isLeadOrAdmin
                    ? 'bg-slate-700 hover:bg-slate-600 text-slate-200'
                    : 'bg-slate-800 text-slate-500 cursor-not-allowed'
                }`}
                title={!isLeadOrAdmin ? 'Only Lead or Admin can close resolved items' : 'Close item'}
              >
                <span>Close Item</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Activity Audit Timeline */}
        <div className="space-y-3">
          <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center space-x-1.5">
            <History className="w-4 h-4 text-emerald-400" />
            <span>Transactional Activity Audit Log</span>
          </div>

          <div className="space-y-2 border-l-2 border-slate-800 ml-2 pl-4">
            {item.activities && item.activities.length > 0 ? (
              item.activities.map((act) => (
                <div key={act.id} className="text-xs space-y-1 py-1 relative">
                  <div className="w-2 h-2 rounded-full bg-emerald-500 absolute -left-[21px] top-2" />
                  <div className="flex items-center justify-between text-slate-400">
                    <span className="font-semibold text-slate-200 capitalize">
                      {act.event_type.replace('_', ' ')}
                    </span>
                    <span className="font-mono text-[10px] text-slate-500">
                      {new Date(act.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </span>
                  </div>
                  <p className="text-slate-300">{act.new_value || act.old_value || 'State updated'}</p>
                </div>
              ))
            ) : (
              <div className="text-xs text-slate-500">No activity recorded yet.</div>
            )}
          </div>
        </div>

        {/* Comments Section */}
        <div className="space-y-3 pt-2">
          <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center space-x-1.5">
            <MessageSquare className="w-4 h-4 text-emerald-400" />
            <span>Operator Comments</span>
          </div>

          {/* Add Comment Form */}
          {isMemberOrAbove && (
            <form onSubmit={handleCommentSubmit} className="space-y-2">
              <textarea
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                placeholder="Add an operational note or resolution comment..."
                rows={2}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500"
              />
              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={isCommenting || !newComment.trim()}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg transition-colors disabled:opacity-40"
                >
                  {isCommenting ? 'Posting...' : 'Post Comment'}
                </button>
              </div>
            </form>
          )}

          {/* Comment List */}
          <div className="space-y-2.5">
            {item.comments && item.comments.length > 0 ? (
              item.comments.map((c) => (
                <div key={c.id} className="p-3 bg-slate-950/60 rounded-lg border border-slate-800/80 space-y-1">
                  <div className="flex items-center justify-between text-[11px] text-slate-400">
                    <span className="font-semibold text-slate-200">{c.user?.full_name || 'Operator'}</span>
                    <span className="font-mono text-slate-500">{new Date(c.created_at).toLocaleTimeString()}</span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">{c.content}</p>
                </div>
              ))
            ) : (
              <div className="text-xs text-slate-500">No comments yet.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
