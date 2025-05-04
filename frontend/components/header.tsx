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
    <header className="p-2 flex flex-col items-center gap-1 bg-background w-full">
      <h1 className="text-4xl md:text-5xl font-medium tracking-tight">SJ Parking</h1>
      {lastUpdated && (
        <p className="text-lg md:text-xl text-gray-400">Last Updated: {lastUpdated}</p>
      )}
    </header>
  )
} 