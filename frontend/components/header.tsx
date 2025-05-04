"use client"

import { useState, useEffect } from "react"
import { getLatestUpdate, getWeather } from "@/lib/data"

export default function Header() {
  const [lastUpdated, setLastUpdated] = useState<string>("")
  const [weather, setWeather] = useState<{ temperature: number; condition: string } | null>(null)

  useEffect(() => {
    const fetchLastUpdated = async () => {
      const timestamp = await getLatestUpdate()
      const date = new Date(timestamp)
      setLastUpdated(date.toLocaleString())
    }
    
    fetchLastUpdated()
    // Update every minute
    const interval = setInterval(fetchLastUpdated, 60000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    const fetchWeather = async () => {
      const data = await getWeather()
      setWeather(data)
    }
    fetchWeather()
  }, [])

  const getWeatherIcon = (condition: string) => {
    const conditionLower = condition.toLowerCase()
    if (conditionLower.includes('sunny') || conditionLower.includes('clear')) return '☀️'
    if (conditionLower.includes('cloud')) return '☁️'
    if (conditionLower.includes('rain')) return '🌧️'
    if (conditionLower.includes('snow')) return '❄️'
    if (conditionLower.includes('thunder')) return '⛈️'
    return '🌤️'
  }

  return (
    <header className="bg-[#252830] py-4 px-6 mb-8 relative">
      <div className="max-w-7xl mx-auto flex justify-between items-center">
        <div className="flex items-center gap-4">
          <h1 className="text-3xl font-bold">SJ Parking</h1>
          {weather && (
            <div className="flex items-center gap-2 text-gray-400">
              <span className="text-2xl">{getWeatherIcon(weather.condition)}</span>
              <span>{weather.temperature}°F</span>
            </div>
          )}
        </div>
        <div className="absolute left-1/2 transform -translate-x-1/2 text-center">
          <h2 className="text-xl font-semibold">San Jose State University</h2>
          {lastUpdated && (
            <p className="text-md text-gray-400">Last Updated: {lastUpdated}</p>
          )}
        </div>
        <div className="w-24"></div>
      </div>
    </header>
  )
} 