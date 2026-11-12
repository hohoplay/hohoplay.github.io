/* 호호플레이 선택 통계 — 월드컵·룰렛·"오늘 어디 갈까?" 결과를 익명으로 한 줄 기록한다.
   - 이름·쿠키·정확한 위치는 보내지 않는다(장소 번호와 고른 조건만).
   - 브라우저의 "추적 안 함(Do Not Track)"을 켜 둔 방문자와, 운영자가 관리 화면에서 끈 브라우저는 보내지 않는다.
   - 실패해도 페이지 동작에는 영향이 없다(조용히 무시). */
(function () {
  'use strict';
  var API = 'https://old-rain-16f7.lyh0929mm.workers.dev/e';
  function off() {
    try { if (navigator.doNotTrack === '1' || window.doNotTrack === '1') return true; } catch (e) {}
    try { if (localStorage.getItem('hhNoStat') === '1') return true; } catch (e) {}
    return false;
  }
  // t: wc(나들이 월드컵) · cwc(캠핑장 월드컵) · rl(룰렛) · pk(오늘 어디 갈까?)
  window.hhStat = function (t, id, o) {
    try {
      if (off() || !id) return;
      var body = JSON.stringify({ t: t, id: String(id), o: o || {} });
      // Content-Type 을 text/plain 으로 보내 브라우저의 사전 확인 요청(preflight) 없이 한 번에 보낸다
      fetch(API, { method: 'POST', headers: { 'Content-Type': 'text/plain;charset=UTF-8' }, body: body, keepalive: true, mode: 'cors', credentials: 'omit' })
        .catch(function () {});
    } catch (e) {}
  };
})();
