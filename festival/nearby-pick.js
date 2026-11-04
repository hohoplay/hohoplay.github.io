/*
 * 나들이픽 — 아이랑 장소 상세페이지(/festival/detail/kids-*.html) 댓글 아래에 "이 근처 나들이픽 5곳"을 그린다.
 *
 * [ADD] 2026-11-04
 *  - 상세페이지 템플릿(templates/kids_detail_template.html)에는 <div id="nearby-pick" data-id="kids-0159"></div>
 *    와 이 파일을 불러오는 <script> 한 줄만 있다. 추천 계산은 전부 여기서, 페이지를 열 때 한다.
 *    → 장소가 추가되거나 지오코딩이 좌표를 고쳐도 상세페이지를 다시 만들 필요가 없다. 규칙을 바꿀 때는 이 파일만 고친다.
 *  - 블록이 화면 근처에 왔을 때만 /data/kids_places.json 을 불러온다(IntersectionObserver).
 *
 * 고르는 규칙
 *  1) 이 장소를 뺀 나머지 중, 반경 10km 안에서 가까운 순. 5곳이 안 차면 25km까지 넓힌다. 하나도 없으면 블록을 숨긴다.
 *  2) 오늘(한국 시간) 쉬는 곳은 뺀다 — 요일 휴관, 기간 휴관(리모델링 등), 운영 기간 밖(계절 시설).
 *     (규칙은 festival/index.html 의 closedDaysFromHours / ctPeriodClosureOn / ctOutsideOperatingSeason 과 같다. 두 곳을 고칠 땐 같이 고칠 것.)
 *  3) 운영시간을 모르는 곳(비어 있거나 "확인 필요")은 실제 거리에 2km를 더해서 순위를 매긴다(뒤로 밀림). 화면에는 실제 거리를 보여준다.
 *  4) 같은 좌표(같은 건물/같은 지역 중심 좌표)에 있는 곳은 최대 2곳.
 *  5) 5곳이 전부 실내거나 전부 실외면, 마지막 자리를 반대 유형(가장 가까운 곳)으로 바꾼다. "실내외"는 어느 쪽에도 안 센다.
 *  운영시간·요금은 사람이 쓴 자유 텍스트라 읽을 수 있는 것만 읽는다. 애매하면 쉬는 날로 보지 않고 "운영시간 확인 필요"로 표시한다.
 */
(function () {
    'use strict';

    var MAX_PICKS = 5;
    var NEAR_KM = 10;
    var FAR_KM = 25;
    var UNKNOWN_HOURS_PENALTY_KM = 2;
    var MAX_PER_COORD = 2;
    var DATA_URL = '/data/kids_places.json';

    var root = document.getElementById('nearby-pick');
    if (!root) return;
    var selfId = root.getAttribute('data-id') || '';
    if (!selfId) return;

    // ── 휴관 판정 (festival/index.html 과 같은 규칙) ──────────────────────────────────────
    var CT_D = '[월화수목금토일]';
    var CT_DL = CT_D + '(?:\\s*요일)?(?:\\s*[·,/]\\s*' + CT_D + '(?:\\s*요일)?)*';
    var CT_RE_P1 = new RegExp('매주\\s*(' + CT_DL + ')([^/;\\n운영개방~]{0,40}?)(?:휴관|휴무|휴일)', 'g');
    var CT_RE_P2 = new RegExp('(^|[^가-힣0-9~])(' + CT_DL + ')\\s*(?:[·,]\\s*(?:법정)?공휴일)?\\s*(?:정기\\s*)?(?:휴관|휴무)', 'g');
    var CT_RE_P3 = new RegExp('(^|[^가-힣0-9])(' + CT_D + ')\\s*~\\s*(' + CT_D + ')\\s*(?:요일)?\\s*(?:정기\\s*)?(?:휴관|휴무)', 'g');
    var CT_RE_P4 = new RegExp('^\\s*(' + CT_D + ')\\s*~\\s*(' + CT_D + ')\\s*(?:요일)?\\s*\\d{1,2}:\\d{2}\\s*~\\s*\\d{1,2}:\\d{2}\\s*(?:\\([^)]*\\))?\\s*$');
    var CT_DAYS = '월화수목금토일';

    function ctDaysOf(s) {
        var out = [];
        var clean = String(s).replace(/요일/g, '');
        for (var i = 0; i < clean.length; i++) if (CT_DAYS.indexOf(clean.charAt(i)) >= 0) out.push(clean.charAt(i));
        return out;
    }

    function closedDaysFromHours(hours) {
        var h = String(hours || '').trim();
        if (!h || h.indexOf('확인되지 않') >= 0 || h.indexOf('확인 필요') >= 0 || h.indexOf('확인필요') >= 0) return { closed: [], known: false };
        var closed = {};
        var partial = function (idx) {
            return /째|마지막\s*주|격주|비수기|성수기|하절기|동절기/.test(h.slice(Math.max(0, idx - 12), idx));
        };
        var m;
        CT_RE_P1.lastIndex = 0;
        while ((m = CT_RE_P1.exec(h)) !== null) {
            if (/\d{1,2}:\d{2}/.test(m[2]) || partial(m.index)) continue;
            ctDaysOf(m[1]).forEach(function (d) { closed[d] = true; });
        }
        CT_RE_P2.lastIndex = 0;
        while ((m = CT_RE_P2.exec(h)) !== null) {
            if (partial(m.index + m[1].length)) continue;
            ctDaysOf(m[2]).forEach(function (d) { closed[d] = true; });
        }
        CT_RE_P3.lastIndex = 0;
        while ((m = CT_RE_P3.exec(h)) !== null) {
            var a3 = CT_DAYS.indexOf(m[2]), b3 = CT_DAYS.indexOf(m[3]);
            if (a3 <= b3) for (var i = a3; i <= b3; i++) closed[CT_DAYS.charAt(i)] = true;
        }
        m = CT_RE_P4.exec(h);
        if (m) {
            var a = CT_DAYS.indexOf(m[1]), b = CT_DAYS.indexOf(m[2]);
            if (a <= b) for (var j = 0; j < CT_DAYS.length; j++) if (j < a || j > b) closed[CT_DAYS.charAt(j)] = true;
        }
        var list = Object.keys(closed);
        if (list.length) return { closed: list, known: true };
        if (/연중무휴|매일|상시 개방|상시개방/.test(h)) return { closed: [], known: true };
        return { closed: [], known: false };
    }

    var CT_PD = '(?:(\\d{4}|\\d{2})\\s*(?:년|[-./])\\s*)?(\\d{1,2})\\s*(?:월|[-./])\\s*(\\d{1,2})\\s*일?';
    var CT_PD_KW = '(?:임시\\s*휴관|임시\\s*휴무|휴관|휴무|휴장|리모델링|공사|보수)';
    var CT_PD_SEP = '\\s*[~～∼–]\\s*';
    var CT_PD_RE_BEFORE = new RegExp(CT_PD_KW + '[^0-9~～∼–]{0,6}' + CT_PD + CT_PD_SEP + CT_PD, 'g');
    var CT_PD_RE_AFTER = new RegExp(CT_PD + CT_PD_SEP + CT_PD + '[\\s:：()\\[\\]·,]{0,3}(?:까지)?[\\s:：()\\[\\]·,]{0,3}' + CT_PD_KW, 'g');
    var CT_SEASON_RE = new RegExp('(?:운영\\s*기간|개장\\s*기간)[^0-9~～∼–]{0,4}' + CT_PD + CT_PD_SEP + CT_PD, 'g');

    function toYear(y) { return y.length === 2 ? 2000 + parseInt(y, 10) : parseInt(y, 10); }

    function rangeHit(g, key, y0) {
        var m1 = parseInt(g[2], 10), d1 = parseInt(g[3], 10), m2 = parseInt(g[5], 10), d2 = parseInt(g[6], 10);
        if (m1 < 1 || m1 > 12 || m2 < 1 || m2 > 12 || d1 < 1 || d1 > 31 || d2 < 1 || d2 > 31) return null;   // null = 읽을 수 없음
        var startYears = g[1] ? [toYear(g[1])] : [y0 - 1, y0];
        var hit = false;
        startYears.forEach(function (ys) {
            var ye = g[4] ? toYear(g[4]) : ((m2 * 100 + d2) < (m1 * 100 + d1) ? ys + 1 : ys);
            var s = ys * 10000 + m1 * 100 + d1, e = ye * 10000 + m2 * 100 + d2;
            if (s <= key && key <= e) hit = true;
        });
        return hit;
    }

    function inPeriodClosure(hours, dateStr) {
        var h = String(hours || '');
        if (!h || (h.indexOf('~') < 0 && h.indexOf('～') < 0 && h.indexOf('∼') < 0 && h.indexOf('–') < 0)) return false;
        var key = parseInt(dateStr, 10), y0 = parseInt(String(dateStr).slice(0, 4), 10);
        var found = false;
        [CT_PD_RE_BEFORE, CT_PD_RE_AFTER].forEach(function (re) {
            re.lastIndex = 0;
            var m;
            while ((m = re.exec(h)) !== null) {
                if (rangeHit(m, key, y0) === true) found = true;
                if (m.index === re.lastIndex) re.lastIndex++;
            }
        });
        return found;
    }

    function outsideSeason(hours, dateStr) {
        var h = String(hours || '');
        if (!h || h.indexOf('기간') < 0) return false;
        var key = parseInt(dateStr, 10), y0 = parseInt(String(dateStr).slice(0, 4), 10);
        var seen = false, inside = false, g;
        CT_SEASON_RE.lastIndex = 0;
        while ((g = CT_SEASON_RE.exec(h)) !== null) {
            if (g.index === CT_SEASON_RE.lastIndex) CT_SEASON_RE.lastIndex++;
            var r = rangeHit(g, key, y0);
            if (r === null) continue;
            seen = true;
            if (r) inside = true;
        }
        return seen && !inside;
    }

    // 한국 시간 기준 오늘: { dateStr: 'YYYYMMDD', dowChar: '월' }
    function koreaToday() {
        var parts = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date()).split('-');
        var y = parseInt(parts[0], 10), mo = parseInt(parts[1], 10), d = parseInt(parts[2], 10);
        var dow = new Date(Date.UTC(y, mo - 1, d)).getUTCDay();   // 0=일
        return { dateStr: parts[0] + parts[1] + parts[2], dowChar: '일월화수목금토'.charAt(dow) };
    }

    // ── 거리 ───────────────────────────────────────────────────────────────────────────
    function haversineKm(lat1, lng1, lat2, lng2) {
        var R = 6371, toRad = Math.PI / 180;
        var dLat = (lat2 - lat1) * toRad, dLng = (lng2 - lng1) * toRad;
        var a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * toRad) * Math.cos(lat2 * toRad) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
        return 2 * R * Math.asin(Math.min(1, Math.sqrt(a)));
    }

    function validCoord(p) {
        return typeof p.lat === 'number' && typeof p.lng === 'number' && isFinite(p.lat) && isFinite(p.lng) && p.lat !== 0 && p.lng !== 0;
    }

    function coordKey(p) { return p.lat.toFixed(4) + ',' + p.lng.toFixed(4); }

    // ── 추천 계산 ──────────────────────────────────────────────────────────────────────
    function pickNearby(all, self, today) {
        var cands = [];
        all.forEach(function (p) {
            if (!p || p.contentid === self.contentid || !p.title || !validCoord(p)) return;
            if (p.title === self.title) return;
            var hours = p.hours || '';
            var cd = closedDaysFromHours(hours);
            if (cd.known && cd.closed.indexOf(today.dowChar) >= 0) return;
            if (inPeriodClosure(hours, today.dateStr)) return;
            if (outsideSeason(hours, today.dateStr)) return;
            var km = haversineKm(self.lat, self.lng, p.lat, p.lng);
            // 운영시간 자체를 모르는 곳(비어 있거나 "확인 필요")만 뒤로 민다. 시간은 적혀 있는데 휴관 요일만 못 읽은 곳은 그대로 둔다.
            var hoursKnown = !(!String(hours).trim() || /확인되지\s*않|확인\s*필요/.test(hours));
            cands.push({ p: p, km: km, rank: km + (hoursKnown ? 0 : UNKNOWN_HOURS_PENALTY_KM), hoursKnown: hoursKnown });
        });
        cands.sort(function (a, b) { return a.rank - b.rank || a.km - b.km; });

        var radius = NEAR_KM;
        var pool = cands.filter(function (c) { return c.km <= NEAR_KM; });
        if (pool.length < MAX_PICKS) {
            radius = FAR_KM;
            pool = cands.filter(function (c) { return c.km <= FAR_KM; });
        }

        // 같은 좌표 최대 MAX_PER_COORD곳
        var perCoord = {};
        pool = pool.filter(function (c) {
            var k = coordKey(c.p);
            perCoord[k] = (perCoord[k] || 0) + 1;
            return perCoord[k] <= MAX_PER_COORD;
        });

        var picks = pool.slice(0, MAX_PICKS);

        // 전부 실내거나 전부 실외면 마지막 자리를 반대 유형으로 바꾼다
        if (picks.length === MAX_PICKS) {
            var indoor = picks.filter(function (c) { return c.p.placeType === '실내'; }).length;
            var outdoor = picks.filter(function (c) { return c.p.placeType === '실외'; }).length;
            var want = null;
            if (indoor === MAX_PICKS) want = '실외';
            else if (outdoor === MAX_PICKS) want = '실내';
            if (want) {
                var swap = null;
                for (var i = MAX_PICKS; i < pool.length; i++) {
                    if (pool[i].p.placeType === want) { swap = pool[i]; break; }
                }
                if (swap) picks[MAX_PICKS - 1] = swap;
            }
        }
        picks.sort(function (a, b) { return a.km - b.km; });   // 화면에는 실제 거리 순으로
        return { picks: picks, radius: radius };
    }

    // ── 화면 ───────────────────────────────────────────────────────────────────────────
    function injectStyle() {
        if (document.getElementById('nearby-pick-style')) return;
        var st = document.createElement('style');
        st.id = 'nearby-pick-style';
        st.textContent =
            '#nearby-pick .np-wrap{max-width:640px;margin:0 auto 16px;padding:0 20px;box-sizing:border-box}' +
            '#nearby-pick .np-card{background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:20px}' +
            '#nearby-pick .np-title{font-size:15px;font-weight:900;color:#1e293b;margin:0 0 4px}' +
            '#nearby-pick .np-sub{font-size:12px;color:#94a3b8;line-height:1.5;margin:0 0 14px}' +
            '#nearby-pick .np-list{display:flex;flex-direction:column;gap:10px;margin:0;padding:0;list-style:none}' +
            '#nearby-pick .np-item{display:block;text-decoration:none;border:1px solid #e2e8f0;border-radius:12px;padding:12px 14px;background:#f8fafc;color:inherit}' +
            '#nearby-pick .np-item:hover{border-color:#a5b4fc;background:#eef2ff}' +
            '#nearby-pick .np-top{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}' +
            '#nearby-pick .np-name{font-size:14px;font-weight:800;color:#111;line-height:1.4;word-break:keep-all}' +
            '#nearby-pick .np-dist{flex:0 0 auto;font-size:12px;font-weight:800;color:#4f46e5;white-space:nowrap;padding-top:1px}' +
            '#nearby-pick .np-desc{font-size:12.5px;color:#475569;line-height:1.5;margin-top:4px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}' +
            '#nearby-pick .np-tags{display:flex;flex-wrap:wrap;gap:5px;margin-top:8px}' +
            '#nearby-pick .np-tag{font-size:11px;font-weight:700;color:#475569;background:#e2e8f0;border-radius:999px;padding:2px 8px}' +
            '#nearby-pick .np-tag.free{color:#047857;background:#d1fae5}' +
            '#nearby-pick .np-tag.warn{color:#b45309;background:#fef3c7}';
        document.head.appendChild(st);
    }

    function el(tag, cls, text) {
        var e = document.createElement(tag);
        if (cls) e.className = cls;
        if (text != null) e.textContent = text;
        return e;
    }

    function fmtDist(km) {
        if (km < 0.1) return '바로 근처';
        if (km < 1) return Math.round(km * 10) * 100 + 'm';
        return (Math.round(km * 10) / 10).toFixed(1) + 'km';
    }

    function render(result, self, today) {
        var picks = result.picks;
        if (!picks.length) { root.style.display = 'none'; return; }
        injectStyle();
        root.innerHTML = '';
        var wrap = el('div', 'np-wrap');
        var card = el('div', 'np-card');
        card.appendChild(el('h2', 'np-title', '🧸 이 근처 나들이픽'));
        var sub = self.title + ' 가까이에서 아이랑 가볼 만한 곳이에요. 오늘(' + today.dowChar + ') 쉬는 곳은 뺐어요.';
        if (result.radius > NEAR_KM) sub += ' 가까운 곳이 적어서 ' + result.radius + 'km까지 넓혀 찾았어요.';
        card.appendChild(el('p', 'np-sub', sub));

        var ul = el('ul', 'np-list');
        picks.forEach(function (c) {
            var p = c.p;
            var li = document.createElement('li');
            var a = document.createElement('a');
            a.className = 'np-item';
            a.href = '/festival/detail/' + encodeURIComponent(p.contentid) + '.html';
            var top = el('div', 'np-top');
            top.appendChild(el('div', 'np-name', p.title));
            top.appendChild(el('div', 'np-dist', fmtDist(c.km)));
            a.appendChild(top);
            if (p.desc) a.appendChild(el('div', 'np-desc', p.desc));
            var tags = el('div', 'np-tags');
            if (p.placeType) tags.appendChild(el('span', 'np-tag', p.placeType));
            var cost = p.costTag;
            if (cost === '완전무료') tags.appendChild(el('span', 'np-tag free', '무료'));
            else if (cost === '유료') tags.appendChild(el('span', 'np-tag', '유료'));
            else if (cost === '유료(일부 무료 조건 있음)') tags.appendChild(el('span', 'np-tag', '일부 무료'));
            else tags.appendChild(el('span', 'np-tag warn', '요금 확인 필요'));
            if (!c.hoursKnown) tags.appendChild(el('span', 'np-tag warn', '운영시간 확인 필요'));
            a.appendChild(tags);
            li.appendChild(a);
            ul.appendChild(li);
        });
        card.appendChild(ul);
        wrap.appendChild(card);
        root.appendChild(wrap);
    }

    function run() {
        fetch(DATA_URL).then(function (r) { return r.ok ? r.json() : []; }).then(function (all) {
            if (!Array.isArray(all)) return;
            var self = null;
            for (var i = 0; i < all.length; i++) if (all[i] && all[i].contentid === selfId) { self = all[i]; break; }
            if (!self || !validCoord(self)) return;   // 데이터에 없는 옛 페이지 → 블록 없음
            render(pickNearby(all, self, koreaToday()), self, koreaToday());
        }).catch(function () { /* 실패해도 상세페이지 표시엔 영향 없음 */ });
    }

    var started = false;
    function start() { if (started) return; started = true; run(); }

    if ('IntersectionObserver' in window) {
        var io = new IntersectionObserver(function (entries) {
            if (entries.some(function (e) { return e.isIntersecting; })) { io.disconnect(); start(); }
        }, { rootMargin: '600px 0px' });
        io.observe(root);
    } else {
        start();
    }
})();
