"use strict";

const fs = require("fs");
const path = require("path");
const sharp = require("sharp");
const { mathjax } = require("mathjax-full/js/mathjax.js");
const { TeX } = require("mathjax-full/js/input/tex.js");
const { SVG } = require("mathjax-full/js/output/svg.js");
const { liteAdaptor } = require("mathjax-full/js/adaptors/liteAdaptor.js");
const { RegisterHTMLHandler } = require("mathjax-full/js/handlers/html.js");
const { AllPackages } = require("mathjax-full/js/input/tex/AllPackages.js");

const adaptor = liteAdaptor();
RegisterHTMLHandler(adaptor);
const tex = new TeX({ packages: AllPackages });
const svgOut = new SVG({ fontCache: "local" });
const doc = mathjax.document("", { InputJax: tex, OutputJax: svgOut });

const equations = {
  "Q1-01": String.raw`Q_{ig}=\frac{1}{m_g}\sum_{j=1}^{m_g}z_{igj},\qquad Q_i=\frac{1}{3}\sum_{g=1}^{3}Q_{ig}`,
  "Q2-01": String.raw`L_0(N_B,D_B)=E+A N_B^{-\alpha}+B D_B^{-\beta}`,
  "Q2-02": String.raw`\Delta_Q(Q_B)=-k_{\mathrm{add}}(Q_B-0.6)`,
  "Q2-03": String.raw`L_{\mathrm{gen}}^{(s)}=L_0+\rho_Q^{(s)}\Delta_Q\!\left(h_s(Q_A)\right)+\tau_p^{(s)}c^{\mathsf T}(p-p_0)`,
  "Q2-04": String.raw`\frac{\partial L}{\partial N_B}=-\alpha A N_B^{-\alpha-1},\qquad \frac{\partial L}{\partial D_B}=-\beta B D_B^{-\beta-1}`,
  "Q3-01": String.raw`C=6ND+\eta NDH,\qquad N=10^9N_B,\qquad D=10^9D_B`,
  "Q4-01": String.raw`M_0:\ y=a;\qquad M_1:\ y=a+b_C\log_{10}C;\qquad M_2:\ y=a+b_C\log_{10}C+b_Tt`,
};

function toSvg(latex) {
  const html = adaptor.outerHTML(doc.convert(latex, { display: true }));
  const a = html.indexOf("<svg");
  const b = html.indexOf("</svg>");
  let svg = a !== -1 && b !== -1 ? html.slice(a, b + 6) : html;
  svg = svg.replace(/<\?xml[^>]*>/g, "");
  if (!/xmlns="http:\/\/www\.w3\.org\/2000\/svg"/.test(svg)) {
    svg = svg.replace(/<svg /, '<svg xmlns="http://www.w3.org/2000/svg" ');
  }
  svg = svg.replace(/(width|height)="([0-9.]+)(ex|em)"/g, (_m, attr, num) => {
    const px = Math.round(parseFloat(num) * 9.5);
    return `${attr}="${px}px"`;
  });
  return svg.replace(/currentColor/g, "#000000");
}

async function main() {
  const outDir = path.resolve(__dirname, "equations");
  fs.mkdirSync(outDir, { recursive: true });
  for (const [id, latex] of Object.entries(equations)) {
    const svg = Buffer.from(toSvg(latex));
    const out = path.join(outDir, `${id}.png`);
    await sharp(svg, { density: 300 }).png().toFile(out);
    process.stdout.write(`${out}\n`);
  }
}

main().catch((error) => {
  process.stderr.write(String(error) + "\n");
  process.exit(1);
});
