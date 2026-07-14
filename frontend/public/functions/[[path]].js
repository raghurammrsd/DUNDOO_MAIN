export async function onRequest(context) {
  const url = new URL(context.request.url);
  
  // 1. Check Cloudflare Edge Cache for static assets or discovery queries
  const isStaticAsset = url.pathname.startsWith("/static/");
  const isDiscoveryApi = context.request.method === "GET" && url.pathname.includes("/nearby_shops_discovery");
  const cache = caches.default;
  
  if (context.request.method === "GET" && (isStaticAsset || isDiscoveryApi)) {
    let cachedResponse = await cache.match(context.request);
    if (cachedResponse) {
      return cachedResponse;
    }
  }

  // 2. Proxy request directly to live Render backend
  const targetUrl = `https://dundoo-main.onrender.com${url.pathname}${url.search}`;
  const newRequest = new Request(targetUrl, {
    method: context.request.method,
    headers: context.request.headers,
    body: ["GET", "HEAD"].includes(context.request.method) ? null : context.request.body,
    redirect: "manual"
  });
  
  let response = await fetch(newRequest);

  // 3. Store static assets & discovery data in Cloudflare Edge Cache (`~15ms` delivery)
  if (context.request.method === "GET" && response.status === 200 && (isStaticAsset || isDiscoveryApi)) {
    response = new Response(response.body, response);
    const cacheControl = isStaticAsset 
      ? "public, max-age=86400, s-maxage=86400" 
      : "public, max-age=300, s-maxage=300";
    response.headers.set("Cache-Control", cacheControl);
    context.waitUntil(cache.put(context.request, response.clone()));
  }

  return response;
}
