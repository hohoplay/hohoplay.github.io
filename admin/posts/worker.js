const ALLOWED_ORIGINS = ['https://hohoplaylab.com', 'https://hohoplay.github.io'];
const MAX_NICKNAME_LEN = 20;
const MAX_CONTENT_LEN = 300;
const COOLDOWN_MS = 30 * 1000;
const LIST_LIMIT = 50;

// [ADD] /admin/comments 페이지네이션 기본/최대 페이지 크기.
// 댓글이 계속 늘어나면서 200건 고정 조회로는 그 이상을 확인할 방법이 없었음.
const ADMIN_COMMENTS_DEFAULT_LIMIT = 50;
const ADMIN_COMMENTS_MAX_LIMIT = 200;

const BANNED_WORDS = ['시발', '씨발', '병신', 'ㅅㅂ', 'ㅂㅅ'];

async function hashIp(ip) {
  const enc = new TextEncoder().encode(ip + '|hohoplay-salt');
  const buf = await crypto.subtle.digest('SHA-256', enc);
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, '0')).join('');
}

function containsBannedWord(text) {
  const lower = text.toLowerCase();
  return BANNED_WORDS.some(w => lower.includes(w));
}

// [ADD] 쿼리스트링의 limit/offset을 안전한 범위로 정리한다.
// 값이 없거나 숫자가 아니면 기본값을, 범위를 벗어나면 최소/최대값으로 잘라낸다.
function parsePageParams(url) {
  let limit = parseInt(url.searchParams.get('limit') || '', 10);
  if (!Number.isFinite(limit) || limit < 1) limit = ADMIN_COMMENTS_DEFAULT_LIMIT;
  if (limit > ADMIN_COMMENTS_MAX_LIMIT) limit = ADMIN_COMMENTS_MAX_LIMIT;

  let offset = parseInt(url.searchParams.get('offset') || '', 10);
  if (!Number.isFinite(offset) || offset < 0) offset = 0;

  return { limit, offset };
}

async function getPollResults(env, pollId) {
  const { results } = await env.DB.prepare(
    'SELECT option_index, COUNT(*) as cnt FROM poll_votes WHERE poll_id = ? GROUP BY option_index'
  ).bind(pollId).all();
  const counts = {};
  let total = 0;
  for (const row of results) {
    counts[row.option_index] = row.cnt;
    total += row.cnt;
  }
  return { counts, total };
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // 요청의 실제 Origin이 허용 목록에 있으면 그대로, 없으면 기본값(새 도메인)으로 응답
    const reqOrigin = request.headers.get('Origin');
    const allowOrigin = ALLOWED_ORIGINS.includes(reqOrigin) ? reqOrigin : ALLOWED_ORIGINS[0];
    const cors = {
      'Access-Control-Allow-Origin': allowOrigin,
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    };
    function json(data, status = 200) {
      return new Response(JSON.stringify(data), {
        status,
        headers: { 'Content-Type': 'application/json; charset=utf-8', ...cors },
      });
    }

    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: cors });
    }

    // ══════════════ 조회수 ══════════════
    if (url.pathname === '/views' && request.method === 'GET') {
      const pageId = url.searchParams.get('page_id');
      if (!pageId) return json({ error: 'page_id required' }, 400);

      const row = await env.DB.prepare(
        `INSERT INTO page_views (page_id, views) VALUES (?, 1)
         ON CONFLICT(page_id) DO UPDATE SET views = views + 1
         RETURNING views`
      ).bind(pageId).first();

      return json({ page_id: pageId, views: row.views });
    }

    if (url.pathname === '/views/batch' && request.method === 'GET') {
      // 여러 페이지 조회수를 한 번에 조회만 하고 싶을 때(증가 없이) — 예: 목록 페이지에서 여러 개 동시 표시
      const idsParam = url.searchParams.get('ids');
      if (!idsParam) return json({ error: 'ids required' }, 400);
      const ids = idsParam.split(',').map(s => s.trim()).filter(Boolean).slice(0, 50);
      if (ids.length === 0) return json({ views: {} });

      const placeholders = ids.map(() => '?').join(',');
      const { results } = await env.DB.prepare(
        `SELECT page_id, views FROM page_views WHERE page_id IN (${placeholders})`
      ).bind(...ids).all();

      const views = {};
      for (const id of ids) views[id] = 0;
      for (const row of results) views[row.page_id] = row.views;
      return json({ views });
    }

    // ══════════════ 관리자 전용 (댓글) ══════════════
    if (url.pathname === '/admin/comments' && request.method === 'GET') {
      if (url.searchParams.get('key') !== env.ADMIN_KEY) {
        return json({ error: 'unauthorized' }, 401);
      }
      const gameId = url.searchParams.get('game_id');
      // [FIX] 댓글이 계속 늘어나면서 LIMIT 200 고정 조회로는 그 이상을 볼 방법이
      // 없었음. limit/offset을 받아 페이지 단위로 조회하고, total을 같이 내려줘서
      // 화면에서 "다음 페이지가 더 있는지"를 판단할 수 있게 한다.
      const { limit, offset } = parsePageParams(url);

      let results, totalRow;
      if (gameId) {
        ({ results } = await env.DB.prepare(
          'SELECT id, game_id, nickname, content, created_at, ip_address, country FROM comments WHERE game_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?'
        ).bind(gameId, limit, offset).all());
        totalRow = await env.DB.prepare(
          'SELECT COUNT(*) as cnt FROM comments WHERE game_id = ?'
        ).bind(gameId).first();
      } else {
        ({ results } = await env.DB.prepare(
          'SELECT id, game_id, nickname, content, created_at, ip_address, country FROM comments ORDER BY created_at DESC LIMIT ? OFFSET ?'
        ).bind(limit, offset).all());
        totalRow = await env.DB.prepare(
          'SELECT COUNT(*) as cnt FROM comments'
        ).first();
      }
      return json({ comments: results, total: totalRow.cnt, limit, offset });
    }

    if (url.pathname === '/admin/comments' && request.method === 'DELETE') {
      if (url.searchParams.get('key') !== env.ADMIN_KEY) {
        return json({ error: 'unauthorized' }, 401);
      }
      const id = url.searchParams.get('id');
      if (!id) return json({ error: 'id required' }, 400);
      await env.DB.prepare('DELETE FROM comments WHERE id = ?').bind(id).run();
      return json({ ok: true });
    }

    // [ADD] 댓글 수정 — /admin/posts PUT과 동일한 패턴. 신고·오타 등으로 관리자가
    // 닉네임/내용을 직접 고쳐야 할 때를 위해 추가. game_id·작성시각·IP·국가는
    // 원본 그대로 유지하고 nickname/content만 바꾼다.
    if (url.pathname === '/admin/comments' && request.method === 'PUT') {
      if (url.searchParams.get('key') !== env.ADMIN_KEY) {
        return json({ error: 'unauthorized' }, 401);
      }
      let body;
      try {
        body = await request.json();
      } catch {
        return json({ error: 'invalid json' }, 400);
      }

      const id = Number(body.id);
      const nickname = (body.nickname || '').trim();
      const content = (body.content || '').trim();

      if (!id || !nickname || !content) {
        return json({ error: '필수 항목이 비어있습니다' }, 400);
      }
      if (nickname.length > MAX_NICKNAME_LEN) {
        return json({ error: `닉네임은 ${MAX_NICKNAME_LEN}자 이하로 입력해주세요` }, 400);
      }
      if (content.length > MAX_CONTENT_LEN) {
        return json({ error: `댓글은 ${MAX_CONTENT_LEN}자 이하로 입력해주세요` }, 400);
      }

      const existing = await env.DB.prepare('SELECT id FROM comments WHERE id = ?').bind(id).first();
      if (!existing) return json({ error: 'not found' }, 404);

      await env.DB.prepare(
        'UPDATE comments SET nickname = ?, content = ? WHERE id = ?'
      ).bind(nickname, content, id).run();

      return json({ ok: true, id });
    }

    // ══════════════ 관리자 전용 (게시글 작성·수정·삭제) ══════════════
    // [ADD] 관리자용 전체 게시글 조회(본문 포함) — writer.html의 "내용 검색" 기능이
    // 쓴다. 공개용 /posts는 목록 카드 렌더링용이라 일부러 content를 안 내려주는데
    // (모든 방문자가 볼 때마다 전체 본문까지 받을 필요는 없어서), 관리자가 옛날
    // 게시글 본문에서 특정 문구(예: 예전 도메인 주소)를 찾을 땐 본문까지 다 필요해서
    // 이 엔드포인트를 따로 둔다.
    if (url.pathname === '/admin/posts' && request.method === 'GET') {
      if (url.searchParams.get('key') !== env.ADMIN_KEY) {
        return json({ error: 'unauthorized' }, 401);
      }
      const { results } = await env.DB.prepare(
        'SELECT id, category, title, author, content, created_at FROM posts ORDER BY created_at DESC LIMIT 200'
      ).all();
      return json({ posts: results });
    }

    if (url.pathname === '/admin/posts' && request.method === 'POST') {
      if (url.searchParams.get('key') !== env.ADMIN_KEY) {
        return json({ error: 'unauthorized' }, 401);
      }
      let body;
      try {
        body = await request.json();
      } catch {
        return json({ error: 'invalid json' }, 400);
      }

      const category = (body.category || '').trim();
      const title = (body.title || '').trim();
      const author = (body.author || '').trim();
      const content = (body.content || '').trim();

      if (!category || !title || !author || !content) {
        return json({ error: '필수 항목이 비어있습니다' }, 400);
      }

      const now = Date.now();
      const row = await env.DB.prepare(
        'INSERT INTO posts (category, title, author, content, created_at) VALUES (?, ?, ?, ?, ?) RETURNING id'
      ).bind(category, title, author, content, now).first();

      return json({ ok: true, id: row.id });
    }

    if (url.pathname === '/admin/posts' && request.method === 'PUT') {
      if (url.searchParams.get('key') !== env.ADMIN_KEY) {
        return json({ error: 'unauthorized' }, 401);
      }
      let body;
      try {
        body = await request.json();
      } catch {
        return json({ error: 'invalid json' }, 400);
      }

      const id = Number(body.id);
      const category = (body.category || '').trim();
      const title = (body.title || '').trim();
      const author = (body.author || '').trim();
      const content = (body.content || '').trim();

      if (!id || !category || !title || !author || !content) {
        return json({ error: '필수 항목이 비어있습니다' }, 400);
      }

      const existing = await env.DB.prepare('SELECT id FROM posts WHERE id = ?').bind(id).first();
      if (!existing) return json({ error: 'not found' }, 404);

      await env.DB.prepare(
        'UPDATE posts SET category = ?, title = ?, author = ?, content = ? WHERE id = ?'
      ).bind(category, title, author, content, id).run();

      return json({ ok: true, id });
    }

    if (url.pathname === '/admin/posts' && request.method === 'DELETE') {
      if (url.searchParams.get('key') !== env.ADMIN_KEY) {
        return json({ error: 'unauthorized' }, 401);
      }
      const id = url.searchParams.get('id');
      if (!id) return json({ error: 'id required' }, 400);
      await env.DB.prepare('DELETE FROM posts WHERE id = ?').bind(id).run();
      return json({ ok: true });
    }

    // ══════════════ 댓글 ══════════════
    if (url.pathname === '/comments') {
      if (request.method === 'GET') {
        const gameId = url.searchParams.get('game_id');
        if (!gameId) return json({ error: 'game_id required' }, 400);

        const { results } = await env.DB.prepare(
          'SELECT nickname, content, created_at FROM comments WHERE game_id = ? ORDER BY created_at DESC LIMIT ?'
        ).bind(gameId, LIST_LIMIT).all();

        return json({ comments: results });
      }

      if (request.method === 'POST') {
        let body;
        try {
          body = await request.json();
        } catch {
          return json({ error: 'invalid json' }, 400);
        }

        const gameId = (body.game_id || '').trim();
        const nickname = (body.nickname || '').trim();
        const content = (body.content || '').trim();

        if (!gameId || !nickname || !content) {
          return json({ error: '필수 항목이 비어있습니다' }, 400);
        }
        if (nickname.length > MAX_NICKNAME_LEN) {
          return json({ error: `닉네임은 ${MAX_NICKNAME_LEN}자 이하로 입력해주세요` }, 400);
        }
        if (content.length > MAX_CONTENT_LEN) {
          return json({ error: `댓글은 ${MAX_CONTENT_LEN}자 이하로 입력해주세요` }, 400);
        }
        if (containsBannedWord(nickname) || containsBannedWord(content)) {
          return json({ error: '부적절한 표현이 포함되어 있습니다' }, 400);
        }

        const ip = request.headers.get('CF-Connecting-IP') || 'unknown';
        const ipHash = await hashIp(ip);
        // [ADD] 관리자 화면에서 국가·IP를 확인할 수 있도록 원본값을 같이 저장한다.
        // request.cf는 Cloudflare가 엣지에서 자동으로 채워주는 값이라 별도
        // GeoIP 서비스 호출 없이 국가코드(ISO 2자리, 예: KR)를 바로 얻을 수 있다.
        const country = (request.cf && request.cf.country) || 'XX';
        const now = Date.now();

        const last = await env.DB.prepare(
          'SELECT created_at FROM comments WHERE ip_hash = ? ORDER BY created_at DESC LIMIT 1'
        ).bind(ipHash).first();

        if (last && now - last.created_at < COOLDOWN_MS) {
          const waitSec = Math.ceil((COOLDOWN_MS - (now - last.created_at)) / 1000);
          return json({ error: `${waitSec}초 후에 다시 시도해주세요` }, 429);
        }

        await env.DB.prepare(
          'INSERT INTO comments (game_id, nickname, content, created_at, ip_hash, ip_address, country) VALUES (?, ?, ?, ?, ?, ?, ?)'
        ).bind(gameId, nickname, content, now, ipHash, ip, country).run();

        return json({ ok: true });
      }

      return json({ error: 'method not allowed' }, 405);
    }

    // ══════════════ 커뮤니티 게시글 (공개 조회) ══════════════
    if (url.pathname === '/posts' && request.method === 'GET') {
      const category = url.searchParams.get('category');
      let results;
      if (category) {
        ({ results } = await env.DB.prepare(
          'SELECT id, category, title, author, created_at FROM posts WHERE category = ? ORDER BY created_at DESC LIMIT 200'
        ).bind(category).all());
      } else {
        ({ results } = await env.DB.prepare(
          'SELECT id, category, title, author, created_at FROM posts ORDER BY created_at DESC LIMIT 200'
        ).all());
      }
      return json({ posts: results });
    }

    if (/^\/posts\/\d+$/.test(url.pathname) && request.method === 'GET') {
      const id = url.pathname.split('/')[2];
      const post = await env.DB.prepare(
        'SELECT id, category, title, author, content, created_at FROM posts WHERE id = ?'
      ).bind(id).first();
      if (!post) return json({ error: 'not found' }, 404);
      return json({ post });
    }

    // ══════════════ 투표 결과 조회 ══════════════
    if (url.pathname === '/polls/results' && request.method === 'GET') {
      const pollId = url.searchParams.get('poll_id');
      if (!pollId) return json({ error: 'poll_id required' }, 400);

      const { counts, total } = await getPollResults(env, pollId);

      // 이 방문자가 이미 투표했는지도 같이 알려줌 (IP 기준)
      const ip = request.headers.get('CF-Connecting-IP') || 'unknown';
      const ipHash = await hashIp(ip);
      const voted = await env.DB.prepare(
        'SELECT option_index FROM poll_votes WHERE poll_id = ? AND ip_hash = ?'
      ).bind(pollId, ipHash).first();

      return json({ counts, total, votedOption: voted ? voted.option_index : null });
    }

    // ══════════════ 투표하기 ══════════════
    if (url.pathname === '/polls/vote' && request.method === 'POST') {
      let body;
      try {
        body = await request.json();
      } catch {
        return json({ error: 'invalid json' }, 400);
      }

      const pollId = (body.poll_id || '').trim();
      const optionIndex = Number(body.option_index);

      if (!pollId || !Number.isInteger(optionIndex) || optionIndex < 0 || optionIndex > 9) {
        return json({ error: '잘못된 요청입니다' }, 400);
      }

      const ip = request.headers.get('CF-Connecting-IP') || 'unknown';
      const ipHash = await hashIp(ip);
      const now = Date.now();

      try {
        await env.DB.prepare(
          'INSERT INTO poll_votes (poll_id, option_index, ip_hash, created_at) VALUES (?, ?, ?, ?)'
        ).bind(pollId, optionIndex, ipHash, now).run();
      } catch (e) {
        // UNIQUE 제약 위반 = 이미 투표한 경우
        const { counts, total } = await getPollResults(env, pollId);
        const voted = await env.DB.prepare(
          'SELECT option_index FROM poll_votes WHERE poll_id = ? AND ip_hash = ?'
        ).bind(pollId, ipHash).first();
        return json({ error: '이미 투표하셨습니다', counts, total, votedOption: voted ? voted.option_index : null }, 409);
      }

      const { counts, total } = await getPollResults(env, pollId);
      return json({ ok: true, counts, total, votedOption: optionIndex });
    }

    return json({ error: 'not found' }, 404);
  },
};
