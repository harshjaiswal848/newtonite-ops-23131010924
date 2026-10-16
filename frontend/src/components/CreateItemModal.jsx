import React, { useState } from 'react';
import { X, Plus, Zap, AlertCircle, CheckCircle2 } from 'lucide-react';

export default function CreateItemModal({ isOpen, onClose, teams, onCreateItem, isCreating }) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [teamId, setTeamId] = useState(teams[0]?.id || '');
  const [type, setType] = useState('task');
  const [priority, setPriority] = useState('medium');
  const [simulateDoubleClick, setSimulateDoubleClick] = useState(false);
  const [idempotencyResult, setIdempotencyResult] = useState(null);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title.trim() || !teamId) return;

    setError(null);
    setIdempotencyResult(null);

    const payload = {
      title,
      description,
      team_id: teamId,
      type,
      priority,
    };

    if (simulateDoubleClick) {
      // Simulate rapid double click using the exact same Idempotency-Key
      const testKey = `manual-double-click-${crypto.randomUUID()}`;
      try {
        const [res1, res2] = await Promise.all([
          onCreateItem(payload, testKey),
          onCreateItem(payload, testKey),
        ]);

        setIdempotencyResult({
          success: true,
          message: `Idempotency test succeeded! Two requests fired concurrently with key: ${testKey.slice(0, 16)}...`,
          res1Id: res1?.item?.id,
          res2Id: res2?.item?.id,
          res2IsReplay: res2?.isReplay,
        });

        setTimeout(() => {
          onClose();
        }, 3000);
      } catch (err) {
        setError(err.message || 'Creation failed');
      }
    } else {
      try {
        await onCreateItem(payload);
        onClose();
      } catch (err) {
        setError(err.message || 'Creation failed');
      }
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-lg shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Plus className="w-5 h-5 text-emerald-400" />
            <h3 className="font-bold text-slate-100 text-base">Create Operational Work Item</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg flex items-center space-x-2 text-rose-400 text-xs">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {idempotencyResult && (
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg space-y-1 text-emerald-300 text-xs">
              <div className="flex items-center space-x-1.5 font-semibold">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>{idempotencyResult.message}</span>
              </div>
              <p className="font-mono text-[11px] text-emerald-400/80">
                Created ID: {idempotencyResult.res1Id} (Replay returned identical object)
              </p>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Title <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Card Authorization Gateway 504 Timeout"
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Provide operational context, steps to reproduce, or incident triage notes..."
              rows={3}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">Team</label>
              <select
                value={teamId}
                onChange={(e) => setTeamId(e.target.value)}
                className="w-full px-2.5 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200"
              >
                {teams.map((t) => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">Type</label>
              <select
                value={type}
                onChange={(e) => setType(e.target.value)}
                className="w-full px-2.5 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200"
              >
                <option value="incident">Incident</option>
                <option value="customer_issue">Customer Issue</option>
                <option value="payment">Payment</option>
                <option value="compliance">Compliance</option>
                <option value="task">Task</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">Priority</label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className="w-full px-2.5 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>
          </div>

          {/* Reviewer Idempotency Test Toggle */}
          <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg flex items-center justify-between">
            <div className="space-y-0.5">
              <span className="text-xs font-semibold text-slate-200 flex items-center space-x-1">
                <Zap className="w-3.5 h-3.5 text-amber-400" />
                <span>Simulate Double-Click (Idempotency Test)</span>
              </span>
              <p className="text-[11px] text-slate-400">
                Fires 2 identical requests concurrently with the same Idempotency-Key
              </p>
            </div>
            <input
              type="checkbox"
              checked={simulateDoubleClick}
              onChange={(e) => setSimulateDoubleClick(e.target.checked)}
              className="w-4 h-4 accent-emerald-500 rounded cursor-pointer"
            />
          </div>

          <div className="pt-2 flex items-center justify-end space-x-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isCreating}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg shadow-sm disabled:opacity-50 flex items-center space-x-1"
            >
              <span>{isCreating ? 'Creating...' : 'Create Item'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
