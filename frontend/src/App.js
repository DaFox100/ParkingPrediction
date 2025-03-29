import React, {useState, useEffect} from 'react';
import {Bar} from 'react-chartjs-2';
import {Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend,} from 'chart.js';
import './App.css'

// Register ChartJS components
ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

function App() {
    const getCssVariable = (name) => {
        return getComputedStyle(document.documentElement).getPropertyValue(name);
    };

    // Gets colors from index.css variables
    const themeColors = {
        text: getCssVariable('--text-color').trim() || '#ffffff',
        grid: getCssVariable('--grid-color').trim() || 'rgba(255, 255, 255, 0.1)',
        border: getCssVariable('--chart-border').trim() || 'rgba(54, 162, 235, 1)',
        bg: getCssVariable('--chart-bg').trim() || 'rgba(75, 192, 192, 0.5)'
    };


    // State value, and function that sets the state
    const [data, setData] = useState([]); // Sets this to be a list
    const [loading, setLoading] = useState(true); // Set this to be a bool

    // React hook for side effects. Second argument is [], meaning this will only run once when mounted
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
                backgroundColor: themeColors.bg,
                borderColor: themeColors.border,
                borderWidth: 1,
            },
        ],
    };

    // Misc elements such as legend, title, etc
    const options = {
        responsive: true,
        plugins: {
            legend: {
                position: 'top',
                labels: {
                    color: themeColors.text,
                },
            },
            title: {
                display: true,
                text: '24-Hour Data Values (0-100)',
                color: themeColors.text,
            },
        },
        scales: {
            x: {
                ticks: {
                    color: themeColors.text,
                    fontSize: 14,
                },
                grid: {
                    color: themeColors.grid,
                },
            },
            y: {
                beginAtZero: true,
                max: 100,
                ticks: {
                    color: themeColors.text,
                    fontSize: 14,
                },
                grid: {
                    color: themeColors.grid,
                },
            },
        },
    };

    // Return text while data is loading
    if (loading) {
        return <div className="loading-text"> Loading data...</div>;
    }

    // Return the chart and data list when data is loaded and ready to display
    return (
        <div className="app-container-dark">
            <h1>24-Hour Data Visualization</h1>
            <div className="chart-container">
                {/* Chart that displays Bar graph */}
                <Bar data={chartData} options={options}/>
            </div>
            <div className="data-list">
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