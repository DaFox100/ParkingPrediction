"use client"

import { useState, useEffect } from "react"
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
import React from "react"

interface DetailedGarageChartProps {
  data: HourlyData[]
  selectedDate: string
  isTodayMode: boolean
  onModeChange: (mode: 'today' | 'historical' | 'future') => void
  averageFullness: number[]
  garageName: string
}

export default function DetailedGarageChart({ data, selectedDate, isTodayMode, onModeChange, averageFullness, garageName }: DetailedGarageChartProps) {
  const today = new Date()
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
  const isToday = selectedDate === todayStr
  const isFuture = selectedDate > todayStr

  // Automatically switch mode based on selected date
  useEffect(() => {
    if (isToday && !isTodayMode) {
      onModeChange('today')
    } else if (isFuture) {
      onModeChange('future')
    } else if (!isToday && !isFuture && isTodayMode) {
      // Only switch to historical mode if we're not already in it
      onModeChange('historical')
    }
  }, [selectedDate, isToday, isFuture, isTodayMode, onModeChange])

  // Find the highest occupancy point to highlight
  const maxOccupancy = data.reduce((max, point) => (point.occupancy > max.occupancy ? point : max), data[0])

  // Find current hour for reference line
  const currentHour = new Date().getHours()
  const currentHourStr = `${currentHour.toString().padStart(2, '0')}:00`

  // Find continuous high-occupancy periods
  const findHighOccupancyPeriods = () => {
    const periods: { start: string; end: string }[] = []
    let currentPeriod: { start: string; end: string } | null = null

    for (let i = 0; i < 24; i++) {
      const hour = i.toString().padStart(2, '0')
      const time = `${hour}:00`
      const displayTime = formatTime(time)
      const avg = averageFullness[i] || 0 // Add fallback for undefined

      if (avg >= 90) {
        if (!currentPeriod) {
          currentPeriod = { start: displayTime, end: displayTime }
        } else {
          currentPeriod.end = displayTime
        }
      } else if (currentPeriod) {
        periods.push(currentPeriod)
        currentPeriod = null
      }
    }

    // Add the last period if it exists
    if (currentPeriod) {
      periods.push(currentPeriod)
    }

    return periods
  }

  const highOccupancyPeriods = findHighOccupancyPeriods()

  // Format the data with AM/PM times
  const formattedData = data.map(entry => ({
    ...entry,
    displayTime: formatTime(entry.time),
    actualOccupancy: entry.occupancy,
    predictedOccupancy: entry.predictedOccupancy ?? entry.occupancy
  }))

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const entry = payload[0].payload
      const isForecast = entry.forecast || isFuture
      const isCurrentHour = isToday && entry.time === currentHourStr
      const isPastHour = isToday && entry.time < currentHourStr
      const hourIndex = parseInt(entry.time.split(':')[0])
      const average = averageFullness[hourIndex]
      const variance = entry.actualOccupancy - entry.predictedOccupancy
      const varianceText = variance > 0 ? `(+${variance}%)` : `(${variance}%)`

      return (
        <div className="bg-[#1a1d24] p-3 border border-[#333842] rounded">
          <p className="text-white text-2xl">{label}</p>
          {isForecast ? (
            <>
              <p className="text-blue-400 text-2xl">Predicted: {entry.predictedOccupancy}%</p>
              <p className="text-gray-400">Average: {average}%</p>
            </>
          ) : (isPastHour || isCurrentHour) ? (
            <>
              <p className="text-white text-2xl">Occupancy: {entry.actualOccupancy}%</p>
              <p className="text-blue-400">
                Predicted: {entry.predictedOccupancy}% <span className="text-yellow-400">{varianceText}</span>
              </p>
              <p className="text-gray-400">Average: {average}%</p>
            </>
          ) : (
            <>
              <p className="text-white text-2xl">Occupancy: {entry.actualOccupancy}%</p>
              <p className="text-gray-400">Average: {average}%</p>
            </>
          )}
        </div>
      )
    }
    return null
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-2">
          <h2 className="text-2xl"></h2>
          {garageName === "North" && (
            <span className="text-yellow-400 text-md">Floor 2 is Employees Only</span>
          )}
        </div>
        <div className="flex rounded-md overflow-hidden">
          <button
            className={`px-4 py-2 ${isFuture ? "bg-blue-600" : "bg-[#333842] hover:bg-[#3b82f6]"} transition-colors`}
            onClick={() => onModeChange('future')}
          >
            Future
          </button>
          <button
            className={`px-4 py-2 ${isTodayMode && !isFuture ? "bg-blue-600" : "bg-[#333842] hover:bg-[#3b82f6]"} transition-colors`}
            onClick={() => onModeChange('today')}
          >
            Today
          </button>
          <button
            className={`px-4 py-2 ${!isTodayMode && !isFuture ? "bg-blue-600" : "bg-[#333842]"} cursor-not-allowed opacity-50`}
            onClick={() => onModeChange('historical')}
            disabled
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
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="actualOccupancy" radius={[4, 4, 0, 0]}>
              {formattedData.map((entry, index) => {
                const isForecast = entry.forecast || isFuture
                const isCurrentHour = isToday && entry.time === currentHourStr
                const isHighOccupancy = entry.actualOccupancy >= 90
                const isMediumOccupancy = entry.actualOccupancy >= 80 && entry.actualOccupancy < 90
                
                let fillColor = isToday ? "#3b82f6" : "#4b5563" // blue or gray
                if (isHighOccupancy) {
                  fillColor = isToday ? "#ef4444" : "#7f1d1d" // red or dark red
                } else if (isMediumOccupancy) {
                  fillColor = isToday ? "#f97316" : "#7c2d12" // orange or dark orange
                }

                // If it's the current hour and we don't have data yet, use the predicted value
                const shouldUsePredicted = isCurrentHour && entry.actualOccupancy === 0 && entry.predictedOccupancy !== null

                return (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={isForecast || shouldUsePredicted ? "url(#pattern-forecast)" : fillColor} 
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
            {!isFuture && highOccupancyPeriods.length > 0 && highOccupancyPeriods.map((period, index) => {
              // Add safety check for period values
              if (!period?.start || !period?.end) return null;
              
              return [
                <ReferenceLine
                  key={`start-${index}`}
                  x={period.start}
                  stroke="#f97316"
                  strokeWidth={2}
                  strokeDasharray="3 3"
                  label={<Label value="( ! )" position="top" fill="#f97316" />}
                  ifOverflow="extendDomain"
                  alwaysShow={true}
                />,
                <ReferenceLine
                  key={`end-${index}`}
                  x={period.end}
                  stroke="#f97316"
                  strokeWidth={2}
                  strokeDasharray="3 3"
                  label={<Label value="( ! )" position="top" fill="#f97316" />}
                  ifOverflow="extendDomain"
                  alwaysShow={true}
                />
              ]
            })}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
