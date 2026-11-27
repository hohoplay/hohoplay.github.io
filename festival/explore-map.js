/* 호호플레이 — 아이랑 나들이(코스·전체목록) 페이지 PC 지도 (festival/explore-map.js)
 *
 * [ADD] 2026-11-27
 * festival/explore.html 의 PC(가로 1024px 이상) 화면 오른쪽 지도를 카카오맵으로 그린다.
 *  - 페이지 안에는 SVG 간이 지도(#pcsvg)가 먼저 들어 있고, 이 파일이 카카오맵을 불러오는 데 성공하면 그 위를 덮는다.
 *    카카오 SDK가 안 뜨거나(도메인 미등록·네트워크 오류 등) 6초 안에 준비되지 않으면 SVG 간이 지도를 그대로 쓴다.
 *  - 페이지(explore.html)의 코드가 부르는 API: window.KMAP.set / focus / hover / region
 *      set(points)            : 지도에 점을 찍는다. points = [{id, la, ln, c?:코스, f?:축제}]
 *      focus(id, stops, la, ln, el) : 카드를 눌렀을 때. stops가 있으면 1·2·3 번호 경로, 없으면 그 장소만 확대
 *      hover(id)              : 카드에 마우스를 올렸을 때 해당 점 강조
 *      region(key)            : 지역(시·도) 영역으로 이동, 빈 값이면 전국
 *  - 모바일(1024px 미만)에서는 아무것도 하지 않는다(지도는 /festival/ 로 이동).
 *  - 카카오 앱키는 festival/index.html 과 같은 값(도메인 등록형 키)이다.
 */
(function () {
  'use strict';
  if (window.KMAP) return;
  if (!window.matchMedia || !matchMedia('(min-width:1024px)').matches) return;
  var host = document.getElementById('pcmap');
  if (!host) return;

  var KEY = '9e0536bde5120d8fcdd09c780e431ea3';
  var BOX = { seoul: [37.7, 37.4, 126.8, 127.2], busan: [35.3, 35.0, 128.9, 129.3], daegu: [35.95, 35.75, 128.45, 128.75], incheon: [37.6, 37.3, 126.4, 126.8], daejeon: [36.5, 36.2, 127.2, 127.55], sejong: [36.7, 36.4, 127.1, 127.4], gyeonggi: [38.0, 36.9, 126.4, 127.7], gangwon: [38.4, 37.0, 127.5, 129.3], chungbuk: [37.2, 36.0, 127.3, 128.5], gyeongbuk: [37.0, 35.7, 128.1, 129.5], gyeongnam: [35.7, 34.7, 127.7, 129.2], chungnam: [37.0, 36.0, 125.9, 127.4], jeonbuk: [36.2, 35.3, 126.4, 127.7], jeonnam: [35.4, 34.3, 126.1, 127.5], gwangju: [35.3, 35.0, 126.7, 127.0], ulsan: [35.7, 35.4, 129.0, 129.45], jeju: [33.6, 33.15, 126.1, 126.95] };

  var K = { ready: false };
  var map, pts = [], pinOv = [], routeOv = [], line = null, selId = null, pinMap = {};

  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function ll(la, ln) { return new kakao.maps.LatLng(la, ln); }

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
    var b = new kakao.maps.LatLngBounds(ll(la0, ln0), ll(la1, ln1));
    map.setBounds(b, 60, 60, 60, 60);
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
    clearRoute(); selId = null;
    var b = BOX[k];
    if (!k || !b) { map.setLevel(13); map.setCenter(ll(36.2, 127.8)); } else { fitBox(b[1], b[0], b[2], b[3]); }
    drawPins();
  };
  /* 점을 눌렀을 때: 목록에 그 카드가 있으면 거기로 스크롤해서 누른 것처럼 처리, 없으면 지도만 확대 */
  K.pinClick = function (id, p) {
    var el = document.querySelector('[data-id="' + id + '"].card,[data-id="' + id + '"].li');
    if (el) {
      el.scrollIntoView({ block: 'center', behavior: 'smooth' });
      el.classList.add('mfl'); setTimeout(function () { el.classList.remove('mfl'); }, 1200);
      el.click();
    } else if (p) { K.focus(id, null, p.la, p.ln, null); }
  };

  function css() {
    var s = document.createElement('style');
    s.textContent = '' +
      '#pcmap #kmap{position:absolute;left:0;top:0;right:0;bottom:0;z-index:0}' +
      '#pcmap.km svg,#pcmap.km .zb,#pcmap.km .tip2{display:none}' +
      '.mtop{z-index:5}' +
      '.kpin{width:12px;height:12px;border-radius:50%;background:#6366f1;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.35);cursor:pointer;box-sizing:border-box}' +
      '.kpin.f{background:#e11d48}.kpin.c{background:#4f46e5;width:16px;height:16px}.kpin.hl{background:#f59e0b;border-color:#78350f;width:18px;height:18px}' +
      '.knum{display:flex;align-items:center;gap:6px;pointer-events:none}' +
      '.knum b{width:26px;height:26px;border-radius:50%;background:#4f46e5;color:#fff;border:2px solid #fff;font-size:13px;display:flex;align-items:center;justify-content:center;box-shadow:0 1px 6px rgba(0,0,0,.35)}' +
      '.knum span{white-space:nowrap;font-size:12px;font-weight:800;color:#1e293b;text-shadow:-1px -1px 0 #fff,1px -1px 0 #fff,-1px 1px 0 #fff,1px 1px 0 #fff}' +
      '.klbl{white-space:nowrap;padding:4px 9px;border-radius:9px;background:#fff;color:#1e293b;font-size:12px;font-weight:800;box-shadow:0 2px 8px rgba(0,0,0,.25);pointer-events:none}';
    document.head.appendChild(s);
  }

  function init() {
    try {
      css();
      var box = document.createElement('div'); box.id = 'kmap';
      host.insertBefore(box, host.firstChild);
      map = new kakao.maps.Map(box, { center: ll(36.2, 127.8), level: 13 });
      map.addControl(new kakao.maps.ZoomControl(), kakao.maps.ControlPosition.RIGHT);
      host.classList.add('km');
      K.ready = true;
      drawPins();
      if (window.__kready) window.__kready();
      setTimeout(function () { map.relayout(); }, 100);
    } catch (e) { K.ready = false; host.classList.remove('km'); }
  }

  window.KMAP = K;
  var timer = setTimeout(function () { /* 6초 안에 준비 안 되면 간이 지도 유지 */ }, 6000);
  var s = document.createElement('script');
  s.src = '//dapi.kakao.com/v2/maps/sdk.js?appkey=' + KEY + '&autoload=false';
  s.onload = function () {
    try { kakao.maps.load(function () { clearTimeout(timer); init(); }); } catch (e) { /* 간이 지도 유지 */ }
  };
  s.onerror = function () { /* 간이 지도 유지 */ };
  document.head.appendChild(s);
})();
