// Đóng gói bộ dựng HyperFrames: remotion/src (giữ nguyên) + 'remotion' -> remotion/hf/shim.tsx
// node remotion/hf/build.mjs <thư mục ra>
import * as esbuild from 'esbuild';
import path from 'node:path';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..', '..');
const out = path.resolve(process.argv[2] || path.join(root, '_cache', 'hfbundle'));
fs.mkdirSync(out, {recursive: true});
const shim = path.join(here, 'shim.tsx');

await esbuild.build({
  entryPoints: [path.join(root, 'remotion', 'src', 'index.ts')],
  bundle: true,
  outfile: path.join(out, 'bundle.js'),
  format: 'iife',
  platform: 'browser',
  target: ['chrome110'],
  jsx: 'automatic',
  minify: true,
  legalComments: 'none',
  logLevel: 'error',
  define: {'process.env.NODE_ENV': '"production"'},
  loader: {'.woff2': 'file', '.woff': 'file', '.ttf': 'file', '.otf': 'file', '.png': 'file', '.jpg': 'file', '.svg': 'file', '.glb': 'file'},
  assetNames: 'assets/[name]-[hash]',
  plugins: [{
    name: 'remotion-shim',
    setup(b) {
      b.onResolve({filter: /^remotion$/}, () => ({path: shim}));
      b.onResolve({filter: /^@remotion\//}, (a) => ({errors: [{text: `Gói ${a.path} chưa có bản thay thế cho HyperFrames`}]}));
    },
  }],
});
console.log('OK ' + out);
