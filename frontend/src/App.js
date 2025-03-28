import React, { useState, useEffect } from 'react';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

function App() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/data');
        const jsonData = await response.json();
        setData(jsonData);
        setLoading(false);
      } catch (error) {
        console.error('Error fetching data:', error);
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const chartData = {
    labels: data.map(item => item.time),
    datasets: [
      {
        label: 'Value',
        data: data.map(item => item.value),
        backgroundColor: 'rgba(54, 162, 235, 0.5)',
        borderColor: 'rgba(54, 162, 235, 1)',
        borderWidth: 1,
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: '24-Hour Data Values (0-100)',
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 100,
      },
    },
  };

  if (loading) {
    return <div>Loading data...</div>;
  }

  return (
    <div style={{ width: '80%', margin: '0 auto', padding: '20px' }}>
      <h1>24-Hour Data Visualization</h1>
      <div style={{ height: '500px' }}>
        <Bar data={chartData} options={options} />
      </div>
      <div style={{ marginTop: '20px' }}>
        <h3>Data Points:</h3>
        <ul>
          {data.map((item, index) => (
            <li key={index}>
              Time: {item.time}, Value: {item.value}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default App;