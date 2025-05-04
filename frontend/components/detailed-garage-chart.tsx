"use client"

import { useState } from "react"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Label,
  Cell,
} from "recharts"
import type { HourlyData } from "@/lib/types"
import { formatTime } from "@/lib/utils"

interface DetailedGarageChartProps {
  data: HourlyData[]
  selectedDate: string
}

export default function DetailedGarageChart({ data, selectedDate }: DetailedGarageChartProps) {
  const today = new Date()
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
  const isToday = selectedDate === todayStr
  const viewMode = isToday ? "today" : "historical"

  // Find the highest occupancy point to highlight
  const maxOccupancy = data.reduce((max, point) => (point.occupancy > max.occupancy ? point : max), data[0])

  // Find current hour for reference line
  const currentHour = new Date().getHours()
  const currentHourStr = `${currentHour.toString().padStart(2, '0')}:00`

  // Format the data with AM/PM times
  const formattedData = data.map(entry => ({
    ...entry,
    displayTime: formatTime(entry.time)
  }))

  return (
    <div>
      <div className="flex justify-end mb-4">
        <div className="flex rounded-md overflow-hidden">
          <button
            className={`px-4 py-2 cursor-default ${viewMode === "today" ? "bg-blue-600" : "bg-[#333842]"}`}
          >
            Today
          </button>
          <button
            className={`px-4 py-2 cursor-default ${viewMode === "historical" ? "bg-blue-600" : "bg-[#333842]"}`}
          >
            Historical
          </button>
        </div>
      </div>

      <div className="h-[400px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={formattedData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
            <defs>
              <pattern
                id="pattern-forecast"
                patternUnits="userSpaceOnUse"
                width="10"
                height="10"
                patternTransform="rotate(45)"
              >
                <line x1="0" y1="0" x2="0" y2="10" stroke="#3b82f6" strokeWidth="4" strokeOpacity="0.5" />
              </pattern>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#333842" />
            <XAxis 
              dataKey="displayTime" 
              tick={{ fill: "#9ca3af" }} 
              axisLine={{ stroke: "#333842" }} 
              tickLine={false} 
            />
            <YAxis tick={{ fill: "#9ca3af" }} axisLine={{ stroke: "#333842" }} tickLine={false} domain={[0, 100]} />
            <Tooltip
              contentStyle={{ backgroundColor: "#1a1d24", borderColor: "#333842" }}
              labelStyle={{ color: "white" }}
              itemStyle={{ color: "white" }}
              formatter={(value) => [`${value}%`, "Occupancy"]}
            />
            <Bar dataKey="occupancy" radius={[4, 4, 0, 0]}>
              {formattedData.map((entry, index) => {
                const isForecast = entry.forecast || (viewMode === "today" && entry.time > currentHourStr)
                return <Cell key={`cell-${index}`} fill={isForecast ? "url(#pattern-forecast)" : "#3b82f6"} />
              })}
            </Bar>
            {viewMode === "today" && (
              <ReferenceLine
                x={formatTime(currentHourStr)}
                stroke="#ffffff"
                strokeWidth={2}
                label={<Label value="Current" position="top" fill="#ffffff" />}
              />
            )}
            <ReferenceLine
              x={formatTime(maxOccupancy.time)}
              stroke="#ef4444"
              strokeDasharray="3 3"
              label={<Label value={`${formatTime(maxOccupancy.time)}\n${maxOccupancy.occupancy}%`} position="top" fill="#ef4444" />}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
