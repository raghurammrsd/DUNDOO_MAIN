// --- Phase 5: Global Multi-Lingual AI Assistant ---

document.addEventListener("DOMContentLoaded", () => {
    if (window.globalVoiceAssistantLoaded) return;
    window.globalVoiceAssistantLoaded = true;

    // Detect if we are on Shop side or User side based on URL or generic element
    const isShop = window.location.pathname.startsWith("/shop/");
    const aiEndpoint = isShop ? "/ai/chat" : "/ai/user_chat";

    // 1. Inject the Global Floating Assistant UI
    const fabContainer = document.createElement("div");
    fabContainer.style.position = "fixed";
    fabContainer.style.bottom = "30px";
    fabContainer.style.right = "30px";
    fabContainer.style.zIndex = "9999";
    fabContainer.style.display = "flex";
    fabContainer.style.flexDirection = "column";
    fabContainer.style.alignItems = "flex-end";
    fabContainer.style.gap = "10px";

    fabContainer.innerHTML = `
        <div id="ai-chat-bubble" class="tilt-effect" style="display: none; background: #ffffff; padding: 12px 16px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); border: 2px solid #16a34a; max-width: 250px; font-weight: 600; color: #115320; font-size: 14px; text-align: right; transform-style: preserve-3d;">
            Hi! I'm Dundoo AI. Tap the mic and tell me what you need!
        </div>
        <div style="display: flex; gap: 10px; align-items: center; background: rgba(255,255,255,0.9); padding: 8px; border-radius: 999px; backdrop-filter: blur(5px); box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
            <select id="global-ai-lang" style="background: transparent; border: none; font-weight: 700; color: #115320; outline: none; cursor: pointer;">
                <option value="en-IN">EN</option>
                <option value="hi-IN">HI</option>
                <option value="te-IN">TE</option>
            </select>
            <button id="global-ai-mic" style="width: 50px; height: 50px; border-radius: 50%; background: #16a34a; color: white; border: none; font-size: 20px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.3s; box-shadow: 0 4px 10px rgba(22,163,74,0.4);">
                <i class="fas fa-microphone"></i>
            </button>
        </div>
    `;

    document.body.appendChild(fabContainer);

    // 2. State & Elements
    let listening = false;
    let speaking = false;
    let recognition = null;
    let controller = null;

    const micBtn = document.getElementById("global-ai-mic");
    const langSelect = document.getElementById("global-ai-lang");
    const chatBubble = document.getElementById("ai-chat-bubble");

    // Show introduction bubble momentarily
    setTimeout(() => {
        chatBubble.style.display = "block";
        setTimeout(() => chatBubble.style.display = "none", 4000);
    }, 1000);

    // 3. Speech Recognition Engine
    function startVoice() {
        if (listening) return;

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            alert("Your browser does not support Voice AI. Try Chrome or Safari.");
            return;
        }

        recognition = new SpeechRecognition();
        recognition.continuous = false; 
        recognition.interimResults = false;
        recognition.lang = langSelect.value; 

        recognition.onstart = function () {
            listening = true;
            micBtn.style.background = "#ef4444"; // Red for recording
            micBtn.style.transform = "scale(1.1)";
            micBtn.innerHTML = '<i class="fas fa-stop"></i>';
            chatBubble.innerText = "Listening...";
            chatBubble.style.display = "block";
        };

        recognition.onresult = function (event) {
            const text = event.results[0][0].transcript.trim();
            if (!text) return;
            
            chatBubble.innerText = `"${text}"`;
            const lower = text.toLowerCase();
            if (lower.includes("open cart") || lower.includes("open my cart") || lower === "cart" || lower.includes("bag")) {
                if (typeof openCartDrawer === "function") openCartDrawer();
                speak("Opening your cart drawer now.", langSelect.value);
                return;
            }
            if (lower.includes("sort by nearest") || lower.includes("sort nearest") || lower.includes("nearest shop")) {
                const sortSel = document.getElementById("sort-order");
                if (sortSel) {
                    sortSel.value = "distance";
                    if (typeof applySortAndRender === "function") applySortAndRender();
                } else {
                    window.location.href = "/user/search?sort=distance";
                }
                speak("Sorting nearby products by shortest distance.", langSelect.value);
                return;
            }
            if (lower.includes("show dairy") || lower.includes("dairy products") || lower.includes("milk")) {
                if (typeof filterCategory === "function") {
                    filterCategory("Dairy & Milk");
                } else {
                    window.location.href = "/user/search?cat=Dairy%20%26%20Milk";
                }
                speak("Showing dairy and milk items.", langSelect.value);
                return;
            }
            if (lower.includes("show grocery") || lower.includes("groceries")) {
                if (typeof filterCategory === "function") {
                    filterCategory("Grocery");
                } else {
                    window.location.href = "/user/search?cat=Grocery";
                }
                speak("Showing grocery staples.", langSelect.value);
                return;
            }
            if (lower.includes("open wishlist") || lower.includes("my wishlist") || lower.includes("favorites")) {
                window.location.href = "/user/wishlist";
                speak("Opening your wishlist.", langSelect.value);
                return;
            }
            if (lower.includes("open orders") || lower.includes("my orders") || lower.includes("track order")) {
                window.location.href = "/user/my-orders";
                speak("Opening your orders.", langSelect.value);
                return;
            }
            if (lower.includes("open reels") || lower.includes("show reels") || lower.includes("dundoo reels")) {
                window.location.href = "/user/reels";
                speak("Opening Dundoo Reels.", langSelect.value);
                return;
            }
            if (lower.startsWith("search ") || lower.startsWith("find ")) {
                const query = lower.replace(/^search\s+|^find\s+/, "").trim();
                if (query) {
                    window.location.href = "/user/search?q=" + encodeURIComponent(query);
                    speak("Searching for " + query, langSelect.value);
                    return;
                }
            }
            sendToAI(text);
        };

        recognition.onerror = function (event) {
            console.error("Global AI Recognition error:", event.error);
            resetUI();
            chatBubble.innerText = "I didn't catch that. Please try again.";
            setTimeout(() => chatBubble.style.display = "none", 3000);
        };

        recognition.onend = function () {
            resetUI();
        };

        recognition.start();
    }

    function resetUI() {
        listening = false;
        micBtn.style.background = "#16a34a";
        micBtn.style.transform = "scale(1)";
        micBtn.innerHTML = '<i class="fas fa-microphone"></i>';
    }

    // 4. Send to Backend AI
    function sendToAI(text) {
        if (controller) controller.abort();
        controller = new AbortController();
        
        // Let user know AI is thinking
        setTimeout(() => {
            if(chatBubble.style.display === "block") chatBubble.innerText = "Thinking...";
        }, 1000);

        fetch(aiEndpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text, lang: langSelect.value }),
            signal: controller.signal
        })
        .then(res => res.json())
        .then(data => {
            chatBubble.innerText = data.reply;
            
            // Speak the reply in the correct language
            speak(data.reply, langSelect.value, () => {
                // Execute action after speaking so it doesn't get cut off immediately
                if (data.action) {
                    window.location.href = data.action;
                } else {
                    setTimeout(() => chatBubble.style.display = "none", 3000);
                }
            });
        })
        .catch(err => {
            if (err.name === 'AbortError') return;
            console.error("AI Network error:", err);
            chatBubble.innerText = "Connection lost. Please try again.";
            setTimeout(() => chatBubble.style.display = "none", 3000);
        });
    }

    // 5. Native Browser Speech Synthesis (TTS)
    function speak(text, langCode, onEndCallback) {
        if (!text) {
            if(onEndCallback) onEndCallback();
            return;
        }

        speechSynthesis.cancel(); // Stop current speech
        speaking = true;

        const speech = new SpeechSynthesisUtterance(text);
        // Ensure the speaking voice matches the target language constraint
        speech.lang = langCode; 
        speech.rate = 1;
        speech.pitch = 1;

        speech.onend = () => {
            speaking = false;
            if(onEndCallback) onEndCallback();
        };

        speech.onerror = () => {
            speaking = false;
            if(onEndCallback) onEndCallback();
        };

        speechSynthesis.speak(speech);
    }

    // Toggle logic
    micBtn.addEventListener("click", () => {
        if (listening) {
            recognition.stop();
            resetUI();
        } else {
            startVoice();
        }
    });
});