/* 목차 리모컨 — 상세페이지·코스 글에서 화면 왼쪽 아래에 떠 있는 "목차" 버튼.
   페이지의 h2 소제목으로 목록을 만들고, 누르면 그 자리로 부드럽게 이동한다. 본문 목차 박스는 그대로 두고 추가로 쓰인다.
   - 소제목이 3개 미만인 페이지에서는 만들지 않는다. 팝업(iframe) 안에서는 일정표 버튼 위에 띄운다.
   - 실패해도 페이지는 그대로 동작한다(스크립트가 없어도 본문 목차가 남는다). */
(function () {
  'use strict';
  // 지도·홈에서 열리는 팝업(iframe) 안에서도 쓴다. 팝업 왼쪽 아래의 "이 장소로 일정표" 버튼(높이 52px) 바로 위로 올려 겹치지 않게 한다.
  var embedded = false;
  try { embedded = window.self !== window.top; } catch (e) { embedded = true; }
  // [ADD] 2026-11-28: 장소 상세페이지는 위에서부터 핵심 정보(기본 정보·운영시간)가 먼저 보이게 한다.
  //   - 본문 목차 박스는 접어 둔다(제목만 보이고, 눌러서 펼치거나 아래 "목차" 버튼을 쓴다).
  //   - 사진이 없어 "사진 준비 중" 일러스트가 들어간 곳은 그림을 작게 줄인다(실제 사진은 그대로 둔다).
  try {
    if (location.pathname.indexOf('/festival/detail/') === 0) {
      var tocBox = document.querySelector('details.pt-toc');
      if (tocBox) tocBox.removeAttribute('open');
      var phs = document.querySelectorAll('img.detail-image');
      for (var k = 0; k < phs.length; k++) {
        if ((phs[k].getAttribute('src') || '').indexOf('/data/placeholders/') === 0) {
          phs[k].style.maxWidth = '170px';
          phs[k].style.marginBottom = '14px';
        }
      }
    }
  } catch (e) { /* 실패해도 페이지는 그대로 보인다 */ }
  // [ADD] 2026-11-28: 검색결과(구글·네이버·다음·빙)를 눌러 장소 상세페이지로 들어온 방문자는 지도 페이지 위 바텀시트로 보여 준다.
  //   - 검색 로봇은 클릭 출처(referrer)가 없어서 이 이동을 하지 않는다. 주소를 직접 입력하거나 다른 곳에서 들어온 경우도 그대로 상세 페이지가 열린다.
  //   - 끄려면 아래 SHEET_FROM_SEARCH 를 false 로 바꾼다. 주소 끝에 ?nosheet 를 붙여도 이동하지 않는다.
  var SHEET_FROM_SEARCH = true;
  try {
    if (SHEET_FROM_SEARCH && !embedded && /^\/festival\/detail\/[^\/?#]+\.html$/.test(location.pathname) &&
        location.search.indexOf('nosheet') < 0 && document.referrer) {
      var rh = '';
      try { rh = new URL(document.referrer).hostname; } catch (e) { rh = ''; }
      var navT = (performance.getEntriesByType && performance.getEntriesByType('navigation')[0]) || null;
      if (/(^|\.)(google\.[a-z.]+|naver\.com|daum\.net|bing\.com)$/.test(rh) && (!navT || navT.type === 'navigate')) {
        document.documentElement.style.visibility = 'hidden';
        window.setTimeout(function () { document.documentElement.style.visibility = ''; }, 2500);
        location.replace('/festival/?hpsheet=' + encodeURIComponent(location.pathname));
        return;
      }
    }
  } catch (e) { document.documentElement.style.visibility = ''; }
  // [ADD] 2026-11-28: 구글 검색결과에서 들어오면 구글이 "검색된 문장" 위치로 페이지를 내려서 열어 준다(주소 뒤 #:~:text=).
  //   그러면 제목·소개가 가려진 채 중간부터 보이므로, 사용자가 아직 스크롤하지 않았다면 맨 위로 되돌린다.
  //   뒤로 가기·새로고침(이전 스크롤 위치 복원)과 #소제목 주소로 들어온 경우, 팝업(iframe) 안에서는 건드리지 않는다. // force-top
  try {
    if (!embedded && location.pathname.indexOf('/festival/detail/') === 0 && !location.hash) {
      var navE = (performance.getEntriesByType && performance.getEntriesByType('navigation')[0]) || null;
      if (!navE || navE.type === 'navigate') {
        var touched = false;
        ['wheel', 'touchstart', 'touchmove', 'keydown', 'mousedown', 'pointerdown'].forEach(function (ev) {
          window.addEventListener(ev, function () { touched = true; }, { passive: true, once: true });
        });
        var toTop = function () {
          if (!touched && (window.pageYOffset || document.documentElement.scrollTop) > 0) {
            try { window.scrollTo({ top: 0, left: 0, behavior: 'instant' }); } catch (e) { window.scrollTo(0, 0); }
          }
        };
        toTop();
        if (document.readyState !== 'complete') window.addEventListener('load', toTop);
        [120, 400, 900, 1800].forEach(function (ms) { setTimeout(toTop, ms); });
      }
    }
  } catch (e) { /* 실패해도 페이지는 그대로 보인다 */ }
  if (document.getElementById('toc-remote')) return;

  function init() {
    var nodes = document.querySelectorAll('h2');
    var heads = [];
    for (var i = 0; i < nodes.length; i++) {
      var h = nodes[i];
      if (h.closest('nav, header, footer, aside, #hoho-footer, .pt-toc, [data-no-toc]')) continue;
      var t = (h.textContent || '').replace(/\s+/g, ' ').trim();
      if (!t || h.offsetParent === null) continue;
      heads.push({ el: h, text: t });
    }
    if (heads.length < 3) return;

    var css = document.createElement('style');
    css.textContent =
      '#toc-remote{position:fixed;left:12px;bottom:16px;z-index:9000;font-family:inherit}' +
      '#toc-remote.emb{left:16px;bottom:80px;bottom:calc(80px + env(safe-area-inset-bottom,0px))}' +
      '#toc-remote .tr-btn{display:flex;align-items:center;gap:6px;border:0;border-radius:9999px;padding:10px 16px;background:#4f46e5;color:#fff;font-size:14px;font-weight:800;box-shadow:0 4px 14px rgba(0,0,0,.25);cursor:pointer}' +
      '#toc-remote .tr-panel{display:none;position:absolute;left:0;bottom:52px;width:min(86vw,320px);max-height:60vh;overflow-y:auto;background:#fff;border:1px solid #e2e8f0;border-radius:14px;box-shadow:0 8px 28px rgba(0,0,0,.22);padding:8px}' +
      '#toc-remote.open .tr-panel{display:block}' +
      '#toc-remote .tr-title{margin:4px 8px 6px;font-size:12px;font-weight:800;color:#64748b}' +
      '#toc-remote .tr-panel a{display:block;padding:9px 10px;border-radius:9px;font-size:14px;line-height:1.4;font-weight:600;color:#1e293b;text-decoration:none;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}' +
      '#toc-remote .tr-panel a:hover,#toc-remote .tr-panel a.on{background:#eef2ff;color:#4f46e5}' +
      '@media (prefers-color-scheme:dark){#toc-remote .tr-panel{background:#1e293b;border-color:#334155}#toc-remote .tr-panel a{color:#e2e8f0}#toc-remote .tr-panel a:hover,#toc-remote .tr-panel a.on{background:#334155;color:#c7d2fe}}';
    document.head.appendChild(css);

    var box = document.createElement('div');
    box.id = 'toc-remote';
    if (embedded) box.className = 'emb';
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'tr-btn';
    btn.setAttribute('aria-expanded', 'false');
    btn.setAttribute('aria-controls', 'toc-remote-panel');
    btn.textContent = '📚 목차';
    var panel = document.createElement('nav');
    panel.className = 'tr-panel';
    panel.id = 'toc-remote-panel';
    panel.setAttribute('aria-label', '페이지 목차 리모컨');
    var title = document.createElement('div');
    title.className = 'tr-title';
    title.textContent = '눌러서 바로 이동';
    panel.appendChild(title);

    var links = [];
    heads.forEach(function (it, idx) {
      if (!it.el.id) it.el.id = 'toc-r-' + (idx + 1);
      it.el.style.scrollMarginTop = '72px';
      var a = document.createElement('a');
      a.href = '#' + it.el.id;
      a.textContent = it.text;
      a.title = it.text;
      a.addEventListener('click', function (ev) {
        ev.preventDefault();
        var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        it.el.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
        try { history.replaceState(null, '', '#' + it.el.id); } catch (e) {}
        setOpen(false);
      });
      panel.appendChild(a);
      links.push(a);
    });

    function setOpen(v) {
      box.classList.toggle('open', v);
      btn.setAttribute('aria-expanded', v ? 'true' : 'false');
    }
    btn.addEventListener('click', function () { setOpen(!box.classList.contains('open')); });
    document.addEventListener('click', function (ev) { if (!box.contains(ev.target)) setOpen(false); });
    document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape') setOpen(false); });

    box.appendChild(panel);
    box.appendChild(btn);
    document.body.appendChild(box);

    // 지금 읽는 소제목 강조
    function mark() {
      var cur = 0;
      for (var i = 0; i < heads.length; i++) {
        if (heads[i].el.getBoundingClientRect().top <= 120) cur = i; else break;
      }
      for (var j = 0; j < links.length; j++) links[j].classList.toggle('on', j === cur);
    }
    var tick = false;
    window.addEventListener('scroll', function () {
      if (tick) return;
      tick = true;
      requestAnimationFrame(function () { tick = false; mark(); });
    }, { passive: true });
    mark();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
