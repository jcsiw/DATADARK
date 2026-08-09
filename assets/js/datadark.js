/* =========================================================
   DATADARK Tecnologia — Bootstrap 1.0
   JavaScript institucional sem dependências externas
   ========================================================= */

(() => {
  'use strict';

  const CONFIG = {
    analyticsId: 'G-0Z3B9DR2VX',
    analyticsConsentKey: 'datadark_analytics_consent'
  };

  const header = document.querySelector('.site-header');
  const navToggle = document.getElementById('navToggle');
  const mainNav = document.getElementById('mainNav');

  // -------------------------------------------------------
  // Menu responsivo
  // -------------------------------------------------------
  function setMenu(open) {
    if (!navToggle || !mainNav) return;

    mainNav.classList.toggle('is-open', open);
    navToggle.setAttribute('aria-expanded', String(open));
    navToggle.setAttribute('aria-label', open ? 'Fechar menu' : 'Abrir menu');
  }

  navToggle?.addEventListener('click', () => {
    setMenu(!mainNav.classList.contains('is-open'));
  });

  mainNav?.querySelectorAll('a[href^="#"]').forEach((link) => {
    link.addEventListener('click', () => setMenu(false));
  });

  window.addEventListener('resize', () => {
    if (window.innerWidth >= 1200) setMenu(false);
  });

  // -------------------------------------------------------
  // Estado visual do menu ao rolar
  // -------------------------------------------------------
  function updateHeader() {
    header?.classList.toggle('is-scrolled', window.scrollY > 20);
  }

  updateHeader();
  window.addEventListener('scroll', updateHeader, { passive: true });

  // -------------------------------------------------------
  // Destaque da seção atual no menu
  // -------------------------------------------------------
  const navLinks = [...document.querySelectorAll('.navbar .nav-link[href^="#"]')];
  const observedSections = navLinks
    .map((link) => document.querySelector(link.getAttribute('href')))
    .filter(Boolean);

  if ('IntersectionObserver' in window && observedSections.length) {
    const observer = new IntersectionObserver((entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];

      if (!visible) return;

      navLinks.forEach((link) => {
        const active = link.getAttribute('href') === `#${visible.target.id}`;
        link.classList.toggle('active', active);
        if (active) link.setAttribute('aria-current', 'page');
        else link.removeAttribute('aria-current');
      });
    }, {
      rootMargin: '-25% 0px -60% 0px',
      threshold: [0.05, 0.2, 0.5]
    });

    observedSections.forEach((section) => observer.observe(section));
  }

  // -------------------------------------------------------
  // Formulário: envio assíncrono pelo Formspree
  // O action/method do HTML funcionam como fallback sem JS.
  // -------------------------------------------------------
  const contactForm = document.getElementById('contactForm');
  const contactSubmit = document.getElementById('contactSubmit');
  const formStatus = document.getElementById('formStatus');

  function setFormStatus(message, type = '') {
    if (!formStatus) return;
    formStatus.textContent = message;
    formStatus.className = `form-status mt-3${type ? ` is-${type}` : ''}`;
    formStatus.hidden = !message;
  }

  contactForm?.addEventListener('submit', async (event) => {
    event.preventDefault();

    if (!contactForm.checkValidity()) {
      contactForm.classList.add('was-validated');
      setFormStatus('Revise os campos destacados antes de enviar.', 'error');
      return;
    }

    contactForm.classList.remove('was-validated');
    setFormStatus('');

    const originalLabel = contactSubmit?.textContent || 'Enviar mensagem';
    if (contactSubmit) {
      contactSubmit.disabled = true;
      contactSubmit.textContent = 'Enviando...';
      contactSubmit.setAttribute('aria-busy', 'true');
    }

    try {
      const response = await fetch(contactForm.action, {
        method: contactForm.method,
        body: new FormData(contactForm),
        headers: {
          Accept: 'application/json'
        }
      });

      if (response.ok) {
        contactForm.reset();
        setFormStatus('Mensagem enviada com sucesso. A DATADARK entrará em contato assim que possível.', 'success');
        return;
      }

      let message = 'Não foi possível enviar a mensagem. Tente novamente em alguns instantes.';

      if (response.status === 429) {
        message = 'Foram realizadas muitas tentativas em pouco tempo. Aguarde alguns minutos e tente novamente.';
      } else {
        try {
          const data = await response.json();
          if (Array.isArray(data?.errors) && data.errors.length) {
            message = data.errors.map((item) => item.message).filter(Boolean).join(' ') || message;
          }
        } catch (_) {
          // Mantém a mensagem genérica quando a resposta não for JSON.
        }
      }

      setFormStatus(message, 'error');
    } catch (_) {
      setFormStatus('Falha de conexão ao enviar. Verifique sua internet e tente novamente.', 'error');
    } finally {
      if (contactSubmit) {
        contactSubmit.disabled = false;
        contactSubmit.textContent = originalLabel;
        contactSubmit.removeAttribute('aria-busy');
      }
    }
  });

  // -------------------------------------------------------
  // Ano do rodapé
  // -------------------------------------------------------
  const year = document.getElementById('currentYear');
  if (year) year.textContent = String(new Date().getFullYear());

  // -------------------------------------------------------
  // Analytics com consentimento
  // -------------------------------------------------------
  const cookieBanner = document.getElementById('cookieBanner');
  const acceptCookies = document.getElementById('acceptCookies');
  const rejectCookies = document.getElementById('rejectCookies');
  let analyticsLoaded = false;

  function isProductionHost() {
    return /(^|\.)datadark\.com\.br$/i.test(window.location.hostname);
  }

  function loadAnalytics() {
    if (analyticsLoaded || !isProductionHost()) return;
    analyticsLoaded = true;

    window.dataLayer = window.dataLayer || [];
    window.gtag = function gtag() {
      window.dataLayer.push(arguments);
    };

    window.gtag('js', new Date());
    window.gtag('config', CONFIG.analyticsId, { anonymize_ip: true });

    const script = document.createElement('script');
    script.async = true;
    script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(CONFIG.analyticsId)}`;
    document.head.appendChild(script);
  }

  function saveConsent(value) {
    try {
      localStorage.setItem(CONFIG.analyticsConsentKey, value);
    } catch (_) {
      // O site continua funcional mesmo se o navegador bloquear localStorage.
    }
  }

  function getConsent() {
    try {
      return localStorage.getItem(CONFIG.analyticsConsentKey);
    } catch (_) {
      return null;
    }
  }

  const consent = getConsent();

  if (consent === 'accepted') {
    loadAnalytics();
  } else if (consent !== 'rejected' && cookieBanner) {
    cookieBanner.hidden = false;
  }

  acceptCookies?.addEventListener('click', () => {
    saveConsent('accepted');
    if (cookieBanner) cookieBanner.hidden = true;
    loadAnalytics();
  });

  rejectCookies?.addEventListener('click', () => {
    saveConsent('rejected');
    if (cookieBanner) cookieBanner.hidden = true;
  });
})();
