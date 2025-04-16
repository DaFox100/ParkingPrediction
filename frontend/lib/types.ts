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

// Should correspond to the data returned by the backend /backend/routes/data.py "DataResponse"
export interface RawDataPoint {
  time: string
  value: number
}

export interface HourlyData {
  time: string
  occupancy: number
  forecast?: boolean
  rawData?: RawDataPoint[]
}
