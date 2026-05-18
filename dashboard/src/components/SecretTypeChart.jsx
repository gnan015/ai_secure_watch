import React from "react";

import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  LinearScale,
  Tooltip,
} from "chart.js";
import { Bar } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip);

function SecretTypeChart({ data }) {
  const maxCount = Math.max(...data.map((item) => item.count), 0);
  const chartData = {
    labels: data.map((item) => item.secret_type),
    datasets: [
      {
        label: "Detections",
        data: data.map((item) => item.count),
        backgroundColor: "#38bdf8",
        borderRadius: 4,
        maxBarThickness: 34,
      },
    ],
  };

  return (
    <section className="panel chart-panel">
      <div className="section-heading">
        <h2>Secret Types</h2>
      </div>
      <div className="chart-body">
        <Bar
          data={chartData}
          options={{
            maintainAspectRatio: false,
            indexAxis: "y",
            plugins: { legend: { display: false } },
            scales: {
              x: {
                beginAtZero: true,
                suggestedMax: Math.max(maxCount + 1, 3),
                ticks: { color: "#cbd5e1", precision: 0, stepSize: 1 },
                grid: { color: "#2a2a2a" },
              },
              y: {
                ticks: { color: "#cbd5e1" },
                grid: { color: "#2a2a2a" },
              },
            },
          }}
        />
      </div>
    </section>
  );
}

export default SecretTypeChart;
