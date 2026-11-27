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
  var map, clusterer = null, pts = [], markers = [], labelOv = [], routeOv = [], line = null, selId = null, courseMode = false;
  var loading = false, waiters = [], mobOpen = false;

  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function ll(la, ln) { return new kakao.maps.LatLng(la, ln); }

  /* ───────── 핀·경로 (예전 지도 화면 festival/map.html 과 같은 방식) ─────────
     기본 카카오 마커 + 클러스터(minLevel 6, 숫자 원) + 확대하면 장소 이름 라벨, 코스는 번호 원(.cpin)+점선 */
  function nameOf(id) {
    var t = (window.ITEMS || []).filter(function (x) { return x.id === id; })[0];
    if (t) return t.n;
    var c = document.querySelector('[data-id="' + id + '"].card h3');
    return c ? c.textContent : '';
  }
  function clearLabels() { labelOv.forEach(function (o) { o.setMap(null); }); labelOv = []; }
  function clearPins() {
    clearLabels();
    if (clusterer) { try { clusterer.clear(); } catch (e) { } }
    markers.forEach(function (m) { m.setMap(null); }); markers = [];
  }
  function drawPins() {
    clearPins();
    markers = pts.map(function (p) {
      var m = new kakao.maps.Marker({ position: ll(p.la, p.ln) });
      kakao.maps.event.addListener(m, 'click', function () { K.pinClick(p.id, p); });
      m._p = p;
      return m;
    });
    if (clusterer) clusterer.addMarkers(markers); else markers.forEach(function (m) { m.setMap(map); });
    updateLabels();
  }
  /* 확대했을 때(레벨 5 이하)만 화면 안 장소 이름을 보여 준다. 겹치지 않게 최대 40개 */
  function updateLabels() {
    clearLabels();
    if (!map || courseMode || map.getLevel() > 5) return;
    var bd = map.getBounds(), n = 0, used = [];
    markers.forEach(function (m) {
      if (n >= 40) return;
      var pos = m.getPosition(); if (!bd.contain(pos)) return;
      var nm = nameOf(m._p.id); if (!nm) return;
      var pr = map.getProjection ? null : null;
      var key = Math.round(pos.getLat() * 2000) + ',' + Math.round(pos.getLng() * 2000);
      if (used.indexOf(key) > -1) return; used.push(key);
      var el = document.createElement('button'); el.type = 'button'; el.className = 'place-label'; el.textContent = nm;
      el.addEventListener('click', function (e) { e.stopPropagation(); K.pinClick(m._p.id, m._p); });
      var o = new kakao.maps.CustomOverlay({ position: pos, content: el, xAnchor: 0.5, yAnchor: 0, zIndex: 1, clickable: true });
      o.setMap(map); labelOv.push(o); n++;
    });
  }
  function setCluster(on) { if (clusterer) { try { clusterer.setMinLevel(on ? 6 : 99); } catch (e) { } } }
  function clearRoute() {
    routeOv.forEach(function (o) { o.setMap(null); }); routeOv = [];
    if (line) { line.setMap(null); line = null; }
    [].forEach.call(document.querySelectorAll('.msel'), function (e) { e.classList.remove('msel'); });
    if (courseMode) { courseMode = false; setCluster(true); }
  }
  function fitBox(la0, la1, ln0, ln1) {
    map.setBounds(new kakao.maps.LatLngBounds(ll(la0, ln0), ll(la1, ln1)), 60, 60, 60, 60);
  }

  K.set = function (a) { pts = a || []; if (K.ready) drawPins(); };
  /* 내 주변: 내 위치 표시 + 지도 이동(지도가 아직 안 열렸으면 열릴 때 적용) */
  var meOv = null, mePos = null;
  function applyMe(center) {
    if (!K.ready || !map) return;
    if (meOv) { meOv.setMap(null); meOv = null; }
    if (!mePos) return;
    var el = document.createElement('div'); el.className = 'mepin'; el.innerHTML = '<i></i><b>내 위치</b>';
    meOv = new kakao.maps.CustomOverlay({ position: ll(mePos[0], mePos[1]), content: el, xAnchor: 0.5, yAnchor: 0.5, zIndex: 20 });
    meOv.setMap(map);
    if (center) { map.setLevel(6); map.setCenter(ll(mePos[0], mePos[1])); }
  }
  K.me = function (p) { mePos = p && p.length ? p : null; applyMe(true); };
  K.hover = function () { /* 기본 마커는 강조 표시를 바꾸지 않는다(예전 지도와 동일) */ };
  K.focus = function (id, st, la, ln, el) {
    if (!K.ready) return;
    clearRoute(); selId = id;
    if (el) el.classList.add('msel');
    if (st && st.length) {
      /* 예전 지도(map.html showCourseOnMap)와 같은 순서·설정: 번호 핀 → 점선 → 화면 맞춤. 코스 화면에서는 클러스터를 끈다 */
      courseMode = true; clearLabels();
      var path = st.map(function (x) { return ll(x[0], x[1]); });
      st.forEach(function (x, i) {
        var wrap = document.createElement('div'); wrap.className = 'cpin';
        wrap.innerHTML = '<div class="cpin-no">' + (i + 1) + '</div><div class="cpin-name"></div>';
        wrap.lastChild.textContent = x[2] || '';
        var o = new kakao.maps.CustomOverlay({ position: path[i], content: wrap, xAnchor: 0.5, yAnchor: 0.5, zIndex: 10 + i, clickable: true });
        o.setMap(map); routeOv.push(o);
      });
      if (path.length >= 2) {
        line = new kakao.maps.Polyline({ path: path, strokeWeight: 3, strokeColor: '#4338ca', strokeOpacity: 0.8, strokeStyle: 'dash' });
        line.setMap(map);
      }
      var b = new kakao.maps.LatLngBounds(); path.forEach(function (p) { b.extend(p); });
      map.setBounds(b, 80, 80, 80, 80);
    } else {
      var t = (window.ITEMS || []).filter(function (x) { return x.id === id; })[0];
      map.setLevel(4); map.setCenter(ll(la, ln));
      var d2 = document.createElement('div'); d2.className = 'place-label'; d2.textContent = t ? t.n : '';
      var o2 = new kakao.maps.CustomOverlay({ position: ll(la, ln), content: d2, xAnchor: 0.5, yAnchor: 0, zIndex: 9 });
      o2.setMap(map); routeOv.push(o2);
    }
    if (!courseMode) drawPins();
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
    var title = '', sub = '', btns = '', extra = '', im = '';
    if (el) {
      title = (el.querySelector('h3') || {}).textContent || '';
      sub = (el.querySelector('.reg') || {}).textContent || '';
      btns = '<button type="button" data-a="course">코스 자세히 보기</button><button type="button" data-a="plan" class="p">📅 일정표 만들기</button>';
    } else if (t) {
      var fee = { free: '무료', paid: '유료' }[t.c] || '';
      function fd(v) { v = String(v || ''); return v.length === 8 ? v.slice(0, 4) + '.' + v.slice(4, 6) + '.' + v.slice(6) : v; }
      title = t.n; sub = (t.t === 'f' ? '🎪 축제' : '📍 아이랑 장소') + (t.s ? ' · ' + t.s : '') + (t.pt ? ' · ' + t.pt : '') + (fee ? ' · ' + fee : '');
      if (t.t === 'f' && t.sd) extra = '<p class="mp">📅 ' + fd(t.sd) + ' ~ ' + fd(t.ed) + '</p>';
      if (t.d) extra += '<p class="md">' + esc(String(t.d).slice(0, 70)) + (String(t.d).length > 70 ? '…' : '') + '</p>';
      if (t.im) im = '<img class="mim" src="' + esc(t.im.replace(/^http:/, 'https:')) + '" alt="" loading="lazy" onerror="this.remove()">';
      btns = '<a href="/festival/detail/' + esc(id) + '.html">상세 보기</a>' +
        '<a href="https://map.kakao.com/link/to/' + encodeURIComponent(t.n) + ',' + t.la + ',' + t.ln + '" target="_blank" rel="noopener">길찾기</a>' +
        (t.t === 'p' ? '<button type="button" data-a="place" class="p">📅 일정표</button>' : '');
    } else { return; }
    c.innerHTML = '<button type="button" class="x" data-a="x" aria-label="닫기">✕</button><div class="mrow">' + im + '<div class="mtx"><b>' + esc(title) + '</b><span>' + esc(sub) + '</span>' + extra + '</div></div><div class="bt">' + btns + '</div>';
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
    /* PC: 예전 지도처럼 핀을 누르면 지도 위에 작은 안내 팝업을 띄운다 */
    showCard(id);
  };

  /* ───────── 스타일 ───────── */
  function css() {
    var s = document.createElement('style');
    s.textContent = '' +
      '#pcmap #kmap{position:absolute;left:0;top:0;right:0;bottom:0;z-index:0}' +
      '#pcmap.km #pcsvg,#pcmap.km .zb{display:none}' +
      '.mtop{z-index:5}' +
      /* 아래는 festival/map.html 의 같은 이름 스타일을 그대로 옮긴 것 */
      '.cpin{position:relative;width:28px;height:28px}' +
      '.cpin-no{display:flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:50%;background:#334155;color:#fff;border:2px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,.35);font-size:14px;font-weight:800;line-height:1;cursor:pointer;box-sizing:border-box}' +
      '.cpin-name{position:absolute;left:32px;top:50%;transform:translateY(-50%);max-width:130px;padding:2px 7px;border-radius:6px;background:rgba(255,255,255,.95);border:1px solid #cbd5e1;color:#1e293b;font-size:11px;font-weight:700;line-height:1.4;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;box-shadow:0 1px 3px rgba(0,0,0,.15);cursor:pointer}' +
      '#pcmap #mcard{display:none}' +
      '@media(min-width:1024px){#pcmap #mcard{position:absolute;left:12px;bottom:22px;width:370px;max-width:calc(100% - 24px);z-index:7;background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:16px;padding:14px 14px 12px;box-shadow:0 6px 24px rgba(0,0,0,.25)}#mcard b{display:block;font-size:15px;padding-right:24px}#mcard span{display:block;margin:2px 0 6px;font-size:12px;color:var(--sub)}#mcard .x{position:absolute;right:8px;top:6px;border:0;background:none;color:var(--sub);font-size:16px;padding:6px;cursor:pointer}#mcard .bt{display:flex;gap:8px}#mcard .bt a,#mcard .bt button{flex:1;text-align:center;border:1px solid var(--pri);color:var(--pri);background:var(--card);border-radius:10px;padding:10px 6px;font:800 13px/1.2 inherit;font-family:inherit;text-decoration:none;cursor:pointer}#mcard .bt .p{background:var(--pri);color:#fff}}' +
      '#mcard .mrow{display:flex;gap:10px;margin-bottom:10px}#mcard .mim{flex:none;width:64px;height:64px;border-radius:10px;object-fit:cover;background:#e2e8f0}#mcard .mtx{min-width:0;flex:1}#mcard .mp{margin:0 0 2px;font-size:12px;font-weight:700;color:var(--ink)}#mcard .md{margin:0;font-size:12px;color:var(--sub);line-height:1.45}' +
      '.mepin{position:relative;width:18px;height:18px}.mepin i{display:block;width:18px;height:18px;border-radius:50%;background:#2563eb;border:3px solid #fff;box-shadow:0 0 0 6px rgba(37,99,235,.25),0 2px 6px rgba(0,0,0,.35);box-sizing:border-box}.mepin b{position:absolute;left:50%;top:22px;transform:translateX(-50%);padding:1px 6px;border-radius:6px;background:#2563eb;color:#fff;font-size:11px;font-weight:800;white-space:nowrap}' +
      '.place-label{display:block;max-width:140px;padding:2px 7px;margin-top:2px;background:rgba(255,255,255,.95);border:1px solid #c7d2fe;border-radius:6px;color:#1e293b;font-size:11px;font-weight:700;line-height:1.4;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;box-shadow:0 1px 3px rgba(0,0,0,.15);cursor:pointer;font-family:inherit}';
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
      try { clusterer = new kakao.maps.MarkerClusterer({ map: map, averageCenter: true, minLevel: 6 }); } catch (e) { clusterer = null; }
      kakao.maps.event.addListener(map, 'idle', updateLabels);
      host.classList.add('km');
      K.ready = true;
      applyMe(true);
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
    s.src = '//dapi.kakao.com/v2/maps/sdk.js?appkey=' + KEY + '&autoload=false&libraries=clusterer';
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

  /* 코스 카드의 "지도로 보기": 지도를 열고 그 코스의 번호 경로(점선)를 보여 준다 */
  K.openCourse = function (id) {
    var el = document.querySelector('[data-id="' + id + '"].card'), st = [], la = 0, ln = 0;
    if (el) { try { st = JSON.parse(el.getAttribute('data-stops') || '[]'); } catch (e) { st = []; } la = +el.getAttribute('data-lat'); ln = +el.getAttribute('data-lng'); }
    K.open(function () {
      K.focus(id, st, la, ln, null);
      if (!isPC()) showCard(id);
      else if (el) { el.classList.add('msel'); }
    });
  };

  window.KMAP = K;
  if (isPC()) ensure();
  window.addEventListener('resize', function () {
    if (K.ready && map) map.relayout();
    else if (isPC() && !loading) ensure();   /* 좁은 창에서 열었다가 창을 넓히면(최대화) 그때 지도를 불러온다 */
  });
})();
