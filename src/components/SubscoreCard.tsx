import { ArrowDownRight, ArrowRight, ArrowUpRight } from "lucide-react";
import { formatNumber, scoreColor } from "../utils/format";

interface SubscoreCardProps {
  title: string;
  score: number;
  weight: string;
  description: string;
}

export function SubscoreCard({ title, score, weight, description }: SubscoreCardProps) {
  const color = scoreColor(score);
  const Icon = score >= 55 ? ArrowUpRight : score < 45 ? ArrowDownRight : ArrowRight;

  return (
    <article className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-950">{title}</h2>
          <p className="mt-1 text-xs text-slate-500">權重 {weight}</p>
        </div>
        <span className="rounded-lg border border-slate-200 bg-slate-50 p-2" style={{ color }}>
          <Icon className="h-5 w-5" />
        </span>
      </div>
      <div className="flex items-end gap-2">
        <span className="text-4xl font-bold text-slate-950">{formatNumber(score, 1)}</span>
        <span className="pb-1 text-sm font-medium text-slate-500">分</span>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
        <div className="h-full rounded-full" style={{ width: `${Math.max(0, Math.min(100, score))}%`, background: color }} />
      </div>
      <p className="mt-3 text-sm leading-5 text-slate-600">{description}</p>
    </article>
  );
}
