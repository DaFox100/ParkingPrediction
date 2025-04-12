"use client"

import { useState, useEffect } from "react"
import ParkingGarageCard from "@/components/parking-garage-card"
import { getParkingData } from "@/lib/data"
import type { GarageData } from "@/lib/types"

export default function ParkingDashboard() {
  const [parkingData, setParkingData] = useState<GarageData[]>([])
  const [expandedGarageId, setExpandedGarageId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadData() {
      const data = await getParkingData()
      setParkingData(data)
      setLoading(false)
    }

    loadData()
  }, [])

  const handleGarageClick = (id: string) => {
    setExpandedGarageId(expandedGarageId === id ? null : id)
  }

  const handleRefresh = async () => {
    setLoading(true)
    const data = await getParkingData()
    setParkingData(data)
    setLoading(false)
  }

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-4">
      {parkingData.map((garage) => (
        <ParkingGarageCard
          key={garage.id}
          garage={garage}
          isExpanded={expandedGarageId === garage.id}
          onGarageClick={handleGarageClick}
          onRefresh={handleRefresh}
        />
      ))}
    </div>
  )
}
