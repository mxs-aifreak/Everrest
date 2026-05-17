/* EverRest Property Management – front-end helpers */

// ── PWA Service Worker registration ──────────────────────
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/static/sw.js')
      .catch(err => console.warn('SW registration failed:', err));
  });
}

// ── Delete confirmation dialogs ───────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', e => {
      const msg = el.dataset.confirm || 'Are you sure you want to delete this? This cannot be undone.';
      if (!confirm(msg)) e.preventDefault();
    });
  });

  // ── Multi-step form ───────────────────────────────────
  initMultiStep();

  // ── Auto-dismiss alerts after 5 s ────────────────────
  document.querySelectorAll('.alert-dismissible').forEach(alert => {
    setTimeout(() => {
      const btn = alert.querySelector('.btn-close');
      if (btn) btn.click();
    }, 5000);
  });

  // ── Currency input formatting ─────────────────────────
  document.querySelectorAll('input[data-currency]').forEach(input => {
    input.addEventListener('blur', () => {
      const val = parseFloat(input.value.replace(/[^0-9.]/g, ''));
      if (!isNaN(val)) input.value = val.toFixed(2);
    });
  });

  // ── Sprinkler: toggle repair fields ──────────────────
  const repairSelect = document.getElementById('repair_needed');
  if (repairSelect) {
    toggleRepairFields(repairSelect.value);
    repairSelect.addEventListener('change', () => toggleRepairFields(repairSelect.value));
  }

  // ── Sprinkler: toggle system fields based on has_sprinkler ──
  const hasSprinkler = document.getElementById('has_sprinkler');
  if (hasSprinkler) {
    toggleSprinklerFields(hasSprinkler.value);
    hasSprinkler.addEventListener('change', () => toggleSprinklerFields(hasSprinkler.value));
  }

  // ── Work order: auto-populate owner from property ────
  const propSelect = document.getElementById('property_id');
  if (propSelect && document.getElementById('owner_id')) {
    propSelect.addEventListener('change', () => fetchPropertyOwner(propSelect.value));
  }
});

// ── Multi-step form logic ─────────────────────────────────
function initMultiStep() {
  const form = document.getElementById('multiStepForm');
  if (!form) return;

  const steps = Array.from(form.querySelectorAll('.form-step'));
  const dots = Array.from(document.querySelectorAll('.step-dot'));
  let current = 0;

  function showStep(idx) {
    steps.forEach((s, i) => s.classList.toggle('d-none', i !== idx));
    dots.forEach((d, i) => {
      d.classList.remove('active', 'done');
      if (i < idx) d.classList.add('done');
      else if (i === idx) d.classList.add('active');
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  form.querySelectorAll('[data-next]').forEach(btn => {
    btn.addEventListener('click', () => {
      if (current < steps.length - 1) {
        current++;
        showStep(current);
      }
    });
  });

  form.querySelectorAll('[data-prev]').forEach(btn => {
    btn.addEventListener('click', () => {
      if (current > 0) {
        current--;
        showStep(current);
      }
    });
  });

  showStep(0);
}

function toggleRepairFields(val) {
  const fields = document.getElementById('repairFields');
  if (!fields) return;
  fields.classList.toggle('d-none', val !== 'Yes');
}

function toggleSprinklerFields(val) {
  const fields = document.getElementById('sprinklerFields');
  if (!fields) return;
  fields.classList.toggle('d-none', val === 'No');
}

function fetchPropertyOwner(propId) {
  if (!propId) return;
  fetch(`/api/property-owner/${propId}`)
    .then(r => r.json())
    .then(data => {
      const ownerSelect = document.getElementById('owner_id');
      if (ownerSelect && data.owner_id) {
        ownerSelect.value = data.owner_id;
      }
    })
    .catch(() => {});
}

// ── Chart initialization (called from dashboard template) ─
function initWoChart(labels, costs) {
  const ctx = document.getElementById('woChart');
  if (!ctx) return;
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Completed WO Cost ($)',
        data: costs,
        backgroundColor: 'rgba(21,67,96,0.75)',
        borderColor: '#154360',
        borderWidth: 1,
        borderRadius: 6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => `$${ctx.parsed.y.toLocaleString('en-US', { minimumFractionDigits: 2 })}`,
          },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: v => `$${v.toLocaleString()}`,
            font: { size: 11 },
          },
          grid: { color: '#eee' },
        },
        x: {
          ticks: { font: { size: 11 } },
          grid: { display: false },
        },
      },
    },
  });
}
