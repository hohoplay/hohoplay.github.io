// ===================================
// MONICA LEE HAIR ACADEMY — Main JS
// ===================================

document.addEventListener('DOMContentLoaded', function () {

  // Mobile hamburger menu
  const hamburger = document.querySelector('.nav-hamburger');
  const mobileMenu = document.querySelector('.mobile-menu');
  if (hamburger && mobileMenu) {
    hamburger.addEventListener('click', function () {
      hamburger.classList.toggle('open');
      mobileMenu.classList.toggle('open');
    });
    // Close menu after clicking a link
    mobileMenu.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        hamburger.classList.remove('open');
        mobileMenu.classList.remove('open');
      });
    });
  }

  // Curriculum toggle (accordion)
  document.querySelectorAll('.curriculum-toggle-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const wrap = btn.nextElementSibling;
      btn.classList.toggle('open');
      wrap.classList.toggle('open');
    });
  });

  // Subtab toggle (Program 1: male/female)
  document.querySelectorAll('.subtab-wrap').forEach(function (wrap) {
    const buttons = wrap.querySelectorAll('.subtab-btn');
    buttons.forEach(function (btn) {
      btn.addEventListener('click', function () {
        const target = btn.getAttribute('data-subtab');
        buttons.forEach(function (b) { b.classList.toggle('active', b === btn); });
        wrap.querySelectorAll('.subtab-panel').forEach(function (panel) {
          panel.classList.toggle('active', panel.getAttribute('data-panel') === target);
        });
      });
    });
  });

  // Mobile program tabs (1:1 / 3:1 toggle, mobile only)
  const progMobileTabs = document.querySelectorAll('.prog-mobile-tab');
  const programCards = document.querySelectorAll('.program-card');

  function activateProgramCard(targetId) {
    progMobileTabs.forEach(function (t) {
      t.classList.toggle('active', t.getAttribute('data-progtab') === targetId);
    });
    programCards.forEach(function (card) {
      card.classList.toggle('mobile-active', card.id === targetId);
    });
  }

  if (progMobileTabs.length && programCards.length) {
    // Set initial state: first card active
    programCards.forEach(function (card, i) {
      card.classList.toggle('mobile-active', i === 0);
    });
    progMobileTabs.forEach(function (tab) {
      tab.addEventListener('click', function () {
        const targetId = tab.getAttribute('data-progtab');
        activateProgramCard(targetId);
        const target = document.getElementById(targetId);
        if (target && window.innerWidth <= 768) {
          target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });
    });

    // Hero panel links (#program-1 / #program-2) also sync the mobile tab
    document.querySelectorAll('a[href="#program-1"], a[href="#program-2"]').forEach(function (link) {
      link.addEventListener('click', function () {
        const targetId = link.getAttribute('href').replace('#', '');
        activateProgramCard(targetId);
      });
    });
  }

  // Scroll-to-top button
  const scrollTopBtn = document.querySelector('.scroll-top');
  if (scrollTopBtn) {
    window.addEventListener('scroll', function () {
      scrollTopBtn.classList.toggle('visible', window.scrollY > 600);
    });
    scrollTopBtn.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // Contact form submit (mailto fallback)
  const contactForm = document.querySelector('.contact-form');
  if (contactForm) {
    contactForm.addEventListener('submit', function (e) {
      e.preventDefault();
      const name = contactForm.querySelector('[name="name"]').value;
      const phone = contactForm.querySelector('[name="phone"]').value;
      const program = contactForm.querySelector('[name="program"]').value;
      const message = contactForm.querySelector('[name="message"]').value;

      const subject = encodeURIComponent('[모니카리 헤어아카데미] 상담 신청 - ' + name);
      const body = encodeURIComponent(
        '이름: ' + name + '\n' +
        '연락처: ' + phone + '\n' +
        '관심 프로그램: ' + program + '\n\n' +
        '문의 내용:\n' + message
      );
      window.location.href = 'mailto:monicahairacademy@naver.com?subject=' + subject + '&body=' + body;
    });
  }
});
