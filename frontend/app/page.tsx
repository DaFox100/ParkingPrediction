import ParkingDashboard from "@/components/parking-dashboard"

export default function Home() {
  return (
    <main className="min-h-screen bg-background text-white p-2">
      {/* <header className="max-w-6xl mx-auto mb-8">
        <h1 className="text-2xl font-semibold tracking-wide">SJ PARKING</h1>
      </header> */}

      <ParkingDashboard />
    </main>
  )
}
