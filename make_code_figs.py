# -*- coding: utf-8 -*-
"""Render notebook code + real output as Jupyter-style images sized for 16:9 slides.

Kept wide (aspect ~2.2) and set at 13pt so the code is still legible once the image
is scaled down onto a slide.
"""
import matplotlib as mpl, matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
mpl.rcParams['savefig.dpi'] = 220

SURF='#fcfcfb'; CELLBG='#f5f5f3'; INK='#1b1b1a'
KW='#a626a4'; STR='#0a7c3e'; NUM='#b35309'; CMT='#8a8985'; FN='#2a78d6'; PROMPT='#3f6ea8'
KEYWORDS={'import','from','as','def','for','in','if','else','elif','return','lambda',
          'not','and','or','assert','print','True','False','None','while'}

def colorize(line):
    if line.lstrip().startswith('#'):
        return [(line, CMT)]
    out=[]; i=0
    while i < len(line):
        ch=line[i]
        if ch in '"\'':
            q=ch; j=i+1
            while j < len(line) and line[j]!=q: j+=1
            out.append((line[i:j+1], STR)); i=j+1
        elif ch=='#':
            out.append((line[i:], CMT)); break
        elif ch.isalpha() or ch=='_':
            j=i
            while j < len(line) and (line[j].isalnum() or line[j]=='_'): j+=1
            w=line[i:j]; nxt=line[j] if j < len(line) else ''
            out.append((w, KW if w in KEYWORDS else (FN if nxt=='(' else INK))); i=j
        elif ch.isdigit():
            j=i
            while j < len(line) and (line[j].isdigit() or line[j]=='.'): j+=1
            out.append((line[i:j], NUM)); i=j
        else:
            out.append((ch, INK)); i+=1
    return out

def render(cells, path, title, width=13.0, fs=13.0):
    lh    = 0.0202 * fs                                # line height, inches
    chw   = fs * 0.00833                               # monospace char width, inches
    x0    = 1.12                                       # left edge of code text
    maxc  = int((width - x0 - 0.30) / chw)             # chars that fit on one line

    over = [(k, len(ln), ln[:60]) for k, (c, o) in enumerate(cells, 1)
            for ln in (c + '\n' + o).split('\n') if len(ln) > maxc]
    if over:
        raise SystemExit(f'line too long for a {width}in canvas (max {maxc} chars): {over}')

    # exact layout height: per cell = code box + gap + output + spacer
    height = 0.90 + 0.10 + sum(len(c.split('\n')) * lh + 0.18 + 0.15
                               + len(o.split('\n')) * lh + 0.30 for c, o in cells)
    fig = plt.figure(figsize=(width, height), facecolor=SURF)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, width); ax.set_ylim(0, height); ax.axis('off')
    ax.text(0.30, height - 0.32, title, fontsize=17, fontweight='bold', color=INK, va='center')
    ax.plot([0.30, width - 0.30], [height - 0.60]*2, color='#e3e2de', lw=1.1)

    y = height - 0.90
    for k, (code, outp) in enumerate(cells, 1):
        lines = code.split('\n')
        box_h = len(lines) * lh + 0.18
        ax.add_patch(FancyBboxPatch((0.98, y - box_h + 0.07), width - 1.28, box_h,
                                    boxstyle='round,pad=0.02,rounding_size=0.03',
                                    fc=CELLBG, ec='#e3e2de', lw=1.0))
        ax.text(0.30, y - 0.11, f'In [{k}]:', fontsize=fs - 1.2, color=PROMPT,
                family='DejaVu Sans Mono', va='top')
        yy = y - 0.11
        for ln in lines:
            x = 1.12
            for tok, col in colorize(ln):
                ax.text(x, yy, tok, fontsize=fs, color=col,
                        family='DejaVu Sans Mono', va='top', ha='left')
                x += len(tok) * fs * 0.00833
            yy -= lh
        y -= box_h + 0.15
        for ln in outp.split('\n'):
            ax.text(1.12, y, ln, fontsize=fs - 0.8, color='#333331',
                    family='DejaVu Sans Mono', va='top')
            y -= lh
        y -= 0.30
    fig.savefig(path, facecolor=SURF)   # no tight bbox: keeps both code images the same width
    plt.close(fig)
    with __import__('PIL.Image', fromlist=['Image']).open(path) as im:
        w, h = im.size
    print(f'saved {path}   {w}x{h}  aspect {w/h:.2f}')

# ---------------- 1 : data quality -> exact reconstruction -> the key feature ----------
render([
("""# Do the derived columns really equal what their names claim? Verify before trusting them.
checks = [('Production = Yield x Area',       df.Yield_Tonnes_Ha * df.Farm_Area_Hectares),
          ('Revenue    = Production x Price', df.Production_Tonnes * df.Market_Price_INR_Tonne),
          ('Profit     = Revenue - Cost',     df.Revenue_INR - df.Total_Cost_INR)]
for (label, lhs), rhs in zip(checks, [df.Production_Tonnes, df.Revenue_INR, df.Profit_INR]):
    print(f'{label:34s} max error = {(lhs - rhs).abs().max():.4f}')""",
"""Production = Yield x Area          max error = 0.0050
Revenue    = Production x Price     max error = 0.5000
Profit     = Revenue - Cost         max error = 0.0000      <- identities hold exactly"""),

("""# Because they hold, the 32 missing yields are RECONSTRUCTED, not estimated:
mask = df.Yield_Tonnes_Ha.isna()
df.loc[mask, 'Yield_Tonnes_Ha'] = (df.loc[mask, 'Production_Tonnes']
                                   / df.loc[mask, 'Farm_Area_Hectares']).round(2)

# THE KEY FEATURE - sugarcane yields 48 t/ha and pulses 0.9 t/ha, so a raw average
# measures crop mix, not seasonal performance. Divide by each crop's own median.
df['Rel_Yield'] = df.Yield_Tonnes_Ha / df.groupby('Crop').Yield_Tonnes_Ha.transform('median')
print(df.groupby('Crop').agg(raw=('Yield_Tonnes_Ha','median'), rel=('Rel_Yield','median')))""",
"""             raw    rel
Pulses      0.94  1.000
Wheat       2.22  1.000
Sugarcane  48.03  1.000     <- a 51x range collapsed onto one comparable scale"""),
], 'figures/code01_cleaning.png',
   'Data-quality audit, exact reconstruction, and the key engineered feature')

# ---------------- 2 : the trap, and what the nested models show ----------------------
render([
("""# The obvious test FAILS - between-crop variance (0.3 to 101 t/ha) swamps the effect
F, p = stats.f_oneway(*[g.Yield_Tonnes_Ha.values for _, g in df.groupby('Season')])
print(f'ANOVA on RAW yield         F = {F:6.2f}   p = {p:.3f}    <- NOT significant')

H, p = stats.kruskal(*[g.Rel_Yield.values for _, g in df.groupby('Season')])
print(f'Kruskal on CROP-RELATIVE   H = {H:6.2f}   p = {p:.1e}  <- highly significant')""",
"""ANOVA on RAW yield         F =   1.46   p = 0.232    <- NOT significant
Kruskal on CROP-RELATIVE   H = 254.13   p = 6.5e-56  <- highly significant"""),

("""# Does the SEASON LABEL explain yield, or do the measurable growing CONDITIONS?
for name, X in [('A  season dummies only',     S),
                ('B  growing conditions only', ENV_X),
                ('C  conditions + season',     np.column_stack([ENV_X, S]))]:
    _, r2, adj, k = ols(X, y)
    print(f'{name:30s} R2 = {r2:.4f}   adj R2 = {adj:.4f}   vars = {k-1}')""",
"""A  season dummies only         R2 = 0.0603   adj R2 = 0.0598   vars = 2
B  growing conditions only     R2 = 0.1245   adj R2 = 0.1212   vars = 15
C  conditions + season         R2 = 0.1297   adj R2 = 0.1259   vars = 17

-> Conditions explain 2.1x what the season label does; season adds only +0.005.
   Season is a PROXY for growing conditions - and conditions can be managed."""),
], 'figures/code02_testing.png',
   'The trap in the obvious test, and what the nested models reveal')
