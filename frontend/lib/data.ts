import type { GarageData, RawDataPoint, HourlyData } from "./types"

// Get parking data from the API
export async function getParkingData(date?: string): Promise<GarageData[]> {
  const selectedDate = date || new Date().toISOString().split('T')[0]
  const garages = ['north', 'west', 'south', 'south_campus']
  const names = ['North', 'West', 'South', 'SouthCampus']
  
  const garageDataPromises = garages.map(async (id) => {
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/data?date=${selectedDate}&garage_id=${id}`)
      if (!response.ok) {
        throw new Error(`Failed to fetch data for ${id}`)
      }
      const data = await response.json()
      
      // Convert hourly values to the format expected by the frontend
      const hourlyData = data.hourly_values.map((value: number | null, index: number) => ({
        time: `${index.toString().padStart(2, '0')}:00`,
        occupancy: value || 0,
        forecast: false,
        rawData: data.raw_data.filter((point: RawDataPoint) => 
          point.time.startsWith(`${index.toString().padStart(2, '0')}:`)
        )
      }))
      
      // Calculate current occupancy and trend
      const currentHour = new Date().getHours()
      const currentHourStr = currentHour.toString().padStart(2, '0') + ':00'
      const currentData = hourlyData.find((d: HourlyData) => d.time === currentHourStr)
      const nextHourData = hourlyData.find((d: HourlyData) => d.time === 
        ((currentHour + 1) % 24).toString().padStart(2, '0') + ':00'
      )
      
      const currentOccupancy = currentData?.occupancy || 0
      const trend = nextHourData ? nextHourData.occupancy - currentOccupancy : 0
      
      return {
        id,
        name: names[garages.indexOf(id)],
        currentOccupancy,
        trend: Math.abs(trend),
        trendDirection: trend >= 0 ? "up" as const : "down" as const,
        nextHour: nextHourData?.time || "00:00",
        trendData: generateTrendData(currentOccupancy, trend),
        hourlyData
      }
    } catch (error) {
      console.error(`Error fetching data for ${id}:`, error)
      // Return mock data if API fails
      return {
        id,
        name: names[garages.indexOf(id)],
        currentOccupancy: 50,
        trend: 0,
        trendDirection: "up" as const,
        nextHour: "00:00",
        trendData: generateTrendData(50, 0),
        hourlyData: []
      }
    }
  })

  return Promise.all(garageDataPromises)
}

// Get garage data by ID from the API
export async function getGarageById(id: string): Promise<GarageData | undefined> {
  const garages = await getParkingData()
  return garages.find((garage) => garage.id === id)
}


// Get available dates from the API
export async function getAvailableDates(): Promise<string[]> {
  try {
    const response = await fetch('http://127.0.0.1:8000/api/dates')
    if (!response.ok) {
      throw new Error('Failed to fetch available dates')
    }
    return await response.json()
  } catch (error) {
    console.error('Error fetching available dates:', error)
    // Return today's date as fallback
    return [new Date().toISOString().split('T')[0]]
  }
}

// Generate mock trend data
function generateTrendData(current: number, trend: number) {
  const points = 10
  const data = []

  // Generate past data points
  for (let i = 0; i < points; i++) {
    const factor = i / points
    const value = trend > 0 ? current - trend * (1 - factor) : current + Math.abs(trend) * (1 - factor)

    data.push({
      time: `${i}`,
      value: Math.max(0, Math.min(100, value)),
    })
  }

  // Add forecast points (dashed line in the UI)
  for (let i = 0; i < 3; i++) {
    const factor = i / 3
    const value = trend > 0 ? current + trend * factor : current - Math.abs(trend) * factor

    data.push({
      time: `${points + i}`,
      value: Math.max(0, Math.min(100, value)),
    })
  }

  return data
}