/* Khối BẢN ĐỒ: nền MapLibre (OpenFreeMap, miễn phí, cần mạng lúc xem trước / xuất), đường đi từ DỰ ÁN (điểm đầu)
   tới từng tiện ích tự vẽ ra, ghim + nhãn ("Vinmec · 5 phút"), camera zoom vào / bay theo đường.
   element: {type: 'map', places: [{name, lng, lat, label?}], paths?: [[lng, lat]...][] (đường bộ đã tính sẵn, theo
   thứ tự tiện ích 1..n), lineMode: road | line | arc, style: positron | liberty | bright | dark | fiord,
   theme: goc | toi | sang (phong cách màu), hideLabels, camera: zoomin | fly | orbit | static, frame: full | card, color,
   d3: dựng KHỐI 3D toà nhà (nghiêng 60°, đổ bóng, trời / sương mù) + khối dự án phát sáng mọc lên + cột 3D ở từng tiện ích,
   towerH: chiều cao khối dự án (m, mặc định 180), tower: false = không dựng khối dự án,
   terrain: true | số (ĐỊA HÌNH 3D núi đồi, số = độ nổi), hillshade: false (tắt đổ bóng địa hình), camera 'globe' (zoom từ QUẢ ĐỊA CẦU
   xuống), colors: {land, water, park, road, building, label, boundary} (màu bản đồ tự chọn), routeStyle: solid | dash | glow,
   arrow: true (mũi tên đầu tuyến), mover: car | moto | plane | bus | walk | ship | train | emoji (xe chạy dọc tuyến)} */
import {S as STY} from './style';
import {FR} from './frame';
import React, {useEffect, useRef, useState} from 'react';
import {AbsoluteFill, continueRender, delayRender, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import * as mlNS from 'maplibre-gl';
// maplibre-gl là gói UMD trong package "type": "module" → webpack có thể chỉ đưa ra .default
// (khi bị coi là ESM, gói UMD tự gắn vào globalThis.maplibregl thay vì export)
const maplibregl: any = (mlNS as any).Map ? mlNS : ((mlNS as any).default?.Map ? (mlNS as any).default : ((globalThis as any).maplibregl || mlNS));
import * as Icons from 'lucide-react';
import {addTerrain, addGlobe, applyColors, screenAngle, MOVER, DEM_CREDIT, MapFx} from './mapfx';

type Place = {name: string; lng: number; lat: number; label?: string; icon?: string};
export type MapEl = {
  places?: Place[];
  paths?: ([number, number][] | null)[];
  lineMode?: string;
  style?: string;
  theme?: string;
  hideLabels?: boolean;
  camera?: string;
  frame?: string;
  color?: string;
  d3?: boolean;
  tower?: boolean;
  towerH?: number;
  routeStyle?: string;
  arrow?: boolean;
  mover?: string;
} & MapFx;
type Theme = {light: string; mid: string; dark: string; gold1: string; gold2: string};

// 'tron' = nền trơn không cần mạng (chỉ có đường đi + ghim)
const STYLE_URL = (s?: string): any =>
  s === 'tron'
    ? {version: 8, sources: {}, layers: [{id: 'nen', type: 'background', paint: {'background-color': '#e9edf2'}}]}
    : `https://tiles.openfreemap.org/styles/${['positron', 'liberty', 'bright', 'dark', 'fiord'].includes(s || '') ? s : 'positron'}`;
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

/* ---- 3D: khối vuông quanh 1 điểm (cạnh ~ m mét) ---- */
const square = (p: {lng: number; lat: number}, m: number) => {
  const dy = m / 2 / 111320, dx = m / 2 / (111320 * Math.cos((p.lat * Math.PI) / 180));
  return [[[p.lng - dx, p.lat - dy], [p.lng + dx, p.lat - dy], [p.lng + dx, p.lat + dy], [p.lng - dx, p.lat + dy], [p.lng - dx, p.lat - dy]]];
};
/** thêm lớp toà nhà 3D (từ dữ liệu OpenStreetMap của nền bản đồ) + ánh sáng, trời, sương */
const add3d = (map: any, m: MapEl, col: string) => {
  const dark = (m.theme || 'goc') === 'toi' || m.style === 'dark' || m.style === 'fiord';
  const st = map.getStyle();
  const vsrc = Object.entries(st.sources || {}).find(([, v]: any) => v.type === 'vector')?.[0];
  for (const L of st.layers || []) {
    // lớp toà nhà phẳng có sẵn -> ẩn (đã có khối 3D); lớp 3D có sẵn (liberty) -> dùng màu của mình
    if ((L as any)['source-layer'] === 'building' && L.type === 'fill') map.setLayoutProperty(L.id, 'visibility', 'none');
    if (L.type === 'fill-extrusion') map.setLayoutProperty(L.id, 'visibility', 'none');
  }
  if (vsrc) {
    const firstSym = (st.layers || []).find((L) => L.type === 'symbol')?.id;
    map.addLayer({
      id: 'b3d', type: 'fill-extrusion', source: vsrc, 'source-layer': 'building', minzoom: 12,
      paint: {
        'fill-extrusion-color': ['interpolate', ['linear'], ['coalesce', ['get', 'render_height'], 10], 0, dark ? '#24477d' : '#dfe4ec', 40, dark ? '#3567ad' : '#c9d2e0', 120, dark ? '#5a93dd' : '#aebbd0'],
        'fill-extrusion-height': ['*', ['coalesce', ['get', 'render_height'], 10], 1.15],
        'fill-extrusion-base': ['coalesce', ['get', 'render_min_height'], 0],
        'fill-extrusion-opacity': 0.92,
        'fill-extrusion-vertical-gradient': true,
      },
    } as any, firstSym);
  }
  // khối dự án + cột tiện ích (độ cao cập nhật theo khung)
  map.addSource('k3d', {type: 'geojson', data: {type: 'FeatureCollection', features: []}});
  map.addLayer({id: 'k3d', type: 'fill-extrusion', source: 'k3d', paint: {
    'fill-extrusion-color': ['get', 'c'], 'fill-extrusion-height': ['get', 'h'], 'fill-extrusion-base': 0, 'fill-extrusion-opacity': 0.95, 'fill-extrusion-vertical-gradient': true,
  }} as any);
  try {
    map.setLight({anchor: 'map', color: '#ffffff', intensity: dark ? 0.35 : 0.5, position: [1.4, 200, 35]} as any);
  } catch {}
  try {
    (map as any).setSky({'sky-color': dark ? '#0b1a33' : '#bcd7f2', 'horizon-color': dark ? '#16305a' : '#eef3f9', 'fog-color': dark ? '#0b1a33' : '#f4f7fb',
      'sky-horizon-blend': 0.6, 'horizon-fog-blend': 0.6, 'fog-ground-blend': 0.25, 'atmosphere-blend': 0.6});
  } catch {}
  void col;
};

/* ---- hình học (không cần thư viện) ---- */
export const merc = ([lng, lat]: [number, number]) => [lng, (Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360)) * 180) / Math.PI];
export const unmerc = ([x, y]: number[]): [number, number] => [x, (Math.atan(Math.exp((y * Math.PI) / 180)) * 360) / Math.PI - 90];
/** đường cong nhẹ giữa 2 điểm (trên mặt phẳng Mercator) */
const arc = (a: [number, number], b: [number, number], n = 64): [number, number][] => {
  const A = merc(a), B = merc(b);
  const mx = (A[0] + B[0]) / 2, my = (A[1] + B[1]) / 2, dx = B[0] - A[0], dy = B[1] - A[1];
  const C = [mx - dy * 0.22, my + dx * 0.22];
  return Array.from({length: n + 1}, (_, i) => {
    const t = i / n;
    return unmerc([(1 - t) * (1 - t) * A[0] + 2 * (1 - t) * t * C[0] + t * t * B[0], (1 - t) * (1 - t) * A[1] + 2 * (1 - t) * t * C[1] + t * t * B[1]]);
  });
};
/** cắt đường tới tỉ lệ k (0–1) theo chiều dài */
export const sliceLine = (pts: [number, number][], k: number): [number, number][] => {
  if (pts.length < 2 || k >= 1) return pts;
  if (k <= 0) return [pts[0], pts[0]];
  const P = pts.map(merc);
  const seg = P.slice(1).map((p, i) => Math.hypot(p[0] - P[i][0], p[1] - P[i][1]));
  const total = seg.reduce((s, x) => s + x, 0);
  let want = total * k;
  const out: [number, number][] = [pts[0]];
  for (let i = 0; i < seg.length; i++) {
    if (want <= seg[i]) {
      const u = seg[i] ? want / seg[i] : 0;
      out.push(unmerc([P[i][0] + (P[i + 1][0] - P[i][0]) * u, P[i][1] + (P[i + 1][1] - P[i][1]) * u]));
      return out;
    }
    want -= seg[i];
    out.push(pts[i + 1]);
  }
  return out;
};
const routeOf = (m: MapEl, i: number): [number, number][] => {
  const ps = m.places || [];
  const a: [number, number] = [ps[0].lng, ps[0].lat], b: [number, number] = [ps[i].lng, ps[i].lat];
  const road = m.paths?.[i - 1];
  if ((m.lineMode || 'road') === 'road' && road && road.length > 1) return road;
  return (m.lineMode || 'road') === 'line' ? [a, b] : arc(a, b);
};

/** đổi màu bản đồ theo phong cách: toi = nền xanh đêm thương hiệu, sang = trắng xám tối giản */
const recolor = (map: any, m: MapEl, t: Theme) => {
  const th = m.theme || 'goc';
  for (const L of map.getStyle().layers || []) {
    const id = L.id.toLowerCase();
    try {
      if (m.hideLabels && L.type === 'symbol') map.setLayoutProperty(L.id, 'visibility', 'none');
      if (th === 'goc') continue;
      const dark = th === 'toi';
      if (L.type === 'background') map.setPaintProperty(L.id, 'background-color', dark ? '#0b1a33' : '#f4f5f7');
      else if (L.type === 'fill') {
        const water = id.includes('water');
        const park = id.includes('park') || id.includes('landcover') || id.includes('wood') || id.includes('grass');
        map.setPaintProperty(L.id, 'fill-color', water ? (dark ? '#123a6b' : '#cfe3f5') : park ? (dark ? '#10294a' : '#e6efe3') : dark ? '#0e2142' : '#eceef1');
      } else if (L.type === 'line') {
        if (id.includes('water') || id.includes('river')) map.setPaintProperty(L.id, 'line-color', dark ? '#1b4c86' : '#b9d6f0');
        else if (id.includes('road') || id.includes('highway') || id.includes('street') || id.includes('transportation') || id.includes('bridge') || id.includes('tunnel'))
          map.setPaintProperty(L.id, 'line-color', dark ? (id.includes('major') || id.includes('motorway') || id.includes('trunk') || id.includes('primary') ? '#3c6aa8' : '#24466f') : '#ffffff');
        else if (id.includes('boundary') || id.includes('admin')) map.setPaintProperty(L.id, 'line-color', dark ? '#2b4f80' : '#c9ced6');
      } else if (L.type === 'fill-extrusion') map.setPaintProperty(L.id, 'fill-extrusion-color', dark ? '#16305a' : '#e2e5ea');
      else if (L.type === 'symbol' && !m.hideLabels) {
        map.setPaintProperty(L.id, 'text-color', dark ? '#9fb7dc' : '#6b7280');
        map.setPaintProperty(L.id, 'text-halo-color', dark ? '#0b1a33' : '#ffffff');
      }
    } catch {
      /* lớp không có thuộc tính đó */
    }
  }
  void t;
};

export const MapBlock: React.FC<{e: MapEl; dur: number; theme: Theme}> = ({e: e0, dur, theme}) => {
  // phong cách có style.map (kiểu nền / đường / camera / màu…) -> làm mặc định, khối map ghi gì thì theo khối
  const e = {...((STY.style as any).map || {}), ...e0} as MapEl;
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const box = useRef<HTMLDivElement>(null);
  const [map, setMap] = useState<any>(null);
  const [fit, setFit] = useState<{center: [number, number]; zoom: number} | null>(null);
  const [fail, setFail] = useState('');
  const [, tick] = useState(0);
  const places = (e.places || []).filter((p) => isFinite(p.lng) && isFinite(p.lat));
  const n = Math.max(0, places.length - 1);
  const card = e.frame === 'card';
  const W = card ? Math.min(960, FR.w - 120) : FR.w, H = card ? Math.min(1100, FR.h - 120) : FR.h;
  const col = e.color || (e.theme === 'sang' || ((e.theme || 'goc') === 'goc' && e.style !== 'dark' && e.style !== 'fiord') ? theme.mid : theme.gold1);
  const globe = e.camera === 'globe';
  const key = JSON.stringify([places.map((p) => [p.lng, p.lat]), e.style, e.theme, e.hideLabels, card, !!e.d3, e.terrain, e.hillshade, globe, e.colors, e.routeStyle]);

  // tạo bản đồ (1 lần cho mỗi bộ điểm / kiểu); chờ tải xong mới cho dựng khung
  useEffect(() => {
    if (!box.current || !places.length) return;
    const h = delayRender('Tải bản đồ', {timeoutInMilliseconds: 60000});
    let done = false;
    const finish = () => {
      if (!done) {
        done = true;
        continueRender(h);
      }
    };
    const m = new maplibregl.Map({
      container: box.current,
      style: STYLE_URL(e.style),
      center: [places[0].lng, places[0].lat],
      zoom: 13,
      interactive: false,
      maxPitch: 70,
      fadeDuration: 0,
      attributionControl: false,
      preserveDrawingBuffer: true,
      pixelRatio: 1,
    } as any);
    m.on('error', (ev: any) => {
      if (!m.isStyleLoaded()) {
        setFail('Không tải được bản đồ (cần mạng): ' + (ev?.error?.message || ''));
        finish();
      }
    });
    m.on('load', () => {
      recolor(m, e, theme);
      applyColors(m, e);
      const darkMap = (e.theme || 'goc') === 'toi' || e.style === 'dark' || e.style === 'fiord';
      addTerrain(m, e, darkMap);
      if (globe) addGlobe(m, {...e, globe: true}, darkMap);
      if (e.d3) add3d(m, e, col);
      const rs = e.routeStyle || 'solid';
      for (let i = 1; i <= n; i++) {
        m.addSource('r' + i, {type: 'geojson', data: {type: 'Feature', properties: {}, geometry: {type: 'LineString', coordinates: []}}});
        if (rs === 'glow') m.addLayer({id: 'r' + i + 'g', type: 'line', source: 'r' + i, layout: {'line-cap': 'round', 'line-join': 'round'}, paint: {'line-color': col, 'line-width': 30, 'line-opacity': 0.45, 'line-blur': 16}});
        m.addLayer({id: 'r' + i + 'c', type: 'line', source: 'r' + i, layout: {'line-cap': 'round', 'line-join': 'round'}, paint: {'line-color': '#000000', 'line-width': 16, 'line-opacity': rs === 'glow' ? 0 : 0.25, 'line-blur': 4}});
        m.addLayer({id: 'r' + i, type: 'line', source: 'r' + i, layout: {'line-cap': rs === 'dash' ? 'butt' : 'round', 'line-join': 'round'}, paint: {'line-color': rs === 'glow' ? '#ffffff' : col, 'line-width': rs === 'glow' ? 6 : 9, ...(rs === 'dash' ? {'line-dasharray': [1.4, 1.1]} : {})}});
      }
      const b = new maplibregl.LngLatBounds();
      places.forEach((p) => b.extend([p.lng, p.lat]));
      const cam = places.length > 1 ? m.cameraForBounds(b, {padding: {top: H * (e.d3 ? 0.34 : 0.28), bottom: H * 0.24, left: W * 0.16, right: W * 0.16}, maxZoom: e.d3 ? 16.5 : 16}) : {center: [places[0].lng, places[0].lat], zoom: e.d3 ? 16 : 15};
      const c = (cam as any)?.center;
      if (e.d3 && places.length > 1) {
        // 3D (nghiêng + xoay): tự tính khung — tâm giữa các điểm, khoảng cách lớn nhất (theo mọi hướng vì camera xoay) chiếm ~60% bề ngang
        const lo = places.map((p) => p.lng), la = places.map((p) => p.lat);
        const cx = (Math.min(...lo) + Math.max(...lo)) / 2, cy = (Math.min(...la) + Math.max(...la)) / 2;
        const mx = (Math.max(...lo) - Math.min(...lo)) * 111320 * Math.cos((cy * Math.PI) / 180), my = (Math.max(...la) - Math.min(...la)) * 111320;
        const span = Math.max(250, Math.hypot(mx, my));
        const z = Math.log2((W * 0.6 * 40075016.686 * Math.cos((cy * Math.PI) / 180)) / (512 * span));
        setFit({center: [cx, cy], zoom: Math.max(10, Math.min(16.5, z))});
      } else
      setFit({center: c ? [c.lng ?? c[0], c.lat ?? c[1]] : [places[0].lng, places[0].lat], zoom: Math.min(16, (cam as any)?.zoom ?? 14)});
      setMap(m);
      m.once('idle', finish);
      // địa hình / quả địa cầu: bản đồ có thể vẽ liên tục, không bao giờ 'idle' -> đợi đủ ô bản đồ rồi cho dựng (tối đa 20 giây)
      const poll = () => {
        if (done) return;
        if (m.areTilesLoaded && m.areTilesLoaded()) finish();
        else setTimeout(poll, 250);
      };
      setTimeout(poll, 600);
      setTimeout(finish, 20000);
    });
    return () => {
      finish();
      // Remotion: không gỡ bản đồ khi đang dựng (theo hướng dẫn) — chỉ gỡ khi khối bị thay đổi trong trình chỉnh sửa
      try {
        m.remove();
      } catch {}
      setMap(null);
      setFit(null);
    };
  }, [key]); // eslint-disable-line react-hooks/exhaustive-deps

  /* ---- dòng thời gian của khối ---- */
  const I = globe ? Math.min(Math.round(fps * 3.2), Math.round(dur * 0.4)) : Math.min(36, Math.round(dur * 0.22)); // zoom vào (từ quả địa cầu: lâu hơn)
  const HOLD = Math.min(24, Math.round(dur * 0.12));
  const S = n ? Math.max(8, (dur - I - HOLD) / n) : 0; // mỗi tiện ích 1 nhịp
  const drawK = (i: number) => interpolate(f, [I + (i - 1) * S, I + (i - 1) * S + S * 0.7], [0, 1], clamp);
  const ease = (x: number) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);

  // cập nhật camera + đường cho khung hiện tại, chờ bản đồ vẽ xong
  useEffect(() => {
    if (!map || !fit) return;
    const h = delayRender('Vẽ khung bản đồ', {timeoutInMilliseconds: 60000});
    const z0 = fit.zoom;
    let center: [number, number] = fit.center, zoom = z0, pitch = 0, bearing = 0;
    const camMode = e.camera || (e.d3 ? 'orbit' : 'zoomin');
    if (camMode === 'globe') {
      // từ quả địa cầu (nhìn từ không gian) lao xuống dự án, quả cầu xoay dần về đúng chỗ, cuối nghiêng 3D
      const k = ease(interpolate(f, [0, I], [0, 1], clamp));
      const u = interpolate(f, [I, dur], [0, 1], clamp);
      zoom = 1.75 + (z0 - 1.75) * k;
      center = [fit.center[0] - 42 * (1 - k), fit.center[1] * (0.35 + 0.65 * k)];
      const tilt = ease(interpolate(f, [I * 0.75, I * 1.25], [0, 1], clamp));
      pitch = (e.d3 || e.terrain ? 58 : 40) * tilt;
      bearing = -18 * (1 - k) + (e.d3 || e.terrain ? 18 * u : 0);
    } else if (e.d3 && (camMode === 'orbit' || camMode === 'zoomin')) {
      // 3D: hạ xuống từ trên cao, nghiêng dần tới 60°, rồi xoay chậm quanh dự án suốt khối
      const k = ease(interpolate(f, [0, I * 1.3], [0, 1], clamp));
      const u = interpolate(f, [0, dur], [0, 1], clamp);
      zoom = z0 - 2.4 * (1 - k);
      pitch = 15 + 47 * k;
      bearing = camMode === 'orbit' ? -14 + 22 * u : -20 * (1 - k);
      // tâm lệch về phía dự án (dự án luôn trong khung khi xoay)
      center = [places[0].lng + (fit.center[0] - places[0].lng) * k, places[0].lat + (fit.center[1] - places[0].lat) * k];
    } else if (camMode === 'zoomin') {
      const k = ease(interpolate(f, [0, I], [0, 1], clamp));
      zoom = z0 - 2.6 * (1 - k);
      pitch = (e.terrain ? 60 : 35) * k;
      bearing = -12 * (1 - k);
      center = [places[0].lng + (fit.center[0] - places[0].lng) * k, places[0].lat + (fit.center[1] - places[0].lat) * k];
    } else if (camMode === 'fly' && n) {
      const cur = Math.min(n, Math.max(1, Math.floor((f - I) / S) + 1));
      const r = routeOf({...e, places}, cur);
      const head = sliceLine(r, drawK(cur)).slice(-1)[0];
      // bay theo đầu đường nhưng vẫn giữ dự án trong khung: lệch tâm vừa phải, zoom gần bằng khung vừa
      center = [fit.center[0] + ((places[0].lng + head[0]) / 2 - fit.center[0]) * 0.6, fit.center[1] + ((places[0].lat + head[1]) / 2 - fit.center[1]) * 0.6];
      zoom = z0 + (e.d3 ? -0.2 : 0.15);
      pitch = e.d3 ? 58 : 40;
      if (e.d3) bearing = -25 + 30 * interpolate(f, [0, dur], [0, 1], clamp);
    }
    if (e.terrain) zoom -= 0.6; // địa hình nổi cao: lùi camera để không chui vào núi
    map.jumpTo({center, zoom, pitch, bearing});
    for (let i = 1; i <= n; i++) {
      const src = map.getSource('r' + i) as any;
      src?.setData({type: 'Feature', properties: {}, geometry: {type: 'LineString', coordinates: sliceLine(routeOf({...e, places}, i), ease(drawK(i)))}});
    }
    if (e.d3) {
      const ks = map.getSource('k3d') as any;
      const rise = (fr: number) => ease(Math.max(0, Math.min(1, fr)));
      const feats: any[] = [];
      // bản đồ rộng (tiện ích xa) -> khối to theo tỉ lệ khung để vẫn nhìn rõ
      const mpp = (40075016.686 * Math.cos((places[0].lat * Math.PI) / 180)) / (512 * Math.pow(2, fit.zoom));
      if (e.tower !== false) {
        const k0 = rise((f - I * 0.35) / (I * 0.9));
        const TH = Math.max(e.towerH ?? 180, 300 * mpp), side = Math.max(70, 46 * mpp);
        feats.push({type: 'Feature', properties: {h: TH * k0, c: theme.gold2}, geometry: {type: 'Polygon', coordinates: square(places[0], side)}});
        feats.push({type: 'Feature', properties: {h: (TH + Math.max(6, 8 * mpp)) * k0, c: theme.gold1}, geometry: {type: 'Polygon', coordinates: square(places[0], side * 0.66)}});
      }
      for (let i = 1; i <= n; i++) {
        const ki = rise((f - (I + (i - 1) * S + S * 0.55)) / 14);
        feats.push({type: 'Feature', properties: {h: Math.max(120, 200 * mpp) * ki, c: theme.light}, geometry: {type: 'Polygon', coordinates: square(places[i], Math.max(40, 26 * mpp))}});
      }
      ks?.setData({type: 'FeatureCollection', features: feats});
    }
    map.triggerRepaint();
    let done = false;
    const fin = () => {
      if (done) return;
      done = true;
      tick((x) => x + 1); // vẽ lại ghim theo vị trí mới
      continueRender(h);
    };
    map.once('idle', fin);
    // chờ ô bản đồ (cả địa hình) tải đủ: phải thấy "đủ" 3 lần liền (sau khi bản đồ đã bắt đầu vẽ khung mới)
    let ok = 0;
    const tp = () => {
      if (done) return;
      ok = map.areTilesLoaded && map.areTilesLoaded() ? ok + 1 : 0;
      if (ok >= 3) fin();
      else setTimeout(tp, 120);
    };
    setTimeout(tp, 350);
    const to = setTimeout(fin, 8000);
    return () => {
      clearTimeout(to);
      fin();
    };
  }, [map, fit, f]); // eslint-disable-line react-hooks/exhaustive-deps

  const appear = spring({frame: f, fps, config: {damping: 16, stiffness: 120}});
  const out = interpolate(f, [dur - 8, dur], [1, 0], clamp);
  // 3D: ghim dự án nằm trên ĐỈNH khối dự án (đẩy lên theo chiều cao khối trên màn hình)
  const towerLift = (p: Place) => {
    if (!map || !e.d3) return 0;
    const i = places.indexOf(p);
    if (i < 0 || (i === 0 && e.tower === false)) return 0;
    const mpp = (40075016.686 * Math.cos((p.lat * Math.PI) / 180)) / (512 * Math.pow(2, map.getZoom()));
    const mpp0 = fit ? (40075016.686 * Math.cos((places[0].lat * Math.PI) / 180)) / (512 * Math.pow(2, fit.zoom)) : mpp;
    const k = i === 0 ? ease(Math.max(0, Math.min(1, (f - I * 0.35) / (I * 0.9)))) : ease(Math.max(0, Math.min(1, (f - (I + (i - 1) * S + S * 0.55)) / 14)));
    const h = i === 0 ? Math.max(e.towerH ?? 180, 300 * mpp0) : Math.max(120, 200 * mpp0);
    return (h * k / mpp) * Math.sin((map.getPitch() * Math.PI) / 180) * 0.92;
  };
  const proj = (p: Place) => {
    if (!map) return null;
    const q = map.project([p.lng, p.lat]);
    return {x: q.x, y: q.y - towerLift(p)};
  };
  const Pin = (Icons as any).House;
  return (
    <AbsoluteFill style={{opacity: out, ...(card ? {alignItems: 'center', justifyContent: 'center'} : {})}}>
      <div
        style={{
          position: 'relative', width: W, height: H, overflow: 'hidden', background: globe ? '#03060d' : e.theme === 'toi' ? '#0b1a33' : '#eef0f3',
          ...(card ? {borderRadius: 44, boxShadow: '0 30px 80px rgba(0,0,0,.5)', border: '4px solid rgba(255,255,255,.85)', transform: `scale(${0.85 + 0.15 * appear})`, opacity: appear} : {}),
        }}
      >
        <div ref={box} style={{position: 'absolute', inset: 0, width: W, height: H}} />
        {fail && (
          <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', color: '#fff', background: '#1f2937', fontSize: 36, padding: 60, textAlign: 'center', fontFamily: 'sans-serif'}}>
            🗺 {fail}
          </AbsoluteFill>
        )}
        {!places.length && (
          <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', color: '#475569', fontSize: 40, fontFamily: 'sans-serif'}}>🗺 Thêm địa điểm cho bản đồ</AbsoluteFill>
        )}
        {map &&
          (() => {
            // tránh nhãn đè nhau: thử đặt trên ghim, đụng nhãn đã đặt thì xuống dưới ghim
            const boxes: number[][] = [];
            const below: boolean[] = [];
            places.forEach((p, i) => {
              const q = proj(p);
              if (!q) return;
              const main = i === 0, fs = main ? 40 : 32;
              const w = (p.name.length + (!main && p.label ? p.label.length + 3 : 0)) * fs * 0.56 + (main ? 48 : 36), h = fs + (main ? 24 : 18);
              const ax = q.x > W * 0.68 ? 1 : q.x < W * 0.32 ? 0 : 0.5;
              const x0 = q.x - w * ax, pinH = main ? 74 : 44;
              const up = [x0, q.y - pinH - h, x0 + w, q.y - pinH], dn = [x0, q.y + 22, x0 + w, q.y + 22 + h];
              const hit = (b: number[]) => boxes.some((o) => b[0] < o[2] && o[0] < b[2] && b[1] < o[3] && o[1] < b[3]);
              const useDn = !main && hit(up) && !hit(dn);
              below[i] = useDn;
              boxes.push(useDn ? dn : up);
            });
            return places.map((p, i) => {
            const q = proj(p);
            if (!q) return null;
            const k = i === 0 ? spring({frame: f - Math.round(I * 0.5), fps, config: {damping: 9, stiffness: 160}}) : spring({frame: Math.round(f - (I + (i - 1) * S + S * 0.62)), fps, config: {damping: 10, stiffness: 170}});
            if (k <= 0.01) return null;
            const main = i === 0;
            // ghim gần mép: nhãn lệch vào trong cho khỏi bị cắt
            const ax = q.x > W * 0.68 ? 'flex-end' : q.x < W * 0.32 ? 'flex-start' : 'center';
            const tx = ax === 'flex-end' ? `calc(-100% + ${main ? 32 : 17}px)` : ax === 'flex-start' ? `-${main ? 32 : 17}px` : '-50%';
            const dn = below[i];
            const half = main ? 32 : 17;
            return (
              <div key={i} style={{position: 'absolute', left: q.x, top: q.y, transform: `translate(${tx}, ${dn ? -half + 'px' : '-100%'}) scale(${k})`, transformOrigin: dn ? '50% 0%' : '50% 100%', display: 'flex', flexDirection: dn ? 'column-reverse' : 'column', alignItems: ax, pointerEvents: 'none'}}>
                <div
                  style={{
                    fontFamily: '"Be Vietnam Pro", sans-serif', fontWeight: 800, fontSize: main ? 40 : 32, whiteSpace: 'nowrap', padding: main ? '10px 24px' : '8px 18px', borderRadius: 999,
                    color: main ? theme.dark : '#fff', background: main ? `linear-gradient(180deg, ${theme.gold1}, ${theme.gold2})` : `linear-gradient(135deg, ${theme.light}, ${theme.dark})`,
                    boxShadow: '0 8px 24px rgba(0,0,0,.35)', border: '3px solid rgba(255,255,255,.9)', ...(dn ? {marginTop: 10} : {marginBottom: 10}),
                  }}
                >
                  {p.name}
                  {!main && p.label ? <span style={{opacity: 0.9, fontWeight: 600}}> · {p.label}</span> : null}
                </div>
                <div style={{width: main ? 64 : 34, height: main ? 64 : 34, borderRadius: '50%', background: main ? theme.gold2 : col, border: '5px solid #fff', boxShadow: '0 6px 18px rgba(0,0,0,.4)', display: 'grid', placeItems: 'center'}}>
                  {main && Pin ? <Pin size={30} color={theme.dark} strokeWidth={2.6} /> : null}
                </div>
              </div>
            );
            });
          })()}
        {map && (e.arrow || e.mover) && Array.from({length: n}, (_, q) => q + 1).map((i) => {
          // đầu tuyến đang vẽ: mũi tên (ở lại khi vẽ xong) + xe / máy bay chạy (ẩn khi tới nơi)
          const k = ease(drawK(i));
          if (k <= 0.001) return null;
          const r = routeOf({...e, places}, i);
          const tipL = sliceLine(r, k).slice(-1)[0], preL = sliceLine(r, Math.max(0, k - 0.03)).slice(-1)[0];
          if (!tipL || !preL) return null;
          const a = map.project(preL), b = map.project(tipL);
          const ang = Math.hypot(b.x - a.x, b.y - a.y) > 0.5 ? screenAngle(a, b) : 0;
          const mv = e.mover && k < 0.995 ? e.mover : '';
          const MI = mv && (Icons as any)[MOVER[mv] || ''];
          return (
            <React.Fragment key={'tip' + i}>
              {e.arrow && !mv && (
                <div style={{position: 'absolute', left: b.x, top: b.y, transform: `translate(-50%, -50%) rotate(${ang}deg)`, width: 0, height: 0, borderLeft: '17px solid transparent', borderRight: '17px solid transparent', borderBottom: `30px solid ${col}`, filter: 'drop-shadow(0 3px 4px rgba(0,0,0,.4))'}} />
              )}
              {mv && (
                <div style={{position: 'absolute', left: b.x, top: b.y, transform: 'translate(-50%, -50%)', width: 66, height: 66, borderRadius: '50%', background: '#fff', border: `5px solid ${col}`, boxShadow: '0 8px 20px rgba(0,0,0,.4)', display: 'grid', placeItems: 'center', fontSize: 36}}>
                  {MI ? <div style={{transform: mv === 'plane' || mv === 'may-bay' ? `rotate(${ang - 45}deg)` : undefined, display: 'grid'}}><MI size={34} color={col} strokeWidth={2.6} /></div> : mv}
                </div>
              )}
            </React.Fragment>
          );
        })}
        <div style={{position: 'absolute', right: 14, bottom: 10, fontSize: 18, color: e.theme === 'toi' ? 'rgba(255,255,255,.55)' : 'rgba(0,0,0,.45)', fontFamily: 'sans-serif', textAlign: 'right'}}>© OpenFreeMap © OpenStreetMap{e.terrain ? <><br />{DEM_CREDIT}</> : null}</div>
      </div>
    </AbsoluteFill>
  );
};
