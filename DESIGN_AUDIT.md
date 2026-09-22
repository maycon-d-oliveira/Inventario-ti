# DESIGN AUDIT — Inventário de Celulares

**Data da auditoria:** 2026-04-28
**Escopo:** Todos os templates Jinja2 e arquivos estáticos

---

## 1. INVENTÁRIO DE PÁGINAS/TEMPLATES

### 1.1 base.html
- **Arquivo:** `templates/base.html`
- **Objetivo:** Layout base com sidebar fixa e área de conteúdo
- **Elementos UI:** Sidebar, nav menu, flash messages, block content
- **Problemas de UX:**
  - Viewport meta incorreto (`1.0` deveria ser `1.0`)
  - Sidebar sem indicação visual de item ativo
  - Flash messages sem auto-dismiss
  - Não tem breadcrumb
  - Não tem confirmação de ações destrutivas
  - Não importa fonte Inter ou system-ui
  - Não tem botão mobile para toggle da sidebar

### 1.2 dashboard.html
- **Arquivo:** `templates/dashboard.html`
- **Objetivo:** Visão geral com indicadores e tabelas resumo
- **Elementos UI:** 3 stat cards, 2 tabelas resumo, 1 tabela de atualizações
- **Problemas de UX:**
  - Cards de estatísticas sem hierarquia visual clara
  - Tabelas sem `thead` com escopo correto
  - Falta espaçamento consistente entre seções
  - Cards não têm sombras sutis ou elevação

### 1.3 inventario/lista.html
- **Arquivo:** `templates/inventario/lista.html`
- **Objetivo:** Listar aparelhos com filtros e paginação
- **Elementos UI:** Header com ações, form de filtros (6 selects + input), tabela, paginação
- **Problemas de UX:**
  - Filtros em linha única sem organização
  - Tabela usa FontAwesome (`fas fa-*`) mas não há import da biblioteca
  - Ações na tabela usam ícones quebrados
  - Paginação simples sem indicador "Mostrando X de Y"
  - Falta estado vazio bem tratado
  - Coluna de ações não destacada visualmente

### 1.4 inventario/form.html
- **Arquivo:** `templates/inventario/form.html`
- **Objetivo:** Cadastrar ou editar aparelho
- **Elementos UI:** Formulário em 4 seções (details/summary), inputs, textarea
- **Problemas de UX:**
  - Labels não têm `for` correspondente aos inputs
  - Campos obrigatórios não marcados com asterisco
  - Sem validação visual de erros
  - Details nativos sem estilo
  - Botão Cancelar é um link estilizado como btn-secondary (deveria ser ghost)
  - Falta legenda de campos obrigatórios no topo
  - Inputs sem estados de foco visíveis

### 1.5 inventario/ficha.html
- **Arquivo:** `templates/inventario/ficha.html`
- **Objetivo:** Visualização detalhada do aparelho
- **Elementos UI:** Detail grid, tabela de histórico de chip, botões de ação
- **Problemas de UX:**
  - Grid de detalhes sem hierarquia clara (label vs valor)
  - Botão "Mover para estoque" é um form separado, quebra o layout
  - Tabela de histórico sem formatação especial
  - Falta data de atualização em destaque

### 1.6 chips/lista.html
- **Arquivo:** `templates/chips/lista.html`
- **Objetivo:** Gestão de chips, vínculo e histórico
- **Elementos UI:** Filtros, tabela de chips, form inline para vincular, tabela de histórico
- **Problemas de UX:**
  - Formulário de vínculo inline na tabela (quebra o layout mobile)
  - Input de ID aparelho sem label visível (placeholder como label)
  - Histórico aparece abaixo sem separação visual clara
  - Falta botão para novo chip

### 1.7 colaboradores/busca.html
- **Arquivo:** `templates/colaboradores/busca.html`
- **Objetivo:** Buscar colaboradores por nome/matrícula
- **Elementos UI:** Campo de busca, tabela de resultados
- **Problemas de UX:**
  - Campo de busca sem label (apenas placeholder)
  - Tabela sem paginação
  - Estado vazio ("Faça uma busca...") não é amigável
  - Resultado aparece só após busca (padrão confuso)

### 1.8 descarte/lista.html
- **Arquivo:** `templates/descarte/lista.html`
- **Objetivo:** Registrar e consultar descartes
- **Elementos UI:** 2 forms (registro + filtros) lado a lado, tabela histórico
- **Problemas de UX:**
  - Formulários lado a lado quebrando em mobile
  - Campos sem labels (apenas spans internos)
  - Tabela sem formatação de data
  - Falta confirmação para exclusão de registros

### 1.9 devolvidos/lista.html
- **Arquivo:** `templates/devolvidos/lista.html`
- **Objetivo:** Controlar devoluções e triagem
- **Elementos UI:** 2 forms (registro + filtros), tabela com ações inline
- **Problemas de UX:**
  - Múltiplos formulários inline na tabela (quebra layout)
  - Ações de destino (estoque/descarte) confusas
  - Campos de data e motivo dentro da tabela
  - Falta workflow visual claro (devolvido → triagem → destino)

### 1.10 estoque/lista.html
- **Arquivo:** `templates/estoque/lista.html`
- **Objetivo:** Controlar estoque de aparelhos
- **Elementos UI:** Filtro, tabela com form inline para mover ao inventário
- **Problemas de UX:**
  - Formulário inline para mover ao inventário (3 campos sem label)
  - Campos "Usuário", "Responsável", "Uso" sem label visível
  - Tabela não indica claramente status disponível/indisponível

### 1.11 grupos/lista.html
- **Arquivo:** `templates/grupos/lista.html`
- **Objetivo:** Visualizar grupos WhatsApp e integrantes
- **Elementos UI:** 2 tabelas lado a lado (resumo + integrantes)
- **Problemas de UX:**
  - Duas tabelas lado a lado sem muito destaque
  - Tabela de integrantes pode crescer muito (sem paginação)
  - Falta indicador visual de linha corporativa

---

## 2. PROBLEMAS GLOBAIS DE UX NO CSS ATUAL

### 2.1 Cores e Tipografia
- Usa paleta própria mas com nomes de variáveis inconsistentes (`--bg`, `--panel`)
- Font-family usa "Segoe UI" (Windows only) — não tem fallbacks adequados
- Falta hierarquia clara de tamanhos de fonte

### 2.2 Componentes
- Botões têm border-radius 12px (muito arredondado para estilo minimalista)
- Cards têm border-radius 18px (excessivo)
- Faltam estados hover/focus consistentes
- Faltam badges/tags para status
- Faltam alertas estilizados (success, error, warning)

### 2.3 Layout
- Sidebar tem 280px (muito larga para o conteúdo)
- Grid usa `auto-fit` mas sem controle de colunas máximas
- Espaçamento inconsistente (mix de 20px, 22px, 28px, 30px)
- Falta max-width container centralizado

### 2.4 Acessibilidade
- Nenhum input tem `id` + label `for`
- Botões de ícone sem `aria-label`
- Cores não atendem contraste 4.5:1 em todos os casos
- Faltam `scope` nos cabeçalhos de tabela

### 2.5 JavaScript
- MDM ID blur já implementado
- Auto-dismiss de flash só esconde, não remove
- Falta confirmação para ações destrutivas
- Falta debounce em campos de busca
- Falta loading state em botões de submit

---

## 3. PRIORIZAÇÃO DE REFORMULAÇÃO

### Alta Prioridade (quebra de UX)
1. Design System completo (tokens + componentes)
2. Base template com sidebar funcional e breadcrumb
3. Formulários com labels adequadas e validação
4. Tabelas com acessibilidade e estados vazios
5. Buttons com estados consistentes

### Média Prioridade
6. Dashboard com cards bien formatados
7. Fichas de detalhes com hierarquia clara
8. Flash messages com auto-dismiss e tipos
9. Confirmações de ações destrutivas

### Baixa Prioridade
10. Animações sutis e transições
11. Estados de loading
12. Busca com debounce

---

## 4. RESUMO DE ELEMENTOS POR PÁGINA

| Página | Tabelas | Forms | Botões | Cards | Filtros | Ações especiais |
|--------|---------|-------|--------|-------|---------|-----------------|
| Dashboard | 3 | 0 | 0 | 3 | 0 | - |
| Inventário Lista | 1 | 1 | 3 | 0 | 6 | Paginação |
| Inventário Form | 0 | 1 | 2 | 4 | 0 | MDM lookup |
| Inventário Ficha | 1 | 1 | 2 | 1 | 0 | Histórico |
| Chips | 2 | 2 | 2 | 0 | 2 | Vínculo inline |
| Colaboradores | 1 | 1 | 1 | 0 | 1 | - |
| Descarte | 1 | 2 | 2 | 0 | 3 | - |
| Devolvidos | 1 | 2 | 2 | 0 | 1 | Ações inline |
| Estoque | 1 | 1 | 1 | 0 | 1 | Mover inline |
| Grupos | 2 | 0 | 1 | 0 | 0 | - |

---

## 5. CHECKLIST PARA REFORMULAÇÃO

- [ ] Criar design-system.css com tokens e componentes
- [ ] Reconstruir base.html com sidebar + topbar
- [ ] Atualizar todas as tabelas com acessibilidade
- [ ] Padronizar todos os formulários
- [ ] Criar estados vazios amigáveis
- [ ] Implementar confirmações de exclusão
- [ ] Atualizar JavaScript com boas práticas
- [ ] Documentar Design System em DESIGN_SYSTEM.md
