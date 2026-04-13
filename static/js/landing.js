/* ── API base + Telegram WebApp ── */
(function () {
  const meta = document.querySelector('meta[name="api-base"]');
  window.__API_BASE__ = (meta && meta.content) ? meta.content.replace(/\/$/, '') : '/api/v1';

  function initTelegram() {
    var tg = window.Telegram && window.Telegram.WebApp;
    if (!tg) return;
    tg.ready();
    try { tg.expand(); } catch (e) {}
    document.body.classList.add('tg-webapp');
    if (tg.colorScheme === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
      var tb = document.querySelector('.theme-btn');
      if (tb) tb.textContent = '☾';
    }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTelegram);
  } else {
    initTelegram();
  }

  function authHeaders() {
    var t = null;
    try { t = sessionStorage.getItem('astrogen_jwt'); } catch (e) {}
    var h = { 'Content-Type': 'application/json' };
    if (t) h['Authorization'] = 'Bearer ' + t;
    return h;
  }
  window.astrogenAuthHeaders = authHeaders;

  document.addEventListener('DOMContentLoaded', function () {
    var prefLang = null;
    try {
      prefLang = localStorage.getItem('astrogen_lang');
      if (prefLang === 'en' || prefLang === 'ru') {
        document.documentElement.setAttribute('lang', prefLang === 'en' ? 'en' : 'ru');
      }
    } catch (eLang0) {}

    if (typeof initAstrogenTariffFromUrl === 'function') initAstrogenTariffFromUrl();

    if ((prefLang === 'en' || prefLang === 'ru') && typeof applyAstrogenLandingLang === 'function') {
      applyAstrogenLandingLang(prefLang, function () {
        document.querySelectorAll('.lang-btn').forEach(function (b) {
          b.classList.remove('active');
        });
        var langBtn = document.querySelector('.lang-btn[onclick="setLang(\'' + prefLang + '\')"]');
        if (langBtn) langBtn.classList.add('active');
        if (typeof applyAstrogenTariffPrices === 'function') applyAstrogenTariffPrices();
        if (typeof refreshWizardStep3Copy === 'function') refreshWizardStep3Copy();
        if (typeof refreshWizardStep2Copy === 'function') refreshWizardStep2Copy();
      });
    }

    var base = window.__API_BASE__;
    function goOAuth(path) {
      window.location.href = base + path;
    }
    var g = document.getElementById('oauth-google');
    var y = document.getElementById('oauth-yandex');
    var a = document.getElementById('oauth-apple');
    if (g) g.addEventListener('click', function (e) { e.preventDefault(); goOAuth('/auth/google/authorize'); });
    if (y) y.addEventListener('click', function (e) { e.preventDefault(); goOAuth('/auth/yandex/authorize'); });
    if (a) a.addEventListener('click', function (e) { e.preventDefault(); goOAuth('/auth/apple/authorize'); });

    var twa = document.getElementById('btn-twa-auth');
    if (twa) {
      twa.addEventListener('click', async function (e) {
        e.preventDefault();
        var tg = window.Telegram && window.Telegram.WebApp;
        if (!tg || !tg.initData) {
          alert(typeof tAstrogen === 'function' ? tAstrogen('alert_tg') : 'Откройте мини-приложение из Telegram');
          return;
        }
        try {
          var r = await fetch(base + '/auth/twa', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ initData: tg.initData }),
          });
          if (!r.ok) throw new Error('auth failed');
          var data = await r.json();
          if (data.access_token) sessionStorage.setItem('astrogen_jwt', data.access_token);
          if (typeof updateStep3AuthUI === 'function') updateStep3AuthUI();
        } catch (err) {
          var ae = document.getElementById('auth-inline-error');
          var msg = typeof tAstrogen === 'function' ? tAstrogen('alert_tg_fail') : 'Не удалось войти через Telegram';
          if (ae) {
            ae.textContent = msg;
            ae.classList.add('show');
          } else {
            alert(msg);
          }
        }
      });
    }

    var logoutBtn = document.getElementById('auth-logout-btn');
    if (logoutBtn) {
      logoutBtn.addEventListener('click', function (e) {
        e.preventDefault();
        try { sessionStorage.removeItem('astrogen_jwt'); } catch (err) {}
        if (typeof updateStep3AuthUI === 'function') updateStep3AuthUI();
      });
    }

    fetch(base + '/tariffs/', { headers: { Accept: 'application/json' } })
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (tariffs) {
        if (!tariffs || !tariffs.length) return;
        var byCode = {};
        tariffs.forEach(function (t) { byCode[t.code] = t; });
        window.__astrogenTariffsByCode = byCode;
        if (typeof applyAstrogenTariffPrices === 'function') applyAstrogenTariffPrices();
        if (typeof refreshWizardStep3Copy === 'function') refreshWizardStep3Copy();
      })
      .catch(function () {});

    var placeInput = document.getElementById('f-place');
    var geocodeTimer = null;
    function runGeocode() {
      var q = (placeInput && placeInput.value || '').trim();
      if (q.length < 2) return;
      fetch(base + '/geocode/?q=' + encodeURIComponent(q), { headers: { Accept: 'application/json' } })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (data) {
          if (!data) return;
          window.__geocodeResult = data;
        })
        .catch(function () {});
    }
    if (placeInput) {
      placeInput.addEventListener('blur', function () {
        clearTimeout(geocodeTimer);
        geocodeTimer = setTimeout(runGeocode, 400);
      });
    }

    if (typeof astrogenBirthDateLocaleInit === 'function') {
      astrogenBirthDateLocaleInit({
        onCommit: function () {
          var h = document.getElementById('f-date');
          if (h) validateAndSaveBirthDate(h, 'select');
        }
      });
    }

    var timeInput = document.getElementById('f-time');
    if (timeInput) {
      timeInput.addEventListener('change', function () { validateAndSaveTime(timeInput); });
      timeInput.addEventListener('blur', function () { validateAndSaveTime(timeInput); });
      validateAndSaveTime(timeInput);
    }

    var cta = document.getElementById('step3-cta');
    if (cta) {
      cta.addEventListener('click', async function (e) {
        e.preventDefault();
        var actErr = document.getElementById('step3-action-error');
        function showAct(msg) {
          if (actErr) {
            actErr.textContent = msg;
            actErr.style.display = '';
          } else {
            alert(msg);
          }
        }
        function clearAct() {
          if (actErr) {
            actErr.style.display = 'none';
            actErr.textContent = '';
          }
        }
        clearAct();
        var token = null;
        try { token = sessionStorage.getItem('astrogen_jwt'); } catch (err) {}
        if (!token) {
          showAct(typeof tAstrogen === 'function' ? tAstrogen('alert_oauth') : 'Сначала войдите (Telegram, Google, Яндекс или Apple).');
          return;
        }
        var altWrap = document.getElementById('report-email-alt-wrap');
        var altInput = document.getElementById('report-email-alt-input');
        var altErr = document.getElementById('report-email-alt-error');
        if (altWrap && altWrap.classList.contains('show') && altInput) {
          var av = altInput.value.trim();
          if (!av || !astrogenIsValidEmail(av)) {
            if (altErr) {
              altErr.textContent = typeof tAstrogen === 'function' ? tAstrogen('err_email_invalid') : 'Введите корректный email';
              altErr.classList.add('show');
            }
            if (altInput) altInput.classList.add('field-error-input');
            return;
          }
          if (altErr) altErr.classList.remove('show');
          if (altInput) altInput.classList.remove('field-error-input');
        }
        var gc = window.__geocodeResult;
        if (!gc || gc.lat == null) {
          showAct(typeof tAstrogen === 'function' ? tAstrogen('alert_geo') : 'Укажите место рождения и подождите определения координат (кликните вне поля города).');
          return;
        }
        var name = (document.getElementById('f-name') && document.getElementById('f-name').value || '').trim();
        if (typeof astrogenBirthDateLocaleCommitFromParts === 'function') {
          astrogenBirthDateLocaleCommitFromParts();
        }
        var dateEl = document.getElementById('f-date');
        var dateStr = dateEl && validateAndSaveBirthDate(dateEl, 'cta');
        var timeEl = document.getElementById('f-time');
        var timeStr = timeEl && validateAndSaveTime(timeEl);
        if (!name || !dateStr) {
          showAct(typeof tAstrogen === 'function' ? tAstrogen('alert_name_date') : 'Заполните имя и дату рождения.');
          return;
        }
        if (!timeStr) timeStr = '12:00';
        var bd = dateStr + 'T00:00:00';
        var bt = dateStr + 'T' + (timeStr.length === 5 ? timeStr + ':00' : timeStr);
        var tariffCode = (window.formData && window.formData.tariff) || 'report';
        var reportLocale = 'ru';
        try {
          var storedLoc = localStorage.getItem('astrogen_lang');
          if (storedLoc === 'en' || storedLoc === 'ru') reportLocale = storedLoc;
          else if (typeof getAstrogenLang === 'function') reportLocale = getAstrogenLang();
        } catch (eLang) {}
        if (reportLocale !== 'en' && reportLocale !== 'ru') reportLocale = 'ru';
        var body = {
          full_name: name,
          birth_date: bd,
          birth_time: bt,
          birth_place: (placeInput && placeInput.value || '').trim() || gc.display_name,
          lat: gc.lat,
          lon: gc.lon,
          timezone: gc.timezone,
          accept_privacy_policy: true,
          report_locale: reportLocale,
        };
        cta.disabled = true;
        try {
          var nr = await fetch(base + '/natal-data/', { method: 'POST', headers: authHeaders(), body: JSON.stringify(body) });
          if (!nr.ok) {
            var errText = await nr.text();
            throw new Error(errText || 'natal-data error');
          }
          var natal = await nr.json();
          var orderPayload = { tariff_code: tariffCode, natal_data_id: natal.id };
          var isPaidTariff = tariffCode !== 'free';
          var accEl = document.getElementById('report-email-account');
          if (isPaidTariff) {
            if (altWrap && altWrap.classList.contains('show') && altInput && altInput.value.trim()) {
              orderPayload.report_delivery_email = altInput.value.trim();
            } else if (
              accEl &&
              window.__astrogenStep3UserEmail &&
              accEl.textContent.trim() &&
              accEl.textContent.trim() !== window.__astrogenStep3UserEmail
            ) {
              orderPayload.report_delivery_email = accEl.textContent.trim();
            }
          }
          var orr = await fetch(base + '/orders/', {
            method: 'POST',
            headers: authHeaders(),
            body: JSON.stringify(orderPayload),
          });
          if (!orr.ok) throw new Error('order error');
          var order = await orr.json();
          if (order.confirmation_url) {
            if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.openLink) {
              window.Telegram.WebApp.openLink(order.confirmation_url, { try_instant_view: false });
            } else {
              window.location.href = order.confirmation_url;
            }
          } else {
            showAct(typeof tAstrogen === 'function' ? tAstrogen('alert_order_ok') : 'Заказ создан. Отчёт будет готов в ближайшее время — проверьте почту или личный кабинет.');
          }
        } catch (err) {
          showAct((typeof tAstrogen === 'function' ? tAstrogen('alert_err') : 'Ошибка:') + ' ' + (err && err.message ? err.message : 'запрос'));
        } finally {
          if (typeof updateStep3AuthUI === 'function') updateStep3AuthUI();
          else { cta.disabled = false; }
        }
      });
    }

    var btnAlt = document.getElementById('btn-toggle-alt-email');
    var altWrapEl = document.getElementById('report-email-alt-wrap');
    var altInp = document.getElementById('report-email-alt-input');
    if (btnAlt && altWrapEl) {
      btnAlt.addEventListener('click', function () {
        var hidden = !altWrapEl.classList.contains('show');
        if (hidden) {
          altWrapEl.classList.add('show');
          if (typeof tAstrogen === 'function') btnAlt.textContent = tAstrogen('report_email_back_btn');
          if (altInp) setTimeout(function () { altInp.focus(); }, 10);
        } else {
          altWrapEl.classList.remove('show');
          if (altInp) altInp.value = '';
          var ae = document.getElementById('report-email-alt-error');
          if (ae) { ae.classList.remove('show'); ae.textContent = ''; }
          if (altInp) altInp.classList.remove('field-error-input');
          if (typeof tAstrogen === 'function') btnAlt.textContent = tAstrogen('report_email_other_btn');
        }
        if (typeof refreshStep3PayButtonState === 'function') refreshStep3PayButtonState();
      });
    }
    var btnAltApply = document.getElementById('btn-alt-email-apply');
    var btnAltCancel = document.getElementById('btn-alt-email-cancel');
    if (btnAltApply && altInp && altWrapEl) {
      btnAltApply.addEventListener('click', function () {
        var errEl = document.getElementById('report-email-alt-error');
        var accEl = document.getElementById('report-email-account');
        var v = altInp.value.trim();
        if (!v || !astrogenIsValidEmail(v)) {
          if (errEl) {
            errEl.textContent = typeof tAstrogen === 'function' ? tAstrogen('err_email_invalid') : 'Введите корректный email';
            errEl.classList.add('show');
          }
          altInp.classList.add('field-error-input');
          return;
        }
        altInp.classList.remove('field-error-input');
        if (errEl) { errEl.classList.remove('show'); errEl.textContent = ''; }
        if (accEl) accEl.textContent = v;
        altWrapEl.classList.remove('show');
        if (btnAlt && typeof tAstrogen === 'function') btnAlt.textContent = tAstrogen('report_email_change_btn');
        if (typeof refreshStep3PayButtonState === 'function') refreshStep3PayButtonState();
      });
    }
    if (btnAltCancel && altWrapEl && altInp && btnAlt) {
      btnAltCancel.addEventListener('click', function () {
        altWrapEl.classList.remove('show');
        altInp.value = '';
        altInp.classList.remove('field-error-input');
        var ae = document.getElementById('report-email-alt-error');
        if (ae) { ae.classList.remove('show'); ae.textContent = ''; }
        if (typeof tAstrogen === 'function') btnAlt.textContent = tAstrogen('report_email_other_btn');
        if (typeof refreshStep3PayButtonState === 'function') refreshStep3PayButtonState();
      });
    }
    if (altInp) {
      altInp.addEventListener('input', function () {
        var ae = document.getElementById('report-email-alt-error');
        if (ae) { ae.classList.remove('show'); ae.textContent = ''; }
        altInp.classList.remove('field-error-input');
        if (typeof refreshStep3PayButtonState === 'function') refreshStep3PayButtonState();
      });
    }

    if (typeof updateStep3AuthUI === 'function') updateStep3AuthUI();

    try {
      var saved = JSON.parse(localStorage.getItem('astrogen_form') || '{}');
      if (saved.name) { var n = document.getElementById('f-name'); if (n) n.value = saved.name; }
      if (saved.date) { var h = document.getElementById('f-date'); if (h) h.value = saved.date; }
      if (saved.time) { var t = document.getElementById('f-time'); if (t) t.value = saved.time; }
      if (saved.place) { var p = document.getElementById('f-place'); if (p) p.value = saved.place; }
      if (
        saved.tariff &&
        typeof astrogenValidTariffCode === 'function' &&
        astrogenValidTariffCode(saved.tariff) &&
        !window.__astrogenTariffFromPricing
      ) {
        formData.tariff = saved.tariff;
        if (typeof applyWizardTariffSelection === 'function') applyWizardTariffSelection(saved.tariff);
      }
    } catch (e1) {}
    if (typeof astrogenBirthDateLocaleSyncFromHidden === 'function') astrogenBirthDateLocaleSyncFromHidden();
    var fh = document.getElementById('f-date');
    if (fh && fh.value) validateAndSaveBirthDate(fh, 'restore');

    if (typeof refreshWizardStep2Copy === 'function') refreshWizardStep2Copy();
  });
})();

/* ── Scroll animations ── */
const observer = new IntersectionObserver((entries) => {
  entries.forEach(el => {
    if (el.isIntersecting) { el.target.classList.add('visible'); observer.unobserve(el.target); }
  });
}, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
document.querySelectorAll('.fade-up').forEach(el => observer.observe(el));

/* ── Animated counters ── */
function animateCounter(el) {
  const target = parseFloat(el.dataset.target);
  const suffix = el.dataset.suffix || '';
  const decimal = parseInt(el.dataset.decimal || '0');
  const duration = 1800;
  const start = performance.now();
  function step(now) {
    const p = Math.min((now - start) / duration, 1);
    const ease = 1 - Math.pow(1 - p, 3);
    const val = target * ease;
    el.textContent = (decimal > 0 ? val.toFixed(decimal) : Math.round(val)) + suffix;
    if (p < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}
const counterObserver = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      animateCounter(e.target);
      counterObserver.unobserve(e.target);
    }
  });
}, { threshold: 0.5 });
document.querySelectorAll('[data-target]').forEach(el => counterObserver.observe(el));

/* ── Hero chart interactivity (pause on hover) ── */
const hc = document.getElementById('heroChart');
if (hc) {
  hc.addEventListener('mouseenter', () => hc.style.animationPlayState = 'paused');
  hc.addEventListener('mouseleave', () => hc.style.animationPlayState = 'running');
  hc.addEventListener('touchstart', () => {
    hc.style.animationPlayState = hc.style.animationPlayState === 'paused' ? 'running' : 'paused';
  }, { passive: true });
}

/* ── Add fade-up to section headings and cards automatically ── */
document.querySelectorAll('.feature-card, .forwho-card, .review-card, .pricing-card, .house-card').forEach((el, i) => {
  if (!el.classList.contains('fade-up')) {
    el.classList.add('fade-up');
    el.style.setProperty('--delay', (i % 3) * 0.1 + 's');
    observer.observe(el);
  }
});
window.formData = window.formData || {};
var formData = window.formData;
function saveField(k,v){ formData[k]=v; try{localStorage.setItem('astrogen_form',JSON.stringify(formData));}catch(e){} }

var BIRTH_DATE_MIN = '1800-01-01';

function todayIsoDate() {
  var d = new Date();
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}

function validateAndSaveBirthDate(el, dbgReason) {
  if (!el) return '';
  if (el.type !== 'hidden') {
    el.max = todayIsoDate();
    el.min = BIRTH_DATE_MIN;
  }
  var v = el.value;
  function clearAndSync() {
    el.value = '';
    saveField('date', '');
    if (typeof astrogenBirthDateLocaleSyncFromHidden === 'function') astrogenBirthDateLocaleSyncFromHidden();
  }
  if (!v) {
    saveField('date', '');
    return '';
  }
  if (!/^\d{4}-\d{2}-\d{2}$/.test(v)) {
    clearAndSync();
    return '';
  }
  var y = parseInt(v.slice(0, 4), 10);
  var mo = parseInt(v.slice(5, 7), 10);
  var da = parseInt(v.slice(8, 10), 10);
  if (v.slice(0, 4).length !== 4 || y < 1800) {
    clearAndSync();
    return '';
  }
  var dt = new Date(y, mo - 1, da);
  if (dt.getFullYear() !== y || dt.getMonth() !== mo - 1 || dt.getDate() !== da) {
    clearAndSync();
    return '';
  }
  var maxD = todayIsoDate();
  if (v > maxD) {
    v = maxD;
    el.value = v;
    if (typeof astrogenBirthDateLocaleSyncFromHidden === 'function') astrogenBirthDateLocaleSyncFromHidden();
  }
  if (v < BIRTH_DATE_MIN) {
    v = BIRTH_DATE_MIN;
    el.value = v;
    if (typeof astrogenBirthDateLocaleSyncFromHidden === 'function') astrogenBirthDateLocaleSyncFromHidden();
  }
  saveField('date', v);
  return v;
}

function validateAndSaveTime(el) {
  if (!el) return '';
  var v = (el.value || '').trim();
  if (!v) {
    saveField('time', '');
    return '';
  }
  var parts = v.split(':');
  if (parts.length < 2) {
    el.value = '';
    saveField('time', '');
    return '';
  }
  var h = parseInt(parts[0], 10);
  var m = parseInt(parts[1], 10);
  var sec = parts[2] !== undefined && String(parts[2]).length ? parseInt(parts[2], 10) : null;
  if (isNaN(h) || isNaN(m)) {
    el.value = '';
    saveField('time', '');
    return '';
  }
  if (h < 0 || h > 23 || m < 0 || m > 59) {
    el.value = '';
    saveField('time', '');
    return '';
  }
  if (sec !== null && (isNaN(sec) || sec < 0 || sec > 59)) {
    el.value = '';
    saveField('time', '');
    return '';
  }
  var out = String(h).padStart(2, '0') + ':' + String(m).padStart(2, '0');
  if (sec !== null) out += ':' + String(sec).padStart(2, '0');
  el.value = out;
  saveField('time', out);
  return out;
}

function astrogenIsValidEmail(s) {
  if (!s || typeof s !== 'string') return false;
  var t = s.trim();
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(t);
}

/**
 * Кнопка шага 3: учёт «другой почты» для оплаты (платный тариф).
 */
function refreshStep3PayButtonState() {
  var cta = document.getElementById('step3-cta');
  if (!cta) return;
  var tariff = (window.formData && window.formData.tariff) || 'report';
  var isFree = tariff === 'free';
  var isPaid = !isFree;
  var token = null;
  try { token = sessionStorage.getItem('astrogen_jwt'); } catch (e) {}
  if (!token || !isPaid) return;

  var altWrap = document.getElementById('report-email-alt-wrap');
  var altInput = document.getElementById('report-email-alt-input');
  if (!altWrap || !altWrap.classList.contains('show')) return;
  var v = altInput && altInput.value.trim() || '';
  if (!v || !astrogenIsValidEmail(v)) {
    cta.disabled = true;
    cta.setAttribute('aria-disabled', 'true');
    cta.classList.add('step3-cta--locked');
  } else {
    cta.disabled = false;
    cta.removeAttribute('aria-disabled');
    cta.classList.remove('step3-cta--locked');
  }
}

/**
 * Сводка заказа и плашка тарифа на шаге 3 (цены из API).
 */
function refreshStep3OrderSummary() {
  var code = (window.formData && window.formData.tariff) || 'report';
  var by = window.__astrogenTariffsByCode;
  var lang = typeof getAstrogenLang === 'function' ? getAstrogenLang() : 'ru';
  var en = lang === 'en';
  var tFn = typeof tAstrogen === 'function' ? tAstrogen : function (k) { return k; };
  var product = document.getElementById('step3-summary-product');
  var linePrice = document.getElementById('step3-summary-line-price');
  var totalEl = document.getElementById('step3-summary-total');
  var pill = document.getElementById('step3-tariff-pill-text');
  var accessVal = document.getElementById('step3-summary-access-val');
  var keys = {
    report: { prod: 'step3_summary_product_report', access: 'step3_summary_forever', pill: 'wt_report' },
    bundle: { prod: 'step3_summary_product_bundle', access: 'step3_summary_access_bundle', pill: 'wt_bundle' },
    pro: { prod: 'step3_summary_product_pro', access: 'step3_summary_access_pro', pill: 'wt_pro' },
    free: { prod: 'step3_summary_product_free', access: 'step3_summary_access_free', pill: 'wt_free' },
  };
  var k = keys[code] || keys.report;
  if (product) product.textContent = tFn(k.prod);
  if (accessVal) accessVal.textContent = tFn(k.access);
  if (pill) pill.textContent = tFn(k.pill);
  if (!by || !by[code]) return;
  var t = by[code];
  if (en) {
    if (code === 'pro') {
      if (linePrice) linePrice.textContent = '$' + astrogenFmtUsd(t.price_usd) + ' / mo';
      if (totalEl) totalEl.textContent = '$' + astrogenFmtUsd(t.price_usd) + '/mo';
    } else {
      if (linePrice) linePrice.textContent = '$' + astrogenFmtUsd(t.price_usd);
      if (totalEl) totalEl.textContent = '$' + astrogenFmtUsd(t.price_usd);
    }
  } else {
    if (code === 'pro') {
      if (linePrice) linePrice.textContent = astrogenFmtRub(t.price) + ' ₽ / мес';
      if (totalEl) totalEl.textContent = astrogenFmtRub(t.price) + ' ₽ / мес';
    } else {
      if (linePrice) linePrice.textContent = astrogenFmtRub(t.price) + ' ₽';
      if (totalEl) totalEl.textContent = astrogenFmtRub(t.price) + ' ₽';
    }
  }
}
window.refreshStep3OrderSummary = refreshStep3OrderSummary;

/**
 * Шаг 3: 3A вход + 3B оплата; после /users/me — компактный статус и активная зона оплаты.
 */
async function updateStep3AuthUI() {
  var base = window.__API_BASE__ || '/api/v1';
  var pending = document.getElementById('auth-panel-pending');
  var done = document.getElementById('auth-panel-done');
  var emailEl = document.getElementById('auth-logged-email');
  var cta = document.getElementById('step3-cta');
  var hint = document.getElementById('step3-cta-hint');
  var freeNote = document.getElementById('auth-free-note');
  var emailBlock = document.getElementById('auth-email-block');
  var paidFlow = document.getElementById('step3-paid-flow');
  var payBlock = document.getElementById('step3-pay-block');
  var lockNotice = document.getElementById('lock-notice');
  var altSection = document.getElementById('step3-alt-email-section');
  var secWrap = document.getElementById('step3-security-wrap');
  var reportAcc = document.getElementById('report-email-account');
  var numA = document.getElementById('substep-num-a');
  var titleA = document.getElementById('substep-title-a');
  var numB = document.getElementById('substep-num-b');
  var titleB = document.getElementById('substep-title-b');
  var descB = document.getElementById('substep-desc-b');
  var tariff = (window.formData && window.formData.tariff) || 'report';
  var isFree = tariff === 'free';
  var isPaid = !isFree;
  var tFn = typeof tAstrogen === 'function' ? tAstrogen : function (k) { return k; };

  function setCtaLocked(locked) {
    if (!cta) return;
    if (locked) {
      cta.disabled = true;
      cta.setAttribute('aria-disabled', 'true');
      cta.classList.add('step3-cta--locked');
      if (hint) {
        if (isPaid) hint.style.display = '';
        else hint.style.display = 'none';
      }
    } else {
      cta.disabled = false;
      cta.removeAttribute('aria-disabled');
      cta.classList.remove('step3-cta--locked');
      if (hint) hint.style.display = 'none';
    }
  }

  function showFreeExtras() {
    if (freeNote && isFree) freeNote.style.display = 'block';
    if (emailBlock && isFree) emailBlock.style.display = 'block';
  }

  function hideFreeExtras() {
    if (freeNote) freeNote.style.display = 'none';
    if (emailBlock) emailBlock.style.display = 'none';
  }

  function resetAltEmailUi() {
    var aw = document.getElementById('report-email-alt-wrap');
    var ai = document.getElementById('report-email-alt-input');
    var ba = document.getElementById('btn-toggle-alt-email');
    var rae = document.getElementById('report-email-alt-error');
    if (aw) aw.classList.remove('show');
    if (ai) {
      ai.value = '';
      ai.classList.remove('field-error-input');
    }
    if (rae) {
      rae.classList.remove('show');
      rae.textContent = '';
    }
    if (ba) ba.textContent = tFn('report_email_other_btn');
  }

  function applySubstepAuth(loggedIn) {
    if (titleA) {
      var ak = loggedIn ? 'step3a_title_done' : 'step3a_title_pending';
      titleA.setAttribute('data-i18n', ak);
      titleA.textContent = tFn(ak);
    }
    if (numA) numA.classList.toggle('done-num', !!loggedIn);
    if (!isPaid || !numB || !titleB || !descB) return;
    if (loggedIn) {
      numB.classList.remove('muted-num');
      titleB.classList.remove('muted');
      descB.classList.remove('substep-desc--muted');
      descB.setAttribute('data-i18n', 'step3b_sub_active');
      descB.textContent = tFn('step3b_sub_active');
    } else {
      numB.classList.add('muted-num');
      titleB.classList.add('muted');
      descB.classList.add('substep-desc--muted');
      descB.setAttribute('data-i18n', 'step3b_sub_locked');
      descB.textContent = tFn('step3b_sub_locked');
    }
  }

  function setPayZoneLocked(locked) {
    if (payBlock) payBlock.classList.toggle('locked', !!locked);
    if (lockNotice) lockNotice.classList.toggle('show', !!locked);
    if (altSection) altSection.style.display = isPaid && !locked ? 'block' : 'none';
  }

  if (paidFlow) paidFlow.style.display = isPaid ? 'block' : 'none';

  var token = null;
  try { token = sessionStorage.getItem('astrogen_jwt'); } catch (e) {}

  if (!token) {
    window.__astrogenStep3UserEmail = '';
    if (pending) {
      pending.classList.remove('hidden');
    }
    if (done) done.classList.remove('show');
    if (emailEl) emailEl.textContent = '';
    if (reportAcc) reportAcc.textContent = '';
    resetAltEmailUi();
    applySubstepAuth(false);
    if (isPaid) {
      setPayZoneLocked(true);
    } else {
      setPayZoneLocked(false);
    }
    if (secWrap) {
      if (isPaid) secWrap.classList.add('form-security--hidden');
      else secWrap.classList.remove('form-security--hidden');
    }
    setCtaLocked(true);
    showFreeExtras();
    if (typeof refreshStep3OrderSummary === 'function') refreshStep3OrderSummary();
    return;
  }

  try {
    var r = await fetch(base + '/users/me', {
      headers: { Authorization: 'Bearer ' + token, Accept: 'application/json' },
    });
    if (!r.ok) throw new Error('unauthorized');
    var user = await r.json();
    var uemail = user.email || '';
    var prevStored = window.__astrogenStep3UserEmail;
    window.__astrogenStep3UserEmail = uemail;
    if (pending) pending.classList.add('hidden');
    if (done) done.classList.add('show');
    var inlineErr = document.getElementById('auth-inline-error');
    if (inlineErr) {
      inlineErr.classList.remove('show');
      inlineErr.textContent = '';
    }
    if (emailEl) emailEl.textContent = uemail;
    if (reportAcc) {
      var curAcc = reportAcc.textContent.trim();
      if (!curAcc || curAcc === '—' || (prevStored && curAcc === prevStored)) {
        reportAcc.textContent = uemail || '—';
      }
    }
    applySubstepAuth(true);
    if (isPaid) {
      setPayZoneLocked(false);
    } else {
      setPayZoneLocked(false);
    }
    if (secWrap) secWrap.classList.remove('form-security--hidden');
    setCtaLocked(false);
    hideFreeExtras();
    refreshStep3PayButtonState();
    if (typeof refreshStep3OrderSummary === 'function') refreshStep3OrderSummary();
  } catch (e) {
    try { sessionStorage.removeItem('astrogen_jwt'); } catch (e2) {}
    window.__astrogenStep3UserEmail = '';
    if (pending) pending.classList.remove('hidden');
    if (done) done.classList.remove('show');
    if (emailEl) emailEl.textContent = '';
    if (reportAcc) reportAcc.textContent = '';
    resetAltEmailUi();
    applySubstepAuth(false);
    if (isPaid) {
      setPayZoneLocked(true);
    }
    if (secWrap) {
      if (isPaid) secWrap.classList.add('form-security--hidden');
      else secWrap.classList.remove('form-security--hidden');
    }
    setCtaLocked(true);
    showFreeExtras();
    if (typeof refreshStep3OrderSummary === 'function') refreshStep3OrderSummary();
  }
}
window.refreshStep3PayButtonState = refreshStep3PayButtonState;

window.astrogenUpdateStep3Auth = updateStep3AuthUI;

function astrogenValidTariffCode(code) {
  return code === 'free' || code === 'report' || code === 'bundle' || code === 'pro';
}

function applyWizardTariffSelection(code) {
  if (!astrogenValidTariffCode(code)) return;
  formData.tariff = code;
  saveField('tariff', code);
  document.querySelectorAll('.wizard-tariff').forEach(function (t) {
    t.classList.toggle('selected', t.getAttribute('data-tariff') === code);
  });
}
window.applyWizardTariffSelection = applyWizardTariffSelection;

function refreshWizardStep2Copy() {
  var fromPricing = !!window.__astrogenTariffFromPricing;
  var tFn = typeof tAstrogen === 'function' ? tAstrogen : function (k, v) { return k; };
  var labelL2 = document.querySelector('.wizard-step[data-step="2"] .wizard-step-label');
  var titleS2 = document.querySelector('#step2 .wizard-panel-title');
  if (labelL2) labelL2.textContent = tFn(fromPricing ? 'wiz_l2_confirm' : 'wiz_l2');
  if (titleS2) titleS2.textContent = tFn(fromPricing ? 'wiz_s2t_confirm' : 'wiz_s2t');
  var step2 = document.getElementById('step2');
  var greeting = document.getElementById('step2-greeting');
  var nameEl = document.getElementById('f-name');
  var name = nameEl ? nameEl.value.trim() : '';
  if (greeting && step2 && step2.classList.contains('active') && name) {
    greeting.textContent = tFn(fromPricing ? 'wizard_greeting_confirm' : 'wizard_greeting', { name: name });
  } else if (greeting && step2 && !step2.classList.contains('active')) {
    greeting.textContent = tFn('wiz_s2sub_default');
  }
}
window.refreshWizardStep2Copy = refreshWizardStep2Copy;

/** После применения ?tariff= из ссылки убираем параметр (и якорь #form), чтобы в адресной строке остался «чистый» URL. */
function astrogenCleanTariffFromAddressBar() {
  try {
    var u = new URL(window.location.href);
    if (!u.searchParams.has('tariff')) return;
    u.searchParams.delete('tariff');
    var search = u.searchParams.toString();
    var hash = u.hash;
    if (hash === '#form' || hash === '#') hash = '';
    var path = u.pathname + (search ? '?' + search : '') + hash;
    if (window.history && typeof window.history.replaceState === 'function') {
      window.history.replaceState(null, '', path);
    }
  } catch (e) {}
}

function initAstrogenTariffFromUrl() {
  try {
    var params = new URLSearchParams(window.location.search);
    var raw = (params.get('tariff') || '').toLowerCase().trim();
    if (!astrogenValidTariffCode(raw)) return;
    window.__astrogenTariffFromPricing = true;
    applyWizardTariffSelection(raw);
    astrogenCleanTariffFromAddressBar();
  } catch (e) {}
}
window.initAstrogenTariffFromUrl = initAstrogenTariffFromUrl;

/** Проверка шага 1 для перехода на 2 или 3 (имя, дата, место). */
function step1InputsValid() {
  if (typeof astrogenBirthDateLocaleCommitFromParts === 'function') {
    astrogenBirthDateLocaleCommitFromParts();
  }
  var dateEl = document.getElementById('f-date');
  var date = dateEl && validateAndSaveBirthDate(dateEl, 'goStep');
  var name = (document.getElementById('f-name') && document.getElementById('f-name').value || '').trim();
  var place = (document.getElementById('f-place') && document.getElementById('f-place').value || '').trim();
  return !!(name && date && place);
}

/**
 * Переход по клику на индикатор шага в шапке визарда.
 */
function tryNavigateWizardStep(n) {
  if (n === 1) {
    goStep(1);
    return;
  }
  if (n === 2) {
    goStep(2);
    return;
  }
  if (n === 3) {
    if (!step1InputsValid()) {
      var err = document.getElementById('step1-error');
      if (err) err.style.display = 'block';
      goStep(1);
      return;
    }
    if (!astrogenValidTariffCode(formData && formData.tariff)) {
      goStep(2);
      return;
    }
    goStep(3);
  }
}
window.tryNavigateWizardStep = tryNavigateWizardStep;

function goStep(n) {
  if (n === 2) {
    const err = document.getElementById('step1-error');
    if (!step1InputsValid()) {
      if (err) err.style.display = 'block';
      return;
    }
    if (err) err.style.display = 'none';
  }
  document.querySelectorAll('.wizard-panel').forEach(p => p.classList.remove('active'));
  document.getElementById('step'+n).classList.add('active');
  updateWizardNav(n);
  document.getElementById('form').scrollIntoView({behavior:'smooth', block:'start'});
  if (n === 1 && typeof refreshWizardStep2Copy === 'function') refreshWizardStep2Copy();
  if (n === 2) {
    var selCode = (formData && formData.tariff) || 'report';
    if (typeof applyWizardTariffSelection === 'function') applyWizardTariffSelection(selCode);
    if (typeof refreshWizardStep2Copy === 'function') refreshWizardStep2Copy();
  }
  if (n === 3 && typeof updateStep3AuthUI === 'function') updateStep3AuthUI();
}

function updateWizardNav(active) {
  document.querySelectorAll('.wizard-step').forEach((s,i) => {
    const stepN = i+1;
    s.classList.remove('active','done');
    if (stepN === active) {
      s.classList.add('active');
      s.setAttribute('aria-current', 'step');
    } else {
      s.removeAttribute('aria-current');
      if (stepN < active) s.classList.add('done');
    }
  });
  document.querySelectorAll('.wizard-connector').forEach((c,i) => {
    c.classList.toggle('done', i+1 < active);
  });
}

document.addEventListener('DOMContentLoaded', function () {
  var ws = document.getElementById('wizardSteps');
  if (!ws) return;
  ws.addEventListener('click', function (e) {
    var stepEl = e.target.closest('.wizard-step');
    if (!stepEl || !ws.contains(stepEl)) return;
    var n = parseInt(stepEl.getAttribute('data-step'), 10);
    if (isNaN(n) || n < 1 || n > 3) return;
    e.preventDefault();
    if (typeof tryNavigateWizardStep === 'function') tryNavigateWizardStep(n);
  });
  ws.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    var stepEl = e.target.closest('.wizard-step');
    if (!stepEl || !ws.contains(stepEl)) return;
    e.preventDefault();
    var n = parseInt(stepEl.getAttribute('data-step'), 10);
    if (isNaN(n) || n < 1 || n > 3) return;
    if (typeof tryNavigateWizardStep === 'function') tryNavigateWizardStep(n);
  });
});

function selectTariff(el) {
  const tariff = el.dataset.tariff;
  if (!tariff) return;
  applyWizardTariffSelection(tariff);
  var aw = document.getElementById('report-email-alt-wrap');
  var ai = document.getElementById('report-email-alt-input');
  var ba = document.getElementById('btn-toggle-alt-email');
  if (aw) aw.classList.remove('show');
  if (ai) ai.value = '';
  var rae = document.getElementById('report-email-alt-error');
  if (rae) { rae.classList.remove('show'); rae.textContent = ''; }
  if (ba && typeof tAstrogen === 'function') ba.textContent = tAstrogen('report_email_other_btn');
  const step3sub = document.getElementById('step3-sub');
  const freeNote = document.getElementById('auth-free-note');
  const emailBlock = document.getElementById('auth-email-block');
  const cta = document.getElementById('step3-cta');
  const tFn = typeof tAstrogen === 'function' ? tAstrogen : function (k, v) { return k; };
  if (tariff === 'free') {
    if (step3sub) step3sub.textContent = tFn('wiz_s3sub_free');
    if (freeNote) freeNote.style.display='block';
    if (emailBlock) emailBlock.style.display='block';
    if (cta) cta.textContent = tFn('step3_cta_free');
  } else {
    const labels = { report: tFn('tariff_lbl_report'), bundle: tFn('tariff_lbl_bundle'), pro: tFn('tariff_lbl_pro') };
    if (step3sub) step3sub.textContent = tFn('wiz_s3sub_paid');
    if (freeNote) freeNote.style.display='none';
    if (emailBlock) emailBlock.style.display='none';
    if (cta) cta.textContent = tFn('step3_pay', { label: labels[tariff] || '' });
  }
  setTimeout(() => goStep(3), 180);
}

function refreshWizardStep3Copy() {
  var tariff = (window.formData && window.formData.tariff) || 'report';
  var tFn = typeof tAstrogen === 'function' ? tAstrogen : function (k, v) { return ''; };
  var step3sub = document.getElementById('step3-sub');
  var cta = document.getElementById('step3-cta');
  if (step3sub && document.getElementById('step3') && document.getElementById('step3').classList.contains('active')) {
    if (tariff === 'free') step3sub.textContent = tFn('wiz_s3sub_free');
    else step3sub.textContent = tFn('wiz_s3sub_paid');
  }
  if (cta && document.getElementById('step3') && document.getElementById('step3').classList.contains('active')) {
    if (tariff === 'free') cta.textContent = tFn('step3_cta_free');
    else {
      var labels = { report: tFn('tariff_lbl_report'), bundle: tFn('tariff_lbl_bundle'), pro: tFn('tariff_lbl_pro') };
      cta.textContent = tFn('step3_pay', { label: labels[tariff] || '' });
    }
  }
  if (typeof refreshStep3OrderSummary === 'function') refreshStep3OrderSummary();
  if (typeof updateStep3AuthUI === 'function') updateStep3AuthUI();
}

function toggleTheme() {
  const html = document.documentElement;
  const isDark = html.getAttribute('data-theme') === 'dark';
  html.setAttribute('data-theme', isDark ? 'light' : 'dark');
  document.querySelector('.theme-btn').textContent = isDark ? '☀' : '☾';
}

/** Форматирование цен: ₽ из API и $ из полей price_usd (бэкенд). */
function astrogenFmtRub(n) {
  var x = Math.round(Number(n));
  if (isNaN(x)) return '';
  return String(x).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
}
function astrogenFmtUsd(n) {
  var x = Number(n);
  if (isNaN(x)) return '0';
  if (x === 0) return '0';
  var s = (Math.round(x * 100) / 100).toFixed(2);
  if (s.indexOf('.') !== -1) s = s.replace(/\.?0+$/, '');
  return s;
}

function applyAstrogenTariffPrices() {
  var byCode = window.__astrogenTariffsByCode;
  if (!byCode) return;
  var lang = typeof getAstrogenLang === 'function' ? getAstrogenLang() : 'ru';
  var en = lang === 'en';
  var B = window.ASTROGEN_L10N_BUNDLE;

  function patchTariffLabels() {
    if (!B || !B.ru || !B.en) return;
    var tR = byCode.report;
    var tB = byCode.bundle;
    var tP = byCode.pro;
    if (tR) {
      B.ru.tariff_lbl_report = 'Отчёт · ' + astrogenFmtRub(tR.price) + ' ₽';
      B.en.tariff_lbl_report = 'Report · $' + astrogenFmtUsd(tR.price_usd);
    }
    if (tB) {
      B.ru.tariff_lbl_bundle = 'Набор «3» · ' + astrogenFmtRub(tB.price) + ' ₽';
      B.en.tariff_lbl_bundle = 'Bundle of 3 · $' + astrogenFmtUsd(tB.price_usd);
    }
    if (tP) {
      B.ru.tariff_lbl_pro = 'Astro Pro · ' + astrogenFmtRub(tP.price) + ' ₽/мес';
      B.en.tariff_lbl_pro = 'Astro Pro · $' + astrogenFmtUsd(tP.price_usd) + '/mo';
    }
  }
  patchTariffLabels();

  function setSimple(cardSelector, code) {
    var t = byCode[code];
    if (!t) return;
    var el = document.querySelector(cardSelector + ' .js-pricing-simple');
    if (!el) return;
    if (en) el.textContent = '$' + astrogenFmtUsd(t.price_usd);
    else el.textContent = astrogenFmtRub(t.price) + ' ₽';
  }
  setSimple('.pricing-card[data-tariff-code="free"]', 'free');
  setSimple('.pricing-card[data-tariff-code="report"]', 'report');

  var tb = byCode.bundle;
  if (tb) {
    var bundleCard = document.querySelector('.pricing-card[data-tariff-code="bundle"]');
    if (bundleCard) {
      var main = bundleCard.querySelector('.js-pricing-bundle-main');
      var cur = bundleCard.querySelector('.js-pricing-bundle-cur');
      var old = bundleCard.querySelector('.js-pricing-bundle-old');
      var meta = bundleCard.querySelector('.js-pricing-bundle-meta');
      var unitEl = bundleCard.querySelector('.js-pricing-bundle-unit');
      if (en) {
        if (main) main.textContent = '$' + astrogenFmtUsd(tb.price_usd);
        if (cur) cur.textContent = '';
        if (old && tb.compare_price_usd != null) old.textContent = '$' + astrogenFmtUsd(tb.compare_price_usd);
        var uUsd = '$' + astrogenFmtUsd(Number(tb.price_usd) / 3);
        if (unitEl) unitEl.textContent = uUsd;
        if (meta) {
          meta.innerHTML = '3 full reports · <span class="pricing-meta-unit">' + uUsd + '</span> each';
        }
      } else {
        if (main) main.textContent = astrogenFmtRub(tb.price);
        if (cur) cur.textContent = '₽';
        var cmpRub = Math.round(Number(tb.price) * (2370 / 1590));
        if (old) old.textContent = astrogenFmtRub(cmpRub);
        var unitRub = Math.round(Number(tb.price) / 3);
        if (unitEl) unitEl.textContent = astrogenFmtRub(unitRub) + ' ₽';
        if (meta) {
          meta.innerHTML = '3 полных отчёта · <span class="pricing-meta-unit">' + astrogenFmtRub(unitRub) + ' ₽</span> за штуку';
        }
      }
    }
  }

  var tp = byCode.pro;
  if (tp) {
    var proCard = document.querySelector('.pricing-card[data-tariff-code="pro"]');
    if (proCard) {
      var pm = proCard.querySelector('.js-pricing-pro-main');
      var pp = proCard.querySelector('.js-pricing-pro-period');
      var pa = proCard.querySelector('.js-pricing-pro-annual');
      if (en) {
        if (pm) pm.textContent = '$' + astrogenFmtUsd(tp.price_usd);
        if (pp) pp.textContent = ' / mo';
        if (pa && tp.annual_total_usd != null) {
          pa.textContent = '≈ $' + astrogenFmtUsd(tp.annual_total_usd) + '/year on monthly billing';
        }
      } else {
        if (pm) pm.textContent = astrogenFmtRub(tp.price);
        if (pp) pp.textContent = '₽ / мес';
        var annualRub = Math.round(Number(tp.price) * 12);
        if (pa) pa.textContent = '≈ ' + astrogenFmtRub(annualRub) + ' ₽/год при помесячной оплате';
      }
    }
  }

  document.querySelectorAll('.wizard-tariff[data-tariff]').forEach(function (el) {
    var code = el.getAttribute('data-tariff');
    var t = byCode[code];
    if (!t) return;
    var line = el.querySelector('.js-wt-line');
    if (!line) return;
    if (code === 'pro') {
      if (en) line.textContent = '$' + astrogenFmtUsd(t.price_usd) + ' / mo';
      else line.textContent = astrogenFmtRub(t.price) + ' ₽ / мес';
    } else if (code === 'free') {
      if (en) line.textContent = '$' + astrogenFmtUsd(t.price_usd);
      else line.textContent = astrogenFmtRub(t.price) + ' ₽';
    } else {
      if (en) line.textContent = '$' + astrogenFmtUsd(t.price_usd);
      else line.textContent = astrogenFmtRub(t.price) + ' ₽';
    }
  });

  var wBundle = document.querySelector('.wizard-tariff[data-tariff="bundle"]');
  if (tb && wBundle) {
    var wm = wBundle.querySelector('.js-wt-bundle-meta');
    var wu = wBundle.querySelector('.js-wt-bundle-unit');
    var b1 = wBundle.querySelector('.js-wt-b1-line');
    if (en) {
      var uUsdW = '$' + astrogenFmtUsd(Number(tb.price_usd) / 3);
      if (wu) wu.textContent = uUsdW;
      if (wm) {
        wm.innerHTML = '3 full reports · <span class="wt-meta-unit">' + uUsdW + '</span> each';
      }
      if (b1) b1.textContent = '3 full reports (' + uUsdW + '/ea)';
    } else {
      var ur = Math.round(Number(tb.price) / 3);
      if (wu) wu.textContent = astrogenFmtRub(ur) + ' ₽';
      if (wm) {
        wm.innerHTML = '3 полных отчёта · <span class="wt-meta-unit">' + astrogenFmtRub(ur) + ' ₽</span> за штуку';
      }
      if (b1) b1.textContent = '3 полных отчёта (' + astrogenFmtRub(ur) + ' ₽/шт)';
    }
  }
  if (typeof refreshStep3OrderSummary === 'function') refreshStep3OrderSummary();
}
window.applyAstrogenTariffPrices = applyAstrogenTariffPrices;

/* ── Language ── */
function setLang(lang) {
  var normalized = lang === 'en' ? 'en' : 'ru';
  try { localStorage.setItem('astrogen_lang', normalized); } catch (e) {}
  if (normalized === 'ru') {
    try { window.__astrogenEnBundleLoadedCallback = null; } catch (e1) {}
  }

  function finishUi() {
    document.querySelectorAll('.lang-btn').forEach(function (b) { b.classList.remove('active'); });
    var btn = document.querySelector('.lang-btn[onclick="setLang(\'' + normalized + '\')"]');
    if (btn) btn.classList.add('active');
    if (typeof applyAstrogenTariffPrices === 'function') applyAstrogenTariffPrices();
    if (typeof refreshWizardStep3Copy === 'function') refreshWizardStep3Copy();
    if (typeof refreshWizardStep2Copy === 'function') refreshWizardStep2Copy();
  }

  if (typeof applyAstrogenLandingLang === 'function') {
    applyAstrogenLandingLang(normalized, finishUi);
  } else {
    document.documentElement.setAttribute('lang', normalized === 'en' ? 'en' : 'ru');
    if (typeof astrogenBirthDateLocaleApplyLang === 'function') astrogenBirthDateLocaleApplyLang();
    finishUi();
  }
}

/* ── Tabs ── */
function switchTab(btn, panelId) {
  btn.closest('.demo-card').querySelectorAll('.demo-tab').forEach(t => t.classList.remove('active'));
  btn.closest('.demo-card').querySelectorAll('.demo-panel').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById(panelId).classList.add('active');
}

/* ── FAQ ── */
function toggleFaq(btn) {
  const item = btn.parentElement;
  const isOpen = item.classList.contains('open');
  document.querySelectorAll('.faq-item.open').forEach(i => i.classList.remove('open'));
  if (!isOpen) item.classList.add('open');
}

/* ── PDF Download simulation ── */
function simulatePdfDownload(el, e) {
  e.preventDefault();
  const tFn = typeof tAstrogen === 'function' ? tAstrogen : function (k) { return k; };
  const orig = el.innerHTML;
  el.innerHTML = '<svg width="15" height="15" viewBox="0 0 15 15" fill="none"><circle cx="7.5" cy="7.5" r="6" stroke="currentColor" stroke-width="1.5" stroke-dasharray="38" stroke-dashoffset="10" style="animation: spin 0.8s linear infinite; transform-origin: 50% 50%;"/></svg> ' + tFn('pdf_loading');
  el.style.opacity = '0.8';
  setTimeout(() => {
    el.innerHTML = '<svg width="15" height="15" viewBox="0 0 15 15" fill="none"><path d="M3 7.5l3 3 6-6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg> ' + tFn('pdf_ready');
    el.style.background = '#52C41A';
    el.style.borderColor = '#52C41A';
    setTimeout(() => {
      el.innerHTML = orig;
      if (typeof applyAstrogenLandingLang === 'function') applyAstrogenLandingLang(typeof getAstrogenLang === 'function' ? getAstrogenLang() : 'ru');
      if (typeof applyAstrogenTariffPrices === 'function') applyAstrogenTariffPrices();
      if (typeof refreshWizardStep3Copy === 'function') refreshWizardStep3Copy();
      if (typeof refreshWizardStep2Copy === 'function') refreshWizardStep2Copy();
      el.style.opacity = '';
      el.style.background = '';
      el.style.borderColor = '';
    }, 2200);
  }, 1400);
  return false;
}

/* ── Carousel ── */
(function() {
  const CARDS = 6;
  const GAP = 20;
  let perView = 3, current = 0, maxIndex = 0;

  function getPerView() {
    if (window.innerWidth <= 600) return 1;
    if (window.innerWidth <= 900) return 2;
    return 3;
  }

  function updateTrack() {
    const track = document.getElementById('carouselTrack');
    const container = document.querySelector('.carousel-track-wrap');
    if (!track || !container) return;
    perView = getPerView();
    maxIndex = CARDS - perView;
    if (current > maxIndex) current = maxIndex;

    const containerW = container.offsetWidth;
    const cardW = Math.floor((containerW - GAP * (perView - 1)) / perView);

    track.querySelectorAll('.review-card').forEach(c => {
      c.style.width = cardW + 'px';
      c.style.minWidth = cardW + 'px';
    });

    track.style.transform = `translateX(-${current * (cardW + GAP)}px)`;

    document.getElementById('carouselPrev').disabled = current === 0;
    document.getElementById('carouselNext').disabled = current >= maxIndex;
    document.getElementById('carouselCounter').textContent = `${current + 1} / ${maxIndex + 1}`;

    const dots = document.getElementById('carouselDots');
    if (dots) {
      dots.innerHTML = '';
      for (let i = 0; i <= maxIndex; i++) {
        const d = document.createElement('div');
        d.className = 'carousel-dot' + (i === current ? ' active' : '');
        d.onclick = () => goTo(i);
        dots.appendChild(d);
      }
    }
  }

  function goTo(idx) { current = Math.max(0, Math.min(idx, maxIndex)); updateTrack(); }
  window.carouselMove = function(dir) { goTo(current + dir); };
  window.addEventListener('resize', updateTrack);
  document.addEventListener('DOMContentLoaded', updateTrack);
  setTimeout(updateTrack, 50);

  const wrap = document.getElementById('carouselTrack');
  if (wrap) {
    let startX = 0;
    wrap.addEventListener('touchstart', e => { startX = e.touches[0].clientX; }, { passive: true });
    wrap.addEventListener('touchend', e => {
      if (Math.abs(e.changedTouches[0].clientX - startX) > 50) carouselMove(e.changedTouches[0].clientX < startX ? 1 : -1);
    }, { passive: true });
  }
})();
