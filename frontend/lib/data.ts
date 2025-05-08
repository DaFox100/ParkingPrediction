import type { GarageData, RawDataPoint, HourlyData } from "./types"

const API_BASE_URL = 'http://127.0.0.1:8000/api';

// Get parking data from the API
export async function getParkingData(date?: string): Promise<GarageData[]> {
  const selectedDate = date || new Date().toISOString().split('T')[0]
  const garages = ['north', 'west', 'south', 'south_campus']
  const names = ['North', 'West', 'South', 'SouthCampus']
  
  // Check if we're viewing today's data or future data
  const today = new Date()
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
  const isToday = selectedDate === todayStr
  const isFuture = selectedDate > todayStr
  
  // For future dates, we don't need to make any API calls
  if (isFuture) {
    const garageDataPromises = garages.map(async (id) => {
      try {
        const predictions = await getPredictionsTomorrow(id)
        const hourlyData = predictions.map((value: number, index: number) => {
          const hour = index.toString().padStart(2, '0')
          const time = `${hour}:00`
          return {
            time,
            occupancy: value,
            predictedOccupancy: value,
            forecast: true,
            rawData: []
          }
        })
        
        return {
          id,
          name: names[garages.indexOf(id)],
          currentOccupancy: predictions[0] || 0,
          trend: 0,
          trendDirection: "up" as const,
          nextHour: "00:00",
          trendData: [],
          hourlyData
        }
      } catch (error) {
        console.error(`Error fetching predictions for ${id}:`, error)
        return {
          id,
          name: names[garages.indexOf(id)],
          currentOccupancy: -1,
          trend: 0,
          trendDirection: "up" as const,
          nextHour: "00:00",
          trendData: [],
          hourlyData: []
        }
      }
    })
    return Promise.all(garageDataPromises)
  }

  // For today or past dates, make the API call
  const garageDataPromises = garages.map(async (id) => {
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/data?date=${selectedDate}&garage_id=${id}`)
      if (!response.ok) {
        throw new Error(`Failed to fetch data for ${id}`)
      }
      const data = await response.json()
      
      // Get predictions for this garage only if viewing today's data
      const predictions = isToday ? await getPredictions(id) : null
      
      // Convert hourly values to the format expected by the frontend
      const hourlyData = data.hourly_values.map((value: number | null, index: number) => {
        const hour = index.toString().padStart(2, '0')
        const time = `${hour}:00`
        const isFuture = isToday && new Date().getHours() < index
        const isCurrentHour = isToday && new Date().getHours() === index
        
        // If it's the current hour, use the most recent raw data point
        let occupancy = value
        if (isCurrentHour) {
          const currentHourRawData = data.raw_data.filter((point: RawDataPoint) => 
            point.time.startsWith(`${hour}:`)
          )
          if (currentHourRawData.length > 0) {
            // Use the most recent raw data point
            occupancy = currentHourRawData[currentHourRawData.length - 1].value
          } else if (value === null) {
            // If no raw data, fall back to previous hour's data
            const prevHour = (index - 1 + 24) % 24 // Handle wrap-around at midnight
            occupancy = data.hourly_values[prevHour]
          }
        }
        
        // If still null, use predictions for future hours or 0 for past hours
        occupancy = occupancy !== null ? occupancy : (isFuture && predictions ? predictions[index] : 0)
        
        return {
          time,
          occupancy,
          predictedOccupancy: predictions ? predictions[index] : null,
          forecast: isFuture,
          rawData: data.raw_data.filter((point: RawDataPoint) => 
            point.time.startsWith(`${hour}:`)
          )
        }
      })
      
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
      return {
        id,
        name: names[garages.indexOf(id)],
        currentOccupancy: -1,
        trend: 0,
        trendDirection: "up" as const,
        nextHour: "00:00",
        trendData: [],
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

// Get the latest update timestamp from the API
export async function getLatestUpdate(): Promise<string> {
  try {
    const response = await fetch('http://127.0.0.1:8000/api/latest-update')
    if (!response.ok) {
      throw new Error('Failed to fetch latest update timestamp')
    }
    const data = await response.json()
    return data.timestamp
  } catch (error) {
    console.error('Error fetching latest update timestamp:', error)
    return new Date().toISOString() // Return current time as fallback
  }
}

export async function getPredictions(garage: string): Promise<number[]> {
  const response = await fetch(`${API_BASE_URL}/predictions/${garage}`);
  if (!response.ok) throw new Error('Failed to fetch predictions');
  return response.json();
}

export async function getPredictionsTomorrow(garage: string): Promise<number[]> {
  const response = await fetch(`${API_BASE_URL}/predictions-tomorrow/${garage}`);
  if (!response.ok) throw new Error('Failed to fetch tomorrow\'s predictions');
  return response.json();
}

export async function getAverageFullness(garageId: string, selectedDate: string): Promise<number[]> {
  try {
    const date = new Date(selectedDate)
    const dayOfWeek = date.getDay() // 0 = Monday, 1 = Tuesday, etc.

    const response = await fetch(`http://127.0.0.1:8000/api/average-fullness/${garageId}/${dayOfWeek}`)
    if (!response.ok) {
      throw new Error(`Failed to fetch average fullness for ${garageId}`)
    }
    return await response.json()
  } catch (error) {
    console.error(`Error fetching average fullness for ${garageId}:`, error)
    return Array(24).fill(0) // Return zeros as fallback
  }
}

export async function getWeather(): Promise<{ temperature: number; condition: string }> {
  try {
    const response = await fetch('http://127.0.0.1:8000/api/weather')
    if (!response.ok) {
      throw new Error('Failed to fetch weather data')
    }
    return await response.json()
  } catch (error) {
    console.error('Error fetching weather data:', error)
    return { temperature: 0, condition: 'unknown' }
  }
}