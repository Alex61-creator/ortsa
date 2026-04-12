/**
 * Личный кабинет: JWT в sessionStorage, REST /api/v1.
 */
(function () {
  var JWT_KEY = "astrogen_jwt";

  function apiBase() {
    var m = document.querySelector('meta[name="api-base"]');
    return m && m.content ? m.content.replace(/\/$/, "") : "/api/v1";
  }

  function getToken() {
    try {
      return sessionStorage.getItem(JWT_KEY);
    } catch (e) {
      return null;
    }
  }

  function setToken(t) {
    try {
      if (t) sessionStorage.setItem(JWT_KEY, t);
      else sessionStorage.removeItem(JWT_KEY);
    } catch (e) {}
  }

  function authHeaders() {
    var t = getToken();
    var h = { "Content-Type": "application/json" };
    if (t) h.Authorization = "Bearer " + t;
    return h;
  }

  async function apiFetch(path, opts) {
    var o = opts || {};
    o.headers = Object.assign({}, authHeaders(), o.headers || {});
    var r = await fetch(apiBase() + path, o);
    return r;
  }

  function isTwaWithInitData() {
    var tg = window.Telegram && window.Telegram.WebApp;
    return !!(tg && tg.initData && String(tg.initData).length > 0);
  }

  function setupLoginTgVisibility() {
    var block = document.getElementById("cabinet-tg-block");
    var sep = document.getElementById("cabinet-tg-sep");
    if (isTwaWithInitData()) {
      if (block) block.classList.remove("auth-nav-hidden");
      if (sep) sep.classList.remove("auth-nav-hidden");
    } else {
      if (block) block.classList.add("auth-nav-hidden");
      if (sep) sep.classList.add("auth-nav-hidden");
    }
  }

  function goOAuth(path) {
    window.location.href = apiBase() + path;
  }

  async function doTwaLogin() {
    var tg = window.Telegram && window.Telegram.WebApp;
    if (!tg || !tg.initData) {
      alert("Откройте приложение из Telegram.");
      return;
    }
    var r = await fetch(apiBase() + "/auth/twa", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ initData: tg.initData }),
    });
    if (!r.ok) {
      alert("Не удалось войти через Telegram.");
      return;
    }
    var data = await r.json();
    if (data.access_token) setToken(data.access_token);
    showCabinet();
    await loadCabinetData();
  }

  function initialsFromEmail(email) {
    if (!email) return "?";
    var local = String(email).split("@")[0] || "";
    return (local.substring(0, 2) || "?").toUpperCase();
  }

  function formatRuDate(iso) {
    if (!iso) return "—";
    try {
      var d = new Date(iso);
      return d.toLocaleDateString("ru-RU", { day: "numeric", month: "short", year: "numeric" });
    } catch (e) {
      return iso;
    }
  }

  function formatMoney(amount) {
    var n = Number(amount);
    if (isNaN(n)) return String(amount);
    return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(n) + " ₽";
  }

  function orderStatusTag(status) {
    var s = String(status || "").toLowerCase();
    if (s === "completed") return '<span class="tag tag-green">Готово</span>';
    if (s === "paid" || s === "processing") return '<span class="tag tag-blue">В работе</span>';
    if (s === "pending") return '<span class="tag tag-amber">Ожидает оплаты</span>';
    return '<span class="tag tag-gray">' + status + "</span>";
  }

  var PANEL_TITLES = {
    dashboard: "Главная",
    orders: "Заказы",
    reports: "Отчёты и PDF",
    natal: "Натальные данные",
    subscription: "Подписка",
    settings: "Настройки",
    support: "Поддержка",
  };

  window.navigate = function (id, btn) {
    document.querySelectorAll(".panel").forEach(function (p) {
      p.classList.remove("active");
    });
    document.querySelectorAll(".nav-item").forEach(function (n) {
      n.classList.remove("active");
    });
    var panel = document.getElementById("panel-" + id);
    if (panel) panel.classList.add("active");
    var title = document.getElementById("topbar-title");
    if (title) title.textContent = PANEL_TITLES[id] || id;
    if (btn) btn.classList.add("active");
    else {
      document.querySelectorAll(".nav-item").forEach(function (n) {
        if (n.textContent.trim().indexOf(PANEL_TITLES[id]) === 0) n.classList.add("active");
      });
    }
    if (window.innerWidth <= 900) {
      var sb = document.getElementById("sidebar");
      if (sb) sb.classList.remove("open");
    }
  };

  window.toggleSidebar = function () {
    var sb = document.getElementById("sidebar");
    if (sb) sb.classList.toggle("open");
  };

  window.toggleTheme = function () {
    var html = document.documentElement;
    var isDark = html.getAttribute("data-theme") === "dark";
    html.setAttribute("data-theme", isDark ? "light" : "dark");
  };

  window.setLang = function (_lang, btn) {
    if (btn && btn.parentElement) {
      btn.parentElement.querySelectorAll(".segment-btn").forEach(function (b) {
        b.classList.remove("on");
      });
      btn.classList.add("on");
    }
  };

  window.setThemeSetting = function (theme, btn) {
    document.documentElement.setAttribute("data-theme", theme);
    if (btn && btn.parentElement) {
      btn.parentElement.querySelectorAll(".segment-btn").forEach(function (b) {
        b.classList.remove("on");
      });
      btn.classList.add("on");
    }
  };

  window.toggleDeliveryField = function () {
    var field = document.getElementById("delivery-field");
    if (!field) return;
    field.classList.toggle("show");
    if (!field.classList.contains("show")) {
      var inp = document.getElementById("delivery-new-email");
      if (inp) inp.value = "";
    }
  };

  window.saveDeliveryEmail = function () {
    var inp = document.getElementById("delivery-new-email");
    var val = inp && inp.value.trim();
    if (!val || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val)) {
      alert("Введите корректный email");
      return;
    }
    var el = document.getElementById("delivery-email-val");
    if (el) el.textContent = val;
    window.toggleDeliveryField();
    alert("Для новых заказов укажите этот email при оформлении. Сохранение в профиль появится в следующих версиях.");
  };

  window.filterOrders = function (_type, btn) {
    document.querySelectorAll(".filter-btn").forEach(function (b) {
      b.classList.remove("on");
    });
    if (btn) btn.classList.add("on");
  };

  window.openModal = function (id) {
    var m = document.getElementById("modal-" + id);
    if (m) m.classList.add("show");
  };

  window.closeModal = function (id) {
    var m = document.getElementById("modal-" + id);
    if (m) m.classList.remove("show");
  };

  window.showCancelConfirm = function () {
    var el = document.getElementById("cancel-confirm");
    if (el) el.classList.add("show");
  };

  window.hideCancelConfirm = function () {
    var el = document.getElementById("cancel-confirm");
    if (el) el.classList.remove("show");
  };

  window.confirmCancel = async function () {
    window.hideCancelConfirm();
    var r = await apiFetch("/subscriptions/me/cancel", { method: "POST" });
    if (!r.ok) {
      alert("Не удалось отменить подписку.");
      return;
    }
    await loadCabinetData();
  };

  window.restoreSub = async function () {
    var r = await apiFetch("/subscriptions/me/resume", { method: "POST" });
    if (!r.ok) {
      var d = await r.json().catch(function () { return {}; });
      alert(d.detail || "Не удалось возобновить подписку.");
      return;
    }
    await loadCabinetData();
  };

  function showLogin() {
    var lp = document.getElementById("login-page");
    var cp = document.getElementById("cabinet-page");
    if (lp) lp.style.display = "flex";
    if (cp) cp.style.display = "none";
  }

  function showCabinet() {
    var lp = document.getElementById("login-page");
    var cp = document.getElementById("cabinet-page");
    if (lp) lp.style.display = "none";
    if (cp) cp.style.display = "block";
    window.navigate("dashboard", null);
  }

  window.logout = function () {
    setToken(null);
    showLogin();
  };

  async function downloadReportPdf(orderId) {
    var r = await fetch(apiBase() + "/reports/" + orderId + "/download", {
      headers: { Authorization: "Bearer " + getToken() },
    });
    if (!r.ok) {
      alert("PDF не найден или ещё готовится.");
      return;
    }
    var blob = await r.blob();
    var u = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = u;
    a.download = "natal_report_" + orderId + ".pdf";
    a.click();
    URL.revokeObjectURL(u);
  }

  window.downloadReportPdf = downloadReportPdf;

  var cache = { orders: [], natal: [], user: null, subscription: null };

  async function loadCabinetData() {
    var meR = await apiFetch("/users/me");
    if (meR.status === 401) {
      setToken(null);
      showLogin();
      return;
    }
    if (!meR.ok) {
      alert("Не удалось загрузить профиль.");
      return;
    }
    cache.user = await meR.json();

    var ordersR = await apiFetch("/orders/");
    cache.orders = ordersR.ok ? await ordersR.json() : [];

    var natalR = await apiFetch("/natal-data/");
    cache.natal = natalR.ok ? await natalR.json() : [];

    var subR = await apiFetch("/subscriptions/me");
    cache.subscription = subR.ok ? await subR.json() : null;

    renderUserSidebar();
    renderDashboard();
    renderOrdersTable();
    renderReports();
    renderNatal();
    renderSubscription();
    renderSettings();
  }

  function renderUserSidebar() {
    var u = cache.user;
    if (!u) return;
    var email = u.email || "";
    var nameEl = document.getElementById("sidebar-name");
    var av = document.getElementById("sidebar-avatar");
    var plan = document.getElementById("sidebar-plan");
    if (nameEl) nameEl.textContent = email.split("@")[0] || "Профиль";
    if (av) av.textContent = initialsFromEmail(email);
    if (plan) {
      if (cache.subscription && cache.subscription.tariff_name) {
        plan.textContent = cache.subscription.tariff_name;
      } else {
        plan.textContent = "Без подписки";
      }
    }
    var nb = document.getElementById("nav-badge-orders");
    if (nb) nb.textContent = String(cache.orders.length);

    var acc = document.getElementById("account-email-display");
    var del = document.getElementById("delete-email");
    var dev = document.getElementById("delivery-email-val");
    if (acc) acc.textContent = email;
    if (del) del.textContent = email;
    if (dev) dev.textContent = email;

    var badge = document.getElementById("provider-badge");
    if (badge) {
      var p = u.oauth_provider || "";
      var labels = {
        google: "Google",
        yandex: "Яндекс",
        apple: "Apple",
        telegram: "Telegram",
      };
      badge.innerHTML = labels[p] || (p || "—");
    }
  }

  function renderDashboard() {
    var natalN = cache.natal.length;
    var pdfN = cache.orders.filter(function (o) {
      return o.report_ready;
    }).length;
    var elN = document.getElementById("dash-natal-count");
    var elP = document.getElementById("dash-pdf-count");
    var elV = document.getElementById("dash-plan-val");
    var elL = document.getElementById("dash-plan-label");
    if (elN) elN.textContent = String(natalN);
    if (elP) elP.textContent = String(pdfN);
    if (cache.subscription) {
      var sub = cache.subscription;
      if (elV) elV.textContent = sub.tariff_name || "Pro";
      if (elL) {
        var end = sub.current_period_end ? formatRuDate(sub.current_period_end) : "—";
        elL.textContent = sub.cancel_at_period_end
          ? "Отмена в конце периода · до " + end
          : "До " + end;
      }
    } else {
      if (elV) elV.textContent = "—";
      if (elL) elL.textContent = "Подписка не подключена";
    }

    var recent = document.getElementById("dash-recent-orders");
    if (!recent) return;
    var list = cache.orders.slice(0, 3);
    if (list.length === 0) {
      recent.innerHTML =
        '<p style="font-size:13px;color:var(--text-3);padding:8px 16px;">Пока нет заказов</p>';
      return;
    }
    recent.innerHTML = list
      .map(function (o) {
        return (
          '<div class="order-mini-card" onclick="navigate(\'orders\',null)">' +
          '<div class="order-mini-icon">📋</div>' +
          '<div class="order-mini-body">' +
          '<div class="order-mini-name">' +
          (o.tariff && o.tariff.name ? o.tariff.name : "Заказ") +
          "</div>" +
          '<div class="order-mini-meta">' +
          formatRuDate(o.created_at) +
          " · " +
          formatMoney(o.amount) +
          "</div></div>" +
          (o.report_ready
            ? '<span class="tag tag-blue">PDF готов</span>'
            : orderStatusTag(o.status)) +
          "</div>"
        );
      })
      .join("");

    var uc = document.querySelector(".upgrade-card .upgrade-title");
    if (uc && cache.subscription) {
      uc.textContent = "Подписка · " + (cache.subscription.tariff_name || "Astro Pro");
    }
  }

  function renderOrdersTable() {
    var tb = document.getElementById("orders-tbody");
    if (!tb) return;
    if (cache.orders.length === 0) {
      tb.innerHTML =
        '<tr><td colspan="5" style="padding:24px;text-align:center;color:var(--text-3);">Нет заказов</td></tr>';
      return;
    }
    tb.innerHTML = cache.orders
      .map(function (o) {
        var actions = "";
        if (o.report_ready) {
          actions =
            '<button type="button" class="btn btn-primary btn-xs" onclick="downloadReportPdf(' +
            o.id +
            ')">PDF</button>';
        } else {
          actions =
            '<button type="button" class="btn btn-default btn-xs" onclick="navigate(\'reports\',null)">Статус</button>';
        }
        return (
          "<tr>" +
          "<td><div class=\"order-name-cell\">" +
          (o.tariff ? o.tariff.name : "Заказ") +
          '</div><div class="order-id">#' +
          o.id +
          "</div></td>" +
          "<td><strong>" +
          formatMoney(o.amount) +
          '</strong><br><span style="font-size:12px;color:var(--text-3);">' +
          (o.tariff ? o.tariff.code : "") +
          "</span></td>" +
          "<td>" +
          formatRuDate(o.created_at) +
          "</td>" +
          "<td>" +
          orderStatusTag(o.status) +
          "</td>" +
          '<td><div class="order-actions">' +
          actions +
          "</div></td></tr>"
        );
      })
      .join("");
  }

  function renderReports() {
    var root = document.getElementById("cabinet-reports-list");
    if (!root) return;
    var ready = cache.orders.filter(function (o) {
      return o.report_ready;
    });
    if (ready.length === 0) {
      root.innerHTML =
        '<p style="color:var(--text-3);font-size:14px;">Нет готовых PDF. Завершите оплату и дождитесь генерации отчёта.</p>';
      return;
    }
    root.innerHTML = ready
      .map(function (o) {
        return (
          '<div class="report-card">' +
          '<div class="report-head">' +
          '<div class="report-icon">☉</div>' +
          '<div class="report-info">' +
          '<div class="report-name">Заказ #' +
          o.id +
          " · " +
          (o.tariff ? o.tariff.name : "Отчёт") +
          "</div>" +
          '<div class="report-meta"><span>' +
          formatRuDate(o.created_at) +
          "</span></div></div>" +
          '<div class="report-actions">' +
          '<button type="button" class="btn btn-primary btn-sm" onclick="downloadReportPdf(' +
          o.id +
          ')">Скачать PDF</button>' +
          "</div></div></div>"
        );
      })
      .join("");
  }

  function renderNatal() {
    var root = document.getElementById("cabinet-natal-root");
    if (!root) return;
    if (cache.natal.length === 0) {
      root.innerHTML =
        '<p style="grid-column:1/-1;color:var(--text-3);">Нет сохранённых натальных данных. Добавьте на лендинге в мастере или здесь (скоро).</p>' +
        '<div class="add-natal-card" onclick="openModal(\'addNatal\')"><svg width="28" height="28" viewBox="0 0 28 28" fill="none"><circle cx="14" cy="14" r="13" stroke="currentColor" stroke-width="1.5"/><line x1="14" y1="8" x2="14" y2="20" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><line x1="8" y1="14" x2="20" y2="14" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>' +
        '<div style="font-size:14px;font-weight:500;">Добавить карту</div><div style="font-size:12px;">Через мастер на главной странице</div></div>';
      return;
    }
    var html = cache.natal
      .map(function (n, i) {
        var bd = n.birth_date ? String(n.birth_date).substring(0, 10) : "—";
        return (
          '<div class="natal-card' +
          (i === 0 ? " active-card" : "") +
          '">' +
          '<div class="natal-card-name">' +
          n.full_name +
          (i === 0 ? ' <span class="tag tag-blue" style="font-size:11px;">Я</span>' : "") +
          "</div>" +
          '<div class="natal-card-row">' +
          bd +
          "</div>" +
          '<div class="natal-card-row">' +
          n.birth_place +
          "</div>" +
          '<div class="natal-card-row">' +
          (n.timezone || "") +
          "</div></div>"
        );
      })
      .join("");
    html +=
      '<div class="add-natal-card" onclick="openModal(\'addNatal\')"><svg width="28" height="28" viewBox="0 0 28 28" fill="none"><circle cx="14" cy="14" r="13" stroke="currentColor" stroke-width="1.5"/><line x1="14" y1="8" x2="14" y2="20" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><line x1="8" y1="14" x2="20" y2="14" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>' +
      '<div style="font-size:14px;font-weight:500;">Добавить карту</div><div style="font-size:12px;">Для близкого человека</div></div>';
    root.innerHTML = html;
  }

  function renderSubscription() {
    var subBlock = document.querySelector(".sub-status-card");
    var noSub = document.getElementById("no-sub-state");
    if (!cache.subscription) {
      if (subBlock) subBlock.style.display = "none";
      if (noSub) noSub.classList.remove("hidden");
      return;
    }
    if (noSub) noSub.classList.add("hidden");
    if (subBlock) subBlock.style.display = "block";

    var sub = cache.subscription;
    var nameEl = document.querySelector(".sub-plan-name");
    if (nameEl) nameEl.textContent = sub.tariff_name || "Подписка";

    var meta = document.querySelector(".sub-meta");
    if (meta) {
      var end = sub.current_period_end ? formatRuDate(sub.current_period_end) : "—";
      meta.innerHTML =
        "<span>💳 " +
        formatMoney(sub.amount) +
        " / месяц</span><span>·</span><span>Период до: <strong>" +
        end +
        "</strong></span>";
      if (sub.cancel_at_period_end) {
        meta.innerHTML +=
          '<span>·</span><span style="color:var(--warning);">Отмена в конце периода</span>';
      }
    }

    var badge = document.querySelector(".sub-status-card .tag");
    if (badge) {
      if (sub.cancel_at_period_end) {
        badge.textContent = "Отменяется";
        badge.className = "tag tag-amber";
      } else {
        badge.textContent = "Активна";
        badge.className = "tag tag-green";
      }
    }

    var actions = document.querySelector(".sub-actions");
    if (actions) {
      if (sub.cancel_at_period_end) {
        actions.innerHTML =
          '<span style="font-size:13px;color:var(--text-3);">Подписка будет остановлена после окончания оплаченного периода.</span>' +
          '<button type="button" class="btn btn-default btn-sm" onclick="restoreSub()">Возобновить</button>';
      } else {
        actions.innerHTML =
          '<button type="button" class="btn btn-danger btn-sm" onclick="showCancelConfirm()">Отменить подписку</button>' +
          '<span style="font-size:12px;color:var(--text-3);">Отмена — в конце текущего периода.</span>';
      }
    }
  }

  function renderSettings() {
    /* export + delete wired below */
  }

  document.addEventListener("DOMContentLoaded", function () {
    setupLoginTgVisibility();

    var g = document.getElementById("cab-login-google");
    var y = document.getElementById("cab-login-yandex");
    var a = document.getElementById("cab-login-apple");
    var t = document.getElementById("cab-login-telegram");
    if (g) g.addEventListener("click", function () { goOAuth("/auth/google/authorize"); });
    if (y) y.addEventListener("click", function () { goOAuth("/auth/yandex/authorize"); });
    if (a) a.addEventListener("click", function () { goOAuth("/auth/apple/authorize"); });
    if (t) t.addEventListener("click", function () { doTwaLogin(); });

    document.querySelectorAll(".modal-overlay").forEach(function (overlay) {
      overlay.addEventListener("click", function (e) {
        if (e.target === overlay) overlay.classList.remove("show");
      });
    });

    var exp = document.getElementById("btn-export-data");
    if (exp) {
      exp.addEventListener("click", async function () {
        var r = await fetch(apiBase() + "/users/me/export", { headers: { Authorization: "Bearer " + getToken() } });
        if (!r.ok) {
          alert("Ошибка выгрузки.");
          return;
        }
        var blob = await r.blob();
        var u = URL.createObjectURL(blob);
        var a = document.createElement("a");
        a.href = u;
        a.download = "user_data_export.json";
        a.click();
        URL.revokeObjectURL(u);
      });
    }

    var delBtn = document.getElementById("btn-confirm-delete-account");
    if (delBtn) {
      delBtn.addEventListener("click", async function () {
        var r = await apiFetch("/users/me", { method: "DELETE" });
        if (r.status === 204) {
          setToken(null);
          window.closeModal("confirmDelete");
          showLogin();
        } else {
          alert("Не удалось удалить аккаунт.");
        }
      });
    }

    if (!getToken()) {
      showLogin();
      return;
    }

    showCabinet();
    loadCabinetData();
  });
})();
