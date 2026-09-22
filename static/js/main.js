/*
  main.js — Comportamentos de interface do sistema.
  Vanilla JavaScript (sem jQuery, sem frameworks de terceiros).
*/

document.addEventListener('DOMContentLoaded', () => {

    // === AUTO-DISMISS DE FLASH MESSAGES ===
    // Fecha automaticamente mensagens flash após 5 segundos
    // para evitar poluição visual durante a navegação.
    const flashArea = document.querySelector('.flash-area');
    if (flashArea) {
        const flashes = flashArea.querySelectorAll('.alert');
        flashes.forEach(flash => {
            // Auto-remove após 5 segundos
            setTimeout(() => {
                flash.style.opacity = '0';
                flash.style.transform = 'translateY(-8px)';
                flash.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
                setTimeout(() => flash.remove(), 400);

                // Remove o container se não houver mais flashes
                if (flashArea.querySelectorAll('.alert').length === 0) {
                    flashArea.remove();
                }
            }, 5000);
        });
    }

    // === FECHAR ALERTAS MANUALMENTE ===
    // Botão de fechar (×) em cada alerta
    document.querySelectorAll('.alert-close').forEach(btn => {
        btn.addEventListener('click', () => {
            const alert = btn.closest('.alert');
            if (alert) {
                alert.style.opacity = '0';
                alert.style.transition = 'opacity 0.3s ease';
                setTimeout(() => alert.remove(), 300);
            }
        });
    });

    // === TOGGLE SIDEBAR MOBILE ===
    // Abre/fecha a sidebar em dispositivos móveis via botão hambúrguer
    const menuToggle = document.getElementById('menuToggle');
    const sidebar = document.getElementById('sidebar');
    if (menuToggle && sidebar) {
        menuToggle.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });

        // Fecha sidebar ao clicar em um link (mobile)
        sidebar.querySelectorAll('.nav-item').forEach(link => {
            link.addEventListener('click', () => {
                if (window.innerWidth <= 768) {
                    sidebar.classList.remove('open');
                }
            });
        });

        // Fecha sidebar ao clicar fora dela (mobile)
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 768 &&
                sidebar.classList.contains('open') &&
                !sidebar.contains(e.target) &&
                e.target !== menuToggle &&
                !menuToggle.contains(e.target)) {
                sidebar.classList.remove('open');
            }
        });
    }

    // === CONFIRMAÇÃO DE AÇÕES DESTRUTIVAS ===
    // Exige confirmação antes de excluir ou mover itens
    // Usa o atributo data-confirm no botão/form
    document.querySelectorAll('[data-confirm]').forEach(element => {
        element.addEventListener('click', (e) => {
            const message = element.getAttribute('data-confirm');
            if (!confirm(message)) {
                e.preventDefault();
                return false;
            }
        });
    });

    // === LOADING STATE EM BOTÕES DE SUBMIT ===
    // Desabilita o botão e troca o texto para evitar envio duplo
    // Também adiciona indicador visual de loading
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', (e) => {
            const submitBtn = form.querySelector('button[type="submit"]:not([data-no-loading])');
            if (submitBtn && !submitBtn.disabled) {
                submitBtn.classList.add('btn-loading');
                submitBtn.disabled = true;

                // Restaura após 5 segundos (fallback se o form não submeter)
                setTimeout(() => {
                    submitBtn.classList.remove('btn-loading');
                    submitBtn.disabled = false;
                }, 5000);
            }
        });
    });

    // === BUSCA COM DEBOUNCE ===
    // Filtra resultados em tempo real com delay de 300ms
    // Evita múltiplas requisições enquanto o usuário digita
    const searchInputs = document.querySelectorAll('[data-table-filter]');
    searchInputs.forEach(input => {
        let timeout;
        input.addEventListener('input', () => {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                const targetId = input.getAttribute('data-table-filter');
                const query = input.value.toLowerCase();
                const table = document.getElementById(targetId);
                if (!table) return;
                const rows = table.querySelectorAll('tbody tr');

                rows.forEach(row => {
                    const text = row.textContent.toLowerCase();
                    row.style.display = text.includes(query) ? '' : 'none';
                });
            }, 300);
        });
    });

    // === FETCH MDM ID (Pulsus API) ===
    // Busca automaticamente dados do dispositivo quando o MDM ID perde o foco
    // Preenche e bloqueia os campos relacionados
    const mdmInput = document.getElementById('mdm_id');
    if (mdmInput) {
        const fields = ['marca', 'modelo', 'imei', 'mac_wifi', 'serial'];

        mdmInput.addEventListener('blur', async () => {
            const mdm = mdmInput.value.trim();
            if (!mdm) return;

            try {
                const response = await fetch(`/api/pulsus/device/${mdm}`);
                if (!response.ok) return;

                const data = await response.json();
                fields.forEach(name => {
                    const el = document.querySelector(`input[name="${name}"]`);
                    if (el) {
                        el.value = data[name] || '';
                        el.readOnly = true;
                    }
                });
            } catch (e) {
                console.error('Erro ao buscar dados do Pulsus:', e);
            }
        });

        // Limpa readonly quando usuário apaga o MDM ID
        mdmInput.addEventListener('input', () => {
            if (!mdmInput.value.trim()) {
                fields.forEach(name => {
                    const el = document.querySelector(`input[name="${name}"]`);
                    if (el) {
                        el.readOnly = false;
                    }
                });
            }
        });
    }

    // === DESTACAR LINHA DA TABELA (opcional, já feito via CSS) ===
    // Adiciona classe na linha clicada para feedback visual
    document.querySelectorAll('.table tbody tr').forEach(row => {
        row.addEventListener('click', (e) => {
            // Evita trigger se clicou em um botão, link ou input
            if (e.target.closest('a, button, input, form')) return;
            row.classList.toggle('row-highlight');
        });
    });

});
