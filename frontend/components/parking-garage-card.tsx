"use client"
import { RefreshCw, Calendar } from "lucide-react"
import { useState, useEffect } from "react"
import type { GarageData } from "@/lib/types"
import TrendChart from "./trend-chart"
import DetailedGarageChart from "./detailed-garage-chart"
import { formatDate } from "@/lib/utils"
import { getAvailableDates } from "@/lib/data"

interface ParkingGarageCardProps {
  garage: GarageData
  isExpanded: boolean
  onGarageClick: (id: string) => void
  onRefresh: () => void
  selectedDate: string
  onDateChange: (date: string) => void
}

export default function ParkingGarageCard({ 
  garage, 
  isExpanded, 
  onGarageClick, 
  onRefresh,
  selectedDate,
  onDateChange
}: ParkingGarageCardProps) {
  const { id, name, currentOccupancy, trend, trendDirection, nextHour } = garage
  const [availableDates, setAvailableDates] = useState<string[]>([])

  useEffect(() => {
    async function loadDates() {
      const dates = await getAvailableDates()
      setAvailableDates(dates)
    }
    loadDates()
  }, [])

  return (
    <div
      className={`bg-[#252830] rounded-lg transition-all duration-500 ease-in-out overflow-hidden
        ${isExpanded ? "md:col-span-2 row-span-2" : ""}`}
    >
      <div className="p-6 cursor-pointer hover:bg-[#2a2e38] transition-colors" onClick={() => onGarageClick(id)}>
        <div className="flex items-center gap-2 mb-2">
          <div className="w-6 h-6 rounded-full bg-blue-500 flex items-center justify-center">
            <span className="text-xs text-white">P</span>
          </div>
          <h2 className="text-xl font-medium">{name}</h2>
        </div>

        <div className="flex justify-between items-end">
          <div>
            <p className="text-6xl font-bold mb-2">{currentOccupancy}%</p>
            <p className={`text-lg ${trendDirection === "down" ? "text-green-500" : "text-red-500"}`}>
              {trendDirection === "down" ? "-" : "+"}
              {Math.abs(trend)}% next hour
            </p>
          </div>

          <div className="w-32 h-16 relative">
            <TrendChart data={garage.trendData} direction={trendDirection} />
            <div className="absolute bottom-0 right-0 text-sm text-gray-400">{nextHour}</div>
          </div>
        </div>
      </div>

      <div
        className={`overflow-hidden transition-all duration-500 ease-in-out
          ${isExpanded ? "max-h-[600px] opacity-100" : "max-h-0 opacity-0"}`}
      >
        <div className="p-6 pt-0 border-t border-[#333842] mt-2">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-semibold">{name} Garage</h2>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 text-gray-400">
                <Calendar size={18} />
                <select
                  className="bg-[#1a1d24] text-gray-400 border border-[#333842] rounded px-2 py-1"
                  value={selectedDate}
                  onChange={(e) => onDateChange(e.target.value)}
                >
                  {availableDates.map((date) => (
                    <option key={date} value={date}>
                      {formatDate(new Date(date))}
                    </option>
                  ))}
                </select>
              </div>
              <button
                className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
                onClick={(e) => {
                  e.stopPropagation()
                  onRefresh()
                }}
              >
                <RefreshCw size={18} />
                <span>Refresh</span>
              </button>
            </div>
          </div>

          <DetailedGarageChart data={garage.hourlyData} selectedDate={selectedDate} />
        </div>
      </div>
    </div>
  )
}
