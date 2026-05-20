const ctx = document.getElementById('chart').getContext('2d');
const chart = new Chart(ctx, {
  type: 'line',
  data: {
    labels: [],
    datasets: [
      { label: 'Temperature °C', data: [], borderColor: '#ef4444', fill: false, tension: 0.3, pointRadius: 0 },
      { label: 'Humidity %', data: [], borderColor: '#3b82f6', fill: false, tension: 0.3, pointRadius: 0, yAxisID: 'y1' },
    ],
  },
  options: {
    responsive: true,
    interaction: { mode: 'index', intersect: false },
    scales: {
      x: { display: true, ticks: { maxTicksLimit: 12 } },
      y: { position: 'left', title: { display: true, text: '°C' } },
      y1: { position: 'right', title: { display: true, text: '%' }, grid: { drawOnChartArea: false } },
    },
  },
});

function updateCurrent(temp, hum, targetTemp, targetHum, alertPct) {
  const tempEl = document.getElementById('temp-display');
  const humEl = document.getElementById('hum-display');
  tempEl.textContent = temp.toFixed(1) + '°C';
  humEl.textContent = Math.round(hum) + '%';

  const tRange = targetTemp * alertPct / 100;
  const hRange = targetHum * alertPct / 100;

  tempEl.className = 'text-3xl font-mono ' + (Math.abs(temp - targetTemp) > tRange ? 'text-red-600' : 'text-green-600');
  humEl.className = 'text-xl font-mono ' + (Math.abs(hum - targetHum) > hRange ? 'text-red-600' : 'text-green-600');
}

function updateConfig(config) {
  document.getElementById('target-temp').value = config.target_temp;
  document.getElementById('target-temp-label').textContent = config.target_temp;
  document.getElementById('target-hum').value = config.target_hum;
  document.getElementById('target-hum-label').textContent = config.target_hum;
  document.getElementById('alert-percent').value = config.alert_percent;
  document.getElementById('alert-percent-label').textContent = config.alert_percent;

  document.querySelectorAll('input[type="range"]').forEach(el => {
    el.addEventListener('change', () => {
      const key = el.id;
      const label = document.getElementById(key + '-label');
      if (label) label.textContent = el.value;
      const configKey = key.replace(/-/g, '_');
      const body = {};
      body[configKey] = el.value;
      fetch('/api/config', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body) });
    });
  });
}

async function loadHistorical() {
  const resp = await fetch('/api/readings?hours=24');
  const readings = await resp.json();
  chart.data.labels = readings.map(r => new Date(r.ts * 1000).toLocaleTimeString());
  chart.data.datasets[0].data = readings.map(r => r.temp);
  chart.data.datasets[1].data = readings.map(r => r.humidity);
  chart.update();
}

async function loadConfig() {
  const resp = await fetch('/api/config');
  const config = await resp.json();
  updateConfig(config);
}

let lastData = null;
function connectSSE() {
  const evtSource = new EventSource('/api/live');
  evtSource.onmessage = (e) => {
    const data = JSON.parse(e.data);
    lastData = data;

    loadConfig().then(() => {
      const config = {
        target_temp: parseFloat(document.getElementById('target-temp').value),
        target_hum: parseFloat(document.getElementById('target-hum').value),
        alert_percent: parseFloat(document.getElementById('alert-percent').value),
      };
      updateCurrent(data.temp, data.humidity, config.target_temp, config.target_hum, config.alert_percent);
    });

    chart.data.labels.push(new Date(data.ts * 1000).toLocaleTimeString());
    chart.data.datasets[0].data.push(data.temp);
    chart.data.datasets[1].data.push(data.humidity);
    if (chart.data.labels.length > 288) {
      chart.data.labels.shift();
      chart.data.datasets[0].data.shift();
      chart.data.datasets[1].data.shift();
    }
    chart.update('none');
    document.getElementById('live-status').textContent = 'Live';
  };
  evtSource.onerror = () => {
    document.getElementById('live-status').textContent = 'Reconnecting...';
  };
}

loadHistorical();
loadConfig();
connectSSE();
