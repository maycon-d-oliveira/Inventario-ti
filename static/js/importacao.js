/*
  importacao.js — Comportamento da página de mapeamento.
  Vanilla JS puro.
*/

/* global SHEET_COLS, TABLE_FIELDS, SHEET_PREVIEW */

function onSheetChange(idx, tableKey, sheetName) {
    'use strict';
    var div = document.getElementById('mapdiv_' + idx);
    var tbody = document.getElementById('mapbody_' + idx);
    var label = document.getElementById('tblabel_' + idx);
    if (!div || !tbody) return;

    if (!tableKey) {
        div.style.display = 'none';
        return;
    }
    div.style.display = 'block';

    // Atualiza label
    if (label) {
        var opt = document.getElementById('sel_' + idx);
        label.textContent = opt ? (opt.options[opt.selectedIndex] || '').text : tableKey;
    }

    // Colunas da aba da planilha
    var sheetCols = (SHEET_COLS && SHEET_COLS[sheetName]) || [];

    // Campos da tabela selecionada
    var fields = (TABLE_FIELDS && TABLE_FIELDS[tableKey]) || [];

    // Preview
    var previews = (SHEET_PREVIEW && SHEET_PREVIEW[sheetName]) || [];

    var html = '';
    fields.forEach(function(field) {
        // Sugestão automática
        var suggestedIdx = -1;
        var fieldNorm = field.toLowerCase().replace(/[^a-z0-9]/g, '_');
        sheetCols.forEach(function(sc, sci) {
            var scNorm = sc.toLowerCase().replace(/[^a-z0-9]/g, '_');
            if (scNorm === fieldNorm || scNorm.indexOf(fieldNorm) >= 0 || fieldNorm.indexOf(scNorm) >= 0) {
                suggestedIdx = sci;
            }
        });

        html += '<tr>';
        // Campo da tabela
        html += '<td><span class="font-medium">' + field + '</span>';
        html += '<input type="hidden" name="sheet_' + idx + '" value="' + (sheetName || '') + '">';
        html += '<input type="hidden" name="table_' + idx + '" value="' + tableKey + '">';
        html += '</td>';

        // Dropdown: escolher coluna da planilha
        html += '<td><select class="form-select" name="map_' + idx + '_' + field + '">';
        html += '<option value="">-- Ignorar --</option>';
        sheetCols.forEach(function(sc, sci) {
            var sel = (sci === suggestedIdx) ? ' selected' : '';
            html += '<option value="' + sci + '"' + sel + '>' + sc + '</option>';
        });
        html += '</select></td>';

        // Preview
        html += '<td class="text-sm text-muted">';
        if (previews.length > 0) {
            var pvs = [];
            previews.forEach(function(row) {
                if (row[sci] !== undefined) pvs.push(row[sci]);
            });
            html += pvs.join(', ');
        }
        html += '</td></tr>';
    });

    tbody.innerHTML = html;
}

// Inicialização
document.addEventListener('DOMContentLoaded', function() {
    var selects = document.querySelectorAll('[id^="sel_"]');
    selects.forEach(function(sel) {
        if (!sel.value) return;
        var idx = sel.id.replace('sel_', '');
        var opt = sel.options[sel.selectedIndex];
        var sheetName = opt ? opt.getAttribute('data-sheet') : '';
        onSheetChange(parseInt(idx, 10), sel.value, sheetName);
    });
});
