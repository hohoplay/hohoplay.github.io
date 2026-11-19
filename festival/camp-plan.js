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
 *          window.HohoCampPlan.hide() — 월드컵을 다시 시작할 때 일정표를 접는다.
 */
(function () {
    'use strict';

    var sec = null, root = null, cur = null, P = null;

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
    function nearRow(n, time) {
        var meta = [];
        if (n.km != null) meta.push(cfg.fromLabel + ' 약 ' + fmtKm(n.km));
        if (n.placeType) meta.push(n.placeType);
        meta.push('운영시간 확인');
        return { id: uid(), day: 1, time: time, title: '📍 ' + n.title, memo: meta.join(' · '), k: 'n', pid: n.contentid || '' };
    }
    function costLabel(c) {
        var t = c && c.costTag;
        if (t === '완전무료') return '무료';
        if (t === '유료') return '유료';
        if (t === '유료(일부 무료 조건 있음)') return '일부 무료';
        return '요금 확인 필요';
    }
    var defNearOff = false;
    function dayDefaultPlan(champ) {
        var forest = cfg.kind === 'forest';
        var two = defNearOff ? [] : pickTwo(champ._near);
        var memo = [];
        if (champ.placeType) memo.push(champ.placeType);
        memo.push(costLabel(champ));
        memo.push('운영시간 확인');
        var rows = [
            { id: uid(), day: 1, time: '10:00', title: '집 출발', memo: '', k: 'x' },
            { id: uid(), day: 1, time: '10:30', title: cfg.icon + ' ' + champ.title, memo: memo.join(' · '), k: 'c', pid: champ.hasDetail === false ? '' : champ.contentid },
            { id: uid(), day: 1, time: forest ? '12:30' : '12:00', title: forest ? '점심 · 도시락' : '점심 · 휴식', memo: forest ? '도시락 또는 근처 식당' : '근처 식당 찾기', k: 'x' }
        ];
        var times = forest ? (two.length >= 2 ? ['14:00', '16:00'] : ['14:30']) : (two.length >= 2 ? ['13:30', '15:30'] : ['14:00']);
        two.forEach(function (n, i) { rows.push(nearRow(n, times[i])); });
        rows.push({ id: uid(), day: 1, time: forest ? '17:30' : '17:30', title: '귀가', memo: '', k: 'out' });
        return { v: 1, mode: forest ? 'forest' : 'day', id: champ.contentid, date: champ._date || '', days: 1, rows: rows, checks: {}, extra: [], note: '', fest: false };
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
        return P.rows.filter(function (r) { return r.k === 'n' || r.k === 'f'; }).map(function (r) {
            var nm = String(r.title).replace(/^(?:📍|🎪)\s*/, '');
            return ['n_' + r.id, '「' + nm + '」 ' + (r.k === 'f' ? '행사 시간·장소 확인' : '운영시간·휴관일 확인')];
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
            '#campPlan .cp-time{width:72px;flex:0 0 auto;text-align:center;font-weight:800}' +
            '#campPlan .cp-col{flex:1 1 auto;min-width:0;display:flex;flex-direction:column;gap:6px}' +
            '#campPlan .cp-col input{width:100%}' +
            '#campPlan .cp-tcol{flex:0 0 72px;width:72px;display:flex;flex-direction:column;gap:6px}' +
            '#campPlan .cp-tcol .cp-time{width:100%}' +
            '#campPlan .cp-detail{display:block;text-align:center;font-size:12px;font-weight:800;color:#4f46e5;background:#eef2ff;border:1px solid #c7d2fe;border-radius:8px;padding:5px 0;text-decoration:none;line-height:1.2}' +
            '#campPlan .cp-detail:hover{background:#e0e7ff}' +
            '#campPlan .cp-col textarea,#campPlan .cp-add textarea{min-height:0;resize:none;overflow:hidden;line-height:1.45;display:block;white-space:pre-wrap;overflow-wrap:anywhere}' +
            '#campPlan .cp-col textarea{width:100%}' +
            '#campPlan .cp-add textarea{flex:1 1 auto;width:auto;min-width:0}' +
            '#campPlan .cp-title{font-weight:800}' +
            '#campPlan .cp-memo{font-size:13px!important;color:#475569}' +
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
    function rowHtml(r) {
        var pid = rowPid(r);
        return '<div class="cp-row" data-id="' + r.id + '">' +
            '<div class="cp-tcol">' +
            '<input class="cp-time" type="text" inputmode="numeric" maxlength="5" value="' + esc(r.time) + '" data-f="time" placeholder="00:00" aria-label="시간 (24시간, 예 13:30)">' +
            (pid ? '<a class="cp-detail" href="/festival/detail/' + pid + '.html" target="_blank" rel="noopener" aria-label="장소 상세페이지 (팝업)">상세보기</a>' : '') +
            '</div>' +
            '<div class="cp-col">' +
            '<textarea class="cp-title" rows="1" maxlength="60" data-f="title" placeholder="일정" aria-label="일정">' + esc(r.title) + '</textarea>' +
            '<textarea class="cp-memo" rows="1" maxlength="100" data-f="memo" placeholder="메모 (예: 예약번호, 준비할 것)" aria-label="메모">' + esc(r.memo) + '</textarea>' +
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

        // 캠핑장 정보
        h += '<div class="cp-box"><div class="cp-cname">' + cfg.icon + ' ' + esc(cur.title) + '</div>';
        if (cur.addr) h += '<div class="cp-line">📍 ' + esc(cur.addr) + '</div>';
        if (tel()) h += '<div class="cp-line">☎ <a href="tel:' + esc(tel().replace(/[^0-9+\-]/g, '')) + '">' + esc(tel()) + '</a>' + cfg.telNote + '</div>';
        h += '<div class="cp-date"><label for="cpDate">' + cfg.dateLabel + '</label><input type="date" id="cpDate" value="' + esc(P.date) + '"><span style="font-weight:600;color:#94a3b8;font-size:12px">(선택)</span></div>' +
            (cfg.hasFest ? '<div class="cp-line" id="cpDateNote" style="display:none;color:#b45309">근처 장소는 오늘 기준으로 골랐어요. 그날의 운영·휴관일은 확인표로 꼭 확인하세요.</div>' : '') + '</div>';

        if (!(cur._near && cur._near.length)) {
            h += '<div class="cp-warn">' + fill(cfg.noNear) + '</div>';
        }

        // 일정
        for (var d = 1; d <= P.days; d++) {
            h += '<div class="cp-dayhd"><span>' + esc(dayLabel(d)) + '</span></div>';
            P.rows.forEach(function (r) { if (r.day === d) h += rowHtml(r); });
            h += '<button type="button" class="cp-btn small" data-act="addrow" data-day="' + d + '">＋ 일정 추가</button>';
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
        h += '<div class="cp-hint"><b style="color:#334155">PDF로 저장하는 방법</b><br>인쇄 창에서 <b>대상(프린터)</b> 칸을 눌러 “PDF로 저장”(또는 “Microsoft Print to PDF”)을 고른 뒤, 오른쪽 아래 버튼이 “저장”으로 바뀌면 누르세요. 편집한 내용은 이 기기에만 저장되고 서버로 보내지 않아요.</div>';
        root.innerHTML = h;
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

    // ── 인쇄용 종이 ─────────────────────────────────────────────────────────────────
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
            h += '<h2>' + esc(dayLabel(d)) + '</h2><table><tr><th style="width:62px">시간</th><th style="width:38%">일정</th><th>메모</th></tr>';
            var any = false;
            P.rows.forEach(function (r) {
                if (r.day !== d) return;
                any = true;
                h += '<tr><td>' + esc(r.time) + '</td><td>' + esc(r.title) + '</td><td>' + esc(r.memo) + '</td></tr>';
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

    // [ADD] 2026-11-19: 상세보기는 일정표 위에 겹쳐 뜨는 팝업창으로 연다(일정표 화면·입력 내용은 그대로 남는다).
    // Ctrl/Shift/가운데 클릭이면 평소처럼 새 탭으로 연다. 팝업을 못 만드는 환경이면 링크가 그대로 새 창으로 열린다.
    var popEl = null, popKey = null, popPrevFocus = null;
    function closeDetail() {
        if (!popEl) return;
        try { document.body.removeChild(popEl); } catch (e) { /* 무시 */ }
        popEl = null;
        document.documentElement.style.overflow = popPrevOverflow;
        if (popKey) { document.removeEventListener('keydown', popKey, true); popKey = null; }
        if (popPrevFocus && popPrevFocus.focus) { try { popPrevFocus.focus(); } catch (e) { /* 무시 */ } }
    }
    var popPrevOverflow = '';
    function openDetail(href, name) {
        closeDetail();
        popPrevFocus = document.activeElement;
        var d = document.createElement('div');
        d.id = 'cpPop';
        d.setAttribute('role', 'dialog'); d.setAttribute('aria-modal', 'true'); d.setAttribute('aria-label', '장소 상세페이지');
        d.style.cssText = 'position:fixed;left:0;top:0;right:0;bottom:0;z-index:2147483000;background:rgba(15,23,42,.55);display:flex;align-items:center;justify-content:center;padding:12px;box-sizing:border-box';
        d.innerHTML = '<div style="background:#fff;border-radius:16px;width:100%;max-width:760px;height:100%;max-height:92vh;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,.4)">' +
            '<div style="display:flex;align-items:center;gap:8px;padding:10px 12px;border-bottom:1px solid #e2e8f0;background:#f8fafc;flex:0 0 auto">' +
            '<b style="font-size:14px;color:#0f172a;flex:1 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">📄 ' + esc(name || '장소 상세페이지') + '</b>' +
            '<a href="' + esc(href) + '" target="_blank" rel="noopener" style="font-size:12px;font-weight:800;color:#4f46e5;text-decoration:none;white-space:nowrap">새 창으로 열기 ↗</a>' +
            '<button type="button" id="cpPopX" aria-label="닫기" style="border:1px solid #cbd5e1;background:#fff;border-radius:8px;width:34px;height:30px;font-size:15px;font-weight:800;color:#334155;cursor:pointer;padding:0">✕</button>' +
            '</div>' +
            '<iframe src="' + esc(href) + '" title="장소 상세페이지" style="border:0;width:100%;flex:1 1 auto;min-height:0;background:#fff"></iframe></div>';
        d.addEventListener('click', function (ev) { if (ev.target === d) closeDetail(); });
        document.body.appendChild(d);
        popEl = d;
        popPrevOverflow = document.documentElement.style.overflow;
        document.documentElement.style.overflow = 'hidden';
        var x = d.querySelector('#cpPopX'); x.addEventListener('click', closeDetail); try { x.focus(); } catch (e) { /* 무시 */ }
        popKey = function (ev) { if (ev.key === 'Escape') { ev.preventDefault(); closeDetail(); } };
        document.addEventListener('keydown', popKey, true);
    }
    function onClick(e) {
        var dl = e.target.closest ? e.target.closest('a.cp-detail') : null;
        if (dl && root.contains(dl)) {
            if (e.ctrlKey || e.metaKey || e.shiftKey || e.button === 1) return;      // 새 탭 열기는 기본 동작 그대로
            e.preventDefault();
            var nm = ''; var re = dl.closest('.cp-row'); var ta = re ? re.querySelector('.cp-title') : null;
            if (ta) nm = String(ta.value || '').replace(/^\S+\s/, '').trim();
            openDetail(dl.getAttribute('href'), nm);
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
            P.rows.splice(fi, 0, { id: uid(), day: 1, time: timeAfter(fi, '14:30'), title: '🎪 ' + fx.f.title, memo: '행사 시간 확인 · ' + cfg.fromLabel + ' 약 ' + fmtKm(fx.km) + ' · ' + md(fx.f.startDate) + '~' + md(fx.f.endDate), k: 'f', pid: fx.f.contentid || fx.f.id || '' });
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
            P = defaultPlan(cur);
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
            if (i >= 0) { P.rows[i][f] = t.value; save(); }
        } else if (t.id === 'cpExtraIn') { if (/[\r\n]/.test(t.value)) t.value = t.value.replace(/[\r\n]+/g, ' '); fit(t); }
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
                if (Array.isArray(opts.over.checkA)) cfg.checkA = opts.over.checkA;
                if (opts.over.key) cfg.key = String(opts.over.key);
                if (typeof opts.over.hasFest === 'boolean') cfg.hasFest = opts.over.hasFest;
            }
            festList = [];
            cur = champ;
            // [ADD] 2026-11-19: opts.variant — 같은 장소로 서로 다른 일정표(예: 축제만 / 축제+나들이)를 따로 저장한다. opts.noDefaultNear — 근처 장소를 처음엔 일정에 넣지 않고 “더 넣기” 버튼으로만 보여 준다.
            var pid = champ.contentid + (opts && opts.variant ? ':' + String(opts.variant) : '');
            defNearOff = !!(opts && opts.noDefaultNear);
            P = load(pid);
            if (!P) { P = defaultPlan(champ); P.id = pid; }
            save();
            render();
            sec.style.display = 'block';
            fitAll();
            try { sec.scrollIntoView({ behavior: 'smooth', block: 'start' }); } catch (e) { sec.scrollIntoView(); }
        },
        hide: function () {
            closeDetail();
            var s = $('campPlan');
            if (s) s.style.display = 'none';
        }
    };
})();
