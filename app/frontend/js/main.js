(function () {
  'use strict';

  // ——— Cursor glow ———
  var cursorGlow = document.getElementById('cursorGlow');
  if (cursorGlow) {
    document.addEventListener('mousemove', function (e) {
      cursorGlow.style.left = e.clientX + 'px';
      cursorGlow.style.top = e.clientY + 'px';
    });
  }

  // ——— Header scroll ———
  var header = document.getElementById('header');
  function onScroll() {
    if (window.scrollY > 50) header.classList.add('scrolled');
    else header.classList.remove('scrolled');
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  // ——— Scroll-triggered animations ———
  var observerOptions = {
    root: null,
    rootMargin: '0px 0px -80px 0px',
    threshold: 0.1
  };
  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      var el = entry.target;
      var delay = el.getAttribute('data-delay');
      if (delay) {
        setTimeout(function () {
          el.classList.add('visible');
        }, parseInt(delay, 10));
      } else {
        el.classList.add('visible');
      }
    });
  }, observerOptions);

  document.querySelectorAll('.animate-on-scroll').forEach(function (el) {
    observer.observe(el);
  });

  // ——— CTA section animations trigger ———
  var ctaSection = document.querySelector('.cta');
  if (ctaSection) {
    var ctaObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          var ctaContent = entry.target.querySelector('.cta-content');
          var ctaPhone = entry.target.querySelector('.cta-phone');
          if (ctaContent) {
            ctaContent.classList.add('visible');
          }
          if (ctaPhone) {
            ctaPhone.classList.add('visible');
          }
        }
      });
    }, { threshold: 0.2 });
    ctaObserver.observe(ctaSection);
  }

  // ——— Stats counter ———
  var statValues = document.querySelectorAll('.stat-value');
  var statsObserved = false;
  var statsObserver = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting || statsObserved) return;
      statsObserved = true;
      statValues.forEach(function (stat) {
        var target = parseInt(stat.getAttribute('data-target'), 10);
        var duration = 2000;
        var step = target / (duration / 16);
        var current = 0;
        var timer = setInterval(function () {
          current += step;
          if (current >= target) {
            stat.textContent = target;
            clearInterval(timer);
          } else {
            stat.textContent = Math.floor(current);
          }
        }, 16);
      });
    });
  }, { threshold: 0.3 });
  var statsSection = document.querySelector('.stats');
  if (statsSection) statsObserver.observe(statsSection);

  // ——— FAQ accordion ———
  document.querySelectorAll('.faq-item').forEach(function (item) {
    var btn = item.querySelector('.faq-question');
    var answer = item.querySelector('.faq-answer');
    if (!btn || !answer) return;
    btn.addEventListener('click', function () {
      var isOpen = item.getAttribute('aria-expanded') === 'true';
      document.querySelectorAll('.faq-item').forEach(function (other) {
        other.setAttribute('aria-expanded', 'false');
      });
      if (!isOpen) {
        item.setAttribute('aria-expanded', 'true');
      }
    });
  });

  // ——— Mobile nav toggle ———
  var navToggle = document.getElementById('navToggle');
  var nav = document.querySelector('.nav');
  if (navToggle && nav) {
    navToggle.addEventListener('click', function () {
      navToggle.classList.toggle('open');
      nav.classList.toggle('open');
      document.body.classList.toggle('nav-open', nav.classList.contains('open'));
    });
  }

  // ——— Smooth scroll for anchor links ———
  document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
    anchor.addEventListener('click', function (e) {
      var id = this.getAttribute('href');
      if (id === '#') return;
      var target = document.querySelector(id);
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        if (nav && nav.classList.contains('open')) {
          nav.classList.remove('open');
          navToggle.classList.remove('open');
          document.body.classList.remove('nav-open');
        }
      }
    });
  });
})();
