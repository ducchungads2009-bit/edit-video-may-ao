/* Thư viện font có tiếng Việt (danh sách ở remotion/fonts.json) */
import '@fontsource/be-vietnam-pro/400.css';
import '@fontsource/be-vietnam-pro/700.css';
import '@fontsource/be-vietnam-pro/900.css';
import '@fontsource/montserrat/400.css';
import '@fontsource/montserrat/700.css';
import '@fontsource/montserrat/900.css';
import '@fontsource/inter/400.css';
import '@fontsource/inter/700.css';
import '@fontsource/inter/900.css';
import '@fontsource/roboto/400.css';
import '@fontsource/roboto/700.css';
import '@fontsource/roboto/900.css';
import '@fontsource/lexend/400.css';
import '@fontsource/lexend/700.css';
import '@fontsource/lexend/900.css';
import '@fontsource/nunito/400.css';
import '@fontsource/nunito/700.css';
import '@fontsource/nunito/900.css';
import '@fontsource/josefin-sans/400.css';
import '@fontsource/josefin-sans/700.css';
import '@fontsource/chakra-petch/400.css';
import '@fontsource/chakra-petch/700.css';
import '@fontsource/oswald/400.css';
import '@fontsource/oswald/700.css';
import '@fontsource/barlow-condensed/400.css';
import '@fontsource/barlow-condensed/700.css';
import '@fontsource/barlow-condensed/900.css';
import '@fontsource/saira-condensed/400.css';
import '@fontsource/saira-condensed/700.css';
import '@fontsource/saira-condensed/900.css';
import '@fontsource/anton/400.css';
import '@fontsource/bungee/400.css';
import '@fontsource/paytone-one/400.css';
import '@fontsource/baloo-2/400.css';
import '@fontsource/baloo-2/700.css';
import '@fontsource/baloo-2/800.css';
import '@fontsource/playfair-display/400.css';
import '@fontsource/playfair-display/700.css';
import '@fontsource/playfair-display/900.css';
import '@fontsource/playfair-display/700-italic.css';
import '@fontsource/playfair-display/400-italic.css';
import '@fontsource/merriweather/400.css';
import '@fontsource/merriweather/700.css';
import '@fontsource/merriweather/900.css';
import '@fontsource/lobster/400.css';
import '@fontsource/pacifico/400.css';
import '@fontsource/dancing-script/400.css';
import '@fontsource/dancing-script/700.css';
import '@fontsource/patrick-hand/400.css';
import list from '../fonts.json';

export type FontInfo = {id: string; family: string; kind: string; weights: number[]; note: string};
export const FONTS = list as FontInfo[];
export const DEFAULT_FONT = 'Be Vietnam Pro';
/** tên font (family hoặc id) -> CSS font-family */
export const fontCss = (name?: string) => {
  const f = name && FONTS.find((x) => x.family.toLowerCase() === name.toLowerCase() || x.id === name.toLowerCase());
  const kind = f?.kind === 'serif' ? 'serif' : f?.kind === 'script' || f?.kind === 'hand' ? 'cursive' : 'sans-serif';
  return `"${f ? f.family : DEFAULT_FONT}", "${DEFAULT_FONT}", ${kind}`;
};
/** độ đậm gần nhất font có */
export const fontWeight = (name: string | undefined, want: number) => {
  const f = name && FONTS.find((x) => x.family.toLowerCase() === name.toLowerCase() || x.id === name.toLowerCase());
  const ws = f ? f.weights : [400, 700, 900];
  return ws.reduce((a, b) => (Math.abs(b - want) < Math.abs(a - want) ? b : a), ws[0]);
};
