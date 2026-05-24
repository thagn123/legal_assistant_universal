import React from 'react';
import { CheckCircle2, XCircle, X } from 'lucide-react';
import type { Toast } from '../../lib/useToast';

interface Props {
  toasts: Toast[];
  dismiss: (id: string) => void;
}

export function ToastContainer({ toasts, dismiss }: Props) {
  if (toasts.length === 0) return null;
  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 pointer-events-none">
      {toasts.map(t => (
        <div
          key={t.id}
          className="pointer-events-auto flex items-center gap-2.5 px-4 py-3 rounded-xl shadow-lg border text-sm font-semibold animate-in slide-in-from-bottom-2 duration-200
            bg-legal-navy/95 backdrop-blur border-white/10 text-white"
        >
          {t.type === 'success'
            ? <CheckCircle2 size={15} className="text-green-400 shrink-0" />
            : <XCircle size={15} className="text-red-400 shrink-0" />
          }
          <span>{t.message}</span>
          <button
            onClick={() => dismiss(t.id)}
            className="ml-1 text-slate-400 hover:text-white transition-colors"
          >
            <X size={13} />
          </button>
        </div>
      ))}
    </div>
  );
}
