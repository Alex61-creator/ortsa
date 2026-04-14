/**
 * Navbar auth popup: OAuth redirects, optional Telegram (TWA only), nav "Кабинет" when JWT present.
 */
(function () {
  var JWT_KEY = "astrogen_jwt";

  function apiBase() {
    var m = document.querySelector('meta[name="api-base"]');
    return m && m.content ? m.content.replace(/\/$/, "") : "/api/v1";
  }

  function hasJwt() {
    try {
      return !!sessionStorage.getItem(JWT_KEY);
    } catch (e) {
      return false;
    }
  }

  function isTwaWithInitData() {
    var tg = window.Telegram && window.Telegram.WebApp;
    return !!(tg && tg.initData && String(tg.initData).length > 0);
  }

  function updateNavAuth() {
    var openBtn = document.getElementById("nav-open-auth");
    var cabinetLink = document.getElementById("nav-go-cabinet");
    if (!openBtn || !cabinetLink) return;
    if (hasJwt()) {
      openBtn.classList.add("auth-nav-hidden");
      cabinetLink.classList.remove("auth-nav-hidden");
    } else {
      openBtn.classList.remove("auth-nav-hidden");
      cabinetLink.classList.add("auth-nav-hidden");
    }
  }

  function openPopup() {
    var p = document.getElementById("auth-popup-panel");
    var o = document.getElementById("auth-popup-overlay");
    if (p) p.classList.add("open");
    if (o) o.classList.add("open");
  }

  function closePopup() {
    var p = document.getElementById("auth-popup-panel");
    var o = document.getElementById("auth-popup-overlay");
    if (p) p.classList.remove("open");
    if (o) o.classList.remove("open");
  }

  function goOAuth(path) {
    window.location.href = apiBase() + path;
  }

  function tAuth(key, fallbackRu) {
    if (typeof window.tAstrogen === "function") {
      var s = window.tAstrogen(key);
      if (s && s !== key) return s;
    }
    return fallbackRu;
  }

  function setLoading(show, text) {
    var lo = document.getElementById("auth-popup-loading");
    var lt = document.getElementById("auth-popup-loading-text");
    if (lt && text) lt.textContent = text;
    if (lo) lo.classList.toggle("show", !!show);
  }

  var twaSilentLock = false;

  async function trySilentTwaLogin() {
    if (twaSilentLock) return;
    if (!isTwaWithInitData() || hasJwt()) return;
    twaSilentLock = true;
    var tg = window.Telegram && window.Telegram.WebApp;
    try {
      var r = await fetch(apiBase() + "/auth/twa", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ initData: tg.initData }),
      });
      if (!r.ok) throw new Error("auth failed");
      var data = await r.json();
      if (data.access_token) {
        try {
          sessionStorage.setItem(JWT_KEY, data.access_token);
        } catch (e) {}
      }
      updateNavAuth();
      if (typeof window.astrogenUpdateStep3Auth === "function") {
        window.astrogenUpdateStep3Auth();
      }
    } catch (err) {
      console.warn("[astrogen] silent TWA login failed", err);
    }
  }

  window.astrogenTwaLoginSilent = trySilentTwaLogin;

  async function doTwaLogin() {
    var tg = window.Telegram && window.Telegram.WebApp;
    if (!tg || !tg.initData) {
      alert(tAuth("auth_popup_alert_open_tg", "Откройте приложение из Telegram, чтобы войти через Telegram."));
      return;
    }
    setLoading(true, tAuth("auth_popup_loading_telegram", "Вход через Telegram…"));
    try {
      var r = await fetch(apiBase() + "/auth/twa", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ initData: tg.initData }),
      });
      if (!r.ok) throw new Error("auth failed");
      var data = await r.json();
      if (data.access_token) {
        try {
          sessionStorage.setItem(JWT_KEY, data.access_token);
        } catch (e) {}
      }
      closePopup();
      updateNavAuth();
      if (typeof window.astrogenUpdateStep3Auth === "function") {
        window.astrogenUpdateStep3Auth();
      }
      window.location.href = "/dashboard";
    } catch (err) {
      alert(tAuth("auth_popup_alert_tg_fail", "Не удалось войти через Telegram."));
    } finally {
      setLoading(false);
    }
  }

  function setupTgVisibility() {
    var block = document.getElementById("auth-popup-tg-block");
    var div = document.getElementById("auth-popup-browser-divider");
    if (isTwaWithInitData()) {
      if (block) block.classList.remove("auth-nav-hidden");
      if (div) div.classList.remove("auth-nav-hidden");
    } else {
      if (block) block.classList.add("auth-nav-hidden");
      if (div) div.classList.add("auth-nav-hidden");
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    updateNavAuth();
    setupTgVisibility();
    trySilentTwaLogin();

    var openBtn = document.getElementById("nav-open-auth");
    if (openBtn) {
      openBtn.addEventListener("click", function (e) {
        e.preventDefault();
        if (hasJwt()) {
          window.location.href = "/dashboard";
          return;
        }
        openPopup();
      });
    }

    var overlay = document.getElementById("auth-popup-overlay");
    if (overlay) overlay.addEventListener("click", closePopup);

    var closeBtn = document.getElementById("auth-popup-close");
    if (closeBtn) closeBtn.addEventListener("click", closePopup);

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closePopup();
    });

    var g = document.getElementById("auth-popup-oauth-google");
    var y = document.getElementById("auth-popup-oauth-yandex");
    var a = document.getElementById("auth-popup-oauth-apple");
    var tgBtn = document.getElementById("auth-popup-oauth-telegram");
    if (g) g.addEventListener("click", function () { goOAuth("/auth/google/authorize"); });
    if (y) y.addEventListener("click", function () { goOAuth("/auth/yandex/authorize"); });
    if (a) a.addEventListener("click", function () { goOAuth("/auth/apple/authorize"); });
    if (tgBtn) tgBtn.addEventListener("click", function () { doTwaLogin(); });
  });

  window.astrogenUpdateNavAuth = updateNavAuth;
})();
