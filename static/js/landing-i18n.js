/**
 * Astrogen static landing — RU / EN copy via data-i18n attributes.
 */
(function (global) {
  var BUNDLE = {
    ru: {},
    en: {},
  };

  function merge(lang, map) {
    var target = BUNDLE[lang] || (BUNDLE[lang] = {});
    Object.keys(map).forEach(function (k) {
      target[k] = map[k];
    });
  }
  global.__astrogenI18nMerge = merge;

  merge('ru', {
    meta_title: 'Astrogen — Персональная натальная карта онлайн | Астрологический паспорт личности',
    meta_description: 'Рассчитайте персональную натальную карту онлайн за 60 секунд. Детальный разбор характера, талантов и жизненных циклов по дате, времени и месту рождения. PDF-отчёт на почту.',
    meta_og_title: 'Astrogen — Персональная натальная карта',
    meta_og_description: 'Ваш астрологический паспорт личности. Расчёт за 60 секунд, PDF-отчёт на почту.',
    nav_features: 'О сервисе',
    nav_example: 'Пример',
    nav_pricing: 'Тарифы',
    nav_about: 'О нас',
    nav_faq: 'FAQ',
    nav_login: 'Войти',
    nav_cabinet: 'Кабинет',
    auth_popup_subtitle: 'Личный кабинет',
    auth_popup_close_aria: 'Закрыть',
    auth_popup_tg_heading: 'Войти одним из способов',
    auth_popup_tg_btn: 'Войти через Telegram',
    auth_popup_divider: 'или через браузер',
    auth_popup_oauth_label: 'Войти через',
    auth_popup_yandex: 'Яндекс',
    auth_popup_footer_html:
      'Входя, вы принимаете <a href="/oferta">Оферту</a> и <a href="/privacy">Политику конфиденциальности</a>',
    auth_popup_loading_telegram: 'Вход через Telegram…',
    auth_popup_alert_open_tg: 'Откройте приложение из Telegram, чтобы войти через Telegram.',
    auth_popup_alert_tg_fail: 'Не удалось войти через Telegram.',
    theme_title: 'Сменить тему',
    hero_label: 'Персональная астрология',
    hero_title_html: 'Вы снова там,<br>где уже были.<br><em>Пора разобраться почему.</em>',
    hero_desc: 'Натальная карта — это не гороскоп. Это точная схема вашей психики: почему вы реагируете именно так, почему повторяются одни сценарии, и когда наконец придёт подходящее время для перемен.',
    hero_cta1: 'Узнать свою карту →',
    hero_cta2: 'Посмотреть пример',
    hero_trust1: 'PDF-отчёт за 60 сек',
    hero_trust2: 'Расчёт по точному времени',
    legend_trine: 'Трин',
    legend_opp: 'Оппозиция',
    legend_square: 'Квадратура',
    legend_conj: 'Соединение',
    stats_charts: 'карт уже рассчитано',
    stats_rating: 'средняя оценка из 5.0',
    stats_time: 'расчёт и PDF на почту',
    stats_pdf: 'в каждом PDF-отчёте',
    stat_suffix_plus: '+',
    stat_suffix_sec: ' с',
    stat_suffix_pages: ' стр.',
    whatis_tag: 'Что такое натальная карта',
    whatis_title: 'Астрологический паспорт вашей личности',
    whatis_p1: 'Натальная карта — это астрологическая схема положения планет в момент вашего рождения. Её используют как инструмент самопознания: она помогает понять паттерны поведения, сильные стороны, источники внутренних конфликтов и наиболее подходящие жизненные сферы.',
    whatis_p2: 'Это не предсказание судьбы — это описание вашей психологической «прошивки». Astrogen рассчитывает её автоматически и формирует PDF-отчёт, который приходит на вашу почту.',
    whatis_c1t: 'Солнце, Луна, Асцендент',
    whatis_c1d: 'Базовая личность, эмоции, внешняя маска',
    whatis_c2t: '12 астрологических домов',
    whatis_c2d: 'Карьера, финансы, отношения, здоровье',
    whatis_c3t: 'Аспекты планет',
    whatis_c3d: 'Таланты, внутренние противоречия, ресурсы',
    whatis_c4t: 'Транзиты и циклы',
    whatis_c4d: 'Актуальные астрологические влияния',
    forwhom_tag: 'Для кого это',
    forwhom_title: 'Узнайте себя в одном из сценариев',
    forwhom_sub: 'Натальная карта даёт ответы там, где обычная психология останавливается',
    forwhom_1t: '«Я снова в тех же отношениях»',
    forwhom_1d: 'Разные люди, одни и те же сценарии. Карта показывает, какой паттерн вы воспроизводите и откуда он берётся — не из прошлого, а из структуры вашей личности.',
    forwhom_1tag: 'Нодальная ось · VII дом · Луна',
    forwhom_2t: '«Не понимаю, куда двигаться в карьере»',
    forwhom_2d: 'Вы умный и способный, но дорога не складывается. Карта указывает, в каких сферах ваш потенциал максимален — и почему одни пути даются легко, а другие превращаются в борьбу.',
    forwhom_2tag: 'X дом · Солнце · Сатурн',
    forwhom_3t: '«Чувствую, что жду чего-то, но не понимаю чего»',
    forwhom_3d: 'Иногда нужно не действовать, а понять — ваше ли это время. Транзиты показывают, когда астрологически открываются окна для старта, а когда лучше накапливать.',
    forwhom_3tag: 'Транзиты · Прогрессии · Юпитер',
    forwhom_4t: '«Мы с партнёром очень разные»',
    forwhom_4d: 'Конфликты не из-за характера — из-за разных «операционных систем». Карта объясняет, почему вы реагируете именно так, и что стоит за поведением близких людей.',
    forwhom_4tag: 'Луна · Асцендент · Марс',
    feat_tag: 'Состав отчёта',
    feat_title: 'Что входит в ваш астрологический паспорт',
    feat_sub: 'Каждый раздел — конкретный инсайт, не абстрактный текст. PDF-отчёт отправляется на почту сразу после расчёта.',
    feat_1t: 'Солнце, Луна и Асцендент',
    feat_1d: 'Ядро личности: как вы воспринимаете себя, как реагируете эмоционально и как выглядите для окружающих. Три главных элемента карты в одном блоке.',
    feat_2t: 'Планеты по домам',
    feat_2d: 'Подробный разбор всех 10 планет в 12 домах гороскопа: карьера, деньги, партнёрство, творчество, путешествия, здоровье и духовность.',
    feat_3t: 'Аспекты и их значение',
    feat_3d: 'Трины, секстили, квадратуры и оппозиции между планетами — где ваши природные таланты и какие внутренние конфликты требуют проработки.',
    feat_4t: 'Транзиты на год',
    feat_4d: 'Движение планет через ваши натальные позиции. Когда лучшее время для старта новых проектов, крупных решений или восстановления.',
    feat_5t: 'Нодальная ось',
    feat_5d: 'Северный и Южный узлы Луны — кармические задачи и ресурсы прошлого. Ключ к пониманию жизненного направления и повторяющихся сценариев.',
    feat_6t: 'Практические рекомендации',
    feat_6d: 'Конкретные советы по ключевым сферам жизни на основе всего разбора. Не общие слова — а адресованные именно вашей конфигурации карты.',
    ex_tag: 'Пример натальной карты',
    ex_title: 'Посмотрите, как выглядит готовый отчёт',
    ex_sub: 'Реальный пример разбора для даты 15 июня 1990, Москва, 08:30',
    demo_tab_scheme: 'Схема карты',
    demo_tab_planets: 'Планеты',
    demo_tab_aspects: 'Аспекты',
    demo_tab_transits: 'Транзиты',
    demo_note: 'Демо-отчёт · 18 страниц',
    demo_calc_for: 'Карта рассчитана для:',
    demo_sample_birth: '15 июня 1990, 08:30, Москва',
    demo_sun_sign: 'Солнечный знак',
    demo_moon_sign: 'Лунный знак',
    demo_asc: 'Асцендент',
    demo_ruler: 'Управитель',
    demo_key: 'Ключевая конфигурация:',
    demo_key_text: 'Большой секстиль — редкая гармоничная конструкция, указывающая на исключительный потенциал в коммуникации и аналитике.',
    pdf_title: 'Пример PDF-отчёта · Натальная карта',
    pdf_sub: '18 страниц · Полный разбор · Схема карты · Аспекты · Рекомендации',
    pdf_tag1: 'Солнце в Близнецах',
    pdf_tag2: 'Луна в Козероге',
    pdf_tag3: 'Большой секстиль',
    pdf_tag4: '7 аспектов',
    pdf_tag5: 'Транзиты 2025',
    pdf_download: 'Скачать пример PDF',
    pdf_free_meta: 'Бесплатно · 2.4 МБ · PDF',
    pdf_loading: 'Загрузка...',
    pdf_ready: 'Файл готов!',
    pricing_tag: 'Тарифы',
    pricing_title: 'Выберите свой формат',
    pricing_sub: 'Каждый платный отчёт отправляется на почту и сохраняется в личном кабинете навсегда.',
    payment_note_html: 'Оплата через <a href="#">ЮKassa</a> · Карты Visa, Mastercard, МИР · Безопасная передача данных',
    reviews_tag: 'Отзывы',
    reviews_title: 'Что говорят первые пользователи',
    reviews_avg: 'средняя оценка',
    steps_tag: 'Как это работает',
    steps_title: 'Три шага до вашей карты',
    step_1t: 'Введите данные рождения',
    step_1d: 'Дата, время и место рождения. Время приблизительное? Укажем диапазон и пометим в отчёте.',
    step_2t: 'Расчёт за 60 секунд',
    step_2d: 'Система рассчитывает точное положение всех планет и формирует персональный отчёт.',
    step_3t: 'PDF на почту и в кабинет',
    step_3d: 'Отчёт мгновенно отправляется на email и сохраняется в личном кабинете навсегда.',
    about_tag: 'О нас',
    about_title: 'Astrogen — сервис персональной астрологии',
    about_p1: 'Мы создали Astrogen с одной целью: сделать астрологию доступным и понятным инструментом самопознания. Без мистики, эзотерического пафоса и размытых формулировок.',
    about_p2: 'Начав с натальных карт, мы развиваем платформу в полноценную экосистему персональной астрологии: синастрия, прогрессии, персональные гороскопы, астрологические прогнозы на год.',
    about_v1s: 'Точность расчётов',
    about_v1l: 'Астрологические алгоритмы профессионального уровня',
    about_v2s: 'Мгновенная доставка',
    about_v2l: 'PDF на почту сразу после расчёта',
    about_v3s: 'Конфиденциальность',
    about_v3l: 'Данные защищены по 152-ФЗ',
    about_v4s: 'Развитие платформы',
    about_v4l: 'Новые продукты в рамках одного аккаунта',
    pill_chart: '★ Натальная карта',
    pill_syn: 'Синастрия',
    pill_fore: 'Прогнозы',
    pill_prog: 'Прогрессии',
    pill_hor: 'Гороскоп',
    pill_tr: 'Транзиты',
    form_tag: 'Расчёт натальной карты',
    form_title: 'Рассчитайте вашу натальную карту',
    form_sub: 'PDF-отчёт будет готов за 60 секунд и придёт на почту',
    wiz_l1: 'Данные рождения',
    wiz_l2: 'Выберите тариф',
    wiz_l2_confirm: 'Подтвердите тариф',
    wiz_l3: 'Вход и оплата',
    wiz_s1t: 'Расскажите о себе',
    wiz_s1sub: 'Данные нужны для астрологического расчёта — они хранятся только в вашем аккаунте',
    label_name: 'Ваше имя',
    ph_name: 'Как к вам обращаться',
    label_date: 'Дата рождения',
    label_time: 'Время рождения',
    hint_time: 'Не знаете точно? Укажите примерное',
    label_place: 'Место рождения',
    ph_place: 'Город, страна',
    step1_err: 'Заполните имя, дату и место рождения',
    btn_continue: 'Продолжить',
    form_privacy_line: 'Данные не передаются третьим лицам · 152-ФЗ',
    wiz_s2t: 'Выберите тариф',
    wiz_s2t_confirm: 'Подтвердите или измените тариф',
    wiz_s2sub_default: 'PDF-отчёт отправляется на почту сразу после расчёта',
    wt_free: 'Бесплатно',
    wt_f1: 'Схема карты + Солнце/Луна/Асц',
    wt_f2: '1-страничный PDF на почту',
    wt_f3: 'Полный разбор планет',
    wt_free_btn: 'Выбрать бесплатно',
    wt_popular: 'Популярный',
    wt_report: 'Отчёт',
    wt_r1: 'Все планеты в 12 домах',
    wt_r2: 'Аспекты + нодальная ось',
    wt_r3: 'PDF 12–14 стр. навсегда',
    wt_report_btn: 'Получить отчёт',
    wt_bundle: 'Набор «3»',
    wt_bundle_meta: '3 полных отчёта · <span class="wt-meta-unit">530 ₽</span> за штуку',
    wt_b1: '3 полных отчёта (530 ₽/шт)',
    wt_b2: 'Режим подарка с открыткой',
    wt_b3: 'Экономия 33%',
    wt_bundle_btn: 'Купить набор',
    wt_sub: 'Подписка',
    wt_pro: 'Astro Pro',
    wt_per: '₽ / мес',
    wt_p1: 'Полный отчёт + транзиты',
    wt_p2: 'Синастрия + прогрессии',
    wt_p3: 'Обновление каждый месяц',
    wt_pro_btn: 'Попробовать Pro',
    btn_back: '← Назад',
    wiz_s3t: 'Последний шаг',
    wiz_s3sub_paid: 'Сначала войдите — затем оплата в ЮKassa и PDF на почту',
    wiz_s3sub_free: 'Войдите чтобы сохранить карту или просто укажите email',
    auth_block_title: 'Войдите любым способом',
    auth_block_hint: 'Нужно, чтобы привязать заказ к аккаунту и отправить PDF на почту.',
    auth_unified_title: 'Войти одним из способов',
    auth_reassure: 'Если аккаунт уже есть — войдите тем же способом, что и раньше.',
    auth_status_ok: 'Вы вошли',
    auth_logout: 'Выйти',
    auth_logged_prefix: 'Вошли как',
    auth_change_account: 'Сменить аккаунт',
    step3a_label: 'Вход',
    step3a_title_pending: 'Войдите в аккаунт',
    step3a_title_done: 'Вход выполнен',
    step3a_lead: 'Аккаунт нужен, чтобы сохранить расчёт и отправить PDF на почту после оплаты.',
    step3b_label: 'Оплата',
    step3b_sub_locked: 'Станет доступна после входа',
    step3b_sub_active: 'Оплата в ЮKassa и PDF на почту',
    auth_block_sub: 'Один тап — аккаунт создаётся автоматически',
    auth_success_note: 'Аккаунт подключён · PDF придёт на эту почту',
    pay_lock_notice_html: '<strong>Сначала войдите выше</strong> — это нужно, чтобы привязать заказ к аккаунту и отправить PDF на почту',
    step3_order_heading: 'Заказ',
    step3_summary_product_report: 'Натальная карта — Полный отчёт',
    step3_summary_product_bundle: 'Набор из 3 полных отчётов',
    step3_summary_product_pro: 'Подписка Astro Pro',
    step3_summary_product_free: 'Базовая натальная карта',
    step3_summary_pdf_row: 'PDF-отчёт на почту',
    step3_summary_included: 'включён',
    step3_summary_cabinet: 'Доступ в личном кабинете',
    step3_summary_forever: 'навсегда',
    step3_summary_access_bundle: '3 отчёта · подарочный режим',
    step3_summary_access_pro: 'полный отчёт + транзиты каждый месяц',
    step3_summary_access_free: '1 карта · базовый PDF',
    step3_summary_total: 'Итого',
    step3_alt_email_info: 'PDF придёт на:',
    pay_hint_flow: 'Вы перейдёте на страницу ЮKassa — затем вернётесь и получите PDF',
    trust_pay_safe: 'Безопасная оплата',
    trust_cards: 'Карты МИР, Visa, MC',
    trust_152: 'Данные по 152-ФЗ',
    btn_alt_email_save: 'Сохранить',
    btn_alt_email_cancel: 'Отмена',
    report_email_change_btn: 'Изменить',
    pay_blocked_banner: 'Сначала войдите выше — без аккаунта мы не сможем привязать оплату и отправить отчёт.',
    pay_locked_lead: 'После входа вы перейдёте в ЮKassa, оплатите выбранный тариф, и мы отправим PDF на почту.',
    pay_flow_hint: 'Нажмите кнопку — откроется безопасная оплата ЮKassa. После оплаты PDF уйдёт на указанную ниже почту (это не чек из ЮKassa).',
    pay_trust_short: 'Оплата через ЮKassa · PCI DSS · данные карт шифруются',
    report_email_line_prefix: 'Отчёт придёт на почту аккаунта:',
    report_email_other_btn: 'Другая почта',
    report_email_back_btn: 'Использовать почту аккаунта',
    report_email_alt_label: 'Email для этого отчёта',
    report_email_alt_hint: 'Аккаунт не меняется — меняется только адрес для этого PDF. Письмо с отчётом — не кассовый чек ЮKassa.',
    ph_email_alt: 'другой@email.com',
    ph_email_free: 'your@email.com',
    err_email_invalid: 'Введите корректный email',
    aria_auth_methods: 'Способы входа',
    step3_cta_locked_hint: 'Сначала войдите выше — кнопка станет активной.',
    auth_free_note: 'Для бесплатного тарифа вход необязателен. Войдите, чтобы сохранить карту в личном кабинете — или просто укажите email для получения базового отчёта.',
    auth_tg: 'Telegram',
    auth_div: 'или через браузер',
    oauth_yandex: 'Яндекс',
    label_email_free: 'Email для получения бесплатного отчёта',
    hint_no_spam: 'Мы не отправляем спам',
    step3_cta: 'Рассчитать натальную карту →',
    step3_cta_free: 'Получить бесплатную карту →',
    step3_pay: 'Перейти к оплате · {label} →',
    form_security: 'Данные защищены · 152-ФЗ · Оплата через ЮKassa · Отмена подписки в один клик',
    btn_change_tariff: '← Сменить тариф',
    faq_title: 'Частые вопросы',
    faq_feedback_title: 'Не нашли ответ? Напишите нам',
    faq_feedback_sub: 'Отвечаем в течение 2 рабочих часов',
    ph_feedback_name: 'Ваше имя',
    ph_feedback_email: 'Email для ответа',
    ph_feedback_msg: 'Опишите вашу ситуацию или вопрос...',
    btn_send: 'Отправить сообщение',
    faq_feedback_or: 'Или напишите напрямую:',
    final_tag: 'Начните прямо сейчас',
    final_title: 'Узнайте себя глубже за 60 секунд',
    final_sub: 'Более 12 000 человек уже получили свой астрологический паспорт',
    final_cta: 'Рассчитать бесплатно →',
    footer_about: 'Персональная астрология как инструмент самопознания. Точные расчёты, понятный язык, мгновенная доставка PDF.',
    footer_service: 'Сервис',
    footer_support: 'Поддержка',
    footer_legal: 'Правовое',
    foot_about_chart: 'О натальной карте',
    foot_sample: 'Пример отчёта',
    foot_tariffs: 'Тарифы',
    foot_company: 'О компании',
    foot_feedback: 'Обратная связь',
    foot_bot: 'Telegram-бот',
    foot_cab: 'Личный кабинет',
    foot_privacy: 'Политика конфиденциальности',
    foot_oferta: 'Публичная оферта',
    foot_terms: 'Пользовательское соглашение',
    foot_152: '152-ФЗ · Обработка данных',
    foot_copy: '© 2025 Astrogen. Все права защищены.',
    foot_pay: 'Оплата через ЮKassa ·',
    wizard_greeting: '{name}, выберите тариф для вашей натальной карты',
    wizard_greeting_confirm: '{name}, вы выбрали тариф выше — подтвердите или измените его',
    tariff_lbl_report: 'Отчёт · 790 ₽',
    tariff_lbl_bundle: 'Набор «3» · 1 590 ₽',
    tariff_lbl_pro: 'Astro Pro · 490 ₽/мес',
    alert_tg: 'Откройте мини-приложение из Telegram',
    alert_tg_fail: 'Не удалось войти через Telegram',
    alert_oauth: 'Сначала войдите (Telegram, Google, Яндекс или Apple).',
    alert_geo: 'Укажите место рождения и подождите определения координат (кликните вне поля города).',
    alert_name_date: 'Заполните имя и дату рождения.',
    alert_order_ok: 'Заказ создан. Отчёт будет готов в ближайшее время — проверьте почту или личный кабинет.',
    alert_err: 'Ошибка:',
    aria_day: 'День',
    aria_month: 'Месяц',
    aria_year: 'Год',
  });


  // Pricing cards, reviews, FAQ, demo tables — large blocks appended below
  var EXTRA_RU = {
    pricing_free_name: 'Бесплатно',
    pricing_free_desc: 'Попробуй — и мы тебя не отпустим',
    pricing_free_meta: 'навсегда',
    pricing_free_f1: 'Схема натальной карты (SVG)',
    pricing_free_f2: 'Солнце, Луна, Асцендент — краткий разбор',
    pricing_free_f3: '1-страничный PDF на почту',
    pricing_free_f4: 'Личный кабинет (1 карта)',
    pricing_free_d1: 'Полный разбор планет',
    pricing_free_d2: 'Транзиты и прогнозы',
    pricing_free_btn: 'Начать бесплатно',
    pricing_badge_popular: 'Популярный',
    pricing_rep_name: 'Отчёт',
    pricing_rep_desc: 'Полная карта навсегда. Один раз — на всю жизнь',
    pricing_rep_meta: 'единоразово · без подписки',
    pricing_rep_f1: 'Всё из «Бесплатно»',
    pricing_rep_f2: 'Все планеты в 12 домах с интерпретацией',
    pricing_rep_f3: 'Аспекты: трины, квадратуры, оппозиции',
    pricing_rep_f4: 'Нодальная ось и кармические задачи',
    pricing_rep_f5: 'PDF 12–14 стр. · пожизненный доступ',
    pricing_rep_d1: 'Транзиты и прогнозы',
    pricing_rep_btn: 'Получить отчёт',
    pricing_bundle_name: 'Набор «3»',
    pricing_bundle_desc: 'Для семьи или в подарок. Экономия 33%',
    pricing_bundle_meta: '3 полных отчёта · <span class="pricing-meta-unit">530 ₽</span> за штуку',
    pricing_bundle_f1: '3 полных отчёта (разные люди)',
    pricing_bundle_f2: 'Все 3 карты в едином кабинете',
    pricing_bundle_f3: 'Режим подарка: красивая ссылка с открыткой',
    pricing_bundle_f4: 'Пожизненный доступ ко всем трём',
    pricing_bundle_d1: 'Транзиты и прогнозы',
    pricing_bundle_btn: 'Купить набор',
    pricing_sub_badge: 'Подписка',
    pricing_pro_desc: 'Живая астрология каждый месяц',
    pricing_pro_hint: '≈ 5 880 ₽/год при помесячной оплате',
    pricing_pro_sub: 'Отмена в любой момент',
    pricing_pro_f1: 'Полный отчёт включён',
    pricing_pro_f2: 'Транзиты + персональный календарь',
    pricing_pro_f3: 'Синастрия (совместимость)',
    pricing_pro_f4: 'Прогрессии на год',
    pricing_pro_f5: 'Обновление прогнозов каждый месяц',
    pricing_pro_f6: 'До 5 человек в одном кабинете',
    pricing_pro_btn: 'Попробовать Pro',
    review_1_name: 'Катя М., 29 лет',
    review_1_city: 'Москва · HR-менеджер · Стандарт',
    review_1_text: '«Читала PDF три раза. Раздел про Луну в Скорпионе в IV доме — будто кто-то поговорил с моей мамой и потом написал про наши отношения. Я серьёзно. Это не "Весам свойственна гармония" — это конкретно про меня. Немного страшно насколько точно.»',
    review_2_name: 'Виктор П., 36 лет',
    review_2_city: 'Новосибирск · Предприниматель · Полный+',
    review_2_text: '«Скептик. Покупал жене на день рождения, думал "ну пусть порадуется". В итоге сам прочитал всё. Раздел про Марс в Козероге в X доме объяснил, почему я могу работать 14 часов без устали, но терпеть не могу, когда кто-то ставит под сомнение мои решения. Это было неудобно осознавать.»',
    review_3_name: 'Алина Н., 24 года',
    review_3_city: 'Казань · Дизайнер · Стандарт',
    review_3_text: '«Понравилось, но ожидала немного другого. Хотелось больше про отношения, а раздел про партнёрство оказался довольно общим. Зато транзиты на год — огонь, особенно про Юпитер в Близнецах. Сразу стало понятно, почему этой весной я вдруг захотела сменить профессию. Буду продлевать.»',
    review_4_name: 'Таня С., 33 года',
    review_4_city: 'Екатеринбург · Психолог · Полный+',
    review_4_text: '«Я психолог и отношусь к астрологии как к проективной методике — способу говорить о себе через символы. С этой позицией PDF работает превосходно. Нодальная ось дала мне формулировки для паттернов, с которыми я работаю уже два года в терапии. Рекомендую коллегам как дополнительный инструмент.»',
    review_5_name: 'Роман Д., 41 год',
    review_5_city: 'СПб · Инженер · Стандарт',
    review_5_text: '«Взял исключительно ради интереса. Солнце в Рыбах в VIII доме — написано что "притяжение к теме смерти и трансформации, работа с кризисными ситуациями". Я 15 лет работаю в антикризисном менеджменте и сам смеялся. Жена говорит — плати им ещё, пусть продолжают.»',
    review_6_name: 'Марина Л., 27 лет',
    review_6_city: 'Краснодар · Маркетолог · Telegram',
    review_6_text: '«Зашла через Telegram-бот в 23:00 просто из любопытства. В 2 ночи всё ещё читала PDF. Меркурий ретроградный в I доме — вот почему я обдумываю каждое слово перед тем как заговорить, и потом жалею что не сказала. Это было откровение. Сразу отправила ссылку трём подругам.»',
    demo_pl1: '☉ Солнце',
    demo_pl1p: '25° Близнецы, Дом X',
    demo_pl1b: 'Власть · Карьера',
    demo_pl2: '☽ Луна',
    demo_pl2p: '14° Козерог, Дом IV',
    demo_pl2b: 'Дом · Структура',
    demo_pl3: '☿ Меркурий',
    demo_pl3p: '18° Близнецы, Дом X',
    demo_pl3b: 'Мышление · Речь',
    demo_pl4: '♀ Венера',
    demo_pl4p: '03° Лев, Дом XI',
    demo_pl4b: 'Творчество · Друзья',
    demo_pl5: '♂ Марс',
    demo_pl5p: '29° Телец, Дом IX',
    demo_pl5b: 'Воля · Путешествия',
    demo_pl6: '♃ Юпитер',
    demo_pl6p: '08° Рак, Дом X',
    demo_pl6b: 'Рост · Удача',
    demo_pl7: '♄ Сатурн',
    demo_pl7p: '22° Козерог, Дом IV',
    demo_pl7b: 'Испытания · Ответственность',
    demo_as1n: '☉ △ ♃',
    demo_as1p: 'Трин Солнце–Юпитер (орб 2°)',
    demo_as1b: 'Сильный',
    demo_as2n: '☽ □ ♀',
    demo_as2p: 'Квадратура Луна–Венера (орб 5°)',
    demo_as2b: 'Напряжение',
    demo_as3n: '☿ ✱ ♃',
    demo_as3p: 'Секстиль Меркурий–Юпитер (орб 1°)',
    demo_as3b: 'Интеллект',
    demo_as4n: '☉ ☍ ☽',
    demo_as4p: 'Оппозиция Солнце–Луна (орб 9°)',
    demo_as4b: 'Внутренний конфликт',
    demo_as5n: '♀ △ ♂',
    demo_as5p: 'Трин Венера–Марс (орб 4°)',
    demo_as5b: 'Гармония',
    demo_tr_head: 'Ключевые транзиты · 2025–2026',
    demo_tr1n: '♃ транзит',
    demo_tr1p: 'Юпитер через Дом I — март–ноябрь 2025',
    demo_tr1b: 'Рост личности',
    demo_tr2n: '♄ транзит',
    demo_tr2p: 'Сатурн ☐ натальное Солнце — янв–апр 2025',
    demo_tr2b: 'Испытание',
    demo_tr3n: '♅ транзит',
    demo_tr3p: 'Уран через Дом IX — 2025–2026',
    demo_tr3b: 'Перемены',
    demo_tr_foot: 'Полный календарь транзитов на год включён в тариф <strong style="color: var(--primary);">Полный+</strong>',
    demo_z1: '☉ Близнецы',
    demo_z2: '☽ Козерог',
    demo_z3: '↑ Дева',
    demo_z4: '☿ Меркурий',
    faq_q1: 'Нужно ли знать точное время рождения?',
    faq_a1: 'Желательно, но не обязательно. Если вы не знаете точного времени, укажите примерное — мы рассчитаем карту и добавим пометку о возможной погрешности по Асценденту. Большинство разбора при этом остаётся точным.',
    faq_q2: 'Чем натальная карта отличается от гороскопа?',
    faq_a2: 'Гороскоп — обобщённый прогноз для целого знака Зодиака, один из 12. Натальная карта уникальна для конкретного человека и учитывает точное время и место рождения. Два человека, рождённых в один день в разных городах и в разное время, получат совершенно разные карты.',
    faq_q3: 'Как долго действует карта и когда её нужно обновлять?',
    faq_a3: 'Натальная карта не меняется — она фиксирует момент рождения. Меняются транзиты: текущие положения планет, которые взаимодействуют с вашей картой. На тарифе Полный+ транзиты обновляются ежемесячно автоматически.',
    faq_q4: 'Могу ли я рассчитать карту для другого человека?',
    faq_a4: 'Да, на любом тарифе вы можете рассчитать карту для любого человека, зная его дату, время и место рождения. На тарифе Полный+ можно хранить карты до 3 человек в одном личном кабинете. В подписке Astro Pro — до 5 человек.',
    faq_q5: 'В каком формате и когда приходит отчёт?',
    faq_a5: 'PDF-отчёт отправляется на указанный email сразу после расчёта — в течение 60 секунд. Одновременно он сохраняется в вашем личном кабинете, где доступен в любое время.',
    faq_q6: 'Что делать, если PDF не пришёл на почту?',
    faq_a6: 'Сначала проверьте папку «Спам» или «Промоакции» — письмо могло попасть туда. Если не нашли, зайдите в личный кабинет — отчёт сохраняется там независимо от email. Если проблема не решилась, напишите нам на support@astrogen.ru — разберёмся в течение 2 часов.',
    faq_q7: 'Как отменить подписку?',
    faq_a7: 'Отмена в один клик в разделе «Подписка» личного кабинета. Подписка продолжает действовать до конца оплаченного периода. Деньги за оставшийся период не возвращаются, но вы можете пользоваться всеми функциями до истечения срока.',
    faq_q8: 'Работает ли сервис через Telegram?',
    faq_a8: 'Да, у нас есть Telegram Mini App с полным функционалом: ввод данных, расчёт карты, оплата и личный кабинет — всё внутри Telegram. Авторизация происходит автоматически через ваш аккаунт.',
    faq_q10: 'Как с вами связаться по вопросам оплаты или технической проблеме?',
    faq_a10: 'Напишите на support@astrogen.ru — отвечаем в течение 2 рабочих часов. Или через форму обратной связи ниже на этой странице. В Telegram: @astrogen_support. Укажите email, с которым регистрировались — это ускорит решение.',
    faq_q11: 'Планируются ли другие астрологические продукты?',
    faq_a11: 'Да. Astrogen развивается как платформа персональной астрологии. В планах: синастрия (совместимость пар), персональные гороскопы, прогрессии и астрологические прогнозы на год. Все продукты будут доступны в одном личном кабинете.',
  };


  merge('ru', EXTRA_RU);

  function getLang() {
    try {
      var stored = localStorage.getItem('astrogen_lang');
      if (stored === 'en' || stored === 'ru') return stored;
    } catch (e) {}
    var l = document.documentElement.getAttribute('lang') || 'ru';
    return String(l).toLowerCase().indexOf('en') === 0 ? 'en' : 'ru';
  }

  function t(key, vars) {
    var lang = getLang();
    var s = (BUNDLE[lang] && BUNDLE[lang][key]) || (BUNDLE.ru && BUNDLE.ru[key]) || key;
    if (vars && typeof s === 'string') {
      Object.keys(vars).forEach(function (k) {
        s = s.split('{' + k + '}').join(vars[k]);
      });
    }
    return s;
  }

  function applyMeta(lang) {
    var T = BUNDLE[lang] || BUNDLE.ru;
    var titleEl = document.querySelector('title');
    if (titleEl && T.meta_title) titleEl.textContent = T.meta_title;
    var md = document.querySelector('meta[name="description"]');
    if (md && T.meta_description) md.setAttribute('content', T.meta_description);
    var ogT = document.querySelector('meta[property="og:title"]');
    if (ogT && T.meta_og_title) ogT.setAttribute('content', T.meta_og_title);
    var ogD = document.querySelector('meta[property="og:description"]');
    if (ogD && T.meta_og_description) ogD.setAttribute('content', T.meta_og_description);
  }

  function applyAstrogenLandingLang(lang, done) {
    if (lang !== 'en' && lang !== 'ru') lang = 'ru';
    if (lang === 'en' && !global.__astrogenEnBundleLoaded) {
      global.__astrogenEnBundleLoadedCallback = function () {
        applyAstrogenLandingLang('en', done);
      };
      if (!global.__astrogenEnScriptRequested) {
        global.__astrogenEnScriptRequested = true;
        var s = document.createElement('script');
        s.src = '/static/js/landing-i18n-en.js';
        s.async = true;
        s.onerror = function () {
          global.__astrogenEnScriptRequested = false;
          if (typeof done === 'function') done();
        };
        document.head.appendChild(s);
      }
      return;
    }

    document.documentElement.setAttribute('lang', lang === 'en' ? 'en' : 'ru');
    var T = BUNDLE[lang] || BUNDLE.ru;
    applyMeta(lang);

    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      var key = el.getAttribute('data-i18n');
      if (!key || !T[key]) return;
      el.textContent = T[key];
    });

    document.querySelectorAll('[data-i18n-html]').forEach(function (el) {
      var key = el.getAttribute('data-i18n-html');
      if (!key || !T[key]) return;
      el.innerHTML = T[key];
    });

    document.querySelectorAll('[data-i18n-placeholder]').forEach(function (el) {
      var key = el.getAttribute('data-i18n-placeholder');
      if (!key || !T[key]) return;
      el.setAttribute('placeholder', T[key]);
    });

    document.querySelectorAll('[data-i18n-title]').forEach(function (el) {
      var key = el.getAttribute('data-i18n-title');
      if (!key || !T[key]) return;
      el.setAttribute('title', T[key]);
    });

    document.querySelectorAll('[data-i18n-aria-label]').forEach(function (el) {
      var key = el.getAttribute('data-i18n-aria-label');
      if (!key || !T[key]) return;
      el.setAttribute('aria-label', T[key]);
    });

    document.querySelectorAll('[data-i18n-stat-suffix]').forEach(function (el) {
      var key = el.getAttribute('data-i18n-stat-suffix');
      if (!key || !T[key]) return;
      el.setAttribute('data-suffix', T[key]);
    });

    if (typeof global.astrogenBirthDateLocaleApplyLang === 'function') {
      global.astrogenBirthDateLocaleApplyLang();
    }

    if (typeof done === 'function') done();
  }

  global.ASTROGEN_L10N_BUNDLE = BUNDLE;
  global.getAstrogenLang = getLang;
  global.tAstrogen = t;
  global.applyAstrogenLandingLang = applyAstrogenLandingLang;
})(window);
