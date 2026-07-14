export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    // Proxy all requests directly to your live Render backend
    const targetUrl = `https://dundoo-main.onrender.com${url.pathname}${url.search}`;
    const newRequest = new Request(targetUrl, {
      method: request.method,
      headers: request.headers,
      body: ["GET", "HEAD"].includes(request.method) ? null : request.body,
      redirect: "manual"
    });
    return fetch(newRequest);
  }
};
