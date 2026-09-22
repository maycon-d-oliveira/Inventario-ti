# DESIGN SYSTEM — Inventário de Celulares

Guiia de uso dos componentes e tokens do sistema.

---

## 1. TOKENS DE DESIGN

Todos os tokens estão definidos em `static/css/design-system.css` sob `:root`.

### Cores
| Token | Valor | Uso |
|-------|-------|-----|
| `--color-primary` | `#0F172A` | Textos principais |
| `--color-primary-soft` | `#1E293B` | Textos secundários |
| `--color-accent` | `#6366F1` | Ação principal (indigo) |
| `--color-accent-hover` | `#4F46E5` | Hover do accent |
| `--color-accent-light` | `#EEF2FF` | Fundo de badges, highlights |
| `--color-muted` | `#64748B` | Textos terciários |
| `--color-border` | `#E2E8F0` | Bordas sutis |
| `--color-surface` | `#F8FAFC` | Fundo de cards, inputs |
| `--color-background` | `#FFFFFF` | Fundo principal |
| `--color-danger` | `#EF4444` | Ações destrutivas |
| `--color-success` | `#10B981` | Sucesso |
| `--color-warning` | `#F59E0B` | Alertas |

### Tipografia
- **Fonte:** Inter (via Google Fonts), fallback para system-ui
- **Escala:** `--text-xs` (0.75rem) até `--text-3xl` (1.875rem)
- **Pesos:** 400 (normal), 500 (medium), 600 (semibold), 700 (bold)

### Espaçamento
Escala baseada em 4px: `--space-1` (4px) até `--space-16` (64px).

### Bordas e Sombras
- Bordas: `--radius-sm` (4px) a `--radius-full` (9999px)
- Sombras: `--shadow-xs` a `--shadow-lg` (sempre sutis)

---

## 2. COMPONENTES

### 2.1 Botões

```html
<!-- Base -->
<button class="btn">Botão</button>

<!-- Variações -->
<button class="btn btn-primary">Primário</button>
<button class="btn btn-secondary">Secundário</button>
<button class="btn btn-ghost">Ghost</button>
<button class="btn btn-danger">Perigo</button>

<!-- Tamanhos -->
<button class="btn btn-sm">Pequeno</button>
<button class="btn">Normal</button>
<button class="btn btn-lg">Grande</button>

<!-- Estado desabilitado -->
<button class="btn" disabled>Não clicável</button>
```

**Regras:**
- Botão primário para ação principal da página
- Botão ghost para "Cancelar" ou ações não prioritárias
- Botão danger apenas para ações destrutivas

### 2.2 Formulários

```html
<div class="form-group">
    <label class="form-label" for="campo">Campo <span class="required">*</span></label>
    <input class="form-input" type="text" id="campo" name="campo" required>
    <span class="form-hint">Texto de ajuda</span>
    <span class="form-error">Mensagem de erro</span>
</div>

<!-- Select -->
<select class="form-select" id="sel" name="sel">
    <option value="">Selecione...</option>
</select>

<!-- Textarea -->
<textarea class="form-textarea" id="obs" name="obs" rows="4"></textarea>
```

**Regras:**
- Labels SEMPRE acima dos inputs
- Campos obrigatórios têm `<span class="required">*</span>`
- Usar `form-group` para agrupar label + input + hint/error
- `form-hint` para texto de ajuda, `form-error` para erros

### 2.3 Grid de Formulário

```html
<div class="form-grid">
    <div class="form-group">
        <label class="form-label" for="um">Campo 1</label>
        <input class="form-input" type="text" id="um" name="um">
    </div>
    <div class="form-group">
        <label class="form-label" for="dois">Campo 2</label>
        <input class="form-input" type="text" id="dois" name="dois">
    </div>
    <!-- Ocupa largura total -->
    <div class="form-group full-width">
        <label>...</label>
        <input ...>
    </div>
</div>
```

### 2.4 Cards

```html
<div class="card">
    <div class="card-header">Cabeçalho</div>
    <div class="card-body">Conteúdo</div>
    <div class="card-footer">
        <button class="btn btn-ghost">Cancelar</button>
        <button class="btn btn-primary">Salvar</button>
    </div>
</div>

<!-- Com hover elevation -->
<div class="card card-hover">...</div>
```

### 2.5 Tabelas

```html
<div class="table-wrapper">
    <table class="table">
        <thead>
            <tr>
                <th scope="col">Coluna</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Dado</td>
            </tr>
        </tbody>
    </table>
</div>
```

**Regras:**
- Sempre usar `scope="col"` no `<th>` do `<thead>`
- Coluna de ações alinhada à direita com `class="actions-cell"`
- Usar `table-wrapper` para scroll horizontal em mobile

### 2.6 Badges

```html
<span class="badge badge-success">Ativo</span>
<span class="badge badge-danger">Inativo</span>
<span class="badge badge-warning">Pendente</span>
<span class="badge badge-info">Novo</span>
<span class="badge badge-neutral">Padrão</span>
```

### 2.7 Alertas

```html
<div class="alert alert-success" role="alert">
    <span>Operação realizada com sucesso!</span>
    <button class="alert-close" onclick="this.parentElement.remove()">&times;</button>
</div>
<div class="alert alert-error">Erro ao processar.</div>
<div class="alert alert-warning">Atenção!</div>
<div class="alert alert-info">Informação.</div>
```

### 2.8 Navegação

**Sidebar:**
```html
<aside class="sidebar">
    <div class="sidebar-brand">
        <h1>Nome</h1>
        <p>Descrição</p>
    </div>
    <nav class="sidebar-nav">
        <div class="nav-group">
            <div class="nav-group-label">Seção</div>
            <a class="nav-item active" href="#">Item ativo</a>
            <a class="nav-item" href="#">Item</a>
        </div>
    </nav>
    <div class="sidebar-footer">Versão</div>
</aside>
```

**Topbar:**
```html
<header class="topbar">
    <div class="topbar-left">
        <h1 class="topbar-title">Página</h1>
        <nav class="breadcrumb">
            <a href="#">Home</a>
            <span class="separator">/</span>
            <span>Atual</span>
        </nav>
    </div>
    <div class="topbar-actions" id="pageActions">
        <!-- Botões de ação da página -->
    </div>
</header>
```

---

## 3. UTILITÁRIOS

### Tipografia
- `.text-muted` — texto cinza
- `.text-sm` / `.text-xs` — tamanhos pequenos
- `.font-medium` / `.font-semibold` / `.font-bold` — pesos

### Flexbox
- `.flex` / `.flex-col` — display e direção
- `.items-center` / `.justify-between` — alinhamento
- `.gap-1` a `.gap-8` — espaçamento entre itens

### Espaçamento
- `.mt-4` / `.mt-6` / `.mt-8` — margin-top
- `.mb-4` / `.mb-6` / `.mb-8` — margin-bottom
- `.px-4` / `.px-6` — padding horizontal
- `.py-4` / `.py-6` — padding vertical

### Layout
- `.w-full` — width: 100%
- `.max-w-sm` / `.max-w-md` / `.max-w-lg` / `.max-w-xl`

### Estado
- `.hidden` — oculta elemento
- `.sr-only` — acessibilidade (screen readers apenas)

---

## 4. COMO ADICIONAR UMA NOVA COR

1. Adicione a variável em `:root` no `design-system.css`:
   ```css
   --color-nova: #123456;
   --color-nova-light: #654321;
   ```

2. Se for um badge, adicione:
   ```css
   .badge-nova {
     background: var(--color-nova-light);
     color: var(--color-nova);
   }
   ```

3. Se for um alerta, adicione:
   ```css
   .alert-nova {
     background: var(--color-nova-light);
     border-color: var(--color-nova);
     color: #......;
   }
   ```

---

## 5. COMO CRIAR UMA NOVA PÁGINA

1. Crie o template em `templates/<modulo>/<pagina>.html`
2. Estenda o base: `{% extends 'base.html' %}`
3. Defina os blocks:
   ```html
   {% block title %}Título{% endblock %}
   {% block page_title %}Título da Página{% endblock %}
   {% block breadcrumb %}<a href="#">Home</a><span class="separator">/</span><span>Atual</span>{% endblock %}
   {% block page_actions %}
       <!-- Botões de ação no topbar -->
   {% endblock %}
   {% block content %}
       <!-- Conteúdo principal -->
   {% endblock %}
   ```
4. Use os componentes do design system (`.card`, `.btn-*`, `.form-*`, `.table`)

---

## 6. CHECKLIST DE UX (validar antes de subir)

- [ ] Título H1 único por página
- [ ] Ação primária no canto superior direito
- [ ] Labels SEMPRE acima dos inputs
- [ ] Campos obrigatórios marcados com `*` e legenda no topo
- [ ] Tabelas têm `scope="col"` no `<thead>`
- [ ] Coluna de ações à direita nas tabelas
- [ ] Botão Cancelar como `.btn-ghost`
- [ ] Estados vazios com ícone, mensagem e ação
- [ ] Paginação com "Mostrando X de Y resultados"
- [ ] Ações destrutivas com `onclick="return confirm(...)"` ou `data-confirm`
- [ ] Contraste mínimo 4.5:1
- [ ] Focus visible em todos os elementos interativos
- [ ] Nenhum estilo inline (tudo em CSS)
- [ ] Responsivo (testado em <=768px)

---

## 7. COMO EXTENDER SEM QUEBRAR

- **Novo componente:** Adicione em `design-system.css` seguindo o padrão de nomenclatura (ex: `.novo-componente`)
- **Ajuste de página específica:** Use `main.css` para estilos que não fazem sentido no design system
- **Nunca** altere um componente base sem testar todas as páginas que o usam
- **Nunca** adicione `style` inline nos templates
- **Sempre** use variáveis CSS (`var(--color-...)`) em vez de valores hardcoded
