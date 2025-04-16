"use client"

import { Line, LineChart, ResponsiveContainer } from "recharts"

interface TrendChartProps {
  data: { time: string; value: number }[]
  direction: "up" | "down"
}

export default function TrendChart({ data, direction }: TrendChartProps) {
  const color = direction === "down" ? "#10b981" : "#ef4444"

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data}>
        <Line type="monotone" dataKey="value" stroke={color} strokeWidth={2} dot={false} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}
