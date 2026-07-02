import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import type { HistoryPoint } from "../utils/types";
import { formatDateTime, formatNumber } from "../utils/format";

interface RdmHistoryChartProps {
  data: HistoryPoint[];
}

export function RdmHistoryChart({ data }: RdmHistoryChartProps) {
  const chartData = data.map((point) => ({
    ...point,
    label: formatDateTime(point.as_of)
  }));

  return (
    <div className="h-[320px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 12, right: 16, bottom: 8, left: -18 }}>
          <CartesianGrid stroke="#e2e8f0" strokeDasharray="4 4" />
          <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={24} stroke="#64748b" />
          <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} stroke="#64748b" />
          <Tooltip
            formatter={(value: number) => formatNumber(value, 1)}
            labelClassName="text-slate-700"
            contentStyle={{ borderRadius: 8, borderColor: "#cbd5e1" }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line
            type="monotone"
            dataKey="ai_rdm_score"
            name="AI-RDM"
            stroke="#0f766e"
            strokeWidth={3}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="supply_chain_revenue"
            name="供應鏈營收"
            stroke="#2563eb"
            strokeWidth={2}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="hyperscaler_capex"
            name="Hyperscaler Capex"
            stroke="#a855f7"
            strokeWidth={2}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="market_confirmation"
            name="市場確認"
            stroke="#f59e0b"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
