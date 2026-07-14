export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    
    // 1. Check Cloudflare Edge Cache for static assets (/static/*) or read-only shop discovery endpoints
    const isStaticAsset = url.pathname.startsWith("/static/");
    const isDiscoveryApi = request.method === "GET" && url.pathname.includes("/nearby_shops_discovery");
    const cache = caches.default;
    
    if (request.method === "GET" && (isStaticAsset || isDiscoveryApi)) {
      let cachedResponse = await cache.match(request);
      if (cachedResponse) {
        return cachedResponse;
      }
    }

    // 2. Proxy request directly to live Render backend
    const targetUrl = `https://dundoo-main.onrender.com${url.pathname}${url.search}`;
    const newRequest = new Request(targetUrl, {
      method: request.method,
      headers: request.headers,
      body: ["GET", "HEAD"].includes(request.method) ? null : request.body,
      redirect: "manual"
    });
    
    let response = await fetch(newRequest);

    // 3. Store static assets (24 hrs) and discovery APIs (5 mins) in Cloudflare's edge memory for instant loading (~15ms)
    if (request.method === "GET" && response.status === 200 && (isStaticAsset || isDiscoveryApi)) {
      response = new Response(response.body, response);
      const cacheControl = isStaticAsset 
        ? "public, max-age=86400, s-maxage=86400" 
        : "public, max-age=300, s-maxage=300";
      response.headers.set("Cache-Control", cacheControl);
      ctx.waitUntil(cache.put(request, response.clone()));
    }

    return response;
  }
};
