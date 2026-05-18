import React from "react";

import {
  ArcElement,
  Chart as ChartJS,
  Legend,
  Tooltip,
} from "chart.js";
import { Doughnut } from "react-chartjs-2";

ChartJS.register(ArcElement, Tooltip, Legend);

function SeverityChart({ data }) {
  const chartData = {
    labels: data.map((item) => item.severity),
    datasets: [
      {
        data: data.map((item) => item.count),
        backgroundColor: ["#dc2626", "#f97316", "#eab308", "#22c55e"],
        borderColor: "#111111",
        borderWidth: 2,
      },
    ],
  };

  return (
    <section className="panel chart-panel">
      <div className="section-heading">
        <h2>Detections by Severity</h2>
      </div>
      <div className="chart-body">
        <Doughnut
          data={chartData}
          options={{
            maintainAspectRatio: false,
            plugins: {
              legend: {
                labels: {
                  color: "#cbd5e1",
                },
              },
            },
          }}
        />
      </div>
    </section>
  );
}

export default SeverityChart;
