async function fetchGoogleLocation() {
    const res = await fetch("https://www.googleapis.com/geolocation/v1/geolocate?key=YOUR_API_KEY", {
      method: "POST"
    });
    const data = await res.json();
    return data.location;
  }
  