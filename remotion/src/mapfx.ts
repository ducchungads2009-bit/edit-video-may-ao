/* Hiệu ứng bản đồ dùng chung cho khối `map` (MapBlock) và `mapTour` (MapTour) — kiểu GEOlayers:
   - terrain: ĐỊA HÌNH 3D (núi đồi nổi khối) + hillshade (đổ bóng địa hình) — dữ liệu độ cao Terrain Tiles (AWS Open Data, miễn phí)
   - globe: QUẢ ĐỊA CẦU (zoom từ ngoài không gian xuống) + khí quyển
   - colors: TỰ CHỈNH MÀU bản đồ {land, water, park, road, building, label, boundary}
   - routeStyle / arrow / mover: tuyến đường nét đứt / phát sáng, mũi tên đầu tuyến, xe / máy bay chạy dọc tuyến */
export const DEM_URL = 'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png';
export const DEM_CREDIT = 'Địa hình: Terrain Tiles (Mapzen, AWS Open Data)';

export type MapFx = {
  terrain?: boolean | number; // true = độ nổi 1.5; số = hệ số phóng độ cao
  hillshade?: boolean; // mặc định bật khi có terrain
  globe?: boolean;
  colors?: {land?: string; water?: string; park?: string; road?: string; building?: string; label?: string; boundary?: string; sky?: string};
};

const firstSymbol = (map: any) => (map.getStyle().layers || []).find((L: any) => L.type === 'symbol')?.id;

/** địa hình 3D + đổ bóng; gọi sau khi style tải xong */
export const addTerrain = (map: any, fx: MapFx, dark = false) => {
  if (!fx.terrain) return;
  const ex = typeof fx.terrain === 'number' ? fx.terrain : 1.5;
  try {
    map.addSource('dem', {type: 'raster-dem', tiles: [DEM_URL], tileSize: 256, maxzoom: 15, encoding: 'terrarium'});
    if (fx.hillshade !== false) {
      map.addSource('dem2', {type: 'raster-dem', tiles: [DEM_URL], tileSize: 256, maxzoom: 15, encoding: 'terrarium'});
      map.addLayer({id: 'hillshade', type: 'hillshade', source: 'dem2', paint: {
        'hillshade-exaggeration': 0.55, 'hillshade-shadow-color': dark ? '#000814' : '#3b4252', 'hillshade-highlight-color': dark ? '#3a5a8a' : '#ffffff',
        'hillshade-accent-color': dark ? '#0b1a33' : '#5b6474', 'hillshade-illumination-direction': 315,
      }}, firstSymbol(map));
    }
    map.setTerrain({source: 'dem', exaggeration: ex});
  } catch {
    /* style không hỗ trợ */
  }
};

/** quả địa cầu + khí quyển (MapLibre 5): ở zoom thấp thấy cả quả cầu, zoom cao tự thành phẳng */
export const addGlobe = (map: any, fx: MapFx, dark = true) => {
  if (!fx.globe) return;
  try {
    map.setProjection({type: 'globe'});
    map.setSky({
      'sky-color': fx.colors?.sky || (dark ? '#0b1a33' : '#9cc7f0'), 'horizon-color': dark ? '#24466f' : '#e6f1fb', 'fog-color': dark ? '#0b1a33' : '#ffffff',
      'sky-horizon-blend': 0.6, 'horizon-fog-blend': 0.5, 'fog-ground-blend': 0.6,
      'atmosphere-blend': ['interpolate', ['linear'], ['zoom'], 0, 1, 5, 1, 8, 0],
    } as any);
  } catch {
    /* bản MapLibre cũ */
  }
};

/** đổi màu từng nhóm lớp bản đồ theo màu người dùng chọn (để trống nhóm nào thì giữ nguyên) */
export const applyColors = (map: any, fx: MapFx) => {
  const c = fx.colors;
  if (!c) return;
  for (const L of map.getStyle().layers || []) {
    const id = String(L.id).toLowerCase();
    const set = (prop: string, v?: string) => {
      if (!v) return;
      try {
        map.setPaintProperty(L.id, prop, v);
      } catch {}
    };
    const water = id.includes('water') || id.includes('ocean') || id.includes('river') || id.includes('lake');
    const park = id.includes('park') || id.includes('landcover') || id.includes('wood') || id.includes('grass') || id.includes('forest');
    const road = id.includes('road') || id.includes('highway') || id.includes('street') || id.includes('transportation') || id.includes('bridge') || id.includes('tunnel');
    if (L.type === 'background') set('background-color', c.land);
    else if (L.type === 'fill') set('fill-color', water ? c.water : park ? c.park : id.includes('building') ? c.building : c.land);
    else if (L.type === 'line') {
      if (water) set('line-color', c.water);
      else if (road) set('line-color', c.road);
      else if (id.includes('boundary') || id.includes('admin')) set('line-color', c.boundary);
    } else if (L.type === 'fill-extrusion' && L.id !== 'k3d' && L.id !== 'rx') set('fill-extrusion-color', c.building);
    else if (L.type === 'symbol') set('text-color', c.label);
  }
};

/** góc (độ, 0 = hướng lên) từ a tới b trên màn hình */
export const screenAngle = (a: {x: number; y: number}, b: {x: number; y: number}) => (Math.atan2(b.x - a.x, -(b.y - a.y)) * 180) / Math.PI;

/** icon xe / máy bay chạy dọc tuyến */
export const MOVER: Record<string, string> = {car: 'Car', xe: 'Car', moto: 'Bike', bike: 'Bike', plane: 'Plane', 'may-bay': 'Plane', walk: 'Footprints', bus: 'Bus', ship: 'Ship', train: 'TrainFront'};
