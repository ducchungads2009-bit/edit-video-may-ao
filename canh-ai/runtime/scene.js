/* Runtime cảnh AI — gốc từ LumReels (github.com/lumtekvn/lumreels, MIT, xem ../LICENSE-LumReels.txt), sửa cho Nhamoi AI Edit:
 *   - window.CANH: dữ liệu khối canhAI trong plan.json (data, w, h, style của phong cách) — đọc từ #canh=<json> trên địa chỉ trang
 *   - seek(t) chờ font của chữ đang hiện tải xong (chữ tạo trong render không bị vẽ bằng font hệ thống ở khung đầu)
 *   - xem thử ngoài Remotion: #t=2.5 (tua tới giây 2.5) · #fontcheck=0,2,4 (ghi báo cáo font vào <script id="__fontreport">)
 * Nạp trong mọi cảnh bằng <script src="./lib/runtime/scene.js"></script>
 *
 * Cảnh gọi:  VideoScene.define({ duration: 8, fps: 30, width: 1080, height: 1920, render(t) { ... } })
 *   - render(t) vẽ TOÀN BỘ khung tại giây t (tất định, không phụ thuộc khung trước).
 *   - Có thể gọi lại nhiều lần, theo thứ tự bất kỳ (seek lùi, nhảy cóc).
 *
 * Runtime xuất ra:
 *   window.__scene = { duration, fps, width, height, seek(t) -> Promise, ready -> Promise }
 *   window.__timelines.main = GSAP timeline (paused) để HyperFrames seek được cùng hàm render.
 */
(function () {
  'use strict';
  var HP = new URLSearchParams(String(location.hash || '').replace(/^#/, ''));
  var CANH = { data: {}, w: 1080, h: 1920, style: {} };
  try { if (HP.get('canh')) { var _c = JSON.parse(HP.get('canh')); for (var _k in _c) CANH[_k] = _c[_k]; } } catch (e) { console.error('[scene] #canh hỏng', e); }
  CANH.data = CANH.data || {};
  window.CANH = CANH;
  var readyResolve;
  var ready = new Promise(function (r) { readyResolve = r; });
  window.__timelines = window.__timelines || {};

  // Không dùng requestAnimationFrame (HyperFrames cấm vì chạy theo đồng hồ thật).
  function nextFrame() { return Promise.resolve(); }

  function define(opts) {
    if (!opts || typeof opts.render !== 'function') throw new Error('VideoScene.define cần render(t)');
    var duration = Number(opts.duration) || 8;
    var fps = Number(opts.fps) || 30;
    var width = Number(opts.width) || 1080;
    var height = Number(opts.height) || 1920;
    var root = document.getElementById('root') || document.body.firstElementChild;
    if (root) {
      root.setAttribute('data-composition-id', 'main');
      root.setAttribute('data-start', '0');
      root.setAttribute('data-duration', String(duration));
      root.setAttribute('data-width', String(width));
      root.setAttribute('data-height', String(height));
      root.setAttribute('data-fps', String(fps));
    }
    var last = 0;
    var setupDone = false;
    function draw(t) {
      t = Math.max(0, Math.min(duration, Number(t) || 0));
      last = t;
      if (!setupDone) return;
      opts.render(t);
    }
    // setup chạy ĐỒNG BỘ ngay trong define để seek đầu tiên đã có DOM đầy đủ.
    var setupResult = null;
    try { setupResult = opts.setup ? opts.setup() : null; } catch (e) { console.error('[scene] setup lỗi', e); }
    if (setupResult && typeof setupResult.then === 'function') {
      setupResult.then(function () { setupDone = true; draw(last); });
    } else {
      setupDone = true;
    }

    // Cầu nối HyperFrames: timeline GSAP paused, một tween proxy gọi render(t).
    if (window.gsap) {
      var proxy = { t: 0 };
      var tl = window.gsap.timeline({ paused: true });
      tl.to(proxy, { t: duration, duration: duration, ease: 'none', onUpdate: function () { draw(proxy.t); } }, 0);
      window.__timelines.main = tl;
    }

    Promise.all([fontsReady(), setupResult])
      .then(function () { setupDone = true; draw(last); readyResolve(true); })
      .catch(function (e) { console.error('[scene] setup lỗi', e); readyResolve(false); });
    draw(0);

    window.__scene = {
      duration: duration, fps: fps, width: width, height: height, ready: ready,
      seek: function (t) {
        draw(t);
        // chữ mới xuất hiện ở khung này có thể dùng font chưa tải -> chờ rồi vẽ lại cho chắc
        return fontsReady().then(function (loaded) { if (loaded) draw(t); });
      },
      get time() { return last; },
    };
    previewHooks(window.__scene);
    return window.__scene;
  }

  // ---- tiện ích tất định cho cảnh ----
  function mulberry32(seed) {
    var a = seed >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      var t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function clamp(x, a, b) { return Math.max(a, Math.min(b, x)); }
  function prog(t, start, dur) { return clamp((t - start) / dur, 0, 1); }
  function lerp(a, b, k) { return a + (b - a) * k; }
  var ease = {
    linear: function (k) { return k; },
    outCubic: function (k) { return 1 - Math.pow(1 - k, 3); },
    inCubic: function (k) { return k * k * k; },
    inOutCubic: function (k) { return k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2; },
    outBack: function (k) { var c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(k - 1, 3) + c1 * Math.pow(k - 1, 2); },
    outExpo: function (k) { return k === 1 ? 1 : 1 - Math.pow(2, -10 * k); },
  };
  function fmtNum(n, sep) {
    sep = sep == null ? '.' : sep;
    var s = String(Math.round(Math.abs(n)));
    var out = s.replace(/\B(?=(\d{3})+(?!\d))/g, sep);
    return (n < 0 ? '-' : '') + out;
  }

  // ---- font ----
  var VI_SAMPLE = 'ẮẰẲẴẶ ẤẦẨẪẬ ĐƯƠ Ữ Ỷ Ệ Ọ đươ ệọ 0123456789';
  /** Chờ font tải xong. specs: mảng chuỗi CSS font ("800 120px 'Barlow Condensed'"); bỏ trống = mọi font
   *  mà các phần tử chữ trong trang đang dùng. Dùng TRƯỚC khi vẽ chữ lên canvas/WebGL. */
  function fontsReady(specs) {
    if (!document.fonts) return Promise.resolve();
    if (!specs) {
      var seen = {};
      specs = [];
      textElements().forEach(function (el) {
        var cs = getComputedStyle(el);
        var k = cs.fontStyle + ' ' + cs.fontWeight + ' 40px ' + cs.fontFamily;
        if (!seen[k]) { seen[k] = 1; specs.push(k); }
      });
    }
    var fresh = specs.filter(function (s) { return !LOADED[s]; });
    if (!fresh.length) return Promise.resolve(false);
    return Promise.all(fresh.map(function (s) { LOADED[s] = 1; return document.fonts.load(s, VI_SAMPLE).catch(function () {}); }))
      .then(function () { return document.fonts.ready; }).then(function () { return true; });
  }
  var LOADED = {};

  // ---- xem thử / kiểm font ngoài Remotion (Chrome headless: canh_ai.py thu / kiem) ----
  function previewHooks(sc) {
    var tp = HP.get('t'), fc = HP.get('fontcheck');
    if (tp == null && fc == null) return;
    sc.ready.then(function () {
      if (tp != null) return sc.seek(Number(tp) || 0).then(function () { document.documentElement.setAttribute('data-seeked', tp); });
      var times = String(fc).split(',').map(Number).filter(function (x) { return isFinite(x); });
      var out = [];
      return times.reduce(function (p, t) {
        return p.then(function () { return sc.seek(t); }).then(function () {
          fontReport().forEach(function (x) { x.t = t; out.push(x); });
          textElements().forEach(function (el) { // con số + font của nó (máy kiểm xem có phải font viết tay không)
            var own = Array.prototype.filter.call(el.childNodes, function (c) { return c.nodeType === 3; }).map(function (c) { return c.nodeValue; }).join('').trim();
            var cs = getComputedStyle(el);
            if (/\d/.test(own) && cs.display !== 'none' && cs.visibility !== 'hidden' && Number(cs.opacity) > 0)
              out.push({ kind: '_DIGITS', text: own.slice(0, 40), font: firstFamily(cs.fontFamily), t: t });
          });
        });
      }, Promise.resolve()).then(function () {
        var el = document.createElement('script');
        el.type = 'application/json'; el.id = '__fontreport';
        el.textContent = JSON.stringify({ duration: sc.duration, width: sc.width, height: sc.height, issues: out });
        document.body.appendChild(el);
      });
    }).catch(function (e) { console.error('[scene] xem thử lỗi', e); });
  }
  function textElements() {
    var out = [];
    var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    var n;
    while ((n = walker.nextNode())) {
      if (!n.nodeValue || !n.nodeValue.trim()) continue;
      var el = n.parentElement;
      if (!el || /^(SCRIPT|STYLE|NOSCRIPT)$/.test(el.tagName)) continue;
      if (out.indexOf(el) < 0) out.push(el);
    }
    return out;
  }
  function firstFamily(ff) { return String(ff).split(',')[0].trim().replace(/^["']|["']$/g, ''); }
  var GENERIC = /^(serif|sans-serif|monospace|cursive|fantasy|system-ui|ui-sans-serif|ui-serif|ui-monospace|emoji|math)$/i;
  /** Báo chữ đang hiển thị bằng font hệ thống / thiếu glyph. Engine gọi sau khi seek. */
  function fontReport() {
    var faces = {};
    document.fonts.forEach(function (f) {
      var fam = f.family.replace(/^["']|["']$/g, '');
      (faces[fam] = faces[fam] || []).push({ weight: f.weight, style: f.style });
    });
    var ctx = document.createElement('canvas').getContext('2d');
    var issues = [];
    textElements().forEach(function (el) {
      var cs = getComputedStyle(el);
      if (cs.display === 'none' || cs.visibility === 'hidden' || Number(cs.opacity) === 0) return;
      var text = Array.prototype.filter.call(el.childNodes, function (c) { return c.nodeType === 3; })
        .map(function (c) { return c.nodeValue; }).join('').replace(/\s+/g, ' ').trim();
      if (!text) return;
      var fam = firstFamily(cs.fontFamily);
      var base = cs.fontStyle + ' ' + cs.fontWeight + ' 100px ';
      // Cỡ chữ thật trên khung 1080 (tính cả scale của transform): < 28px khó đọc trên điện thoại.
      var fs = parseFloat(cs.fontSize) || 0;
      var r = el.getBoundingClientRect();
      var k = el.offsetHeight ? r.height / el.offsetHeight : 1;
      var eff = fs * (k > 0 && isFinite(k) ? k : 1);
      if (eff > 0 && eff < 28 && r.width > 0 && r.bottom > 0 && r.top < (CANH.h || 1920)) {
        issues.push({ kind: 'FONT_SMALL', text: text.slice(0, 40), font: fam, weight: cs.fontWeight, why: 'cỡ chữ ~' + Math.round(eff) + 'px < 28px, khó đọc trên điện thoại' });
      }
      if (text.indexOf('₫') >= 0) {
        issues.push({ kind: 'FONT_DONG', text: text.slice(0, 40), font: fam, weight: cs.fontWeight, why: 'ký hiệu "₫" nhiều font vẽ sai/lệch dòng — viết "đ" hoặc "VNĐ"' });
      }
      if (GENERIC.test(fam) || !faces[fam]) {
        issues.push({ kind: 'FONT_OUTSIDE', text: text.slice(0, 40), font: fam, weight: cs.fontWeight });
        return;
      }
      if (!document.fonts.check(base + '"' + fam + '"', text)) {
        issues.push({ kind: 'FONT_FALLBACK', text: text.slice(0, 40), font: fam, weight: cs.fontWeight, why: 'chưa tải/không có glyph' });
        return;
      }
      // Ký tự thiếu glyph: đo 2 lần với 2 fallback khác nhau; chữ có đủ glyph thì bề ngang bằng nhau.
      ctx.font = base + '"' + fam + '", monospace'; var a = ctx.measureText(text).width;
      ctx.font = base + '"' + fam + '", serif'; var b = ctx.measureText(text).width;
      if (Math.abs(a - b) > 0.5) {
        var bad = Array.from(new Set(Array.from(text))).filter(function (ch) {
          ctx.font = base + '"' + fam + '", monospace'; var x = ctx.measureText(ch).width;
          ctx.font = base + '"' + fam + '", serif'; return Math.abs(x - ctx.measureText(ch).width) > 0.5;
        }).join('');
        issues.push({ kind: 'FONT_FALLBACK', text: text.slice(0, 40), font: fam, weight: cs.fontWeight, why: 'thiếu glyph: ' + bad });
      }
      var w = Number(cs.fontWeight);
      var ok = faces[fam].some(function (f) { return Math.abs(Number(f.weight) - w) <= 100; });
      if (!ok) issues.push({ kind: 'FONT_WEIGHT', text: text.slice(0, 40), font: fam, weight: cs.fontWeight, why: 'không có độ đậm này, trình duyệt tự làm đậm/mảnh giả' });
    });
    return issues;
  }
  window.__fontReport = fontReport;

  window.VideoScene = { data: CANH.data, define: define, rng: mulberry32, fontsReady: fontsReady, clamp: clamp, prog: prog, lerp: lerp, ease: ease, fmtNum: fmtNum, ready: ready };
})();
