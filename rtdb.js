/*
  Realtime Database helper for PDF DERSHANEM.
  This file replaces the previous Firestore implementation and uses Firebase Realtime Database.
  Default config is set to the provided project config; pass a different config to initRealtime
  or store it in localStorage under key "pdf_dershanem_rtdb_cfg" to auto-init via autoInitIfConfigured().
*/

const DEFAULT_RTDB_CONFIG = {
  // Provided Firebase configuration
  apiKey: "AIzaSyArNeaPYGiPg-K7O19Xg4btYhqfnzvyCtw",
  authDomain: "pdfdershanem.firebaseapp.com",
  databaseURL: "https://pdfdershanem-default-rtdb.firebaseio.com",
  projectId: "pdfdershanem",
  storageBucket: "pdfdershanem.firebasestorage.app",
  messagingSenderId: "149337981694",
  appId: "1:149337981694:web:87ec729568567f43879baf",
  measurementId: "G-BZB9FD26GT"
};

let ready = false;
let useRemote = false;
let db = null;
let rootRefPath = "pdf_dershanem/state";

/**
 * Initialize Realtime Database.
 * config: firebase config object
 * enable: boolean - only initialize when true
 */
export async function initRealtime(config = DEFAULT_RTDB_CONFIG, enable = false) {
  try {
    if (!enable) return false;
    const { initializeApp } = await import("firebase/app");
    const { getDatabase } = await import("firebase/database");
    const app = initializeApp(config);
    db = getDatabase(app);
    ready = true;
    useRemote = true;
    return true;
  } catch (e) {
    console.warn("Realtime DB init failed:", e);
    ready = false;
    useRemote = false;
    return false;
  }
}

/**
 * Fetch state from Realtime Database path /pdf_dershanem/state
 * returns the state object or null
 */
export async function fetchRemoteState() {
  if (!ready || !useRemote || !db) return null;
  try {
    const { ref, get } = await import("firebase/database");
    const r = ref(db, rootRefPath);
    const snap = await get(r);
    if (!snap.exists()) return null;
    const data = snap.val();
    // expected structure: { state: {...}, updatedAt: "..." } or directly the state
    if (data && data.state) return data.state;
    return data;
  } catch (e) {
    console.warn("fetchRemoteState error", e);
    return null;
  }
}

/**
 * Save state to Realtime Database under /pdf_dershanem/state
 * returns true/false
 */
export async function saveRemoteState(state) {
  if (!ready || !useRemote || !db) return false;
  try {
    const { ref, set } = await import("firebase/database");
    const r = ref(db, rootRefPath);
    await set(r, { state, updatedAt: new Date().toISOString() });
    return true;
  } catch (e) {
    console.warn("saveRemoteState error", e);
    return false;
  }
}

/**
 * Auto-init if a config object is stored in localStorage under key "pdf_dershanem_rtdb_cfg"
 * Expected format: { config: {...}, enabled: true }
 */
export async function autoInitIfConfigured() {
  try {
    const raw = localStorage.getItem("pdf_dershanem_rtdb_cfg");
    if (!raw) return false;
    const cfgObj = JSON.parse(raw);
    if (!cfgObj || !cfgObj.config || !cfgObj.config.projectId) return false;
    const enabled = cfgObj.enabled === true;
    return await initRealtime(cfgObj.config, enabled);
  } catch (e) {
    return false;
  }
}