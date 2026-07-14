let isPaying = false;

document.addEventListener("DOMContentLoaded", function () {
  const btn = document.getElementById("payBtn");
  if (!btn) return;

  btn.addEventListener("click", function () {
    if (isPaying) return;
    isPaying = true;

    fetch("/shop/payment/create-order", { method: "POST" })
      .then(res => res.json())
      .then(order => {

        const options = {
          key: razorpay_key,
          amount: order.amount,
          currency: "INR",
          order_id: order.id,

          handler: function (response) {
            fetch("/shop/payment/success", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(response)
            })
            .then(r => r.json())
            .then(data => window.location.href = data.redirect);
          },

          modal: {
            ondismiss: function () {
              isPaying = false;
            }
          }
        };

        new Razorpay(options).open();
      });
  });
});
