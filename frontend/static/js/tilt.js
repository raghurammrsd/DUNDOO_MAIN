document.addEventListener('DOMContentLoaded', () => {
    // Basic 3D effect handler
    const initTilt = () => {
        const tiltElements = document.querySelectorAll('.tilt-effect');

        tiltElements.forEach(el => {
            el.addEventListener('mousemove', (e) => {
                const rect = el.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                
                // Calculate percentage based rotation (max 10 degrees)
                const xPct = (x / rect.width - 0.5) * 2;
                const yPct = (y / rect.height - 0.5) * 2;
                
                // Y rotation is determined by X position. X rotation by Y position.
                // Decrease the 10 multiplier to 4 for a much subtler, premium effect.
                const rotateY = xPct * 4;
                const rotateX = -yPct * 4;

                // Add slight glare/light reflection shift
                el.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.02, 1.02, 1.02)`;
                
                // If it has an image inside, lift the image slightly for parallax
                const innerImg = el.querySelector('img');
                if(innerImg) {
                    innerImg.style.transform = 'translateZ(20px)';
                    innerImg.style.transition = 'transform 0.1s ease-out';
                }
            });

            el.addEventListener('mouseleave', () => {
                el.style.transform = `perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)`;
                
                const innerImg = el.querySelector('img');
                if(innerImg) {
                    innerImg.style.transform = 'translateZ(0)';
                }
            });
            
            // Set base transition for smoothing out the exit
            el.style.transition = 'transform 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
            el.style.transformStyle = 'preserve-3d';
        });
    };

    initTilt();
    
    // Mutation observer to attach tilt to dynamically added elements (like search results)
    const observer = new MutationObserver((mutations) => {
        let shouldReinit = false;
        mutations.forEach(m => {
            if(m.addedNodes.length > 0) shouldReinit = true;
        });
        if(shouldReinit) initTilt();
    });
    
    // Observer config to look at the whole document body for child additions
    if(document.body) {
        observer.observe(document.body, { childList: true, subtree: true });
    }
});
