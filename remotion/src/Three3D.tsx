/* KHỐI 3D THẬT — dựng bằng Three.js (WebGL) trên nền trong suốt, đè lên video. Mỗi khung tính lại từ số khung (không phụ thuộc
   khung trước) nên xuất nhiều luồng / tua trong trình chỉnh sửa vẫn khớp. Xuất video nên bật card đồ hoạ (render.py tự thêm --gl=angle
   trên Mac / Windows).
   - text3dPro: CHỮ KHỐI 3D THẬT — có độ dày, vát cạnh, phản chiếu kim loại, vệt sáng chạy qua, bóng đổ. Tiếng Việt đủ dấu.
     {text ("\n" xuống dòng), lines?: [{text, size?, mat?, color?}], sub (dòng phụ nhỏ), font: be-vietnam-pro | montserrat | playfair,
      mat: gold | silver | chrome | copper | rose | white | black | color (+ color), subMat, subColor, size (px, 190), depth (0.28 × cỡ),
      x (px tâm, giữa khung), y (px tâm, 650), width (px tối đa, 920), anim: drop | rise | flip | spin | zoom, stagger (giây giữa
      2 chữ, 0.06), glint (vệt sáng, true), shadow (bóng đổ, true), sway (lắc nhẹ, true)}
   - photo3d: ẢNH BAY 3D — ảnh bay vào, lật, xếp vòng xoay quanh người (nửa sau nằm SAU người như orbit), phóng một ảnh ra trước
     mặt đúng lúc nhắc tới, cuối khối bay ra khỏi khung.
     {items: ["assets/a.jpg" | {src, caption}] (chỉ ảnh), cx (0–1), cy (px) — bỏ trống = theo mặt (như orbit), rx (px bán kính, 380),
      tilt (độ nghiêng vòng, 18), period (giây / vòng, 7), dir (1 | -1), cardW (px, 250), look: polaroid | clean | glass,
      flyIn (true), exit (true), backDim (0–1, 0.25), hero: [{i (ảnh số, từ 0), at (giây tính từ lúc khối hiện), hold (giây, 1.5)}],
      heroX / heroY (px, bỏ trống = bên đối diện người nói), heroScale (1.7), behind (false = cả vòng trước người)}
     _half: 'back' | 'front' (EditPlan tự tách khi có lớp người)
   - object3d: VẬT THỂ 3D đặt trên mặt đất của cảnh — ghim vị trí, ngôi nhà, bảng giá, mô hình .glb — có bóng đổ.
     {items: [{kind: pin | house | tag | model, x, y (px điểm chạm đất trên khung), size (px cao, 260), at (giây trễ), color,
      text / sub (bảng giá), mat (chữ bảng giá), src (file .glb khi kind = model), spin (true = xoay), turn (độ xoay sẵn),
      lift (px nhấc lên khỏi mặt đất — vd ghim lơ lửng trên mái nhà = cỡ nhà)}]
      — hoặc 1 vật ghi thẳng các trường đó ở khối; dời theo vật bằng trackPts (scripts/track.py) như khối thường} */
import React, {useEffect, useLayoutEffect, useRef, useState} from 'react';
import {OffthreadVideo, continueRender, delayRender, useCurrentFrame, useVideoConfig} from 'remotion';
import * as THREE from 'three';
import {FontLoader} from 'three/examples/jsm/loaders/FontLoader.js';
import {TextGeometry} from 'three/examples/jsm/geometries/TextGeometry.js';
import {RoomEnvironment} from 'three/examples/jsm/environments/RoomEnvironment.js';
import {RoundedBoxGeometry} from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import {GLTFLoader} from 'three/examples/jsm/loaders/GLTFLoader.js';
import {Line2} from 'three/examples/jsm/lines/Line2.js';
import {LineGeometry} from 'three/examples/jsm/lines/LineGeometry.js';
import {LineMaterial} from 'three/examples/jsm/lines/LineMaterial.js';
import {mediaSrc} from './Media';
import {FR, fy} from './frame';
import F_BVP from './fonts3d/be-vietnam-pro.json';
import F_MON from './fonts3d/montserrat.json';
import F_PF from './fonts3d/playfair.json';

const TAU = Math.PI * 2;
const cl = (x: number) => Math.min(1, Math.max(0, x));
const pr = (t: number, a: number, d: number) => cl((t - a) / Math.max(1e-6, d));
const E = {
  back: (x: number) => 1 + 2.70158 * (x - 1) ** 3 + 1.70158 * (x - 1) ** 2,
  cub: (x: number) => 1 - (1 - x) ** 3,
  inc: (x: number) => x * x * x,
  io: (x: number) => (x < 0.5 ? 4 * x * x * x : 1 - (-2 * x + 2) ** 3 / 2),
  bounce: (x: number) => {
    const n = 7.5625, d = 2.75;
    if (x < 1 / d) return n * x * x;
    if (x < 2 / d) return n * (x -= 1.5 / d) * x + 0.75;
    if (x < 2.5 / d) return n * (x -= 2.25 / d) * x + 0.9375;
    return n * (x -= 2.625 / d) * x + 0.984375;
  },
};
const PPU = 100; // px trên khung ứng với 1 đơn vị 3D ở mặt phẳng z = 0

/* ---------- font & chất liệu ---------- */
const FONTS3D: Record<string, any> = {'be-vietnam-pro': F_BVP, montserrat: F_MON, playfair: F_PF, 'playfair-display': F_PF};
const fontCache: Record<string, any> = {};
export const font3d = (k?: string) => {
  const key = k && FONTS3D[k] ? k : 'be-vietnam-pro';
  return (fontCache[key] ||= new FontLoader().parse(FONTS3D[key]));
};
export const MATS3D: Record<string, [number, number, number]> = {
  gold: [0xe2b24f, 1, 0.18], silver: [0xe4e7ec, 1, 0.16], chrome: [0xffffff, 1, 0.06], copper: [0xc77a4c, 1, 0.3],
  rose: [0xe8b4a2, 1, 0.24], white: [0xf3eee4, 0.1, 0.45], black: [0x1f1f22, 0.6, 0.3],
};
const mkMat = (m?: string, color?: string) => {
  if (color && (!m || m === 'color' || !MATS3D[m])) return new THREE.MeshStandardMaterial({color: new THREE.Color(color), metalness: 0.3, roughness: 0.35});
  const v = MATS3D[m || 'gold'] || MATS3D.gold;
  return new THREE.MeshStandardMaterial({color: v[0], metalness: v[1], roughness: v[2]});
};

/* ---------- dựng / huỷ cảnh WebGL ---------- */
type GLS = {renderer: THREE.WebGLRenderer; scene: THREE.Scene; camera: THREE.PerspectiveCamera; canvas: HTMLCanvasElement; [k: string]: any};
const mkGL = (cv: HTMLCanvasElement, fov: number, envI = 0.8): GLS => {
  const renderer = new THREE.WebGLRenderer({canvas: cv, alpha: true, antialias: true, preserveDrawingBuffer: true});
  renderer.setPixelRatio(1);
  renderer.setSize(FR.w, FR.h, false);
  renderer.setClearColor(0x000000, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.1;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  const scene = new THREE.Scene();
  const pm = new THREE.PMREMGenerator(renderer);
  scene.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture;
  (scene as any).environmentIntensity = envI;
  pm.dispose();
  scene.add(new THREE.HemisphereLight(0xffffff, 0x777777, 0.9));
  const camera = new THREE.PerspectiveCamera(fov, FR.w / FR.h, 0.1, 500);
  const D = FR.h / 2 / PPU / Math.tan((fov / 2) * (Math.PI / 180));
  camera.position.set(0, 0, D);
  camera.lookAt(0, 0, 0);
  return {renderer, scene, camera, canvas: cv, D};
};
const disposeGL = (s: GLS | null) => {
  if (!s) return;
  s.scene.traverse((o: any) => {
    o.geometry?.dispose?.();
    for (const m of Array.isArray(o.material) ? o.material : o.material ? [o.material] : []) {
      m.map?.dispose?.();
      m.dispose?.();
    }
  });
  s.scene.environment?.dispose?.();
  s.renderer.dispose();
  s.renderer.forceContextLoss();
};
/** điểm trên khung (px) -> điểm 3D ở mặt phẳng z = 0 (camera nhìn thẳng) */
const W0 = (x: number, y: number) => new THREE.Vector3((x - FR.w / 2) / PPU, (FR.h / 2 - y) / PPU, 0);
/** tia từ camera qua điểm (px) cắt mặt phẳng z = zw */
const onZ = (cam: THREE.Camera, x: number, y: number, zw: number) => {
  const v = new THREE.Vector3((x / FR.w) * 2 - 1, 1 - (y / FR.h) * 2, 0.5).unproject(cam).sub(cam.position).normalize();
  return cam.position.clone().add(v.multiplyScalar((zw - cam.position.z) / v.z));
};

/** canvas WebGL: dựng cảnh 1 lần (build), mỗi khung gọi update rồi vẽ. key đổi -> canvas mới, dựng lại */
const GLCanvas: React.FC<{k: string; ready: boolean; build: (cv: HTMLCanvasElement) => GLS; update: (s: GLS) => void; api?: React.MutableRefObject<any>}> = ({k, ready, build, update, api}) => {
  const ref = useRef<HTMLCanvasElement>(null);
  const st = useRef<GLS | null>(null);
  if (api) api.current = {redraw: () => { if (st.current) { update(st.current); st.current.renderer.render(st.current.scene, st.current.camera); } }};
  useLayoutEffect(() => {
    if (!ready || !ref.current) return;
    if (st.current && st.current.canvas !== ref.current) {
      disposeGL(st.current);
      st.current = null;
    }
    if (!st.current) st.current = build(ref.current);
    update(st.current);
    st.current.renderer.render(st.current.scene, st.current.camera);
  });
  useEffect(() => () => {
    disposeGL(st.current);
    st.current = null;
  }, []);
  return <canvas key={k} ref={ref} width={FR.w} height={FR.h} style={{position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none'}} />;
};

/* ---------- tải ảnh / mô hình (giữ khung chờ tới khi tải xong) ---------- */
const imgCache = new Map<string, Promise<HTMLImageElement | null>>();
const loadImg = (src: string) => {
  if (!imgCache.has(src))
    imgCache.set(src, new Promise((res) => {
      const im = new Image();
      im.crossOrigin = 'anonymous';
      im.onload = () => res(im);
      im.onerror = () => res(null);
      im.src = mediaSrc(src);
    }));
  return imgCache.get(src)!;
};
const glbCache = new Map<string, Promise<any>>();
const loadGlb = (src: string) => {
  if (!glbCache.has(src)) glbCache.set(src, new GLTFLoader().loadAsync(mediaSrc(src)).catch(() => null));
  return glbCache.get(src)!;
};
function useLoad<T>(key: string, fn: () => Promise<T>): T | null {
  const [v, setV] = useState<{k: string; v: T} | null>(null);
  const [h] = useState(() => delayRender('Khối 3D: tải ảnh / mô hình', {timeoutInMilliseconds: 60000}));
  const done = useRef(false);
  useEffect(() => {
    let live = true;
    fn().then((r) => {
      if (live) setV({k: key, v: r});
      if (!done.current) {
        done.current = true;
        continueRender(h);
      }
    });
    return () => {
      live = false;
    };
  }, [key]);
  useEffect(() => () => {
    if (!done.current) {
      done.current = true;
      continueRender(h);
    }
  }, []);
  return v && v.k === key ? v.v : null;
}
const fontReady = (fams: string[] = []) => (typeof document !== 'undefined' && (document as any).fonts
  ? Promise.all(['Be Vietnam Pro', ...fams.filter(Boolean)].flatMap((fm) => ['400', '700', '900'].map((w) => (document as any).fonts.load(`${w} 40px "${fm}"`, 'Ăâđ').catch(() => null))))
  : Promise.resolve())

/* ---------- chữ khối ---------- */
type Line = {text: string; size: number; mat?: string; color?: string};
const buildLine = (font: any, str: string, size: number, mat: THREE.Material, depth: number) => {
  const G = font.data.glyphs, RES = font.data.resolution;
  const g = new THREE.Group();
  const L: THREE.Group[] = [];
  let x = 0;
  for (const ch of [...(str || '').normalize('NFC')]) {
    const gl = G[ch] || G[ch.toUpperCase()];
    if (!gl) continue;
    if (ch.trim()) {
      const geo = new TextGeometry(G[ch] ? ch : ch.toUpperCase(), {font, size, depth, curveSegments: 6, bevelEnabled: true, bevelThickness: depth * 0.2, bevelSize: size * 0.022, bevelSegments: 3});
      geo.computeBoundingBox();
      const b = geo.boundingBox!, cx = (b.min.x + b.max.x) / 2;
      geo.translate(-cx, 0, -depth / 2);
      const m = new THREE.Mesh(geo, mat);
      m.castShadow = true;
      const p = new THREE.Group();
      p.add(m);
      p.position.x = x + cx;
      g.add(p);
      L.push(p);
    }
    x += (gl.ha / RES) * size;
  }
  for (const p of L) {
    p.position.x -= x / 2;
    p.userData.b = p.position.clone();
  }
  g.userData = {w: x, L};
  return g;
};

export const Text3DPro: React.FC<{e: any; dur: number}> = ({e, dur}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const size = (e.size ?? 190) / PPU;
  const lines: Line[] = (e.lines && e.lines.length ? e.lines : String(e.text ?? '2,5 TỶ').split('\n').map((s: string) => ({text: s})))
    .filter((l: any) => l && String(l.text || '').trim())
    .map((l: any) => ({text: String(l.text), size: (l.size ?? 1) * size, mat: l.mat, color: l.color}));
  if (e.sub) lines.push({text: String(e.sub), size: size * (e.subSize ?? 0.34), mat: e.subMat || (e.subColor ? 'color' : 'white'), color: e.subColor});
  const key = JSON.stringify([lines, e.font, e.mat, e.color, e.depth, e.width, e.x, e.y, e.size, e.shadow, e.noShadow, FR.w, FR.h]);
  const build = (cv: HTMLCanvasElement) => {
    const s = mkGL(cv, 30, 0.9);
    const font = font3d(e.font);
    const root = new THREE.Group();
    s.scene.add(root);
    const maxW = (e.width ?? 920) / PPU;
    const depth = (e.depth ?? 0.28) * size;
    const groups: THREE.Group[] = [];
    let total = 0;
    lines.forEach((l, i) => {
      const mat = mkMat(l.mat || e.mat || (e.color ? 'color' : 'gold'), l.color || (l.mat ? undefined : e.color));
      const g = buildLine(font, l.text, l.size, mat, i === lines.length - 1 && e.sub ? depth * 0.35 : depth);
      const sc = Math.min(1, maxW / Math.max(0.01, g.userData.w));
      g.scale.setScalar(sc);
      g.userData.h = l.size * 1.28 * sc;
      g.userData.sc = sc;
      total += g.userData.h;
      groups.push(g);
      root.add(g);
    });
    let yy = total / 2;
    for (const g of groups) {
      yy -= g.userData.h;
      g.position.y = yy + g.userData.h * 0.12;
    }
    const c = W0(e.x ?? FR.w / 2, e.y ?? fy(650));
    root.position.copy(c);
    const kl = new THREE.DirectionalLight(0xffffff, 1.7);
    kl.position.set(c.x - 2.5, c.y + 3.5, 10);
    kl.target.position.copy(c);
    kl.castShadow = e.shadow !== false && !e.noShadow;
    const half = maxW / 2 + 2;
    Object.assign(kl.shadow.camera, {left: -half, right: half, top: half, bottom: -half, near: 1, far: 40});
    kl.shadow.mapSize.set(2048, 2048);
    kl.shadow.radius = 6;
    kl.shadow.bias = -0.0005;
    const sweep = new THREE.DirectionalLight(0xfff2d6, 0);
    sweep.target.position.copy(c);
    s.scene.add(kl, kl.target, sweep, sweep.target);
    if (e.shadow !== false && !e.noShadow) {
      const wall = new THREE.Mesh(new THREE.PlaneGeometry(60, 60), new THREE.ShadowMaterial({opacity: 0.24}));
      wall.position.set(c.x, c.y, -depth * 1.3);
      wall.receiveShadow = true;
      s.scene.add(wall);
    }
    return Object.assign(s, {root, groups, sweep, c});
  };
  const update = (s: GLS) => {
    const t = f / fps, T = dur / fps;
    const all = s.groups.flatMap((g: THREE.Group, gi: number) => g.userData.L.map((p: THREE.Group) => ({p, gi})));
    const mains = all.filter((x: any) => !(e.sub && x.gi === s.groups.length - 1));
    const st = Math.min(e.stagger ?? 0.06, 0.9 / Math.max(1, mains.length));
    const anim = e.anim || 'drop';
    let landed = 0;
    mains.forEach(({p}: any, i: number) => {
      const t0 = 0.05 + i * st, a = pr(t, t0, 0.75), b = E.back(a), c = E.cub(a), u = p.userData.b, sz = lines[0].size;
      landed = Math.max(landed, t0 + 0.75);
      p.visible = a > 0;
      p.rotation.set(0, 0, 0);
      p.position.copy(u);
      p.scale.setScalar(1);
      if (anim === 'drop') {
        p.rotation.x = (1 - b) * -1.6;
        p.position.y = u.y + (1 - c) * 1.8 * sz;
        p.position.z = (1 - c) * -1.2 * sz;
      } else if (anim === 'rise') {
        p.scale.set(1, Math.max(0.001, b), 1);
        p.position.y = u.y - (1 - c) * 0.3 * sz;
      } else if (anim === 'flip') {
        p.rotation.y = (1 - b) * -Math.PI / 2;
      } else if (anim === 'spin') {
        p.rotation.y = (1 - c) * TAU;
        p.scale.setScalar(Math.max(0.001, c));
      } else {
        p.position.z = (1 - c) * 8;
        p.scale.setScalar(Math.max(0.001, 0.3 + 0.7 * c));
      }
    });
    if (e.sub) {
      const g = s.groups[s.groups.length - 1], a = pr(t, landed - 0.2, 0.6);
      g.visible = a > 0;
      for (const p of g.userData.L) {
        p.position.copy(p.userData.b);
        p.position.z = (1 - E.cub(a)) * 1.5;
      }
      g.scale.setScalar(g.userData.sc * Math.max(0.001, 0.6 + 0.4 * E.back(a)));
    }
    const out = E.inc(pr(t, T - 0.35, 0.35));
    s.root.scale.setScalar(Math.max(0.001, 1 - out));
    s.root.rotation.y = e.sway === false || e.noSway ? 0 : Math.sin(t * 0.9) * 0.08 * pr(t, landed - 0.3, 1);
    s.root.rotation.x = e.sway === false || e.noSway ? 0 : Math.sin(t * 0.7) * 0.03 * pr(t, landed - 0.3, 1);
    const g = pr(t, landed - 0.1, 1.4);
    s.sweep.intensity = e.glint === false || e.noGlint || g <= 0 || g >= 1 ? 0 : 2.6 * Math.sin(g * Math.PI);
    s.sweep.position.set(s.c.x - 7 + 14 * E.io(g), s.c.y + 1.5, 6);
  };
  return <GLCanvas k={key} ready build={build} update={update} />;
};

/* ---------- ảnh bay 3D ---------- */
const isVid = (s: string) => /\.(mp4|mov|m4v|webm|mkv)$/i.test(s || '');
const cardTex = (im: HTMLImageElement | null, look: string, cap: string, ratio: number) => {
  const w = 600, h = Math.round(w * ratio);
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  const x = c.getContext('2d')!;
  const pol = look === 'polaroid';
  const P = pol ? 26 : look === 'clean' ? 10 : 0;
  const capH = pol ? 104 : 0;
  x.fillStyle = pol || look === 'clean' ? '#fbfaf6' : '#111';
  x.fillRect(0, 0, w, h);
  const bw = w - P * 2, bh = h - P * 2 - capH + (pol ? P : 0);
  if (im) {
    const s = Math.max(bw / im.width, bh / im.height), dw = im.width * s, dh = im.height * s;
    x.save();
    x.beginPath();
    x.rect(P, P, bw, bh);
    x.clip();
    x.drawImage(im, P + (bw - dw) / 2, P + (bh - dh) / 2, dw, dh);
    x.restore();
  }
  if (look === 'glass') {
    const g = x.createLinearGradient(0, 0, w, h);
    g.addColorStop(0, 'rgba(255,255,255,.32)');
    g.addColorStop(0.38, 'rgba(255,255,255,0)');
    g.addColorStop(0.75, 'rgba(255,255,255,0)');
    g.addColorStop(1, 'rgba(255,255,255,.14)');
    x.fillStyle = g;
    x.fillRect(0, 0, w, h);
    x.strokeStyle = 'rgba(255,255,255,.7)';
    x.lineWidth = 6;
    x.strokeRect(3, 3, w - 6, h - 6);
  }
  if (pol && cap) {
    x.fillStyle = '#24211c';
    let fs = 40;
    x.font = `700 ${fs}px "Be Vietnam Pro", sans-serif`;
    while (x.measureText(cap).width > w - 60 && fs > 22) x.font = `700 ${(fs -= 2)}px "Be Vietnam Pro", sans-serif`;
    x.fillText(cap, 30, h - 40);
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  return t;
};

/** vị trí + hướng của ảnh i theo kiểu xếp (layout): ring | fan | stack | wall | helix. d: độ sâu -1 (sau) .. 1 (trước) */
const layoutPose = (e: any, i: number, n: number, t: number, C: THREE.Vector3, cw: number, ch: number) => {
  const lay = e.layout || 'ring';
  const dir = e.dir === -1 ? -1 : 1, P = Math.max(1.5, e.period ?? 7);
  const R = (e.rx ?? 380) / PPU;
  const p = new THREE.Vector3(), q = new THREE.Quaternion();
  let d = 1, front = false;
  if (lay === 'fan') {
    const spread = ((e.spread ?? 70) * Math.PI) / 180, u = n > 1 ? i / (n - 1) - 0.5 : 0;
    const sway = Math.sin((t * TAU) / P) * 0.12;
    const a = u * spread + sway;
    const piv = C.clone().add(new THREE.Vector3(0, -ch * 0.9, 0));
    p.set(Math.sin(a) * ch * 1.15, Math.cos(a) * ch * 1.15, i * 0.02).add(piv);
    q.setFromEuler(new THREE.Euler(-0.08, Math.sin(t * 0.8) * 0.15, -a));
    front = true;
  } else if (lay === 'stack') {
    const step = P / Math.max(1, n), k = Math.floor(t / step), u = (t - k * step) / step;
    const r = (((i - k) % n) + n) % n;
    const lift = E.io(pr(u, 0.55, 0.45));
    let rf = r - (r > 0 ? lift : 0);
    const jit = Math.sin(i * 12.9898) * 0.06;
    p.set(rf * 0.05 * cw, -rf * 0.04 * ch, -rf * 0.35).add(C);
    q.setFromEuler(new THREE.Euler(-0.05, -0.12, jit + rf * 0.02));
    if (r === 0 && lift > 0) {
      const a = lift * Math.PI;
      p.set(Math.sin(a) * cw * 1.3, Math.sin(a) * ch * 0.25, -lift * (n - 1) * 0.35 + Math.sin(a) * 0.8).add(C);
      q.setFromEuler(new THREE.Euler(-0.05, -0.12 + lift * 0.6, jit + lift * 0.4));
    }
    d = 1 - (2 * rf) / Math.max(1, n - 1);
    front = true;
  } else if (lay === 'wall') {
    const cols = e.cols ?? (n > 4 ? 3 : 2), rows = Math.ceil(n / cols);
    const cx = (i % cols) - (cols - 1) / 2, cy = Math.floor(i / cols) - (rows - 1) / 2;
    const g = new THREE.Group();
    g.position.copy(C);
    g.rotation.set(0.06, ((e.wallTurn ?? -24) * Math.PI) / 180 + Math.sin((t * TAU) / (P * 2)) * 0.1, 0);
    g.updateMatrixWorld();
    p.set(cx * cw * 1.12, -cy * ch * 1.08, 0).applyMatrix4(g.matrixWorld);
    q.copy(g.quaternion);
    front = true;
  } else {
    const ang = (dir * TAU * t) / P;
    const a = ang + (lay === 'helix' ? i * 0.95 : (i * TAU) / n), bob = Math.sin(t * 2.1 + i * 1.7) * 0.06;
    const y = lay === 'helix' ? (i - (n - 1) / 2) * ch * 0.55 + bob : bob;
    const qT = new THREE.Quaternion().setFromEuler(new THREE.Euler(((e.tilt ?? (lay === 'helix' ? 6 : 18)) * Math.PI) / 180, 0, 0));
    p.set(Math.sin(a) * R, y, Math.cos(a) * R).applyQuaternion(qT).add(C);
    q.setFromEuler(new THREE.Euler(0, a, Math.sin(t * 1.3 + i) * 0.06)).premultiply(qT);
    d = Math.cos(a);
  }
  return {p, q, d, front};
};

export type Photo3DEl = {layout?: string; spread?: number; cols?: number; wallTurn?: number; items?: any[]; cx?: number; cy?: number; rx?: number; tilt?: number; period?: number; dir?: number; cardW?: number; look?: string;
  flyIn?: boolean; exit?: boolean; backDim?: number; hero?: {i: number; at: number; hold?: number}[]; heroX?: number; heroY?: number; heroScale?: number; _half?: 'back' | 'front'};

export const Photo3D: React.FC<{e: Photo3DEl; dur: number}> = ({e, dur}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const items = (e.items || []).map((x: any) => (typeof x === 'string' ? {src: x} : x)).filter((x: any) => x && x.src && !isVid(x.src));
  const srcs = items.map((x: any) => x.src);
  const imgs = useLoad('p3d:' + srcs.join('|'), () => fontReady().then(() => Promise.all(srcs.map(loadImg))));
  const look = e.look || 'polaroid';
  const ratio = look === 'polaroid' ? 1.32 : 1.25;
  const key = JSON.stringify([srcs, items.map((x: any) => x.caption || x.label || ''), look, e.cardW, FR.w, FR.h, !!imgs]);
  if (!items.length) return null;
  const build = (cv: HTMLCanvasElement) => {
    const s = mkGL(cv, 50, 0.7);
    const kl = new THREE.DirectionalLight(0xfff6ea, 1.5);
    kl.position.set(-6, 8, 12);
    s.scene.add(kl);
    const cw = (e.cardW ?? 250) / PPU, ch = cw * ratio;
    const back = new THREE.MeshStandardMaterial({color: 0xf4f1ea, roughness: 0.6});
    const cards = items.map((it: any, i: number) => {
      const m = new THREE.MeshStandardMaterial({map: cardTex(imgs?.[i] || null, look, it.caption || it.label || '', ratio), roughness: 0.45});
      const mesh = new THREE.Mesh(new THREE.BoxGeometry(cw, ch, 0.02), [back, back, back, back, m, m]);
      s.scene.add(mesh);
      return mesh;
    });
    let seed = 11;
    const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
    const start = cards.map(() => ({
      p: new THREE.Vector3(-FR.w / PPU * (0.75 + rnd() * 0.3), (rnd() - 0.5) * FR.h / PPU * 0.6, -6 - rnd() * 6),
      q: new THREE.Quaternion().setFromEuler(new THREE.Euler(rnd() * 3 - 1.5, rnd() * 6, rnd() * 2 - 1)),
    }));
    return Object.assign(s, {cards, start});
  };
  const update = (s: GLS) => {
    const t = f / fps, T = dur / fps, n = s.cards.length;
    const C = W0((e.cx ?? 0.5) * FR.w, e.cy ?? fy(1150));
    const dim = Math.max(0, Math.min(1, e.backDim ?? 0.25));
    const hx = e.heroX ?? ((e.cx ?? 0.5) > 0.5 ? FR.w * 0.32 : FR.w * 0.68), hy = e.heroY ?? fy(1000);
    const cw = (e.cardW ?? 250) / PPU, ch = cw * ratio;
    s.cards.forEach((c: THREE.Mesh, i: number) => {
      const L = layoutPose(e, i, n, t, C, cw, ch);
      const out = e.exit === false ? 0 : E.inc(pr(t, T - 0.95 + i * 0.05, 0.8));
      if (out > 0) {
        const dir = L.p.clone().sub(C).setY(0);
        if (dir.lengthSq() < 1e-4) dir.set(i % 2 ? 1 : -1, 0, 0.3);
        L.p.add(dir.normalize().multiplyScalar(out * 9)).add(new THREE.Vector3(0, out * 3, 0));
      }
      if (e.flyIn === false) {
        const k = E.back(pr(t, i * 0.05, 0.6));
        c.position.lerpVectors(C, L.p, Math.max(0, k));
        c.quaternion.copy(L.q);
        c.scale.setScalar(Math.max(0.001, Math.min(1, k)));
      } else {
        const p = pr(t, 0.05 + i * 0.13, 1.1);
        c.position.lerpVectors(s.start[i].p, L.p, E.cub(p));
        c.quaternion.slerpQuaternions(s.start[i].q, L.q, E.io(p));
        c.scale.setScalar(1);
      }
      let hv = 0;
      for (const h of e.hero || []) {
        if (h && h.i === i) hv = Math.max(hv, E.io(pr(t, h.at, 0.65)) - E.io(pr(t, h.at + 0.65 + (h.hold ?? 1.5), 0.65)));
      }
      if (hv > 0) {
        const P = onZ(s.camera, hx, hy, s.D * 0.38);
        P.y += Math.sin(t * 2) * 0.05;
        const qh = new THREE.Quaternion().setFromEuler(new THREE.Euler(-0.04, ((e.cx ?? 0.5) > 0.5 ? 0.16 : -0.16) + Math.sin(t * 1.4) * 0.05, 0));
        c.position.lerp(P, hv);
        c.quaternion.slerp(qh, hv);
        c.scale.setScalar(1 + hv * (Math.max(0.5, (e.heroScale ?? 1.7) * 0.62) - 1));
      }
      c.renderOrder = Math.round(c.position.z * 100);
      const front = hv > 0.3 || c.position.z > C.z + 0.01 || L.front;
      c.visible = e._half === 'back' ? !front : e._half === 'front' ? front : true;
      const lit = hv > 0 ? 1 : 1 - dim * (1 - (L.d + 1) / 2);
      for (const m of c.material as THREE.MeshStandardMaterial[]) m.color.setScalar(lit);
    });
  };
  return <GLCanvas k={key} ready={!!imgs} build={build} update={update} />;
};

/* ---------- vật thể 3D trên mặt đất ---------- */
const houseModel = (color?: string) => {
  const g = new THREE.Group();
  const M = (c: number | string, r = 0.7) => new THREE.MeshStandardMaterial({color: new THREE.Color(c as any), roughness: r});
  const box = (w: number, h: number, d: number, m: THREE.Material, x: number, y: number, z: number) => {
    const o = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m);
    o.position.set(x, y, z);
    o.castShadow = o.receiveShadow = true;
    g.add(o);
    return o;
  };
  box(1.7, 1, 1.3, M(0xf1e9da), 0, 0.5, 0);
  box(0.8, 0.7, 0.9, M(0xe6dccb), 1.05, 0.35, 0.15);
  const roof = new THREE.Mesh(new THREE.ConeGeometry(1.35, 0.75, 4), M(color || 0xb5573b, 0.6));
  roof.rotation.y = Math.PI / 4;
  roof.scale.set(1, 1, 0.78);
  roof.position.y = 1.37;
  roof.castShadow = true;
  g.add(roof);
  box(0.32, 0.55, 0.04, M(0x6b4a33), 0, 0.28, 0.66);
  for (const x of [-0.55, 0.55]) box(0.32, 0.3, 0.04, M(0x5d86a6, 0.2), x, 0.58, 0.66);
  box(0.3, 0.25, 0.04, M(0x5d86a6, 0.2), 1.05, 0.38, 0.61);
  g.scale.setScalar(1 / 1.75);
  const w = new THREE.Group();
  w.add(g);
  return w;
};
const pinModel = (color?: string) => {
  const g = new THREE.Group();
  const red = new THREE.MeshStandardMaterial({color: new THREE.Color(color || '#e2483a'), roughness: 0.3, metalness: 0.1});
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.32, 40, 20), red);
  head.position.y = 0.68;
  const cone = new THREE.Mesh(new THREE.ConeGeometry(0.22, 0.55, 40), red);
  cone.rotation.x = Math.PI;
  cone.position.y = 0.3;
  const dot = new THREE.Mesh(new THREE.SphereGeometry(0.12, 20, 10), new THREE.MeshStandardMaterial({color: 0xffffff, roughness: 0.3}));
  dot.position.set(0, 0.71, 0.24);
  head.castShadow = cone.castShadow = true;
  g.add(head, cone, dot);
  g.scale.setScalar(1 / 1.0);
  return g;
};
const tagModel = (it: any) => {
  const g = new THREE.Group();
  const font = font3d(it.font);
  const main = buildLine(font, String(it.text || '3,2 TỶ'), 0.5, mkMat(it.mat || 'gold', it.color), 0.12);
  const subTxt = it.sub ? buildLine(font, String(it.sub), 0.19, new THREE.MeshStandardMaterial({color: 0x2c2a26, roughness: 0.6}), 0.03) : null;
  const wMain = main.userData.w, wSub = subTxt ? subTxt.userData.w : 0;
  const W = Math.max(1.6, Math.min(3.4, Math.max(wMain, wSub) + 0.5)), H = subTxt ? 1.05 : 0.8;
  main.scale.setScalar(Math.min(1, (W - 0.4) / Math.max(0.01, wMain)));
  const panel = new THREE.Mesh(new RoundedBoxGeometry(W, H, 0.14, 4, 0.08), new THREE.MeshStandardMaterial({color: new THREE.Color(it.bg || '#fbfaf6'), roughness: 0.4}));
  panel.castShadow = true;
  panel.position.y = H / 2;
  main.position.set(0, subTxt ? H * 0.42 : H * 0.28, 0.08);
  g.add(panel, main);
  if (subTxt) {
    subTxt.scale.setScalar(Math.min(1, (W - 0.4) / Math.max(0.01, wSub)));
    subTxt.position.set(0, H * 0.13, 0.08);
    g.add(subTxt);
  }
  g.scale.setScalar(1 / H);
  g.userData.billboard = true;
  return g;
};

export const Object3D: React.FC<{e: any; dur: number}> = ({e, dur}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const items: any[] = (e.items && e.items.length ? e.items : [{kind: e.kind || 'pin', x: e.x, y: e.y, size: e.size, color: e.color, text: e.text, sub: e.sub, src: e.src, spin: e.spin, mat: e.mat, font: e.font}]).filter(Boolean);
  const glbs = items.filter((it) => it.kind === 'model' && it.src).map((it) => it.src);
  const models = useLoad('o3d:' + glbs.join('|'), () => Promise.all(glbs.map(loadGlb)));
  const key = JSON.stringify([items, e.pitch, e.shadow, e.noShadow, FR.w, FR.h, !!models]);
  const build = (cv: HTMLCanvasElement) => {
    const s = mkGL(cv, 40, 0.75);
    const pitch = (e.pitch ?? 24) * (Math.PI / 180);
    s.camera.position.set(0, Math.sin(pitch) * s.D, Math.cos(pitch) * s.D);
    s.camera.lookAt(0, 0, 0);
    s.camera.updateMatrixWorld();
    const sun = new THREE.DirectionalLight(0xffffff, 2);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    sun.shadow.radius = 5;
    sun.shadow.bias = -0.0005;
    const ground = new THREE.Mesh(new THREE.PlaneGeometry(400, 400), new THREE.ShadowMaterial({opacity: e.shadow === false || e.noShadow ? 0 : 0.35}));
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    s.scene.add(sun, sun.target, ground);
    const ray = new THREE.Raycaster();
    const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
    let mi = 0;
    const objs = items.map((it) => {
      ray.setFromCamera(new THREE.Vector2(((it.x ?? FR.w / 2) / FR.w) * 2 - 1, 1 - ((it.y ?? fy(1150)) / FR.h) * 2), s.camera);
      const hit = new THREE.Vector3();
      if (!ray.ray.intersectPlane(plane, hit)) hit.set(0, 0, 0);
      const up = hit.clone().add(new THREE.Vector3(0, 1, 0)).project(s.camera), p0 = hit.clone().project(s.camera);
      const ppu = Math.abs(up.y - p0.y) * (FR.h / 2);
      const h = (it.size ?? 260) / Math.max(1, ppu);
      let o: THREE.Object3D;
      if (it.kind === 'house') o = houseModel(it.color);
      else if (it.kind === 'tag') o = tagModel(it);
      else if (it.kind === 'model') {
        const m = models?.[mi++];
        o = new THREE.Group();
        if (m?.scene) {
          const sc = m.scene.clone(true);
          sc.traverse((x: any) => {
            if (x.isMesh) x.castShadow = x.receiveShadow = true;
          });
          const bb = new THREE.Box3().setFromObject(sc), sz = bb.getSize(new THREE.Vector3()), ct = bb.getCenter(new THREE.Vector3());
          sc.position.set(-ct.x, -bb.min.y, -ct.z);
          const w = new THREE.Group();
          w.add(sc);
          w.scale.setScalar(1 / Math.max(1e-6, sz.y));
          o.add(w);
        }
      } else o = pinModel(it.color);
      const holder = new THREE.Group();
      holder.add(o);
      holder.position.copy(hit);
      holder.userData = {it, h, base: hit.clone(), o, ppu};
      s.scene.add(holder);
      return holder;
    });
    const bb = new THREE.Box3();
    objs.forEach((o: THREE.Group) => bb.expandByPoint(o.position));
    const ctr = bb.isEmpty() ? new THREE.Vector3() : bb.getCenter(new THREE.Vector3());
    const span = Math.max(4, ...objs.map((o: THREE.Group) => o.userData.h * 3), bb.isEmpty() ? 0 : bb.getSize(new THREE.Vector3()).length());
    sun.position.set(ctr.x + span * 0.6, span * 2, ctr.z + span * 0.5);
    sun.target.position.copy(ctr);
    Object.assign(sun.shadow.camera, {left: -span, right: span, top: span, bottom: -span, near: 0.5, far: span * 6});
    return Object.assign(s, {objs});
  };
  const update = (s: GLS) => {
    const t = f / fps, T = dur / fps;
    const out = E.inc(pr(t, T - 0.35, 0.35));
    s.objs.forEach((hd: THREE.Group, i: number) => {
      const {it, h, base, o, ppu} = hd.userData;
      const lift = (it.lift ?? (it.kind === 'tag' ? (it.size ?? 260) * 0.15 : 0)) / Math.max(1, ppu);
      const t0 = it.at ?? 0.15 + i * 0.35, a = pr(t, t0, it.kind === 'pin' ? 0.9 : 0.8);
      hd.visible = a > 0;
      hd.position.copy(base);
      hd.rotation.set(0, ((it.turn ?? (it.kind === 'house' ? -25 : 0)) * Math.PI) / 180, 0);
      let sc = h;
      if (it.kind === 'pin') {
        hd.position.y = base.y + lift + (1 - E.bounce(a)) * h * 3 + (a >= 1 ? Math.sin(t * 3) * h * 0.04 : 0);
        hd.rotation.y = it.spin === false ? 0 : t * 2;
      } else if (it.kind === 'tag') {
        sc = h * Math.max(0.001, E.back(a));
        hd.position.y = base.y + lift + (a >= 1 ? Math.sin(t * 2.2) * h * 0.03 : 0);
      } else {
        hd.position.y = base.y + lift;
        o.scale.set(Math.max(0.001, E.cub(a)), Math.max(0.001, E.back(a)), Math.max(0.001, E.cub(a)));
        if (it.spin) hd.rotation.y += t * 0.8;
      }
      hd.scale.setScalar(Math.max(0.001, sc * (1 - out)));
      if (o.userData.billboard) hd.quaternion.copy(s.camera.quaternion);
    });
  };
  return <GLCanvas k={key} ready={!!models} build={build} update={update} />;
};

/* ---------- MÀN HÌNH 3D: video / ảnh / trang chữ trong khung 3D TỰ THIẾT KẾ ----------
   screen3d: {look (kiểu dựng sẵn — điểm xuất phát): holo | glass | device | phone | curved | neon | tv | billboard | card | custom,
    frame: {…} (THIẾT KẾ KHUNG — ghi đè từng thông số của kiểu dựng sẵn, xem FRAME_DOC), pageStyle: {…} (kiểu trang chữ),
    pages: [{src (ảnh | video), from, volume} | {title, text ("\n" = dòng mới), sub, style?: {…}}], x, y (px tâm), w (px rộng),
    ratio (cao / rộng), tiltY / tiltX (độ), enter: unfold | fly | flip | rise | fade, float (lơ lửng, true), at: [giây chuyển trang],
    swipes / handPts (scripts/tay.py), handFollow (0–1), handOver, touch}
   FRAME_DOC — frame: {
    curve: độ cong ngang (0 = phẳng, 40–90 = màn hình cong), corner: bo góc (0–0.5 × cạnh ngắn),
    bezel: {w: px viền, depth: px dày, color, metal 0–1, rough 0–1} (w 0 = không khung),
    plate: {color, opacity} (tấm nền sau nội dung — kính mờ / kính tối), inset: tỉ lệ vùng nội dung (0.8–1),
    glow: {color, width (px nét), halo (0–1 quầng sáng), pulse (true = thở sáng)}, neon: {color, color2?, width, flicker (true)},
    corners: bracket | dot | none (góc kiểu HUD), scan: lines | led | grid | none (+ scanColor, scanOpacity),
    reflection: 0–1 (vệt bóng kính chéo), shadow: 0–1 (bóng đổ mềm phía sau), notch: true (tai thỏ điện thoại), buttons: true (nút cạnh),
    stand: true (chân đế TV / màn hình), transition: slide | fade | flip (chuyển trang)}
   pageStyle: {bg: "#màu" | ["#màu1", "#màu2"] (chuyển sắc) | "none", ink (màu chữ), accent (màu nhấn), align: left | center,
    font (tên font đã có trong tool, vd "Montserrat"), glow: true (chữ neon phát sáng), titleSize (px, 92)} */
const isVidSrc = (s?: string) => !!s && /\.(mp4|mov|m4v|webm|mkv)$/i.test(s);
export const SCREEN_LOOKS: Record<string, {frame: any; page: any; ratio?: number; w?: number; enter?: string}> = {
  holo: {frame: {curve: 0, corner: 0.02, bezel: {w: 0}, plate: {color: '#06283a', opacity: 0.42}, inset: 0.92, glow: {color: '#5ad1ff', width: 4, halo: 0.6}, corners: 'bracket', scan: 'lines', scanColor: '#5ad1ff', transition: 'slide'},
    page: {bg: 'none', ink: '#ffffff', accent: '#5ad1ff'}, enter: 'unfold'},
  glass: {frame: {corner: 0.05, bezel: {w: 0}, plate: {color: '#ffffff', opacity: 0.3}, inset: 0.94, glow: {color: '#ffffff', width: 3, halo: 0}, reflection: 0.5, shadow: 0.25},
    page: {bg: 'rgba(255,255,255,.55)', ink: '#15171a', accent: '#d4a23c'}, enter: 'fly'},
  device: {frame: {corner: 0.05, bezel: {w: 14, depth: 16, color: '#17191c', metal: 0.6, rough: 0.3}, inset: 1, reflection: 0.25, shadow: 0.35},
    page: {bg: '#111418', ink: '#ffffff', accent: '#d4a23c'}, ratio: 0.66, w: 640, enter: 'fly'},
  phone: {frame: {corner: 0.16, bezel: {w: 12, depth: 20, color: '#1b1c1f', metal: 0.75, rough: 0.25}, inset: 1, notch: true, buttons: true, reflection: 0.3, shadow: 0.35},
    page: {bg: '#0f1115', ink: '#ffffff', accent: '#4fd18b'}, ratio: 2.05, w: 380, enter: 'rise'},
  curved: {frame: {curve: 70, corner: 0.03, bezel: {w: 10, depth: 14, color: '#101114', metal: 0.5}, inset: 1, reflection: 0.3, shadow: 0.3, transition: 'fade'},
    page: {bg: '#0d0f12', ink: '#ffffff', accent: '#ffb547'}, ratio: 0.48, w: 900, enter: 'fade'},
  neon: {frame: {corner: 0.08, bezel: {w: 0}, plate: {color: '#0a0014', opacity: 0.55}, inset: 0.88, neon: {color: '#ff3df2', color2: '#3df2ff', width: 6, flicker: true}, transition: 'fade'},
    page: {bg: 'none', ink: '#ffffff', accent: '#ff3df2', glow: true, align: 'center'}, enter: 'fade'},
  tv: {frame: {corner: 0.01, bezel: {w: 9, depth: 28, color: '#1d1e21', metal: 0.4}, inset: 1, stand: true, reflection: 0.2, shadow: 0.3},
    page: {bg: '#0d0f12', ink: '#ffffff', accent: '#e94b3c'}, ratio: 0.5625, w: 700, enter: 'rise'},
  billboard: {frame: {corner: 0.0, bezel: {w: 20, depth: 26, color: '#2a2b2e', metal: 0.3, rough: 0.6}, inset: 1, scan: 'led', scanOpacity: 0.35, shadow: 0.3},
    page: {bg: '#050505', ink: '#ffd84a', accent: '#ff5a1f', align: 'center'}, ratio: 0.5, w: 820, enter: 'flip'},
  card: {frame: {corner: 0.06, bezel: {w: 0}, plate: {color: '#ffffff', opacity: 1}, inset: 0.94, shadow: 0.55},
    page: {bg: '#ffffff', ink: '#15171a', accent: '#c8902e'}, enter: 'fly'},
};
const mergeDeep = (a: any, b: any): any => {
  if (!b) return a;
  const o: any = {...a};
  for (const k of Object.keys(b)) o[k] = b[k] && typeof b[k] === 'object' && !Array.isArray(b[k]) && a?.[k] && typeof a[k] === 'object' ? mergeDeep(a[k], b[k]) : b[k];
  return o;
};
const roundRectPath = (x: CanvasRenderingContext2D, X: number, Y: number, w: number, h: number, r: number) => {
  x.beginPath();
  x.roundRect(X, Y, w, h, Math.max(0, Math.min(r, w / 2, h / 2)));
};
const pageTex = (pg: any, im: HTMLImageElement | null, ratio: number, st: any, corner: number) => {
  const w = 1024, h = Math.round(w * ratio);
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  const x = c.getContext('2d')!;
  const rr = corner * Math.min(w, h);
  x.save();
  roundRectPath(x, 0, 0, w, h, rr);
  x.clip();
  if (im) {
    const s = Math.max(w / im.width, h / im.height), dw = im.width * s, dh = im.height * s;
    x.drawImage(im, (w - dw) / 2, (h - dh) / 2, dw, dh);
  } else {
    const bg = st.bg ?? 'none';
    if (Array.isArray(bg)) {
      const g = x.createLinearGradient(0, 0, w, h);
      bg.forEach((col: string, k: number) => g.addColorStop(k / Math.max(1, bg.length - 1), col));
      x.fillStyle = g;
      x.fillRect(0, 0, w, h);
    } else if (bg !== 'none') {
      x.fillStyle = bg;
      x.fillRect(0, 0, w, h);
    }
    const ink = st.ink || '#ffffff', acc = st.accent || '#5ad1ff', fam = `"${st.font || 'Be Vietnam Pro'}", "Be Vietnam Pro", sans-serif`;
    const center = st.align === 'center';
    const pad = 70;
    x.textAlign = center ? 'center' : 'left';
    const X = center ? w / 2 : pad;
    const glow = (col: string, b: number) => {
      x.shadowColor = st.glow ? col : 'transparent';
      x.shadowBlur = st.glow ? b : 0;
    };
    const lines = String(pg.text || '').split('\n').filter(Boolean);
    let fs = st.titleSize ?? 92;
    const lh = 78;
    const blockH = (pg.title ? fs + 40 : 0) + lines.length * lh;
    let y = center ? Math.max(pad + fs, (h - blockH) / 2 + fs * 0.8) : pad + 120;
    if (!center) {
      x.fillStyle = acc;
      x.fillRect(pad, pad, 90, 10);
    }
    if (pg.title) {
      x.font = `900 ${fs}px ${fam}`;
      while (x.measureText(pg.title).width > w - pad * 2 && fs > 40) x.font = `900 ${(fs -= 4)}px ${fam}`;
      x.fillStyle = st.glow ? acc : ink;
      glow(acc, 40);
      x.fillText(pg.title, X, y);
      if (st.glow) x.fillText(pg.title, X, y);
      y += fs * 0.6 + 40;
    }
    x.font = `700 50px ${fam}`;
    for (const ln of lines) {
      glow(ink, 24);
      if (!center) {
        x.fillStyle = acc;
        x.beginPath();
        x.arc(pad + 14, y - 16, 10, 0, TAU);
        x.fill();
      }
      x.fillStyle = ink;
      x.fillText(ln, center ? X : pad + 48, y);
      y += lh;
    }
    if (pg.sub) {
      glow(acc, 16);
      x.font = `400 36px ${fam}`;
      x.fillStyle = st.subColor || (st.glow ? acc : 'rgba(127,127,127,.95)');
      x.fillText(pg.sub, X, h - pad);
    }
  }
  x.restore();
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  return t;
};
const canvasTex = (w: number, h: number, draw: (x: CanvasRenderingContext2D) => void, srgb = true) => {
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  draw(c.getContext('2d')!);
  const t = new THREE.CanvasTexture(c);
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  return t;
};
const glowDot = (tint: string) => canvasTex(128, 128, (x) => {
  const g = x.createRadialGradient(64, 64, 0, 64, 64, 64);
  g.addColorStop(0, 'rgba(255,255,255,1)');
  g.addColorStop(0.25, tint);
  g.addColorStop(1, 'rgba(0,0,0,0)');
  x.fillStyle = g;
  x.fillRect(0, 0, 128, 128);
});
/** mặt nạ bo góc (alphaMap) */
const roundMask = (ratio: number, corner: number) => canvasTex(512, Math.round(512 * ratio), (x) => {
  x.fillStyle = '#000';
  x.fillRect(0, 0, 512, 512 * ratio);
  x.fillStyle = '#fff';
  roundRectPath(x, 0, 0, 512, 512 * ratio, corner * Math.min(512, 512 * ratio));
  x.fill();
}, false);
const scanTex = (kind: string, ratio: number) => {
  if (kind === 'led')
    return canvasTex(512, Math.round(512 * ratio), (x) => {
      x.fillStyle = '#fff';
      x.fillRect(0, 0, 512, 512 * ratio);
      x.fillStyle = '#000';
      for (let i = 0; i < 512; i += 6) x.fillRect(i, 0, 2, 512 * ratio);
      for (let j = 0; j < 512 * ratio; j += 6) x.fillRect(0, j, 512, 2);
    }, false);
  if (kind === 'grid')
    return canvasTex(512, Math.round(512 * ratio), (x) => {
      x.strokeStyle = 'rgba(255,255,255,.55)';
      x.lineWidth = 1.5;
      for (let i = 0; i <= 512; i += 32) { x.beginPath(); x.moveTo(i, 0); x.lineTo(i, 512 * ratio); x.stroke(); }
      for (let j = 0; j <= 512 * ratio; j += 32) { x.beginPath(); x.moveTo(0, j); x.lineTo(512, j); x.stroke(); }
    }, false);
  const t = canvasTex(8, 256, (x) => {
    for (let y = 0; y < 256; y += 4) {
      x.fillStyle = 'rgba(255,255,255,.5)';
      x.fillRect(0, y, 8, 1);
    }
  }, false);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(1, 18);
  return t;
};
/** uốn cong theo chiều ngang: x -> góc trên trụ bán kính R, mép tiến về phía người xem */
const bendPt = (v: THREE.Vector3, R: number) => {
  if (!R) return v;
  const th = v.x / R;
  return new THREE.Vector3(Math.sin(th) * R, v.y, v.z + R * (1 - Math.cos(th)));
};
const bendGeo = (g: THREE.BufferGeometry, R: number) => {
  if (!R) return g;
  const p = g.attributes.position as THREE.BufferAttribute;
  const v = new THREE.Vector3();
  for (let i = 0; i < p.count; i++) {
    v.fromBufferAttribute(p, i);
    const b = bendPt(v, R);
    p.setXYZ(i, b.x, b.y, b.z);
  }
  p.needsUpdate = true;
  g.computeVertexNormals();
  return g;
};
const rrShape = (w: number, h: number, r: number) => {
  const s = new THREE.Shape();
  r = Math.max(0.0001, Math.min(r, w / 2, h / 2));
  const x = -w / 2, y = -h / 2;
  s.moveTo(x + r, y);
  s.lineTo(x + w - r, y);
  s.quadraticCurveTo(x + w, y, x + w, y + r);
  s.lineTo(x + w, y + h - r);
  s.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  s.lineTo(x + r, y + h);
  s.quadraticCurveTo(x, y + h, x, y + h - r);
  s.lineTo(x, y + r);
  s.quadraticCurveTo(x, y, x + r, y);
  return s;
};
const rrPoints = (w: number, h: number, r: number, z: number, R: number) => {
  const pts: THREE.Vector3[] = [];
  const sh = rrShape(w, h, r);
  const base = sh.getSpacedPoints(160);
  for (const p of base) pts.push(bendPt(new THREE.Vector3(p.x, p.y, z), R));
  return pts;
};
/** điểm tay ở giây t (trong khối): [[t, x, y, …]] — mất tay > 0.3 giây thì null */
export const handAt = (pts: number[][] | undefined, t: number): number[] | null => {
  if (!pts || !pts.length) return null;
  let lo = 0, hi = pts.length - 1;
  if (t <= pts[0][0]) return pts[0][0] - t < 0.3 ? pts[0].slice(1) : null;
  if (t >= pts[hi][0]) return t - pts[hi][0] < 0.3 ? pts[hi].slice(1) : null;
  while (hi - lo > 1) {
    const m = (lo + hi) >> 1;
    if (pts[m][0] <= t) lo = m;
    else hi = m;
  }
  const a = pts[lo], b = pts[hi];
  if (b[0] - a[0] > 0.45) return t - a[0] < 0.3 ? a.slice(1) : b[0] - t < 0.3 ? b.slice(1) : null;
  const u = (t - a[0]) / Math.max(1e-6, b[0] - a[0]);
  return a.slice(1).map((v, k) => v + ((b[k + 1] ?? v) - v) * u);
};

export const Screen3D: React.FC<{e: any; dur: number; hand?: number[][]; ev?: {t: number; dir: number}[]}> = ({e, dur, hand, ev}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pages: any[] = (e.pages && e.pages.length ? e.pages : e.src ? [{src: e.src, from: e.from, volume: e.volume}] : [{title: 'Tiêu đề', text: 'Dòng 1\nDòng 2'}]).filter(Boolean);
  const L0 = SCREEN_LOOKS[e.look] || (e.look === 'custom' ? {frame: {}, page: {}} : SCREEN_LOOKS.holo);
  const F: any = mergeDeep(mergeDeep({curve: 0, corner: 0.04, bezel: {w: 0, depth: 16, color: '#17191c', metal: 0.5, rough: 0.3}, inset: 1}, L0.frame), e.frame || {});
  if (e.color && F.glow) F.glow = {...F.glow, color: e.color};
  if (e.color && F.neon) F.neon = {...F.neon, color: e.color};
  const PS = mergeDeep(mergeDeep({ink: '#ffffff', accent: '#5ad1ff', bg: 'none'}, L0.page), e.pageStyle || {});
  const ratio = e.ratio ?? L0.ratio ?? 0.64;
  const tint = F.glow?.color || F.neon?.color || PS.accent || '#5ad1ff';
  const imgSrcs = pages.map((p) => (p.src && !isVidSrc(p.src) ? p.src : ''));
  const imgs = useLoad('s3d:' + imgSrcs.join('|') + '|' + (PS.font || ''), () => fontReady([PS.font, ...pages.map((p) => p.style?.font)]).then(() => Promise.all(imgSrcs.map((s) => (s ? loadImg(s) : Promise.resolve(null))))));
  const vref = useRef<(HTMLDivElement | null)[]>([]);
  const api = useRef<any>(null);
  const key = JSON.stringify([pages, F, PS, ratio, e.w, FR.w, FR.h, !!imgs]);
  const T = dur / fps;
  const evs = (ev && ev.length ? ev : (e.at || []).map((t: number) => ({t, dir: 1}))).slice().sort((a: any, b: any) => a.t - b.t);
  const auto = !evs.length && pages.length > 1 && e.auto !== false;
  const steps: {t: number; from: number; to: number}[] = [];
  let cur = 0;
  if (auto) for (let k = 1; k < pages.length; k++) steps.push({t: (T * k) / pages.length - 0.25, from: k - 1, to: k});
  else
    for (const x of evs) {
      const to = Math.max(0, Math.min(pages.length - 1, cur + (x.dir >= 0 ? 1 : -1)));
      if (to !== cur) steps.push({t: x.t, from: cur, to});
      cur = to;
    }
  const build = (cv: HTMLCanvasElement) => {
    const s = mkGL(cv, 30, 0.8);
    s.renderer.toneMapping = THREE.NoToneMapping;
    const W = (e.w ?? L0.w ?? 620) / PPU, H = W * ratio;
    const R = F.curve > 0 ? W / ((Math.min(170, F.curve) * Math.PI) / 180) : 0;
    const rad = (F.corner ?? 0.04) * Math.min(W, H);
    const g = new THREE.Group();
    s.scene.add(g);
    const kl = new THREE.DirectionalLight(0xffffff, 1.8);
    kl.position.set(-4, 6, 10);
    const fill = new THREE.DirectionalLight(0xffffff, 0.6);
    fill.position.set(5, -2, 6);
    s.scene.add(kl, fill);
    const seg = (w: number, h: number) => new THREE.PlaneGeometry(w, h, R ? 64 : 1, 1);
    const extras: any = {};
    // bóng đổ mềm phía sau
    if (F.shadow > 0) {
      const sh = new THREE.Mesh(new THREE.PlaneGeometry(W * 1.5, H * 1.5), new THREE.MeshBasicMaterial({map: canvasTex(256, 256, (x) => {
        const gg = x.createRadialGradient(128, 128, 20, 128, 128, 128);
        gg.addColorStop(0, 'rgba(0,0,0,.9)');
        gg.addColorStop(1, 'rgba(0,0,0,0)');
        x.fillStyle = gg;
        x.fillRect(0, 0, 256, 256);
      }), transparent: true, opacity: F.shadow, depthWrite: false}));
      sh.position.set(W * 0.06, -H * 0.08, -0.6);
      sh.renderOrder = -3;
      g.add(sh);
    }
    // vỏ máy / viền khung
    const bw = (F.bezel?.w ?? 0) / PPU, bd = Math.max(0.02, (F.bezel?.depth ?? 16) / PPU);
    if (bw > 0) {
      const bm = new THREE.MeshStandardMaterial({color: new THREE.Color(F.bezel.color || '#17191c'), metalness: F.bezel.metal ?? 0.5, roughness: F.bezel.rough ?? 0.3});
      if (R) {
        const back = new THREE.Mesh(bendGeo(seg(W + 2 * bw, H + 2 * bw), R), bm);
        (back.material as any).alphaMap = roundMask((H + 2 * bw) / (W + 2 * bw), (rad + bw) / Math.min(W + 2 * bw, H + 2 * bw));
        (back.material as any).transparent = true;
        back.material.side = THREE.DoubleSide;
        back.position.z = -0.01;
        back.renderOrder = -2;
        g.add(back);
        const back2 = back.clone();
        back2.position.z = -bd;
        g.add(back2);
      } else {
        const outer = rrShape(W + 2 * bw, H + 2 * bw, rad + bw);
        const body = new THREE.Mesh(new THREE.ExtrudeGeometry(outer, {depth: bd, bevelEnabled: true, bevelThickness: Math.min(0.03, bd * 0.3), bevelSize: Math.min(0.03, bw * 0.4), bevelSegments: 3, curveSegments: 16}), bm);
        body.position.z = -bd - 0.02 - Math.min(0.03, bd * 0.3);
        body.renderOrder = -2;
        g.add(body);
      }
      if (F.buttons) {
        for (const [yy, hh] of [[0.22, 0.12], [0.05, 0.12], [-0.12, 0.08]] as [number, number][]) {
          const b = new THREE.Mesh(new THREE.BoxGeometry(0.03, H * hh, bd * 0.6), bm);
          b.position.set(W / 2 + bw + 0.012, H * yy, -bd / 2);
          g.add(b);
        }
      }
      if (F.stand && !R) {
        const neck = new THREE.Mesh(new THREE.BoxGeometry(W * 0.06, H * 0.22, bd * 0.6), bm);
        neck.position.set(0, -H / 2 - bw - H * 0.11, -bd * 0.7);
        const base = new THREE.Mesh(new RoundedBoxGeometry(W * 0.36, 0.06, W * 0.14, 4, 0.03), bm);
        base.position.set(0, -H / 2 - bw - H * 0.22, -bd * 0.7);
        g.add(neck, base);
      }
    }
    // tấm nền
    if (F.plate && (F.plate.opacity ?? 0) > 0) {
      const plate = new THREE.Mesh(bendGeo(seg(W, H), R), new THREE.MeshBasicMaterial({color: new THREE.Color(F.plate.color || '#000'), transparent: true, opacity: F.plate.opacity, depthWrite: false, alphaMap: roundMask(ratio, rad / Math.min(W, H)), side: THREE.DoubleSide}));
      plate.position.z = -0.005;
      plate.renderOrder = -1;
      g.add(plate);
    }
    // trang nội dung
    const inset = F.inset ?? 1, pw = W * inset, ph = H * inset;
    const pcorner = Math.max(0, (rad - (W - pw) / 2) / Math.min(pw, ph));
    const pg = pages.map((p, i) => {
      const tex = p.src && isVidSrc(p.src) ? null : pageTex(p, imgs?.[i] || null, ph / pw, mergeDeep(PS, p.style), pcorner);
      const m = new THREE.MeshBasicMaterial({map: tex, color: tex ? 0xffffff : 0x000000, transparent: true, depthWrite: false, toneMapped: false, alphaMap: roundMask(ph / pw, pcorner), side: THREE.DoubleSide});
      const mesh = new THREE.Mesh(bendGeo(seg(pw, ph), R), m);
      mesh.position.z = 0.01;
      g.add(mesh);
      return mesh;
    });
    // tai thỏ
    if (F.notch) {
      const n = new THREE.Mesh(new THREE.ShapeGeometry(rrShape(W * 0.3, W * 0.075, W * 0.0375)), new THREE.MeshBasicMaterial({color: 0x000000}));
      n.position.set(0, H / 2 - W * 0.07, 0.03);
      n.renderOrder = 1;
      g.add(n);
    }
    // vạch quét / LED / lưới
    if (F.scan && F.scan !== 'none') {
      const st = scanTex(F.scan, ratio);
      const led = F.scan === 'led';
      const sc = new THREE.Mesh(bendGeo(seg(pw, ph), R), new THREE.MeshBasicMaterial({map: led ? undefined : st, alphaMap: led ? st : undefined, color: led ? 0x000000 : new THREE.Color(F.scanColor || tint),
        transparent: true, opacity: F.scanOpacity ?? (led ? 0.35 : 0.12), depthWrite: false, blending: led ? THREE.NormalBlending : THREE.AdditiveBlending}));
      sc.position.z = 0.02;
      sc.renderOrder = 2;
      g.add(sc);
      if (!led && F.scan === 'lines') extras.scan = st;
    }
    // vệt bóng kính
    if (F.reflection > 0) {
      const rt = canvasTex(512, 512, (x) => {
        const gg = x.createLinearGradient(0, 0, 512, 512);
        gg.addColorStop(0, 'rgba(255,255,255,0)');
        gg.addColorStop(0.38, 'rgba(255,255,255,0)');
        gg.addColorStop(0.45, 'rgba(255,255,255,.55)');
        gg.addColorStop(0.55, 'rgba(255,255,255,.08)');
        gg.addColorStop(0.62, 'rgba(255,255,255,0)');
        x.fillStyle = gg;
        x.fillRect(0, 0, 512, 512);
      });
      const rf = new THREE.Mesh(bendGeo(seg(W, H), R), new THREE.MeshBasicMaterial({map: rt, transparent: true, opacity: F.reflection, depthWrite: false, blending: THREE.AdditiveBlending, alphaMap: roundMask(ratio, rad / Math.min(W, H))}));
      rf.position.z = 0.03;
      rf.renderOrder = 3;
      g.add(rf);
      extras.refl = rt;
    }
    // viền phát sáng / ống neon
    const lines: {l: any; base: number; kind: string}[] = [];
    const addLine = (pts: THREE.Vector3[], color: string, width: number, op: number, kind: string, add = false) => {
      const lg = new LineGeometry();
      lg.setPositions(pts.flatMap((p) => [p.x, p.y, p.z]));
      const m = new LineMaterial({color: new THREE.Color(color).getHex(), linewidth: width, transparent: true, opacity: op, depthWrite: false, blending: add ? THREE.AdditiveBlending : THREE.NormalBlending});
      m.resolution.set(FR.w, FR.h);
      const l = new Line2(lg, m);
      l.computeLineDistances();
      l.renderOrder = 4;
      g.add(l);
      lines.push({l, base: op, kind});
    };
    const glowPlane = (gw: number, gh: number, gr: number, color: string, blur: number, lw: number, op: number, kind: string, z = 0.035) => {
      const m = 0.18, cw = 1024, chh = Math.round((1024 * (gh + 2 * m * gw)) / (gw * (1 + 2 * m)));
      const sc = cw / (gw * (1 + 2 * m));
      const tx = canvasTex(cw, chh, (x) => {
        x.strokeStyle = color;
        x.shadowColor = color;
        x.lineWidth = lw;
        for (const b of [blur, blur * 0.5, blur * 0.25]) {
          x.shadowBlur = b;
          roundRectPath(x, m * gw * sc, (chh - gh * sc) / 2, gw * sc, gh * sc, gr * sc);
          x.stroke();
        }
      });
      const mesh = new THREE.Mesh(bendGeo(new THREE.PlaneGeometry(gw * (1 + 2 * m), gh + 2 * m * gw, R ? 64 : 1, 1), R), new THREE.MeshBasicMaterial({map: tx, transparent: true, opacity: op, depthWrite: false, blending: THREE.AdditiveBlending}));
      mesh.position.z = z;
      mesh.renderOrder = 4;
      g.add(mesh);
      lines.push({l: mesh, base: op, kind});
    };
    const edge = rrPoints(W, H, rad, 0.04, R);
    if (F.glow && (F.glow.width ?? 0) > 0) {
      if ((F.glow.halo ?? 0.5) > 0) glowPlane(W, H, rad, F.glow.color, 40, F.glow.width * 2, Math.min(1, F.glow.halo ?? 0.5), 'glow');
      addLine(edge, F.glow.color, F.glow.width, 1, 'glow');
    }
    if (F.neon) {
      const nw = F.neon.width ?? 6;
      const ring = (w2: number, h2: number, r2: number, col: string, z: number) => {
        glowPlane(w2, h2, r2, col, 60, nw * 3, 0.9, 'neon', z - 0.005);
        addLine(rrPoints(w2, h2, r2, z, R), col, nw, 1, 'neon');
        addLine(rrPoints(w2, h2, r2, z + 0.002, R), '#ffffff', Math.max(1.5, nw * 0.3), 0.9, 'neon');
      };
      ring(W, H, rad, F.neon.color, 0.04);
      if (F.neon.color2) ring(W * 0.94, H * 0.92, rad * 0.8, F.neon.color2, 0.045);
    }
    if (F.corners === 'bracket' || F.corners === 'dot') {
      const hw = W / 2 + 0.06, hh = H / 2 + 0.06, a = Math.min(W, H) * 0.12;
      for (const [sx, sy] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) {
        if (F.corners === 'bracket') addLine([new THREE.Vector3(sx * hw, sy * (hh - a), 0.05), new THREE.Vector3(sx * hw, sy * hh, 0.05), new THREE.Vector3(sx * (hw - a), sy * hh, 0.05)].map((p) => bendPt(p, R)), '#ffffff', 6, 1, 'corner');
        else {
          const d = new THREE.Mesh(new THREE.CircleGeometry(0.05, 20), new THREE.MeshBasicMaterial({color: new THREE.Color(tint)}));
          d.position.copy(bendPt(new THREE.Vector3(sx * hw, sy * hh, 0.05), R));
          g.add(d);
        }
      }
    }
    const dot = new THREE.Sprite(new THREE.SpriteMaterial({map: glowDot(tint), transparent: true, depthWrite: false, depthTest: false, blending: THREE.AdditiveBlending}));
    dot.scale.setScalar(0.9);
    dot.renderOrder = 5;
    g.add(dot);
    const ring = new THREE.Mesh(new THREE.RingGeometry(0.92, 1, 64), new THREE.MeshBasicMaterial({color: new THREE.Color(tint), transparent: true, depthWrite: false, depthTest: false}));
    g.add(ring);
    return Object.assign(s, {g, pg, W, H, R, pw, ph, dot, ring, lines, extras, vt: [] as any[]});
  };
  const update = (s: GLS) => {
    const t = f / fps;
    pages.forEach((p, i) => {
      if (!isVidSrc(p.src)) return;
      const el: any = vref.current[i]?.querySelector('img,video');
      if (!el) return;
      let tx = s.vt[i];
      if (!tx || tx.image !== el) {
        tx?.dispose?.();
        tx = el.tagName === 'VIDEO' ? new THREE.VideoTexture(el) : new THREE.Texture(el);
        tx.colorSpace = THREE.SRGBColorSpace;
        s.vt[i] = tx;
        if (el.tagName === 'IMG' && !el.__s3d) {
          el.__s3d = true;
          el.addEventListener('load', () => api.current?.redraw());
        }
        const m = s.pg[i].material as THREE.MeshBasicMaterial;
        m.map = tx;
        m.color.set(0xffffff);
        m.needsUpdate = true;
      }
      if (el.tagName === 'IMG' && el.complete && el.naturalWidth) tx.needsUpdate = true;
      const vw = el.naturalWidth || el.videoWidth, vh = el.naturalHeight || el.videoHeight;
      if (vw && vh) {
        const pr2 = s.ph / s.pw, k = pr2 / (vh / vw);
        if (k > 1) { tx.repeat.set(1 / k, 1); tx.offset.set((1 - 1 / k) / 2, 0); } else { tx.repeat.set(1, k); tx.offset.set(0, (1 - k) / 2); }
      }
    });
    const hp = handAt(hand, t);
    const cx = e.x ?? FR.w * 0.32, cy = e.y ?? fy(820);
    const P = W0(cx, cy);
    const side = cx < FR.w / 2 ? 1 : -1;
    const hf = e.handFollow ?? 0.5;
    let ty = ((e.tiltY ?? side * (s.R ? 8 : 16)) * Math.PI) / 180, txl = ((e.tiltX ?? 4) * Math.PI) / 180;
    if (hp) {
      ty += ((hp[0] - cx) / FR.w) * 0.6 * hf;
      txl += ((hp[1] - cy) / FR.h) * 0.4 * hf;
    }
    s.g.position.copy(P);
    if (e.float !== false) s.g.position.y += Math.sin(t * 1.6) * 0.06;
    s.g.rotation.set(txl, ty, Math.sin(t * 0.9) * 0.01);
    const a = pr(t, 0, 0.7), o = E.inc(pr(t, T - 0.4, 0.4));
    const enter = e.enter || L0.enter || 'fly';
    let sx = 1, sy = 1, op = 1;
    s.g.visible = true;
    if (enter === 'unfold') {
      sx = Math.max(0.01, E.cub(pr(a, 0, 0.45)));
      sy = Math.max(0.01, E.back(pr(a, 0.35, 0.65)));
      if (a < 1) s.g.visible = Math.sin(t * 90) > -0.6 || a > 0.6;
    } else if (enter === 'flip') {
      s.g.rotation.x += (1 - E.back(a)) * -Math.PI / 2;
    } else if (enter === 'rise') {
      s.g.position.y -= (1 - E.cub(a)) * 6;
      s.g.rotation.x += (1 - E.cub(a)) * 0.5;
    } else if (enter === 'fade') {
      op = E.cub(a);
      sx = sy = 0.92 + 0.08 * E.cub(a);
    } else {
      s.g.position.x += (1 - E.cub(a)) * -side * 8;
      s.g.rotation.y += (1 - E.cub(a)) * side * 0.9;
    }
    if (o > 0) {
      if (enter === 'unfold') {
        sy *= Math.max(0.01, 1 - E.cub(pr(o, 0, 0.6)));
        sx *= Math.max(0.01, 1 - E.cub(pr(o, 0.4, 0.6)));
      } else if (enter === 'fade') op *= 1 - o;
      else {
        sx *= Math.max(0.01, 1 - o);
        sy *= Math.max(0.01, 1 - o);
      }
    }
    s.g.scale.set(sx, sy, 1);
    if (s.extras.scan) s.extras.scan.offset.y = -t * 0.6;
    if (s.extras.refl) s.extras.refl.offset.x = Math.sin(t * 0.5) * 0.15;
    // đèn: thở sáng / neon chập chờn lúc bật
    const flick = F.neon?.flicker !== false && F.neon ? (a < 1 ? (Math.sin(t * 61) * Math.sin(t * 23) > -0.15 ? 1 : 0.15) : 1) : 1;
    const pulse = F.glow?.pulse ? 0.75 + 0.25 * Math.sin(t * 3) : 1;
    for (const L of s.lines) (L.l.material as any).opacity = L.base * op * (L.kind === 'neon' ? flick : L.kind === 'glow' ? pulse : 1);
    s.g.traverse((m: any) => {
      if (m.isMesh && m.material && !m.material.isLineMaterial && m.material.userData.op0 == null) m.material.userData.op0 = m.material.opacity ?? 1;
    });
    // trang
    let pos = 0;
    for (const st of steps) if (t >= st.t) pos = st.from + (st.to - st.from) * E.io(pr(t, st.t, 0.45));
    const tr = F.transition || (s.R ? 'fade' : 'slide');
    s.pg.forEach((m: THREE.Mesh, i: number) => {
      const k = i - pos, ak = Math.abs(k);
      const mat = m.material as THREE.MeshBasicMaterial;
      m.position.set(0, 0, 0.01);
      m.rotation.set(0, 0, 0);
      m.scale.setScalar(1);
      if (tr === 'fade') {
        m.visible = ak < 1;
        mat.opacity = Math.max(0, 1 - ak) * op;
        m.scale.setScalar(1 + ak * 0.04);
      } else if (tr === 'flip') {
        m.visible = ak < 0.5;
        m.rotation.x = k * Math.PI;
        mat.opacity = op;
      } else {
        m.visible = ak < 1.6;
        m.position.set(k * s.pw * 1.08, 0, 0.01 - ak * 0.3);
        m.rotation.y = -Math.max(-1, Math.min(1, k)) * 0.55;
        m.scale.setScalar(1 - Math.min(0.2, ak * 0.15));
        mat.opacity = Math.max(0, 1 - ak * 0.9) * op;
      }
    });
    s.g.traverse((m: any) => {
      if (m.isMesh && m.material && !s.pg.includes(m) && m.material.userData.op0 != null) m.material.opacity = m.material.userData.op0 * op;
    });
    s.dot.visible = false;
    s.ring.visible = false;
    if (hp && e.touch !== false) {
      s.g.updateMatrixWorld();
      const n = new THREE.Vector3(0, 0, 1).applyQuaternion(s.g.getWorldQuaternion(new THREE.Quaternion()));
      const pl = new THREE.Plane().setFromNormalAndCoplanarPoint(n, s.g.getWorldPosition(new THREE.Vector3()));
      const rc = new THREE.Raycaster();
      rc.setFromCamera(new THREE.Vector2((hp[0] / FR.w) * 2 - 1, 1 - (hp[1] / FR.h) * 2), s.camera);
      const hit = new THREE.Vector3();
      if (rc.ray.intersectPlane(pl, hit)) {
        const loc = s.g.worldToLocal(hit.clone());
        if (Math.abs(loc.x) < (s.W / 2) * 1.02 && Math.abs(loc.y) < (s.H / 2) * 1.02 && a >= 1) {
          s.dot.visible = true;
          s.dot.position.copy(bendPt(new THREE.Vector3(loc.x, loc.y, 0.06), s.R));
          s.dot.scale.setScalar(0.8 + Math.sin(t * 12) * 0.08);
        }
      }
    }
    const last = [...steps].reverse().find((st) => t >= st.t && t < st.t + 0.6);
    if (last) {
      const u = (t - last.t) / 0.6;
      s.ring.visible = true;
      s.ring.position.set(s.dot.visible ? s.dot.position.x : 0, s.dot.visible ? s.dot.position.y : 0, 0.07);
      s.ring.scale.setScalar(0.2 + u * 1.4);
      (s.ring.material as THREE.MeshBasicMaterial).opacity = 1 - u;
    }
  };
  useEffect(() => {
    const obs = new MutationObserver(() => api.current?.redraw());
    vref.current.forEach((d) => d && obs.observe(d, {childList: true, subtree: true, attributes: true, attributeFilter: ['src']}));
    return () => obs.disconnect();
  }, [key]);
  return (
    <>
      {pages.map((p, i) =>
        isVidSrc(p.src) ? (
          <div key={'v' + i} ref={(el) => (vref.current[i] = el)} style={{position: 'absolute', left: 0, top: 0, width: 4, height: 4, opacity: 0, overflow: 'hidden', pointerEvents: 'none'}}>
            <OffthreadVideo src={mediaSrc(p.src)} startFrom={Math.round((p.from || 0) * fps)} volume={p.volume ?? 0} muted={!p.volume} style={{width: 4, height: 4}} />
          </div>
        ) : null,
      )}
      <GLCanvas k={key} ready={!!imgs} build={build} update={update} api={api} />
    </>
  );
};
