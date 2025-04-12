export interface GarageData {
  id: string
  name: string
  currentOccupancy: number
  trend: number
  trendDirection: "up" | "down"
  nextHour: string
  trendData: { time: string; value: number }[]
  hourlyData: HourlyData[]
}

export interface HourlyData {
  time: string
  occupancy: number
  forecast?: boolean
}
