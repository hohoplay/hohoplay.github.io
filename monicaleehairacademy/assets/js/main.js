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

  // Partner tabs (가맹점 / 제휴 toggle)
  const partnerTabs = document.querySelectorAll('.partner-tab');
  const partnerPanels = document.querySelectorAll('.partner-tabpanel');
  if (partnerTabs.length && partnerPanels.length) {
    partnerTabs.forEach(function (tab) {
      tab.addEventListener('click', function () {
        const target = tab.getAttribute('data-partnertab');
        partnerTabs.forEach(function (t) { t.classList.toggle('active', t === tab); });
        partnerPanels.forEach(function (panel) {
          panel.classList.toggle('active', panel.getAttribute('data-partnerpanel') === target);
        });
      });
    });
  }

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

  // Gallery pagination (groups items by data-page; auto-hides if only 1 page)
  const ITEMS_PER_PAGE = 4;
  const galleryGrid = document.querySelector('.gallery-grid');
  const galleryPagination = document.getElementById('galleryPagination');
  const galleryPageNumbers = document.getElementById('galleryPageNumbers');
  let currentGalleryPage = 1;

  function initGalleryPagination() {
    if (!galleryGrid) return;
    const allItems = Array.from(galleryGrid.querySelectorAll('.gallery-item'));
    if (!allItems.length) return;

    // If items don't have explicit data-page, auto-assign based on position
    allItems.forEach(function (item, i) {
      if (!item.hasAttribute('data-page')) {
        item.setAttribute('data-page', String(Math.floor(i / ITEMS_PER_PAGE) + 1));
      }
    });

    const pageNumbers = Array.from(new Set(allItems.map(function (item) {
      return parseInt(item.getAttribute('data-page'), 10);
    }))).sort(function (a, b) { return a - b; });

    const totalPages = pageNumbers.length;

    if (totalPages <= 1) {
      if (galleryPagination) galleryPagination.classList.remove('active');
      return;
    }

    if (galleryPagination) galleryPagination.classList.add('active');

    function renderPageNumbers() {
      if (!galleryPageNumbers) return;
      galleryPageNumbers.innerHTML = '';
      pageNumbers.forEach(function (p) {
        const btn = document.createElement('button');
        btn.className = 'gallery-page-btn' + (p === currentGalleryPage ? ' active' : '');
        btn.textContent = p;
        btn.addEventListener('click', function () { goToGalleryPage(p); });
        galleryPageNumbers.appendChild(btn);
      });
    }

    function updateArrowStates() {
      const prevBtn = galleryPagination.querySelector('[data-direction="prev"]');
      const nextBtn = galleryPagination.querySelector('[data-direction="next"]');
      if (prevBtn) prevBtn.disabled = currentGalleryPage === pageNumbers[0];
      if (nextBtn) nextBtn.disabled = currentGalleryPage === pageNumbers[pageNumbers.length - 1];
    }

    function goToGalleryPage(p) {
      currentGalleryPage = p;
      allItems.forEach(function (item) {
        const itemPage = parseInt(item.getAttribute('data-page'), 10);
        item.style.display = itemPage === p ? '' : 'none';
      });
      renderPageNumbers();
      updateArrowStates();
    }

    galleryPagination.querySelectorAll('.gallery-page-arrow').forEach(function (arrow) {
      arrow.addEventListener('click', function () {
        const dir = arrow.getAttribute('data-direction');
        const idx = pageNumbers.indexOf(currentGalleryPage);
        if (dir === 'prev' && idx > 0) goToGalleryPage(pageNumbers[idx - 1]);
        if (dir === 'next' && idx < pageNumbers.length - 1) goToGalleryPage(pageNumbers[idx + 1]);
      });
    });

    goToGalleryPage(pageNumbers[0]);
  }
  initGalleryPagination();

  // Gallery lightbox (click to expand, X / outside click / ESC to close)
  const lightbox = document.getElementById('lightbox');
  const lightboxImg = document.getElementById('lightboxImg');
  const lightboxClose = document.querySelector('.lightbox-close');
  const galleryItems = document.querySelectorAll('.gallery-item');

  function openLightbox(src, pos) {
    lightboxImg.src = src;
    lightboxImg.style.objectPosition = pos || 'center';
    lightbox.classList.add('open');
    document.body.classList.add('lightbox-active');
    document.body.style.overflow = 'hidden';
  }
  function closeLightbox() {
    lightbox.classList.remove('open');
    document.body.classList.remove('lightbox-active');
    document.body.style.overflow = '';
  }

  galleryItems.forEach(function (item) {
    item.addEventListener('click', function () {
      const src = item.getAttribute('data-lightbox-src');
      const pos = item.getAttribute('data-lightbox-pos');
      if (src) openLightbox(src, pos);
    });
  });

  if (lightboxClose) lightboxClose.addEventListener('click', closeLightbox);
  if (lightbox) {
    lightbox.addEventListener('click', function (e) {
      if (e.target === lightbox) closeLightbox();
    });
  }
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && lightbox && lightbox.classList.contains('open')) closeLightbox();
  });

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
