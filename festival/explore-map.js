/* 호호플레이 — 아이랑 나들이(코스·전체목록) 페이지 지도 (festival/explore-map.js)
 *
 * [ADD] 2026-11-27
 * festival/index.html 의 카카오맵. 예전 시안용 SVG 간이 지도는 화면에 보이지 않게 숨겼다.
 *  - PC(가로 1024px 이상): 오른쪽 지도(#pcmap)를 페이지를 열 때 바로 불러온다.
 *  - 모바일: "지도" 탭을 누를 때 처음 불러오고, 화면 전체를 덮는 지도(body.mapmode)로 보여 준다.
 *    같은 주소(/festival/)에서 열리고, 뒤로가기(또는 ← 목록)로 목록으로 돌아온다.
 *  - 카카오 SDK가 안 뜨면(도메인 미등록·네트워크 오류) 안내 문구만 보여 준다.
 *  - 옛 지도 링크(/festival/?id=…&lat=…&lng=… / ?region=…)도 이 지도로 열어 준다(openAt).
 *
 * 페이지(index.html) 코드가 부르는 API: window.KMAP
 *   set(points) · focus(id, stops, la, ln, el) · hover(id) · region(key) · open() · close() · openAt(id, la, ln)
 * 카카오 앱키는 festival/map.html 과 같은 값(도메인 등록형 키)이다.
 */
(function () {
  'use strict';
  if (window.KMAP) return;
  var host = document.getElementById('pcmap');
  if (!host) return;
  function isPC() { return !!window.matchMedia && matchMedia('(min-width:1024px)').matches; }

  var KEY = '9e0536bde5120d8fcdd09c780e431ea3';
  var BOX = { seoul: [37.7, 37.4, 126.8, 127.2], busan: [35.3, 35.0, 128.9, 129.3], daegu: [35.95, 35.75, 128.45, 128.75], incheon: [37.6, 37.3, 126.4, 126.8], daejeon: [36.5, 36.2, 127.2, 127.55], sejong: [36.7, 36.4, 127.1, 127.4], gyeonggi: [38.0, 36.9, 126.4, 127.7], gangwon: [38.4, 37.0, 127.5, 129.3], chungbuk: [37.2, 36.0, 127.3, 128.5], gyeongbuk: [37.0, 35.7, 128.1, 129.5], gyeongnam: [35.7, 34.7, 127.7, 129.2], chungnam: [37.0, 36.0, 125.9, 127.4], jeonbuk: [36.2, 35.3, 126.4, 127.7], jeonnam: [35.4, 34.3, 126.1, 127.5], gwangju: [35.3, 35.0, 126.7, 127.0], ulsan: [35.7, 35.4, 129.0, 129.45], jeju: [33.6, 33.15, 126.1, 126.95] };

  var K = { ready: false };
  var map, pts = [], pinOv = [], routeOv = [], line = null, selId = null, pinMap = {};
  var loading = false, waiters = [], mobOpen = false;

  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function ll(la, ln) { return new kakao.maps.LatLng(la, ln); }

  /* ───────── 점·경로 ───────── */
  function clearPins() { pinOv.forEach(function (o) { o.setMap(null); }); pinOv = []; pinMap = {}; }
  function clearRoute() {
    routeOv.forEach(function (o) { o.setMap(null); }); routeOv = [];
    if (line) { line.setMap(null); line = null; }
    [].forEach.call(document.querySelectorAll('.msel'), function (e) { e.classList.remove('msel'); });
  }
  function drawPins() {
    clearPins();
    pts.forEach(function (p) {
      var d = document.createElement('div');
      d.className = 'kpin' + (p.c ? ' c' : '') + (p.f ? ' f' : '') + (p.id === selId ? ' hl' : '');
      d.setAttribute('data-id', p.id);
      d.addEventListener('click', function (e) { e.stopPropagation(); K.pinClick(p.id, p); });
      var o = new kakao.maps.CustomOverlay({ position: ll(p.la, p.ln), content: d, yAnchor: 0.5, xAnchor: 0.5, zIndex: p.id === selId ? 5 : 1 });
      o.setMap(map);
      pinOv.push(o); pinMap[p.id] = d;
    });
  }
  function fitBox(la0, la1, ln0, ln1) {
    map.setBounds(new kakao.maps.LatLngBounds(ll(la0, ln0), ll(la1, ln1)), 60, 60, 60, 60);
  }

  K.set = function (a) { pts = a || []; if (K.ready) drawPins(); };
  K.hover = function (id) {
    Object.keys(pinMap).forEach(function (k) { pinMap[k].classList.toggle('hl', k === (id || selId)); });
  };
  K.focus = function (id, st, la, ln, el) {
    if (!K.ready) return;
    clearRoute(); selId = id;
    if (el) el.classList.add('msel');
    if (st && st.length) {
      var path = st.map(function (x) { return ll(x[0], x[1]); });
      var b = new kakao.maps.LatLngBounds(); path.forEach(function (p) { b.extend(p); });
      map.setBounds(b, 80, 80, 80, 80);
      line = new kakao.maps.Polyline({ path: path, strokeWeight: 4, strokeColor: '#4f46e5', strokeOpacity: .9, strokeStyle: 'shortdash' });
      line.setMap(map);
      st.forEach(function (x, i) {
        var d = document.createElement('div'); d.className = 'knum';
        d.innerHTML = '<b>' + (i + 1) + '</b><span>' + esc(x[2] || '') + '</span>';
        var o = new kakao.maps.CustomOverlay({ position: path[i], content: d, yAnchor: 0.5, xAnchor: 0.5, zIndex: 8 });
        o.setMap(map); routeOv.push(o);
      });
    } else {
      var t = (window.ITEMS || []).filter(function (x) { return x.id === id; })[0];
      map.setLevel(4); map.setCenter(ll(la, ln));
      var d2 = document.createElement('div'); d2.className = 'klbl'; d2.textContent = t ? t.n : '';
      var o2 = new kakao.maps.CustomOverlay({ position: ll(la, ln), content: d2, yAnchor: 1.6, xAnchor: 0.5, zIndex: 9 });
      o2.setMap(map); routeOv.push(o2);
    }
    drawPins();
  };
  K.region = function (k) {
    if (!K.ready) return;
    clearRoute(); selId = null; hideCard();
    var b = BOX[k];
    if (!k || !b) { map.setLevel(13); map.setCenter(ll(36.2, 127.8)); } else { fitBox(b[1], b[0], b[2], b[3]); }
    drawPins();
  };

  /* ───────── 모바일 아래 카드 ───────── */
  function hideCard() { var c = host.querySelector('#mcard'); if (c) c.style.display = 'none'; }
  function showCard(id) {
    var c = host.querySelector('#mcard'); if (!c) return;
    var el = document.querySelector('[data-id="' + id + '"].card');
    var t = (window.ITEMS || []).filter(function (x) { return x.id === id; })[0];
    var title = '', sub = '', btns = '';
    if (el) {
      title = (el.querySelector('h3') || {}).textContent || '';
      sub = (el.querySelector('.reg') || {}).textContent || '';
      btns = '<button type="button" data-a="course">코스 자세히 보기</button><button type="button" data-a="plan" class="p">📅 일정표 만들기</button>';
    } else if (t) {
      title = t.n; sub = (t.t === 'f' ? '🎪 축제' : '📍 아이랑 장소') + (t.s ? ' · ' + t.s : '');
      btns = '<a href="/festival/detail/' + esc(id) + '.html">상세 보기</a>' + (t.t === 'p' ? '<button type="button" data-a="place" class="p">📅 일정표 만들기</button>' : '');
    } else { return; }
    c.innerHTML = '<button type="button" class="x" data-a="x" aria-label="닫기">✕</button><b>' + esc(title) + '</b><span>' + esc(sub) + '</span><div class="bt">' + btns + '</div>';
    c.setAttribute('data-id', id); c.style.display = 'block';
  }
  host.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('#mcard [data-a]'); if (!b) return;
    var a = b.getAttribute('data-a'), id = host.querySelector('#mcard').getAttribute('data-id');
    if (a === 'x') { hideCard(); return; }
    if (a === 'course') { var el = document.querySelector('[data-id="' + id + '"].card'); K.close(); if (el) setTimeout(function () { el.scrollIntoView({ block: 'center' }); }, 120); return; }
    if (a === 'plan') { var el2 = document.querySelector('[data-id="' + id + '"].card .plan'); if (el2) el2.click(); return; }
    if (a === 'place' && window.__plan) window.__plan.place(id);
  });

  /* 점을 눌렀을 때: PC는 목록의 그 카드로 스크롤+선택, 모바일 지도는 아래 카드 */
  K.pinClick = function (id, p) {
    if (document.body.classList.contains('mapmode')) {
      var el0 = document.querySelector('[data-id="' + id + '"].card'), st = null;
      if (el0) { try { st = JSON.parse(el0.getAttribute('data-stops') || '[]'); } catch (e) { st = null; } }
      K.focus(id, st, p ? p.la : 0, p ? p.ln : 0, null); showCard(id); return;
    }
    var el = document.querySelector('[data-id="' + id + '"].card,[data-id="' + id + '"].li');
    if (el) {
      el.scrollIntoView({ block: 'center', behavior: 'smooth' });
      el.classList.add('mfl'); setTimeout(function () { el.classList.remove('mfl'); }, 1200);
      el.click();
    } else if (p) { K.focus(id, null, p.la, p.ln, null); }
  };

  /* ───────── 스타일 ───────── */
  function css() {
    var s = document.createElement('style');
    s.textContent = '' +
      '#pcmap #kmap{position:absolute;left:0;top:0;right:0;bottom:0;z-index:0}' +
      '#pcmap.km svg,#pcmap.km .zb{display:none}' +
      '.mtop{z-index:5}' +
      '.kpin{width:12px;height:12px;border-radius:50%;background:#6366f1;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.35);cursor:pointer;box-sizing:border-box}' +
      '.kpin.f{background:#e11d48}.kpin.c{background:#4f46e5;width:16px;height:16px}.kpin.hl{background:#f59e0b;border-color:#78350f;width:18px;height:18px}' +
      '.knum{display:flex;align-items:center;gap:6px;pointer-events:none}' +
      '.knum b{width:26px;height:26px;border-radius:50%;background:#4f46e5;color:#fff;border:2px solid #fff;font-size:13px;display:flex;align-items:center;justify-content:center;box-shadow:0 1px 6px rgba(0,0,0,.35)}' +
      '.knum span{white-space:nowrap;font-size:12px;font-weight:800;color:#1e293b;text-shadow:-1px -1px 0 #fff,1px -1px 0 #fff,-1px 1px 0 #fff,1px 1px 0 #fff}' +
      '.klbl{white-space:nowrap;padding:4px 9px;border-radius:9px;background:#fff;color:#1e293b;font-size:12px;font-weight:800;box-shadow:0 2px 8px rgba(0,0,0,.25);pointer-events:none}';
    document.head.appendChild(s);
  }

  function failMsg() {
    if (host.querySelector('.kfail')) return;
    var d = document.createElement('div'); d.className = 'kfail';
    d.style.cssText = 'position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);text-align:center;font-size:14px;font-weight:700;color:#475569;line-height:1.8;z-index:2;padding:0 16px';
    d.innerHTML = '지도를 불러오지 못했어요.<br>잠시 후 다시 시도해 주세요.';
    host.appendChild(d);
  }

  function init() {
    try {
      css();
      var box = document.createElement('div'); box.id = 'kmap';
      host.insertBefore(box, host.firstChild);
      map = new kakao.maps.Map(box, { center: ll(36.2, 127.8), level: 13 });
      map.addControl(new kakao.maps.ZoomControl(), kakao.maps.ControlPosition.RIGHT);
      kakao.maps.event.addListener(map, 'click', hideCard);
      host.classList.add('km');
      K.ready = true;
      var f = host.querySelector('.kload'); if (f) f.remove();
      drawPins();
      setTimeout(function () { map.relayout(); if (window.__kready) window.__kready(); }, 100);
      waiters.splice(0).forEach(function (cb) { try { cb(); } catch (e) { } });
    } catch (e) { K.ready = false; host.classList.remove('km'); failMsg(); }
  }

  function ensure(cb) {
    if (K.ready) { if (cb) cb(); return; }
    if (cb) waiters.push(cb);
    if (loading) return;
    loading = true;
    var d = document.createElement('div'); d.className = 'kload';
    d.style.cssText = 'position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);font-size:13px;font-weight:700;color:#64748b;z-index:1';
    d.textContent = '지도 불러오는 중…'; host.appendChild(d);
    var timer = setTimeout(function () { if (!K.ready) { var l = host.querySelector('.kload'); if (l) l.remove(); failMsg(); } }, 7000);
    var s = document.createElement('script');
    s.src = '//dapi.kakao.com/v2/maps/sdk.js?appkey=' + KEY + '&autoload=false';
    s.onload = function () { try { kakao.maps.load(function () { clearTimeout(timer); init(); }); } catch (e) { clearTimeout(timer); failMsg(); } };
    s.onerror = function () { clearTimeout(timer); var l = host.querySelector('.kload'); if (l) l.remove(); failMsg(); };
    document.head.appendChild(s);
  }

  /* ───────── 열기/닫기 (모바일 전체화면) ───────── */
  K.open = function (cb) {
    if (isPC()) { ensure(cb); return; }
    if (!mobOpen) {
      mobOpen = true;
      document.body.classList.add('mapmode');
      try { history.pushState({ kmap: 1 }, '', location.href); } catch (e) { }
    }
    ensure(function () {
      if (map) map.relayout();
      if (window.__kready) window.__kready();
      if (cb) cb();
    });
  };
  K.close = function (fromPop) {
    if (!mobOpen) return;
    mobOpen = false;
    document.body.classList.remove('mapmode'); hideCard();
    if (!fromPop) { try { if (history.state && history.state.kmap) history.back(); } catch (e) { } }
  };
  window.addEventListener('popstate', function () { if (mobOpen) K.close(true); });

  /* 옛 지도 링크(?id=…&lat=…&lng=… / ?region=…): 전체목록으로 바꾸고 그 자리를 지도에 보여 준다 */
  K.openAt = function (id, la, ln) {
    var t = (window.ITEMS || []).filter(function (x) { return x.id === id; })[0];
    if (t) { la = t.la; ln = t.ln; }
    var tab = document.querySelector('#vc .seg a:nth-child(2)'); if (tab && window.__view === 'c') tab.click();
    K.open(function () {
      if (la && ln) { K.focus(id || '', null, la, ln, null); if (id && !isPC()) showCard(id); }
    });
  };

  window.KMAP = K;
  if (isPC()) ensure();
  window.addEventListener('resize', function () { if (K.ready && map) map.relayout(); });
})();
