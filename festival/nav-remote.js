/* 이동 리모컨 — 긴 목록 페이지에서 아래로 내려가도 "지도"·"홈"으로 바로 나갈 수 있게 화면 오른쪽 아래에 띄운다.
   - 조금 스크롤한 뒤에 나타난다(맨 위에는 원래 있는 "← 지도로 돌아가기 / 홈" 줄이 보이므로).
   - 팝업(iframe) 안에서는 만들지 않는다(팝업에는 닫기 버튼이 있다). 실패해도 페이지는 그대로 동작한다. */
(function () {
  'use strict';
  try { if (window.self !== window.top) return; } catch (e) { return; }
  if (document.getElementById('nav-remote')) return;

  function init() {
    var css = document.createElement('style');
    css.textContent =
      '#nav-remote{position:fixed;right:12px;bottom:16px;bottom:calc(16px + env(safe-area-inset-bottom,0px));z-index:8900;display:flex;flex-direction:column;gap:8px;opacity:0;pointer-events:none;transform:translateY(8px);transition:opacity .2s ease,transform .2s ease}' +
      '#nav-remote.show{opacity:1;pointer-events:auto;transform:none}' +
      '#nav-remote a{display:flex;align-items:center;justify-content:center;gap:5px;min-width:76px;height:44px;padding:0 14px;border-radius:9999px;background:#111827;color:#fff;font-size:14px;font-weight:800;text-decoration:none;box-shadow:0 4px 14px rgba(0,0,0,.25)}' +
      '#nav-remote a.nr-map{background:#4f46e5}' +
      '#nav-remote a:focus-visible{outline:3px solid #93c5fd;outline-offset:2px}';
    document.head.appendChild(css);

    var box = document.createElement('div');
    box.id = 'nav-remote';
    box.setAttribute('role', 'navigation');
    box.setAttribute('aria-label', '지도·홈 이동');
    var map = document.createElement('a');
    map.className = 'nr-map';
    map.href = '/festival/';
    map.textContent = '🗺️ 지도';
    var home = document.createElement('a');
    home.href = '/';
    home.textContent = '🏠 홈';
    box.appendChild(map);
    box.appendChild(home);
    document.body.appendChild(box);

    var tick = false;
    function update() { box.classList.toggle('show', (window.pageYOffset || document.documentElement.scrollTop) > 300); }
    window.addEventListener('scroll', function () {
      if (tick) return;
      tick = true;
      requestAnimationFrame(function () { tick = false; update(); });
    }, { passive: true });
    update();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
