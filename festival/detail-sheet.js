/* 호호플레이 — 상세정보 바텀시트 (festival/detail-sheet.js)
 *
 * [ADD] 2026-11-11
 * 지도·나들이 월드컵·캠핑장 월드컵·룰렛·축제 포스터·오늘 어디 갈까? 에서 "상세보기" 류의 링크
 * (/festival/detail/○○.html)를 누르면, 전체 화면으로 페이지를 넘기지 않고 아래에서 위로 올라오는
 * 팝업(바텀시트)으로 상세 내용을 보여 준다. 팝업 오른쪽 하단에 ✕ 닫기 버튼이 있다.
 *
 * 동작 방식
 *  - 페이지 전체에서 클릭을 가로채는 위임(delegation) 방식이라 각 페이지의 기존 코드를 고치지 않는다.
 *    링크는 그대로 <a href="/festival/detail/…"> 이므로 JS가 안 돌거나 새 탭으로 열면 예전처럼 동작한다.
 *  - 상세 페이지 HTML을 받아 iframe(srcdoc) 안에 그대로 보여 준다(스타일 충돌 없음, 댓글·나들이픽 등도 동작).
 *    iframe 안에서는 맨 위 "← 지도로 돌아가기/홈" 줄과 푸터만 숨긴다.
 *  - 닫기: 오른쪽 하단 ✕ / 바깥(어두운 영역) 터치 / ESC / 손잡이를 아래로 끌기 / 브라우저 뒤로가기.
 *  - 불러오기에 실패하면 예전처럼 상세 페이지로 그냥 이동한다.
 *  - 직접 열려면 window.HohoDetailSheet.open('/festival/detail/kids-0001.html').
 *  - 가로채지 않을 링크에는 data-nosheet 속성을 붙인다.
 */
(function () {
  'use strict';
  if (window.HohoDetailSheet) return;

  var DETAIL_RE = /^\/festival\/detail\/[^\/?#]+\.html$/;
  var cache = {};
  var seq = 0;
  var opened = false;
  var pushed = false;
  var lastFocus = null;
  var prevOverflow = '';
  var closeTimer = null;
  var root, panel, body, frame, loading, closeBtn, grab, backdrop;

  var CSS = '' +
    '#hpSheetRoot{position:fixed;left:0;top:0;right:0;bottom:0;z-index:2147483000;display:none;}' +
    '#hpSheetRoot.hp-on{display:block;}' +
    '#hpSheetRoot .hp-bd{position:absolute;left:0;top:0;right:0;bottom:0;background:rgba(15,23,42,.55);opacity:0;transition:opacity .28s ease;}' +
    '#hpSheetRoot.hp-open .hp-bd{opacity:1;}' +
    '#hpSheetRoot .hp-panel{position:absolute;left:0;right:0;bottom:0;margin:0 auto;width:100%;max-width:680px;height:88vh;height:88dvh;' +
      'background:#f8fafc;border-radius:20px 20px 0 0;box-shadow:0 -10px 40px rgba(15,23,42,.35);display:flex;flex-direction:column;overflow:hidden;' +
      'transform:translateY(105%);transition:transform .32s cubic-bezier(.22,.8,.3,1);will-change:transform;}' +
    '#hpSheetRoot.hp-open .hp-panel{transform:translateY(0);}' +
    '#hpSheetRoot .hp-panel.hp-drag{transition:none;}' +
    '#hpSheetRoot .hp-grab{flex:0 0 auto;position:relative;height:30px;background:#fff;border-bottom:1px solid #e2e8f0;cursor:grab;touch-action:none;}' +
    '#hpSheetRoot .hp-grab:before{content:"";position:absolute;left:50%;top:10px;width:44px;height:5px;margin-left:-22px;border-radius:99px;background:#cbd5e1;}' +
    '#hpSheetRoot .hp-body{position:relative;flex:1 1 auto;min-height:0;background:#f8fafc;}' +
    '#hpSheetRoot .hp-frame{display:block;width:100%;height:100%;border:0;background:#f8fafc;}' +
    '#hpSheetRoot .hp-loading{position:absolute;left:0;right:0;top:40%;text-align:center;font-size:14px;font-weight:700;color:#64748b;pointer-events:none;}' +
    '#hpSheetRoot .hp-close{position:absolute;right:16px;bottom:16px;bottom:calc(16px + env(safe-area-inset-bottom,0px));z-index:5;width:52px;height:52px;border-radius:50%;' +
      'border:0;background:#111827;color:#fff;font-size:24px;font-weight:700;line-height:52px;text-align:center;padding:0;cursor:pointer;' +
      'box-shadow:0 6px 18px rgba(15,23,42,.45);-webkit-tap-highlight-color:transparent;}' +
    '#hpSheetRoot .hp-close:hover{background:#1f2937;}' +
    '#hpSheetRoot .hp-close:focus-visible{outline:3px solid #93c5fd;outline-offset:2px;}' +
    '@media (prefers-reduced-motion:reduce){#hpSheetRoot .hp-panel,#hpSheetRoot .hp-bd{transition:none;}}';

  // iframe 안에 넣는 보정: 맨 위 줄(← 지도로 돌아가기 / 홈)과 푸터를 숨기고, 아래쪽에 ✕ 버튼이 안 가리도록 여백을 둔다.
  var FRAME_CSS = '<style id="hp-sheet-fix">' +
    '.detail-wrap>div:first-child{display:none!important;}' +
    '#site-footer{display:none!important;}' +
    '.detail-wrap{padding-top:16px!important;padding-bottom:110px!important;}' +
    'html{-webkit-text-size-adjust:100%;}' +
    '</style>';

  // iframe 안에서 누른 링크 처리: 다른 상세 페이지는 이 팝업 안에서 교체, 그 밖의 사이트 내부 링크는 전체 창으로 이동.
  var FRAME_JS = '<script>(function(){document.addEventListener("click",function(e){' +
    'try{if(e.defaultPrevented||e.button!==0||e.metaKey||e.ctrlKey||e.shiftKey||e.altKey)return;' +
    'var a=e.target.closest&&e.target.closest("a[href]");if(!a)return;' +
    'var t=a.getAttribute("target");if(t&&t!=="_self"&&t!=="_top")return;' +
    'var h=a.getAttribute("href");if(!h||h.charAt(0)==="#"||/^(tel|mailto|sms|javascript):/i.test(h))return;' +
    'var u=new URL(h,"__BASE__");' +
    'if(u.origin!==window.top.location.origin){return;}' +
    'e.preventDefault();' +
    'if(/^\\/festival\\/detail\\/[^\\/?#]+\\.html$/.test(u.pathname)&&window.parent&&window.parent.HohoDetailSheet){window.parent.HohoDetailSheet.open(u.pathname);}' +
    'else{window.top.location.href=u.href;}' +
    '}catch(_){}},true);})();<\/script>';

  function build() {
    if (root) return;
    var st = document.createElement('style');
    st.id = 'hpSheetStyle';
    st.textContent = CSS;
    document.head.appendChild(st);

    root = document.createElement('div');
    root.id = 'hpSheetRoot';
    root.setAttribute('role', 'dialog');
    root.setAttribute('aria-modal', 'true');
    root.setAttribute('aria-label', '상세 정보');
    root.innerHTML =
      '<div class="hp-bd"></div>' +
      '<div class="hp-panel">' +
        '<div class="hp-grab"></div>' +
        '<div class="hp-body">' +
          '<div class="hp-loading">불러오는 중…</div>' +
        '</div>' +
        '<button type="button" class="hp-close" aria-label="닫기">✕</button>' +
      '</div>';
    document.body.appendChild(root);

    backdrop = root.querySelector('.hp-bd');
    panel = root.querySelector('.hp-panel');
    grab = root.querySelector('.hp-grab');
    body = root.querySelector('.hp-body');
    loading = root.querySelector('.hp-loading');
    closeBtn = root.querySelector('.hp-close');

    closeBtn.addEventListener('click', function () { close(); });
    backdrop.addEventListener('click', function () { close(); });
    document.addEventListener('keydown', function (e) {
      if (opened && (e.key === 'Escape' || e.key === 'Esc')) { e.preventDefault(); close(); }
    });
    bindDrag();
  }

  // 손잡이를 아래로 끌어서 닫기(터치·마우스)
  function bindDrag() {
    var startY = null, dy = 0;
    function down(e) {
      if (e.target && e.target.closest && e.target.closest('a')) return;
      startY = e.clientY; dy = 0;
      panel.classList.add('hp-drag');
      try { grab.setPointerCapture(e.pointerId); } catch (_) {}
    }
    function move(e) {
      if (startY === null) return;
      dy = Math.max(0, e.clientY - startY);
      panel.style.transform = 'translateY(' + dy + 'px)';
    }
    function up() {
      if (startY === null) return;
      panel.classList.remove('hp-drag');
      var shouldClose = dy > 110;
      startY = null;
      panel.style.transform = '';
      if (shouldClose) close();
    }
    grab.addEventListener('pointerdown', down);
    grab.addEventListener('pointermove', move);
    grab.addEventListener('pointerup', up);
    grab.addEventListener('pointercancel', up);
  }

  // iframe 주소를 바꾸면 브라우저 "뒤로가기" 기록이 쌓여 팝업이 안 닫히는 문제가 생긴다.
  // 그래서 매번 새 iframe을 만들어 srcdoc를 넣은 뒤 끼워 넣는다(최초 로드는 기록을 남기지 않는다).
  function setFrame(doc) {
    if (frame && frame.parentNode) frame.parentNode.removeChild(frame);
    frame = null;
    if (doc === null) return;
    var f = document.createElement('iframe');
    f.className = 'hp-frame';
    f.title = '상세 정보';
    f.addEventListener('load', function () { if (loading) loading.style.display = 'none'; });
    f.srcdoc = doc;
    body.appendChild(f);
    frame = f;
  }

  function prepareHtml(html, path) {
    var origin = location.origin;
    // 푸터를 불러오는 스크립트는 팝업에서 필요 없다.
    html = html.replace(/<script(?![^>]*\bsrc=)[^>]*>[\s\S]*?<\/script>/gi, function (m) {
      return m.indexOf('/footer.html') > -1 ? '' : m;
    });
    // 혹시 광고 코드가 들어 있어도 팝업(iframe) 안에서는 실행하지 않는다.
    html = html.replace(/<script[^>]*adsbygoogle[^>]*>[\s\S]*?<\/script>/gi, '');
    html = html.replace(/<ins[^>]*adsbygoogle[^>]*>[\s\S]*?<\/ins>/gi, '');
    var head = '<base href="' + origin + path + '">' + FRAME_CSS + FRAME_JS.replace('__BASE__', origin + path);
    if (/<head[^>]*>/i.test(html)) return html.replace(/<head[^>]*>/i, function (m) { return m + head; });
    return '<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">' + head + '</head><body>' + html + '</body></html>';
  }

  function load(path) {
    var token = ++seq;
    loading.style.display = 'block';
    var p = cache[path]
      ? Promise.resolve(cache[path])
      : fetch(path, { credentials: 'same-origin' }).then(function (r) {
          if (!r.ok) throw new Error('HTTP ' + r.status);
          return r.text();
        }).then(function (t) { cache[path] = t; return t; });
    p.then(function (html) {
      if (token !== seq || !opened) return;
      setFrame(prepareHtml(html, path));
    }).catch(function () {
      if (token !== seq) return;
      // 불러오기에 실패하면 예전처럼 상세 페이지로 이동한다.
      hardClose();
      location.href = path;
    });
  }

  function open(path) {
    if (!path || !DETAIL_RE.test(path)) return;
    build();
    clearTimeout(closeTimer);
    if (!opened) {
      opened = true;
      lastFocus = document.activeElement;
      prevOverflow = document.documentElement.style.overflow;
      document.documentElement.style.overflow = 'hidden';
      root.classList.add('hp-on');
      panel.style.transform = '';
      // 레이아웃을 한 번 확정한 뒤 클래스를 붙여야 올라오는 애니메이션이 보인다.
      void root.offsetHeight;
      root.classList.add('hp-open');
      try { history.pushState({ hpSheet: 1 }, '', location.href); pushed = true; } catch (_) { pushed = false; }
      closeBtn.focus({ preventScroll: true });
    }
    setFrame(null);
    load(path);
  }

  function hardClose() {
    clearTimeout(closeTimer);
    seq++;
    opened = false;
    pushed = false;
    if (root) {
      root.classList.remove('hp-open');
      root.classList.remove('hp-on');
      setFrame(null);
    }
    document.documentElement.style.overflow = prevOverflow;
  }

  function finish() {
    if (!opened) return;
    opened = false;
    seq++;
    root.classList.remove('hp-open');
    document.documentElement.style.overflow = prevOverflow;
    closeTimer = setTimeout(function () {
      root.classList.remove('hp-on');
      setFrame(null);
    }, 340);
    try { if (lastFocus && lastFocus.focus) lastFocus.focus({ preventScroll: true }); } catch (_) {}
  }

  function close() {
    if (!opened) return;
    if (pushed) {
      pushed = false;
      try {
        history.back();
        // 만약 popstate 가 오지 않으면(기록이 꼬인 경우) 직접 닫는다.
        setTimeout(function () { if (opened) finish(); }, 500);
        return;
      } catch (_) {}
    }
    finish();
  }

  // 브라우저(휴대폰) 뒤로가기 → 팝업만 닫는다.
  window.addEventListener('popstate', function () {
    if (opened) { pushed = false; finish(); }
  });

  // 상세 링크 클릭 가로채기
  document.addEventListener('click', function (e) {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var a = e.target && e.target.closest ? e.target.closest('a[href]') : null;
    if (!a || a.hasAttribute('data-nosheet') || a.hasAttribute('download')) return;
    var t = a.getAttribute('target');
    if (t && t !== '_self') return;
    var u;
    try { u = new URL(a.getAttribute('href'), location.href); } catch (_) { return; }
    if (u.origin !== location.origin || !DETAIL_RE.test(u.pathname)) return;
    e.preventDefault();
    open(u.pathname);
  }, true);

  window.HohoDetailSheet = { open: open, close: close };
})();
