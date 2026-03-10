/**
 * main.js — 5탭 대시보드 진입점
 * 각 탭의 이벤트를 바인딩하고 모듈을 연결
 */
(function () {
  'use strict';

  var GOOGLE_API_KEY = (window.CONFIG || {}).GOOGLE_API_KEY || '';
  var GOOGLE_CLIENT_ID = (window.CONFIG || {}).GOOGLE_CLIENT_ID || '';

  // 상태
  var _parsedTools = [];
  var _blogResults = [];
  var _sheetToolDB = [];
  var _sheetBlogContents = [];

  // 탭4: 이미지 삽입 상태
  var _selectedBlogIndex = -1;
  var _imageTags = [];           // [{tag, description}]
  var _imageFiles = {};          // { index: File }
  var _uploadedImageUrls = {};   // { index: url }

  // ─── 초기화 ───

  async function init() {
    UI.initTabs();
    UI.initStatusToggle();
    UI.initScheduleToggle();
    UI.clearPreview();
    UI.updateAuthUI(false);

    // 백엔드 헬스체크
    var alive = await API.checkBackend();
    UI.updateBackendDot(alive);
    UI.showStatus(
      alive ? '백엔드 연결됨 (localhost:8000)' : '백엔드 오프라인 — 목업 모드로 동작',
      alive ? 'success' : 'info'
    );

    // Google API
    if (GOOGLE_API_KEY && GOOGLE_CLIENT_ID) {
      UI.showStatus('Google API 초기화 중...', 'loading');
      try {
        await Sheets.initSheetsAPI(GOOGLE_API_KEY, GOOGLE_CLIENT_ID, function (isSignedIn) {
          UI.updateAuthUI(isSignedIn);
          if (isSignedIn) {
            UI.showStatus('Google 로그인 완료 — 시트 데이터 불러오는 중...', 'loading');
            _loadSheetData();
          } else {
            UI.showStatus('로그아웃', 'info');
            _sheetToolDB = [];
            _sheetBlogContents = [];
          }
        });
        UI.showStatus('Google Sheets API 준비 완료', 'success');
      } catch (err) {
        UI.showStatus('Google API 초기화 실패: ' + err.message, 'error');
        console.error('Google API 초기화 오류:', err);
      }
    } else {
      UI.showStatus('Google API 키가 config.js에 설정되지 않았습니다.', 'error');
    }

    // 티스토리 카테고리 로드
    _loadCategories();

    _bindAll();
    UI.showStatus('앱 준비 완료', 'success');
  }

  /** 로그인 후 시트 데이터 자동 불러오기 */
  async function _loadSheetData() {
    try {
      // 툴 DB 불러오기
      _sheetToolDB = await Sheets.getToolDB();
      UI.showStatus('툴 DB 로드 완료: ' + _sheetToolDB.length + '개 툴', 'success');

      // 블로그 콘텐츠 불러오기
      _sheetBlogContents = await Sheets.getBlogContents();
      UI.showStatus('블로그 콘텐츠 로드 완료: ' + _sheetBlogContents.length + '개 글', 'success');

      // 탭2에 시트 상태 표시
      UI.showSheetsResult(
        '📦 툴 DB: ' + _sheetToolDB.length + '개 | 📝 블로그: ' + _sheetBlogContents.length + '개',
        false
      );

      // 이미 생성된 블로그가 있으면 _blogResults에도 반영
      if (_sheetBlogContents.length > 0 && _blogResults.length === 0) {
        _blogResults = _sheetBlogContents.map(function (b) {
          return {
            tool: b.toolName,
            name: b.toolName,
            type: b.blogType || 'B',
            title: b.title,
            content: b.content,
            charCount: (b.content || '').length,
            status: 'success',
            blogStatus: b.uploadStatus || '글완성',
            uploadStatus: b.uploadStatus,
          };
        });
        UI.showBlogResults(_blogResults);
        UI.populateBlogSelect(_blogResults);
      }

      // 업로드 탭 체크리스트 반영
      if (_blogResults.length > 0) {
        UI.showUploadChecklist(_blogResults);
      }

    } catch (err) {
      UI.showStatus('시트 데이터 로드 실패: ' + err.message, 'error');
      console.error('시트 데이터 로드 오류:', err);
    }
  }

  async function _loadCategories() {
    try {
      var data = await API.getTistoryCategories();
      UI.loadTistoryCategories(data.categories);
    } catch (e) {
      console.warn('카테고리 로드 실패:', e);
    }
  }

  // ─── 이벤트 바인딩 ───

  function _bindAll() {
    // 탭 1: 데이터 입력
    _on('btn-parse', 'click', _handleParse);

    // 탭 2: Sheets — 로그인
    _on('btn-sign-in', 'click', async function () {
      if (!Sheets.isReady()) {
        UI.showStatus('Google API 초기화 중... 잠시 기다려 주세요.', 'loading');
        // 최대 10초 대기
        for (var i = 0; i < 50; i++) {
          await new Promise(function (r) { setTimeout(r, 200); });
          if (Sheets.isReady()) break;
        }
        if (!Sheets.isReady()) {
          UI.showStatus('Google API 초기화에 실패했습니다. 페이지를 새로고침하세요.', 'error');
          return;
        }
      }
      try { Sheets.signIn(); } catch (e) { UI.showStatus(e.message, 'error'); }
    });
    _on('btn-sign-out', 'click', function () { Sheets.signOut(); });
    _on('btn-save-sheets', 'click', _handleSaveSheets);

    // 탭 3: 블로그
    _on('btn-generate-blog', 'click', _handleGenerateBlog);

    // 탭 4: 이미지 삽입
    _on('image-blog-select', 'change', _handleBlogSelect);
    _on('btn-apply-images', 'click', _handleApplyImages);

    // 탭 5: 업로드
    _on('publish-mode', 'change', function () {
      var opts = document.getElementById('schedule-options');
      if (opts) opts.hidden = this.value !== 'schedule';
    });
    _on('btn-upload', 'click', _handleUpload);
    _on('btn-select-all', 'click', function () {
      document.querySelectorAll('.upload-check:not(:disabled)').forEach(function (c) { c.checked = true; });
    });
    _on('btn-deselect-all', 'click', function () {
      document.querySelectorAll('.upload-check:not(:disabled)').forEach(function (c) { c.checked = false; });
    });
  }

  function _on(id, evt, fn) {
    var el = document.getElementById(id);
    if (el) el.addEventListener(evt, fn);
  }

  // ─── 탭 1: 파싱 ───

  function _handleParse() {
    var text = UI.getTextareaValue();
    if (!text.trim()) {
      UI.showStatus('텍스트를 먼저 붙여넣으세요.', 'error');
      return;
    }

    UI.showStatus('데이터 파싱 중...', 'loading');
    var result = Parser.parseRawText(text);

    if (result.error) {
      UI.showStatus('파싱 오류: ' + result.error, 'error');
      UI.clearPreview();
      _parsedTools = [];
      return;
    }

    _parsedTools = result.tools;
    UI.showParsedPreview(_parsedTools);
    UI.showStatus('파싱 완료: ' + _parsedTools.length + '개 툴', 'success');
  }

  // ─── 탭 2: Sheets 저장 ───

  async function _handleSaveSheets() {
    if (_parsedTools.length === 0) {
      UI.showStatus('탭1에서 먼저 데이터를 파싱하세요.', 'error');
      return;
    }

    var saveLog = document.getElementById('chk-weekly-log').checked;
    var updateDB = document.getElementById('chk-tool-db').checked;

    if (!saveLog && !updateDB) {
      UI.showStatus('저장 옵션을 하나 이상 선택하세요.', 'error');
      return;
    }

    var btn = document.getElementById('btn-save-sheets');
    btn.disabled = true;
    var messages = [];

    try {
      if (saveLog) {
        UI.showStatus('주간 로그 저장 중...', 'loading');
        var count = await Sheets.appendToWeeklyLog(_parsedTools);
        messages.push('주간 로그: ' + count + '행 추가');
        UI.showStatus('주간 로그 저장 완료: ' + count + '행', 'success');
      }

      if (updateDB) {
        UI.showStatus('툴 DB 업데이트 중...', 'loading');
        var result = await Sheets.updateToolDB(_parsedTools);
        messages.push('툴 DB: 신규 ' + result.added + '개, 갱신 ' + result.updated + '개');
        UI.showStatus('툴 DB 업데이트 완료', 'success');
      }

      UI.showSheetsResult(messages.join(' | '), false);
    } catch (err) {
      UI.showSheetsResult('저장 실패: ' + err.message, true);
      UI.showStatus('Sheets 저장 실패: ' + err.message, 'error');
    } finally {
      btn.disabled = false;
    }
  }

  // ─── 탭 3: 블로그 생성 ───

  async function _handleGenerateBlog() {
    var target = document.getElementById('blog-target').value;
    var type = document.getElementById('blog-type').value;
    var limit = parseInt(document.getElementById('blog-limit').value) || 3;

    var tools = [];

    if (target === 'parsed') {
      tools = _parsedTools;
      if (tools.length === 0) {
        UI.showStatus('탭1에서 먼저 데이터를 파싱하세요.', 'error');
        return;
      }
    } else {
      // 시트에서 타겟(✅) + 미작성/글완성 툴 가져오기
      if (_sheetToolDB.length > 0) {
        tools = _sheetToolDB.filter(function (t) {
          return t.target === '✅' && (!t.blogStatus || t.blogStatus === '미작성' || t.blogStatus === '글완성');
        });
      }
      if (tools.length === 0) {
        // 폴백: API로 시도
        UI.showStatus('시트에서 타겟 툴 불러오는 중...', 'loading');
        try {
          var data = await API.getTargetTools();
          tools = data.tools || [];
        } catch (e) {
          UI.showStatus('타겟 툴 로드 실패: ' + e.message, 'error');
          return;
        }
      }
      if (tools.length === 0) {
        UI.showStatus('생성할 타겟(✅) 툴이 없습니다.', 'error');
        return;
      }

      // 미작성/글완성 개수 표시
      var unwritten = tools.filter(function (t) { return !t.blogStatus || t.blogStatus === '미작성'; }).length;
      var written = tools.filter(function (t) { return t.blogStatus === '글완성'; }).length;
      UI.showStatus(tools.length + '개 타겟 툴 로드 (미작성: ' + unwritten + ', 글완성: ' + written + ')', 'success');
    }

    var btn = document.getElementById('btn-generate-blog');
    btn.disabled = true;
    UI.showProgress('blog', 10, '블로그 생성 중...');
    UI.showStatus('블로그 생성 시작 (' + Math.min(limit, tools.length) + '개)', 'loading');

    try {
      var options = {
        tools: tools.slice(0, limit),
        type: type === 'auto' ? undefined : type,
        limit: limit,
      };

      UI.showProgress('blog', 50, 'Claude API 호출 중...');
      var result = await API.generateBlog(options);
      _blogResults = result.results || [];

      UI.showProgress('blog', 100, '완료!');
      UI.showBlogResults(_blogResults);
      UI.populateBlogSelect(_blogResults);
      UI.showUploadChecklist(_blogResults);
      UI.showStatus('블로그 생성 완료: ' + _blogResults.length + '개', 'success');

      setTimeout(function () { UI.hideProgress('blog'); }, 1500);
    } catch (err) {
      UI.showStatus('블로그 생성 실패: ' + err.message, 'error');
      UI.hideProgress('blog');
    } finally {
      btn.disabled = false;
    }
  }

  // ─── 탭 4: 이미지 삽입 ───

  /** 블로그 글 선택 시 이미지 태그 파싱 → 드롭존 표시 */
  function _handleBlogSelect() {
    var sel = document.getElementById('image-blog-select');
    var idx = parseInt(sel.value);
    _selectedBlogIndex = -1;
    _imageTags = [];
    _imageFiles = {};
    _uploadedImageUrls = {};

    if (isNaN(idx) || !_blogResults[idx]) {
      UI.showImageSlots([]);
      UI.setApplyButtonEnabled(false);
      return;
    }

    _selectedBlogIndex = idx;
    var blog = _blogResults[idx];
    _imageTags = UI.parseImageTags(blog.content || '');

    if (_imageTags.length === 0) {
      UI.showStatus('이 글에 [이미지: 설명] 태그가 없습니다.', 'info');
    } else {
      UI.showStatus(_imageTags.length + '개 이미지 태그 발견', 'success');
    }

    UI.showImageSlots(_imageTags, _onImageFileAdded, _onImageFileRemoved);
    _updateApplyButton();
  }

  /** 드롭존에 파일 추가 콜백 */
  function _onImageFileAdded(index, file) {
    _imageFiles[index] = file;
    UI.showStatus('슬롯 ' + (index + 1) + ': ' + file.name + ' 추가', 'success');
    _updateApplyButton();
  }

  /** 드롭존에서 파일 제거 콜백 */
  function _onImageFileRemoved(index) {
    delete _imageFiles[index];
    delete _uploadedImageUrls[index];
    UI.showStatus('슬롯 ' + (index + 1) + ' 이미지 제거', 'info');
    _updateApplyButton();
  }

  /** 하나 이상의 이미지가 추가되면 적용 버튼 활성화 */
  function _updateApplyButton() {
    var hasAny = Object.keys(_imageFiles).length > 0;
    UI.setApplyButtonEnabled(hasAny);
  }

  /** 이미지 적용: 업로드 → [이미지: 설명] → <img> 교체 */
  async function _handleApplyImages() {
    if (_selectedBlogIndex < 0 || !_blogResults[_selectedBlogIndex]) {
      UI.showStatus('글을 먼저 선택하세요.', 'error');
      return;
    }

    var fileKeys = Object.keys(_imageFiles);
    if (fileKeys.length === 0) {
      UI.showStatus('이미지를 하나 이상 추가하세요.', 'error');
      return;
    }

    var btn = document.getElementById('btn-apply-images');
    btn.disabled = true;
    UI.showProgress('image', 0, '이미지 업로드 중...');

    try {
      // 1) 각 이미지 업로드
      var total = fileKeys.length;
      for (var i = 0; i < total; i++) {
        var key = parseInt(fileKeys[i]);
        var file = _imageFiles[key];
        var pct = Math.round(((i + 1) / total) * 60);
        UI.showProgress('image', pct, '업로드 중 (' + (i + 1) + '/' + total + '): ' + file.name);

        var uploaded = await API.uploadImage(file);
        _uploadedImageUrls[key] = uploaded.url;
        UI.showStatus('슬롯 ' + (key + 1) + ' 업로드 완료: ' + (uploaded.filename || file.name), 'success');
      }

      // 2) 태그 → <img> 교체
      UI.showProgress('image', 80, '태그를 이미지로 교체 중...');

      var blog = _blogResults[_selectedBlogIndex];
      var imageMap = [];
      for (var k in _uploadedImageUrls) {
        var idx = parseInt(k);
        if (_imageTags[idx]) {
          imageMap.push({
            tag: _imageTags[idx].tag,
            description: _imageTags[idx].description,
            url: _uploadedImageUrls[idx],
          });
        }
      }

      var result = await API.applyImages({
        toolName: blog.tool,
        content: blog.content,
        images: imageMap,
      });

      // 3) 결과 반영
      _blogResults[_selectedBlogIndex].content = result.content;
      UI.showProgress('image', 100, '완료!');
      UI.showImageResult(
        result.replacedCount + '개 이미지 태그 교체 완료 → 탭5에서 업로드하세요',
        false
      );
      UI.showStatus('이미지 적용 완료: ' + result.replacedCount + '개 교체', 'success');

      setTimeout(function () { UI.hideProgress('image'); }, 1500);

    } catch (err) {
      UI.showStatus('이미지 적용 실패: ' + err.message, 'error');
      UI.showImageResult('이미지 적용 실패: ' + err.message, true);
      UI.hideProgress('image');
    } finally {
      btn.disabled = false;
    }
  }

  // ─── 탭 5: 티스토리 업로드 ───

  async function _handleUpload() {
    if (_blogResults.length === 0) {
      UI.showStatus('탭3에서 먼저 블로그를 생성하세요.', 'error');
      return;
    }

    // 선택된 글만 업로드
    var selectedIndices = UI.getSelectedUploadIndices();
    if (selectedIndices.length === 0) {
      UI.showStatus('업로드할 글을 하나 이상 선택하세요.', 'error');
      return;
    }

    var selectedPosts = selectedIndices.map(function (i) { return _blogResults[i]; }).filter(Boolean);

    var mode = document.getElementById('publish-mode').value;
    var category = document.getElementById('tistory-category').value;

    var uploadOpts = {
      posts: selectedPosts.map(function (r) {
        return { title: r.title, content: r.content, type: r.type };
      }),
      mode: mode,
      category: category,
    };

    // 예약 옵션
    if (mode === 'schedule') {
      uploadOpts.startDate = document.getElementById('schedule-date').value;
      uploadOpts.startTime = document.getElementById('schedule-time').value;
      uploadOpts.interval = parseInt(document.getElementById('schedule-interval').value) || 0;

      if (!uploadOpts.startDate) {
        UI.showStatus('예약 날짜를 입력하세요.', 'error');
        return;
      }
    }

    var btn = document.getElementById('btn-upload');
    btn.disabled = true;
    UI.showProgress('upload', 20, '업로드 준비 중...');
    UI.showStatus('티스토리 업로드 시작 (' + selectedPosts.length + '개, ' + mode + ')', 'loading');

    // 업로드 전 목록 표시 (대기 상태)
    UI.showUploadList(selectedPosts.map(function (r) {
      return { title: r.title, status: 'wait' };
    }));

    try {
      UI.showProgress('upload', 60, '업로드 중...');
      var result = await API.uploadToTistory(uploadOpts);
      var uploads = result.results || [];

      UI.showProgress('upload', 100, '완료!');
      UI.showUploadList(uploads);

      var successCount = uploads.filter(function (u) { return u.status === 'success'; }).length;
      UI.showStatus('업로드 완료: ' + successCount + '/' + uploads.length + '개 성공', 'success');

      setTimeout(function () { UI.hideProgress('upload'); }, 1500);
    } catch (err) {
      UI.showStatus('업로드 실패: ' + err.message, 'error');
      UI.hideProgress('upload');
    } finally {
      btn.disabled = false;
    }
  }

  // ─── 시작 ───

  document.addEventListener('DOMContentLoaded', init);
})();
