async function loadReels() {
    const res = await fetch("/shopkeeper/my-reels");
    const reels = await res.json();
  
    const tbody = document.getElementById("reelsTable");
    tbody.innerHTML = "";
  
    reels.forEach(r => {
      const tr = document.createElement("tr");
  
      tr.innerHTML = `
        <td>
          <video src="${r.video}" width="120" controls muted></video>
        </td>
        <td>${r.offer}</td>
        <td>${r.days_left}</td>
        <td>
          <span class="${r.active ? 'badge-green' : 'badge-gray'}">
            ${r.active ? 'Active' : 'Expired'}
          </span>
        </td>
        <td class="text-right">
          <button class="btn-danger" onclick="deleteReel(${r.id})">
            Delete
          </button>
        </td>
      `;
  
      tbody.appendChild(tr);
    });
  }
  
  async function deleteReel(id) {
    if (!confirm("Delete this reel?")) return;
  
    await fetch(`/shopkeeper/reels/${id}`, { method: "DELETE" });
    loadReels();
  }
  
  document.getElementById("reelForm").addEventListener("submit", async (e) => {
    e.preventDefault();
  
    const formData = new FormData();
  
    formData.append("video", document.getElementById("video").files[0]);
    formData.append("offer_type", document.getElementById("offer_type").value);
    formData.append("offer_value", document.getElementById("offer_value").value);
    formData.append("duration_days", document.getElementById("duration_days").value);
    formData.append("radius", document.getElementById("radius").value);
    formData.append("budget", document.getElementById("budget").value);
    formData.append("lat", SHOP_LAT);
    formData.append("lon", SHOP_LON);
  
    const res = await fetch("/shopkeeper/reels", {
      method: "POST",
      body: formData
    });
  
    if (res.ok) {
      alert("🎉 Reel uploaded successfully");
      document.getElementById("reelForm").reset();
      loadReels();
    } else {
      const err = await res.json();
      alert(err.error || "Upload failed");
    }
  });
  
  loadReels();
  