// sw.js
// 다낭 여행 가이드 지도 - 오프라인 캐싱용 Service Worker
//
// [사용 조건] file://로 로컬에서 직접 연 HTML에서는 브라우저 보안 정책상
// Service Worker가 등록되지 않습니다. GitHub Pages 같은 http(s) 서버에
// danang_guide.html과 이 sw.js를 "같은 폴더"에 올려서 접속해야 동작합니다.
//
// [동작 방식]
// 1) 최초 1회는 반드시 온라인 상태로 접속해서 화면을 한 번 띄워야 합니다.
//    이때 지도에 보인 타일과 CDN 리소스(Tailwind/Leaflet/FontAwesome/폰트)가
//    자동으로 캐시에 저장됩니다.
// 2) 이후 오프라인 상태여도, "이미 한 번 화면에 표시됐던 지역의 지도"와
//    기본 UI는 계속 보입니다. 한 번도 안 본 지역으로 이동하면 빈 타일이
//    나올 수 있습니다 (이건 구조적 한계이며, 여행 전 미리 각 탭/구역을
//    한 번씩 눌러서 둘러봐두면 캐시가 채워집니다).
// 3) Nominatim 주소 검색은 오프라인에서는 동작하지 않습니다(실시간 API이므로).

const CACHE_VERSION = 'v1';
const STATIC_CACHE = `danang-guide-static-${CACHE_VERSION}`;
const TILE_CACHE = `danang-guide-tiles-${CACHE_VERSION}`;
const MAX_TILE_CACHE_ITEMS = 400; // 타일 캐시 용량 제한(오래된 것부터 정리)

// 최초 설치 시 미리 캐싱해둘 핵심 정적 리소스
const PRECACHE_URLS = [
    'https://cdn.tailwindcss.com',
    'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css',
    'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
    'https://cdnjs.cloudflare.com/ajax/libs/pretendard/1.3.9/static/pretendard.min.css'
];

self.addEventListener('install', (event) => {
    self.skipWaiting();
    event.waitUntil(
        caches.open(STATIC_CACHE).then(async (cache) => {
            // 리소스 하나가 실패해도 전체 설치가 실패하지 않도록 개별 처리
            await Promise.all(
                PRECACHE_URLS.map((url) =>
                    cache.add(url).catch((err) => {
                        console.warn('[SW] 사전 캐싱 실패:', url, err);
                    })
                )
            );
        })
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(
                keys
                    .filter((key) => key !== STATIC_CACHE && key !== TILE_CACHE)
                    .map((key) => caches.delete(key))
            )
        )
    );
    self.clients.claim();
});

function isMapTileRequest(url) {
    return url.includes('tile.openstreetmap.org');
}

function isStaticAssetRequest(url) {
    return (
        url.includes('cdn.tailwindcss.com') ||
        url.includes('cdnjs.cloudflare.com') ||
        url.includes('fonts.googleapis.com') ||
        url.includes('fonts.gstatic.com')
    );
}

// 캐시 항목 수가 너무 늘어나지 않도록 오래된 것부터 정리
async function trimCache(cacheName, maxItems) {
    const cache = await caches.open(cacheName);
    const keys = await cache.keys();
    if (keys.length > maxItems) {
        const removeCount = keys.length - maxItems;
        for (let i = 0; i < removeCount; i++) {
            await cache.delete(keys[i]);
        }
    }
}

// Cache-first, network fallback (오프라인 대비 - 지도 타일/정적 리소스 전용)
async function cacheFirst(request, cacheName) {
    const cache = await caches.open(cacheName);
    const cached = await cache.match(request);
    if (cached) {
        return cached;
    }
    try {
        const response = await fetch(request);
        if (response && response.status === 200) {
            cache.put(request, response.clone());
            if (cacheName === TILE_CACHE) {
                trimCache(TILE_CACHE, MAX_TILE_CACHE_ITEMS);
            }
        }
        return response;
    } catch (err) {
        // 네트워크도 없고 캐시에도 없으면 실패 그대로 전달
        throw err;
    }
}

self.addEventListener('fetch', (event) => {
    const url = event.request.url;

    // Nominatim 검색 등 실시간 API 요청은 캐싱하지 않고 네트워크로 그대로 통과
    if (isMapTileRequest(url)) {
        event.respondWith(cacheFirst(event.request, TILE_CACHE));
        return;
    }
    if (isStaticAssetRequest(url)) {
        event.respondWith(cacheFirst(event.request, STATIC_CACHE));
        return;
    }
    // 그 외 요청(HTML 본문, Nominatim API 등)은 브라우저 기본 동작에 맡김
});
