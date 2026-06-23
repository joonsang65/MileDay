import type { PropsWithChildren } from 'react';

export function WidgetShell({ children }: PropsWithChildren) {
  return <main className="min-h-screen bg-slate-50 text-slate-950">{children}</main>;
}

