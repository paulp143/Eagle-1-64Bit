/**
 * Super Earth Defense Command — Eagle-1 Flight Engine
 * 
 * Performance & Responsiveness Optimizations:
 * - Direct rAF coordinate sampling (zero scroll event thrashing or layout trashing).
 * - Immediate follow response without compounding lag during rapid scroll wheel events.
 * - Hardware accelerated 3D transform rendering.
 */

document.addEventListener('DOMContentLoaded', () => {
  const eagle = document.getElementById('flyingEagle');
  const triggerFlybyBtn = document.getElementById('triggerFlybyBtn');

  // Viewport dimensions & initial coordinates
  const initialX = Math.max(20, window.innerWidth - 140);
  const initialY = 130;

  let currentViewportX = initialX;
  let currentViewportY = initialY;
  let currentHeading = 180;
  let bankRoll = 0;

  // Real-time cursor coordinates in page/document space
  let cursorPageX = window.scrollX + initialX + 36;
  let cursorPageY = window.scrollY + initialY;
  let hasMouseMoved = false;

  // Path history buffer: records [ { pageX, pageY, time } ]
  const pathHistory = [];
  const DELAY_MS = 60; // Crisp ~60ms response: maintains flight trail feel without sluggish drag

  let engineCutoffTimer = null;

  function shortestAngleDiff(target, current) {
    let diff = (target - current) % 360;
    if (diff > 180) diff -= 360;
    if (diff < -180) diff += 360;
    return diff;
  }

  // Mousemove: lightweight coordinate update
  window.addEventListener('mousemove', (e) => {
    hasMouseMoved = true;
    cursorPageX = window.scrollX + e.clientX;
    cursorPageY = window.scrollY + e.clientY;
  }, { passive: true });

  // Standby flank position when mouse hasn't been active
  function getStandbyPageCoords() {
    const scrollMax = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
    const scrollProgress = Math.min(1, Math.max(0, window.scrollY / scrollMax));
    const targetViewportY = 130 + scrollProgress * (window.innerHeight - 270);
    return {
      x: window.scrollX + (window.innerWidth - 135),
      y: window.scrollY + targetViewportY
    };
  }

  // 60 FPS Engine Loop (all sampling synchronized with screen refresh)
  function flightLoop() {
    if (eagle) {
      const now = performance.now();

      // Sample current cursor/page position once per frame
      let sampleX, sampleY;
      if (hasMouseMoved) {
        sampleX = cursorPageX;
        sampleY = cursorPageY;
      } else {
        const standby = getStandbyPageCoords();
        sampleX = standby.x;
        sampleY = standby.y;
      }

      // Record frame sample
      pathHistory.push({
        pageX: sampleX,
        pageY: sampleY,
        time: now
      });

      // Maintain lean history buffer
      while (pathHistory.length > 2 && now - pathHistory[0].time > 400) {
        pathHistory.shift();
      }

      const targetTime = now - DELAY_MS;
      let targetPoint = null;

      // Locate breadcrumb at target playback time
      let index = 0;
      while (index < pathHistory.length - 1 && pathHistory[index + 1].time <= targetTime) {
        index++;
      }

      const p1 = pathHistory[index];
      const p2 = pathHistory[index + 1] || p1;

      if (p2 !== p1 && p2.time > p1.time) {
        const ratio = Math.max(0, Math.min(1, (targetTime - p1.time) / (p2.time - p1.time)));
        targetPoint = {
          pageX: p1.pageX + (p2.pageX - p1.pageX) * ratio,
          pageY: p1.pageY + (p2.pageY - p1.pageY) * ratio
        };
      } else {
        targetPoint = { pageX: p1.pageX, pageY: p1.pageY };
      }

      // Convert page coordinates to current viewport position
      const scrollX = window.scrollX;
      const scrollY = window.scrollY;

      const targetViewportX = targetPoint.pageX - scrollX - 36;
      const targetViewportY = targetPoint.pageY - scrollY;

      const dx = targetViewportX - currentViewportX;
      const dy = targetViewportY - currentViewportY;
      const dist = Math.hypot(dx, dy);

      // Snappy, responsive interpolation
      currentViewportX += dx * 0.32;
      currentViewportY += dy * 0.32;

      if (dist > 1.5) {
        const rad = Math.atan2(dx, -dy);
        const targetHeading = (rad * (180 / Math.PI) + 360) % 360;

        const angleDelta = shortestAngleDiff(targetHeading, currentHeading);
        bankRoll = Math.max(-20, Math.min(20, angleDelta * 0.45));

        currentHeading += angleDelta * 0.22;

        eagle.classList.add('engines-on');
        clearTimeout(engineCutoffTimer);
      } else {
        bankRoll *= 0.85;
        if (!engineCutoffTimer) {
          engineCutoffTimer = setTimeout(() => {
            if (eagle) eagle.classList.remove('engines-on');
            engineCutoffTimer = null;
          }, 100);
        }
      }

      const totalRenderAngle = currentHeading + bankRoll;
      eagle.style.transform = `translate3d(${currentViewportX}px, ${currentViewportY}px, 0) rotate(${totalRenderAngle}deg)`;
    }

    requestAnimationFrame(flightLoop);
  }

  // Pre-seed buffer & run
  pathHistory.push({
    pageX: cursorPageX,
    pageY: cursorPageY,
    time: performance.now()
  });

  if (eagle) {
    eagle.style.transform = `translate3d(${currentViewportX}px, ${currentViewportY}px, 0) rotate(${currentHeading}deg)`;
  }

  requestAnimationFrame(flightLoop);

  // Evasive Maneuver button
  if (triggerFlybyBtn) {
    triggerFlybyBtn.addEventListener('click', (e) => {
      e.preventDefault();
      if (eagle) {
        eagle.classList.add('engines-on');
        const startX = currentViewportX;
        currentViewportX = Math.max(30, currentViewportX - 180);
        currentHeading += 360;
        
        setTimeout(() => {
          currentViewportX = startX;
          setTimeout(() => {
            eagle.classList.remove('engines-on');
          }, 300);
        }, 400);
      }
    });
  }

  // Copy Snippet functionality for dev page
  const copyBtns = document.querySelectorAll('.btn-copy-code');
  copyBtns.forEach(btn => {
    btn.addEventListener('click', async () => {
      const targetId = btn.getAttribute('data-target');
      const targetEl = document.getElementById(targetId);
      if (targetEl) {
        try {
          await navigator.clipboard.writeText(targetEl.innerText);
          const original = btn.innerText;
          btn.innerText = 'COPIED!';
          btn.style.color = '#ffcc00';
          setTimeout(() => {
            btn.innerText = original;
            btn.style.color = '';
          }, 2000);
        } catch (err) {
          console.warn('Copy failed:', err);
        }
      }
    });
  });

  // Dynamic GitHub Release Version Check
  const releaseInfoBadge = document.getElementById('releaseInfoBadge');
  if (releaseInfoBadge) {
    fetch('https://api.github.com/repos/paulp143/Eagle-1-64Bit/releases/latest')
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => {
        if (data && data.tag_name) {
          releaseInfoBadge.innerText = `${data.tag_name} • STANDALONE EXECUTABLE`;
        }
      })
      .catch(() => {
        // Fallback intact
      });
  }
});
