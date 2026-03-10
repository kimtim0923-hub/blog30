/**
 * api.js — 백엔드 API 클라이언트
 * 백엔드(localhost:8000)가 없으면 목업 데이터로 폴백
 */
(function () {
  'use strict';

  var BASE = 'http://localhost:8000';
  var _backendAlive = false;

  /** 백엔드 헬스체크 */
  async function checkBackend() {
    try {
      var res = await fetch(BASE + '/health', { method: 'GET', signal: AbortSignal.timeout(2000) });
      _backendAlive = res.ok;
    } catch (e) {
      _backendAlive = false;
    }
    return _backendAlive;
  }

  /** 공통 fetch 래퍼 */
  async function _post(path, body) {
    var res = await fetch(BASE + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      var err = await res.text();
      throw new Error(err || 'API 오류 ' + res.status);
    }
    return res.json();
  }

  async function _get(path) {
    var res = await fetch(BASE + path);
    if (!res.ok) throw new Error('API 오류 ' + res.status);
    return res.json();
  }

  // ─── 블로그 생성 ───

  /** 블로그 생성 요청 */
  async function generateBlog(options) {
    if (_backendAlive) {
      return _post('/api/blog/generate', options);
    }
    // 목업
    return _mockGenerateBlog(options);
  }

  function _mockGenerateBlog(options) {
    var limit = options.limit || 3;
    var tools = options.tools || [];
    var results = [];

    for (var i = 0; i < Math.min(limit, tools.length || limit); i++) {
      var name = (tools[i] && tools[i].name) || '샘플 AI 툴 ' + (i + 1);
      results.push({
        tool: name,
        type: options.type || 'B',
        title: name + ' 리뷰: AI 크리에이터를 위한 필수 도구 (2026)',
        content: '> 이 글에는 제휴 링크가 포함되어 있습니다.\n\n'
          + '# ' + name + ' 리뷰\n\n'
          + '## ' + name + '이란?\n'
          + name + '은(는) 크리에이터를 위한 AI 도구입니다.\n\n'
          + '## 핵심 기능 3가지\n'
          + '### 1. 자동 생성\n빠르고 정확한 콘텐츠 생성.\n\n'
          + '### 2. 한국어 지원\n자연스러운 한국어 출력.\n\n'
          + '### 3. 합리적 가격\n무료 플랜 제공.\n\n'
          + '## 가격 및 플랜\n| 플랜 | 월 비용 | 추천 |\n|---|---|---|\n'
          + '| Free | $0 | 입문자 |\n| Pro | $19/월 (≈₩25,000) | 전문가 |\n\n'
          + '## 최종 결론\n추천합니다.\n\n'
          + '[CTA 버튼] "' + name + ' 무료로 시작하기 →"',
        charCount: 850,
        status: 'success',
      });
    }

    return new Promise(function (resolve) {
      setTimeout(function () { resolve({ results: results }); }, 1500);
    });
  }

  // ─── 이미지 업로드 ───

  /**
   * 단일 이미지 파일 업로드
   * @param {File} file - 이미지 파일
   * @returns {{ url: string, filename: string }}
   */
  async function uploadImage(file) {
    if (_backendAlive) {
      var formData = new FormData();
      formData.append('image', file);
      var res = await fetch(BASE + '/api/upload/image', {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) throw new Error('이미지 업로드 실패: ' + res.status);
      return res.json();
    }
    // 목업: 로컬 URL 생성
    return new Promise(function (resolve) {
      var reader = new FileReader();
      reader.onload = function () {
        resolve({ url: reader.result, filename: file.name });
      };
      reader.readAsDataURL(file);
    });
  }

  /**
   * 블로그 글의 [이미지: 설명] 태그를 <img> 로 교체
   * @param {{ toolName: string, content: string, images: Array<{tag: string, url: string}> }}
   * @returns {{ content: string, replacedCount: number }}
   */
  async function applyImages(options) {
    if (_backendAlive) {
      return _post('/api/blog/apply-images', options);
    }
    // 목업: 로컬에서 직접 교체
    var content = options.content || '';
    var count = 0;
    (options.images || []).forEach(function (img) {
      if (img.url && img.tag) {
        var escaped = img.tag.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        var regex = new RegExp(escaped, 'g');
        var replacement = '<img src="' + img.url + '" alt="' + _escAttr(img.description || img.tag) + '" style="max-width:100%;border-radius:8px;margin:16px 0;">';
        if (regex.test(content)) {
          content = content.replace(regex, replacement);
          count++;
        }
      }
    });
    return { content: content, replacedCount: count };
  }

  function _escAttr(s) {
    return (s || '').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  // ─── 티스토리 업로드 ───

  async function uploadToTistory(options) {
    if (_backendAlive) {
      return _post('/api/tistory/upload', options);
    }
    return _mockUpload(options);
  }

  function _mockUpload(options) {
    var posts = options.posts || [];
    var results = posts.map(function (p, i) {
      var scheduled = '';
      if (options.mode === 'schedule' && options.startDate) {
        var d = new Date(options.startDate + 'T' + (options.startTime || '09:00'));
        d.setMinutes(d.getMinutes() + (options.interval || 0) * i);
        scheduled = d.toLocaleString('ko-KR');
      }
      return {
        title: p.title || '제목 없음',
        status: 'success',
        mode: options.mode || 'draft',
        scheduledAt: scheduled,
        url: '#mock-' + (i + 1),
      };
    });
    return new Promise(function (resolve) {
      setTimeout(function () { resolve({ results: results }); }, 1200);
    });
  }

  // ─── 시트에서 데이터 가져오기 ───

  async function getTargetTools() {
    if (_backendAlive) {
      return _get('/api/sheets/target-tools');
    }
    // 목업
    return {
      tools: [
        { name: 'MockTool A', tagline: 'AI video generator', category: 'Video', price: 'Freemium', saves: '1.2K' },
        { name: 'MockTool B', tagline: 'AI writing assistant', category: 'Writing', price: '$12/mo', saves: '890' },
        { name: 'MockTool C', tagline: 'AI image editor', category: 'Image', price: 'Free', saves: '2.5K' },
      ],
    };
  }

  async function getTistoryCategories() {
    if (_backendAlive) {
      return _get('/api/tistory/categories');
    }
    return {
      categories: [
        { id: '1', name: 'AI 툴 리뷰' },
        { id: '2', name: 'AI 비교' },
        { id: '3', name: 'AI 뉴스' },
      ],
    };
  }

  window.API = {
    checkBackend: checkBackend,
    isBackendAlive: function () { return _backendAlive; },
    generateBlog: generateBlog,
    uploadImage: uploadImage,
    applyImages: applyImages,
    uploadToTistory: uploadToTistory,
    getTargetTools: getTargetTools,
    getTistoryCategories: getTistoryCategories,
  };
})();
