/**
 * sheets.js — Google Sheets API v4 브라우저 클라이언트
 * gapi를 사용해 스프레드시트 읽기/쓰기
 */
(function () {
  'use strict';

  var SPREADSHEET_ID = '1WXJ-6pbTv8Dg-fYhNyvKK98wo8VWonxo8TZPk6I-H1A';
  var DISCOVERY_DOC = 'https://sheets.googleapis.com/$discovery/rest?version=v4';
  var SCOPES = 'https://www.googleapis.com/auth/spreadsheets';

  var _tokenClient = null;
  var _onAuthChange = null;
  var _isSignedIn = false;

  // ─── gapi / google 로딩 대기 ───

  function _waitForGapi(timeout) {
    timeout = timeout || 10000;
    return new Promise(function (resolve, reject) {
      var start = Date.now();
      (function check() {
        if (typeof gapi !== 'undefined') return resolve();
        if (Date.now() - start > timeout) return reject(new Error('gapi 로드 타임아웃'));
        setTimeout(check, 200);
      })();
    });
  }

  function _waitForGoogle(timeout) {
    timeout = timeout || 10000;
    return new Promise(function (resolve, reject) {
      var start = Date.now();
      (function check() {
        if (typeof google !== 'undefined' && google.accounts && google.accounts.oauth2) return resolve();
        if (Date.now() - start > timeout) return reject(new Error('Google Identity Services 로드 타임아웃'));
        setTimeout(check, 200);
      })();
    });
  }

  // ─── 초기화 ───

  async function initSheetsAPI(apiKey, clientId, onAuthChange) {
    _onAuthChange = onAuthChange;

    // gapi 스크립트 로딩 대기
    await _waitForGapi();

    // gapi client 로드
    await new Promise(function (resolve, reject) {
      gapi.load('client', { callback: resolve, onerror: reject });
    });

    await gapi.client.init({
      apiKey: apiKey,
      discoveryDocs: [DISCOVERY_DOC],
    });

    // GIS 스크립트 로딩 대기
    await _waitForGoogle();

    // GIS 토큰 클라이언트
    _tokenClient = google.accounts.oauth2.initTokenClient({
      client_id: clientId,
      scope: SCOPES,
      callback: function (resp) {
        if (resp.error) {
          console.error('인증 오류:', resp);
          _isSignedIn = false;
          if (_onAuthChange) _onAuthChange(false);
          return;
        }
        _isSignedIn = true;
        if (_onAuthChange) _onAuthChange(true);
      },
    });

    console.log('Google Sheets API 초기화 완료');
  }

  /** 초기화 완료 여부 */
  function isReady() {
    return _tokenClient !== null;
  }

  /** OAuth2 로그인 */
  function signIn() {
    if (!_tokenClient) {
      throw new Error('Google API 초기화 중입니다. 잠시 후 다시 시도하세요.');
    }
    _tokenClient.requestAccessToken();
  }

  /** 로그아웃 */
  function signOut() {
    var token = gapi.client.getToken();
    if (token) {
      google.accounts.oauth2.revoke(token.access_token);
      gapi.client.setToken(null);
    }
    _isSignedIn = false;
    if (_onAuthChange) _onAuthChange(false);
  }

  /** 로그인 상태 확인 */
  function isSignedIn() {
    return _isSignedIn;
  }

  // ─── 읽기 ───

  /** 툴 DB 전체 읽기 */
  async function getToolDB() {
    var response = await gapi.client.sheets.spreadsheets.values.get({
      spreadsheetId: SPREADSHEET_ID,
      range: '📦 툴 DB!A:J',
    });

    var rows = response.result.values || [];
    if (rows.length <= 1) return [];

    return rows.slice(1).map(function (row, i) {
      while (row.length < 10) row.push('');
      return {
        name:          row[0],
        tagline:       row[1],
        taaftCategory: row[2],
        aiCategory:    row[3],
        price:         row[4],
        released:      row[5],
        saves:         row[6],
        target:        row[7],
        blogStatus:    row[8],
        firstDate:     row[9],
        rowIndex:      i + 2,
      };
    });
  }

  /** 블로그 콘텐츠 시트 읽기 */
  async function getBlogContents() {
    var response = await gapi.client.sheets.spreadsheets.values.get({
      spreadsheetId: SPREADSHEET_ID,
      range: '📝 블로그 콘텐츠!A:F',
    });

    var rows = response.result.values || [];
    if (rows.length <= 1) return [];

    return rows.slice(1).map(function (row, i) {
      while (row.length < 6) row.push('');
      return {
        toolName:     row[0],
        title:        row[1],
        content:      row[2],
        createdAt:    row[3],
        uploadStatus: row[4],
        blogType:     row[5],
        rowIndex:     i + 2,
      };
    });
  }

  /** 주간 로그 읽기 */
  async function getWeeklyLog() {
    var response = await gapi.client.sheets.spreadsheets.values.get({
      spreadsheetId: SPREADSHEET_ID,
      range: '📅 주간 로그!A:K',
    });

    var rows = response.result.values || [];
    if (rows.length <= 1) return [];

    return rows.slice(1).map(function (row) {
      while (row.length < 11) row.push('');
      return {
        date:         row[0],
        rank:         row[1],
        name:         row[2],
        tagline:      row[3],
        taaftCategory:row[4],
        aiCategory:   row[5],
        price:        row[6],
        saves:        row[7],
        target:       row[8],
        newOrDup:     row[9],
        blogCreated:  row[10],
      };
    });
  }

  // ─── 쓰기 ───

  /** 주간 로그에 추가 */
  async function appendToWeeklyLog(tools) {
    if (!tools || tools.length === 0) throw new Error('저장할 툴이 없습니다.');

    var today = new Date().toISOString().split('T')[0];
    var rows = tools.map(function (t) {
      return [
        today, t.rank || '', t.name || '', t.tagline || '',
        t.category || '', '', t.price || '', t.saves || '',
        '', '', '',
      ];
    });

    var response = await gapi.client.sheets.spreadsheets.values.append({
      spreadsheetId: SPREADSHEET_ID,
      range: '📅 주간 로그!A:K',
      valueInputOption: 'RAW',
      insertDataOption: 'INSERT_ROWS',
      resource: { values: rows },
    });

    var updated = response.result.updates;
    return updated.updatedRows;
  }

  /** 툴 DB 업데이트 (신규 추가 + 저장수 갱신) */
  async function updateToolDB(tools) {
    if (!tools || tools.length === 0) throw new Error('업데이트할 툴이 없습니다.');

    var existing = await getToolDB();
    var existingNames = {};
    existing.forEach(function (t) { existingNames[t.name.toLowerCase()] = t; });

    var today = new Date().toISOString().split('T')[0];
    var added = 0;
    var updated = 0;

    var newRows = [];
    tools.forEach(function (t) {
      if (!existingNames[t.name.toLowerCase()]) {
        newRows.push([
          t.name, t.tagline, t.category, '',
          t.price, '', t.saves, '', '미작성', today,
        ]);
      }
    });

    if (newRows.length > 0) {
      await gapi.client.sheets.spreadsheets.values.append({
        spreadsheetId: SPREADSHEET_ID,
        range: '📦 툴 DB!A:J',
        valueInputOption: 'RAW',
        insertDataOption: 'INSERT_ROWS',
        resource: { values: newRows },
      });
      added = newRows.length;
    }

    for (var i = 0; i < tools.length; i++) {
      var t = tools[i];
      var match = existingNames[t.name.toLowerCase()];
      if (match && match.rowIndex && t.saves) {
        await gapi.client.sheets.spreadsheets.values.update({
          spreadsheetId: SPREADSHEET_ID,
          range: '📦 툴 DB!G' + match.rowIndex,
          valueInputOption: 'RAW',
          resource: { values: [[t.saves]] },
        });
        updated++;
      }
    }

    return { added: added, updated: updated };
  }

  window.Sheets = {
    initSheetsAPI: initSheetsAPI,
    isReady: isReady,
    signIn: signIn,
    signOut: signOut,
    isSignedIn: isSignedIn,
    getToolDB: getToolDB,
    getBlogContents: getBlogContents,
    getWeeklyLog: getWeeklyLog,
    appendToWeeklyLog: appendToWeeklyLog,
    updateToolDB: updateToolDB,
  };
})();
