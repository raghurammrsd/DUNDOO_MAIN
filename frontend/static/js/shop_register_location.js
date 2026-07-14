document.addEventListener("DOMContentLoaded", function () {

    let map = null;
    let marker = null;
  
    const detectBtn = document.getElementById("detectLocationBtn");
    const mapDiv = document.getElementById("shop-map");
    const statusText = document.getElementById("location-status");
    const latInput = document.getElementById("latitude");
    const lngInput = document.getElementById("longitude");
  
    detectBtn.addEventListener("click", function () {
  
        if (!navigator.geolocation) {
            alert("Geolocation is not supported by your browser");
            return;
        }
  
        statusText.innerText = "Detecting your shop location...";
  
        navigator.geolocation.getCurrentPosition(
          success,
          error,
          { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
        );
    });
  
    function success(position) {
        const lat = position.coords.latitude;
        const lng = position.coords.longitude;
      
        latInput.value = lat;
        lngInput.value = lng;
      
        mapDiv.classList.add("leaflet-ready");
      
        if (!map) {
          map = L.map("shop-map", {
            center: [lat, lng],
            zoom: 16,
            zoomControl: true
          });
      
          L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution: "© OpenStreetMap"
          }).addTo(map);
      
          marker = L.marker([lat, lng], { draggable: true }).addTo(map);
      
          marker.on("dragend", () => {
            const p = marker.getLatLng();
            latInput.value = p.lat;
            lngInput.value = p.lng;
          });
      
          map.on("click", e => {
            marker.setLatLng(e.latlng);
            latInput.value = e.latlng.lat;
            lngInput.value = e.latlng.lng;
          });
      
          setTimeout(() => map.invalidateSize(true), 150);
          setTimeout(() => {
            const r = mapDiv.getBoundingClientRect();
            console.log("MAP SIZE:", r.width, r.height);
          }, 300);
          
      
        } else {
          map.setView([lat, lng], 16);
          marker.setLatLng([lat, lng]);
          setTimeout(() => map.invalidateSize(true), 150);
        }
      
        statusText.innerText = "Adjust the pin to mark exact shop location.";
      }
      
  
    function error(err) {
        alert("Location failed: " + err.message);
        statusText.innerText = "Unable to detect location.";
    }
  
  });
  