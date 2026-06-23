interface CalendarHeaderProps {
  label: string;
  onPreviousMonth: () => void;
  onNextMonth: () => void;
}

export function CalendarHeader({
  label,
  onPreviousMonth,
  onNextMonth,
}: CalendarHeaderProps) {
  return (
    <div className="flex items-center justify-between px-1">
      <button
        aria-label="Previous month"
        className="app-no-drag grid h-7 w-7 place-items-center rounded border border-zinc-700 text-sm text-zinc-300 hover:bg-zinc-800"
        type="button"
        onClick={onPreviousMonth}
      >
        &lt;
      </button>
      <div className="text-sm font-semibold text-zinc-100">{label}</div>
      <button
        aria-label="Next month"
        className="app-no-drag grid h-7 w-7 place-items-center rounded border border-zinc-700 text-sm text-zinc-300 hover:bg-zinc-800"
        type="button"
        onClick={onNextMonth}
      >
        &gt;
      </button>
    </div>
  );
}
