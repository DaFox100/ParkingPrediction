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
  isTodayMode: boolean
  onModeChange: (mode: 'today' | 'historical') => void
}

export default function DetailedGarageChart({ data, selectedDate, isTodayMode, onModeChange }: DetailedGarageChartProps) {
  const today = new Date()
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
  const isToday = selectedDate === todayStr

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
            className={`px-4 py-2 ${isTodayMode ? "bg-blue-600" : "bg-[#333842] hover:bg-[#3b82f6]"} transition-colors`}
            onClick={() => onModeChange('today')}
          >
            Today
          </button>
          <button
            className={`px-4 py-2 ${!isTodayMode ? "bg-blue-600" : "bg-[#333842] hover:bg-[#3b82f6]"} transition-colors`}
            onClick={() => onModeChange('historical')}
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
                const isForecast = entry.forecast || (isToday && entry.time > currentHourStr)
                const isHighOccupancy = entry.occupancy >= 90
                const isMediumOccupancy = entry.occupancy >= 80 && entry.occupancy < 90
                
                let fillColor = isToday ? "#3b82f6" : "#4b5563" // blue or gray
                if (isHighOccupancy) {
                  fillColor = isToday ? "#ef4444" : "#7f1d1d" // red or dark red
                } else if (isMediumOccupancy) {
                  fillColor = isToday ? "#f97316" : "#7c2d12" // orange or dark orange
                }

                return (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={isForecast ? "url(#pattern-forecast)" : fillColor} 
                  />
                )
              })}
            </Bar>
            {isToday && (
              <ReferenceLine
                x={formatTime(currentHourStr)}
                stroke="#ffffff"
                strokeWidth={2}
                label={<Label value="Current" position="top" fill="#ffffff" />}
              />
            )}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
