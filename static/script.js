let chartInstance = null;

async function loadData() {
  const indicator = document.getElementById('refreshIndicator');
  indicator.classList.add('active');

  try {
    // Fetch summary & data
    const resSummary = await fetch("/api/summary");
    const summary = await resSummary.json();

    const resData = await fetch("/api/data");
    const data = await resData.json();

    // Update status cards (data terakhir)
    if (data.length > 0) {
      const latest = data[0];
      document.getElementById('currentTemp').textContent = latest.suhu ?? '--';
      document.getElementById('currentHumid').textContent = latest.humidity ?? '--';
      document.getElementById('currentLux').textContent = latest.lux ?? '--';
      document.getElementById('totalData').textContent = data.length;
    }

    // Update summary statistics
    document.getElementById('suhuMax').textContent = summary.suhumax ?? '--';
    document.getElementById('suhuMin').textContent = summary.suhumin ?? '--';
    document.getElementById('suhuAvg').textContent = summary.suhurata ?? '--';
    document.getElementById('humidMax').textContent = summary.humidmax ?? '--';
    document.getElementById('humidMin').textContent = summary.humidmin ?? '--';
    document.getElementById('humidAvg').textContent = summary.humidrata ?? '--';

    // Chart data
    const labels = data.map(d => d.timestamp.split(" ")[1]);
    const suhu = data.map(d => d.suhu);
    const humid = data.map(d => d.humidity);

    // Destroy old chart
    if (chartInstance) chartInstance.destroy();

    // Create new chart
    const ctx = document.getElementById("chartSuhu").getContext("2d");
    const gradientTemp = ctx.createLinearGradient(0, 0, 0, 400);
    gradientTemp.addColorStop(0, 'rgba(255, 107, 107, 0.5)');
    gradientTemp.addColorStop(1, 'rgba(255, 107, 107, 0.05)');
    const gradientHumid = ctx.createLinearGradient(0, 0, 0, 400);
    gradientHumid.addColorStop(0, 'rgba(78, 205, 196, 0.5)');
    gradientHumid.addColorStop(1, 'rgba(78, 205, 196, 0.05)');

    chartInstance = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels.reverse(),
        datasets: [
          {
            label: "Suhu (°C)",
            data: suhu.reverse(),
            borderColor: "#ff6b6b",
            backgroundColor: gradientTemp,
            fill: true,
            tension: 0.4,
            borderWidth: 3
          },
          {
            label: "Kelembapan (%)",
            data: humid.reverse(),
            borderColor: "#4ecdc4",
            backgroundColor: gradientHumid,
            fill: true,
            tension: 0.4,
            borderWidth: 3
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom' }
        },
        scales: {
          y: { beginAtZero: true },
          x: { grid: { display: false } }
        }
      }
    });

    // Tabel data
    const body = document.getElementById("dataBody");
    body.innerHTML = data.map(d => `
      <tr>
        <td><strong>#${d.id}</strong></td>
        <td>${d.timestamp}</td>
        <td><span class="badge badge-temp">${d.suhu}°C</span></td>
        <td><span class="badge badge-humid">${d.humidity}%</span></td>
        <td><span class="badge badge-lux">${d.lux} Lux</span></td>
      </tr>
    `).join('');

    document.getElementById('dataCount').textContent = `${data.length} data`;

  } catch (err) {
    console.error("⚠️ Gagal memuat data:", err);
  } finally {
    setTimeout(() => {
      indicator.classList.remove('active');
    }, 500);
  }
}

// Auto refresh setiap 5 detik
loadData();
setInterval(loadData, 5000);
