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

  /**
   * Google API 초기화
   * @param {string} apiKey - Google API 키
   * @param {string} clientId - OAuth2 클라이언트 ID
   * @param {function} onAuthChange - 인증 상태 변경 콜백(isSignedIn)
   */
  async function initSheetsAPI(apiKey, clientId, onAuthChange) {
    _onAuthChange = onAuthChange;

    // gapi client 로드
    await new Promise(function (resolve, reject) {
      gapi.load('client', { callback: resolve, onerror: reject });
    });

    await gapi.client.init({
      apiKey: apiKey,
      discoveryDocs: [DISCOVERY_DOC],
    });

    // GIS 토큰 클라이언트
    _tokenClient = google.accounts.oauth2.initTokenClient({
      client_id: clientId,
      scope: SCOPES,
      callback: function (resp) {
        if (resp.error) {
          console.error('인증 오류:', resp);
          if (_onAuthChange) _onAuthChange(false);
          return;
        }
        if (_onAuthChange) _onAuthChange(true);
      },
    });

    console.log('Google Sheets API 초기화 완료');
  }

  /** OAuth2 로그인 */
  function signIn() {
    if (!_tokenClient) {
      throw new Error('API가 초기화되지 않았습니다. initSheetsAPI를 먼저 호출하세요.');
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
    if (_onAuthChange) _onAuthChange(false);
  }

  /**
   * 주간 로그 시트에 파싱된 툴 목록 추가
   * 컬럼: 수집일/순위/툴이름/Tagline/TAAFT카테고리/AI있다카테고리/가격/저장수/타겟?/신규중복/블로그생성
   */
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
    console.log('주간 로그에 ' + updated.updatedRows + '행 추가 완료');
    return updated.updatedRows;
  }

  /**
   * 툴 DB에 새 툴 추가 또는 기존 툴 저장수 업데이트
   * @returns {{ added: number, updated: number }}
   */
  async function updateToolDB(tools) {
    if (!tools || tools.length === 0) throw new Error('업데이트할 툴이 없습니다.');

    var existing = await getToolDB();
    var existingNames = {};
    existing.forEach(function (t) { existingNames[t.name.toLowerCase()] = t; });

    var today = new Date().toISOString().split('T')[0];
    var added = 0;
    var updated = 0;

    // 새 툴 추가
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

    // 기존 툴 저장수 업데이트
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

    console.log('툴 DB 업데이트: 신규 ' + added + '개, 갱신 ' + updated + '개');
    return { added: added, updated: updated };
  }

  /**
   * 툴 DB 전체 읽기
   */
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

  window.Sheets = {
    initSheetsAPI: initSheetsAPI,
    signIn: signIn,
    signOut: signOut,
    appendToWeeklyLog: appendToWeeklyLog,
    updateToolDB: updateToolDB,
    getToolDB: getToolDB,
  };
})();
