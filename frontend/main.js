/* ==========================================================================
   Eagle-1 64Bit — Frontend Scripts & Cross-Platform Download Management
   ========================================================================== */

(function () {
  'use strict';

  /* ---------- Platform Configurations & Download Links ---------- */
  const RELEASES_BASE = 'https://github.com/paulp143/Eagle-1-64Bit/releases/latest/download';
  const PLATFORMS = {
    windows: {
      name: 'Windows',
      file: 'Eagle-1-Windows.zip',
      ext: '.zip',
      size: '39 MB',
      version: 'v0.2.0',
      url: `${RELEASES_BASE}/Eagle-1-Windows.zip`,
      badge: 'Windows (x86_64)',
      summary: 'v0.2.0 · 39 MB · .zip',
      launchHint: 'Double-click Eagle-1.exe'
    },
    mac: {
      name: 'macOS',
      displayName: '<span class="preserve-case">macOS</span>',
      file: 'Eagle-1-macOS.zip',
      ext: '.zip',
      size: '42 MB',
      version: 'v0.2.0',
      url: `${RELEASES_BASE}/Eagle-1-macOS.zip`,
      dmgUrl: `${RELEASES_BASE}/Eagle-1-macOS.dmg`,
      badge: 'macOS (.app bundle)',
      summary: 'v0.2.0 · 42 MB · .zip / .dmg',
      launchHint: 'Drag Eagle-1.app to Applications'
    },
    linux: {
      name: 'Linux',
      displayName: 'Linux',
      file: 'Eagle-1-Linux.tar.gz',
      ext: '.tar.gz',
      size: '41 MB',
      version: 'v0.2.0',
      url: `${RELEASES_BASE}/Eagle-1-Linux.tar.gz`,
      badge: 'Linux (glibc / standalone)',
      summary: 'v0.2.0 · 41 MB · .tar.gz',
      launchHint: 'Run ./Eagle-1/Eagle-1'
    }
  };

  /* ---------- OS Auto-Detection ---------- */
  function detectOS() {
    const ua = (navigator.userAgent || '').toLowerCase();
    const platform = (navigator.userAgentData?.platform || navigator.platform || '').toLowerCase();

    if (platform.includes('mac') || ua.includes('macintosh') || ua.includes('mac os x')) {
      return 'mac';
    }
    if (platform.includes('linux') || ua.includes('linux') || ua.includes('x11')) {
      return 'linux';
    }
    return 'windows';
  }

  let currentOS = detectOS();

  /* ---------- UI Synchronization ---------- */
  function updateDownloadButtons(osKey) {
    const p = PLATFORMS[osKey] || PLATFORMS.windows;
    const displayOS = p.displayName || p.name;
    currentOS = osKey;

    // 1. Header Download Button
    const headerBtn = document.getElementById('headerDownloadBtn');
    if (headerBtn) {
      headerBtn.href = p.url;
      headerBtn.setAttribute('title', `Download ${p.file} (${p.size})`);
    }

    // 2. Hero Download Button
    const heroBtn = document.getElementById('heroDownloadBtn');
    const heroMeta = document.getElementById('heroDownloadMeta');
    const heroLabel = document.getElementById('heroDownloadLabel');
    if (heroBtn) {
      heroBtn.href = p.url;
      if (heroLabel) heroLabel.innerHTML = `Download for ${displayOS}`;
      if (heroMeta) heroMeta.textContent = p.summary;
    }

    // 3. Final Call-to-Action Button
    const finalBtn = document.getElementById('finalDownloadBtn');
    const finalMeta = document.getElementById('finalDownloadMeta');
    const finalLabel = document.getElementById('finalDownloadLabel');
    if (finalBtn) {
      finalBtn.href = p.url;
      if (finalLabel) finalLabel.innerHTML = `Download for ${displayOS}`;
      if (finalMeta) finalMeta.textContent = p.summary;
    }

    // 4. Hero Platform Pills
    document.querySelectorAll('.platform-pill').forEach(pill => {
      const match = pill.getAttribute('data-os') === osKey;
      pill.classList.toggle('active', match);
      pill.setAttribute('aria-pressed', match ? 'true' : 'false');
    });

    // 5. Install Section Tabs & Panels
    document.querySelectorAll('.tab-btn').forEach(tab => {
      const match = tab.getAttribute('data-tab') === osKey;
      tab.classList.toggle('active', match);
      tab.setAttribute('aria-selected', match ? 'true' : 'false');
    });

    document.querySelectorAll('.install-panel').forEach(panel => {
      const match = panel.getAttribute('data-os-panel') === osKey;
      panel.classList.toggle('active', match);
    });

    const installLabel = document.getElementById('installSectionLabel');
    if (installLabel) {
      installLabel.innerHTML = `Enlistment · ${displayOS}`;
    }
  }

  /* ---------- Event Handlers for Platform Toggles ---------- */
  function initPlatformSelectors() {
    // Hero pills click
    document.querySelectorAll('.platform-pill').forEach(pill => {
      pill.addEventListener('click', e => {
        e.preventDefault();
        const os = pill.getAttribute('data-os');
        if (os && PLATFORMS[os]) {
          updateDownloadButtons(os);
        }
      });
    });

    // Install section tabs click
    document.querySelectorAll('.tab-btn').forEach(tab => {
      tab.addEventListener('click', e => {
        e.preventDefault();
        const os = tab.getAttribute('data-tab');
        if (os && PLATFORMS[os]) {
          updateDownloadButtons(os);
        }
      });
    });

    // Alternative links in footer / final section
    document.querySelectorAll('[data-switch-os]').forEach(link => {
      link.addEventListener('click', e => {
        e.preventDefault();
        const os = link.getAttribute('data-switch-os');
        if (os && PLATFORMS[os]) {
          updateDownloadButtons(os);
          const installSec = document.getElementById('install');
          if (installSec) {
            installSec.scrollIntoView({ behavior: 'smooth' });
          }
        }
      });
    });

    // Initialize with detected OS
    updateDownloadButtons(currentOS);
  }

  /* ---------- Data-Driven Tables (Strikes & Rosters) ---------- */
  function initDataTables() {
    const strikes = [
      { n: "Machine Gun Dive", c: 3, px: 55, t: "55 px lane · 26 rounds" },
      { n: "Eagle 500kg Bomb", c: 1, px: 480, t: "480 px radius", hero: true },
      { n: "Cluster Bomb", c: 3, px: 280, t: "280 px · 10 bomblets" },
      { n: "Napalm Strike", c: 2, px: 300, t: "300 px fire wall" },
      { n: "Gas Strike", c: 2, px: 240, t: "240 px cloud" },
      { n: "Rocket Pods", c: 2, px: null, t: "3 guided missiles" },
      { n: "EMS Stun Strike", c: 2, px: 280, t: "280 px · 4.5 s stun" },
      { n: "Smoke Screen", c: 2, px: 280, t: "280 px radar cloud" }
    ];

    const tb = document.getElementById('strikeRows');
    if (tb) {
      tb.innerHTML = strikes.map(s => {
        const pips = [0, 1, 2].map(i => `<i class="${i < s.c ? '' : 'off'}"></i>`).join('');
        const foot = s.px
          ? `<div class="bar"><div class="track"><div class="fill" style="width:${(s.px / 480 * 100).toFixed(1)}%"></div></div><span class="val">${s.t}</span></div>`
          : `<div class="bar"><span class="val" style="text-align:left">${s.t}</span></div>`;
        return `<tr class="${s.hero ? 'hero-row' : ''}"><td>${s.n}</td><td><span class="pips" aria-label="${s.c} charges">${pips}</span></td><td>${foot}</td></tr>`;
      }).join('');
    }

    const hpRow = (who, role, hp, max) =>
      `<li><span class="who">${who}<small>${role}</small></span><span class="hp"><span class="track"><span class="fill" style="width:${(hp / max * 100).toFixed(1)}%"></span></span><span class="val">${hp} HP</span></span></li>`;

    const friendlies = document.getElementById('friendlies');
    if (friendlies) {
      friendlies.innerHTML = [
        ["Viper-1", "Squad lead · tactical rifle", 100],
        ["Viper-2", "Heavy · anti-air suppression", 100],
        ["Viper-3", "Scout · long-range marksman", 100],
        ["Viper-4", "Medic · keeps the squad standing", 100]
      ].map(r => hpRow(r[0], r[1], r[2], 300)).join('');
    }

    const hostiles = document.getElementById('hostiles');
    if (hostiles) {
      hostiles.innerHTML = [
        ["Trooper", "Fast infantry, laser blasters", 35],
        ["Heavy Bomber", "Targets your orbital base", 75],
        ["Walker", "Armored, rapid dual-pulse lasers", 120],
        ["Fabricator", "Builds reinforcements every 8 s", 220],
        ["Factory Strider", "Walking fortress, plasma cannon", 300]
      ].map(r => hpRow(r[0], r[1], r[2], 300)).join('');
    }

    const copyBtn = document.getElementById('copyBtn');
    const code = document.getElementById('srcCode');
    if (copyBtn && code) {
      copyBtn.addEventListener('click', () => {
        const done = () => {
          copyBtn.textContent = 'Copied';
          setTimeout(() => (copyBtn.textContent = 'Copy'), 1600);
        };
        const select = () => {
          const r = document.createRange();
          r.selectNodeContents(code);
          const s = getSelection();
          s.removeAllRanges();
          s.addRange(r);
          copyBtn.textContent = 'Selected · press Ctrl+C';
          setTimeout(() => (copyBtn.textContent = 'Copy'), 2400);
        };
        try {
          navigator.clipboard.writeText(code.textContent).then(done, select);
        } catch (e) {
          select();
        }
      });
    }
  }

  /* ---------- Hero Sortie Canvas Animation ---------- */
  function initHeroCanvas() {
    const cvs = document.getElementById('sky');
    if (!cvs) return;
    const ctx = cvs.getContext('2d');
    const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
    const flash = document.getElementById('flash');
    const hudK = document.getElementById('hudKills');
    const hudS = document.getElementById('hudSpeed');
    const hudW = document.getElementById('hudWave');

    const load = src => new Promise(r => {
      const i = new Image();
      i.onload = () => r(i);
      i.onerror = () => r(null);
      i.src = src;
    });

    let W = 0, H = 0, dpr = 1, map, ship, enemy, expl, shipShadow, enemyShadow;

    function silhouette(img) {
      const c = document.createElement('canvas');
      c.width = img.width;
      c.height = img.height;
      const x = c.getContext('2d');
      x.drawImage(img, 0, 0);
      x.globalCompositeOperation = 'source-in';
      x.fillStyle = '#000';
      x.fillRect(0, 0, c.width, c.height);
      return c;
    }

    function resize() {
      const r = cvs.getBoundingClientRect();
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      W = r.width;
      H = r.height;
      cvs.width = Math.round(W * dpr);
      cvs.height = Math.round(H * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    const S = {
      t: 0, scroll: 0, enemies: [], bullets: [], bolts: [], booms: [], sparks: [],
      trail: [], craters: [], nextEnemy: 0.6, nextShot: 0, nextBomb: 4.5, bomb: null,
      flashA: 0, kills: 0, ship: { x: 0, y: 0, a: 0, size: 96 }
    };
    const GROUND = 70;
    const narrow = () => W < 761;
    function shipBase() {
      return narrow() ? { x: W * 0.5, y: Math.min(H * 0.2, 175) } : { x: W * 0.68, y: H * 0.56 };
    }

    function spawnEnemy() {
      const b = shipBase(), spread = narrow() ? W * 0.38 : W * 0.22;
      S.enemies.push({
        x: b.x + (Math.random() * 2 - 1) * spread,
        y: -40,
        vy: 110 + Math.random() * 60,
        vx: (Math.random() * 2 - 1) * 20,
        hp: 3,
        size: narrow() ? 40 : 50,
        wob: Math.random() * 6,
        fire: 1 + Math.random() * 1.5
      });
    }

    function boom(x, y, scale) {
      S.booms.push({ x, y, f: 0, scale });
      for (let i = 0; i < 14; i++) {
        const a = Math.random() * 6.28, v = 60 + Math.random() * 220;
        S.sparks.push({ x, y, vx: Math.cos(a) * v, vy: Math.sin(a) * v, life: 0.5 + Math.random() * 0.5, max: 1 });
      }
    }

    function update(dt) {
      S.t += dt;
      S.scroll += GROUND * dt;
      const b = shipBase(), sh = S.ship;
      sh.size = Math.max(64, Math.min(120, W * 0.085));
      const nx = b.x + Math.sin(S.t * 0.55) * W * (narrow() ? 0.18 : 0.09) + Math.sin(S.t * 1.7) * 10;
      const ny = b.y + Math.sin(S.t * 0.8) * 14;
      const dx = (nx - sh.x) / Math.max(dt, 1e-3);
      sh.a += ((Math.max(-0.35, Math.min(0.35, dx * 0.004))) - sh.a) * Math.min(1, dt * 4);
      sh.bank = Math.max(0.72, 1 - Math.abs(sh.a) * 0.8);
      sh.x = nx;
      sh.y = ny;
      if (hudS) hudS.textContent = (4.6 + Math.sin(S.t * 0.8) * 1.1).toFixed(1);

      // afterburner
      const s = sh.size, h = s * 1.27;
      for (const side of [-1, 1]) {
        const ox = side * s * 0.16, oy = h * 0.43;
        const cx = sh.x + ox * Math.cos(sh.a) - oy * Math.sin(sh.a);
        const cy = sh.y + ox * Math.sin(sh.a) + oy * Math.cos(sh.a);
        S.trail.push({
          x: cx + (Math.random() - 0.5) * 3,
          y: cy,
          vy: GROUND + 120 + Math.random() * 60,
          vx: (Math.random() - 0.5) * 20 - Math.sin(sh.a) * 60,
          life: 0.45,
          max: 0.45,
          r: 3 + Math.random() * 3
        });
      }

      // enemies
      S.nextEnemy -= dt;
      if (S.nextEnemy <= 0) {
        spawnEnemy();
        S.nextEnemy = 1.1 + Math.random() * 1.2;
      }
      for (const e of S.enemies) {
        e.y += e.vy * dt;
        e.x += e.vx * dt + Math.sin(S.t * 2 + e.wob) * 0.6;
        e.fire -= dt;
        if (e.fire <= 0 && e.y > 20 && e.y < sh.y - 60) {
          e.fire = 1.4 + Math.random();
          S.bolts.push({ x: e.x, y: e.y + e.size * 0.4, vx: (Math.random() - 0.5) * 60, vy: 380 });
        }
      }

      // shooting
      S.nextShot -= dt;
      const target = S.enemies.find(e => e.y < sh.y - 40 && e.y > -10 && Math.abs(e.x - sh.x) < s * 1.1);
      if (target && S.nextShot <= 0) {
        S.nextShot = 0.13;
        for (const off of [-0.34, -0.14, 0.14, 0.34]) {
          const ox = off * s, oy = -h * 0.1;
          S.bullets.push({
            x: sh.x + ox * Math.cos(sh.a) - oy * Math.sin(sh.a),
            y: sh.y + ox * Math.sin(sh.a) + oy * Math.cos(sh.a),
            vx: Math.sin(sh.a) * 900,
            vy: -Math.cos(sh.a) * 900
          });
        }
      }

      for (const u of S.bullets) {
        u.x += u.vx * dt;
        u.y += u.vy * dt;
        for (const e of S.enemies) {
          if (e.hp > 0 && Math.abs(u.x - e.x) < e.size * 0.45 && Math.abs(u.y - e.y) < e.size * 0.45) {
            u.dead = 1;
            e.hp--;
            S.sparks.push({ x: u.x, y: u.y, vx: (Math.random() - 0.5) * 120, vy: -40, life: 0.25, max: 0.25 });
            if (e.hp <= 0) {
              boom(e.x, e.y, 1.6);
              S.kills++;
              if (hudK) hudK.textContent = S.kills;
              if (hudW) hudW.textContent = Math.min(5, 1 + Math.floor(S.kills / 8));
            }
            break;
          }
        }
      }
      S.enemies = S.enemies.filter(e => e.hp > 0 && e.y < H + 80);
      S.bullets = S.bullets.filter(u => !u.dead && u.y > -30);
      for (const o of S.bolts) {
        o.x += o.vx * dt;
        o.y += o.vy * dt;
      }
      S.bolts = S.bolts.filter(o => o.y < H + 30);

      // 500kg bomb run
      S.nextBomb -= dt;
      if (S.nextBomb <= 0 && !S.bomb) {
        S.bomb = {
          x: sh.x + (narrow() ? 0 : -W * 0.06),
          y: narrow() ? Math.max(70, sh.y - 80) : sh.y - H * 0.26,
          timer: 1.3,
          stage: 0
        };
        S.nextBomb = 9;
      }
      if (S.bomb) {
        const bb = S.bomb;
        bb.y += GROUND * dt;
        bb.timer -= dt;
        if (bb.stage === 0 && bb.timer <= 0) {
          bb.stage = 1;
          bb.timer = 1.1;
          bb.ring = 0;
          S.flashA = 0.55;
          boom(bb.x, bb.y, 3.2);
          for (let i = 0; i < 6; i++) {
            const a = (i / 6) * 6.28;
            boom(bb.x + Math.cos(a) * 50, bb.y + Math.sin(a) * 38, 1.8);
          }
          S.craters.push({ x: bb.x, y: bb.y, r: Math.min(W, H) * 0.12 });
          S.enemies.forEach(e => {
            if (Math.hypot(e.x - bb.x, e.y - bb.y) < Math.min(W, H) * 0.45) {
              e.hp = 0;
              boom(e.x, e.y, 1.6);
              S.kills++;
            }
          });
          if (hudK) hudK.textContent = S.kills;
          if (flash) {
            flash.classList.add('on');
            setTimeout(() => flash.classList.remove('on'), 1700);
          }
        }
        if (bb.stage === 1) {
          bb.ring += dt;
          if (bb.timer <= 0) S.bomb = null;
        }
      }
      for (const c of S.craters) c.y += GROUND * dt;
      S.craters = S.craters.filter(c => c.y < H + 200);
      S.flashA = Math.max(0, S.flashA - dt * 1.3);

      for (const p of S.trail) {
        p.x += p.vx * dt;
        p.y += p.vy * dt;
        p.life -= dt;
      }
      S.trail = S.trail.filter(p => p.life > 0);
      for (const p of S.sparks) {
        p.x += p.vx * dt;
        p.y += p.vy * dt + GROUND * dt;
        p.vx *= 0.96;
        p.vy *= 0.96;
        p.life -= dt;
      }
      S.sparks = S.sparks.filter(p => p.life > 0);
      for (const o of S.booms) {
        o.f += dt * 30;
        o.y += GROUND * dt;
      }
      S.booms = S.booms.filter(o => o.f < 23);
    }

    function drawGround() {
      if (!map) {
        ctx.fillStyle = '#16233a';
        ctx.fillRect(0, 0, W, H);
        return;
      }
      const sc = Math.max(W / map.width, (H / map.height) * 0.8) * 1.08;
      const tw = map.width * sc, th = map.height * sc, x0 = (W - tw) / 2;
      const off = S.scroll % (2 * th);
      for (let k = -2; k * th + off < H; k++) {
        const y = off + k * th;
        if (y + th < 0) continue;
        if (((k % 2) + 2) % 2 === 1) {
          ctx.save();
          ctx.translate(0, y + th);
          ctx.scale(1, -1);
          ctx.drawImage(map, x0, 0, tw, th);
          ctx.restore();
        } else {
          ctx.drawImage(map, x0, y, tw, th);
        }
      }
      ctx.fillStyle = 'rgba(8,14,28,.42)';
      ctx.fillRect(0, 0, W, H);
      const g = ctx.createRadialGradient(W * 0.62, H * 0.5, Math.min(W, H) * 0.2, W * 0.62, H * 0.5, Math.max(W, H) * 0.8);
      g.addColorStop(0, 'rgba(7,11,20,0)');
      g.addColorStop(1, 'rgba(7,11,20,.75)');
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, W, H);
    }

    function drawSprite(img, shadow, x, y, w, h, a, sx, lift) {
      if (shadow) {
        ctx.save();
        ctx.globalAlpha = 0.32;
        ctx.translate(x + lift, y + lift * 1.4);
        ctx.rotate(a);
        ctx.scale(sx * 0.82, 0.82);
        ctx.drawImage(shadow, -w / 2, -h / 2, w, h);
        ctx.restore();
      }
      ctx.save();
      ctx.translate(x, y);
      ctx.rotate(a);
      ctx.scale(sx, 1);
      ctx.drawImage(img, -w / 2, -h / 2, w, h);
      ctx.restore();
    }

    function draw() {
      ctx.imageSmoothingEnabled = true;
      drawGround();
      for (const c of S.craters) {
        const g = ctx.createRadialGradient(c.x, c.y, 0, c.x, c.y, c.r);
        g.addColorStop(0, 'rgba(20,14,10,.75)');
        g.addColorStop(0.6, 'rgba(40,28,20,.35)');
        g.addColorStop(1, 'rgba(40,28,20,0)');
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.ellipse(c.x, c.y, c.r, c.r * 0.8, 0, 0, 6.28);
        ctx.fill();
      }

      if (S.bomb && S.bomb.stage === 0) {
        const bb = S.bomb, r = Math.min(W, H) * 0.11, p = 0.6 + 0.4 * Math.sin(S.t * 18);
        ctx.save();
        ctx.strokeStyle = `rgba(226,67,47,${p})`;
        ctx.lineWidth = 2;
        ctx.setLineDash([8, 6]);
        ctx.beginPath();
        ctx.ellipse(bb.x, bb.y, r, r * 0.8, 0, 0, 6.28);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.beginPath();
        ctx.moveTo(bb.x - r * 1.25, bb.y);
        ctx.lineTo(bb.x - r * 0.35, bb.y);
        ctx.moveTo(bb.x + r * 0.35, bb.y);
        ctx.lineTo(bb.x + r * 1.25, bb.y);
        ctx.moveTo(bb.x, bb.y - r);
        ctx.lineTo(bb.x, bb.y - r * 0.3);
        ctx.moveTo(bb.x, bb.y + r * 0.3);
        ctx.lineTo(bb.x, bb.y + r);
        ctx.stroke();
        ctx.font = '12px "Share Tech Mono", monospace';
        ctx.fillStyle = `rgba(226,67,47,${p})`;
        ctx.fillText('500KG · TARGET', bb.x + r * 0.4, bb.y - r * 0.85);
        ctx.restore();
      }

      if (S.bomb && S.bomb.stage === 1) {
        const bb = S.bomb, k = bb.ring / 1.1, R = Math.min(W, H) * 0.55 * Math.sqrt(k);
        ctx.save();
        ctx.strokeStyle = `rgba(255,226,170,${(1 - k) * 0.85})`;
        ctx.lineWidth = 6 * (1 - k) + 1;
        ctx.beginPath();
        ctx.ellipse(bb.x, bb.y, R, R * 0.8, 0, 0, 6.28);
        ctx.stroke();
        ctx.restore();
      }

      ctx.save();
      ctx.globalCompositeOperation = 'lighter';
      for (const p of S.trail) {
        const k = p.life / p.max;
        ctx.fillStyle = `rgba(255,${Math.round(120 + 110 * k)},${Math.round(40 * k)},${k * 0.55})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r * (0.4 + k), 0, 6.28);
        ctx.fill();
      }
      ctx.restore();

      ctx.imageSmoothingEnabled = false;
      for (const e of S.enemies) {
        if (enemy) drawSprite(enemy, enemyShadow, e.x, e.y, e.size, e.size * 0.92, Math.PI, 1, 26);
      }

      const sh = S.ship;
      if (ship) drawSprite(ship, shipShadow, sh.x, sh.y, sh.size, sh.size * 1.27, sh.a, sh.bank, 48);
      ctx.imageSmoothingEnabled = true;

      ctx.save();
      ctx.globalCompositeOperation = 'lighter';
      ctx.lineCap = 'round';
      ctx.strokeStyle = 'rgba(255,214,90,.95)';
      ctx.lineWidth = 2.4;
      for (const u of S.bullets) {
        ctx.beginPath();
        ctx.moveTo(u.x, u.y);
        ctx.lineTo(u.x - u.vx * 0.016, u.y - u.vy * 0.016);
        ctx.stroke();
      }
      ctx.strokeStyle = 'rgba(255,70,50,.95)';
      ctx.lineWidth = 3;
      for (const o of S.bolts) {
        ctx.beginPath();
        ctx.moveTo(o.x, o.y);
        ctx.lineTo(o.x - o.vx * 0.03, o.y - o.vy * 0.03);
        ctx.stroke();
      }
      for (const p of S.sparks) {
        const k = p.life / p.max;
        ctx.fillStyle = `rgba(255,${Math.round(150 + 90 * k)},80,${k})`;
        ctx.fillRect(p.x - 1.5, p.y - 1.5, 3, 3);
      }
      ctx.restore();

      if (expl) {
        ctx.imageSmoothingEnabled = false;
        for (const o of S.booms) {
          const f = Math.min(22, Math.floor(o.f)), sz = 64 * o.scale * (narrow() ? 0.8 : 1);
          ctx.drawImage(expl, f * 64, 0, 64, 64, o.x - sz / 2, o.y - sz / 2, sz, sz);
        }
        ctx.imageSmoothingEnabled = true;
      }
      if (S.flashA > 0) {
        ctx.fillStyle = `rgba(255,240,210,${S.flashA})`;
        ctx.fillRect(0, 0, W, H);
      }
    }

    let running = false, visible = true, last = 0, raf = 0;
    function frame(ts) {
      const dt = Math.min(0.05, (ts - last) / 1000 || 0.016);
      last = ts;
      update(dt);
      draw();
      if (running) raf = requestAnimationFrame(frame);
    }

    function setRun(on) {
      if (on && !running && !reduce) {
        running = true;
        last = performance.now();
        raf = requestAnimationFrame(frame);
      } else if (!on && running) {
        running = false;
        cancelAnimationFrame(raf);
      }
    }

    Promise.all([
      load('./assets/battlefield.webp'),
      load('./assets/eagle1-sprite.png'),
      load('./assets/enemy-fighter.png'),
      load('./assets/explosion-sheet.png')
    ]).then(([m, s, e, x]) => {
      map = m;
      ship = s;
      enemy = e;
      expl = x;
      if (ship) shipShadow = silhouette(ship);
      if (enemy) enemyShadow = silhouette(enemy);
      resize();
      const b = shipBase();
      S.ship.x = b.x;
      S.ship.y = b.y;
      for (let i = 0; i < 150; i++) update(1 / 60);
      draw();
      if (!reduce) {
        new IntersectionObserver(es => {
          visible = es[0].isIntersecting;
          setRun(visible && !document.hidden);
        }).observe(cvs);
        document.addEventListener('visibilitychange', () => setRun(visible && !document.hidden));
        setRun(true);
      }
    });

    let rt;
    window.addEventListener('resize', () => {
      clearTimeout(rt);
      rt = setTimeout(() => {
        resize();
        if (!running) draw();
      }, 120);
    });
  }

  /* ---------- Initialize on DOM Ready ---------- */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      initPlatformSelectors();
      initDataTables();
      initHeroCanvas();
    });
  } else {
    initPlatformSelectors();
    initDataTables();
    initHeroCanvas();
  }
})();

