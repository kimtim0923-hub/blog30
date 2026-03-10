/**
 * ui.js — 탭 대시보드 UI 모듈
 * 탭 전환, 테이블 렌더링, 상태 표시, 진행률 등
 */
(function () {
  'use strict';

  var $ = function (sel) { return document.querySelector(sel); };
  var $$ = function (sel) { return document.querySelectorAll(sel); };
  var _logCount = 0;

  // ─── 탭 전환 ───

  function initTabs() {
    $$('.tab-nav__btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        switchTab(btn.dataset.tab);
      });
    });
  }

  function switchTab(tabId) {
    // 탭 버튼
    $$('.tab-nav__btn').forEach(function (btn) {
      btn.classList.toggle('active', btn.dataset.tab === tabId);
    });
    // 탭 패널
    $$('.tab-panel').forEach(function (panel) {
      panel.classList.toggle('active', panel.id === 'tab-' + tabId);
    });
  }

  // ─── 상태 로그 ───

  function showStatus(message, type) {
    type = type || 'info';
    var log = $('#status-log');
    var time = new Date().toLocaleTimeString('ko-KR');
    var item = document.createElement('div');
    item.className = 'status-log__item status-log__item--' + type;
    item.textContent = '[' + time + '] ' + message;
    log.prepend(item);

    _logCount++;
    var badge = $('#log-badge');
    if (badge) badge.textContent = _logCount;

    while (log.children.length > 100) {
      log.removeChild(log.lastChild);
    }
  }

  function initStatusToggle() {
    var toggle = $('#status-toggle');
    var log = $('#status-log');
    if (toggle && log) {
      toggle.addEventListener('click', function () {
        log.classList.toggle('open');
      });
    }
  }

  // ─── 파싱 결과 테이블 (탭1) ───

  function showParsedPreview(tools) {
    var area = $('#preview-area');
    var countBadge = $('#parse-count');

    if (!tools || tools.length === 0) {
      area.innerHTML = '<div class="preview--empty">파싱된 결과가 없습니다</div>';
      if (countBadge) countBadge.hidden = true;
      return;
    }

    if (countBadge) {
      countBadge.textContent = tools.length + '개';
      countBadge.hidden = false;
    }

    var header =
      '<thead><tr>' +
      '<th>#</th><th>툴 이름</th><th>태그라인</th>' +
      '<th>카테고리</th><th>가격</th><th>저장수</th>' +
      '</tr></thead>';

    var rows = tools.map(function (t) {
      return '<tr>' +
        '<td>' + _esc(String(t.rank || '')) + '</td>' +
        '<td><strong>' + _esc(t.name) + '</strong></td>' +
        '<td>' + _esc(t.tagline) + '</td>' +
        '<td>' + _esc(t.category) + '</td>' +
        '<td>' + _esc(t.price) + '</td>' +
        '<td>' + _esc(t.saves) + '</td>' +
        '</tr>';
    }).join('');

    area.innerHTML = '<table class="table">' + header + '<tbody>' + rows + '</tbody></table>';
    area.classList.remove('preview--empty');
  }

  function clearPreview() {
    var area = $('#preview-area');
    area.innerHTML = '<div class="preview--empty">TAAFT 데이터를 붙여넣고 "파싱하기"를 클릭하세요</div>';
    area.classList.add('preview--empty');
    var countBadge = $('#parse-count');
    if (countBadge) countBadge.hidden = true;
  }

  // ─── 인증 UI ───

  function updateAuthUI(isSignedIn) {
    var btnIn = $('#btn-sign-in');
    var btnOut = $('#btn-sign-out');
    var dot = $('#sheets-dot');
    var title = $('#sheets-conn-title');
    var desc = $('#sheets-conn-desc');
    var saveBtn = $('#btn-save-sheets');

    if (isSignedIn) {
      if (btnIn) btnIn.hidden = true;
      if (btnOut) btnOut.hidden = false;
      if (dot) { dot.className = 'dot dot--on'; }
      if (title) title.textContent = '연결됨';
      if (desc) desc.textContent = '스프레드시트에 쓸 수 있습니다';
      if (saveBtn) saveBtn.disabled = false;
    } else {
      if (btnIn) btnIn.hidden = false;
      if (btnOut) btnOut.hidden = true;
      if (dot) { dot.className = 'dot dot--off'; }
      if (title) title.textContent = '연결 안 됨';
      if (desc) desc.textContent = 'Google 로그인 후 사용 가능';
      if (saveBtn) saveBtn.disabled = true;
    }
  }

  // ─── 백엔드 연결 상태 ───

  function updateBackendDot(alive) {
    var dot = $('#connection-dot');
    if (dot) {
      dot.className = alive ? 'dot dot--on' : 'dot dot--off';
      dot.title = alive ? '백엔드 연결됨' : '백엔드 오프라인 (목업 모드)';
    }
  }

  // ─── Sheets 결과 ───

  function showSheetsResult(message, isError) {
    var box = $('#sheets-result');
    if (!box) return;
    box.hidden = false;
    box.className = 'result-box ' + (isError ? 'result-box--error' : 'result-box--success');
    box.textContent = message;
  }

  // ─── 진행률 ───

  function showProgress(prefix, percent, text) {
    var bar = $('#' + prefix + '-bar');
    var txt = $('#' + prefix + '-progress-text');
    var box = $('#' + prefix + '-progress');
    if (box) box.hidden = false;
    if (bar) bar.style.width = percent + '%';
    if (txt) txt.textContent = text;
  }

  function hideProgress(prefix) {
    var box = $('#' + prefix + '-progress');
    if (box) box.hidden = true;
  }

  // ─── 블로그 리스트 (탭3) ───

  function showBlogResults(results) {
    var list = $('#blog-list');
    var badge = $('#blog-count');
    if (!list) return;

    if (!results || results.length === 0) {
      list.innerHTML = '<div class="preview--empty">생성된 글이 없습니다</div>';
      if (badge) badge.hidden = true;
      return;
    }

    if (badge) {
      badge.textContent = results.length + '개';
      badge.hidden = false;
    }

    list.innerHTML = results.map(function (r, i) {
      // 상태 뱃지: 미작성/글완성/업로드완료/실패 구분
      var badgeCls = 'badge--info';
      var badgeText = '미작성';
      if (r.blogStatus === '글완성' || r.uploadStatus === '글완성') {
        badgeCls = 'badge--success';
        badgeText = '글완성';
      } else if (r.blogStatus === '업로드완료' || r.uploadStatus === '업로드완료') {
        badgeCls = 'badge--done';
        badgeText = '업로드완료';
      } else if (r.status === 'success') {
        badgeCls = 'badge--success';
        badgeText = '완료';
      } else if (r.status === 'error' || r.blogStatus === '생성오류') {
        badgeCls = 'badge--danger';
        badgeText = '실패';
      }

      return '<div class="blog-item" data-index="' + i + '">'
        + '<div class="blog-item__title">' + _esc(r.title || r.tool || r.name || '') + '</div>'
        + '<div class="blog-item__meta">'
        + '<span>유형: ' + _esc(r.type || '-') + '</span>'
        + '<span>' + (r.charCount || 0) + '자</span>'
        + '<span class="badge badge--sm ' + badgeCls + '">' + badgeText + '</span>'
        + '</div></div>';
    }).join('');
  }

  // ─── 이미지 슬롯 (탭4 드래그&드롭) ───

  /** [이미지: 설명] 태그를 파싱하여 배열로 반환 */
  function parseImageTags(content) {
    var regex = /\[이미지:\s*([^\]]+)\]/g;
    var tags = [];
    var match;
    while ((match = regex.exec(content)) !== null) {
      tags.push({ tag: match[0], description: match[1].trim() });
    }
    return tags;
  }

  /**
   * 블로그 선택 드롭다운 업데이트
   * @param {Array} blogResults - [{tool, title, ...}]
   */
  function populateBlogSelect(blogResults) {
    var sel = $('#image-blog-select');
    if (!sel) return;
    sel.innerHTML = '<option value="">글을 선택하세요...</option>';
    (blogResults || []).forEach(function (r, i) {
      if (r.status !== 'success') return;
      var opt = document.createElement('option');
      opt.value = i;
      opt.textContent = (r.tool || '') + ' — ' + (r.title || '').substring(0, 50);
      sel.appendChild(opt);
    });
  }

  /**
   * 이미지 슬롯(드롭존) 렌더링
   * @param {Array} imageTags - [{tag, description}]
   * @param {function} onFileAdded - callback(index, file)
   * @param {function} onFileRemoved - callback(index)
   */
  function showImageSlots(imageTags, onFileAdded, onFileRemoved) {
    var container = $('#image-slots');
    var actions = $('#image-actions');
    if (!container) return;

    if (!imageTags || imageTags.length === 0) {
      container.innerHTML = '<div class="preview--empty">이 글에 [이미지: 설명] 태그가 없습니다</div>';
      if (actions) actions.hidden = true;
      return;
    }

    if (actions) actions.hidden = false;

    container.innerHTML = imageTags.map(function (t, i) {
      return '<div class="image-slot" data-index="' + i + '">'
        + '<div class="image-slot__num">' + (i + 1) + '</div>'
        + '<div class="image-slot__info">'
        + '<span class="image-slot__tag">' + _esc(t.tag) + '</span>'
        + '<span class="image-slot__desc">' + _esc(t.description) + '</span>'
        + '</div>'
        + '<div class="dropzone" data-index="' + i + '">'
        + '<input type="file" accept="image/*">'
        + '<span class="dropzone__icon">+</span>'
        + '<span class="dropzone__text">이미지를 드래그하거나<br>클릭해서 선택</span>'
        + '<button class="dropzone__remove" type="button" title="제거">✕</button>'
        + '</div>'
        + '</div>';
    }).join('');

    // 드롭존 이벤트 바인딩
    container.querySelectorAll('.dropzone').forEach(function (dz) {
      var idx = parseInt(dz.dataset.index);
      var fileInput = dz.querySelector('input[type="file"]');

      // 클릭 → 파일 선택
      dz.addEventListener('click', function (e) {
        if (e.target.classList.contains('dropzone__remove')) return;
        fileInput.click();
      });

      fileInput.addEventListener('change', function () {
        if (fileInput.files[0]) _handleDropFile(dz, idx, fileInput.files[0], onFileAdded);
      });

      // 드래그 앤 드롭
      dz.addEventListener('dragover', function (e) {
        e.preventDefault();
        dz.classList.add('drag-over');
      });
      dz.addEventListener('dragleave', function () {
        dz.classList.remove('drag-over');
      });
      dz.addEventListener('drop', function (e) {
        e.preventDefault();
        dz.classList.remove('drag-over');
        var file = e.dataTransfer.files[0];
        if (file && file.type.startsWith('image/')) {
          _handleDropFile(dz, idx, file, onFileAdded);
        }
      });

      // 제거 버튼
      dz.querySelector('.dropzone__remove').addEventListener('click', function (e) {
        e.stopPropagation();
        _clearDropzone(dz);
        if (onFileRemoved) onFileRemoved(idx);
      });
    });
  }

  function _handleDropFile(dz, index, file, callback) {
    var reader = new FileReader();
    reader.onload = function () {
      dz.classList.add('has-image');
      // 기존 내용 숨기고 이미지 표시
      var icon = dz.querySelector('.dropzone__icon');
      var text = dz.querySelector('.dropzone__text');
      if (icon) icon.style.display = 'none';
      if (text) text.style.display = 'none';

      // 기존 img 제거
      var oldImg = dz.querySelector('img');
      if (oldImg) oldImg.remove();

      var img = document.createElement('img');
      img.src = reader.result;
      img.alt = file.name;
      dz.insertBefore(img, dz.firstChild);

      if (callback) callback(index, file);
    };
    reader.readAsDataURL(file);
  }

  function _clearDropzone(dz) {
    dz.classList.remove('has-image');
    var img = dz.querySelector('img');
    if (img) img.remove();
    var icon = dz.querySelector('.dropzone__icon');
    var text = dz.querySelector('.dropzone__text');
    if (icon) icon.style.display = '';
    if (text) text.style.display = '';
    var input = dz.querySelector('input[type="file"]');
    if (input) input.value = '';
  }

  /** 이미지 적용 결과 표시 */
  function showImageResult(message, isError) {
    var box = $('#image-result');
    if (!box) return;
    box.hidden = false;
    box.className = 'result-box ' + (isError ? 'result-box--error' : 'result-box--success');
    box.textContent = message;
  }

  /** 적용 버튼 활성/비활성 */
  function setApplyButtonEnabled(enabled) {
    var btn = $('#btn-apply-images');
    if (btn) btn.disabled = !enabled;
  }

  // ─── 업로드 체크리스트 (탭5 — 글 선택) ───

  function showUploadChecklist(posts) {
    var container = $('#upload-checklist');
    if (!container) return;

    if (!posts || posts.length === 0) {
      container.innerHTML = '<div class="preview--empty">업로드할 글이 없습니다</div>';
      return;
    }

    container.innerHTML = posts.map(function (p, i) {
      var checked = p.uploadStatus !== '업로드완료' ? ' checked' : '';
      var disabled = p.uploadStatus === '업로드완료' ? ' disabled' : '';
      var statusBadge = '';
      if (p.uploadStatus === '업로드완료') {
        statusBadge = '<span class="badge badge--sm badge--done">업로드완료</span>';
      } else if (p.blogStatus === '글완성' || p.uploadStatus === '글완성') {
        statusBadge = '<span class="badge badge--sm badge--success">글완성</span>';
      }
      return '<label class="check-card"' + disabled + '>'
        + '<input type="checkbox" class="upload-check" data-index="' + i + '"' + checked + disabled + '>'
        + '<span>' + _esc(p.title || p.tool || '') + '</span>'
        + statusBadge
        + '</label>';
    }).join('');
  }

  function getSelectedUploadIndices() {
    var checks = $$('.upload-check:checked:not(:disabled)');
    var indices = [];
    checks.forEach(function (chk) {
      indices.push(parseInt(chk.dataset.index));
    });
    return indices;
  }

  // ─── 업로드 리스트 (탭5 — 결과) ───

  function showUploadList(posts) {
    var list = $('#upload-list');
    var badge = $('#upload-count');
    if (!list) return;

    if (!posts || posts.length === 0) {
      list.innerHTML = '<div class="preview--empty">업로드할 글이 없습니다</div>';
      if (badge) badge.hidden = true;
      return;
    }

    if (badge) {
      badge.textContent = posts.length + '개';
      badge.hidden = false;
    }

    list.innerHTML = posts.map(function (p) {
      var statusCls = p.status === 'success' ? '--done' : p.status === 'error' ? '--fail' : '--wait';
      var statusText = p.status === 'success' ? '완료' : p.status === 'error' ? '실패' : '대기';
      return '<div class="upload-item">'
        + '<div class="upload-item__left">'
        + '<span class="upload-item__status upload-item__status' + statusCls + '">' + statusText + '</span>'
        + '<span>' + _esc(p.title) + '</span>'
        + '</div>'
        + (p.scheduledAt ? '<span class="upload-item__schedule">' + _esc(p.scheduledAt) + '</span>' : '')
        + '</div>';
    }).join('');
  }

  // ─── 예약 옵션 토글 ───

  function initScheduleToggle() {
    var modeSelect = $('#publish-mode');
    var options = $('#schedule-options');
    if (modeSelect && options) {
      modeSelect.addEventListener('change', function () {
        options.hidden = modeSelect.value !== 'schedule';
      });
      // 기본 날짜 = 내일
      var dateInput = $('#schedule-date');
      if (dateInput) {
        var tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        dateInput.value = tomorrow.toISOString().split('T')[0];
      }
    }
  }

  // ─── 티스토리 카테고리 로드 ───

  function loadTistoryCategories(categories) {
    var select = $('#tistory-category');
    if (!select || !categories) return;
    select.innerHTML = '<option value="">선택...</option>';
    categories.forEach(function (c) {
      var opt = document.createElement('option');
      opt.value = c.id;
      opt.textContent = c.name;
      select.appendChild(opt);
    });
  }

  // ─── 유틸 ───

  function getTextareaValue() {
    return ($('#raw-input') || {}).value || '';
  }

  function _esc(str) {
    var div = document.createElement('div');
    div.textContent = str || '';
    return div.innerHTML;
  }

  function setButtonsEnabled(enabled) {
    $$('.btn--primary, .btn--success').forEach(function (btn) {
      btn.disabled = !enabled;
    });
  }

  // ─── 공개 API ───

  window.UI = {
    initTabs: initTabs,
    switchTab: switchTab,
    initStatusToggle: initStatusToggle,
    initScheduleToggle: initScheduleToggle,
    showStatus: showStatus,
    showParsedPreview: showParsedPreview,
    clearPreview: clearPreview,
    updateAuthUI: updateAuthUI,
    updateBackendDot: updateBackendDot,
    showSheetsResult: showSheetsResult,
    showProgress: showProgress,
    hideProgress: hideProgress,
    showBlogResults: showBlogResults,
    parseImageTags: parseImageTags,
    populateBlogSelect: populateBlogSelect,
    showImageSlots: showImageSlots,
    showImageResult: showImageResult,
    setApplyButtonEnabled: setApplyButtonEnabled,
    showUploadChecklist: showUploadChecklist,
    getSelectedUploadIndices: getSelectedUploadIndices,
    showUploadList: showUploadList,
    loadTistoryCategories: loadTistoryCategories,
    getTextareaValue: getTextareaValue,
    setButtonsEnabled: setButtonsEnabled,
  };
})();
