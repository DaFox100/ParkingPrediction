import type { GarageData } from "./types"

// Mock data - in a real app, this would come from your API
export async function getParkingData(): Promise<GarageData[]> {
  // Simulate API call
  await new Promise((resolve) => setTimeout(resolve, 500))

  return [
    {
      id: "north",
      name: "North",
      currentOccupancy: 69,
      trend: 15,
      trendDirection: "down",
      nextHour: "5PM",
      trendData: generateTrendData(69, -15),
      hourlyData: generateHourlyData("north"),
    },
    {
      id: "west",
      name: "West",
      currentOccupancy: 34,
      trend: 3,
      trendDirection: "up",
      nextHour: "5PM",
      trendData: generateTrendData(34, 3),
      hourlyData: generateHourlyData("west"),
    },
    {
      id: "south",
      name: "South",
      currentOccupancy: 81,
      trend: 24,
      trendDirection: "down",
      nextHour: "5PM",
      trendData: generateTrendData(81, -24),
      hourlyData: generateHourlyData("south"),
    },
    {
      id: "southcampus",
      name: "SouthCampus",
      currentOccupancy: 21,
      trend: 20,
      trendDirection: "down",
      nextHour: "23:00",
      trendData: generateTrendData(21, -20),
      hourlyData: generateHourlyData("southcampus"),
    },
  ]
}

export async function getGarageById(id: string): Promise<GarageData | undefined> {
  const garages = await getParkingData()
  return garages.find((garage) => garage.id === id)
}

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

function generateHourlyData(garageId: string) {
  const hours = [
    "00:00",
    "01:00",
    "02:00",
    "03:00",
    "04:00",
    "05:00",
    "06:00",
    "07:00",
    "08:00",
    "09:00",
    "10:00",
    "11:00",
    "12:00",
    "13:00",
    "14:00",
    "15:00",
    "16:00",
    "17:00",
    "18:00",
    "19:00",
    "20:00",
    "21:00",
    "22:00",
    "23:00",
  ]

  // Different patterns for different garages
  const patterns = {
    north: [2, 3, 5, 12, 40, 60, 75, 85, 87, 80, 75, 70, 60, 45, 40, 25, 15, 5],
    west: [5, 7, 10, 15, 25, 30, 32, 34, 38, 35, 30, 28, 25, 20, 15, 10, 8, 5],
    south: [3, 5, 8, 20, 45, 65, 75, 81, 78, 75, 70, 65, 55, 45, 35, 25, 15, 5],
    southcampus: [1, 2, 3, 5, 10, 15, 18, 20, 21, 19, 17, 15, 12, 10, 8, 5, 3, 1],
  }

  const pattern = patterns[garageId as keyof typeof patterns] || patterns.north
  const currentHour = new Date().getHours()

  return hours.map((time, index) => {
    // Use pattern for first 18 hours, then zeros for remaining hours
    const occupancy = index < pattern.length ? pattern[index] : 0

    return {
      time,
      occupancy,
      // Mark as forecast for future hours
      forecast: index > currentHour,
    }
  })
}
