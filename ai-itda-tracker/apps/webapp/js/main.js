/**
 * main.js — 모듈 조합 + 이벤트 바인딩
 * Parser, Sheets, UI를 연결하는 진입점
 */

(function () {
  'use strict';

  // Google API 설정 (사용자가 직접 입력)
  var GOOGLE_API_KEY = (window.CONFIG || {}).GOOGLE_API_KEY || '';
  var GOOGLE_CLIENT_ID = (window.CONFIG || {}).GOOGLE_CLIENT_ID || '';

  // 현재 파싱된 툴 목록
  var _parsedTools = [];

  /** 초기화 */
  async function init() {
    UI.clearPreview();
    UI.updateAuthUI(false);
    UI.showStatus('앱 초기화 중...', 'info');

    // Google API 초기화
    if (GOOGLE_API_KEY && GOOGLE_CLIENT_ID) {
      try {
        await Sheets.initSheetsAPI(GOOGLE_API_KEY, GOOGLE_CLIENT_ID, function (isSignedIn) {
          UI.updateAuthUI(isSignedIn);
          UI.showStatus(
            isSignedIn ? 'Google 로그인 완료' : 'Google 로그아웃 완료',
            isSignedIn ? 'success' : 'info'
          );
        });
        UI.showStatus('Google Sheets API 준비 완료', 'success');
      } catch (err) {
        UI.showStatus('Google API 초기화 실패: ' + err.message, 'error');
        console.error(err);
      }
    } else {
      UI.showStatus('Google API 키가 설정되지 않았습니다. main.js에서 키를 입력하세요.', 'error');
    }

    _bindEvents();
    UI.showStatus('앱 준비 완료', 'success');
  }

  /** 이벤트 바인딩 */
  function _bindEvents() {
    document.getElementById('btn-parse').addEventListener('click', _handleParse);
    document.getElementById('btn-save-log').addEventListener('click', _handleSaveLog);
    document.getElementById('btn-update-db').addEventListener('click', _handleUpdateDB);

    document.getElementById('btn-sign-in').addEventListener('click', function () {
      try { Sheets.signIn(); } catch (e) { UI.showStatus(e.message, 'error'); }
    });
    document.getElementById('btn-sign-out').addEventListener('click', function () {
      Sheets.signOut();
    });
  }

  /** 파싱 처리 */
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
    UI.showStatus('파싱 완료: ' + _parsedTools.length + '개 툴 발견', 'success');
  }

  /** 주간 로그 저장 */
  async function _handleSaveLog() {
    if (_parsedTools.length === 0) {
      UI.showStatus('먼저 데이터를 파싱하세요.', 'error');
      return;
    }

    UI.setButtonsEnabled(false);
    UI.showStatus('주간 로그에 ' + _parsedTools.length + '개 툴 저장 중...', 'loading');

    try {
      var count = await Sheets.appendToWeeklyLog(_parsedTools);
      UI.showStatus('주간 로그 저장 완료: ' + count + '행 추가됨', 'success');
    } catch (err) {
      UI.showStatus('주간 로그 저장 실패: ' + err.message, 'error');
      console.error(err);
    } finally {
      UI.setButtonsEnabled(true);
    }
  }

  /** 툴 DB 업데이트 */
  async function _handleUpdateDB() {
    if (_parsedTools.length === 0) {
      UI.showStatus('먼저 데이터를 파싱하세요.', 'error');
      return;
    }

    UI.setButtonsEnabled(false);
    UI.showStatus('툴 DB 업데이트 중 (' + _parsedTools.length + '개 툴)...', 'loading');

    try {
      var result = await Sheets.updateToolDB(_parsedTools);
      UI.showStatus('툴 DB 업데이트 완료: 신규 ' + result.added + '개, 갱신 ' + result.updated + '개', 'success');
    } catch (err) {
      UI.showStatus('툴 DB 업데이트 실패: ' + err.message, 'error');
      console.error(err);
    } finally {
      UI.setButtonsEnabled(true);
    }
  }

  document.addEventListener('DOMContentLoaded', init);
})();
