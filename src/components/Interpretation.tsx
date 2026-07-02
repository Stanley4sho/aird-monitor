import { FileText } from "lucide-react";

interface InterpretationProps {
  text: string;
}

export function Interpretation({ text }: InterpretationProps) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start gap-3">
        <span className="rounded-lg bg-teal-50 p-2 text-teal-700">
          <FileText className="h-5 w-5" />
        </span>
        <div>
          <h2 className="text-base font-semibold text-slate-950">00988A 解讀</h2>
          <p className="mt-2 text-base leading-7 text-slate-700">{text}</p>
        </div>
      </div>
    </section>
  );
}
