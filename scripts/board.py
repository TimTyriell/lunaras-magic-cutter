"""Render a local HTML review board for clip candidates.

Usage: python scripts/board.py <stem>
Writes work/<stem>/board.html (self-contained, open in browser). Per candidate: description,
transcript excerpt, YouTube preview of the exact window, pick/maybe/skip + note + window tweak.
Feedback persists in the browser (localStorage) and exports as feedback_<stem>.json
-> ingest with scripts/feedback.py.
"""
import json
import sys
import tomllib
import webbrowser

from paths import CONFIG, FINAL, load, session_dir


def excerpt(segs, c, pad=5):
    return [{"t": s["start"], "p": s["person"], "ch": s["character"], "x": s["text"]}
            for s in segs if s["end"] > c["start"] - pad and s["start"] < c["end"] + pad]


def main(stem, *flags):
    d = session_dir(stem)
    head = load(FINAL / f"{stem}.json")
    segs = load(d / "segments.json")
    cands = load(d / "candidates.json")
    for c in cands:
        c["lines"] = excerpt(segs, c)
        c["screens"] = [f"screens/{p.name}" for p in sorted((d / "screens").glob(f"{c['id']}_*.jpg"))]
    colors = {k: v["color"] for k, v in tomllib.loads((CONFIG / "speakers.toml").read_text(encoding="utf-8")).items()}
    data = {"stem": stem, "title": head["video_title"], "video_id": stem.split("_", 2)[2],
            "colors": colors, "cands": cands}
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out = d / "board.html"
    out.write_text(TEMPLATE.replace("__DATA__", blob), encoding="utf-8")
    print(out)
    if "--open" in flags:
        webbrowser.open(out.as_uri())


TEMPLATE = r"""<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Clip Board</title>
<style>
:root{--bg:#f6f5f2;--card:#fff;--ink:#1d1d1f;--mute:#6b6b70;--line:#e3e1dc;--pick:#1f9d55;--maybe:#c98a00;--skip:#c0392b;--acc:#3b5bdb}
@media (prefers-color-scheme:dark){:root{--bg:#141416;--card:#1e1e22;--ink:#ececf0;--mute:#9a9aa3;--line:#2e2e34;--acc:#7c94ff}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
header{position:sticky;top:0;z-index:2;background:var(--bg);border-bottom:1px solid var(--line);padding:12px 16px;display:flex;flex-wrap:wrap;gap:12px;align-items:center}
h1{font-size:17px;margin:0;flex:1 1 300px}.stat{color:var(--mute);font-size:13px}
button{font:inherit;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:8px;padding:6px 12px;cursor:pointer}
button.primary{background:var(--acc);border-color:var(--acc);color:#fff}
select{font:inherit;background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:5px}
main{max-width:980px;margin:0 auto;padding:16px;display:grid;gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-left:6px solid var(--line);border-radius:12px;padding:16px}
.card[data-v=pick]{border-left-color:var(--pick)}.card[data-v=maybe]{border-left-color:var(--maybe)}.card[data-v=skip]{border-left-color:var(--skip);opacity:.6}
.top{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:baseline}.id{font-weight:700;font-size:18px}
.chip{font-size:12px;padding:2px 8px;border-radius:99px;border:1px solid var(--line);color:var(--mute)}
.score{font-weight:700}.hook{font-size:17px;font-weight:600;margin:8px 0 4px}.why{color:var(--mute);margin:0 0 10px}
details{margin:8px 0}summary{cursor:pointer;color:var(--acc)}
.tx{max-height:260px;overflow:auto;border:1px solid var(--line);border-radius:8px;padding:8px 10px;font-size:14px}
.tx p{margin:4px 0}.tx .out{opacity:.45}.tx b{font-weight:600}.ts{color:var(--mute);font-variant-numeric:tabular-nums;font-size:12px;margin-right:6px}
.vid{aspect-ratio:16/9;width:100%;border:0;border-radius:8px;margin-top:8px;background:#000}
.fb{display:grid;gap:8px;margin-top:12px;border-top:1px solid var(--line);padding-top:12px}
.verd{display:flex;gap:6px;flex-wrap:wrap}.verd button.on[data-x=pick]{background:var(--pick);color:#fff;border-color:var(--pick)}
.verd button.on[data-x=maybe]{background:var(--maybe);color:#fff;border-color:var(--maybe)}.verd button.on[data-x=skip]{background:var(--skip);color:#fff;border-color:var(--skip)}
textarea{width:100%;min-height:54px;font:inherit;background:var(--bg);color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:8px}
.win{display:flex;flex-wrap:wrap;gap:8px;align-items:center;font-size:13px;color:var(--mute)}
.win input{width:90px;font:inherit;background:var(--bg);color:var(--ink);border:1px solid var(--line);border-radius:6px;padding:3px 6px}
a{color:var(--acc)}
.shots{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:6px;margin:8px 0}
.shots img{width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:6px;border:1px solid var(--line);display:block}
</style></head><body>
<header><h1 id="ttl"></h1><span class="stat" id="stat"></span>
<select id="filter"><option value="">alle</option><option value="open">offen</option><option value="pick">pick</option><option value="maybe">maybe</option><option value="skip">skip</option></select>
<button id="copy">Kopieren</button><button class="primary" id="export">Feedback exportieren</button></header>
<main id="list"></main>
<script id="data" type="application/json">__DATA__</script>
<script>
const D=JSON.parse(document.getElementById('data').textContent);
const KEY='clipboard:'+D.stem;
let S={};try{S=JSON.parse(localStorage.getItem(KEY))||{}}catch(e){}
const save=()=>{try{localStorage.setItem(KEY,JSON.stringify(S))}catch(e){};stat()};
const hms=t=>{t=Math.floor(t);return[t/3600|0,(t%3600)/60|0,t%60].map(n=>String(n).padStart(2,'0')).join(':')};
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
document.getElementById('ttl').textContent=D.title;
function st(id){return S[id]||(S[id]={verdict:'',note:''})}
function stat(){const v=Object.values(S);const n=k=>v.filter(x=>x.verdict===k).length;
 document.getElementById('stat').textContent=`${D.cands.length} Kandidaten · ${n('pick')} pick · ${n('maybe')} maybe · ${n('skip')} skip`}
function render(){const f=document.getElementById('filter').value;const L=document.getElementById('list');L.innerHTML='';
 for(const c of D.cands){const s=st(c.id);if(f&&(f==='open'?s.verdict:s.verdict!==f))continue;
  const el=document.createElement('article');el.className='card';el.dataset.v=s.verdict;
  const yt=`https://www.youtube.com/watch?v=${D.video_id}&t=${Math.floor(c.start)}s`;
  const lines=c.lines.map(l=>{const inn=l.t>=c.start-1&&l.t<c.end;return `<p class="${inn?'':'out'}"><span class="ts">${hms(l.t)}</span><b style="color:${D.colors[l.p]||'inherit'}">${esc(l.p)} (${esc(l.ch)})</b>: ${esc(l.x)}</p>`}).join('');
  el.innerHTML=`<div class="top"><span class="id">${c.id}</span><span class="score">${c.score}/10</span><span class="chip">${esc(c.type)}</span>${c.format?`<span class="chip">${esc(c.format)}</span>`:""}
   <span class="chip">${hms(c.start)} – ${hms(c.end)} · ${Math.round(c.end-c.start)} s</span><a href="${yt}" target="_blank" rel="noopener">auf YouTube öffnen ↗</a></div>
   <div class="hook">„${esc(c.hook_line)}“</div><p class="why">${esc(c.why)}</p>
   ${c.screens.length?`<div class="shots">${c.screens.map(p=>`<a href="${p}" target="_blank"><img loading="lazy" src="${p}" alt="Standbild ${c.id}"></a>`).join('')}</div>`:''}
   <details><summary>Transkript</summary><div class="tx">${lines}</div></details>
   <details class="pv"><summary>Vorschau (Fenster)</summary></details>
   <div class="fb"><div class="verd">${['pick','maybe','skip'].map(x=>`<button data-x="${x}" class="${s.verdict===x?'on':''}">${x}</button>`).join('')}</div>
   <textarea placeholder="Feedback: warum (nicht)? Hook? Schnitt?">${esc(s.note)}</textarea>
   <div class="win">Fenster anpassen (s): <input type="number" step="0.5" data-k="start" value="${s.start??c.start}"> bis <input type="number" step="0.5" data-k="end" value="${s.end??c.end}"></div></div>`;
  el.querySelector('.pv').addEventListener('toggle',e=>{const d=e.target;if(d.open&&!d.querySelector('iframe')){d.insertAdjacentHTML('beforeend',`<iframe class="vid" allow="autoplay; encrypted-media" allowfullscreen src="https://www.youtube-nocookie.com/embed/${D.video_id}?start=${Math.floor(s.start??c.start)}&end=${Math.ceil(s.end??c.end)}&rel=0"></iframe><p class="why">Lädt die Vorschau nicht (lokale Datei), nutze „auf YouTube öffnen“.</p>`)}});
  el.querySelectorAll('.verd button').forEach(b=>b.onclick=()=>{s.verdict=s.verdict===b.dataset.x?'':b.dataset.x;save();render()});
  el.querySelector('textarea').oninput=e=>{s.note=e.target.value;save()};
  el.querySelectorAll('.win input').forEach(i=>i.onchange=()=>{s[i.dataset.k]=parseFloat(i.value);save()});
  L.appendChild(el)}}
function payload(){return JSON.stringify({stem:D.stem,exported:new Date().toISOString(),items:D.cands.map(c=>({id:c.id,...st(c.id),start:st(c.id).start??c.start,end:st(c.id).end??c.end}))},null,2)}
document.getElementById('export').onclick=()=>{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([payload()],{type:'application/json'}));a.download=`feedback_${D.stem}.json`;a.click()};
document.getElementById('copy').onclick=()=>navigator.clipboard.writeText(payload()).then(()=>alert('Feedback-JSON kopiert'));
document.getElementById('filter').onchange=render;
stat();render();
</script></body></html>
"""

if __name__ == "__main__":
    main(*sys.argv[1:])
