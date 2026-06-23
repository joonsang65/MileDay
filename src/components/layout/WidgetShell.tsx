import type { PointerEvent, PropsWithChildren } from 'react';
import { useRef } from 'react';

const minWidgetWidth = 320;
const minWidgetHeight = 420;

export function WidgetShell({ children }: PropsWithChildren) {
  const resizeStateRef = useRef<{
    startX: number;
    startY: number;
    startWidth: number;
    startHeight: number;
  } | null>(null);

  const handleResizePointerDown = async (
    event: PointerEvent<HTMLDivElement>,
  ) => {
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);

    const bounds = await window.mileDayWidget?.getWindowBounds();

    resizeStateRef.current = {
      startX: event.clientX,
      startY: event.clientY,
      startWidth: bounds?.width ?? window.innerWidth,
      startHeight: bounds?.height ?? window.innerHeight,
    };
  };

  const handleResizePointerMove = (event: PointerEvent<HTMLDivElement>) => {
    const resizeState = resizeStateRef.current;

    if (!resizeState) {
      return;
    }

    const nextWidth = Math.max(
      minWidgetWidth,
      resizeState.startWidth + event.clientX - resizeState.startX,
    );
    const nextHeight = Math.max(
      minWidgetHeight,
      resizeState.startHeight + event.clientY - resizeState.startY,
    );

    void window.mileDayWidget?.resizeWindow(nextWidth, nextHeight);
  };

  const handleResizePointerEnd = (event: PointerEvent<HTMLDivElement>) => {
    resizeStateRef.current = null;

    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  };

  return (
    <main className="h-screen overflow-hidden bg-zinc-950 p-2 text-zinc-50">
      <section className="relative mx-auto flex h-full w-full flex-col overflow-hidden rounded-lg border border-zinc-800 bg-zinc-900 shadow-2xl">
        {children}
        <div
          aria-label="Resize widget"
          className="app-no-drag widget-resize-handle"
          role="separator"
          onPointerCancel={handleResizePointerEnd}
          onPointerDown={(event) => void handleResizePointerDown(event)}
          onPointerMove={handleResizePointerMove}
          onPointerUp={handleResizePointerEnd}
        />
      </section>
    </main>
  );
}
