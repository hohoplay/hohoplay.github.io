/*
 * 내 일정표 편집기 — 월드컵 결과 화면 아래에 펼쳐진다. 두 가지 틀(mode)을 쓴다.
 *   camp : 캠핑장 월드컵(/festival/camping-worldcup.html) — 1박 2일
 *   day  : 아이랑 나들이 월드컵(/festival/worldcup.html) — 하루 나들이 + "축제 넣기" 스위치 (2026-11-19 추가)
 *   forest: 숲·수목원·휴양림(룰렛 /festival/roulette.html) — 하루 숲 나들이(예약·긴팔·벌레 확인표)
 *   open(champ, { mode, over }) 의 over 로 화면 글자 일부(icon, placeLabel, fromLabel)를 바꿀 수 있다(룰렛은 "우승"이 아니라 "오늘의 장소").
 *
 * [ADD] 2026-11-19
 *  - 우승 캠핑장 + 근처 아이랑 장소 2곳(나들이픽 5곳 중 가까운 곳, 실내·실외가 섞이게)을 미리 담은 1박 2일 틀을 만들고,
 *    사용자가 시간·일정·메모를 고치고, 순서를 바꾸고, 하루를 더 넣거나 뺄 수 있다.
 *  - 이 서비스에 없는 정보(요금·예약·운영 기간·반려동물)는 "출발 전 확인표"로 바꿔 체크하게 한다. 준비물 체크도 함께.
 *  - 인쇄·PDF 저장은 일정표만 A4로 나오게 한다(pick.html 의 인쇄 방식과 같음: 화면의 나머지는 인쇄 때만 숨김).
 *  - 편집 내용은 이 기기 브라우저(localStorage)에만 저장한다. 서버로 보내지 않는다. 다른 캠핑장이 우승하면 새로 시작한다.
 *  - 입구: window.HohoCampPlan.open(champ, { mode: 'camp' | 'day' })  (mode 생략 = 'camp') — champ = { contentid, title, addr, lat?, lng?, tel?/_tel?, fee?, hours?, placeType?, costTag?, _near? }
 *          champ._near 는 nearby-pick.js 의 onPicks 콜백이 채운다([{ title, km, placeType, contentid }]).
 *
 * [ADD] 2026-11-28 숙박 칸: 일정 아래 "🏨 숙박 넣기" — 카카오 숙박(AD5)에서 호텔·리조트·콘도·펜션·풀빌라·글램핑만 보여 준다(모텔·여관·대실 등은 뺌). 줄 종류는 식사와 같은 k:'m' (제목이 🏨 로 시작).
 * [ADD] 2026-11-23 식사 칸: 일정 아래 "🍴 식당·카페 넣기" — 앞 장소 근처 음식점(FD6)·카페(CE7)를 카카오 장소검색으로 찾아 일정에 넣는다(줄 종류 k:'m').
 *    카카오 지도 SDK(services)는 처음 누를 때만 불러온다(지도 페이지는 이미 불러와 있으면 재사용). 영업시간·메뉴는 저장하지 않고 카카오맵 확인으로 안내한다.
 *          window.HohoCampPlan.hide() — 월드컵을 다시 시작할 때 일정표를 접는다.
 */
(function () {
    'use strict';

    var sec = null, root = null, cur = null, P = null;
    var mealUI = null;   // 식사 찾기 패널 상태 { day, ref, cat, q, rad, rep, results, status }
    var KAKAO_KEY = '9e0536bde5120d8fcdd09c780e431ea3';

    var MODES = {
        camp: {
            kind: 'camp', key: 'hp_campplan_v1', days: 2, anchorKind: 'in', nearTime: '12:00', hasFest: false,
            title: '🗓️ 내 캠핑 일정표', paperTitle: '⛺ 나의 캠핑 일정표', placeLabel: '캠핑장', icon: '⛺', fromLabel: '캠핑장에서',
            sub: '캠핑장과 근처 아이랑 장소를 미리 담아 두었어요. 시간·일정·메모를 마음대로 고치고, 아래 <b>출발 전 확인표</b>까지 체크한 뒤 인쇄하거나 PDF로 저장하세요.',
            dateLabel: '출발일', telNote: ' · 요금·예약은 전화로 확인하세요',
            noNear: '근처 아이랑 장소를 찾지 못해서 캠핑장 일정만 담았어요. 아래 “일정 추가”로 직접 넣을 수 있어요.',
            checkNote: '요금·예약 가능 여부·운영 기간·반려동물 동반은 이 서비스에 없는 정보예요. 캠핑장 공식 홈페이지나 전화로 확인하며 체크하세요.',
            footer: '호호플레이 hohoplaylab.com · 요금·예약·운영 시간은 방문 전 캠핑장에 꼭 확인하세요.',
            checkA: [
                ['a1', '예약 확인서(예약 날짜·사이트 번호) 챙기기'],
                ['a2', '이용 요금·추가 인원 요금 확인'],
                ['a3', '운영 기간·휴장일 확인 (겨울철 휴장·단축 운영 가능)'],
                ['a4', '체크인·체크아웃 시간 확인'],
                ['a5', '반려동물 동반 가능 여부 확인'],
                ['a6', '우천·취소·환불 규정 확인'],
                ['a7', '화로대·장작·전기 사용 가능 여부 확인']
            ],
            checkB: [
                ['b1', '텐트·타프·팩 (글램핑·카라반은 생략)'],
                ['b2', '침낭·매트·담요'],
                ['b3', '계절에 맞는 난방·방한용품'],
                ['b4', '취사도구·식재료·식수'],
                ['b5', '랜턴·멀티탭·보조배터리'],
                ['b6', '아이 여벌 옷·여분 신발·물티슈'],
                ['b7', '구급용품·벌레 퇴치용품'],
                ['b8', '쓰레기봉투']
            ]
        },
        day: {
            kind: 'day', key: 'hp_dayplan_v1', days: 1, anchorKind: 'out', nearTime: '14:00', hasFest: true,
            title: '🗓️ 내 하루 나들이 일정표', paperTitle: '🧸 나의 하루 나들이 일정표', placeLabel: '우승 장소', icon: '🏆', fromLabel: '우승 장소에서',
            sub: '{P}와 근처 아이랑 장소를 미리 담아 두었어요. 시간·일정·메모를 마음대로 고치고, 원하면 <b>그날 열리는 축제</b>도 넣어 보세요. 아래 <b>출발 전 확인표</b>까지 체크한 뒤 인쇄하거나 PDF로 저장하세요.',
            dateLabel: '나들이 날짜', telNote: ' · 운영시간·요금은 전화로 확인하세요',
            noNear: '근처 아이랑 장소를 찾지 못해서 {P} 일정만 담았어요. 아래 “일정 추가”로 직접 넣을 수 있어요.',
            checkNote: '운영시간·휴관일·요금은 사람이 적어 둔 안내라 바뀔 수 있어요. 공식 홈페이지나 전화로 확인하며 체크하세요.',
            footer: '호호플레이 hohoplaylab.com · 운영시간·휴관일·요금은 방문 전 공식 안내를 꼭 확인하세요.',
            checkA: [
                ['a1', '{P} 운영시간·휴관일 확인 (공식 홈페이지·전화)'],
                ['a2', '입장료·이용 요금 확인'],
                ['a3', '예약·시간제 입장 필요 여부 확인'],
                ['a4', '주차장·주차 요금 확인'],
                ['a5', '아이 나이·키 제한 등 이용 조건 확인'],
                ['a6', '날씨 확인 (실외라면 우산·방한 준비)']
            ],
            checkB: [
                ['b1', '아이 간식·물·물티슈'],
                ['b2', '여벌 옷·기저귀 (필요한 경우)'],
                ['b3', '유모차·아기띠 (필요한 경우)'],
                ['b4', '모자·선크림·우산 (날씨에 맞게)'],
                ['b5', '구급용품 (밴드 등)'],
                ['b6', '보조배터리·결제 수단'],
                ['b7', '돗자리·장난감 (야외라면)']
            ]
        }
    };
    // 숲·수목원·휴양림 — 하루 틀을 바탕으로 예약·복장·벌레·통신을 확인표에 담는다
    MODES.forest = {
        kind: 'forest', key: 'hp_forestplan_v1', days: 1, anchorKind: 'out', nearTime: '14:00', hasFest: true,
        title: '🗓️ 내 숲 나들이 일정표', paperTitle: '🌲 나의 숲 나들이 일정표', placeLabel: '오늘의 장소', icon: '🎯', fromLabel: '이곳에서',
        sub: '{P}와 근처 아이랑 장소를 미리 담아 두었어요. 숲은 걷는 시간이 길어서 점심 뒤에 가까운 곳 한두 곳만 담았어요. 시간·일정·메모를 고치고, <b>예약·복장·벌레 확인표</b>까지 체크한 뒤 인쇄하거나 PDF로 저장하세요.',
        dateLabel: '나들이 날짜', telNote: ' · 운영·예약은 전화로 확인하세요',
        noNear: '근처 아이랑 장소를 찾지 못해서 {P} 일정만 담았어요. 아래 “일정 추가”로 직접 넣을 수 있어요.',
        checkNote: '숲·수목원·휴양림은 운영 시간, 입장료, 예약 여부가 이 서비스에 없어요. 공식 홈페이지나 전화로 확인하며 체크하세요.',
        footer: '호호플레이 hohoplaylab.com · 운영시간·입장료·예약 여부는 방문 전 공식 안내를 꼭 확인하세요.',
        checkA: [
            ['a1', '{P} 운영시간·휴장일 확인 (시설·계절마다 달라요)'],
            ['a2', '입장료·주차 요금 확인'],
            ['a3', '숲해설·체험 프로그램 예약 필요 여부 확인'],
            ['a4', '진입 도로·주차장 상태 확인 (산길·눈·비)'],
            ['a5', '아이 연령·키 제한, 유모차 이동 가능 여부 확인'],
            ['a6', '날씨·일몰 시간 확인 (해가 짧은 계절은 일찍 내려오기)']
        ],
        checkB: [
            ['b1', '긴팔·긴바지, 미끄럽지 않은 운동화'],
            ['b2', '아이 간식·물·물티슈'],
            ['b3', '벌레 기피제·모자·선크림'],
            ['b4', '여벌 옷·양말 (젖거나 흙이 묻을 때)'],
            ['b5', '돗자리·쓰레기봉투'],
            ['b6', '구급용품 (밴드 등)'],
            ['b7', '유모차·아기띠 (필요한 경우)'],
            ['b8', '보조배터리 (산속은 통신이 약할 수 있어요)']
        ]
    };
    var cfg = MODES.camp;
    function fill(t) { return String(t == null ? '' : t).replace(/\{P\}/g, cfg.placeLabel); }

    function esc(s) {
        return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
    }
    function uid() { return 'r' + Math.random().toString(36).slice(2, 8); }
    function $(id) { return document.getElementById(id); }

    function fmtKm(km) {
        if (typeof km !== 'number' || !isFinite(km)) return '';
        if (km < 1) return Math.max(100, Math.round(km * 10) * 100) + 'm';
        return (Math.round(km * 10) / 10).toFixed(1) + 'km';
    }

    // ── 저장 ──────────────────────────────────────────────────────────────────────
    function load(id) {
        try {
            var o = JSON.parse(localStorage.getItem(cfg.key) || 'null');
            if (o && o.v === 1 && o.id === id && Array.isArray(o.rows) && o.days >= 1) return o;
        } catch (e) { /* 저장소를 못 쓰는 환경 */ }
        return null;
    }
    function save() {
        try { localStorage.setItem(cfg.key, JSON.stringify(P)); } catch (e) { /* 무시 */ }
        var pp = $('cpPaper'); if (pp && cur && P) pp.innerHTML = paperHtml();   // 미리보기에 바로 반영
    }

    // ── 기본 일정 ─────────────────────────────────────────────────────────────────
    // 가까운 곳 + (있으면) 실내·실외가 다른 곳 1곳
    function pickTwo(list) {
        var a = (list || []).filter(function (n) { return n && n.title; });
        if (a.length <= 2) return a;
        var first = a[0];
        var second = null;
        var t0 = first.placeType;
        if (t0 === '실내' || t0 === '실외') {
            var want = t0 === '실내' ? '실외' : '실내';
            for (var i = 1; i < a.length; i++) { if (a[i].placeType === want) { second = a[i]; break; } }
        }
        return [first, second || a[1]];
    }
    function costLabel(c) {
        var t = c && c.costTag;
        if (t === '완전무료') return '무료';
        if (t === '유료') return '유료';
        if (t === '유료(일부 무료 조건 있음)') return '일부 무료';
        return '요금 확인 필요';
    }
    // [ADD] 2026-11-20: 일정 줄에 "실내/실외 · 무료/유료" 배지를 보여 준다. 줄을 만들 때 tg 로 함께 저장해 두므로
    // 저장된 일정을 다시 열어도, 근처 장소 목록이 아직 안 불러와져 있어도 그대로 보인다. (c: free=초록, in/out=파랑 계열)
    function tagsOf(src) {
        var t = [];
        if (!src) return t;
        if (src.placeType === '실내') t.push(['in', '🏠 실내']);
        else if (src.placeType === '실외') t.push(['out', '🌳 야외']);
        else if (src.placeType === '실내외') t.push(['in', '🏠🌳 실내·야외']);
        if (src.costTag !== undefined) t.push([src.costTag === '완전무료' ? 'free' : '', costLabel(src)]);
        return t;
    }
    function festTags(f) {
        var ft = f && f.feeType;
        if (ft === 'free') return [['free', '무료']];
        if (ft === 'paid') return [['', '유료']];
        if (ft === 'mixed') return [['', '일부 유료']];
        return [['', '요금 확인 필요']];
    }
    // [ADD] 2026-11-22: 줄에 장소 위치(lat·lng)를 같이 저장 → 이동 순서 그림이 순서·장소가 바뀔 때마다 직선거리를 다시 계산한다.
    function withGeo(row, o) {
        if (o && o.lat !== '' && o.lat != null && o.lng !== '' && o.lng != null && isFinite(+o.lat) && isFinite(+o.lng)) { row.lat = +o.lat; row.lng = +o.lng; }
        return row;
    }
    function nearRow(n, time) {
        var meta = [];
        if (n.km != null) meta.push(cfg.fromLabel + ' 약 ' + fmtKm(n.km));
        meta.push('운영시간 확인');
        return withGeo({ id: uid(), day: 1, time: time, title: '📍 ' + n.title, memo: meta.join(' · '), k: 'n', pid: n.contentid || '', tg: tagsOf(n) }, n);
    }
    var defNearOff = false;
    function dayDefaultPlan(champ) {
        var forest = cfg.kind === 'forest';
        var two = defNearOff ? [] : pickTwo(champ._near);
        var memo = ['운영시간 확인'];
        var rows = [
            { id: uid(), day: 1, time: '10:00', title: '집 출발', memo: '', k: 'x' },
            withGeo({ id: uid(), day: 1, time: '10:30', title: cfg.icon + ' ' + champ.title, memo: memo.join(' · '), k: 'c', pid: champ.hasDetail === false ? '' : champ.contentid, tg: tagsOf(champ) }, champ),
            { id: uid(), day: 1, time: forest ? '12:30' : '12:00', title: forest ? '점심 · 도시락' : '점심 · 휴식', memo: forest ? '도시락 또는 근처 식당' : '근처 식당 찾기', k: 'x' }
        ];
        var times = forest ? (two.length >= 2 ? ['14:00', '16:00'] : ['14:30']) : (two.length >= 2 ? ['13:30', '15:30'] : ['14:00']);
        two.forEach(function (n, i) { rows.push(nearRow(n, times[i])); });
        rows.push({ id: uid(), day: 1, time: forest ? '17:30' : '17:30', title: '귀가', memo: '', k: 'out' });
        return { v: 1, mode: forest ? 'forest' : 'day', id: champ.contentid, date: champ._date || '', days: 1, rows: rows, checks: {}, extra: [], note: '', fest: false };
    }
    var seedRows = null;
    function newPlan(champ) {
        var pl = defaultPlan(champ);
        if (seedRows) {
            pl.rows = seedRows.map(function (r) {
                var o = { id: uid(), day: 1, time: r.time || '', title: r.title || '', memo: r.memo || '', k: r.k || 'x' };
                if (r.pid) o.pid = r.pid;
                withGeo(o, r);
                if (r.src) o.tg = r.k === 'f' ? festTags(r.src) : tagsOf(r.src);
                return o;
            });
        }
        return pl;
    }
    function defaultPlan(champ) {
        if (cfg.kind !== 'camp') return dayDefaultPlan(champ);
        var two = pickTwo(champ._near);
        var rows = [{ id: uid(), day: 1, time: '10:00', title: '집 출발', memo: '', k: 'x' }];
        var times = two.length >= 2 ? ['11:30', '13:30'] : ['12:00'];
        two.forEach(function (n, i) { rows.push(nearRow(n, times[i])); });
        rows.push({ id: uid(), day: 1, time: '15:30', title: '⛺ 캠핑장 체크인', memo: '체크인 시간은 캠핑장에 확인', k: 'in', pid: champ.hasDetail === false ? '' : champ.contentid });
        rows.push({ id: uid(), day: 1, time: '18:00', title: '저녁 · 불멍', memo: '', k: 'x' });
        rows.push({ id: uid(), day: 2, time: '09:00', title: '아침 식사 · 짐 정리', memo: '', k: 'x' });
        rows.push({ id: uid(), day: 2, time: '11:00', title: '⛺ 캠핑장 체크아웃', memo: '퇴실 시간 확인 · 쓰레기 정리', k: 'out' });
        rows.push({ id: uid(), day: 2, time: '12:30', title: '귀가 · 점심', memo: '', k: 'x' });
        return { v: 1, mode: 'camp', id: champ.contentid, date: '', days: 2, rows: rows, checks: {}, extra: [], note: '', fest: false };
    }

    // ── 날짜 표시 ─────────────────────────────────────────────────────────────────
    function dayLabel(d) {
        var s = cfg.kind === 'camp' ? d + '일차' : (cfg.kind === 'forest' ? '숲 나들이' : '하루 나들이');
        if (P.date && /^\d{4}-\d{2}-\d{2}$/.test(P.date)) {
            var p = P.date.split('-');
            var dt = new Date(Date.UTC(+p[0], +p[1] - 1, +p[2] + d - 1));
            s += ' · ' + (dt.getUTCMonth() + 1) + '/' + dt.getUTCDate() + '(' + '일월화수목금토'.charAt(dt.getUTCDay()) + ')';
        }
        return s;
    }
    function tel() { return cur ? String(cur._tel || cur.tel || '') : ''; }

    // ── 확인표 항목(근처 장소 확인은 일정 줄에서 만든다) ─────────────────────────────
    function nearChecks() {
        return P.rows.filter(function (r) { return r.k === 'n' || r.k === 'f' || r.k === 'm'; }).map(function (r) {
            var nm = String(r.title).replace(/^(?:📍|🎪|🍴|🏨|🎠)\s*/, '');
            return ['n_' + r.id, '「' + nm + '」 ' + (r.k === 'f' ? '행사 시간·장소 확인' : (r.k === 'm' ? (/^🏨/.test(r.title) ? '요금·예약·체크인 시간 확인' : '영업시간·휴무·대기 확인') : '운영시간·휴관일 확인'))];
        });
    }
    function isOn(id) { return !!P.checks[id]; }

    // ── 화면 ─────────────────────────────────────────────────────────────────────
    function injectStyle() {
        if ($('cp-style')) return;
        var st = document.createElement('style');
        st.id = 'cp-style';
        st.textContent =
            '#campPlan{scroll-margin-top:96px}' +
            '#campPlan .cp-back{display:inline-block;font-size:12.5px;font-weight:800;color:#047857;text-decoration:none;margin-bottom:8px}' +
            '#campPlan h2{margin:0 0 4px;font-size:18px;font-weight:900;color:#0f172a}' +
            '#campPlan .cp-sub{font-size:12.5px;color:#64748b;line-height:1.6;margin:0 0 12px}' +
            '#campPlan .cp-box{border:1px solid #e2e8f0;border-radius:12px;background:#f8fafc;padding:12px 14px;margin:0 0 14px}' +
            '#campPlan .cp-cname{font-size:15px;font-weight:900;color:#0f172a}' +
            '#campPlan .cp-line{font-size:12.5px;color:#475569;line-height:1.6;margin-top:2px;word-break:keep-all}' +
            '#campPlan .cp-line a{color:#4f46e5;font-weight:800;text-decoration:none}' +
            '#campPlan .cp-date{display:flex;align-items:center;gap:8px;margin-top:10px;font-size:13px;font-weight:800;color:#334155;flex-wrap:wrap}' +
            '#campPlan input[type=date],#campPlan input[type=time],#campPlan input[type=text],#campPlan textarea{font:inherit;font-size:14px;border:1px solid #cbd5e1;border-radius:8px;padding:7px 8px;background:#fff;color:#0f172a;box-sizing:border-box;max-width:100%}' +
            '#campPlan h3{margin:18px 0 8px;font-size:15px;font-weight:900;color:#0f172a;display:flex;align-items:center;justify-content:space-between;gap:8px}' +
            '#campPlan .cp-dayhd{background:#ecfdf5;border-radius:10px;padding:7px 12px;font-size:14px;font-weight:900;color:#065f46;margin:14px 0 8px;display:flex;justify-content:space-between;align-items:center;gap:8px}' +
            '#campPlan .cp-row{display:flex;gap:8px;align-items:flex-start;border:1px solid #e2e8f0;border-radius:12px;background:#fff;padding:8px;margin-bottom:8px}' +
            '#campPlan .cp-time{width:100%;min-width:0;max-width:100%;box-sizing:border-box;-webkit-appearance:none;appearance:none;display:block;flex:0 0 auto;text-align:center;font-weight:800;font-size:13px;padding:7px 2px;line-height:1.2}' +
            '#campPlan .cp-time::-webkit-date-and-time-value{text-align:center;min-height:1.2em}' +
            '@media (max-width:560px){#campPlan .cp-time::-webkit-calendar-picker-indicator{display:none}}' +
            '#campPlan .cp-col{flex:1 1 auto;min-width:0;display:flex;flex-direction:column;gap:6px}' +
            '#campPlan .cp-col input{width:100%}' +
            '#campPlan .cp-tcol{flex:0 0 136px;width:136px;min-width:0;display:flex;flex-direction:column;gap:6px}' +
            '@media (max-width:560px){#campPlan .cp-tcol{flex:0 0 98px;width:98px}}' +
            '#campPlan .cp-tcol .cp-time{width:100%}' +
            '#campPlan .cp-detail{display:block;text-align:center;font-size:12px;font-weight:800;color:#4f46e5;background:#eef2ff;border:1px solid #c7d2fe;border-radius:8px;padding:5px 0;text-decoration:none;line-height:1.2}' +
            '#campPlan .cp-detail:hover{background:#e0e7ff}' +
            '#campPlan button.cp-rinfo{width:100%;cursor:pointer;font-family:inherit;-webkit-appearance:none;appearance:none;color:#047857;background:#ecfdf5;border-color:#a7f3d0}' +
            '#campPlan button.cp-rinfo:hover{background:#d1fae5}' +
            '#campPlan .cp-mm{margin:0 0 14px;border:1px solid #e2e8f0;border-radius:14px;overflow:hidden;background:#fff}' +
            '#campPlan .cp-mmh{display:flex;gap:6px;align-items:center;flex-wrap:wrap;padding:8px 10px;background:#f8fafc;border-bottom:1px solid #e2e8f0;font-size:12.5px;font-weight:800;color:#334155}' +
            '#campPlan .cp-mmh button{border:1px solid #c7d2fe;background:#fff;color:#4f46e5;border-radius:999px;padding:4px 10px;font-size:12px;font-weight:800;line-height:1.2;font-family:inherit;cursor:pointer}' +
            '#campPlan .cp-mmh button.on{background:#4f46e5;color:#fff;border-color:#4f46e5}' +
            '#campPlan .cp-mmm{height:210px;background:#e2e8f0;position:relative}' +
            '#campPlan .cp-mmn{font-size:11.5px;color:#64748b;line-height:1.5;padding:6px 10px;background:#f8fafc}' +
            '#campPlan .cp-pin{width:26px;height:26px;border-radius:50%;background:#4f46e5;color:#fff;font:900 13px/22px sans-serif;text-align:center;border:2px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,.35);cursor:pointer}' +
            '#campPlan .cp-row.cp-flash{outline:3px solid #a5b4fc;outline-offset:2px;border-radius:12px;transition:outline-color .3s}' +
            '#campPlan .cp-share{margin-top:16px;padding:12px 14px;border:1px solid #c7d2fe;border-radius:14px;background:#f5f7ff}' +
            '#campPlan .cp-sh-t{font-size:14px;font-weight:900;color:#312e81;margin-bottom:4px}' +
            '#campPlan .cp-shl{display:block;font-size:12.5px;font-weight:800;color:#334155;line-height:1.5}#campPlan .cp-shl span{font-weight:600;color:#64748b}' +
            '#campPlan .cp-shurl{width:100%;box-sizing:border-box;margin-top:8px;padding:8px 10px;border:1px solid #cbd5e1;border-radius:10px;font-size:12px;color:#334155;background:#fff}' +
            '#campPlan .cp-col textarea,#campPlan .cp-add textarea{min-height:0;resize:none;overflow:hidden;line-height:1.45;display:block;white-space:pre-wrap;overflow-wrap:anywhere}' +
            '#campPlan .cp-col textarea{width:100%}' +
            '#campPlan .cp-add textarea{flex:1 1 auto;width:auto;min-width:0}' +
            '#campPlan .cp-title{font-weight:800}' +
            '#campPlan .cp-memo{font-size:13px!important;color:#475569}' +
            '#campPlan .cp-chips{display:flex;flex-wrap:wrap;gap:4px;margin-top:5px}' +
            '#campPlan .cp-bd{display:inline-block;font-size:11.5px;font-weight:800;line-height:1;padding:4px 8px;border-radius:999px;background:#f1f5f9;color:#475569;border:1px solid #e2e8f0}' +
            '#campPlan .cp-bd.in,#campPlan .cp-bd.out{background:#eff6ff;color:#1d4ed8;border-color:#bfdbfe}' +
            '#campPlan .cp-bd.free{background:#ecfdf5;color:#047857;border-color:#a7f3d0}' +
            '#campPlan .cp-btns{display:flex;flex-direction:column;gap:4px;flex:0 0 auto}' +
            '#campPlan .cp-ib{border:1px solid #cbd5e1;background:#fff;border-radius:8px;width:34px;height:30px;font-size:14px;font-weight:800;color:#334155;cursor:pointer;padding:0}' +
            '#campPlan .cp-ib:hover{background:#f1f5f9}' +
            '#campPlan .cp-ib.del{color:#b91c1c}' +
            '#campPlan .cp-btn{border:1px solid #cbd5e1;background:#fff;border-radius:10px;padding:8px 12px;font-size:13px;font-weight:800;color:#334155;cursor:pointer}' +
            '#campPlan .cp-btn:hover{background:#f1f5f9}' +
            '#campPlan .cp-btn.pri{background:#047857;border-color:#047857;color:#fff}' +
            '#campPlan .cp-btn.pri:hover{background:#065f46}' +
            '#campPlan .cp-btn.small{padding:5px 10px;font-size:12px}' +
            '#campPlan .cp-chips{display:flex;flex-wrap:wrap;gap:6px}' +
            '#campPlan .cp-chip{border:1px dashed #94a3b8;background:#fff;border-radius:999px;padding:6px 12px;font-size:12.5px;font-weight:700;color:#334155;cursor:pointer}' +
            '#campPlan .cp-chip:hover{background:#eef2ff;border-color:#818cf8}' +
            '#campPlan .cp-chip[disabled]{opacity:.5;cursor:default;background:#f1f5f9}' +
            '#campPlan .cp-chk{display:flex;gap:8px;align-items:flex-start;padding:7px 4px;font-size:13.5px;color:#1e293b;line-height:1.5;cursor:pointer;border-bottom:1px solid #f1f5f9}' +
            '#campPlan .cp-chk input{margin-top:3px;width:17px;height:17px;flex:0 0 auto}' +
            '#campPlan .cp-chk.on span{color:#94a3b8;text-decoration:line-through}' +
            '#campPlan .cp-chk .x{margin-left:auto;border:0;background:none;color:#b91c1c;font-weight:800;cursor:pointer}' +
            '#campPlan .cp-add{display:flex;gap:6px;margin-top:8px}' +
            '#campPlan .cp-add input{flex:1 1 auto;min-width:0}' +
            '#campPlan textarea{width:100%;min-height:84px;resize:vertical;line-height:1.6}' +
            '#campPlan .cp-acts{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}' +
            '#campPlan .cp-hint{margin-top:10px;padding:10px 12px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;font-size:12px;line-height:1.7;color:#475569}' +
            '#campPlan .cp-fest{margin:6px 0 0;padding:10px 12px;background:#fffbeb;border:1px solid #fde68a;border-radius:10px;font-size:12.5px;color:#92400e;line-height:1.6}' +
            '#campPlan .cp-bd.meal{background:#fff7ed;color:#c2410c;border-color:#fed7aa}' +
            '#campPlan .cp-meal{border:1px solid #fed7aa;background:#fffbf5;border-radius:12px;padding:12px;margin:8px 0}' +
            '#campPlan .cp-meal h4{margin:0 0 8px;font-size:14px;font-weight:900;color:#9a3412}' +
            '#campPlan .cp-meal select{font:inherit;font-size:13px;border:1px solid #cbd5e1;border-radius:8px;padding:6px;background:#fff;max-width:100%}' +
            '#campPlan .cp-mrow{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:6px 0;font-size:12.5px;color:#475569}' +
            '#campPlan .cp-mres{display:flex;gap:8px;align-items:flex-start;justify-content:space-between;border:1px solid #e2e8f0;background:#fff;border-radius:10px;padding:8px 10px;margin-top:6px}' +
            '#campPlan .cp-mres b{font-size:13.5px;color:#0f172a}' +
            '#campPlan .cp-mres .mi{font-size:12px;color:#64748b;line-height:1.5;word-break:keep-all}' +
            '#campPlan .cp-mres a{color:#4f46e5;font-weight:800;text-decoration:none}' +
            '#campPlan .cp-mnote{font-size:11.5px;color:#94a3b8;margin-top:8px;line-height:1.5}' +
            '#campPlan .cp-warn{font-size:12.5px;color:#b45309;background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:8px 12px;margin:0 0 10px;line-height:1.6}' +
            '@media (max-width:480px){#campPlan .cp-row{padding:7px}}' +
            // 인쇄: 일정표 종이(#cp-print-host)만 A4 한 장으로
            '#cp-print-host{display:none}' +
            '#campPlan .cp-paper{background:#fff;border:1px solid #94a3b8;border-radius:6px;padding:14px;margin-top:8px;overflow-x:auto}' +
            '#cpPaper .cpp table{min-width:430px}' +
            '#cp-print-host .cpp,#cpPaper .cpp{font-family:inherit;color:#111;font-size:12.5px;line-height:1.5}' +
            '#cp-print-host .cpp h1,#cpPaper .cpp h1{font-size:21px;margin:0 0 8px}' +
            '#cp-print-host .cpp .info,#cpPaper .cpp .info{border:1px solid #999;padding:7px 10px;margin-bottom:10px}' +
            '#cp-print-host .cpp .info div,#cpPaper .cpp .info div{margin:1px 0}' +
            '#cp-print-host .cpp h2,#cpPaper .cpp h2{font-size:14px;margin:12px 0 5px;padding-bottom:2px;border-bottom:2px solid #333}' +
            '#cp-print-host .cpp table,#cpPaper .cpp table{width:100%;border-collapse:collapse}' +
            '#cp-print-host .cpp th,#cp-print-host .cpp td,#cpPaper .cpp th,#cp-print-host .cpp td{border:1px solid #999;padding:4px 6px;text-align:left;vertical-align:top}' +
            '#cp-print-host .cpp th,#cpPaper .cpp th{background:#eee;font-size:12px}' +
            '#cp-print-host .cpp .cols,#cpPaper .cpp .cols{column-count:2;column-gap:18px}' +
            '#cp-print-host .cpp .ck,#cpPaper .cpp .ck{break-inside:avoid;margin:2px 0}' +
            '#cp-print-host .cpp .memo,#cpPaper .cpp .memo{border:1px solid #999;min-height:70px;padding:6px 8px;white-space:pre-wrap;margin-top:4px}' +
            '#cp-print-host .cpp .foot,#cpPaper .cpp .foot{margin-top:10px;font-size:11px;color:#555}' +
            '#cp-print-host .cpp .rt-cap,#cpPaper .cpp .rt-cap{font-size:11px;color:#64748b;margin:2px 0 0}' +
            '#cp-print-host .cpp .rt,#cpPaper .cpp .rt{display:flex;margin:4px 0 8px;padding-top:16px}' +
            '#cp-print-host .cpp .rt-n,#cpPaper .cpp .rt-n{flex:1 1 0;min-width:84px;position:relative;text-align:center}' +
            '#cp-print-host .cpp .rt-t,#cpPaper .cpp .rt-t{display:flex;align-items:center}' +
            '#cp-print-host .cpp .rt-t i,#cpPaper .cpp .rt-t i{flex:1;height:0;border-top:2px solid #64748b}' +
            '#cp-print-host .cpp .rt-t i.off,#cpPaper .cpp .rt-t i.off{border-top-color:transparent}' +
            '#cp-print-host .cpp .rt-t b,#cpPaper .cpp .rt-t b{flex:none;width:26px;height:26px;box-sizing:border-box;border:2px solid #334155;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:800;color:#111;background:#fff;line-height:1}' +
            '#cp-print-host .cpp .rt-d,#cpPaper .cpp .rt-d{position:absolute;left:0;top:-15px;transform:translateX(-50%);font-size:10px;color:#475569;white-space:nowrap}' +
            '#cp-print-host .cpp .rt-nm,#cpPaper .cpp .rt-nm{font-size:11.5px;font-weight:700;line-height:1.3;margin-top:4px;padding:0 3px;overflow-wrap:anywhere;min-height:2.6em}' +
            '#cp-print-host .cpp .rt-tm,#cpPaper .cpp .rt-tm{font-size:11px;color:#334155;margin-top:1px}' +
            '#cp-print-host .cpp .rt-hr,#cpPaper .cpp .rt-hr{font-size:10px;color:#64748b;margin-top:1px;line-height:1.3;padding:0 2px}' +
            '@media print{' +
            'body.cp-printing > *:not(#cp-print-host){display:none!important}' +
            'body.cp-printing #cp-print-host{display:block!important}' +
            '@page{size:A4;margin:12mm}' +
            '}';
        document.head.appendChild(st);
    }

    // [ADD] 2026-11-19: 일정 줄의 장소 상세페이지 링크(시간 칸 아래) + 일정·메모 칸 자동 줄바꿈
    // 예전에 저장된 일정(pid 없음)도 장소 이름으로 찾아 링크를 붙인다.
    function rowPid(r) {
        var id = r.pid || '';
        if (!id && cur) {
            if (r.k === 'c' || r.k === 'in') id = cur.hasDetail === false ? '' : cur.contentid;
            else if (r.k === 'n' && cur._near) {
                var t = String(r.title || '').replace(/^\S+\s/, '').trim();
                for (var i = 0; i < cur._near.length; i++) { if (cur._near[i] && cur._near[i].title === t) { id = cur._near[i].contentid; break; } }
            }
        }
        return /^[A-Za-z0-9_\-]+$/.test(String(id || '')) ? String(id) : '';
    }
    // 예전에 저장된 줄(tg 없음)은 지금 열린 장소·근처 목록에서 찾아 본다. 못 찾으면 배지를 안 보여 준다.
    function rowTags(r) {
        if (r && r.tg) return r.tg;
        if (!cur || !r) return [];
        if (r.k === 'c') return tagsOf(cur);
        if (r.k === 'n' && cur._near) {
            var pid = rowPid(r);
            for (var i = 0; i < cur._near.length; i++) { if (cur._near[i] && pid && cur._near[i].contentid === pid) return tagsOf(cur._near[i]); }
        }
        return [];
    }
    function chipsHtml(tags) {
        if (!tags || !tags.length) return '';
        var h = '<div class="cp-chips" aria-label="장소 정보">';
        tags.forEach(function (t) { h += '<span class="cp-bd' + (t[0] ? ' ' + esc(t[0]) : '') + '">' + esc(t[1]) + '</span>'; });
        return h + '</div>';
    }
    // [CHG] 2026-11-20: 시간 칸을 시간 입력창(type=time)으로 — 숫자 직접 입력도 되고 시간 선택창(드롭다운·휠)도 열린다.
    // 예전에 저장된 글자(예: 1330)는 HH:MM으로 바꿔 보여주고, 알아볼 수 없으면 빈 칸으로 둔다(저장값은 그대로).
    function timeVal(v) {
        var s = String(v || '');
        if (/^\d{2}:\d{2}$/.test(s)) return s;
        var d = s.replace(/[^0-9]/g, ''), h, m;
        if (!d) return '';
        if (d.length <= 2) { h = +d; m = 0; } else if (d.length === 3) { h = +d.slice(0, 1); m = +d.slice(1); } else { h = +d.slice(0, 2); m = +d.slice(2, 4); }
        if (h > 23 || m > 59) return '';
        return ('0' + h).slice(-2) + ':' + ('0' + m).slice(-2);
    }
    function rowHtml(r) {
        var pid = rowPid(r);
        return '<div class="cp-row" data-id="' + r.id + '">' +
            '<div class="cp-tcol">' +
            '<input class="cp-time" type="time" step="300" value="' + esc(timeVal(r.time)) + '" data-f="time" aria-label="시간 (직접 입력하거나 선택, 예 13:30)">' +
            (pid ? '<a class="cp-detail" href="/festival/detail/' + pid + '.html" aria-label="장소 상세페이지 (팝업)">상세보기</a>' : '') +
            (r.info ? '<button type="button" class="cp-detail cp-rinfo" data-act="rowinfo" aria-label="장소 정보 (팝업)">정보보기</button>' : '') +
            '</div>' +
            '<div class="cp-col">' +
            '<textarea class="cp-title" rows="1" maxlength="60" data-f="title" placeholder="일정" aria-label="일정">' + esc(r.title) + '</textarea>' +
            '<textarea class="cp-memo" rows="1" maxlength="100" data-f="memo" placeholder="메모 (예: 예약번호, 준비할 것)" aria-label="메모">' + esc(r.memo) + '</textarea>' +
            chipsHtml(rowTags(r)) +
            '</div>' +
            '<div class="cp-btns">' +
            '<button type="button" class="cp-ib" data-act="up" aria-label="위로">↑</button>' +
            '<button type="button" class="cp-ib" data-act="down" aria-label="아래로">↓</button>' +
            '<button type="button" class="cp-ib del" data-act="del" aria-label="삭제">✕</button>' +
            '</div></div>';
    }
    function chkHtml(id, text, removable) {
        return '<label class="cp-chk' + (isOn(id) ? ' on' : '') + '"><input type="checkbox" data-chk="' + esc(id) + '"' + (isOn(id) ? ' checked' : '') + '><span>' + esc(text) + '</span>' +
            (removable ? '<button type="button" class="x" data-act="xextra" data-id="' + esc(id) + '" aria-label="삭제">✕</button>' : '') + '</label>';
    }

    // 글자 칸 높이를 글자 수에 맞춘다(길게 쓰면 자동으로 아래 줄로 내려가 모두 보인다). 화면에 안 보이는 동안엔 높이를 못 재므로 건너뛴다.
    function fit(el) {
        if (!el || !el.scrollHeight) return;
        el.style.height = 'auto';
        el.style.height = (el.scrollHeight + 2) + 'px';
    }
    function fitAll() {
        if (!root) return;
        var a = root.querySelectorAll('.cp-col textarea, #cpExtraIn');
        for (var i = 0; i < a.length; i++) fit(a[i]);
    }
    var fitTimer = 0;
    function onResize() { clearTimeout(fitTimer); fitTimer = setTimeout(fitAll, 120); }

    function render() {
        var h = '';
        h += '<a href="#result" class="cp-back" data-act="back">↑ 결과로 돌아가기</a>';
        h += '<h2>' + cfg.title + '</h2>';
        h += '<p class="cp-sub">' + fill(cfg.sub) + '</p>';

        h += '<div id="cpMMslot" style="display:none"></div>';   // 코스 미니맵(번호 핀 + 점선)

        // 캠핑장 정보
        h += '<div class="cp-box"><div class="cp-cname">' + cfg.icon + ' ' + esc(cur.title) + '</div>';
        if (cur.addr) h += '<div class="cp-line">📍 ' + esc(cur.addr) + '</div>';
        if (tel()) h += '<div class="cp-line">☎ <a href="tel:' + esc(tel().replace(/[^0-9+\-]/g, '')) + '">' + esc(tel()) + '</a>' + cfg.telNote + '</div>';
        h += '<div class="cp-date"><label for="cpDate">' + cfg.dateLabel + '</label><input type="date" id="cpDate" value="' + esc(P.date) + '"><span style="font-weight:600;color:#94a3b8;font-size:12px">(선택)</span></div>' +
            (cfg.hasFest ? '<div class="cp-line" id="cpDateNote" style="display:none;color:#b45309">근처 장소는 오늘 기준으로 골랐어요. 그날의 운영·휴관일은 확인표로 꼭 확인하세요.</div>' : '') + '</div>';

        if (cfg.noNear && !(cur._near && cur._near.length)) {
            h += '<div class="cp-warn">' + fill(cfg.noNear) + '</div>';
        }

        // 일정
        for (var d = 1; d <= P.days; d++) {
            h += '<div class="cp-dayhd"><span>' + esc(dayLabel(d)) + '</span></div>';
            P.rows.forEach(function (r) { if (r.day === d) h += rowHtml(r); });
            h += '<button type="button" class="cp-btn small" data-act="addrow" data-day="' + d + '">＋ 일정 추가</button> ' +
                '<button type="button" class="cp-btn small" data-act="mealopen" data-day="' + d + '">🍴 식당·카페 넣기</button>' +
                ' <button type="button" class="cp-btn small" data-act="stayopen" data-day="' + d + '">🏨 숙박 넣기</button>';
            if (mealUI && mealUI.day === d) h += '<div id="cpMeal" class="cp-meal">' + mealInner() + '</div>';
        }

        // 축제 넣기 스위치 (하루 나들이 틀에서만)
        if (cfg.hasFest) {
            h += '<h3>🎪 축제도 넣을까요?</h3>';
            h += '<label class="cp-chk"><input type="checkbox" id="cpFestOn"' + (P.fest ? ' checked' : '') + '><span>그날 근처에서 열리는 축제를 후보로 보여 주세요 (켜면 날짜가 필요해요)</span></label>';
            if (P.fest) h += '<div id="cpFestBox" class="cp-fest"></div>';
        }

        // 근처 후보
        if (cur._near && cur._near.length) {
            var have = {};
            P.rows.forEach(function (r) { have[String(r.title).replace(/^📍\s*/, '')] = true; });
            // 이미 일정에 담은 곳은 빼고, 더 넣을 곳이 남아 있을 때만 보여 준다.
            var left = [];
            cur._near.forEach(function (n, i) { if (!have[n.title]) left.push([n, i]); });
            if (left.length) {
                h += '<h3>🧸 근처 아이랑 장소 더 넣기 <span style="font-size:11.5px;font-weight:600;color:#94a3b8">눌러서 1일차에 넣기</span></h3><div class="cp-chips">';
                left.forEach(function (x) {
                    h += '<button type="button" class="cp-chip" data-act="addnear" data-i="' + x[1] + '">＋ ' + esc(x[0].title) + ' · ' + esc(fmtKm(x[0].km)) + '</button>';
                });
                h += '</div>';
            }
        }

        // 확인표
        h += '<h3>✅ 출발 전 확인표</h3>';
        h += '<p class="cp-sub" style="margin-bottom:4px">' + cfg.checkNote + '</p>';
        cfg.checkA.forEach(function (c) { h += chkHtml(c[0], fill(c[1]), false); });
        var nc = nearChecks();
        if (nc.length) {
            h += '<div class="cp-sub" style="margin:12px 0 2px;font-weight:800;color:#334155">들를 곳 확인</div>';
            nc.forEach(function (c) { h += chkHtml(c[0], c[1], false); });
        }
        h += '<div class="cp-sub" style="margin:12px 0 2px;font-weight:800;color:#334155">준비물</div>';
        cfg.checkB.forEach(function (c) { h += chkHtml(c[0], c[1], false); });
        P.extra.forEach(function (c) { h += chkHtml(c.id, c.text, true); });
        h += '<div class="cp-add"><textarea id="cpExtraIn" rows="1" maxlength="40" placeholder="내 준비물·할 일 추가"></textarea><button type="button" class="cp-btn small" data-act="addextra">추가</button></div>';

        // 메모
        h += '<h3>📝 메모</h3><textarea id="cpNote" maxlength="600" placeholder="예약 번호, 차량 번호, 같이 가는 사람, 장볼 목록 등을 적어 두세요.">' + esc(P.note) + '</textarea>';

        h += '<h3>📄 일정표 미리보기 <span style="font-size:11.5px;font-weight:600;color:#94a3b8">(A4 한 장)</span></h3><div id="cpPaper" class="cp-paper">' + paperHtml() + '</div>';
        h += '<div class="cp-acts"><button type="button" class="cp-btn pri" data-act="print">🖨️ 일정표 인쇄·PDF 저장</button><button type="button" class="cp-btn" data-act="reset">↺ 처음 상태로</button></div>';
        h += '<div class="cp-share"><div class="cp-sh-t">📤 일정표 보내기</div>' +
            '<div class="cp-sub" style="margin:0 0 8px">링크를 받은 사람은 이 일정표를 자기 폰에서 열어 고칠 수 있어요. 보낸 사람의 일정표는 바뀌지 않아요.</div>' +
            '<label class="cp-shl"><input type="checkbox" id="cpShareMemo"> 메모도 같이 보내기 <span>(예약번호·전화번호 등이 있으면 끄세요)</span></label>' +
            '<div class="cp-acts" style="margin-top:8px"><button type="button" class="cp-btn pri" data-act="share">📤 공유</button><button type="button" class="cp-btn" data-act="sharecopy">🔗 링크 복사</button></div>' +
            '<input type="text" id="cpShareUrl" class="cp-shurl" readonly style="display:none" aria-label="공유 링크"><div id="cpShareMsg" class="cp-sub" style="margin:6px 0 0" role="status"></div></div>';
        h += '<div class="cp-hint"><b style="color:#334155">PDF로 저장하는 방법</b><br>인쇄 창에서 <b>대상(프린터)</b> 칸을 눌러 “PDF로 저장”(또는 “Microsoft Print to PDF”)을 고른 뒤, 오른쪽 아래 버튼이 “저장”으로 바뀌면 누르세요. 편집한 내용은 이 기기에만 저장되고 서버로 보내지 않아요.</div>';
        root.innerHTML = h;
        mmAttach();
        fitAll();
        updateDateNote();
        if (cfg.hasFest && P.fest) updateFest();
    }

    // 새로 넣는 줄의 시간: 바로 앞 줄 시간 + 1시간 30분(앞 줄 시간을 읽을 수 없으면 기본값)
    function timeAfter(idx, fallback) {
        var prev = idx > 0 ? P.rows[idx - 1] : null;
        var m = prev && /^(\d{1,2}):(\d{2})$/.exec(String(prev.time || ''));
        if (!m) return fallback;
        var t = +m[1] * 60 + +m[2] + 90;
        if (t > 21 * 60) t = 21 * 60;
        return ('0' + Math.floor(t / 60)).slice(-2) + ':' + ('0' + (t % 60)).slice(-2);
    }
    function clip(t, n) { t = String(t || '').replace(/\s+/g, ' ').trim(); return t.length > n ? t.slice(0, n).trimEnd() + '…' : t; }

    // ── 축제 넣기 (하루 나들이 틀) ───────────────────────────────────────────────────
    var festData = null, festErr = false, festList = [];
    function todayKST() { return new Date(Date.now() + 9 * 3600 * 1000).toISOString().slice(0, 10); }
    function kmBetween(a, b, c, d) {
        var R = 6371, rad = Math.PI / 180, dl = (c - a) * rad, dg = (d - b) * rad;
        var x = Math.sin(dl / 2) * Math.sin(dl / 2) + Math.cos(a * rad) * Math.cos(c * rad) * Math.sin(dg / 2) * Math.sin(dg / 2);
        return 2 * R * Math.asin(Math.min(1, Math.sqrt(x)));
    }
    function md(s) { return s && s.length === 8 ? (+s.slice(4, 6)) + '.' + (+s.slice(6, 8)) : ''; }
    function loadFestData(cb) {
        if (festData) { cb(); return; }
        fetch('/data/festivals.json').then(function (r) { return r.ok ? r.json() : []; }).then(function (a) {
            festData = Array.isArray(a) ? a : []; cb();
        }).catch(function () { festData = []; festErr = true; cb(); });
    }
    function updateDateNote() {
        var n = $('cpDateNote');
        if (n) n.style.display = (P.date && P.date !== todayKST()) ? '' : 'none';
    }
    function updateFest() {
        var box = $('cpFestBox');
        if (!box) return;
        if (!P.date) { box.textContent = '위쪽 “나들이 날짜”를 고르면 그날 열리는 근처 축제를 보여 드려요.'; return; }
        box.textContent = '축제 정보를 불러오는 중이에요…';
        loadFestData(function () {
            var b = $('cpFestBox'); if (!b) return;
            var lat = +cur.lat, lng = +cur.lng;
            if (festErr) { b.textContent = '축제 정보를 불러오지 못했어요. 잠시 뒤 다시 시도해 주세요.'; festErr = false; festData = null; return; }
            if (!isFinite(lat) || !isFinite(lng)) { b.textContent = '우승 장소의 좌표가 없어서 근처 축제를 찾지 못했어요.'; return; }
            var key = P.date.replace(/-/g, '');
            var have = {}; P.rows.forEach(function (r) { have[String(r.title).replace(/^(?:📍|🎪)\s*/, '')] = true; });
            festList = festData.filter(function (f) {
                return f && f.type === 'festival' && f.startDate <= key && key <= f.endDate && isFinite(+f.lat) && isFinite(+f.lng) && !have[f.title];
            }).map(function (f) { return { f: f, km: kmBetween(lat, lng, +f.lat, +f.lng) }; })
              .filter(function (x) { return x.km <= 40; })
              .sort(function (a, c) { return a.km - c.km; }).slice(0, 6);
            if (!festList.length) { b.innerHTML = '이 날짜에 우승 장소 근처(40km 안)에서 열리는 축제가 없어요. 다른 날짜를 골라 보세요.'; return; }
            var h = '<div class="cp-chips">';
            festList.forEach(function (x, i) {
                h += '<button type="button" class="cp-chip" data-act="addfest" data-i="' + i + '">＋ 🎪 ' + esc(x.f.title) + ' · ' + esc(fmtKm(x.km)) + ' · ' + esc(md(x.f.startDate) + '~' + md(x.f.endDate)) + '</button>';
            });
            h += '</div><div class="cp-sub" style="margin:8px 0 0">축제 정보는 한국관광공사 TourAPI 기준이에요. 행사 시간·장소는 공식 안내를 꼭 확인하세요.</div>';
            b.innerHTML = h;
        });
    }


    // ── 식사 칸: 카카오 장소검색으로 앞 장소 근처 음식점·카페 찾기 ────────────────────────────
    function withKakao(ok, fail) {
        function ready() { return window.kakao && kakao.maps && kakao.maps.services; }
        if (ready()) { ok(); return; }
        function go() { try { kakao.maps.load(function () { ready() ? ok() : fail(); }); } catch (e) { fail(); } }
        if (window.kakao && kakao.maps && kakao.maps.load) { go(); return; }
        var ex = document.getElementById('cp-kakao-sdk');
        if (ex) { ex.addEventListener('load', go); ex.addEventListener('error', fail); return; }
        var s = document.createElement('script');
        s.id = 'cp-kakao-sdk';
        s.src = 'https://dapi.kakao.com/v2/maps/sdk.js?appkey=' + KAKAO_KEY + '&libraries=services&autoload=false';
        s.onload = go; s.onerror = function () { s.parentNode && s.parentNode.removeChild(s); fail(); };
        document.head.appendChild(s);
    }
    function dayGeoRows(d) { return P.rows.filter(function (r) { return r.day === d && r.lat != null && isFinite(+r.lat) && isFinite(+r.lng); }); }
    function lunchPlaceholder(d) {
        for (var i = 0; i < P.rows.length; i++) { var r = P.rows[i]; if (r.day === d && r.k === 'x' && /^(점심|식사|브런치)/.test(plainTitle(r.title))) return r; }
        return null;
    }
    // 기준 장소: 점심 칸이 있으면 그 바로 앞 장소, 없으면 12:30 이전의 마지막 장소(없으면 첫 장소)
    function defaultRef(d) {
        var lp = lunchPlaceholder(d), best = null, any = null;
        for (var i = 0; i < P.rows.length; i++) {
            var r = P.rows[i];
            if (r.day !== d) continue;
            if (lp && r.id === lp.id) break;
            if (r.lat != null && isFinite(+r.lat) && isFinite(+r.lng)) {
                if (!any) any = r;
                if (lp || !r.time || timeVal(r.time) <= '12:30') best = r;
            }
        }
        return (best || any || {}).id || '';
    }
    function mealOpen(d, stay) {
        var geo = dayGeoRows(d);
        mealUI = { day: d, ref: defaultRef(d), cat: 'FD6', q: '', rad: 1000, rep: true, results: null, status: '', busy: false };
        if (stay) {
            // 숙박: 그날 마지막으로 위치가 있는 줄을 기준으로, 반경은 넓게(5km)
            var lg = geo.length ? geo[geo.length - 1] : null;
            mealUI.mode = 'stay'; mealUI.cat = 'AD5'; mealUI.kw = ''; mealUI.rad = 5000; mealUI.rep = false; mealUI.ref = lg ? lg.id : mealUI.ref;
        }
        if (!mealUI.ref && !geo.length && !(cur && isFinite(+cur.lat) && isFinite(+cur.lng))) mealUI.status = '기준이 될 장소 위치가 없어요. 아래 검색창에 "지역 + 음식 종류"(예: 차이나타운 짜장면)를 넣어 찾아 보세요.';
    }
    function refPoint() {
        var r = null;
        if (mealUI.ref) { var i = rowIndex(mealUI.ref); if (i >= 0) r = P.rows[i]; }
        if (r && r.lat != null && isFinite(+r.lat)) return { lat: +r.lat, lng: +r.lng, name: plainTitle(r.title) };
        if (cur && isFinite(+cur.lat) && isFinite(+cur.lng) && cur.lat !== '' && cur.lat != null) return { lat: +cur.lat, lng: +cur.lng, name: plainTitle(cur.title) };
        return null;
    }
    // 숙박 종류 칩: 키워드는 카카오 키워드 검색에 쓰고, 결과는 숙박(AD5)만 남긴다
    var STAY_CHIPS = [['', '🏨 전체'], ['호텔', '호텔'], ['리조트', '리조트·콘도'], ['풀빌라', '풀빌라'], ['펜션', '펜션'], ['글램핑', '글램핑']];
    // 모텔촌 거르기: 분류·이름에 이 말이 들어 있으면 뺀다
    var STAY_BAD = /모텔|여관|여인숙|휴게텔|무인텔|대실|파티룸|스파룸|룸카페|찜질|사우나|호스텔|게스트하우스|MOTEL/i;
    function mealInner() {
        var u = mealUI, stay = u.mode === 'stay', h = '<h4>' + (stay ? '🏨 숙박 찾아서 넣기' : '🍴 식당·카페 찾아서 넣기') + '</h4>';
        var geo = dayGeoRows(u.day);
        if (geo.length) {
            h += '<div class="cp-mrow"><label for="cpMealRef">기준 장소</label><select id="cpMealRef">';
            geo.forEach(function (r) { h += '<option value="' + esc(r.id) + '"' + (r.id === u.ref ? ' selected' : '') + '>' + esc(clip(plainTitle(r.title), 20)) + (r.time ? ' (' + esc(timeVal(r.time)) + ')' : '') + '</option>'; });
            h += '</select><label for="cpMealRad">반경</label><select id="cpMealRad">';
            (stay ? [[3000, '3km'], [5000, '5km'], [10000, '10km'], [20000, '20km']] : [[500, '500m'], [1000, '1km'], [2000, '2km'], [3000, '3km']]).forEach(function (x) { h += '<option value="' + x[0] + '"' + (x[0] === u.rad ? ' selected' : '') + '>' + x[1] + '</option>'; });
            h += '</select></div>';
        }
        if (stay) {
            h += '<div class="cp-mrow">';
            STAY_CHIPS.forEach(function (c) { h += '<button type="button" class="cp-chip" data-act="staycat" data-kw="' + esc(c[0]) + '"' + (!u.q && (u.kw || '') === c[0] ? ' style="background:#eef2ff;border-style:solid"' : '') + '>' + esc(c[1]) + '</button>'; });
            h += '</div>';
        } else h += '<div class="cp-mrow"><button type="button" class="cp-chip" data-act="mealcat" data-cat="FD6"' + (u.cat === 'FD6' && !u.q ? ' style="background:#eef2ff;border-style:solid"' : '') + '>🍚 음식점</button>' +
            '<button type="button" class="cp-chip" data-act="mealcat" data-cat="CE7"' + (u.cat === 'CE7' && !u.q ? ' style="background:#eef2ff;border-style:solid"' : '') + '>☕ 카페</button>' +
            '<button type="button" class="cp-chip" data-act="mealkid"' + (u.kid ? ' style="background:#eef2ff;border-style:solid"' : '') + '>🎠 키즈카페</button></div>';
        h += '<div class="cp-mrow"><input type="text" id="cpMealQ" maxlength="30" placeholder="' + (stay ? '직접 검색 (예: 키즈 풀빌라, 가족 펜션, 키즈 호텔)' : '직접 검색 (예: 칼국수, 돈까스, 키즈카페)') + '" value="' + esc(u.q) + '" style="flex:1 1 160px"><button type="button" class="cp-btn small" data-act="mealsearch">검색</button></div>';
        if (!stay && !u.kid && lunchPlaceholder(u.day)) h += '<label class="cp-chk" style="border:0;padding:2px 0"><input type="checkbox" id="cpMealRep"' + (u.rep ? ' checked' : '') + '><span>일정의 “점심” 줄을 고른 곳으로 바꾸기</span></label>';
        if (u.busy) h += '<div class="cp-mnote">찾는 중이에요…</div>';
        else if (u.status) h += '<div class="cp-mnote" style="color:#b45309">' + esc(u.status) + '</div>';
        if (u.results) {
            if (!u.results.length) h += '<div class="cp-mnote">근처에서 찾지 못했어요. 반경을 넓히거나 다른 검색어를 써 보세요.</div>';
            u.results.forEach(function (x, i) {
                h += '<div class="cp-mres"><div><b>' + esc(x.name) + '</b><div class="mi">' + esc(x.cat) + (x.km != null ? ' · 기준 장소에서 약 ' + esc(fmtKm(x.km)) : '') + (x.addr ? '<br>' + esc(x.addr) : '') + (x.phone ? ' · ☎ ' + esc(x.phone) : '') + '</div>' +
                    (x.url ? '<a class="mi" href="' + esc(x.url) + '" target="_blank" rel="noopener">카카오맵에서 보기 ↗</a>' : '') + '</div>' +
                    '<div style="display:flex;flex-direction:column;gap:6px;flex:none"><button type="button" class="cp-btn small" data-act="mealinfo" data-i="' + i + '">정보 보기</button>' +
                    '<button type="button" class="cp-btn small pri" data-act="mealadd" data-i="' + i + '">＋ 넣기</button></div></div>';
            });
        }
        h += '<div class="cp-mnote">' + (stay ? '검색 결과는 카카오맵 기준이에요(모텔·여관 등은 뺐어요). 키즈 전용 여부·요금·예약 가능 여부·체크인 시간은 카카오맵이나 전화로 꼭 확인하세요.' : '검색 결과는 카카오맵 기준이에요. 영업시간·휴무·메뉴·예약은 카카오맵이나 전화로 꼭 확인하세요.') + '</div>' +
            '<div class="cp-mrow" style="margin-top:8px"><input type="text" id="cpMealMan" maxlength="30" placeholder="찾는 곳이 없으면 이름 직접 입력" style="flex:1 1 160px"><button type="button" class="cp-btn small" data-act="mealman">직접 넣기</button><button type="button" class="cp-btn small" data-act="mealclose">닫기</button></div>';
        return h;
    }
    function mealRefresh() { var b = $('cpMeal'); if (b && mealUI) { b.innerHTML = mealInner(); fitAll(); } }
    function mealSearch() {
        var u = mealUI; if (!u || u.busy) return;
        var pt = refPoint(), q = (u.q || '').trim();
        if (!pt && !q) { u.status = '기준 장소 위치가 없어요. 검색어를 입력해 주세요.'; mealRefresh(); return; }
        u.busy = true; u.status = ''; u.results = null; mealRefresh();
        var done = function (data, st) {
            if (!mealUI || mealUI !== u) return;
            u.busy = false;
            var S = window.kakao && kakao.maps && kakao.maps.services;
            if (S && st === S.Status.OK) {
                if (u.mode === 'stay') {
                    data = data.filter(function (p) { return p.category_group_code === 'AD5' && !STAY_BAD.test(String(p.category_name || '') + ' ' + String(p.place_name || '')); });
                }
                if (u.kid) {
                    var kd = data.filter(function (p) { return /키즈|놀이터|놀이방|실내놀이/.test(String(p.category_name || '') + ' ' + String(p.place_name || '')); });
                    if (kd.length) data = kd;
                }
                u.results = data.slice(0, 8).map(function (p) {
                    var parts = String(p.category_name || '').split('>').map(function (z) { return z.trim(); }).filter(Boolean);
                    var km = (pt && isFinite(+p.y) && isFinite(+p.x)) ? kmBetween(pt.lat, pt.lng, +p.y, +p.x) : null;
                    return { name: p.place_name, cat: clip(parts.slice(1).join('·') || parts[0] || '', 22), addr: p.road_address_name || p.address_name || '', phone: p.phone || '', url: /^https?:\/\//.test(p.place_url || '') ? p.place_url : '', lat: +p.y, lng: +p.x, km: km };
                });
            } else if (S && st === S.Status.ZERO_RESULT) u.results = [];
            else u.status = '검색하지 못했어요. 잠시 뒤 다시 시도하거나 아래에서 직접 넣어 주세요.';
            mealRefresh();
        };
        withKakao(function () {
            var ps = new kakao.maps.services.Places();
            var o = { size: u.mode === 'stay' ? 15 : 10 };
            if (pt) { o.location = new kakao.maps.LatLng(pt.lat, pt.lng); o.radius = u.rad; o.sort = kakao.maps.services.SortBy.DISTANCE; }
            if (u.mode === 'stay') {
                var kw = q || u.kw;
                if (kw) { o.category_group_code = 'AD5'; ps.keywordSearch(kw, done, o); } else ps.categorySearch('AD5', done, o);
            } else if (q) ps.keywordSearch(q, done, o); else ps.categorySearch(u.cat, done, o);
        }, function () { u.busy = false; u.status = '검색 서비스를 불러오지 못했어요. 아래에서 직접 넣어 주세요.'; mealRefresh(); });
    }
    // 고른 곳을 일정에 넣는다: "점심" 칸이 있고 체크돼 있으면 그 칸을 바꾸고, 아니면 기준 장소 바로 뒤에 새 줄

    // ── 장소 정보 팝업 (식당·카페·숙박·키즈카페 검색 결과) ──────────────────────────────
    //   카카오 장소검색이 준 정보(이름·분류·주소·전화·거리·위치)만 보여 주고, 사진·영업시간·후기는 카카오맵 링크로 안내한다.
    //   장소 상세처럼 아래에서 올라오고, 닫기(✕)는 오른쪽 아래. 팝업 안에서 바로 일정에 넣을 수 있다.
    var infoEl = null, infoPushed = false, infoIdx = -1, infoMap = null;
    function infoCss() {
        if (document.getElementById('cpInfoCss')) return;
        var st = document.createElement('style'); st.id = 'cpInfoCss';
        st.textContent = '#cpInfo{position:fixed;left:0;top:0;right:0;bottom:0;z-index:2147483640;display:none;font-family:inherit}#cpInfo.on{display:block}' +
            '#cpInfo .ci-bd{position:absolute;left:0;top:0;right:0;bottom:0;background:rgba(15,23,42,.45)}' +
            '#cpInfo .ci-pn{position:absolute;left:0;right:0;bottom:0;max-height:82vh;overflow:auto;background:#fff;border-radius:18px 18px 0 0;padding:10px 18px 24px;box-shadow:0 -8px 30px rgba(0,0,0,.25);transform:translateY(100%);transition:transform .28s ease;max-width:640px;margin:0 auto;-webkit-overflow-scrolling:touch}' +
            '#cpInfo.up .ci-pn{transform:none}' +
            '#cpInfo .ci-bar{width:44px;height:5px;border-radius:3px;background:#cbd5e1;margin:0 auto 12px}' +
            '#cpInfo h3{margin:0 0 4px;font-size:18px;line-height:1.35;color:#0f172a;word-break:keep-all}' +
            '#cpInfo .ci-tags{display:flex;gap:6px;flex-wrap:wrap;margin:6px 0 10px}#cpInfo .ci-tags i{font-style:normal;font-size:12px;font-weight:800;padding:3px 9px;border-radius:999px;background:#eef2ff;color:#4338ca}' +
            '#cpInfo .ci-row{font-size:14px;line-height:1.6;color:#334155;margin:4px 0;word-break:keep-all}#cpInfo .ci-row b{color:#0f172a}' +
            '#cpInfo .ci-map{height:170px;border-radius:12px;margin:12px 0;background:#e2e8f0;overflow:hidden}' +
            '#cpInfo .ci-note{font-size:12.5px;color:#64748b;line-height:1.55;margin:8px 0 14px;padding:10px 12px;background:#f8fafc;border-radius:10px}' +
            '#cpInfo .ci-act{display:flex;gap:8px;flex-wrap:wrap;padding-right:70px;min-height:52px}' +
            '#cpInfo .ci-act a,#cpInfo .ci-act button{flex:1 1 auto;text-align:center;border:1px solid #4f46e5;color:#4f46e5;background:#fff;border-radius:12px;padding:12px 10px;font:800 14px/1.2 inherit;font-family:inherit;text-decoration:none;cursor:pointer}' +
            '#cpInfo .ci-act .p{background:#4f46e5;color:#fff}' +
            '#cpInfo .ci-x{position:fixed;right:16px;bottom:16px;bottom:calc(16px + env(safe-area-inset-bottom,0px));z-index:3;width:52px;height:52px;border-radius:50%;border:0;background:#0f172a;color:#fff;font-size:22px;cursor:pointer;box-shadow:0 4px 14px rgba(0,0,0,.35)}';
        document.head.appendChild(st);
    }
    function infoBuild() {
        if (infoEl) return;
        infoEl = document.createElement('div'); infoEl.id = 'cpInfo';
        infoEl.innerHTML = '<div class="ci-bd"></div><div class="ci-pn" role="dialog" aria-label="장소 정보"><div class="ci-bar"></div><div class="ci-c"></div></div><button type="button" class="ci-x" aria-label="닫기">✕</button>';
        document.body.appendChild(infoEl);
        infoEl.querySelector('.ci-bd').addEventListener('click', function () { infoClose(); });
        infoEl.querySelector('.ci-x').addEventListener('click', function () { infoClose(); });
        infoEl.addEventListener('click', function (e) {
            var b = e.target.closest ? e.target.closest('[data-ci="add"]') : null;
            if (!b) return;
            var i = infoIdx; infoClose(true);
            setTimeout(function () { var btn = document.querySelector('#cpMeal [data-act="mealadd"][data-i="' + i + '"]'); if (btn) btn.click(); }, 60);
        });
        window.addEventListener('keydown', function (e) {
            if (infoEl && infoEl.classList.contains('on') && (e.key === 'Escape' || e.key === 'Esc')) { e.preventDefault(); e.stopPropagation(); infoClose(); }
        }, true);
        // 휴대폰 뒤로가기: 팝업만 닫는다(일정표 창은 그대로). plan-modal.js 가 이 표시를 보고 일정표를 닫지 않는다.
        window.addEventListener('popstate', function () {
            if (infoEl && infoEl.classList.contains('on')) { infoPushed = false; infoHide(); }
            setTimeout(function () { window.__cpInfoSkip = false; }, 0);
        });
    }
    function infoHide() {
        if (!infoEl) return;
        infoEl.classList.remove('up');
        var el = infoEl; setTimeout(function () { if (!el.classList.contains('up')) el.classList.remove('on'); }, 300);
        infoMap = null;
        document.documentElement.style.overflow = infoPrevOv;
    }
    var infoPrevOv = '';
    function infoClose(noBack) {
        if (!infoEl || !infoEl.classList.contains('on')) return;
        infoHide();
        if (infoPushed) {
            infoPushed = false;
            window.__cpInfoSkip = true;
            setTimeout(function () { window.__cpInfoSkip = false; }, 700);
            try { history.back(); } catch (_) { window.__cpInfoSkip = false; }
        }
    }
    function infoOpen(x, idx, rowKind) {
        infoCss(); infoBuild();
        infoIdx = idx;
        var u = mealUI || {}, pt = (mealUI && !rowKind) ? refPoint() : null;
        if (rowKind) u = { mode: rowKind === 'stay' ? 'stay' : '', kid: rowKind === 'kid' };   // 일정 줄에서 연 팝업: 안내문만 종류에 맞추고, '일정에 넣기'는 뺀다
        var note = u.mode === 'stay' ? '요금·예약 가능 여부·체크인 시간·키즈 시설 여부는 카카오맵이나 전화로 꼭 확인하세요.'
            : (u.kid ? '이용 요금·예약·연령 제한·양말 지참 여부는 카카오맵이나 전화로 꼭 확인하세요.' : '영업시간·휴무일·메뉴·예약은 카카오맵이나 전화로 꼭 확인하세요.');
        var h = '<h3>' + esc(x.name) + '</h3><div class="ci-tags">' + (x.cat ? '<i>' + esc(x.cat) + '</i>' : '') +
            (x.km != null ? '<i>' + esc((pt && pt.name ? clip(pt.name, 14) + '에서 ' : '기준 장소에서 ') + '약 ' + fmtKm(x.km)) + '</i>' : '') + '</div>' +
            (x.addr ? '<div class="ci-row"><b>주소</b> ' + esc(x.addr) + '</div>' : '') +
            (x.phone ? '<div class="ci-row"><b>전화</b> ' + esc(x.phone) + '</div>' : '') +
            ((x.lat != null && isFinite(x.lat)) ? '<div class="ci-map" id="ciMap"></div>' : '') +
            '<div class="ci-note">' + esc(note) + ' 사진·후기는 카카오맵에서 볼 수 있어요.</div>' +
            '<div class="ci-act">' + (x.phone ? '<a href="tel:' + esc(String(x.phone).replace(/[^\d+]/g, '')) + '">📞 전화</a>' : '') +
            (x.url ? '<a href="' + esc(x.url) + '" target="_blank" rel="noopener">🗺️ 카카오맵</a>' : '') +
            (rowKind ? '' : '<button type="button" class="p" data-ci="add">＋ 일정에 넣기</button>') + '</div>';
        infoEl.querySelector('.ci-c').innerHTML = h;
        infoEl.querySelector('.ci-pn').scrollTop = 0;
        if (!infoEl.classList.contains('on')) {
            infoPrevOv = document.documentElement.style.overflow;
            document.documentElement.style.overflow = 'hidden';
            infoEl.classList.add('on');
            void infoEl.offsetHeight;
            try { history.pushState({ cpInfo: 1 }, '', location.href); infoPushed = true; window.__cpInfoSkip = false; } catch (_) { infoPushed = false; }
        }
        infoEl.classList.add('up');
        // 작은 지도(카카오 지도 라이브러리가 있을 때만)
        setTimeout(function () {
            try {
                var box = document.getElementById('ciMap');
                if (!box || !window.kakao || !kakao.maps || !kakao.maps.Map || x.lat == null) { if (box) box.style.display = 'none'; return; }
                var pos = new kakao.maps.LatLng(x.lat, x.lng);
                infoMap = new kakao.maps.Map(box, { center: pos, level: 4 });
                new kakao.maps.Marker({ position: pos }).setMap(infoMap);
                infoMap.relayout(); infoMap.setCenter(pos);
            } catch (_) { var b2 = document.getElementById('ciMap'); if (b2) b2.style.display = 'none'; }
        }, 320);
    }

    // 일정에 넣은 줄에 장소 정보(이름·분류·주소·전화·카카오맵 주소·위치)를 함께 저장해 두고, 줄의 "정보보기"로 같은 팝업을 다시 연다.
    //   직접 쓴 이름처럼 정보가 없으면 저장하지 않는다(버튼도 안 나온다). m: stay=숙박, kid=키즈카페, meal=식당·카페
    function mkInfo(x, m) {
        if (!x || !(x.addr || x.phone || x.url || (x.lat != null && isFinite(x.lat)))) return null;
        var o = { n: String(x.name || '').slice(0, 40), c: String(x.cat || '').slice(0, 30), a: String(x.addr || '').slice(0, 80), p: String(x.phone || '').slice(0, 30), m: m };
        if (/^https?:\/\//.test(x.url || '')) o.u = x.url;
        if (x.lat != null && isFinite(x.lat) && isFinite(x.lng)) { o.la = +x.lat; o.lo = +x.lng; }
        return o;
    }
    function stayPut(x) {
        var u = mealUI, d = u.day, memo = [];
        if (x.cat) memo.push(x.cat);
        if (x.phone) memo.push('☎ ' + x.phone);
        memo.push('요금·예약·체크인 확인');
        var row = newRow(d, '', '🏨 ' + x.name, 'm'); row.memo = clip(memo.join(' · '), 100); row.tg = [['stay', '🏨 숙박']];
        var inf0 = mkInfo(x, 'stay'); if (inf0) row.info = inf0;
        // 그날 "귀가" 줄 앞(없으면 그날 맨 끝)에 넣고, 시간은 저녁 6시 무렵
        var at = -1; P.rows.forEach(function (rr, i) { if (at < 0 && rr.day === d && rr.k === 'out') at = i; });
        if (at < 0) at = lastIndexOfDay(d) + 1;
        if (at <= 0) at = P.rows.length;
        var prev = at > 0 ? P.rows[at - 1] : null;
        var pm = prev && /^(\d{1,2}):(\d{2})$/.exec(String(prev.time || ''));
        row.time = (pm && +pm[1] * 60 + +pm[2] >= 17 * 60) ? timeAfter(at, '18:00') : '18:00';
        if (x.lat != null && isFinite(x.lat) && isFinite(x.lng)) { row.lat = x.lat; row.lng = x.lng; }
        P.rows.splice(at, 0, row);
        mealUI = null;
    }
    function mealPut(x) {
        if (mealUI && mealUI.mode === 'stay') { stayPut(x); return; }
        var u = mealUI, d = u.day;
        var memo = [];
        if (x.cat) memo.push(x.cat);
        if (x.phone) memo.push('☎ ' + x.phone);
        memo.push('영업시간 확인');
        var data = { title: '🍴 ' + x.name, memo: clip(memo.join(' · '), 100), k: 'm', tg: [['meal', '🍴 식당·카페']] };
        if (u.kid) {   // 키즈카페: 점심 칸은 바꾸지 않고 새 줄로 넣는다(요금·예약·연령 확인 안내)
            memo.pop(); memo.push('요금·예약·연령 제한 확인');
            data = { title: '🎠 ' + x.name, memo: clip(memo.join(' · '), 100), k: 'm', tg: [['kid', '🎠 키즈카페']] };
        }
        var lp = (u.rep && !u.kid) ? lunchPlaceholder(d) : null;
        var row;
        if (lp) { row = lp; row.title = data.title; row.memo = data.memo; row.k = 'm'; row.tg = data.tg; delete row.pid; }
        else {
            var ri = u.ref ? rowIndex(u.ref) : -1;
            var at = ri >= 0 ? ri + 1 : lastIndexOfDay(d) + 1;
            if (at <= 0) at = P.rows.length;
            row = newRow(d, '', data.title, 'm'); row.memo = data.memo; row.tg = data.tg;
            var prev = at > 0 ? P.rows[at - 1] : null;
            var pm = prev && /^(\d{1,2}):(\d{2})$/.exec(String(prev.time || ''));
            row.time = u.kid ? timeAfter(at, '14:00') : ((pm && +pm[1] * 60 + +pm[2] >= 11 * 60 + 30) ? timeAfter(at, '12:00') : '12:00');
            P.rows.splice(at, 0, row);
        }
        if (x.lat != null && isFinite(x.lat) && isFinite(x.lng)) { row.lat = x.lat; row.lng = x.lng; } else { delete row.lat; delete row.lng; }
        var inf1 = mkInfo(x, u.kid ? 'kid' : 'meal'); if (inf1) row.info = inf1; else delete row.info;
        mealUI = null;
    }

    // ── 코스 미니맵 ───────────────────────────────────────────────────────────────────
    //   일정 줄 가운데 위치(lat·lng)가 있는 곳을 순서대로 번호 핀 + 점선으로 이어 일정표 맨 위에 보여 준다. 선은 직선(실제 길과 다름).
    //   지도는 한 번만 만들고, 일정이 바뀔 때마다 핀과 선만 다시 그린다. 지도 SDK 는 이미 불러와져 있으면 그대로 쓴다.
    var mmWrap = null, mmMap = null, mmObjs = [], mmDay = 1, mmLock = true, mmTimer = 0;
    function geoOk(r) { return !!r && r.lat != null && r.lat !== '' && r.lng != null && r.lng !== '' && isFinite(+r.lat) && isFinite(+r.lng); }
    function mmCount() { var n = 0; if (P) P.rows.forEach(function (r) { if (geoOk(r)) n++; }); return n; }
    function mmEnsure(ok, fail) {
        function have() { return window.kakao && kakao.maps && kakao.maps.Map && kakao.maps.Polyline && kakao.maps.CustomOverlay && kakao.maps.LatLngBounds; }
        if (have()) { ok(); return; }
        if (window.kakao && kakao.maps && kakao.maps.load) {
            try { kakao.maps.load(function () { have() ? ok() : fail(); }); } catch (e) { fail(); }
            return;
        }
        withKakao(function () { have() ? ok() : fail(); }, fail);
    }
    function mmSoon() { clearTimeout(mmTimer); mmTimer = setTimeout(mmUpdate, 40); }
    function mmAttach() {
        var sl = $('cpMMslot');
        if (!sl || !P || !mmCount()) return;
        if (mmWrap) { sl.style.display = ''; sl.appendChild(mmWrap); }   // 일정표를 다시 그려도 지도는 그대로 옮겨 붙인다(깜빡임·재생성 방지)
        mmSoon();
    }
    function mmApplyLock() { try { mmMap.setDraggable(!mmLock); mmMap.setZoomable(!mmLock); } catch (e) { /* 무시 */ } }
    function mmUpdate() {
        var sl = $('cpMMslot');
        if (!sl || !P || !root) return;
        if (!mmCount()) { sl.style.display = 'none'; return; }
        sl.style.display = '';
        if (!mmWrap) { mmWrap = document.createElement('div'); mmWrap.className = 'cp-mm'; mmWrap.innerHTML = '<div class="cp-mmh"></div><div class="cp-mmm"></div><div class="cp-mmn"></div>'; }
        if (mmWrap.parentNode !== sl) sl.appendChild(mmWrap);
        if (mmDay > P.days || mmDay < 1) mmDay = 1;
        var hd = '<span>🗺️ 코스 한눈에</span>';
        if (P.days > 1) { for (var d = 1; d <= P.days; d++) hd += '<button type="button" data-act="mmday" data-d="' + d + '" class="' + (d === mmDay ? 'on' : '') + '">' + d + '일차</button>'; }
        hd += '<button type="button" data-act="mmlock" style="margin-left:auto">' + (mmLock ? '🔒 고정됨 · 눌러서 움직이기' : '🔓 움직이는 중 · 눌러서 고정') + '</button>';
        mmWrap.querySelector('.cp-mmh').innerHTML = hd;
        var pts = [], miss = 0;
        P.rows.forEach(function (r) { if (r.day !== mmDay) return; if (geoOk(r)) pts.push({ id: r.id, la: +r.lat, lo: +r.lng }); else miss++; });
        var box = mmWrap.querySelector('.cp-mmm');
        mmWrap.querySelector('.cp-mmn').textContent = (pts.length ? '번호는 일정 순서예요. 선은 직선이라 실제 길과 달라요.' : '이 날은 지도에 표시할 장소가 아직 없어요.') +
            (pts.length && miss ? ' 위치 정보가 없는 ' + miss + '줄은 지도에 안 나와요.' : '');
        box.style.display = pts.length ? '' : 'none';
        if (!pts.length) return;
        mmEnsure(function () { mmDraw(box, pts); }, function () { if (!mmMap) box.innerHTML = '<div style="padding:18px;font-size:12.5px;color:#64748b">지도를 불러오지 못했어요.</div>'; });
    }
    function mmDraw(box, pts) {
        try {
            if (!box.offsetWidth) return;   // 일정표가 닫혀 있을 때는 그리지 않는다(다음에 열 때 그린다)
            if (!mmMap || mmMap._box !== box) {
                mmMap = new kakao.maps.Map(box, { center: new kakao.maps.LatLng(pts[0].la, pts[0].lo), level: 6 });
                mmMap._box = box;
            }
            mmApplyLock();
            try { mmMap.relayout(); } catch (e) { /* 무시 */ }
            mmObjs.forEach(function (o) { try { o.setMap(null); } catch (e) { /* 무시 */ } });
            mmObjs = [];
            var path = pts.map(function (q) { return new kakao.maps.LatLng(q.la, q.lo); });
            if (path.length > 1) {
                var pl = new kakao.maps.Polyline({ path: path, strokeWeight: 4, strokeColor: '#4f46e5', strokeOpacity: 0.85, strokeStyle: 'dash' });
                pl.setMap(mmMap); mmObjs.push(pl);
            }
            pts.forEach(function (q, i) {
                var el = document.createElement('div');
                el.className = 'cp-pin'; el.textContent = String(i + 1);
                el.addEventListener('click', function () {
                    var re = root && root.querySelector('.cp-row[data-id="' + q.id + '"]');
                    if (!re) return;
                    try { re.scrollIntoView({ behavior: 'smooth', block: 'center' }); } catch (e2) { re.scrollIntoView(); }
                    re.classList.add('cp-flash'); setTimeout(function () { re.classList.remove('cp-flash'); }, 1400);
                });
                var ov = new kakao.maps.CustomOverlay({ position: path[i], content: el, xAnchor: 0.5, yAnchor: 0.5, zIndex: 3 });
                ov.setMap(mmMap); mmObjs.push(ov);
            });
            if (path.length === 1) { mmMap.setCenter(path[0]); mmMap.setLevel(4); }
            else { var bd = new kakao.maps.LatLngBounds(); path.forEach(function (q) { bd.extend(q); }); mmMap.setBounds(bd, 30, 30, 30, 30); }
        } catch (e) { /* 지도가 안 그려져도 일정표 사용에는 지장 없다 */ }
    }

    // ── 일정표 공유(링크) ──────────────────────────────────────────────────────────────
    //   일정 내용을 JSON → 압축(지원 브라우저) → base64url 로 링크(/festival/?plan=…)에 담는다. 서버가 없어 링크에 모든 내용이 들어간다.
    //   받는 쪽(plan-modal.js)은 decodeShare 로 읽고, 내용을 모두 걸러(길이·종류·주소 형식 검사) 사본으로 저장한다.
    var SHARE_KINDS = { x: 1, n: 1, f: 1, m: 1, out: 1 };
    var SHARE_TG = { '': 1, 'in': 1, out: 1, free: 1, stay: 1, meal: 1, kid: 1 };
    function str(v, n) { return String(v == null ? '' : v).slice(0, n); }
    function r5(v) { return Math.round(+v * 1e5) / 1e5; }
    function shareBuild(withMemo) {
        var o = { v: 1, t: str(cur && cur.title, 40), n: P.days, r: [] };
        if (withMemo && P.note) o.o = str(P.note, 600);
        P.rows.forEach(function (r) {
            var q = { d: r.day, t: timeVal(r.time), x: str(r.title, 60) };
            if (withMemo && r.memo) q.m = str(r.memo, 100);
            if (SHARE_KINDS[r.k] && r.k !== 'x') q.k = r.k;
            var pid = rowPid(r); if (pid) q.p = pid;
            if (geoOk(r)) q.l = [r5(r.lat), r5(r.lng)];
            var tg = rowTags(r); if (tg && tg.length) q.g = tg.map(function (t) { return [t[0] || '', t[1]]; });
            if (r.info) q.i = r.info;
            o.r.push(q);
        });
        return o;
    }
    function shareClean(o) {
        if (!o || o.v !== 1 || !Array.isArray(o.r) || !o.r.length) return null;
        var days = Math.max(1, Math.min(7, parseInt(o.n, 10) || 1)), rows = [];
        o.r.slice(0, 60).forEach(function (q) {
            if (!q || typeof q !== 'object') return;
            var r = { id: uid(), day: Math.max(1, Math.min(days, parseInt(q.d, 10) || 1)), time: timeVal(q.t), title: str(q.x, 60), memo: str(q.m, 100), k: SHARE_KINDS[q.k] ? q.k : 'x' };
            if (typeof q.p === 'string' && /^[A-Za-z0-9_-]{1,24}$/.test(q.p)) r.pid = q.p;
            if (Array.isArray(q.l) && isFinite(+q.l[0]) && isFinite(+q.l[1]) && Math.abs(+q.l[0]) <= 90 && Math.abs(+q.l[1]) <= 180) { r.lat = +q.l[0]; r.lng = +q.l[1]; }
            if (Array.isArray(q.g)) {
                var tg = [];
                q.g.slice(0, 4).forEach(function (t) { if (Array.isArray(t) && SHARE_TG.hasOwnProperty(String(t[0] || ''))) tg.push([String(t[0] || ''), str(t[1], 20)]); });
                if (tg.length) r.tg = tg;
            }
            if (q.i && typeof q.i === 'object') {
                var inf = mkInfo({ name: q.i.n, cat: q.i.c, addr: q.i.a, phone: q.i.p, url: q.i.u, lat: q.i.la, lng: q.i.lo }, (q.i.m === 'stay' || q.i.m === 'kid') ? q.i.m : 'meal');
                if (inf) r.info = inf;
            }
            rows.push(r);
        });
        if (!rows.length) return null;
        return { t: str(o.t, 40) || '친구가 보낸 코스', n: days, o: str(o.o, 600), r: rows };
    }
    function fromShared(sh) {
        return { v: 1, mode: 'day', id: '', date: '', days: sh.n, rows: sh.r, checks: {}, extra: [], note: sh.o || '', fest: false };
    }
    function b64uEnc(u8) {
        var s = '';
        for (var i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000));
        return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
    }
    function b64uDec(t) {
        t = String(t).replace(/-/g, '+').replace(/_/g, '/');
        while (t.length % 4) t += '=';
        var b = atob(t), u = new Uint8Array(b.length);
        for (var i = 0; i < b.length; i++) u[i] = b.charCodeAt(i);
        return u;
    }
    function streamBytes(tf, u8) {
        var w = tf.writable.getWriter();
        w.write(u8); w.close();
        return new Response(tf.readable).arrayBuffer().then(function (ab) { return new Uint8Array(ab); });
    }
    function shareEncode(obj) {
        var u8 = new TextEncoder().encode(JSON.stringify(obj));
        if (typeof CompressionStream === 'function') {
            try { return streamBytes(new CompressionStream('deflate-raw'), u8).then(function (z) { return 'z.' + b64uEnc(z); }); } catch (e) { /* 압축 없이 */ }
        }
        return Promise.resolve('u.' + b64uEnc(u8));
    }
    function decodeShare(code) {
        code = String(code || '');
        if (code.length > 12000) return Promise.reject(new Error('long'));
        var kind = code.slice(0, 2), p;
        try {
            var u8 = b64uDec(code.slice(2));
            if (kind === 'u.') p = Promise.resolve(u8);
            else if (kind === 'z.' && typeof DecompressionStream === 'function') p = streamBytes(new DecompressionStream('deflate-raw'), u8);
            else return Promise.reject(new Error('nosupport'));
        } catch (e) { return Promise.reject(e); }
        return p.then(function (bytes) {
            var c = shareClean(JSON.parse(new TextDecoder().decode(bytes)));
            if (!c) throw new Error('bad');
            return c;
        });
    }
    function shareMsg(t) { var e = $('cpShareMsg'); if (e) e.textContent = t || ''; }
    function shareMake(cb) {
        var m = $('cpShareMemo');
        shareMsg('링크를 만드는 중…');
        shareEncode(shareBuild(!!(m && m.checked))).then(function (code) {
            if (code.length > 7000) { shareMsg('일정이 너무 길어 링크로 보내기 어려워요. 줄을 줄이거나 "메모도 같이 보내기"를 꺼 보세요.'); return; }
            var url = location.origin + '/festival/?plan=' + code;
            var inp = $('cpShareUrl'); if (inp) { inp.value = url; inp.style.display = ''; }
            shareMsg('');
            cb(url);
        }, function () { shareMsg('링크를 만들지 못했어요. 잠시 후 다시 시도해 주세요.'); });
    }
    function copyText(url, done) {
        function fb() {
            try { var inp = $('cpShareUrl'); if (inp) { inp.focus(); inp.select(); inp.setSelectionRange(0, 99999); } done(!!document.execCommand('copy')); } catch (e) { done(false); }
        }
        if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(url).then(function () { done(true); }, fb);
        else fb();
    }

    // ── 인쇄용 종이 ─────────────────────────────────────────────────────────────────
    // [ADD] 2026-11-22: 일정표 종이 맨 위 "이동 순서" 그림 — 집 출발 → 장소들 → 귀가를 점과 선으로 잇고,
    // 점마다 시간·운영시간, 선 위에는 앞 장소와의 직선거리를 적는다. 줄(memo) 글자에서 읽어 오므로 새 저장값이 필요 없다.
    // 이동 방법·소요 시간·대중교통은 일부러 넣지 않는다(지도앱이 더 정확).
    function plainTitle(t) { return String(t || '').replace(/^(?:[←-⯿️‍]|[\uD83C-\uD83E][\uDC00-\uDFFF])+\s*/, '').replace(/\s+/g, ' ').trim(); }
    function routeStops(d) {
        var out = [], n = 0;
        var hasGeo = P.rows.some(function (r) { return r.lat != null && isFinite(+r.lat) && isFinite(+r.lng); });
        var lastGeo = null;
        P.rows.forEach(function (r) {
            if (r.day !== d) return;
            var title = plainTitle(r.title);
            if (!title) return;
            var icon, home = /^(집 출발|출발|귀가)/.test(title), meal = !home && (r.k === 'm' || /^(점심|저녁|아침|식사|간식|카페|브런치)/.test(title));
            if (home) icon = '🏠'; else if (/^🏨/.test(String(r.title))) icon = '🏨'; else if (/^🎠/.test(String(r.title))) icon = '🎠'; else if (meal) icon = '🍴'; else icon = String(++n);
            var conn = '', place = '', hours = '';
            String(r.memo || '').split(' · ').forEach(function (m) {
                m = m.trim();
                if (!m) return;
                if (/^앞 장소와 같은 곳/.test(m)) conn = '같은 곳';
                else if (/^앞 장소에서 약\s*[\d.,]+\s*(km|m)/i.test(m)) conn = '약 ' + m.replace(/^앞 장소에서 약\s*/, '');
                else if (/약\s*[\d.,]+\s*(km|m)\b/i.test(m)) place = m;
                else if (/^(운영 |회차 |상시 개방|운영시간 확인)/.test(m)) hours = m;
            });
            if (hasGeo) {   // 위치가 저장된 줄이 있으면 앞 장소와의 거리를 지금 순서대로 다시 계산한다(메모 속 옛 거리는 쓰지 않음)
                conn = '';
                if (r.lat != null && isFinite(+r.lat) && isFinite(+r.lng)) {
                    if (lastGeo) { var kmv = kmBetween(lastGeo.lat, lastGeo.lng, +r.lat, +r.lng); conn = kmv < 0.1 ? '같은 곳' : '약 ' + fmtKm(kmv); }
                    lastGeo = { lat: +r.lat, lng: +r.lng };
                }
            }
            out.push({ icon: icon, title: title.length > 18 ? title.slice(0, 17) + '…' : title, time: timeVal(r.time), conn: conn, place: place, hours: (home || meal) ? '' : hours });
        });
        return out;
    }
    function routeHtml(d) {
        if (cfg.kind === 'camp') return '';
        var st = routeStops(d);
        if (st.length < 3 || st.length > 9) return '';
        var h = '<div class="rt-cap">🧭 이동 순서 · 거리는 직선 기준이에요. 가는 방법과 시간은 지도앱에서 확인하세요.</div><div class="rt">';
        st.forEach(function (x, i) {
            h += '<div class="rt-n">' + (i > 0 && x.conn ? '<span class="rt-d">' + esc(x.conn) + '</span>' : '') +
                '<div class="rt-t"><i' + (i === 0 ? ' class="off"' : '') + '></i><b>' + esc(x.icon) + '</b><i' + (i === st.length - 1 ? ' class="off"' : '') + '></i></div>' +
                '<div class="rt-nm">' + esc(x.title) + '</div>' +
                (x.time ? '<div class="rt-tm">' + esc(x.time) + '</div>' : '') +
                (x.place ? '<div class="rt-hr">' + esc(x.place) + '</div>' : '') +
                (x.hours ? '<div class="rt-hr">' + esc(x.hours) + '</div>' : '') + '</div>';
        });
        return h + '</div>';
    }
    function paperHtml() {
        var h = '<div class="cpp"><h1>' + esc(cfg.paperTitle) + '</h1><div class="info">';
        h += '<div><b>' + esc(cfg.placeLabel) + '</b> ' + esc(cur.title) + '</div>';
        if (cur.addr) h += '<div><b>주소</b> ' + esc(cur.addr) + '</div>';
        if (tel()) h += '<div><b>전화</b> ' + esc(tel()) + '</div>';
        if (cfg.kind !== 'camp') {
            if (cur.fee) h += '<div><b>요금 안내</b> ' + esc(clip(cur.fee, 80)) + '</div>';
            if (cur.hours) h += '<div><b>운영시간(참고)</b> ' + esc(clip(cur.hours, 90)) + '</div>';
        }
        if (P.date) h += '<div><b>' + esc(cfg.dateLabel) + '</b> ' + esc(dayLabel(1).replace(/^(1일차|하루 나들이|숲 나들이) · /, '')) + '</div>';
        h += '</div>';
        for (var d = 1; d <= P.days; d++) {
            h += '<h2>' + esc(dayLabel(d)) + '</h2>' + routeHtml(d) + '<table><tr><th style="width:62px">시간</th><th style="width:38%">일정</th><th>메모</th></tr>';
            var any = false;
            P.rows.forEach(function (r) {
                if (r.day !== d) return;
                any = true;
                var tgs = rowTags(r).map(function (t) { return t[1]; }).join(' · ');
                h += '<tr><td>' + esc(r.time) + '</td><td>' + esc(r.title) + (tgs ? '<div style="font-size:11px;color:#555">' + esc(tgs) + '</div>' : '') + '</td><td>' + esc(r.memo) + (r.info && r.info.a ? '<div style="font-size:11px;color:#555">📍 ' + esc(r.info.a) + '</div>' : '') + '</td></tr>';
            });
            if (!any) h += '<tr><td colspan="3">&nbsp;</td></tr>';
            h += '</table>';
        }
        function ck(id, text) { return '<div class="ck">' + (isOn(id) ? '☑' : '☐') + ' ' + esc(text) + '</div>'; }
        h += '<h2>출발 전 확인표</h2><div class="cols">';
        cfg.checkA.forEach(function (c) { h += ck(c[0], fill(c[1])); });
        nearChecks().forEach(function (c) { h += ck(c[0], c[1]); });
        h += '</div><h2>준비물</h2><div class="cols">';
        cfg.checkB.forEach(function (c) { h += ck(c[0], c[1]); });
        P.extra.forEach(function (c) { h += ck(c.id, c.text); });
        h += '</div><h2>메모</h2><div class="memo">' + esc(P.note) + '</div>';
        h += '<div class="foot">' + esc(cfg.footer) + '</div></div>';
        return h;
    }
    function doPrint() {
        var host = $('cp-print-host');
        if (!host) { host = document.createElement('div'); host.id = 'cp-print-host'; document.body.appendChild(host); }
        host.innerHTML = paperHtml();
        document.body.classList.add('cp-printing');
        var done = function () { document.body.classList.remove('cp-printing'); window.removeEventListener('afterprint', done); };
        window.addEventListener('afterprint', done);
        window.print();
    }

    // ── 동작 ─────────────────────────────────────────────────────────────────────
    function rowIndex(id) { for (var i = 0; i < P.rows.length; i++) if (P.rows[i].id === id) return i; return -1; }
    function lastIndexOfDay(d) { var idx = -1; P.rows.forEach(function (r, i) { if (r.day === d) idx = i; }); return idx; }
    function firstIndexOfDay(d) { for (var i = 0; i < P.rows.length; i++) if (P.rows[i].day === d) return i; return -1; }
    function newRow(day, time, title, k) { return { id: uid(), day: day, time: time || '', title: title || '', memo: '', k: k || 'x' }; }

    // [ADD] 2026-11-19: 일정 줄의 "상세보기"는 지도·월드컵·룰렛·포스터와 같은 상세 팝업(festival/detail-sheet.js, 아래에서 올라오는 시트)으로 열린다.
    //   링크에 target="_blank"를 붙이지 않으므로 detail-sheet.js 가 클릭을 가로채 팝업을 띄운다(일정표 화면·입력 내용은 그대로).
    //   detail-sheet.js 가 없는 페이지에서만 새 탭으로 연다.
    function onClick(e) {
        var dl = e.target.closest ? e.target.closest('a.cp-detail') : null;
        if (dl && root.contains(dl)) {
            if (!e.defaultPrevented && !window.HohoDetailSheet && !(e.ctrlKey || e.metaKey || e.shiftKey || e.button === 1)) {
                e.preventDefault();
                try { window.open(dl.getAttribute('href'), '_blank', 'noopener'); } catch (err) { location.href = dl.getAttribute('href'); }
            }
            return;
        }
        var t = e.target.closest ? e.target.closest('[data-act]') : null;
        if (!t || !root.contains(t)) return;
        var act = t.getAttribute('data-act');
        var rowEl = t.closest('.cp-row');
        var id = rowEl ? rowEl.getAttribute('data-id') : '';
        var i;
        if (act === 'back') {
            e.preventDefault();
            var rs = $('result'); if (rs && rs.scrollIntoView) rs.scrollIntoView({ behavior: 'smooth', block: 'start' });
            return;
        }
        if (act === 'mmday') { mmDay = +t.getAttribute('data-d') || 1; mmUpdate(); return; }
        if (act === 'mmlock') { mmLock = !mmLock; mmUpdate(); return; }
        if (act === 'share') {
            shareMake(function (url) {
                if (navigator.share) {
                    navigator.share({ title: '나들이 일정표', text: (cur && cur.title ? cur.title : '나들이') + ' 일정표를 보내요', url: url }).then(function () { shareMsg('공유했어요.'); }, function (err) {
                        if (err && err.name === 'AbortError') { shareMsg(''); return; }
                        copyText(url, function (ok) { shareMsg(ok ? '공유창을 열 수 없어 링크를 복사했어요. 카카오톡이나 문자에 붙여넣어 보내세요.' : '아래 링크를 길게 눌러 복사해 주세요.'); });
                    });
                } else {
                    copyText(url, function (ok) { shareMsg(ok ? '링크를 복사했어요. 카카오톡이나 문자에 붙여넣어 보내세요.' : '아래 링크를 길게 눌러 복사해 주세요.'); });
                }
            });
            return;
        }
        if (act === 'sharecopy') {
            shareMake(function (url) { copyText(url, function (ok) { shareMsg(ok ? '링크를 복사했어요. 카카오톡이나 문자에 붙여넣어 보내세요.' : '아래 링크를 길게 눌러 복사해 주세요.'); }); });
            return;
        }
        if (act === 'up' || act === 'down') {
            i = rowIndex(id); if (i < 0) return;
            var r = P.rows[i];
            if (act === 'up') {
                if (i > 0 && P.rows[i - 1].day === r.day) { P.rows[i] = P.rows[i - 1]; P.rows[i - 1] = r; }
                else if (r.day > 1) r.day -= 1;           // 그날의 맨 위 → 전날 맨 아래로
            } else {
                if (i < P.rows.length - 1 && P.rows[i + 1].day === r.day) { P.rows[i] = P.rows[i + 1]; P.rows[i + 1] = r; }
                else if (r.day < P.days) r.day += 1;      // 그날의 맨 아래 → 다음날 맨 위로
            }
        } else if (act === 'del') {
            i = rowIndex(id); if (i >= 0) P.rows.splice(i, 1);
        } else if (act === 'addrow') {
            var d = +t.getAttribute('data-day');
            var li = lastIndexOfDay(d);
            var nr = newRow(d, '', '', 'x');
            if (li >= 0) P.rows.splice(li + 1, 0, nr);
            else {                                         // 비어 있는 날: 다음 날 첫 줄 앞에 넣는다
                var nx = -1; for (var k = d + 1; k <= P.days && nx < 0; k++) nx = firstIndexOfDay(k);
                if (nx < 0) P.rows.push(nr); else P.rows.splice(nx, 0, nr);
            }
        } else if (act === 'addnear') {
            var nn = cur._near[+t.getAttribute('data-i')];
            if (!nn) return;
            var ni = -1; P.rows.forEach(function (rr, x) { if (ni < 0 && rr.day === 1 && rr.k === cfg.anchorKind) ni = x; });
            if (ni < 0) ni = lastIndexOfDay(1) + 1;
            P.rows.splice(ni, 0, nearRow(nn, timeAfter(ni, cfg.nearTime)));
        } else if (act === 'addfest') {
            var fx = festList[+t.getAttribute('data-i')];
            if (!fx) return;
            var fi = -1; P.rows.forEach(function (rr, x) { if (fi < 0 && rr.day === 1 && rr.k === 'out') fi = x; });
            if (fi < 0) fi = lastIndexOfDay(1) + 1;
            P.rows.splice(fi, 0, withGeo({ id: uid(), day: 1, time: timeAfter(fi, '14:30'), title: '🎪 ' + fx.f.title, memo: '행사 시간 확인 · ' + cfg.fromLabel + ' 약 ' + fmtKm(fx.km) + ' · ' + md(fx.f.startDate) + '~' + md(fx.f.endDate), k: 'f', pid: fx.f.contentid || fx.f.id || '', tg: festTags(fx.f) }, fx.f));
        } else if (act === 'mealopen') {
            mealOpen(+t.getAttribute('data-day'));
        } else if (act === 'stayopen') {
            mealOpen(+t.getAttribute('data-day'), true);
        } else if (act === 'staycat') {
            if (!mealUI) return;
            mealUI.kw = t.getAttribute('data-kw') || ''; mealUI.q = '';
            var qs = $('cpMealQ'); if (qs) qs.value = '';
            mealSearch(); return;
        } else if (act === 'mealclose') {
            mealUI = null;
        } else if (act === 'mealkid') {
            if (!mealUI) return;
            mealUI.kid = true; mealUI.q = '키즈카페'; if (mealUI.rad < 3000) mealUI.rad = 3000;   // 키즈카페는 드물어서 반경을 3km로 넓혀 찾는다
            mealSearch(); return;
        } else if (act === 'mealcat') {
            if (!mealUI) return;
            mealUI.kid = false;
            mealUI.cat = t.getAttribute('data-cat') === 'CE7' ? 'CE7' : 'FD6'; mealUI.q = '';
            var qi = $('cpMealQ'); if (qi) qi.value = '';
            mealSearch(); return;
        } else if (act === 'mealsearch') {
            if (!mealUI) return;
            var qv = $('cpMealQ'); mealUI.q = qv ? qv.value : ''; mealUI.kid = /키즈/.test(mealUI.q);
            mealSearch(); return;
        } else if (act === 'mealinfo') {
            if (!mealUI || !mealUI.results) return;
            var ix = mealUI.results[+t.getAttribute('data-i')]; if (!ix) return;
            infoOpen(ix, +t.getAttribute('data-i')); return;
        } else if (act === 'rowinfo') {
            var ri0 = rowIndex(id); var rr0 = ri0 >= 0 ? P.rows[ri0] : null;
            if (!rr0 || !rr0.info) return;
            var f0 = rr0.info;
            infoOpen({ name: f0.n || plainTitle(rr0.title), cat: f0.c, addr: f0.a, phone: f0.p, url: f0.u || '', lat: f0.la != null ? f0.la : null, lng: f0.lo != null ? f0.lo : null }, -1, f0.m || 'meal'); return;
        } else if (act === 'mealadd') {
            if (!mealUI || !mealUI.results) return;
            var mx = mealUI.results[+t.getAttribute('data-i')]; if (!mx) return;
            mealPut(mx);
        } else if (act === 'mealman') {
            var mi = $('cpMealMan'); var mv = mi ? mi.value.trim() : '';
            if (!mv || !mealUI) return;
            mealPut({ name: mv.slice(0, 30), cat: '', phone: '', lat: null, lng: null });
        } else if (act === 'addextra') {
            var inp = $('cpExtraIn'); var v = inp ? inp.value.trim() : '';
            if (!v) return;
            P.extra.push({ id: 'x_' + uid(), text: v.slice(0, 40) });
        } else if (act === 'xextra') {
            var xid = t.getAttribute('data-id');
            P.extra = P.extra.filter(function (c) { return c.id !== xid; });
            delete P.checks[xid];
            e.preventDefault();
        } else if (act === 'reset') {
            if (!window.confirm('편집한 내용을 지우고 처음 상태로 되돌릴까요?')) return;
            var keepId = P.id; P = newPlan(cur); P.id = keepId; mealUI = null;
        } else if (act === 'print') {
            doPrint();
            return;
        } else return;
        save(); render();
    }
    function onInput(e) {
        var t = e.target;
        var f = t.getAttribute && t.getAttribute('data-f');
        if (f) {
            if (f !== 'time' && t.tagName === 'TEXTAREA') {
                if (/[\r\n]/.test(t.value)) t.value = t.value.replace(/[\r\n]+/g, ' ');   // 붙여넣은 줄바꿈은 공백으로
                fit(t);
            }
            var rowEl = t.closest('.cp-row');
            var i = rowEl ? rowIndex(rowEl.getAttribute('data-id')) : -1;
            if (i >= 0) {
                var rr0 = P.rows[i];
                if (f === 'title' && rr0.lat != null) {   // 다른 장소 이름으로 바꾸면 옛 위치가 남지 않게 지운다(거리는 비워 두고 틀린 값은 보여 주지 않음)
                    var oldNm = plainTitle(rr0.title).slice(0, 3);
                    if (!oldNm || plainTitle(t.value).indexOf(oldNm) < 0) { delete rr0.lat; delete rr0.lng; }
                }
                rr0[f] = t.value; save();
            }
        } else if (t.id === 'cpExtraIn') { if (/[\r\n]/.test(t.value)) t.value = t.value.replace(/[\r\n]+/g, ' '); fit(t); }
        else if (t.id === 'cpMealQ') { if (mealUI) mealUI.q = t.value; }
        else if (t.id === 'cpNote') { P.note = t.value; save(); }
        else if (t.id === 'cpDate') { P.date = t.value; save(); updateDayLabels(); updateDateNote(); if (cfg.hasFest && P.fest) updateFest(); }
    }
    function updateDayLabels() {
        var hs = root.querySelectorAll('.cp-dayhd > span');
        for (var i = 0; i < hs.length; i++) hs[i].textContent = dayLabel(i + 1);
    }
    function onChange(e) {
        var t = e.target;
        if (t.id === 'cpFestOn') {
            P.fest = !!t.checked;
            if (P.fest && !P.date) P.date = todayKST();
            save(); render(); return;
        }
        if (t.id === 'cpMealRef' && mealUI) { mealUI.ref = t.value; if (mealUI.results || mealUI.q) mealSearch(); return; }
        if (t.id === 'cpMealRad' && mealUI) { mealUI.rad = +t.value || 1000; if (mealUI.results) mealSearch(); return; }
        if (t.id === 'cpMealRep' && mealUI) { mealUI.rep = !!t.checked; return; }
        var cid = t.getAttribute && t.getAttribute('data-chk');
        if (cid) {
            if (t.checked) P.checks[cid] = true; else delete P.checks[cid];
            var lab = t.closest('.cp-chk'); if (lab) lab.classList.toggle('on', t.checked);
            save();
        }
    }
    // 시간 칸: 1330 → 13:30, 9 → 09:00 처럼 24시간 HH:MM으로 정리한다(알아볼 수 없으면 그대로 둔다).
    function normTime(v) {
        var d = String(v || '').replace(/[^0-9]/g, '');
        if (!d) return '';
        var h, m;
        if (d.length <= 2) { h = +d; m = 0; }
        else if (d.length === 3) { h = +d.slice(0, 1); m = +d.slice(1); }
        else { h = +d.slice(0, 2); m = +d.slice(2, 4); }
        if (h > 23 || m > 59) return String(v);
        return ('0' + h).slice(-2) + ':' + ('0' + m).slice(-2);
    }
    function onBlur(e) {
        var t = e.target;
        if (!t.getAttribute || t.getAttribute('data-f') !== 'time') return;
        var v = normTime(t.value);
        if (v !== t.value) {
            t.value = v;
            var rowEl = t.closest('.cp-row'); var i = rowEl ? rowIndex(rowEl.getAttribute('data-id')) : -1;
            if (i >= 0) { P.rows[i].time = v; save(); }
        }
    }
    function onKey(e) {
        if (e.key === 'Enter' && e.target && e.target.tagName === 'TEXTAREA' && e.target.getAttribute('data-f')) {
            e.preventDefault();          // 글자는 칸 너비에 맞춰 알아서 내려가므로 줄바꿈 키는 입력 끝으로 쓴다
            e.target.blur();
            return;
        }
        if (e.key === 'Enter' && e.target && e.target.id === 'cpMealQ') { e.preventDefault(); if (mealUI) { mealUI.q = e.target.value; mealSearch(); } return; }
        if (e.key === 'Enter' && e.target && e.target.id === 'cpMealMan') { e.preventDefault(); var mb = root.querySelector('[data-act="mealman"]'); if (mb) mb.click(); return; }
        if (e.key === 'Enter' && e.target && e.target.id === 'cpExtraIn') {
            e.preventDefault();
            var b = root.querySelector('[data-act="addextra"]'); if (b) b.click();
        }
    }

    // ── 입구 ─────────────────────────────────────────────────────────────────────
    function ensure() {
        sec = $('campPlan');
        if (!sec) return false;
        if (!root) {
            root = $('cpRoot');
            if (!root) { root = document.createElement('div'); root.id = 'cpRoot'; sec.appendChild(root); }
            root.addEventListener('click', onClick);
            root.addEventListener('input', onInput);
            root.addEventListener('change', onChange);
            root.addEventListener('keydown', onKey);
            root.addEventListener('focusout', onBlur);
            window.addEventListener('resize', onResize);
        }
        injectStyle();
        return true;
    }

    window.HohoCampPlan = {
        open: function (champ, opts) {
            if (!champ || !champ.contentid || !ensure()) return;
            var base = MODES[(opts && opts.mode) || 'camp'] || MODES.camp;
            cfg = base;
            if (opts && opts.over) {                         // 화면 글자 일부만 바꿔 쓴다(룰렛: 우승 → 오늘의 장소). 원본 틀은 건드리지 않는다.
                cfg = {};
                Object.keys(base).forEach(function (k) { cfg[k] = base[k]; });
                // 글자(icon·placeLabel·fromLabel·title·paperTitle·sub·dateLabel·noNear), 확인표(checkA), 저장 칸(key), 축제 스위치(hasFest)를 바꿔 쓸 수 있다.
                ['icon', 'placeLabel', 'fromLabel', 'title', 'paperTitle', 'sub', 'dateLabel', 'noNear'].forEach(function (k) { if (opts.over[k]) cfg[k] = String(opts.over[k]); });
                if (opts.over.noNear === '') cfg.noNear = '';   // [ADD] 2026-11-22: 빈 글자면 "근처 장소를 못 찾았어요" 안내를 숨긴다(코스 일정표)
                if (Array.isArray(opts.over.checkA)) cfg.checkA = opts.over.checkA;
                if (opts.over.key) cfg.key = String(opts.over.key);
                if (typeof opts.over.hasFest === 'boolean') cfg.hasFest = opts.over.hasFest;
            }
            festList = [];
            mealUI = null;
            cur = champ;
            // [ADD] 2026-11-19: opts.variant — 같은 장소로 서로 다른 일정표(예: 축제만 / 축제+나들이)를 따로 저장한다. opts.noDefaultNear — 근처 장소를 처음엔 일정에 넣지 않고 “더 넣기” 버튼으로만 보여 준다.
            var pid = champ.contentid + (opts && opts.variant ? ':' + String(opts.variant) : '');
            defNearOff = !!(opts && opts.noDefaultNear);
            P = load(pid);
            mmDay = 1;
            if (!P && opts && opts.shared) { P = fromShared(opts.shared); P.id = pid; }   // 공유 링크로 받은 일정표: 받은 내용을 사본으로 저장한다
            // [ADD] 2026-11-22: opts.rows — 지도의 코스 카드처럼 여러 곳을 한 번에 담은 일정표. 저장된 일정이 없을 때(그리고 "처음 상태로")만 이 줄들로 채운다.
            //   rows: [{ time:'10:00', title, memo, k:'x'|'n'|'f', pid?, src? }]  (src = costTag·placeType 가 든 장소 정보 → 실내/야외·무료/유료 배지)
            seedRows = (opts && Array.isArray(opts.rows) && opts.rows.length) ? opts.rows : null;
            if (!P) { P = newPlan(champ); P.id = pid; }
            save();
            render();
            sec.style.display = 'block';
            fitAll();
            mmSoon();
            try { sec.scrollIntoView({ behavior: 'smooth', block: 'start' }); } catch (e) { sec.scrollIntoView(); }
        },
        decodeShare: decodeShare,
        hide: function () {
            var s = $('campPlan');
            if (s) s.style.display = 'none';
        }
    };
})();
