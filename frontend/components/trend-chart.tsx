"use client"

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { formatTime } from '@/lib/utils';

interface RawDataPoint {
  time: string;
  value: number;
}

interface TrendChartProps {
  rawData: RawDataPoint[];
  predictions: number[];
  direction: 'up' | 'down';
}

export default function TrendChart({ rawData, predictions, direction }: TrendChartProps) {
  const currentHour = new Date().getHours();
  const currentMinute = new Date().getMinutes();
  
  // Get historical data from the last 3 hours
  const historicalData = predictions
    .slice(currentHour - 3, currentHour + 1)
    .map((value, index) => {
      const hour = currentHour - 3 + index;
      const time = `${hour.toString().padStart(2, '0')}:00`;
      return {
        time,
        displayTime: formatTime(time),
        value,
        isForecast: false
      };
    });

  // Format predictions for future hours (only show next 3 hours)
  const futurePredictions = predictions
    .slice(currentHour + 1, currentHour + 4)
    .map((value, index) => {
      const predictionHour = currentHour + 1 + index;
      const time = `${predictionHour.toString().padStart(2, '0')}:00`;
      return {
        time,
        displayTime: formatTime(time),
        value,
        isForecast: true
      };
    });

  // Combine the data
  const chartData = [
    ...historicalData,
    ...futurePredictions
  ];

  // Find the current hour's time string for the reference line
  const currentTimeStr = `${currentHour.toString().padStart(2, '0')}:00`;

  // Create array of ticks we want to show
  const startHour = formatTime(`${(currentHour - 3).toString().padStart(2, '0')}:00`);
  const currentHourFormatted = formatTime(currentTimeStr);
  const endHour = formatTime(`${(currentHour + 3).toString().padStart(2, '0')}:00`);
  const ticks = [startHour, currentHourFormatted, endHour];

  return (
    <div className="h-40 w-full mt-4 ml-4">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart 
          data={chartData} 
          margin={{ top: 5, right: 20, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" vertical={false} horizontal={false} />
          <XAxis 
            dataKey="displayTime" 
            tick={{ fill: '#9ca3af' }} 
            axisLine={{ stroke: '#333842' }} 
            tickLine={false}
            ticks={ticks}
            interval={0}
            minTickGap={0}
          />
          <YAxis 
            hide={true}
            domain={[0, 100]} 
          />
          <Tooltip
            contentStyle={{ backgroundColor: '#1a1d24', borderColor: '#333842' }}
            labelStyle={{ color: 'white' }}
            itemStyle={{ color: 'white' }}
            formatter={(value) => [`${value}%`, 'Occupancy']}
          />
          {/* Main line */}
          <Line
            type="monotone"
            dataKey="value"
            stroke={direction === 'up' ? '#ef4444' : '#10b981'}
            strokeWidth={3}
            dot={false}
            connectNulls
          />
          {/* Reference line for current time */}
          <ReferenceLine
            x={formatTime(currentTimeStr)}
            stroke="#ffffff"
            strokeWidth={1}
            strokeDasharray="3 3"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
