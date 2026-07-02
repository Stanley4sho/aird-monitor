import { sourceClass, sourceLabel } from "../utils/format";
import type { SourceHealth } from "../utils/types";

interface StatusPillProps {
  status?: SourceHealth;
}

export function StatusPill({ status }: StatusPillProps) {
  return (
    <span className={`inline-flex items-center rounded border px-2 py-1 text-xs font-medium ${sourceClass(status)}`}>
      {sourceLabel(status)}
    </span>
  );
}
