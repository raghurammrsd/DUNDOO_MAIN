function initShopCharts() {
  if (typeof Chart === "undefined") {
    setTimeout(initShopCharts, 50);
    return;
  }

  const salesCanvas = document.getElementById("salesChart");
  if (salesCanvas && typeof salesLabels !== "undefined" && Array.isArray(salesLabels)) {
    const ctx = salesCanvas.getContext("2d");

    new Chart(ctx, {
      type: "bar",
      data: {
        labels: salesLabels,
        datasets: [
          {
            label: "Sales (₹)",
            data: salesData,
            backgroundColor: "rgba(22, 163, 74, 0.85)",
            borderRadius: 6
          },
          {
            label: "Profit (₹)",
            data: profitData,
            backgroundColor: "rgba(34, 197, 94, 0.85)",
            borderRadius: 6
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: (value) => "₹" + value.toLocaleString()
            },
            grid: {
              color: "#e5e7eb"
            }
          },
          x: {
            grid: {
              display: false
            }
          }
        },
        plugins: {
          legend: {
            position: "bottom"
          },
          tooltip: {
            callbacks: {
              label: (ctx) => {
                const val = ctx.parsed.y || 0;
                return `${ctx.dataset.label}: ₹${val.toLocaleString()}`;
              }
            }
          }
        }
      }
    });
  }

  const stockCanvas = document.getElementById("stockChart");
  if (stockCanvas && typeof stockLabels !== "undefined" && Array.isArray(stockLabels) && stockLabels.length > 0) {
    const ctx2 = stockCanvas.getContext("2d");

    new Chart(ctx2, {
      type: "doughnut",
      data: {
        labels: stockLabels,
        datasets: [
          {
            data: stockValues,
            backgroundColor: [
              "#16a34a",
              "#2563eb",
              "#f97316",
              "#a855f7",
              "#e11d48",
              "#0ea5e9",
              "#eab308"
            ],
            borderWidth: 2,
            borderColor: "#ffffff"
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "right"
          },
          tooltip: {
            callbacks: {
              label: (ctx) => {
                const label = ctx.label || "";
                const value = ctx.parsed || 0;
                return `${label}: ₹${value.toLocaleString()}`;
              }
            }
          }
        },
        cutout: "65%"
      }
    });
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initShopCharts);
} else {
  initShopCharts();
}

function showShopToast(msg, isError = false) {
  let toast = document.getElementById("shop-quick-toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "shop-quick-toast";
    toast.style.cssText = "position: fixed; bottom: 24px; right: 24px; z-index: 9999; padding: 12px 24px; border-radius: 12px; font-weight: 800; font-size: 14px; box-shadow: 0 10px 25px rgba(0,0,0,0.15); transition: all 0.3s ease; transform: translateY(100px); opacity: 0;";
    document.body.appendChild(toast);
  }
  toast.innerText = msg;
  toast.style.background = isError ? "#ef4444" : "#16a34a";
  toast.style.color = "white";
  toast.style.transform = "translateY(0)";
  toast.style.opacity = "1";
  setTimeout(() => {
    toast.style.transform = "translateY(100px)";
    toast.style.opacity = "0";
  }, 2500);
}

function quickToggleStock(pid, currentVal) {
  fetch("/shop/api/product/quick_toggle", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ product_id: pid, available: !currentVal })
  })
  .then(r => r.json())
  .then(d => {
    if (d.success) {
      const btn = document.getElementById("avail-btn-" + pid);
      if (btn) {
        btn.setAttribute("onclick", `quickToggleStock(${pid}, ${d.available})`);
        if (d.available) {
          btn.innerText = "In Stock";
          btn.style.background = "#dcfce7";
          btn.style.color = "#166534";
        } else {
          btn.innerText = "Out of Stock";
          btn.style.background = "#fee2e2";
          btn.style.color = "#dc2626";
        }
      }
      showShopToast(d.available ? "Marked In Stock" : "Marked Out of Stock");
    } else {
      showShopToast("Failed to update stock status", true);
    }
  })
  .catch(() => showShopToast("Network error", true));
}

function quickUpdatePrice(pid) {
  const inp = document.getElementById("price-input-" + pid);
  if (!inp) return;
  fetch("/shop/api/product/quick_toggle", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ product_id: pid, price: inp.value })
  })
  .then(r => r.json())
  .then(d => {
    if (d.success) {
      inp.value = parseFloat(d.price).toFixed(2);
      inp.style.borderColor = "#16a34a";
      inp.style.background = "#dcfce7";
      setTimeout(() => { inp.style.borderColor = "#e5e7eb"; inp.style.background = "white"; }, 1000);
      showShopToast("Price updated to ₹" + parseFloat(d.price).toFixed(2));
    } else {
      showShopToast("Failed to update price", true);
    }
  })
  .catch(() => showShopToast("Network error", true));
}

function quickUpdateQty(pid) {
  const inp = document.getElementById("qty-input-" + pid);
  if (!inp) return;
  fetch("/shop/api/product/quick_toggle", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ product_id: pid, quantity: inp.value })
  })
  .then(r => r.json())
  .then(d => {
    if (d.success) {
      inp.value = d.quantity;
      inp.style.borderColor = "#16a34a";
      inp.style.background = "#dcfce7";
      setTimeout(() => { inp.style.borderColor = "#e5e7eb"; inp.style.background = "white"; }, 1000);
      showShopToast("Stock count updated to " + d.quantity);
    } else {
      showShopToast("Failed to update quantity", true);
    }
  })
  .catch(() => showShopToast("Network error", true));
}
