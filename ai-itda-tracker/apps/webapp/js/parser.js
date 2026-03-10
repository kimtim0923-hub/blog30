/**
 * parser.js — TAAFT 복사 데이터 파서
 * TAAFT에서 복사한 텍스트를 파싱해 구조화된 툴 배열로 변환
 */

(function () {
  'use strict';

  /**
   * 메인 파싱 함수: 원시 텍스트 -> 툴 배열
   * @param {string} text - 붙여넣은 원시 텍스트
   * @returns {{ tools: Array, error: string|null }}
   */
  function parseRawText(text) {
    if (!text || !text.trim()) {
      return { tools: [], error: '텍스트가 비어 있습니다.' };
    }

    var trimmed = text.trim();
    var firstLine = trimmed.split('\n')[0];

    // 탭 구분 형식 감지: 첫 줄에 탭이 2개 이상이면 TSV
    if ((firstLine.match(/\t/g) || []).length >= 2) {
      return _parseTSV(trimmed);
    }

    // 번호 리스트 형식: "1." 또는 "1)" 으로 시작
    if (/^\s*\d+[\.\)]\s/.test(firstLine)) {
      return _parseNumberedList(trimmed);
    }

    // 단순 줄 형식 (이름 - 태그라인)
    if (firstLine.includes(' - ') || firstLine.includes(' \u2013 ')) {
      return _parseSimpleLines(trimmed);
    }

    return { tools: [], error: '인식할 수 없는 형식입니다. 번호 리스트 또는 탭 구분 형식을 사용하세요.' };
  }

  /** 탭 구분(TSV) 형식 파싱 */
  function _parseTSV(text) {
    var lines = text.split('\n').filter(function (l) { return l.trim(); });
    if (lines.length === 0) return { tools: [], error: '빈 데이터' };

    var tools = [];
    var startIdx = 0;

    // 헤더 감지: 첫 번째 컬럼이 정확히 헤더 키워드인 경우만
    var firstCol = lines[0].split('\t')[0].trim().toLowerCase();
    if (firstCol === 'name' || firstCol === 'tool' || firstCol === 'tool name' || firstCol === '툴' || firstCol === '툴이름' || firstCol === '툴 이름') {
      startIdx = 1;
    }

    for (var i = startIdx; i < lines.length; i++) {
      var cols = lines[i].split('\t').map(function (c) { return c.trim(); });
      if (cols.length < 2 || !cols[0]) continue;

      tools.push({
        rank: tools.length + 1,
        name: cols[0],
        tagline: cols[1] || '',
        category: cols[2] || '',
        price: cols[3] || '',
        saves: cols[4] || '',
      });
    }

    if (tools.length === 0) return { tools: [], error: '파싱 가능한 행이 없습니다.' };
    return { tools: tools, error: null };
  }

  /** 번호 리스트 형식 파싱 */
  function _parseNumberedList(text) {
    var lines = text.split('\n');
    var tools = [];
    var current = null;

    for (var li = 0; li < lines.length; li++) {
      var trimLine = lines[li].trim();
      if (!trimLine) continue;

      // 번호로 시작하는 새 항목
      var numMatch = trimLine.match(/^\d+[\.\)]\s*(.+)/);
      if (numMatch) {
        if (current) tools.push(current);

        var rest = numMatch[1];
        var dashIdx = rest.search(/\s[-\u2013\u2014]\s/);
        var name, tagline;
        if (dashIdx > 0) {
          name = rest.substring(0, dashIdx).trim();
          tagline = rest.substring(dashIdx + 3).trim();
        } else {
          name = rest.trim();
          tagline = '';
        }

        current = {
          rank: tools.length + 1,
          name: name,
          tagline: tagline,
          category: '',
          price: '',
          saves: '',
        };
        continue;
      }

      // 메타데이터 줄
      if (current) {
        _extractMeta(trimLine, current);
      }
    }

    if (current) tools.push(current);
    if (tools.length === 0) return { tools: [], error: '파싱 가능한 항목이 없습니다.' };
    return { tools: tools, error: null };
  }

  /** 단순 줄 형식 파싱 */
  function _parseSimpleLines(text) {
    var lines = text.split('\n').filter(function (l) { return l.trim(); });
    var tools = [];

    for (var i = 0; i < lines.length; i++) {
      var trimLine = lines[i].trim();
      var dashIdx = trimLine.search(/\s[-\u2013\u2014]\s/);
      if (dashIdx > 0) {
        tools.push({
          rank: tools.length + 1,
          name: trimLine.substring(0, dashIdx).trim(),
          tagline: trimLine.substring(dashIdx + 3).trim(),
          category: '',
          price: '',
          saves: '',
        });
      }
    }

    if (tools.length === 0) return { tools: [], error: '파싱 가능한 항목이 없습니다.' };
    return { tools: tools, error: null };
  }

  /** 메타데이터 추출 */
  function _extractMeta(line, tool) {
    var catMatch = line.match(/(?:category|카테고리)\s*:\s*([^|]+)/i);
    if (catMatch) tool.category = catMatch[1].trim();

    var priceMatch = line.match(/(?:price|가격)\s*:\s*([^|]+)/i);
    if (priceMatch) tool.price = priceMatch[1].trim();

    var savesMatch = line.match(/(?:saves?|저장|저장수)\s*:\s*([^|]+)/i);
    if (savesMatch) tool.saves = savesMatch[1].trim();
  }

  window.Parser = { parseRawText: parseRawText };
})();
