import React from "react";

import {
  CategoryScale,
  Chart as ChartJS,
  LineElement,
  LinearScale,
  PointElement,
  Tooltip,
} from "chart.js";
import { Line } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip);

function TrendChart({ data }) {
  const chartData = {
    labels: data.map((item) => item.date),
    datasets: [
      {
        label: "Detections",
        data: data.map((item) => item.count),
        borderColor: "#a3e635",
        backgroundColor: "rgba(163, 230, 53, 0.16)",
        tension: 0.35,
        fill: false,
      },
    ],
  };

  return (
    <section className="panel chart-panel wide">
      <div className="section-heading">
        <h2>Detection Trends</h2>
      </div>
      <div className="chart-body">
        <Line
          data={chartData}
          options={{
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
              x: {
                ticks: { color: "#cbd5e1", maxTicksLimit: 8 },
                grid: { color: "#2a2a2a" },
              },
              y: { ticks: { color: "#cbd5e1" }, grid: { color: "#2a2a2a" } },
            },
          }}
        />
      </div>
    </section>
  );
}

export default TrendChart;
