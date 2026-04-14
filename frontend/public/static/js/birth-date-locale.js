/**
 * Локальный порядок полей даты рождения: RU — день · месяц · год, EN — месяц · день · год.
 * Синхронизация со скрытым input#f-date (ISO YYYY-MM-DD).
 * Год — input type="number" (без гигантского нативного select).
 */
(function (global) {
  var MONTHS_RU = ['янв.', 'февр.', 'мар.', 'апр.', 'мая', 'июн.', 'июл.', 'авг.', 'сен.', 'окт.', 'нояб.', 'дек.'];
  var MONTHS_EN = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  function daysInMonth(y, m) {
    return new Date(y, m, 0).getDate();
  }

  function pad2(n) {
    return String(n).padStart(2, '0');
  }

  function getLang() {
    var langAttr = (document.documentElement && document.documentElement.getAttribute('lang')) || 'ru';
    if (langAttr.toLowerCase().indexOf('en') === 0) return 'en';
    var active = document.querySelector('.lang-btn.active');
    if (active && /en/i.test((active.textContent || '').trim())) return 'en';
    return 'ru';
  }

  function bindYearInput(inp, maxY) {
    inp.setAttribute('min', '1800');
    inp.setAttribute('max', String(maxY));
    inp.placeholder = getLang() === 'en' ? 'Year' : 'Год';
  }

  function fillMonthSelect(sel) {
    var lang = getLang();
    var labels = lang === 'en' ? MONTHS_EN : MONTHS_RU;
    var v = sel.value;
    sel.innerHTML = '<option value="">' + (lang === 'en' ? 'Month' : 'Месяц') + '</option>';
    for (var m = 1; m <= 12; m++) {
      var o = document.createElement('option');
      o.value = String(m);
      o.textContent = labels[m - 1];
      sel.appendChild(o);
    }
    if (v && sel.querySelector('option[value="' + v + '"]')) sel.value = v;
  }

  function fillDaySelect(sel, y, m) {
    var v = sel.value;
    var maxD = y && m ? daysInMonth(y, m) : 31;
    sel.innerHTML = '<option value="">' + (getLang() === 'en' ? 'Day' : 'Число') + '</option>';
    for (var d = 1; d <= maxD; d++) {
      var o = document.createElement('option');
      o.value = String(d);
      o.textContent = String(d);
      sel.appendChild(o);
    }
    if (v) {
      var iv = parseInt(v, 10);
      if (iv >= 1 && iv <= maxD && sel.querySelector('option[value="' + v + '"]')) sel.value = v;
      else sel.value = String(Math.min(iv, maxD));
    }
  }

  function applyPartsOrder(partsEl) {
    var lang = getLang();
    partsEl.setAttribute('data-order', lang === 'en' ? 'mdy' : 'dmy');
  }

  function parseIso(iso) {
    if (!iso || !/^\d{4}-\d{2}-\d{2}$/.test(iso)) return null;
    return {
      y: parseInt(iso.slice(0, 4), 10),
      m: parseInt(iso.slice(5, 7), 10),
      d: parseInt(iso.slice(8, 10), 10),
    };
  }

  function yearOk(y, maxY) {
    return typeof y === 'number' && !isNaN(y) && y >= 1800 && y <= maxY;
  }

  global.astrogenBirthDateLocaleInit = function (opts) {
    opts = opts || {};
    var hidden = document.getElementById('f-date');
    var partsEl = document.getElementById('f-date-parts');
    var daySel = document.getElementById('f-date-day');
    var monthSel = document.getElementById('f-date-month');
    var yearInp = document.getElementById('f-date-year');
    if (!hidden || !partsEl || !daySel || !monthSel || !yearInp) return;

    var maxY = new Date().getFullYear();

    function refreshDays() {
      var y = parseInt(yearInp.value, 10);
      var m = parseInt(monthSel.value, 10);
      if (!yearOk(y, maxY) || !m) {
        fillDaySelect(daySel, null, null);
        return;
      }
      fillDaySelect(daySel, y, m);
    }

    function commit() {
      var y = parseInt(yearInp.value, 10);
      var m = parseInt(monthSel.value, 10);
      var d = parseInt(daySel.value, 10);
      if (!yearOk(y, maxY) || !m || !d) {
        hidden.value = '';
        if (opts.onCommit) opts.onCommit('');
        return;
      }
      var iso = y + '-' + pad2(m) + '-' + pad2(d);
      hidden.value = iso;
      if (opts.onCommit) opts.onCommit(iso);
    }

    function syncUIFromHidden() {
      var iso = hidden.value;
      var p = parseIso(iso);
      bindYearInput(yearInp, maxY);
      fillMonthSelect(monthSel);
      if (!p) {
        daySel.innerHTML = '<option value="">' + (getLang() === 'en' ? 'Day' : 'Число') + '</option>';
        for (var i = 1; i <= 31; i++) {
          var o = document.createElement('option');
          o.value = String(i);
          o.textContent = String(i);
          daySel.appendChild(o);
        }
        yearInp.value = '';
        monthSel.value = '';
        daySel.value = '';
        return;
      }
      yearInp.value = String(p.y);
      monthSel.value = String(p.m);
      fillDaySelect(daySel, p.y, p.m);
      daySel.value = String(p.d);
    }

    bindYearInput(yearInp, maxY);
    fillMonthSelect(monthSel);
    fillDaySelect(daySel, null, null);
    applyPartsOrder(partsEl);

    yearInp.addEventListener('input', function () {
      refreshDays();
      commit();
    });
    yearInp.addEventListener('change', function () {
      var y = parseInt(yearInp.value, 10);
      if (yearInp.value !== '' && !isNaN(y)) {
        if (y < 1800) yearInp.value = '1800';
        if (y > maxY) yearInp.value = String(maxY);
      }
      refreshDays();
      commit();
    });
    yearInp.addEventListener('wheel', function (e) {
      if (document.activeElement === yearInp) e.preventDefault();
    }, { passive: false });

    monthSel.addEventListener('change', function () {
      refreshDays();
      commit();
    });
    daySel.addEventListener('change', commit);

    global.astrogenBirthDateLocaleApplyLang = function () {
      document.documentElement.setAttribute('lang', getLang() === 'en' ? 'en' : 'ru');
      applyPartsOrder(partsEl);
      bindYearInput(yearInp, maxY);
      var y = parseInt(yearInp.value, 10);
      var m = parseInt(monthSel.value, 10);
      var d = parseInt(daySel.value, 10);
      fillMonthSelect(monthSel);
      if (yearOk(y, maxY) && m) {
        fillDaySelect(daySel, y, m);
        if (d) daySel.value = String(Math.min(d, daysInMonth(y, m)));
      } else {
        fillDaySelect(daySel, null, null);
      }
      commit();
    };

    global.astrogenBirthDateLocaleSyncFromHidden = syncUIFromHidden;
    /** Записать ISO в #f-date из день/месяц/год (перед валидацией шага, если UI рассинхронен со скрытым полем). */
    global.astrogenBirthDateLocaleCommitFromParts = commit;

    syncUIFromHidden();
  };
})(window);
