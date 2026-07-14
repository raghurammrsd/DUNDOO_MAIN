document.addEventListener("DOMContentLoaded", () => {
    const viewport = document.getElementById("reels-viewport");
    
    // Abstracting some dummy mock data since we don't have a media endpoint
    const mockReels = [
        {
            id: 1,
            video_url: "https://www.w3schools.com/html/mov_bbb.mp4", // Free sample video
            shop_name: "Green Valley Farms",
            product_name: "Organic Apples",
            price: "₹150",
            desc: "Freshly picked organic apples straight from our local farm. Crunchy and sweet! 🍏✨ #organic #fresh",
            likes: "1.2K",
            comments: 45
        },
        {
            id: 2,
            video_url: "https://d23dyxeqlo5psv.cloudfront.net/big_buck_bunny.mp4",
            shop_name: "Daily Needs Supermart",
            product_name: "Premium Dairy Milk",
            price: "₹65",
            desc: "Start your morning right with our farm-fresh premium milk. 🥛 #dairy #morning",
            likes: "856",
            comments: 12
        },
        {
            id: 3,
            video_url: "https://www.w3schools.com/html/mov_bbb.mp4",
            shop_name: "Sneaker Hub",
            product_name: "Nike Air Max",
            price: "₹4500",
            desc: "Step up your sneaker game! Limited stock available. 👟🔥 #sneakers #fashion",
            likes: "4.5K",
            comments: 320
        }
    ];

    setTimeout(() => {
        document.getElementById("reel-loader").remove();
        renderReels(mockReels);
        setupIntersectionObserver();
    }, 800); // Fake network delay

    function renderReels(reels) {
        reels.forEach(reel => {
            const node = document.createElement("div");
            node.className = "reel-node";
            
            node.innerHTML = `
                <video class="reel-video" src="${reel.video_url}" loop muted playsinline></video>
                
                <i class="fas fa-heart big-heart"></i>

                <div class="reel-product-card tilt-effect" onclick="if(typeof addToCartGlobal === 'function'){ addToCartGlobal('${reel.product_name}', '${reel.price}', '${reel.id}'); } else { alert('Added ${reel.product_name} to cart!'); }" style="cursor: pointer;">
                    <div style="background: #16a34a; width: 40px; height: 40px; border-radius: 8px; display:flex; align-items:center; justify-content:center; color:white; font-size:20px;">
                        <i class="fas fa-shopping-bag"></i>
                    </div>
                    <div>
                        <div style="font-weight: 800; color: #111827; font-size: 14px;">${reel.product_name}</div>
                        <div style="font-weight: 900; color: #16a34a; font-size: 14px;">${reel.price} <span style="font-size:11px; background:#dcfce7; color:#16a34a; padding:2px 6px; border-radius:4px; margin-left:4px; font-weight:800;">+ Add</span></div>
                    </div>
                </div>

                <div class="reel-overlay"></div>
                
                <div class="reel-info">
                    <h3 class="reel-shop">
                        ${reel.shop_name} 
                        <i class="fas fa-check-circle verified-badge"></i>
                    </h3>
                    <p class="reel-desc">${reel.desc}</p>
                    <div class="reel-music">
                        <i class="fas fa-music"></i>
                        <marquee scrollamount="4" style="width: 150px;">Original Audio - ${reel.shop_name}</marquee>
                    </div>
                </div>

                <div class="reel-actions">
                    <button class="action-btn like-btn">
                        <i class="fas fa-heart"></i>
                        <span class="action-text">${reel.likes}</span>
                    </button>
                    <button class="action-btn comment-btn" onclick="alert('💬 Comments for ${reel.product_name}:\\n\\n✨ Rahul: Amazing quality! Ordered twice.\\n🔥 Priya: Delivery in just 12 minutes!\\n🍏 Amit: Super fresh, loved it!')">
                        <i class="fas fa-comment"></i>
                        <span class="action-text">${reel.comments}</span>
                    </button>
                    <button class="action-btn share-btn" onclick="navigator.clipboard.writeText(window.location.href); alert('✈️ Reel link copied! Ready to share on Instagram or WhatsApp!');">
                        <i class="fas fa-share"></i>
                        <span class="action-text">Share</span>
                    </button>
                    <button class="action-btn" style="margin-top: 10px;">
                        <img src="https://ui-avatars.com/api/?name=${reel.shop_name}&background=16a34a&color=fff" style="width: 35px; height: 35px; border-radius: 50%; border: 2px solid white;">
                    </button>
                </div>
            `;

            viewport.appendChild(node);

            // Double Tap to Like implementation
            let lastTap = 0;
            node.addEventListener('click', function(e) {
                // Ignore clicks on side-buttons or product card
                if(e.target.closest('.reel-actions') || e.target.closest('.reel-product-card')) return;

                const currentTime = new Date().getTime();
                const tapLength = currentTime - lastTap;
                if (tapLength < 500 && tapLength > 0) {
                    // Double tap detected
                    triggerLike(node);
                    e.preventDefault();
                } else {
                    // Single tap: Pause/Play
                    const vid = node.querySelector('video');
                    if (vid.paused) { vid.play(); } else { vid.pause(); }
                }
                lastTap = currentTime;
            });

            // Like button click
            const likeBtn = node.querySelector('.like-btn');
            likeBtn.addEventListener('click', () => {
                triggerLike(node);
            });
        });

        // Initialize tilt.js for the dynamic product cards over the video
        if (typeof attachTiltListeners === "function") {
            attachTiltListeners();
        }
    }

    function triggerLike(node) {
        const bigHeart = node.querySelector('.big-heart');
        const likeBtn = node.querySelector('.like-btn');
        const likeText = likeBtn.querySelector('.action-text');
        
        let currentLikesStr = likeText.innerText;
        let isK = currentLikesStr.includes('K');
        let currentLikes = parseFloat(currentLikesStr);
        
        // If getting liked
        if (!likeBtn.classList.contains('liked')) {
            // Add animated big heart class
            bigHeart.classList.remove('animate-heart');
            void bigHeart.offsetWidth; // trigger reflow
            bigHeart.classList.add('animate-heart');
            
            likeBtn.classList.add('liked');
            if (isK) {
                // Approximate increment for K format
                // In a real app we'd track exact ints, but for UI demo:
                likeText.innerText = (currentLikes + 0.1).toFixed(1) + 'K';
            } else {
                likeText.innerText = parseInt(currentLikes) + 1;
            }
        } else {
            // Unlike
            likeBtn.classList.remove('liked');
            if (isK) {
                likeText.innerText = (currentLikes - 0.1).toFixed(1) + 'K';
            } else {
                likeText.innerText = parseInt(currentLikes) - 1;
            }
        }
    }

    // Auto-play the video that is currently in view using IntersectionObserver
    function setupIntersectionObserver() {
        const observerOptions = {
            root: viewport,
            rootMargin: '0px',
            threshold: 0.6 // 60% of video must be visible to play
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                const video = entry.target.querySelector('video');
                if(!video) return;

                if (entry.isIntersecting) {
                    // Restart video from beginning when scrolled to
                    video.currentTime = 0;
                    // Attempt to auto play
                    video.play().catch(e => console.log("Autoplay blocked by browser. User must interact."));
                } else {
                    video.pause();
                }
            });
        }, observerOptions);

        const nodes = document.querySelectorAll('.reel-node');
        nodes.forEach(node => observer.observe(node));
    }
});