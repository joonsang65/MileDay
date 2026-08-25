export const RESIZE_DIRECTIONS = ["n", "e", "s", "w", "ne", "nw", "se", "sw"] as const;

export type ResizeDirection = (typeof RESIZE_DIRECTIONS)[number];

export function isResizeDirection(value: unknown): value is ResizeDirection {
  return typeof value === "string" && RESIZE_DIRECTIONS.includes(value as ResizeDirection);
}
