/**
 * ui.js — UI 인터랙션 모듈
 * DOM 조작, 상태 표시, 테이블 렌더링 담당
 */

(function () {
  'use strict';

  var $ = function (sel) { return document.querySelector(sel); };

  /**
   * 파싱 결과를 테이블로 렌더링
   * @param {Array} tools - [{ rank, name, tagline, category, price, saves }]
   */
  function showParsedPreview(tools) {
    var area = $('#preview-area');
    if (!tools || tools.length === 0) {
      area.innerHTML = '<div class="preview--empty">파싱된 결과가 없습니다</div>';
      return;
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

    area.innerHTML =
      '<table class="table" id="preview-table">' +
      header + '<tbody>' + rows + '</tbody></table>';
  }

  /**
   * 상태 메시지 표시
   * @param {string} message
   * @param {"info"|"success"|"error"|"loading"} type
   */
  function showStatus(message, type) {
    type = type || 'info';
    var log = $('#status-log');
    var time = new Date().toLocaleTimeString('ko-KR');
    var item = document.createElement('div');
    item.className = 'status-log__item status-log__item--' + type;
    item.textContent = '[' + time + '] ' + message;
    log.prepend(item);

    // 최대 50개 유지
    while (log.children.length > 50) {
      log.removeChild(log.lastChild);
    }
  }

  /** 미리보기 초기화 */
  function clearPreview() {
    var area = $('#preview-area');
    area.innerHTML = '<div class="preview--empty">TAAFT 데이터를 붙여넣고 "파싱하기" 버튼을 클릭하세요</div>';
  }

  /**
   * 인증 상태에 따라 UI 업데이트
   * @param {boolean} isSignedIn
   */
  function updateAuthUI(isSignedIn) {
    var btnIn = $('#btn-sign-in');
    var btnOut = $('#btn-sign-out');
    var btnSave = $('#btn-save-log');
    var btnUpdate = $('#btn-update-db');

    if (isSignedIn) {
      btnIn.hidden = true;
      btnOut.hidden = false;
      btnSave.disabled = false;
      btnUpdate.disabled = false;
    } else {
      btnIn.hidden = false;
      btnOut.hidden = true;
      btnSave.disabled = true;
      btnUpdate.disabled = true;
    }
  }

  /** textarea 값 반환 */
  function getTextareaValue() {
    return ($('#raw-input') || {}).value || '';
  }

  /**
   * 버튼 활성/비활성 일괄 토글
   * @param {boolean} enabled
   */
  function setButtonsEnabled(enabled) {
    var buttons = document.querySelectorAll('.btn--primary, .btn--success');
    buttons.forEach(function (btn) { btn.disabled = !enabled; });
  }

  /** HTML 이스케이프 */
  function _esc(str) {
    var div = document.createElement('div');
    div.textContent = str || '';
    return div.innerHTML;
  }

  window.UI = {
    showParsedPreview: showParsedPreview,
    showStatus: showStatus,
    clearPreview: clearPreview,
    updateAuthUI: updateAuthUI,
    getTextareaValue: getTextareaValue,
    setButtonsEnabled: setButtonsEnabled,
  };
})();
