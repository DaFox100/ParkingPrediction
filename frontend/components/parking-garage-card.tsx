"use client"
import { RefreshCw, Calendar } from "lucide-react"
import { useState, useEffect } from "react"
import type { GarageData } from "@/lib/types"
import TrendChart from "./trend-chart"
import DetailedGarageChart from "./detailed-garage-chart"
import { formatDate } from "@/lib/utils"
import { getAvailableDates, getGarageById, getAverageFullness } from "@/lib/data"

interface ParkingGarageCardProps {
  garage: GarageData
  isExpanded: boolean
  onGarageClick: (id: string) => void
  onRefresh: () => void
  selectedDate: string
  onDateChange: (date: string) => void
  availableDates: string[]
  isTodayMode: boolean
  onModeChange: (mode: 'today' | 'historical') => void
  averageFullness: number[]
}

export default function ParkingGarageCard({ 
  garage, 
  isExpanded, 
  onGarageClick, 
  onRefresh,
  selectedDate,
  onDateChange,
  availableDates,
  isTodayMode,
  onModeChange,
  averageFullness
}: ParkingGarageCardProps) {
  const { id, name, currentOccupancy, trend, trendDirection, nextHour } = garage
  const [garageData, setGarageData] = useState(garage)
  const [isLoading, setIsLoading] = useState(false)

  const today = new Date()
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
  const isToday = selectedDate === todayStr

  useEffect(() => {
    setGarageData(garage)
  }, [garage])

  const handleDateChange = async (date: string) => {
    onDateChange(date)
  }

  return (
    <div
      className={`bg-[#252830] rounded-3xl transition-all duration-500 ease-in-out overflow-hidden
        ${isExpanded ? "md:col-span-2 row-span-2" : ""}`}
    >
      {/* DO NOT USE h-full, it will cause the card to not show chart */}
      <div className="p-8 cursor-pointer hover:bg-[#2a2e38] transition-colors flex flex-col justify-between" onClick={() => onGarageClick(id)}>
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-full bg-blue-500 flex items-center justify-center">
            <span className="text-lg text-white font-semibold">P</span>
          </div>
          <h2 className="text-2xl md:text-3xl">{name}</h2>
          {isExpanded && (
            <div className="flex items-center gap-2 ml-auto">
              <p className={`text-4xl md:text-5xl leading-none ${!isToday ? "text-gray-400" : ""}`}>{garageData.currentOccupancy}%</p>
              {isToday && (
                <p className={`text-xl md:text-2xl ${garageData.trendDirection === "down" ? "text-green-500" : "text-red-500"}`}>
                  {garageData.trendDirection === "down" ? "-" : "+"}
                  {Math.abs(garageData.trend)}% next hour
                </p>
              )}
            </div>
          )}
        </div>

        {!isExpanded && (
          <div className="flex justify-between items-end mt-4">
            <div className="flex items-center gap-1">
              <div>
                <p className={`text-7xl md:text-8xl mb-2 leading-none ${!isToday ? "text-gray-400" : ""}`}>{garageData.currentOccupancy}%</p>
                {isToday && (
                  <p className={`text-2xl md:text-3xl ${garageData.trendDirection === "down" ? "text-green-500" : "text-red-500"}`}>
                    {garageData.trendDirection === "down" ? "-" : "+"}
                    {Math.abs(garageData.trend)}% next hour
                  </p>
                )}
              </div>
              <div className="w-60 h-32 relative ml-4 mb-10">
                <TrendChart 
                  rawData={garageData.hourlyData.flatMap(hour => hour.rawData || [])}
                  predictions={garageData.hourlyData.map(hour => hour.occupancy)}
                  direction={garageData.trendDirection} 
                />
              </div>
            </div>
          </div>
        )}
      </div>

      <div
        className={`overflow-hidden transition-all duration-500 ease-in-out
          ${isExpanded ? "max-h-[600px] opacity-100" : "max-h-0 opacity-0"}`}
      >
        <div className="p-6 pt-0 border-t border-[#333842] mt-2">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl">{name} Garage</h2>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 text-gray-400">
                <Calendar size={18} />
                <select
                  className="bg-[#1a1d24] text-gray-400 border border-[#333842] rounded px-2 py-1"
                  value={selectedDate}
                  onChange={(e) => handleDateChange(e.target.value)}
                  disabled={isLoading}
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
                disabled={isLoading}
              >
                <RefreshCw size={18} />
                <span>Refresh</span>
              </button>
            </div>
          </div>

          {isLoading ? (
            <div className="flex justify-center items-center h-[400px]">
              <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
            </div>
          ) : (
            <DetailedGarageChart 
              data={garageData.hourlyData} 
              selectedDate={selectedDate} 
              isTodayMode={isTodayMode}
              onModeChange={onModeChange}
              averageFullness={averageFullness}
              garageName={name}
            />
          )}
        </div>
      </div>
    </div>
  )
}