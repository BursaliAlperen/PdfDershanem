import dayjs from "dayjs";
import { initRealtime, fetchRemoteState, saveRemoteState, autoInitIfConfigured } from "./rtdb.js";

const ADMIN_IDS = ["8392479231","7904032877"];
const STORAGE_KEY = "pdf_dershanem_v1";

const DEFAULT_DATA = {
  users: {}, // id -> {name, avatar, downloads}
  pdfs: [], // {id, title, url, category, addedAt, downloads, requiredAds}
};

function uid(){return Math.random().toString(36).slice(2,9);}

function load(){
  const raw = localStorage.getItem(STORAGE_KEY);
  if(!raw) { localStorage.setItem(STORAGE_KEY, JSON.stringify(DEFAULT_DATA)); return DEFAULT_DATA; }
  try { return JSON.parse(raw); } catch(e){ localStorage.setItem(STORAGE_KEY, JSON.stringify(DEFAULT_DATA)); return DEFAULT_DATA; }
}
async function save(data){
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  // attempt to persist to Realtime Database if initialized
  try{
    await saveRemoteState(data);
  }catch(e){
    // noop - save locally regardless
  }
}

let state = load();

/* Utilities */
function showToast(msg, t=2000){
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.remove("hidden");
  setTimeout(()=>el.classList.add("hidden"), t);
}

function sanitizeDropboxLink(link){
  // Accept Dropbox share links and transform to direct dl link if possible
  if(!link) return null;
  try{
    const u = new URL(link.trim());
    // if dl=0 -> dl=1
    if(u.hostname.includes("dropbox.com")){
      u.searchParams.set("dl","1");
      return u.toString();
    }
    // allow direct pdf links
    if(link.endsWith(".pdf")) return link;
    return link;
  }catch(e){
    return null;
  }
}

function inferTitleFromUrl(url){
  // try to produce a readable title from a URL or filename: decode, strip query, remove extension and extra chars
  try{
    const u = new URL(url);
    let name = (u.pathname.split("/").pop() || "").split("?")[0];
    // decode percent-encoding
    name = decodeURIComponent(name.replace(/\+/g," "));
    // remove common file extensions
    name = name.replace(/\.(pdf|docx?|pptx?)$/i, "");
    // replace separators with space and collapse multiple spaces
    name = name.replace(/[_\-\.]/g," ").replace(/\s+/g," ").trim();
    // remove leading numbers like "01 - " or "2023_"
    name = name.replace(/^[0-9\-\_\.]+\s*/,"");
    // fallback
    if(!name) name = "PDF";
    return name;
  }catch(e){ return "PDF"; }
}

function inferCategoryFromTitle(title){
  const t = (title||"").toUpperCase();
  // stronger checks with common keywords
  if(/TYT/.test(t) || /\bTEMEL\b/.test(t) || /\bYETENEK\b/.test(t)) return "TYT";
  if(/AYT/.test(t) || /\bALAN\b/.test(t) || /\bYÜKSEK\b/.test(t)) return "AYT";
  if(/\bKPSS\b/.test(t) || /\bKAMU\b/.test(t)) return "KPSS";
  if(/MATEM|MAT\b|GEOMETR|ANALIZ|KALKÜL/.test(t)) return "MATEMATİK";
  if(/FİZİK|KİMYA|BİYOLOJİ|TARİH|COĞRAFYA|EDEBİYAT|İNGİLİZCE|DİN/.test(t)) return "GENEL";
  // fallback
  return "GENEL";
}

/* UI rendering */
const SCR = document.getElementById("screen");
const NAV_BTNS = document.querySelectorAll(".nav-btn");
NAV_BTNS.forEach(b=>b.addEventListener("click", ()=>{ setScreen(b.dataset.screen); NAV_BTNS.forEach(x=>x.classList.remove("active")); b.classList.add("active"); }));

function setScreen(name){
  if(name==="home") renderHome();
  else if(name==="pdfs") renderPDFs();
  else if(name==="profile") renderProfile();
}

/* Home */
function renderHome(){
  SCR.innerHTML = "";
  const card = el("div","card");
  card.innerHTML = `
    <div class="header-row">
      <img id="home-avatar" class="avatar" src="${getCurrentUser().avatar || 'https://cdn.jsdelivr.net/gh/edent/SuperTinyIcons/images/svg/telegram.svg'}" alt="avatar">
      <div>
        <div class="h1">Hoşgeldin, ${getCurrentUser().name || "Kullanıcı"}</div>
        <div class="muted small">PDF DERSHANEM'e hoşgeldiniz</div>
      </div>
      <div style="margin-left:auto;">
        <button id="open-admin" class="btn-ghost small">Admin</button>
      </div>
    </div>
  `;
  SCR.appendChild(card);

  const searchCard = el("div","card");
  searchCard.innerHTML = `
    <div class="search">
      <input id="search-input" class="input" placeholder="Ara: TYT, AYT, KPSS, matematik..." />
      <button id="search-btn" class="btn">Ara</button>
    </div>
    <div class="small-note">Kategoriler</div>
    <div class="categories" id="categories"></div>
  `;
  SCR.appendChild(searchCard);

  // categories
  const cats = ["TYT","AYT","KPSS","MATEMATİK","GENEL"];
  const catsEl = searchCard.querySelector("#categories");
  cats.forEach(c=>{
    const d = el("div","cat");
    d.textContent = c;
    d.addEventListener("click", ()=>{ renderPDFs(c); setActiveNav("pdfs"); });
    catsEl.appendChild(d);
  });

  const recentCard = el("div","card");
  recentCard.innerHTML = `<div class="small muted">Son eklenenler</div><div id="recent-list" class="pdf-list"></div>`;
  SCR.appendChild(recentCard);

  renderRecent();

  document.getElementById("open-admin").addEventListener("click", ()=>openAdminIfAllowed());
  document.getElementById("search-btn").addEventListener("click", ()=> { const q = document.getElementById("search-input").value; renderPDFs(null, q); setActiveNav("pdfs"); });
}

function renderRecent(){
  const list = document.getElementById("recent-list");
  list.innerHTML = "";
  const pdfs = [...state.pdfs].sort((a,b)=> new Date(b.addedAt) - new Date(a.addedAt)).slice(0,6);
  if(pdfs.length===0){ list.innerHTML = `<div class="muted small">Henüz PDF yok</div>`; return; }
  pdfs.forEach(p=>{
    const row = el("div","pdf-item");
    row.innerHTML = `
      <div>
        <div class="pdf-meta">
          <div>
            <div class="pdf-title">${p.title}</div>
            <div class="pdf-cat">${p.category} • ${dayjs(p.addedAt).format("YYYY-MM-DD")} • İndirme: ${p.downloads || 0}</div>
          </div>
        </div>
        <div class="inline-banner" data-banner-for="${p.id}">
          <small>Banner alanı • reklam burada görünecek</small>
        </div>
      </div>
      <div>
        <button class="btn" data-id="${p.id}">İndir</button>
      </div>
    `;
    row.querySelector(".btn").addEventListener("click", ()=>handleDownload(p.id));
    list.appendChild(row);
  });
}

/* PDFs screen */
function renderPDFs(category=null, query=""){
  SCR.innerHTML = "";
  const top = el("div","card");
  top.innerHTML = `<div class="h1">PDF'LER</div><div class="muted small">Kategorilerin arasında gez ve ara</div>`;
  SCR.appendChild(top);

  const searchRow = el("div","card");
  searchRow.innerHTML = `<div class="search"><input id="pdf-search" class="input" placeholder="Arama..." value="${query||""}"/><button id="pdf-search-btn" class="btn">Ara</button></div>`;
  SCR.appendChild(searchRow);

  const listCard = el("div","card");
  listCard.innerHTML = `<div id="pdfs-list" class="pdf-list"></div>`;
  SCR.appendChild(listCard);

  document.getElementById("pdf-search-btn").addEventListener("click", ()=> {
    const q = document.getElementById("pdf-search").value;
    renderPDFs(null, q);
  });

  const filtered = state.pdfs.filter(p=>{
    if(category && p.category !== category) return false;
    if(query && query.trim()!==""){
      const q = query.toLowerCase();
      return p.title.toLowerCase().includes(q) || p.category.toLowerCase().includes(q);
    }
    return true;
  });

  const list = document.getElementById("pdfs-list");
  if(filtered.length===0){ list.innerHTML = `<div class="muted small">Eşleşen PDF yok</div>`; return; }
  filtered.sort((a,b)=> new Date(b.addedAt)-new Date(a.addedAt)).forEach(p=>{
    const item = el("div","pdf-item");
    item.innerHTML = `
      <div style="display:flex;flex-direction:column;gap:8px;">
        <div class="pdf-meta">
          <div>
            <div class="pdf-title">${p.title}</div>
            <div class="pdf-cat">${p.category} • İndirme: ${p.downloads || 0}</div>
          </div>
        </div>

        <div class="inline-banner" data-banner-for="${p.id}">
          <small>Banner alanı • reklam burada görünecek</small>
        </div>
      </div>

      <div style="display:flex;gap:8px;align-items:center">
        <button class="btn-ghost small" data-id="${p.id}" data-admin-remove>Sil</button>
        <button class="btn" data-id="${p.id}">İndir</button>
      </div>
    `;
    item.querySelectorAll("button").forEach(btn=>{
      if(btn.dataset.adminRemove!==undefined){
        btn.addEventListener("click", ()=>{ openAdminIfAllowed(()=>removePDF(p.id)); });
      } else {
        btn.addEventListener("click", ()=>handleDownload(p.id));
      }
    });
    list.appendChild(item);
  });
}

/* Profile */
function getCurrentUser(){
  // persistent, non-editable user id plus lightweight profile stored in localStorage
  // try to read tgId from URL param once (so Telegram web can pass ?tgid=...)
  function readUrlParam(name){
    try{ const p = new URLSearchParams(window.location.search); return p.get(name); }catch(e){return null;}
  }
  const existing = JSON.parse(localStorage.getItem("pdf_dershanem_user")||"null");
  // stable internal id stored separately to ensure immutability across sessions
  let stableId = localStorage.getItem("pdf_dershanem_user_id");
  if(!stableId){
    stableId = uid();
    localStorage.setItem("pdf_dershanem_user_id", stableId);
  }
  if(!existing){
    // generate default name and avatar automatically using stable id
    const autoName = "Telegram Kullanıcı";
    const tgFromUrl = readUrlParam("tgid") || "";
    const avatar = `https://api.dicebear.com/6.x/identicon/svg?seed=${encodeURIComponent(stableId)}`;
    const user = { id: stableId, name: autoName, avatar, tgId: tgFromUrl };
    localStorage.setItem("pdf_dershanem_user", JSON.stringify(user));
    return user;
  } else {
    // ensure fields exist and keep id immutable (use stableId)
    existing.id = stableId;
    if(!("name" in existing) || !existing.name) existing.name = "Telegram Kullanıcı";
    if(!("avatar" in existing) || !existing.avatar) existing.avatar = `https://api.dicebear.com/6.x/identicon/svg?seed=${encodeURIComponent(stableId)}`;
    if(!("tgId" in existing)) existing.tgId = readUrlParam("tgid") || "";
    // if URL provided tgId and not previously set, store it
    const maybeTg = readUrlParam("tgid");
    if(maybeTg && maybeTg !== existing.tgId){
      existing.tgId = maybeTg;
      localStorage.setItem("pdf_dershanem_user", JSON.stringify(existing));
    }
    return existing;
  }
}
function saveCurrentUser(u){
  // preserve immutable id and stable stored id
  const stableId = localStorage.getItem("pdf_dershanem_user_id") || uid();
  const cur = JSON.parse(localStorage.getItem("pdf_dershanem_user")||"null") || {};
  const sanitized = {
    id: stableId,
    name: u.name || cur.name || "Telegram Kullanıcı",
    avatar: u.avatar || cur.avatar || `https://api.dicebear.com/6.x/identicon/svg?seed=${encodeURIComponent(stableId)}`,
    tgId: cur.tgId || u.tgId || ""
  };
  localStorage.setItem("pdf_dershanem_user", JSON.stringify(sanitized));
}

function renderProfile(){
  SCR.innerHTML = "";
  const user = getCurrentUser();
  const totalDownloadsAll = state.pdfs.reduce((s,p)=>s + (p.downloads||0),0);
  const userDownloads = aggregateDownloadsForUser(user.id);
  const p = el("div","card");
  p.innerHTML = `
    <div class="header-row">
      <img id="profile-avatar" class="avatar" src="${user.avatar || 'https://cdn.jsdelivr.net/gh/edent/SuperTinyIcons/images/svg/telegram.svg'}" alt="avatar">
      <div>
        <div class="h1">${user.name}</div>
        <div class="muted small">PDF DERSHANEM profili</div>
        <div class="small muted">ID: ${user.id}</div>
      </div>
      <div style="margin-left:auto;">
        <button id="edit-profile" class="btn-ghost small">Düzenle</button>
      </div>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px;">
      <div class="card" style="padding:10px;">
        <div class="small muted">Sizin indirmeler</div>
        <div class="h1" style="font-size:16px;margin-top:6px;">${userDownloads}</div>
      </div>
      <div class="card" style="padding:10px;">
        <div class="small muted">Toplam indirme (tüm PDF'ler)</div>
        <div class="h1" style="font-size:16px;margin-top:6px;">${totalDownloadsAll}</div>
      </div>
    </div>

    <div class="small-note" style="margin-top:8px;">Kullanıcı bilgilerini düzenlerken ID değiştirilemez.</div>
  `;
  SCR.appendChild(p);

  // edit modal simple (only name/avatar editable; id is fixed)
  document.getElementById("edit-profile").addEventListener("click", ()=>{
    const name = prompt("Profil ismi", user.name) || user.name;
    const avatar = prompt("Avatar URL (TG profil fotoğrafı linki)", user.avatar || "") || user.avatar;
    saveCurrentUser({ ...user, name, avatar });
    showToast("Profil kaydedildi");
    renderProfile();
  });
}

function aggregateDownloadsForUser(uid){
  // simple: count downloads that were incremented and tracked by user in state.users
  const users = state.users || {};
  const u = users[uid];
  return u ? (u.downloads||0) : 0;
}

/* Admin handling */
const ADMIN_MODAL = document.getElementById("admin-modal");
document.getElementById("admin-close").addEventListener("click", ()=>{ ADMIN_MODAL.classList.add("hidden"); ADMIN_MODAL.setAttribute("aria-hidden","true"); });

function openAdminIfAllowed(onSuccess){
  // Automatic admin check: if user's saved Telegram id matches known admin IDs, open admin.
  const me = getCurrentUser();
  const candidate = (me.tgId || "").toString().trim();
  if(candidate && ADMIN_IDS.includes(candidate)){
    ADMIN_MODAL.classList.remove("hidden");
    ADMIN_MODAL.setAttribute("aria-hidden","false");
    renderAdminPanel();
    if(onSuccess) onSuccess();
    return;
  }
  // If not admin, silently do nothing (no prompt). Admins must save their TG id in profile.
  showToast("Admin erişimi için profilinize TG ID ekleyin");
}

function renderAdminPanel(){
  const drop = document.getElementById("admin-dropbox");
  const catInput = document.getElementById("admin-category");
  const adcount = document.getElementById("admin-adcount");
  const addBtn = document.getElementById("admin-add");
  const listEl = document.getElementById("admin-list");
  const statsEl = document.getElementById("admin-stats");
  const usersEl = document.getElementById("admin-users");

  drop.value = "";
  catInput.value = "";
  adcount.value = "1";

  addBtn.onclick = ()=>{
    const raw = drop.value.trim();
    const url = sanitizeDropboxLink(raw);
    if(!url){ showToast("Geçerli Dropbox/pdf linki girin"); return; }
    const title = inferTitleFromUrl(url);
    const category = (catInput.value.trim() || inferCategoryFromTitle(title)).toUpperCase();
    const pdf = { id: uid(), title, url, category, addedAt: new Date().toISOString(), downloads: 0, requiredAds: Math.min(100, Math.max(1, Number(adcount.value||1))) };
    state.pdfs.push(pdf);
    save(state);
    showToast("PDF eklendi");
    renderAdminPanel();
  };

  // list
  listEl.innerHTML = "";
  if(state.pdfs.length===0) listEl.innerHTML = `<div class="muted small">PDF yok</div>`;
  state.pdfs.slice().reverse().forEach(p=>{
    const row = el("div","admin-row");
    row.innerHTML = `<div><strong>${p.title}</strong><div class="small muted">${p.category} • ${p.requiredAds} reklam</div></div><div><button class="btn-ghost small" data-id="${p.id}">Sil</button></div>`;
    row.querySelector("button").addEventListener("click", ()=>{ if(confirm("Silinsin mi?")){ removePDF(p.id); renderAdminPanel(); }});
    listEl.appendChild(row);
  });

  // stats
  const total = state.pdfs.length;
  const totalDownloads = state.pdfs.reduce((s,p)=>s + (p.downloads||0),0);
  statsEl.innerHTML = `<div class="small">PDF sayısı: ${total}</div><div class="small">Toplam indirme: ${totalDownloads}</div>`;

  // users
  usersEl.innerHTML = "";
  const keys = Object.keys(state.users||{});
  if(keys.length===0) usersEl.innerHTML = `<div class="muted small">Kullanıcı yok</div>`;
  keys.forEach(k=>{
    const u = state.users[k];
    const div = document.createElement("div");
    div.className = "small";
    div.textContent = `${u.name || k} • İndirme: ${u.downloads||0}`;
    usersEl.appendChild(div);
  });
}

function removePDF(id){
  state.pdfs = state.pdfs.filter(p=>p.id !== id);
  save(state);
  showToast("PDF silindi");
  renderPDFs();
}

/* Download + Ad logic */
async function handleDownload(pdfId){
  const p = state.pdfs.find(x=>x.id===pdfId);
  if(!p) return showToast("PDF bulunamadı");
  // If p.requiredAds > 0, require watching that many interstitials before direct download
  // We'll simulate ad watching by injecting interstitial.js (already loaded) and prompting user to click "İzle".
  const need = p.requiredAds || 1;
  const proceed = await askToWatchAds(need);
  if(!proceed) return;
  // increment counters
  p.downloads = (p.downloads||0) + 1;
  // track per-user
  const me = getCurrentUser();
  if(!state.users) state.users = {};
  if(!state.users[me.id]) state.users[me.id] = { name: me.name || "Misafir", downloads: 0 };
  state.users[me.id].downloads = (state.users[me.id].downloads || 0) + 1;
  save(state);
  showToast("İndirme başlatılıyor...");
  // Open the pdf url in new tab
  window.open(p.url, "_blank");
  renderPDFs();
  renderRecent();
  renderProfile();
}

function askToWatchAds(count){
  return new Promise((resolve)=>{
    if(count<=0) return resolve(true);
    // show confirm with option to watch ad(s) or cancel
    const willing = confirm(`Bu PDF için ${count} reklam izlenmesi gerekiyor. Reklam izlemek ister misiniz?`);
    if(!willing) return resolve(false);
    // We will attempt to load the interstitial script (it is included in head). Some providers require calling a function; since there's no SDK documented, we will try to emit an event to show it if available, otherwise fallback to a simulated delay.
    try{
      // If the ad provider attaches a global function (e.g., showAd or mndShow), attempt common names
      const tryShow = () => {
        if(typeof window.showad === "function") { window.showad(); return true; }
        if(typeof window.showAd === "function") { window.showAd(); return true; }
        if(typeof window.mndShowAd === "function") { window.mndShowAd(); return true; }
        return false;
      };
      let shown = false;
      // attempt to show required number of ads sequentially
      let i = 0;
      const runNext = ()=>{
        if(i>=count){ resolve(true); return; }
        i++;
        // try to show real ad
        shown = tryShow();
        if(shown){
          // wait a short time assuming ad will run
          setTimeout(()=>{ runNext(); }, 1500);
        } else {
          // Provider likely doesn't expose function. As fallback, open a small popup window to the interstitial script's source (best-effort) and wait 2s to simulate a watch.
          const w = window.open("about:blank","_blank","width=400,height=600");
          if(w){
            w.document.body.innerHTML = `<div style="font-family:Arial;padding:20px;"><h3>Reklam (simülasyon)</h3><p>Reklam izleniyor... (${i}/${count})</p><button id="close">Kapat</button></div>`;
            w.document.getElementById("close").addEventListener("click", ()=>{ w.close(); runNext(); });
            // auto-close after 2500ms
            setTimeout(()=>{ try{ w.close(); }catch(e){}; runNext(); }, 2500);
          } else {
            // popup blocked: simulate timer
            setTimeout(()=>{ runNext(); }, 2000);
          }
        }
      };
      runNext();
    }catch(e){
      // fallback
      setTimeout(()=>resolve(true), 1000);
    }
  });
}

/* small helpers */
function el(tag,cls){ const d = document.createElement(tag); if(cls) d.className = cls; return d; }
function setActiveNav(name){
  NAV_BTNS.forEach(b=> b.classList.toggle("active", b.dataset.screen===name));
}

/* initial render */
// attempt to auto-init Realtime DB if configuration exists in localStorage, then try to fetch remote state and merge
(async ()=>{
  await autoInitIfConfigured();
  if(typeof fetchRemoteState === "function"){
    try{
      const remote = await fetchRemoteState();
      if(remote && typeof remote === "object"){
        // merge remote state (prefer remote for pdfs/users but keep local fallback)
        if(remote.pdfs && Array.isArray(remote.pdfs)) state.pdfs = remote.pdfs;
        if(remote.users && typeof remote.users === "object") state.users = remote.users;
        // persist merged to local
        localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      }
    }catch(e){}
  }
  setScreen("home");

  // auto-open admin if current profile tgId matches known admins
  const me = getCurrentUser();
  if(me.tgId && ADMIN_IDS.includes(me.tgId.toString().trim())){
    setTimeout(()=>{ openAdminIfAllowed(); }, 500);
  }
})();

/* Expose some dev helpers (in window) */
window.PDFDERS = {
  state,
  saveState: ()=>{ save(state); showToast("Kaydedildi"); },
  addPdfFromDropbox: (link, category, requiredAds=1)=>{
    const url = sanitizeDropboxLink(link);
    const title = inferTitleFromUrl(url);
    const cat = (category && category.trim()) ? category.trim().toUpperCase() : inferCategoryFromTitle(title);
    const pdf = { id: uid(), title, url, category:cat, addedAt:new Date().toISOString(), downloads:0, requiredAds: Math.min(100, Math.max(1, Number(requiredAds))) };
    state.pdfs.push(pdf); save(state);
    return pdf;
  }
};