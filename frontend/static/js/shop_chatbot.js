
(function () {
  const form = document.getElementById("chatbot-form");
  const input = document.getElementById("chatbot-input");
  const box = document.getElementById("chatbot-messages");

  if (!form || !input || !box) {
    return; 
  }

  function addMessage(text, who) {
    const div = document.createElement("div");
    div.className = "chatbot-message " + (who === "user" ? "user" : "bot");
    div.style.marginBottom = "8px";
    div.style.padding = "8px 10px";
    div.style.borderRadius = "12px";
    div.style.fontSize = "0.9rem";
    if (who === "user") {
      div.style.background = "#2563eb11";
      div.style.alignSelf = "flex-end";
    } else {
      div.style.background = "#ffffff";
      div.style.border = "1px solid #e5e7eb";
    }
    div.innerHTML = text;
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
  }

  function answer(raw) {
    const text = raw.toLowerCase();

  
    if (text.includes("add product") || text.includes("new product")) {
      return `
        To add a product:<br>
        1️⃣ Go to <strong>Stock &gt; Add Product</strong>.<br>
        2️⃣ Fill name, category, selling price, cost price and opening stock.<br>
        3️⃣ (Optional) Set low-stock threshold &amp; expiry date.<br>
        4️⃣ Click <strong>Add product</strong>.<br><br>
        The product will appear in Dashboard, Stock and Manage Products.
      `;
    }

    if (text.includes("add stock") || text.includes("increase stock")) {
      return `
        To increase stock for an existing product:<br>
        1️⃣ Open <strong>Stock</strong> page.<br>
        2️⃣ Find the product row.<br>
        3️⃣ Enter the quantity in the small input box and click <strong>+ Add</strong>.<br><br>
        This updates current quantity, opening stock stays as your first quantity.
      `;
    }

    if (text.includes("damage")) {
      return `
        To mark items as damaged:<br>
        1️⃣ Go to <strong>Stock</strong> page.<br>
        2️⃣ In that product row, type how many units are damaged.<br>
        3️⃣ Click <strong>Damage</strong>.<br><br>
        Quantity decreases and damaged stock is tracked separately.
      `;
    }

    if (text.includes("record sale") || text.includes("sale") || text.includes("billing")) {
      return `
        To record a sale:<br>
        1️⃣ Open <strong>Record Sale</strong> from sidebar.<br>
        2️⃣ Choose the product and quantity.<br>
        3️⃣ (Optional) enter customer name.<br>
        4️⃣ Click <strong>Record Sale</strong>.<br><br>
        Stock is automatically reduced and the sale appears in Dashboard, Billing and Reports.
      `;
    }

    if (text.includes("low stock")) {
      return `
        Low-stock alert means your quantity is less than or equal to the
        <strong>Low-stock threshold</strong> set for that product (default 10).<br><br>
        When this happens:<br>
        • The row is highlighted in <strong>Stock</strong> page.<br>
        • It shows in Dashboard &amp; Stock as <em>Low stock</em> and can trigger an email alert.
      `;
    }

    if (text.includes("expiry") || text.includes("expire")) {
      return `
        If you set an <strong>expiry date</strong> for a product:<br>
        • When the date passes, it is shown as <strong>Expired</strong> in Stock and emails can be sent.<br>
        • If expiry is within 7 days, it appears under <em>Expiring soon</em>.<br><br>
        You can edit the date from <strong>Stock &gt; Edit</strong> or in <strong>Manage Products</strong>.
      `;
    }

    if (text.includes("dashboard") || text.includes("today") || text.includes("monthly profit")) {
      return `
        Dashboard shows live metrics:<br>
        • <strong>Today's sales</strong> – total value of sales recorded today.<br>
        • <strong>Today's profit</strong> – based on selling price minus cost price.<br>
        • <strong>Monthly profit / loss</strong> – sum of profits for this month.<br>
        • <strong>Low stock items</strong> – count of products below threshold.<br><br>
        Charts show last 7 days sales &amp; profit and stock value by product.
      `;
    }

    if (text.includes("reports") || text.includes("growth")) {
      return `
        Reports page explains your growth:<br>
        • Sales &amp; profit for the last 30 days.<br>
        • Number of orders and average order value.<br>
        • Growth % compared with the previous 30 days.<br>
        • 6-month sales trend chart.<br>
        • Top products table for last 30 days.<br><br>
        Use it to understand which products are performing well.
      `;
    }

    if (text.includes("error") || text.includes("not working")) {
      return `
        For technical errors:<br>
        1️⃣ Check you are logged in as the correct shop.<br>
        2️⃣ Try refreshing the page.<br>
        3️⃣ If something still fails, note the red error message at top of the page
        and share it with the developer (with a screenshot and what you clicked).<br><br>
        I can also explain any specific page if you mention its name.
      `;
    }

    // Default
    return `
      I didn't fully understand that, but I can help with:<br>
      • Adding / editing products<br>
      • Updating stock or marking damage<br>
      • Recording sales &amp; billing<br>
      • Low-stock and expiry alerts<br>
      • Dashboard metrics &amp; Reports<br><br>
      Try asking like: <code>how do I add a new product?</code>
    `;
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    addMessage(text, "user");
    const reply = answer(text);
    addMessage(reply, "bot");
    input.value = "";
    input.focus();
  });
})();
