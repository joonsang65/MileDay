import { type MouseEvent, type ReactNode, useEffect } from "react";
import { X } from "lucide-react";

type FloatingPanelProps = {
  title: string;
  subtitle?: string;
  children: ReactNode;
  footer?: ReactNode;
  onClose: () => void;
  labelledBy?: string;
  placement?: "side" | "center";
  chrome?: "banded" | "plain";
  closeLabel?: string;
  className?: string;
};

export function FloatingPanel({
  title,
  subtitle,
  children,
  footer,
  onClose,
  labelledBy = "floating-panel-title",
  placement = "side",
  chrome = "banded",
  closeLabel = "닫기",
  className = "",
}: FloatingPanelProps) {
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose]);

  function handleBackdropClick(event: MouseEvent<HTMLDivElement>) {
    if (event.target === event.currentTarget) {
      onClose();
    }
  }

  return (
    <div className={`floating-layer ${placement}`} role="presentation" onClick={handleBackdropClick}>
      <section className={`floating-panel ${chrome} ${className}`.trim()} role="dialog" aria-modal="false" aria-labelledby={labelledBy}>
        <header className="floating-panel-header">
          <div className="floating-panel-title-row">
            <h2 id={labelledBy}>{title}</h2>
            {subtitle ? <span className="floating-panel-subtitle">{subtitle}</span> : null}
          </div>
          <button type="button" className="icon-button compact-icon" onClick={onClose} title={closeLabel}>
            <X size={16} aria-hidden="true" />
          </button>
        </header>
        <div className="floating-panel-body">{children}</div>
        {footer ? <footer className="floating-panel-footer">{footer}</footer> : null}
      </section>
    </div>
  );
}
