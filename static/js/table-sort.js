/*
  table-sort.js — Ordenação e filtro client-side de tabelas (vanilla JS puro).
  Uso: adicione data-sortable="true" no <table> ou data-sortable nos <th>.
  Para filtro: adicione um input com data-table-filter="id-da-tabela"
*/

(function () {
  'use strict';

  var ICON_NEUTRAL = '↕'; // ↕
  var ICON_ASC = '↑';   // ↑
  var ICON_DESC = '↓';  // ↓

  var tableStates = new WeakMap();

  function initTableSort() {
    var tables = document.querySelectorAll('table[data-sortable]');
    tables.forEach(makeSortable);

    document.querySelectorAll('th[data-sortable]').forEach(function (th) {
      var table = th.closest('table');
      if (table && !tableStates.has(table)) {
        makeSortable(table);
      }
    });
  }

  function makeSortable(table) {
    var thead = table.querySelector('thead');
    if (!thead) return;

    var headers = thead.querySelectorAll('th[data-sortable]');
    if (headers.length === 0) {
      headers = thead.querySelectorAll('th');
    }

    var state = { colIndex: -1, dir: 'none' };
    tableStates.set(table, state);

    headers.forEach(function (th) {
      th.style.cursor = 'pointer';
      th.style.userSelect = 'none';
      var icon = document.createElement('span');
      icon.className = 'sort-icon';
      icon.textContent = ' ' + ICON_NEUTRAL;
      icon.style.fontSize = '0.75em';
      icon.style.opacity = '0.4';
      icon.style.marginLeft = '4px';
      th.appendChild(icon);

      th.addEventListener('click', function () {
        var tbody = table.querySelector('tbody');
        if (!tbody) return;

        var colIdx = Array.prototype.indexOf.call(th.parentNode.children, th);

        var newDir;
        if (state.colIndex === colIdx && state.dir === 'asc') {
          newDir = 'desc';
        } else if (state.colIndex === colIdx && state.dir === 'desc') {
          newDir = 'none';
        } else {
          newDir = 'asc';
        }

        thead.querySelectorAll('.sort-icon').forEach(function (ic) {
          ic.textContent = ' ' + ICON_NEUTRAL;
          ic.style.opacity = '0.4';
        });

        if (newDir === 'none') {
          state.colIndex = -1;
          state.dir = 'none';
          return;
        }

        icon.textContent = ' ' + (newDir === 'asc' ? ICON_ASC : ICON_DESC);
        icon.style.opacity = '1';

        state.colIndex = colIdx;
        state.dir = newDir;

        var rows = Array.prototype.slice.call(tbody.querySelectorAll('tr'));

        rows.sort(function (a, b) {
          var cellA = a.children[colIdx];
          var cellB = b.children[colIdx];
          if (!cellA || !cellB) return 0;

          var valA = cellA.textContent.trim();
          var valB = cellB.textContent.trim();

          var result = compareValues(valA, valB);
          return newDir === 'asc' ? result : -result;
        });

        rows.forEach(function (row) {
          tbody.appendChild(row);
        });
      });
    });
  }

  function compareValues(a, b) {
    var numA = parseFloat(a.replace(',', '.'));
    var numB = parseFloat(b.replace(',', '.'));
    if (!isNaN(numA) && !isNaN(numB)) {
      return numA - numB;
    }

    var dateA = parseDate(a);
    var dateB = parseDate(b);
    if (dateA && dateB) {
      return dateA - dateB;
    }

    return a.localeCompare(b, 'pt-BR', { sensitivity: 'base' });
  }

  function parseDate(str) {
    if (!str || str === '-' || str === '—') return null;

    var m = str.match(/^(\d{1,2})\/(\d{1,2})\/(\d{2,4})$/);
    if (m) {
      var year = parseInt(m[3], 10);
      if (year < 100) year += 2000;
      return new Date(year, parseInt(m[2], 10) - 1, parseInt(m[1], 10));
    }

    var m2 = str.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (m2) {
      return new Date(parseInt(m2[1], 10), parseInt(m2[2], 10) - 1, parseInt(m2[3], 10));
    }

    return null;
  }

  // Filtro de busca para tabelas
  function initTableFilter() {
    document.querySelectorAll('[data-table-filter]').forEach(function (input) {
      var tableId = input.getAttribute('data-table-filter');
      var table = document.getElementById(tableId);
      if (!table) return;

      input.addEventListener('input', function () {
        var query = input.value.toLowerCase();
        var tbody = table.querySelector('tbody');
        if (!tbody) return;

        tbody.querySelectorAll('tr').forEach(function (row) {
          var text = row.textContent.toLowerCase();
          row.style.display = text.indexOf(query) !== -1 ? '' : 'none';
        });
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      initTableSort();
      initTableFilter();
    });
  } else {
    initTableSort();
    initTableFilter();
  }
})();
