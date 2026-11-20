/* 호호매거진 최신 글 3개 — 상세페이지가 열릴 때 /blog 와 같은 글 API 로 불러온다.
   (장소 상세페이지를 다시 만들 필요 없음. 카테고리/개수를 바꿀 땐 이 파일만 고친다.)
   실패하거나 글이 없으면 섹션을 숨겨서 빈 칸이 보이지 않게 한다. */
(function () {
  var box = document.getElementById('latest-magazine');
  if (!box) return;
  var API = 'https://old-rain-16f7.lyh0929mm.workers.dev/posts';
  var CATEGORY = '호호 매거진';
  var COUNT = 3;
  function esc(s) { var d = document.createElement('div'); d.textContent = s == null ? '' : String(s); return d.innerHTML; }
  function fmt(ts) {
    var t = typeof ts === 'number' ? ts : Date.parse(ts);
    if (!t) return '';
    var d = new Date(t);
    return d.getFullYear() + '.' + String(d.getMonth() + 1).padStart(2, '0') + '.' + String(d.getDate()).padStart(2, '0');
  }
  function hide() { box.style.display = 'none'; }
  fetch(API + '?_=' + Date.now(), { cache: 'no-store' })
    .then(function (r) { if (!r.ok) throw new Error('http'); return r.json(); })
    .then(function (data) {
      var list = Array.isArray(data) ? data : (data && (data.posts || data.results || data.data)) || [];
      list = list.filter(function (p) { return p && p.category === CATEGORY && p.id != null && p.title; });
      list.sort(function (a, b) { return (Date.parse(b.created_at) || b.created_at || 0) - (Date.parse(a.created_at) || a.created_at || 0); });
      list = list.slice(0, COUNT);
      if (!list.length) return hide();
      var h = '<h2 class="pt-h2">📰 호호매거진 최신 글</h2><ul class="pt-links">';
      list.forEach(function (p) {
        h += '<li><a href="/blog/magazine/' + encodeURIComponent(p.id) + '.html" class="detail-link">' + esc(p.title) + '</a>' +
             '<span class="pt-sub">' + esc(fmt(p.created_at)) + '</span></li>';
      });
      h += '</ul><p style="margin:10px 0 0;"><a href="/blog/" class="detail-link">매거진 전체 보기 →</a></p>';
      box.innerHTML = h;
    })
    .catch(hide);
})();
