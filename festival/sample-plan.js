/* 호호플레이 — "샘플 일정표" (festival/sample-plan.js)
 *
 * [ADD] 2026-11-23
 * 월드컵·캠핑장 월드컵·룰렛 화면의 "👀 샘플 결과" 아래에, 같은 샘플 장소로 만든 예시 일정표를 글자로 보여 준다.
 *  - 일정표 편집기(camp-plan.js)의 기본 틀과 같은 순서·시간이라, 실제로 만들면 이 모양으로 열린다.
 *  - 근처 장소 2곳은 festival/nearby-pick.js 의 규칙(휴관 요일 제외, 가까운 순, 실내·실외 섞기)으로 고른다.
 *  - 시간은 예시, 운영시간·요금·예약은 "확인"으로 적는다(없는 정보는 만들지 않는다).
 * 입구: window.HohoSamplePlan.render(box, { contentid, title, lat, lng, placeType?, costTag? }, mode, opts?)   mode = 'day' | 'forest' | 'camp'
 *   opts(선택) = { icon, from, anchorMemo, intro }  (축제 포스터: 🎪·'이 축제에서'·'행사 시간 확인')
 */
(function () {
  'use strict';
  if (window.HohoSamplePlan) return;
  var seq = 0;

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function fmtKm(km) {
    if (typeof km !== 'number' || !isFinite(km)) return '';
    if (km < 1) return Math.max(100, Math.round(km * 10) * 100) + 'm';
    return (Math.round(km * 10) / 10).toFixed(1) + 'km';
  }
  function pickTwo(list) {
    var a = (list || []).filter(function (n) { return n && n.title; });
    if (a.length <= 2) return a;
    var first = a[0], second = null, t0 = first.placeType;
    if (t0 === '실내' || t0 === '실외') {
      var want = t0 === '실내' ? '실외' : '실내';
      for (var i = 1; i < a.length; i++) { if (a[i].placeType === want) { second = a[i]; break; } }
    }
    return [first, second || a[1]];
  }
  function tagText(src) {
    var t = [];
    if (!src) return '';
    if (src.placeType === '실내') t.push('🏠 실내'); else if (src.placeType === '실외') t.push('🌳 야외'); else if (src.placeType === '실내외') t.push('🏠🌳 실내·야외');
    if (src.costTag !== undefined) t.push(src.costTag === '완전무료' ? '무료' : src.costTag === '유료' ? '유료' : src.costTag === '유료(일부 무료 조건 있음)' ? '일부 무료' : '요금 확인 필요');
    return t.join(' · ');
  }
  function injectStyle() {
    if (document.getElementById('sp-style')) return;
    var st = document.createElement('style');
    st.id = 'sp-style';
    st.textContent =
      '.sp{margin-top:18px;padding-top:16px;border-top:1px dashed #cbd5e1}' +
      '.sp h3{margin:0 0 4px;font-size:15px;font-weight:900;color:#0f172a}' +
      '.sp .sp-sub{margin:0 0 10px;font-size:12.5px;color:#64748b;line-height:1.6;word-break:keep-all}' +
      '.sp .sp-day{margin:10px 0 6px;font-size:13px;font-weight:900;color:#065f46;background:#ecfdf5;border-radius:8px;padding:5px 10px}' +
      '.sp .sp-tbl{overflow-x:auto;-webkit-overflow-scrolling:touch}' +
      '.sp table{width:100%;min-width:420px;border-collapse:collapse;background:#fff;font-size:13px}' +
      '.sp th,.sp td{border:1px solid #e2e8f0;padding:7px 9px;text-align:left;vertical-align:top;line-height:1.5}' +
      '.sp th{background:#f1f5f9;font-size:12.5px}' +
      '.sp td:first-child{white-space:nowrap;font-weight:800;color:#334155}' +
      '.sp .sp-tg{display:block;font-size:11.5px;color:#64748b;font-weight:600}' +
      '.sp .sp-ft{margin-top:8px;font-size:12px;color:#94a3b8;line-height:1.6}' +
      '.sp .sp-ft a{color:#4f46e5;font-weight:800;text-decoration:none}';
    document.head.appendChild(st);
  }

  function rowsFor(mode, place, two, from, o) {
    o = o || {};
    var near = function (n, t) {
      return { t: t, a: '📍 ' + n.title, tg: tagText(n), m: (n.km != null ? from + ' 약 ' + fmtKm(n.km) + ' · ' : '') + '운영시간 확인' };
    };
    var days = [], r;
    if (mode === 'camp') {
      r = [{ t: '10:00', a: '집 출발' }];
      var ts = two.length >= 2 ? ['11:30', '13:30'] : ['12:00'];
      two.forEach(function (n, i) { r.push(near(n, ts[i])); });
      r.push({ t: '15:30', a: '⛺ ' + place.title + ' 체크인', m: '체크인 시간은 캠핑장에 확인' });
      r.push({ t: '18:00', a: '저녁 · 불멍' });
      days.push({ h: '1일차', rows: r });
      days.push({ h: '2일차', rows: [{ t: '09:00', a: '아침 식사 · 짐 정리' }, { t: '11:00', a: '⛺ 체크아웃', m: '퇴실 시간 확인 · 쓰레기 정리' }, { t: '12:30', a: '귀가 · 점심' }] });
    } else {
      var forest = mode === 'forest';
      r = [
        { t: '10:00', a: '집 출발' },
        { t: '10:30', a: (o.icon || (forest ? '🎯' : '🏆')) + ' ' + place.title, tg: tagText(place), m: o.anchorMemo || '운영시간 확인' },
        { t: forest ? '12:30' : '12:00', a: forest ? '점심 · 도시락' : '점심 · 휴식', m: forest ? '도시락 또는 근처 식당' : '근처 식당 찾기 (일정표에서 식당·카페를 검색해 넣을 수 있어요)' }
      ];
      var tt = forest ? (two.length >= 2 ? ['14:00', '16:00'] : ['14:30']) : (two.length >= 2 ? ['13:30', '15:30'] : ['14:00']);
      two.forEach(function (n, i) { r.push(near(n, tt[i])); });
      r.push({ t: '17:30', a: '귀가' });
      days.push({ h: '', rows: r });
    }
    return days;
  }

  function build(box, place, mode, near, tok, o) {
    o = o || {};
    if (box._sp !== tok) return;
    var old = box.querySelector('.sp'); if (old) old.parentNode.removeChild(old);
    injectStyle();
    var from = o.from || (mode === 'camp' ? '캠핑장에서' : '이 장소에서');
    var days = rowsFor(mode, place, pickTwo(near), from, o);
    var h = '<div class="sp"><h3>🗓️ 샘플 일정표 (예시)</h3><p class="sp-sub">' + (o.intro || ('위 샘플 ' + (mode === 'camp' ? '캠핑장으로' : '장소로'))) + ' 일정표를 만들면 이런 시간표가 먼저 담겨요. 시간·일정·메모는 마음대로 고칠 수 있고, “식당·카페 넣기”로 근처 식당·카페를 검색해 넣을 수도 있어요.</p>';
    days.forEach(function (d) {
      if (d.h) h += '<div class="sp-day">' + esc(d.h) + '</div>';
      h += '<div class="sp-tbl"><table><thead><tr><th style="width:58px">시간</th><th style="width:42%">일정</th><th>메모</th></tr></thead><tbody>';
      d.rows.forEach(function (x) {
        h += '<tr><td>' + esc(x.t) + '</td><td>' + esc(x.a) + (x.tg ? '<span class="sp-tg">' + esc(x.tg) + '</span>' : '') + '</td><td>' + esc(x.m || '') + '</td></tr>';
      });
      h += '</tbody></table></div>';
    });
    h += '<p class="sp-ft">시간은 예시예요. 운영시간·휴관일·요금·예약은 바뀔 수 있으니 방문 전 공식 안내를 확인하세요. 근처 장소는 직선거리 기준이에요. <a href="/festival/plan-guide.html">일정표 만들기 가이드 보기 →</a></p></div>';
    var w = document.createElement('div');
    w.innerHTML = h;
    box.appendChild(w.firstChild);
  }

  function render(box, place, mode, o) {
    if (!box || !place) return;
    mode = (mode === 'camp' || mode === 'forest') ? mode : 'day';
    var tok = ++seq; box._sp = tok;
    var old = box.querySelector('.sp'); if (old) old.parentNode.removeChild(old);
    var lat = +place.lat, lng = +place.lng;
    if (!place.title || !isFinite(lat) || !isFinite(lng) || place.lat === '' || place.lat == null) { build(box, place, mode, [], tok, o); return; }
    var done = false;
    function finish(list) { if (done) return; done = true; build(box, place, mode, list || [], tok, o); }
    var timer = setTimeout(function () { finish([]); }, 6000);
    (function go(tries) {
      if (box._sp !== tok) return;
      if (window.HohoNearbyPick) {
        window.HohoNearbyPick.mount(document.createElement('div'), {
          contentid: place.contentid, title: place.title, lat: lat, lng: lng,
          onPicks: function (list) { clearTimeout(timer); finish(list); }
        });
      } else if (tries < 20) setTimeout(function () { go(tries + 1); }, 300);
    })(0);
  }

  window.HohoSamplePlan = { render: render };
})();
