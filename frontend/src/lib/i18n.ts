import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

const resources = {
  ru: {
    translation: {
      appName: 'AstroGen',
      nav: {
        home: 'Главная',
        dashboard: 'Кабинет',
        tryFree: 'Попробовать бесплатно',
        login: 'Войти',
        tariff: 'Тарифы',
        order: 'Заказ',
      },
      common: {
        loading: 'Загрузка…',
        save: 'Сохранить',
        cancel: 'Отмена',
        delete: 'Удалить',
        edit: 'Редактировать',
        continue: 'Продолжить',
        back: 'Назад',
        download: 'Скачать',
        error: 'Ошибка',
      },
      dashboard: {
        profile: 'Профиль',
        natal: 'Мои данные рождения',
        orders: 'Мои заказы',
        logout: 'Выйти',
      },
      profile: {
        title: 'Профиль',
        email: 'Email',
        consent: 'Согласие на обработку персональных данных',
        export: 'Экспорт моих данных',
        deleteAccount: 'Удалить аккаунт',
        deleteConfirm: 'Удалить аккаунт безвозвратно?',
      },
      orders: {
        title: 'Заказы',
        status: 'Статус',
        amount: 'Сумма',
        tariff: 'Тариф',
        report: 'Отчёт',
        openReport: 'Скачать отчёт',
      },
      order: {
        stepTariff: 'Тариф',
        stepData: 'Данные',
        stepConfirm: 'Оплата',
        selectTariff: 'Выберите тариф',
        pay: 'Перейти к оплате',
        statusTitle: 'Статус оплаты',
        paidHint: 'Отчёт будет отправлен на вашу почту. Также он доступен в личном кабинете.',
        loginToContinue: 'Чтобы открыть «{{place}}», войдите в аккаунт.',
      },
      reports: {
        title: 'Отчёт',
        pdf: 'Скачать PDF',
        png: 'Скачать карту (PNG)',
      },
    },
  },
  en: {
    translation: {
      appName: 'AstroGen',
      nav: {
        home: 'Home',
        dashboard: 'Dashboard',
        tryFree: 'Try for free',
        login: 'Sign in',
        tariff: 'Pricing',
        order: 'Order',
      },
      common: {
        loading: 'Loading…',
        save: 'Save',
        cancel: 'Cancel',
        delete: 'Delete',
        edit: 'Edit',
        continue: 'Continue',
        back: 'Back',
        download: 'Download',
        error: 'Error',
      },
      dashboard: {
        profile: 'Profile',
        natal: 'Birth data',
        orders: 'Orders',
        logout: 'Log out',
      },
      profile: {
        title: 'Profile',
        email: 'Email',
        consent: 'Consent to personal data processing',
        export: 'Export my data',
        deleteAccount: 'Delete account',
        deleteConfirm: 'Permanently delete your account?',
      },
      orders: {
        title: 'Orders',
        status: 'Status',
        amount: 'Amount',
        tariff: 'Tariff',
        report: 'Report',
        openReport: 'Download report',
      },
      order: {
        stepTariff: 'Plan',
        stepData: 'Data',
        stepConfirm: 'Payment',
        selectTariff: 'Choose a plan',
        pay: 'Pay',
        statusTitle: 'Payment status',
        paidHint: 'The report will be emailed to you. It is also available in your account.',
        loginToContinue: 'Sign in to open «{{place}}».',
      },
      reports: {
        title: 'Report',
        pdf: 'Download PDF',
        png: 'Download chart (PNG)',
      },
    },
  },
}

void i18n.use(initReactI18next).init({
  resources,
  lng: 'ru',
  fallbackLng: 'ru',
  interpolation: { escapeValue: false },
})

export default i18n
