const form = document.getElementById('uploadForm');
const tableBody = document.getElementById('resultTableBody');
const ctx = document.getElementById('sentimentChart');
const sektorCtx = document.getElementById('negatifSektorChart');
let chart;
let sektorChart;
let bulananChart;
let top5Chart;

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const formData = new FormData(form);

  const res = await fetch('/predict', {
    method: 'POST',
    body: formData
  });

  if (!res.ok) {
    alert('Gagal memproses file');
    return;
  }

  const json = await res.json();
  renderTable(json.data);
  renderChart(json.chart);
  renderNegatifSektorChart(json.negatif_per_sektor);
  renderNegatifBulananChart(json.negatif_per_bulan);
  renderTop5BulananChart(json.top5_bulanan);
});

function renderTable(data) {
  tableBody.innerHTML = '';
  const map = { '-1': 'Negatif', '0': 'Netral', '1': 'Positif' };

  data.forEach(row => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${row.nama}</td>
      <td>${row.waktu}</td>
      <td>${row.ulasan || '-'}</td>
      <td>${map[row.prediksi]}</td>
      <td>${row.sektor}</td>
      <td>${row.bulan_tahun}</td>
    `;
    tableBody.appendChild(tr);
  });
}

function renderChart(chartData) {
  const labels = Object.keys(chartData);
  const values = Object.values(chartData);

  if (chart) chart.destroy(); // destroy chart if already exists

  chart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Jumlah Sentimen',
        data: values,
        backgroundColor: ['#f44336', '#ffeb3b', '#4caf50'],
        borderColor: '#333',
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      scales: {
        y: { beginAtZero: true }
      }
    }
  });
}

function renderNegatifSektorChart(data) {
  const labels = Object.keys(data);
  const values = Object.values(data);
  const dynamicThickness = Math.max(10, 60 - labels.length * 5);

  if (sektorChart) sektorChart.destroy();

  sektorChart = new Chart(sektorCtx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Komentar Negatif per Sektor',
        data: values,
        backgroundColor: '#f44336',
        borderColor: '#b71c1c',
        borderWidth: 1,
        barThickness: dynamicThickness
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true
        }
      }
    }
  });
}

function renderNegatifBulananChart(data) {
  const labels = data.map(item => item.bulan_tahun);
  const values = data.map(item => item.jumlah_negatif);

  const bulananCtx = document.getElementById('negatifBulananChart');

  if (bulananChart) bulananChart.destroy();

  bulananChart = new Chart(bulananCtx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Jumlah Komentar Negatif per Bulan',
        data: values,
        backgroundColor: '#9c27b0',
        borderColor: '#6a1b9a',
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      scales: {
        y: { beginAtZero: true }
      }
    }
  });
}

function renderTop5BulananChart(data) {
  const ctx = document.getElementById('top5BulananChart');

  if (top5Chart) top5Chart.destroy();

  top5Chart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.labels,
      datasets: data.datasets.map((ds, i) => ({
        ...ds,
        backgroundColor: getColor(i),
        borderWidth: 1
      }))
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: 'top' },
        title: {
          display: true,
          text: 'Top 5 Sektor Komentar Negatif per Bulan'
        }
      },
      scales: {
        y: { beginAtZero: true }
      }
    }
  });
}

function getColor(i) {
  const colors = [
    '#f44336', '#2196f3', '#ff9800', '#4caf50', '#9c27b0', '#00bcd4'
  ];
  return colors[i % colors.length];
}
