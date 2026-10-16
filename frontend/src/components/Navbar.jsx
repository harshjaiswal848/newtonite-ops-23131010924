import React from 'react';
import { Shield, Zap, LogOut, User, RefreshCw } from 'lucide-react';

export default function Navbar({ currentUser, onLogout, onOpenLogin, onRefresh, isFetching }) {
  return (
    <header className="bg-slate-900 border-b border-slate-800 sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            <Zap className="w-5 h-5 fill-emerald-400" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-slate-100 text-lg tracking-tight">Newtonite</span>
              <span className="text-xs font-mono uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-1.5 py-0.5 rounded">
                OPS PRESSURE
              </span>
            </div>
            <p className="text-xs text-slate-400">Concurrency &amp; Cross-Team Coordination</p>
          </div>
        </div>

        {/* Right side / User Info */}
        <div className="flex items-center space-x-4">
          <button
            onClick={onRefresh}
            disabled={isFetching}
            className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors title='Refresh Work Items'"
          >
            <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin text-emerald-400' : ''}`} />
          </button>

          {currentUser ? (
            <div className="flex items-center space-x-3">
              <div className="text-right hidden sm:block">
                <div className="text-sm font-medium text-slate-200">{currentUser.full_name}</div>
                <div className="text-xs text-slate-400 font-mono">
                  {currentUser.roles?.map(r => `${r.team_name}: ${r.role}`).join(' • ') || 'No Teams'}
                </div>
              </div>
              <button
                onClick={onOpenLogin}
                className="px-2.5 py-1 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 transition-colors"
                title="Switch demo account"
              >
                Switch Role
              </button>
              <button
                onClick={onLogout}
                className="p-2 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-colors"
                title="Sign out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <button
              onClick={onOpenLogin}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm rounded-lg transition-colors flex items-center space-x-1.5 shadow-sm"
            >
              <User className="w-4 h-4" />
              <span>Select Demo Account</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
