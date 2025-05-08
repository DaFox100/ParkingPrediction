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
  predictedOccupancy?: number
  forecast?: boolean
  rawData?: RawDataPoint[]
}

export interface ParkingGarageCardProps {
  garage: GarageData
  isExpanded: boolean
  onGarageClick: (id: string) => void
  onRefresh: () => void
  selectedDate: string
  onDateChange: (date: string) => void
  availableDates: string[]
  isTodayMode: boolean
  onModeChange: (mode: 'today' | 'historical' | 'future') => void
  averageFullness: number[]
  tomorrowPredictions: number[]
}
