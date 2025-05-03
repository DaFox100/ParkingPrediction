"use client"

import { useEffect, useState } from "react"
import { getLatestUpdate } from "@/lib/data"

export default function Header() {
  const [lastUpdated, setLastUpdated] = useState<string>("")

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

  return (
    <header className="p-4">
      <h1 className="text-2xl font-bold">SJ Parking</h1>
      {lastUpdated && (
        <p className="text-sm text-gray-400">Last Updated: {lastUpdated}</p>
      )}
    </header>
  )
} 