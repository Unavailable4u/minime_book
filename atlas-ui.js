/* MiniMe Atlas — Universal Mobile Navigation, TOC Drawer & Global Command Palette (Ctrl+K) */
(function(){
  if(window.__minimeAtlasUiLoaded) return;
  window.__minimeAtlasUiLoaded = true;

  var ITEMS = [
    {t:"Overview (Home)", u:"index.html", c:"Atlas Core", k:"home overview kpi dashboard start"},
    {t:"The MiniMe Book — All 14 Chapters", u:"docs.html", c:"Connected Book", k:"docs book chapters guides library reading"},
    {t:"Ch. 1 · Financial & Model Strategy Rulebook", u:"doc-rulebook.html", c:"Part I · Strategy", k:"rulebook pricing tiers basic moderate ultimate models groq gemini deepseek anthropic openai budget hiring equity"},
    {t:"Ch. 2 · Technical Implementation Roadmap (Tech-A → Tech-H)", u:"doc-tech-roadmap.html", c:"Part I · Strategy", k:"tech-a tech-b tech-c tech-d tech-e tech-f tech-g tech-h brain monitor instrumentation"},
    {t:"Ch. 3 · Server Management & Splitting Guide", u:"doc-server-guide.html", c:"Part I · Strategy", k:"server split docker postgres redis worker vps hetzner"},
    {t:"Ch. 4 · MiniMe — Complete Feature & Product Guide", u:"doc-minime-feature-guide.html", c:"Part II · MiniMe Web", k:"minime feature guide chat notebooks research plan build test growth role library cad knowledge graph"},
    {t:"Ch. 5 · MiniMake — Complete Feature & Product Guide", u:"doc-minimake-feature-guide.html", c:"Part III · MiniMake", k:"minimake feature guide cli tui terminal coding agent bubblewrap sandbox tools checkpoints"},
    {t:"Ch. 6 · MiniMake Build Execution Guide (64 WPs)", u:"doc-minimake-plan.html", c:"Part III · MiniMake", k:"minimake build plan work packages waves b00 p00 s01 minicore"},
    {t:"Ch. 7 · MiniMake Product & Build Guide (Initial Spec)", u:"doc-minimake-product.html", c:"Part III · MiniMake", k:"minimake initial product spec design note overrides"},
    {t:"Ch. 8 · MiniMate — Complete Feature & Product Guide", u:"doc-minimate-feature-guide.html", c:"Part IV · MiniMate", k:"minimate feature guide automation node cron triggers approvals t0 t5 telegram email calendar vault playwright"},
    {t:"Ch. 9 · MiniMate Build Execution Guide (59 WPs)", u:"doc-minimate-plan.html", c:"Part IV · MiniMate", k:"minimate build execution guide work packages waves mt-k00 mt-i01"},
    {t:"Ch. 10 · MiniMate Product & Build Guide (Initial Spec)", u:"doc-minimate-product.html", c:"Part IV · MiniMate", k:"minimate initial product spec design note overrides"},
    {t:"Ch. 11 · FBEBC Research Program Guide", u:"doc-fbebc-program.html", c:"Part V · FBEBC", k:"fbebc research program bacterial colony funsearch stage 1 stage 2"},
    {t:"Ch. 12 · FBEBC Phase 1 Implementation Guide", u:"doc-fbebc-phase1.html", c:"Part V · FBEBC", k:"fbebc phase 1 barrier implementation spec"},
    {t:"Ch. 13 · FBEBC Preprint / Workshop Paper Guide", u:"doc-fbebc-paper.html", c:"Part V · FBEBC", k:"fbebc paper preprint claims c0 c3 wilcoxon"},
    {t:"Ch. 14 · FBEBC Live Build & Run Status", u:"doc-fbebc-status.html", c:"Part V · FBEBC", k:"fbebc status tests bug fixes d1 d4 capset"},
    {t:"Roadmap — Master Timeline & Critical Path", u:"roadmap.html", c:"Plan & Tracking", k:"roadmap timeline gantt plan actual swimlanes gates"},
    {t:"To-do — Team Kanban, List, Calendar & Activity", u:"todo.html", c:"Plan & Tracking", k:"todo tasks kanban board calendar team sync"},
    {t:"Journey — Interactive Section-by-Section Book Map", u:"journey.html", c:"Plan & Tracking", k:"journey path sections progress chips"},
    {t:"Progress — Tech-A to Tech-H vs Codebase", u:"progress.html", c:"Plan & Tracking", k:"progress tech phases source files"},
    {t:"Build — Work Package Checklists (MiniMake, MiniMate, FBEBC)", u:"build.html", c:"Plan & Tracking", k:"build work packages wps checklist export"},
    {t:"Decisions — 86 Golden Rules & Architectural Locks", u:"decisions.html", c:"Plan & Tracking", k:"decisions golden rules lock"},
    {t:"Consistency — Cross-Book Governance & Sync Matrix", u:"consistency.html", c:"Plan & Tracking", k:"consistency sync contradictions governance"},
    {t:"Explore — Global File, Function, Route & Guide Search", u:"explore.html", c:"Codebase Atlas", k:"explore search graph files functions routes"},
    {t:"Map — Codebase Treemap by Lines / Churn / Recency", u:"map.html", c:"Codebase Atlas", k:"map treemap lines of code"},
    {t:"Files — Full Repository File Inventory", u:"code.html", c:"Codebase Atlas", k:"files code inventory"},
    {t:"Functions — 3,262 Functions & Classes", u:"functions.html", c:"Codebase Atlas", k:"functions classes methods"},
    {t:"Graph — 752-Node Knowledge Graph Communities", u:"graph.html", c:"Codebase Atlas", k:"graph communities nodes edges"},
    {t:"API — 174 FastAPI Endpoints", u:"api.html", c:"Codebase Atlas", k:"api routes endpoints fastapi"},
    {t:"Agents — 73 Agent Modules & 46 Router Roles", u:"agents.html", c:"Codebase Atlas", k:"agents roles model router"},
    {t:"Data Model — 15 Public Tables & 11 Migrations", u:"data.html", c:"Codebase Atlas", k:"data database tables schema migrations postgres"},
    {t:"Infra — Docker, Env Vars & Provider Key Pool", u:"infra.html", c:"Codebase Atlas", k:"infra docker env keys"},
    {t:"History — Git Velocity & Commit Timeline", u:"history.html", c:"Codebase Atlas", k:"history git commits"},
    {t:"Architecture — Visual System Diagrams", u:"architecture.html", c:"Codebase Atlas", k:"architecture diagrams"},
    {t:"Tests — 785 Automated Tests & Coverage", u:"tests.html", c:"Quality & Money", k:"tests unit integration security"},
    {t:"Health — Largest Files, Hotspots & Audit Risks", u:"health.html", c:"Quality & Money", k:"health audit risks complexity"},
    {t:"Finance — Pricing, Margins, Scenarios & Runway", u:"finance.html", c:"Quality & Money", k:"finance money revenue burn runway"},
    {t:"Rulebook Summary — 15 Golden Rules & Model Roster", u:"rulebook.html", c:"Quality & Money", k:"rulebook summary rules models"},
    {t:"Tables — All 172 Searchable Book Tables", u:"tables.html", c:"Connected Book", k:"tables search reference"}
  ];

  function init(){
    var nav = document.querySelector('nav');
    var main = document.querySelector('main');
    var toc = document.querySelector('.toc');
    if(!nav || !main) return;

    // 1. Wrap #edit table on roadmap.html in .tw if not wrapped
    var editTbl = document.getElementById('edit');
    if(editTbl && (!editTbl.parentElement || !editTbl.parentElement.classList.contains('tw'))){
      var tw = document.createElement('div');
      tw.className = 'tw';
      editTbl.parentNode.insertBefore(tw, editTbl);
      tw.appendChild(editTbl);
    }

    // 2. Wrap wide SVGs in .svg-scroll for crisp touch panning on mobile
    document.querySelectorAll('main svg').forEach(function(svg){
      var vb = (svg.getAttribute('viewBox') || '').split(/[\s,]+/);
      var w = parseFloat(vb[2] || '0');
      if(w >= 650 && svg.parentElement && !svg.parentElement.classList.contains('svg-scroll') && !svg.parentElement.classList.contains('svg-wrap')){
        var wrap = document.createElement('div');
        wrap.className = 'svg-scroll';
        svg.parentNode.insertBefore(wrap, svg);
        wrap.appendChild(svg);
      }
    });

    // 3. Inject Quick-Jump button inside desktop/mobile <nav> right below .logo
    var logo = nav.querySelector('.logo');
    if(logo && !nav.querySelector('.nav-qjump')){
      var qbtn = document.createElement('button');
      qbtn.className = 'nav-qjump';
      qbtn.type = 'button';
      qbtn.innerHTML = '<span>⌕ Quick Jump</span><kbd>Ctrl+K</kbd>';
      qbtn.addEventListener('click', openPalette);
      logo.insertAdjacentElement('afterend', qbtn);

      // Mobile close button inside nav
      var cbtn = document.createElement('button');
      cbtn.className = 'nav-mclose';
      cbtn.type = 'button';
      cbtn.setAttribute('aria-label', 'Close menu');
      cbtn.innerHTML = '✕ Close';
      cbtn.addEventListener('click', closeDrawers);
      logo.appendChild(cbtn);
    }

    // 4. Create Sticky Mobile Top Bar (.m-topbar) & Backdrop (.m-backdrop)
    var h1 = main.querySelector('h1');
    var pageTitle = h1 ? h1.textContent.trim() : document.title.replace(/\s*-\s*MiniMe Atlas.*$/, '');

    var topbar = document.createElement('header');
    topbar.className = 'm-topbar';
    topbar.innerHTML =
      '<button type="button" class="m-btn m-menu-btn" aria-label="Open navigation menu">☰ <span>Menu</span></button>' +
      '<a href="index.html" class="m-brand">Mini<b>Me</b> · <small>' + escapeHtml(pageTitle.slice(0, 28)) + '</small></a>' +
      '<div class="m-right">' +
        (toc ? '<button type="button" class="m-btn m-toc-btn" aria-label="Table of contents">§ <span>Contents</span></button>' : '') +
        '<button type="button" class="m-btn m-search-btn" aria-label="Quick search">⌕</button>' +
      '</div>';
    document.body.insertBefore(topbar, document.body.firstChild);

    var backdrop = document.createElement('div');
    backdrop.className = 'm-backdrop';
    backdrop.addEventListener('click', closeDrawers);
    document.body.appendChild(backdrop);

    topbar.querySelector('.m-menu-btn').addEventListener('click', function(){
      var open = !document.body.classList.contains('nav-open');
      closeDrawers();
      if(open) document.body.classList.add('nav-open');
    });

    topbar.querySelector('.m-search-btn').addEventListener('click', openPalette);

    if(toc){
      // Add mobile header inside .toc
      var tocHdr = document.createElement('div');
      tocHdr.className = 'toc-mhdr';
      tocHdr.innerHTML = '<b>Chapter Contents</b><button type="button" class="toc-mclose">✕ Close</button>';
      toc.insertBefore(tocHdr, toc.firstChild);
      tocHdr.querySelector('.toc-mclose').addEventListener('click', closeDrawers);

      var tocBtn = topbar.querySelector('.m-toc-btn');
      if(tocBtn){
        tocBtn.addEventListener('click', function(){
          var open = !document.body.classList.contains('toc-open');
          closeDrawers();
          if(open) document.body.classList.add('toc-open');
        });
      }
      toc.addEventListener('click', function(e){
        if(e.target.closest('a')) closeDrawers();
      });
    }

    nav.addEventListener('click', function(e){
      if(e.target.closest('a')) closeDrawers();
    });

    // 5. Floating Back-to-Top button
    var btt = document.createElement('button');
    btt.type = 'button';
    btt.className = 'm-btt';
    btt.title = 'Back to top';
    btt.innerHTML = '↑';
    btt.addEventListener('click', function(){ window.scrollTo({top:0, behavior:'smooth'}); });
    document.body.appendChild(btt);
    window.addEventListener('scroll', function(){
      btt.classList.toggle('vis', window.scrollY > 450);
    }, {passive:true});

    // 6. Global Keyboard Shortcuts (Ctrl+K / Cmd+K / Escape)
    document.addEventListener('keydown', function(e){
      if((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k'){
        e.preventDefault();
        openPalette();
      } else if(e.key === 'Escape'){
        closeDrawers();
        closePalette();
      }
    });
  }

  function closeDrawers(){
    document.body.classList.remove('nav-open', 'toc-open');
  }

  var palEl = null;
  function buildPalette(){
    if(palEl) return palEl;
    palEl = document.createElement('div');
    palEl.className = 'cmd-modal';
    palEl.innerHTML =
      '<div class="cmd-box">' +
        '<div class="cmd-top">' +
          '<span>⌕</span>' +
          '<input type="search" id="cmd-inp" placeholder="Jump to any book chapter, page, or topic (e.g. MiniMake, Rulebook, T0-T5, FBEBC)...">' +
          '<button type="button" class="cmd-esc">Esc</button>' +
        '</div>' +
        '<div class="cmd-list" id="cmd-list"></div>' +
      '</div>';
    palEl.addEventListener('click', function(e){
      if(e.target === palEl || e.target.classList.contains('cmd-esc')) closePalette();
    });
    document.body.appendChild(palEl);

    var inp = palEl.querySelector('#cmd-inp');
    inp.addEventListener('input', function(){ renderPaletteList(inp.value); });
    inp.addEventListener('keydown', function(e){
      if(e.key === 'Enter'){
        var first = palEl.querySelector('.cmd-item');
        if(first) window.location.href = first.getAttribute('href');
      }
    });
    return palEl;
  }

  function renderPaletteList(q){
    var s = (q || '').toLowerCase().trim();
    var list = document.getElementById('cmd-list');
    if(!list) return;
    var matches = ITEMS.filter(function(it){
      if(!s) return true;
      return (it.t + ' ' + it.c + ' ' + it.k).toLowerCase().includes(s);
    }).slice(0, 18);
    if(!matches.length){
      list.innerHTML = '<div style="padding:14px;color:var(--dim);font-size:13px">No direct page match. <a href="explore.html#' + encodeURIComponent(s) + '">Search "' + escapeHtml(s) + '" in Code &amp; Guide Explorer →</a></div>';
      return;
    }
    list.innerHTML = matches.map(function(it){
      return '<a class="cmd-item" href="' + it.u + '">' +
        '<div><b>' + escapeHtml(it.t) + '</b><small>' + escapeHtml(it.u) + '</small></div>' +
        '<span class="pill">' + escapeHtml(it.c) + '</span>' +
      '</a>';
    }).join('');
  }

  function openPalette(){
    closeDrawers();
    var el = buildPalette();
    el.classList.add('open');
    var inp = document.getElementById('cmd-inp');
    inp.value = '';
    renderPaletteList('');
    setTimeout(function(){ inp.focus(); }, 20);
  }

  function closePalette(){
    if(palEl) palEl.classList.remove('open');
  }

  function escapeHtml(s){
    return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
