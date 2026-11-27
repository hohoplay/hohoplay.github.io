/* 목차 리모컨 — 상세페이지·코스 글에서 화면 왼쪽 아래에 떠 있는 "목차" 버튼.
   페이지의 h2 소제목으로 목록을 만들고, 누르면 그 자리로 부드럽게 이동한다. 본문 목차 박스는 그대로 두고 추가로 쓰인다.
   - 팝업(iframe) 안, 소제목이 3개 미만인 페이지에서는 만들지 않는다.
   - 실패해도 페이지는 그대로 동작한다(스크립트가 없어도 본문 목차가 남는다). */
(function () {
  'use strict';
  try { if (window.self !== window.top) return; } catch (e) { return; }
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
