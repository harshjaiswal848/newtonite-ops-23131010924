import React, { useState, useEffect } from 'react';
import { X, ShieldCheck, UserCheck, Eye, KeyRound, AlertCircle } from 'lucide-react';
import { getDemoUsers } from '../api/client';

export default function LoginModal({ isOpen, onClose, onLogin, activeUserId }) {
  const [demoUsers, setDemoUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [customEmail, setCustomEmail] = useState('');
  const [customPassword, setCustomPassword] = useState('password123');
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen) {
      setLoading(true);
      getDemoUsers()
        .then(users => {
          setDemoUsers(users);
          setLoading(false);
        })
        .catch(err => {
          console.error(err);
          setLoading(false);
        });
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSelectUser = async (email, password = 'password123') => {
    try {
      setError(null);
      await onLogin(email, password);
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to authenticate');
    }
  };

  const getRoleIcon = (role) => {
    switch (role) {
      case 'Lead': return <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />;
      case 'Admin': return <KeyRound className="w-3.5 h-3.5 text-purple-400" />;
      case 'Viewer': return <Eye className="w-3.5 h-3.5 text-slate-400" />;
      default: return <UserCheck className="w-3.5 h-3.5 text-emerald-400" />;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-900/50">
          <div>
            <h2 className="text-lg font-bold text-slate-100">Select Test Persona / Account</h2>
            <p className="text-xs text-slate-400">
              One-click switcher to test real server-side authorization across roles and teams
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="mx-5 mt-4 p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg flex items-center space-x-2 text-rose-400 text-sm">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* User Selection Grid */}
        <div className="p-5 overflow-y-auto space-y-3 flex-1">
          {loading ? (
            <div className="py-12 text-center text-slate-400 text-sm">Loading seeded personas...</div>
          ) : (
            demoUsers.map((u) => {
              const isActive = u.id === activeUserId;
              return (
                <div
                  key={u.id}
                  onClick={() => handleSelectUser(u.email)}
                  className={`p-3.5 rounded-lg border transition-all cursor-pointer flex items-center justify-between ${
                    isActive
                      ? 'bg-emerald-950/40 border-emerald-500/50 ring-1 ring-emerald-500/30'
                      : 'bg-slate-800/40 border-slate-800 hover:border-slate-700 hover:bg-slate-800/80'
                  }`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="font-semibold text-sm text-slate-100">{u.full_name}</span>
                      {isActive && (
                        <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                          Active
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-slate-400 font-mono">{u.email}</div>
                    <div className="flex flex-wrap gap-1.5 mt-1.5">
                      {u.teams?.map((t, idx) => (
                        <span
                          key={idx}
                          className="inline-flex items-center space-x-1 text-[11px] px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-300"
                        >
                          {getRoleIcon(t.role)}
                          <span>{t.team_name}:</span>
                          <span className="font-semibold text-slate-200">{t.role}</span>
                        </span>
                      ))}
                    </div>
                  </div>

                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleSelectUser(u.email);
                    }}
                    className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                      isActive
                        ? 'bg-emerald-600 text-white'
                        : 'bg-slate-700 hover:bg-slate-600 text-slate-200'
                    }`}
                  >
                    {isActive ? 'Current' : 'Select'}
                  </button>
                </div>
              );
            })
          )}
        </div>

        {/* Manual Login Footer */}
        <div className="p-4 bg-slate-950 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
          <span>Default seeded password for all users: <code className="text-emerald-400">password123</code></span>
          <button
            onClick={onClose}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-xs transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
