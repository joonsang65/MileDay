import type { ReactNode } from "react";
import { X } from "lucide-react";

type FloatingPanelProps = {
  title: string;
  children: ReactNode;
  footer?: ReactNode;
  onClose: () => void;
  labelledBy?: string;
  placement?: "side" | "center";
  chrome?: "banded" | "plain";
  closeLabel?: string;
};

export function FloatingPanel({
  title,
  children,
  footer,
  onClose,
  labelledBy = "floating-panel-title",
  placement = "side",
  chrome = "banded",
  closeLabel = "닫기",
}: FloatingPanelProps) {
  return (
    <div className={`floating-layer ${placement}`} role="presentation">
      <section className={`floating-panel ${chrome}`} role="dialog" aria-modal="false" aria-labelledby={labelledBy}>
        <header className="floating-panel-header">
          <h2 id={labelledBy}>{title}</h2>
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
