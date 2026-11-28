/* 호호플레이 — 일정표 팝업 (festival/plan-modal.js)
 *
 * [ADD] 2026-11-22
 * 지도 페이지의 "코스 카드"와 "장소 상세 팝업"에서 바로 나들이 일정표를 열기 위한 전체 화면 창.
 * 일정표 편집기 자체는 /festival/camp-plan.js 를 쓰고(월드컵·룰렛·포스터와 같은 편집기), 이 파일은 그 편집기를 담을 창만 만든다.
 *
 *  - window.HohoPlanModal.openPlace(contentid)  : 아이랑 장소(kids-○○○○) 하나를 기준으로 근처 나들이픽 2곳을 담은 하루 일정표
 *  - window.HohoPlanModal.openCourse(spec)      : 코스 카드의 장소·예상 시간을 그대로 담은 일정표
 *        spec = { title, dateStr, rows:[{ time, title, memo, k:'n'|'f'|'x', pid?, src? }] }
 *  - 닫기: 오른쪽 위 ✕ / 어두운 바깥 / ESC / 브라우저 뒤로가기
 *  - camp-plan.js 는 처음 열 때만 불러온다(지도 페이지가 느려지지 않음). 편집 내용은 이 기기 브라우저에만 저장된다.
 *  - 이 창은 월드컵·룰렛에서 쓰는 일정표 저장 칸과 겹치지 않도록 따로 저장한다(hp_popupplan_v1 / hp_courseplan_v1).
 */
(function () {
  'use strict';
  if (window.HohoPlanModal) return;

  var CP_URL = '/festival/camp-plan.js?v=20261128a';
  var DATA_URL = '/data/kids_places.json';
  var NEAR_KM = 10, FAR_KM = 25, WANT = 5, UNKNOWN_HOURS_PENALTY_KM = 2;
  var root, box, opened = false, pushed = false, prevOverflow = '';
  var cpPromise = null, dataPromise = null;

  var CSS = '' +
    '#hpPlanRoot{position:fixed;left:0;top:0;right:0;bottom:0;z-index:2147483600;display:none;}' +
    '#hpPlanRoot.hp-on{display:block;}' +
    '#hpPlanRoot .hpp-bd{position:absolute;left:0;top:0;right:0;bottom:0;background:rgba(15,23,42,.6);}' +
    '#hpPlanRoot .hpp-box{position:absolute;left:0;right:0;bottom:0;margin:0 auto;width:100%;max-width:720px;height:94vh;height:94dvh;background:#f8fafc;' +
      'border-radius:18px 18px 0 0;box-shadow:0 -10px 40px rgba(15,23,42,.35);overflow-y:auto;-webkit-overflow-scrolling:touch;overscroll-behavior:contain;}' +
    '#hpPlanRoot .hpp-bar{position:sticky;top:0;z-index:3;display:flex;align-items:center;justify-content:space-between;gap:8px;padding:10px 14px;background:#fff;border-bottom:1px solid #e2e8f0;}' +
    '#hpPlanRoot .hpp-bar b{font-size:14px;font-weight:900;color:#0f172a;}' +
    '#hpPlanRoot .hpp-g{margin-left:auto;font-size:12.5px;font-weight:800;color:#4f46e5;text-decoration:none;white-space:nowrap;}' +
    '#hpPlanRoot .hpp-x{border:0;background:#111827;color:#fff;font-size:13px;font-weight:800;border-radius:99px;padding:8px 14px;cursor:pointer;}' +
    '#hpPlanRoot .hpp-x:focus-visible{outline:3px solid #93c5fd;outline-offset:2px;}' +
    '#hpPlanRoot #campPlan{margin:12px;background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:16px;}' +
    '#hpPlanRoot .cp-back{display:none!important;}' +
    '#hpPlanRoot .hpp-msg{padding:40px 16px;text-align:center;font-size:14px;font-weight:700;color:#64748b;}';

  function build() {
    if (root) return;
    var st = document.createElement('style');
    st.id = 'hpPlanStyle';
    st.textContent = CSS;
    document.head.appendChild(st);
    root = document.createElement('div');
    root.id = 'hpPlanRoot';
    root.setAttribute('role', 'dialog');
    root.setAttribute('aria-modal', 'true');
    root.setAttribute('aria-label', '나들이 일정표');
    root.innerHTML =
      '<div class="hpp-bd"></div>' +
      '<div class="hpp-box">' +
        '<div class="hpp-bar"><b>🗓️ 나들이 일정표</b><a class="hpp-g" href="/festival/plan-guide.html" target="_blank" rel="noopener">샘플·사용법</a><button type="button" class="hpp-x" aria-label="일정표 닫기">✕ 닫기</button></div>' +
        '<div class="hpp-msg" id="hppMsg">불러오는 중…</div>' +
        '<section id="campPlan" aria-label="내 일정표" style="display:none"><div id="cpRoot"></div></section>' +
      '</div>';
    document.body.appendChild(root);
    box = root.querySelector('.hpp-box');
    root.querySelector('.hpp-x').addEventListener('click', close);
    root.querySelector('.hpp-bd').addEventListener('click', close);
    // ESC: 일정표만 닫는다(아래에 깔린 상세 팝업은 그대로 둔다).
    window.addEventListener('keydown', function (e) {
      if (opened && (e.key === 'Escape' || e.key === 'Esc')) { e.preventDefault(); e.stopPropagation(); close(); }
    }, true);
    // 휴대폰 뒤로가기: 일정표를 먼저 닫는다.
    window.addEventListener('popstate', function () {
      // 일정표 위에서 "상세보기" 팝업을 열었다가 뒤로가기로 팝업만 닫을 때는 일정표를 그대로 둔다.
      var ci = document.getElementById('cpInfo');
      if (window.__cpInfoSkip || (ci && ci.classList.contains('on'))) return;   // 장소 정보 팝업(camp-plan.js)만 닫는 뒤로가기
      var sh = document.getElementById('hpSheetRoot');
      if (sh && sh.getAttribute('data-over') === '1' && sh.classList.contains('hp-on')) return;
      if (opened) { pushed = false; hardClose(); }
    });
  }

  function showBox() {
    build();
    if (!opened) {
      opened = true;
      prevOverflow = document.documentElement.style.overflow;
      document.documentElement.style.overflow = 'hidden';
      root.classList.add('hp-on');
      // 장소 상세 팝업 위에서 열 때는 기록을 더 쌓지 않는다(뒤로가기 한 번에 둘 다 닫히는 것을 피하려고, 상세 팝업이 이미 쌓은 기록을 쓴다).
      var sheet = document.getElementById('hpSheetRoot');
      pushed = false;
      if (!(sheet && sheet.classList.contains('hp-on'))) {
        try { history.pushState({ hpPlan: 1 }, '', location.href); pushed = true; } catch (_) { pushed = false; }
      }
    }
    var m = document.getElementById('hppMsg'); if (m) { m.style.display = 'block'; m.textContent = '불러오는 중…'; }
    var sec = document.getElementById('campPlan'); if (sec) sec.style.display = 'none';
    box.scrollTop = 0;
  }
  function hideMsg() { var m = document.getElementById('hppMsg'); if (m) m.style.display = 'none'; }
  function fail() {
    var m = document.getElementById('hppMsg');
    if (m) { m.style.display = 'block'; m.textContent = '일정표를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.'; }
  }

  function hardClose() {
    if (!opened) return;
    opened = false;
    root.classList.remove('hp-on');
    document.documentElement.style.overflow = prevOverflow;
  }
  function close() {
    if (!opened) return;
    var wasPushed = pushed;
    pushed = false;
    hardClose();
    // 열 때 쌓아 둔 기록 한 칸을 되돌린다.
    if (wasPushed) { try { history.back(); } catch (_) { /* 무시 */ } }
  }

  function loadCampPlan() {
    if (window.HohoCampPlan) return Promise.resolve();
    if (cpPromise) return cpPromise;
    cpPromise = new Promise(function (resolve, reject) {
      var s = document.createElement('script');
      s.src = CP_URL;
      s.onload = function () { window.HohoCampPlan ? resolve() : reject(new Error('no HohoCampPlan')); };
      s.onerror = function () { cpPromise = null; reject(new Error('load fail')); };
      document.head.appendChild(s);
    });
    return cpPromise;
  }
  function loadData() {
    if (!dataPromise) {
      dataPromise = fetch(DATA_URL).then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
        .catch(function (e) { dataPromise = null; throw e; });
    }
    return dataPromise;
  }

  function haversineKm(lat1, lng1, lat2, lng2) {
    var R = 6371, rad = Math.PI / 180;
    var dLat = (lat2 - lat1) * rad, dLng = (lng2 - lng1) * rad;
    var a = Math.sin(dLat / 2) * Math.sin(dLat / 2) + Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
    return 2 * R * Math.asin(Math.sqrt(a));
  }
  // nearby-pick.js 와 같은 기준: 반경 10km 안에서 가까운 순(운영시간을 모르는 곳은 2km 뒤로), 5곳이 안 차면 25km까지.
  function nearOf(self, all) {
    var cands = [];
    all.forEach(function (p) {
      if (!p || p.contentid === self.contentid || typeof p.lat !== 'number' || typeof p.lng !== 'number') return;
      var km = haversineKm(self.lat, self.lng, p.lat, p.lng);
      var h = String(p.hours || '');
      var known = !!h && h.indexOf('확인 필요') < 0;
      cands.push({ p: p, km: km, rank: km + (known ? 0 : UNKNOWN_HOURS_PENALTY_KM) });
    });
    cands.sort(function (a, b) { return a.rank - b.rank || a.km - b.km; });
    var pool = cands.filter(function (c) { return c.km <= NEAR_KM; });
    if (pool.length < WANT) pool = cands.filter(function (c) { return c.km <= FAR_KM; });
    var picks = pool.slice(0, WANT);
    picks.sort(function (a, b) { return a.km - b.km; });
    return picks.map(function (c) { return { contentid: c.p.contentid, title: c.p.title, km: c.km, lat: c.p.lat, lng: c.p.lng, placeType: c.p.placeType || '', costTag: c.p.costTag || '' }; });
  }

  var CHECK_PLACE = [
    ['a1', '{P} 운영시간·휴관일 확인 (공식 홈페이지·전화)'],
    ['a2', '입장료·이용 요금 확인'],
    ['a3', '예약·시간제 입장 필요 여부 확인'],
    ['a4', '주차장·주차 요금 확인'],
    ['a5', '우천·미세먼지 때 바꿀 곳 정해 두기']
  ];
  var CHECK_COURSE = [
    ['a1', '들를 곳 운영시간·휴관일 확인 (공식 홈페이지·전화)'],
    ['a2', '입장료·예약·시간제 입장 필요 여부 확인'],
    ['a3', '장소 사이 이동 시간·주차장 확인'],
    ['a4', '우천·미세먼지 때 바꿀 곳 정해 두기']
  ];

  function openPlace(contentid) {
    if (!contentid) return;
    showBox();
    Promise.all([loadCampPlan(), loadData()]).then(function (r) {
      var all = r[1] || [];
      var self = null;
      for (var i = 0; i < all.length; i++) { if (all[i] && all[i].contentid === contentid) { self = all[i]; break; } }
      if (!self) throw new Error('place not found');
      var champ = {
        contentid: self.contentid, title: self.title, addr: self.addr || '', lat: self.lat, lng: self.lng,
        tel: self.tel || '', fee: self.fee || '', hours: self.hours || '', placeType: self.placeType || '', costTag: self.costTag || '',
        hasDetail: self.hasDetail !== false, _near: []
      };
      if (typeof self.lat === 'number' && typeof self.lng === 'number') champ._near = nearOf(self, all);
      if (!opened) return;
      hideMsg();
      window.HohoCampPlan.open(champ, {
        mode: 'day',
        variant: 'popup',
        over: {
          key: 'hp_popupplan_v1', icon: '📍', placeLabel: '기준 장소', fromLabel: '이 장소에서', hasFest: false,
          title: '🗓️ 이 장소로 만든 나들이 일정표',
          sub: '{P}와 근처 나들이픽을 미리 담아 두었어요. 시간·일정·메모를 마음대로 고치고, 아래 <b>출발 전 확인표</b>까지 체크한 뒤 인쇄하거나 PDF로 저장하세요.',
          checkA: CHECK_PLACE
        }
      });
      box.scrollTop = 0;
    }).catch(fail);
  }

  function hashOf(str) {
    var h = 5381;
    for (var i = 0; i < str.length; i++) h = ((h * 33) ^ str.charCodeAt(i)) >>> 0;
    return h.toString(36);
  }

  function openCourse(spec) {
    if (!spec || !spec.rows || !spec.rows.length) return;
    showBox();
    loadCampPlan().then(function () {
      var sig = (spec.dateStr || '') + '|' + spec.rows.map(function (r) { return r.title; }).join('|');
      var champ = { contentid: 'course-' + hashOf(sig), title: spec.title || '추천 코스', addr: '', _near: [], _date: spec.dateStr || '' };
      if (!opened) return;
      hideMsg();
      window.HohoCampPlan.open(champ, {
        mode: 'day',
        noDefaultNear: true,
        rows: spec.rows,
        over: {
          key: 'hp_courseplan_v1', icon: '🗺️', placeLabel: '코스', fromLabel: '앞 장소에서', hasFest: false, noNear: '',
          title: '🗓️ 내 코스 일정표',
          paperTitle: '🗺️ 나의 나들이 코스 일정표',
          sub: '추천 코스의 장소와 예상 시간을 그대로 담아 두었어요. 예상 시간은 직선거리 기준 대략치라 실제와 다를 수 있어요. 시간·일정·메모를 마음대로 고치고, 아래 <b>출발 전 확인표</b>까지 체크한 뒤 인쇄하거나 PDF로 저장하세요.',
          checkA: CHECK_COURSE
        }
      });
      box.scrollTop = 0;
    }).catch(fail);
  }

  window.HohoPlanModal = { openPlace: openPlace, openCourse: openCourse, close: close };
})();
