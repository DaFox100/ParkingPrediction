"use client"

import { useState, useEffect } from "react"
import ParkingGarageCard from "@/components/parking-garage-card"
import { getParkingData, getAvailableDates, getAverageFullness, getPredictionsTomorrow } from "@/lib/data"
import type { GarageData } from "@/lib/types"

export default function ParkingDashboard() {
  const [parkingData, setParkingData] = useState<GarageData[]>([])
  const [expandedGarageId, setExpandedGarageId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedDate, setSelectedDate] = useState<string>("")
  const [availableDates, setAvailableDates] = useState<string[]>([])
  const [isTodayMode, setIsTodayMode] = useState(true)
  const [averageFullness, setAverageFullness] = useState<Record<string, number[]>>({})
  const [tomorrowPredictions, setTomorrowPredictions] = useState<Record<string, number[]>>({})

  useEffect(() => {
    async function loadDates() {
      const dates = await getAvailableDates()
      // Sort dates in descending order (newest first)
      const sortedDates = dates.sort((a, b) => new Date(b).getTime() - new Date(a).getTime())
      setAvailableDates(sortedDates)
      
      // Set to today's date by default
      const today = new Date()
      const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
      setSelectedDate(todayStr)
    }
    loadDates()
  }, [])

  const fetchAverages = async (garages: GarageData[]) => {
    const avgFullnessPromises = garages.map(async (garage) => {
      const fullness = await getAverageFullness(garage.id, selectedDate)
      return { id: garage.id, fullness }
    })
    const avgFullnessResults = await Promise.all(avgFullnessPromises)
    const avgFullnessMap = avgFullnessResults.reduce((acc, { id, fullness }) => {
      acc[id] = fullness
      return acc
    }, {} as Record<string, number[]>)
    setAverageFullness(avgFullnessMap)
  }

  const fetchTomorrowPredictions = async (garages: GarageData[]) => {
    const predictionsPromises = garages.map(async (garage) => {
      const predictions = await getPredictionsTomorrow(garage.id)
      return { id: garage.id, predictions }
    })
    const predictionsResults = await Promise.all(predictionsPromises)
    const predictionsMap = predictionsResults.reduce((acc, { id, predictions }) => {
      acc[id] = predictions
      return acc
    }, {} as Record<string, number[]>)
    setTomorrowPredictions(predictionsMap)
  }

  useEffect(() => {
    async function loadData() {
      if (selectedDate) {
        setLoading(true)
        try {
          const today = new Date().toISOString().split('T')[0]
          const isTomorrow = selectedDate > today
          
          // For tomorrow, we'll use predictions
          const data = await getParkingData(selectedDate)
          setParkingData(data)
          
          // Only fetch averages for today or past dates
          if (!isTomorrow) {
            await fetchAverages(data)
          }
        } catch (error) {
          console.error('Error loading parking data:', error)
        } finally {
          setLoading(false)
        }
      }
    }

    loadData()
  }, [selectedDate]) // Only depend on selectedDate

  const handleGarageClick = (id: string) => {
    setExpandedGarageId(expandedGarageId === id ? null : id)
  }

  const handleRefresh = async () => {
    setLoading(true)
    try {
      const today = new Date().toISOString().split('T')[0]
      const isTomorrow = selectedDate > today
      
      const data = await getParkingData(selectedDate)
      setParkingData(data)
      
      // Only fetch averages for today or past dates
      if (!isTomorrow) {
        await fetchAverages(data)
      }
    } catch (error) {
      console.error('Error refreshing parking data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleModeChange = (mode: 'today' | 'historical' | 'future') => {
    if (availableDates.length < 2) return

    const today = new Date()
    const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`

    if (mode === 'today') {
      setIsTodayMode(true)
      setSelectedDate(todayStr)
    } else if (mode === 'future') {
      setIsTodayMode(false)
      const tomorrow = new Date()
      tomorrow.setDate(tomorrow.getDate() + 1)
      const tomorrowStr = `${tomorrow.getFullYear()}-${String(tomorrow.getMonth() + 1).padStart(2, '0')}-${String(tomorrow.getDate()).padStart(2, '0')}`
      setSelectedDate(tomorrowStr)
    } else {
      // For historical mode, don't change the date if one is already selected
      setIsTodayMode(false)
      if (!selectedDate || selectedDate === todayStr) {
        setSelectedDate(availableDates[1]) // Second most recent date
      }
    }
  }

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto relative">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {parkingData.map((garage) => (
          <div
            key={garage.id}
            className={`transition-all duration-500 ease-in-out ${
              expandedGarageId && expandedGarageId !== garage.id ? "hidden pointer-events-none" : ""
            } ${expandedGarageId === garage.id ? "md:col-span-2 row-span-2 absolute top-0 left-0 right-0" : ""}`}
          >
            <ParkingGarageCard
              garage={garage}
              isExpanded={expandedGarageId === garage.id}
              onGarageClick={handleGarageClick}
              onRefresh={handleRefresh}
              selectedDate={selectedDate}
              onDateChange={setSelectedDate}
              availableDates={availableDates}
              isTodayMode={isTodayMode}
              onModeChange={handleModeChange}
              averageFullness={averageFullness[garage.id] || []}
              tomorrowPredictions={tomorrowPredictions[garage.id] || []}
            />
          </div>
        ))}
      </div>
    </div>
  )
}
