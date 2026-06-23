import { WidgetShell } from './components/layout/WidgetShell';

export default function App() {
  return (
    <WidgetShell>
      <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center">
        <h1 className="text-xl font-semibold text-slate-950">MileDay</h1>
        <p className="text-sm leading-6 text-slate-600">
          Electron + React + TypeScript setup is ready.
        </p>
      </div>
    </WidgetShell>
  );
}

