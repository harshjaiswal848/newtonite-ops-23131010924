import React from 'react';
import { AlertTriangle, RefreshCw, X, ShieldAlert } from 'lucide-react';

export default function ConflictBanner({ conflictInfo, onDismiss, onReload }) {
  if (!conflictInfo) return null;

  const isForbidden = conflictInfo.status === 403;
  const isVersionConflict = conflictInfo.status === 409 && conflictInfo.type === 'version';
  const isClaimConflict = conflictInfo.status === 409 && conflictInfo.type === 'claim';

  return (
    <div className={`p-4 rounded-xl border mb-6 shadow-lg animate-in fade-in slide-in-from-top-2 duration-300 ${
      isForbidden
        ? 'bg-amber-950/40 border-amber-500/40 text-amber-200'
        : 'bg-rose-950/40 border-rose-500/40 text-rose-200'
    }`}>
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3">
          <div className="p-1 rounded bg-black/30 shrink-0 mt-0.5">
            {isForbidden ? (
              <ShieldAlert className="w-5 h-5 text-amber-400" />
            ) : (
              <AlertTriangle className="w-5 h-5 text-rose-400" />
            )}
          </div>
          <div className="space-y-1">
            <h4 className="font-semibold text-sm">
              {isForbidden && 'Authorization Denied (403 Forbidden)'}
              {isVersionConflict && 'Optimistic Lock Version Conflict (409 Conflict)'}
              {isClaimConflict && 'Race Condition Collision (409 Conflict)'}
              {!isForbidden && !isVersionConflict && !isClaimConflict && 'Operation Rejected by Server'}
            </h4>
            <p className="text-xs opacity-90 leading-relaxed">
              {conflictInfo.message}
            </p>
            {conflictInfo.detail && (
              <div className="text-[11px] font-mono bg-black/30 p-2 rounded border border-white/5 mt-2">
                {typeof conflictInfo.detail === 'object' ? JSON.stringify(conflictInfo.detail, null, 2) : conflictInfo.detail}
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center space-x-2 shrink-0 ml-4">
          {onReload && (
            <button
              onClick={onReload}
              className="px-3 py-1.5 bg-white/10 hover:bg-white/20 text-xs font-medium rounded-lg transition-colors flex items-center space-x-1.5"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Reload Latest</span>
            </button>
          )}
          <button
            onClick={onDismiss}
            className="p-1 hover:bg-white/10 rounded transition-colors text-white/60 hover:text-white"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
