/* Three Inks: the cinema's hall-screen menu, the week as a risograph proof (design/menu-round3/three-inks, John 22/10).
   One sheet per shape, made once and kept: unmounted for a walk and mounted again on the way back, so you come back to
   where you were. WATCH IT on a talk's card calls watch(id); walks(id) says whether that talk has a seat to walk to. */
const made = new Map();
export function inksMenu({ phone, watch, walks, textHref }) {
  if (made.has(phone)) return made.get(phone);
  const root = make({ phone, watch, walks, textHref });
  made.set(phone, root);
  return root;
}
function make({ phone, watch, walks, textHref }) {
  const M = window.MENU;
  const clean = (s) => String(s || "").replace(/[\p{Extended_Pictographic}\uFE0F\u200D]/gu, "").replace(/\s{2,}/g, " ").trim();
  const TALKS = M.talks.filter((t) => t.type !== "Keynote Overflow").map((t) => ({ ...t, title: clean(t.title) }));
  const N = TALKS.length;
  const esc0 = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const root = document.createElement("main");
  root.className = `face inks sheet printing${phone ? " is-phone" : ""}`;
  root.setAttribute("aria-label", `Devoxx Belgium 2026: ${N} talks, summarised in eight verdicts. The week printed in three inks.`);
  root.innerHTML = ((esc) => `
  <section class="band band-pink" id="band-pink">
    <p class="eyebrow">Devoxx Belgium 2026 &middot; ${N} talks, summarised</p>
    <h1 class="bh"><button class="band-open" data-story="pink" aria-label="Coding agents took a third of the week: 63 talks. Open the coding agents story, 4 verdicts (key 1)"><span class="headline" id="headline">Coding agents took <br>a third of the week.</span><span class="count">4 verdicts</span></button></h1>
  </section>
  <div class="tools">
    <label class="isearch sheet-search" for="search">
      <svg viewBox="0 0 24 24" fill="none" stroke="#111" stroke-width="2.6" stroke-linecap="round" aria-hidden="true"><circle cx="10" cy="10" r="6.5"/><path d="M15 15l6 6"/></svg>
      <input id="search" type="search" placeholder="Search talks, speakers, topics" aria-label="Search ${N} talks (key /)" autocomplete="off" spellcheck="false" enterkeyhint="search">
    </label>
    <button class="iprog" id="prog" data-act="programme" aria-label="Programme: the talks day by day (key P)"><span>Programme</span></button>
    <button class="watch" id="watch" data-act="picks" aria-label="Watch first: eight talks, one per verdict (key W)"><span class="wt">Watch first</span><span class="ws">8 picks</span></button>
  </div>
  <section class="band band-blue" id="band-blue">
    <h2 class="bh"><button class="band-open" data-story="blue" aria-label="Java: leaner and faster, 39 talks. Open the Java story, 2 verdicts (key 2)"><span class="title">Java</span><span class="find">Leaner and faster.</span><span class="count">2 verdicts</span></button></h2>
  </section>
  <section class="band band-yellow" id="band-yellow">
    <h2 class="bh"><button class="band-open" data-story="yellow" aria-label="Architecture and people: clear boundaries, kept skills, 61 talks. Open the story, 2 verdicts (key 3)"><span class="title">Architecture &amp; people</span><span class="find">Clear boundaries, kept skills.</span><span class="count">2 verdicts</span></button></h2>
  </section>
  <footer class="band band-paper" id="foot"></footer>
  <a class="itextlink" href="${esc(textHref)}">Text version</a>
  <section id="opened" hidden aria-live="polite"></section>
  <div id="toast" role="status" aria-live="polite"></div>
  <div class="grain" aria-hidden="true"></div>
`)(esc0);
  const $ = (s, el) => (el || root).querySelector(s);
  const $$ = (s, el) => Array.from((el || root).querySelectorAll(s));
  const menu = root, opened = $("#opened"), toast = $("#toast");
  const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const PHONE = !!phone;

  // ---- the inks: which track prints in which ink; which verdicts belong to which storyline of the intro
  const TRACK_INK = {
    "Agentic Engineering & Tooling": "pink",
    "Java Language & Platform": "blue",
    "Architecture & Modernization": "yellow", "Development Practices": "yellow", "People, Practices & Career": "yellow",
  };
  const inkOf = (t) => TRACK_INK[t.track] || "paper";
  const INK_NAME = { pink: "Coding agents", blue: "Java", yellow: "Architecture & people", paper: "Other tracks" };
  const STORIES = {
    pink: { word: "Coding agents", verdicts: [0, 1, 2, 3], count: 63,
      standfirst: "Most talks asked less what agents can do than how to check, review and contain them." },
    blue: { word: "Java", verdicts: [4, 5], count: 39,
      standfirst: "A runtime that keeps getting leaner and faster: compact object headers, Leyden's AOT cache, Valhalla value classes." },
    yellow: { word: "Architecture & people", verdicts: [6, 7], count: 61,
      standfirst: "Clear boundaries, and keeping the skills that AI makes easy to skip." },
  };
  const INKS = ["pink", "blue", "yellow"];
  const storyOfVerdict = (i) => INKS.find((k) => STORIES[k].verdicts.includes(i));
  const byId = new Map(TALKS.map((t) => [t.id, t]));
  const pickIds = new Set(M.picks.map((p) => p.talkId));
  const PAGE = 4;   // watch first shows four picks at a time
  // the programme's five days (the sheet no longer carries them: one Programme button opens Monday with these as tabs)
  const DAYS = [["2026-10-05", "Mon 5", "Monday 5 October"], ["2026-10-06", "Tue 6", "Tuesday 6 October"], ["2026-10-07", "Wed 7", "Wednesday 7 October"],
    ["2026-10-08", "Thu 8", "Thursday 8 October"], ["2026-10-09", "Fri 9", "Friday 9 October"]];

  const PLACEHOLDER = PHONE ? `Search ${N} talks` : "Search talks, speakers, topics";
  $("#search").placeholder = PLACEHOLDER;
  // attendee star ratings from the Devoxx app, once Devoxx publishes them (scripts/fetch_metrics.py picks them up daily)
  const RATED = !!(M.signals && M.signals.hasRatings);
  const S = { view: "sheet", story: null, verdict: null, day: null, q: "", sort: RATED ? "rating" : "views", page: 0, sel: 0,
    hide: { pink: false, blue: false, yellow: false, paper: false }, returnFocus: null };

  // ---- helpers
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const nf = new Intl.NumberFormat("en-GB");
  const TZ = "Europe/Brussels";
  const fTime = new Intl.DateTimeFormat("en-GB", { timeZone: TZ, hour: "2-digit", minute: "2-digit", hour12: false });
  const fDayShort = new Intl.DateTimeFormat("en-GB", { timeZone: TZ, weekday: "short", day: "numeric" });
  const fDayLong = new Intl.DateTimeFormat("en-GB", { timeZone: TZ, weekday: "long", day: "numeric", month: "long" });
  const fKey = new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" });
  const dayKey = (t) => fKey.format(new Date(t.start));
  const when = (t) => `${fDayShort.format(new Date(t.start))}, ${fTime.format(new Date(t.start))}`;
  const speakers = (t) => t.speakers.map((s) => s.name).join(", ");
  const shown = (t) => !S.hide[inkOf(t)];
  const talkOfSpeaker = (name, ids) => ids.map((id) => byId.get(id)).find((t) => t && t.speakers.some((s) => s.name === name));
  // the talk's real YouTube thumbnail as a two-colour print (black and the story's ink); a flat ink block if it never arrives
  const thumb = (t, ink, big) => t.videoId
    ? `<span class="thumb ${ink}"><img src="https://i.ytimg.com/vi/${esc(t.videoId)}/${big ? "hq" : "mq"}default.jpg" alt="" width="160" height="90" decoding="async" onerror="this.parentNode.classList.add('none')"></span>`
    : `<span class="thumb ${ink} none"></span>`;
  const SEARCH_SVG = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" aria-hidden="true"><circle cx="10" cy="10" r="6.5"/><path d="M15 15l6 6"/></svg>`;

  function sorted(list) {
    const l = list.slice();
    if (S.sort === "rating") l.sort((a, b) => ((a.rating == null) - (b.rating == null)) || (b.rating - a.rating) || ((b.numRatings || 0) - (a.numRatings || 0)));
    else if (S.sort === "likeRate") l.sort((a, b) => ((a.views == null) - (b.views == null)) || ((a.thin ? 1 : 0) - (b.thin ? 1 : 0)) || (b.likeRate - a.likeRate));
    else if (S.sort === "hearts") l.sort((a, b) => b.hearts - a.hearts);
    else l.sort((a, b) => ((a.views == null) - (b.views == null)) || (b.views - a.views));
    return l;
  }
  // the right-hand column holds one number; its unit is said once, in the list head
  function signal(t) {
    if (S.sort === "rating") return t.rating == null ? `<small>not rated</small>` : `${t.rating.toFixed(2)}<small>${nf.format(t.numRatings)} ratings</small>`;
    if (t.views == null) return `<small>no video</small>`;
    if (S.sort === "likeRate") return `${t.likeRate}${t.thin ? `<small class="few">few votes</small>` : ""}`;
    if (S.sort === "hearts") return nf.format(t.hearts);
    return nf.format(t.views);
  }
  const UNIT = { rating: "stars, out of 5", views: "views", likeRate: "likes per 100 views", hearts: "schedule saves" };
  // a row is two lines: the title (one line, cut with an ellipsis) and one grey line of who, where and when
  function row(t, opts) {
    const o = opts || {};
    const meta = [speakers(t), t.room, o.noDate ? null : when(t)].filter(Boolean).join(" · ");
    const time = o.time ? `<span class="tm">${fTime.format(new Date(t.start))}</span>` : "";
    return `<li><button class="row ${inkOf(t)}${o.time ? " timed" : ""}" data-talk="${t.id}" title="${esc(t.title)}" aria-label="${esc(t.title)}, ${esc(INK_NAME[inkOf(t)])}">${time}<span class="bar" aria-hidden="true"></span><span class="t">${esc(t.title)}</span><span class="m">${pickIds.has(t.id) ? '<span class="wf">Watch first</span>' : ""}${esc(meta)}</span><span class="s">${signal(t)}</span></button></li>`;
  }
  const sortbar = () => `<div class="sortbar" role="group" aria-label="Sort the talks"><span>Sort</span>` +
    [...(RATED ? [["rating", "Best rated", "Average star rating by attendees in the Devoxx app"]] : []), ["views", "Most watched", "YouTube views of the recording"], ["likeRate", "Best liked", "YouTube likes per 100 views"],
      ["hearts", "Most anticipated", "How many attendees saved the talk in their schedule before the conference"]].map(([k, l, d]) =>
      `<button data-sort="${k}" aria-pressed="${S.sort === k}" title="${d}">${l}</button>`).join("") + `</div>`;
  // the head: the count, the sort, and over the number column its unit, as a column head
  const listhead = (count, lead) => `<div class="listhead">${lead || ""}<h3>${count}</h3>${lead ? "" : sortbar()}<span class="unit">${UNIT[S.sort]}</span></div>`;
  // the one filter: the colour key under every list. Each ink is a switch; switch one off and its talks leave the lists.
  const keyline = () => `<div class="key" role="group" aria-label="Colour key: click an ink to hide its talks"><span class="kcap">Show</span>` +
    ["pink", "blue", "yellow", "paper"].map((k) => `<button class="ink ${k}" data-ink="${k}" aria-pressed="${!S.hide[k]}"><span class="sw" aria-hidden="true"></span>${esc(INK_NAME[k])}</button>`).join("") +
    `</div>`;
  // a list is a window: about six rows, the rest scroll; the foot says how many wait below
  const listWrap = (items) => `<div class="win"><ul class="list" tabindex="-1">${items}</ul></div><div class="lfoot">${keyline()}<span class="below" aria-hidden="true"></span></div>`;

  // ---- views
  function headHTML(title) {
    const ink = inkOfView();
    const right = S.view === "index"
      ? `<label class="isearch" for="search2">${SEARCH_SVG}<span class="sr">Search ${N} talks</span><input id="search2" type="search" placeholder="${PLACEHOLDER}" autocomplete="off" spellcheck="false" value="${esc(S.q)}"></label>`
      : `<button class="searchbtn" data-act="search">${SEARCH_SVG}<span>Search</span></button>`;
    return `<div class="ohead${ink ? " " + ink : ""}"><button class="back" data-act="back"><span>Back</span><kbd>Esc</kbd></button><h2 class="otitle" tabindex="-1">${title}</h2>${right}</div>`;
  }
  function storyBody(ink) {
    const st = STORIES[ink];
    const rows = st.verdicts.map((i) => {
      const v = M.recap.trends[i];
      return `<li><button class="vrow" data-verdict="${i}"><span class="vn">${i + 1}</span><span class="vt">${esc(v.title)}</span><span class="vq">${esc(v.debate.question)}</span><span class="go" aria-hidden="true"></span></button></li>`;
    }).join("");
    return `<p class="standfirst">${esc(st.standfirst)}</p><ol class="vrows ${st.verdicts.length > 2 ? "four" : "two"}">${rows}</ol>`;
  }
  // the Valhalla verdict's stances open with a long sentence of evidence, not a claim; these are its claims in short
  const CLAIM = { 4: ["Yes: it removes Java's last layout handicap.", "Not fully: the measured limits are real."] };
  // a verdict in two zones: what the week concluded (big), then the debate on its own panel; the ways on sit at the foot
  function verdictBody(i) {
    const v = M.recap.trends[i], ink = storyOfVerdict(i), list = STORIES[ink].verdicts, at = list.indexOf(i);
    // each side is its own card: a letter, its claim (the stance's first sentence), who argued it; VS between the cards
    const sides = v.debate.sides.map((s, k) => {
      const who = s.who.map((name) => { const t = talkOfSpeaker(name, s.talkIds); return t ? `<button data-talk="${t.id}">${esc(name)}</button>` : `<span>${esc(name)}</span>`; }).join("");
      const m = /^(.*?[.!?])\s+(.*)$/s.exec(s.stance);
      const claim = (CLAIM[i] && CLAIM[i][k]) || (m ? m[1] : s.stance);
      return `<div class="side" title="${esc(s.stance)}"><span class="sl" aria-hidden="true">${"ABC"[k]}</span><p class="stance">${esc(claim)}</p><div class="who"><span class="by">Argued by</span>${who}</div></div>`;
    }).join("");
    const n = v.talkIds.filter((id) => byId.has(id)).length;
    const prev = at > 0 ? list[at - 1] : null, next = at < list.length - 1 ? list[at + 1] : null;
    return `<div class="iverdict"><div class="vtop"><h2 class="vh">${esc(v.title)}</h2><p class="consensus">${esc(v.consensus)}</p></div>` +
      `<div class="debate"><p class="lbl">The debate</p><p class="question">${esc(v.debate.question)}</p><div class="sides n${v.debate.sides.length}">${sides}</div></div>` +
      `<div class="vfoot"><button class="primary" data-act="talks">See its ${n} talks</button><span class="vpos">Verdict ${i + 1} of 8</span>` +
      `<span class="pager">${prev != null ? `<button class="pg prev" data-verdict="${prev}" aria-label="Previous verdict: ${esc(M.recap.trends[prev].title)}">Previous</button>` : ""}` +
      `${next != null ? `<button class="pg next" data-verdict="${next}" aria-label="Next verdict: ${esc(M.recap.trends[next].title)}">Next verdict</button>` : ""}</span></div></div>`;
  }
  function talksBody(i) {
    const v = M.recap.trends[i];
    const all = v.talkIds.map((id) => byId.get(id)).filter(Boolean), talks = sorted(all.filter(shown));
    const items = talks.map((t) => row(t)).join("") || `<li class="iempty">Every talk of this verdict is in an ink you switched off. Switch it back on below.</li>`;
    return listhead(`${talks.length} talks`) + listWrap(items);
  }
  const pickOf = (p) => { const i = M.recap.trends.findIndex((v) => v.title === p.verdict); return { ink: storyOfVerdict(i), t: byId.get(p.talkId) }; };
  // watch first on the wall: four short rows (verdict, title) on the left, the one under the pointer or focus on the
  // right with its picture, where and when, and why. On the phone each pick is one card in a scrolling column.
  function pickDetail(n) {
    const p = M.picks[n]; if (!p) return "";
    const { ink, t } = pickOf(p); if (!t) return "";
    return `${thumb(t, ink, true)}<p class="dv"><span class="sw" aria-hidden="true"></span>${esc(p.verdict)}</p><h3 class="dt">${esc(t.title)}</h3>` +
      `<p class="dm">${esc(speakers(t))} &middot; ${esc(t.room)} &middot; ${esc(when(t))}</p><p class="dw">${esc(p.why)}</p>` +
      `<button class="primary" data-talk="${t.id}">Watch it</button>`;
  }
  function picksBody() {
    const a = S.page * PAGE, page = M.picks.slice(a, a + PAGE);
    const pages = Math.ceil(M.picks.length / PAGE), b = Math.min(M.picks.length, a + PAGE);
    const pager = `<div class="ppager"><button class="pg prev" data-act="pprev"${S.page === 0 ? " disabled" : ""}>Previous</button><span class="pos">Picks ${a + 1}&ndash;${b} of ${M.picks.length}</span><button class="pg next" data-act="pnext"${S.page >= pages - 1 ? " disabled" : ""}>Next picks</button></div>`;
    if (PHONE) {
      const cells = page.map((p) => {
        const { ink, t } = pickOf(p); if (!t) return "";
        return `<li class="pk ${ink}">${thumb(t, ink)}<div class="pkt"><span class="v"><span class="sw" aria-hidden="true"></span>${esc(p.verdict)}</span><button class="pt" data-talk="${t.id}">${esc(t.title)}</button><span class="pm">${esc(speakers(t))} &middot; ${esc(t.room)} &middot; ${esc(when(t))}</span><span class="pw">${esc(p.why)}</span></div></li>`;
      }).join("");
      return `<ol class="picks" start="${a + 1}">${cells}</ol>${pager}`;
    }
    if (S.sel < a || S.sel >= b) S.sel = a;
    const rows = page.map((p, k) => {
      const { ink, t } = pickOf(p); if (!t) return "";
      return `<li><button class="prow pt ${ink}" data-talk="${t.id}" data-pick="${a + k}"${a + k === S.sel ? ' aria-current="true"' : ""}><span class="v"><span class="sw" aria-hidden="true"></span>${esc(p.verdict)}</span><span class="ptt">${esc(t.title)}</span></button></li>`;
    }).join("");
    return `<div class="pgrid"><ol class="picks plist" start="${a + 1}">${rows}</ol><div class="pdetail" aria-live="polite">${pickDetail(S.sel)}</div></div>${pager}`;
  }
  function selectPick(n) {
    if (S.view !== "picks" || PHONE || n === S.sel) return;
    S.sel = n;
    const d = $(".pdetail", opened); if (d) d.innerHTML = pickDetail(n);
    $$(".prow", opened).forEach((r) => r.toggleAttribute("aria-current", Number(r.dataset.pick) === n));
  }
  function hay(t) {
    return [t.title, t.speakers.map((s) => s.name + " " + (s.company || "")).join(" "), (t.keywords || []).join(" "), (t.themes || []).join(" "), t.tldr || "", t.track || ""].join(" ").toLowerCase();
  }
  function indexBody() {
    const terms = S.q.trim().toLowerCase().split(/\s+/).filter(Boolean);
    const hits = sorted(TALKS.filter(shown).filter((t) => terms.every((q) => hay(t).includes(q))));
    if (!hits.length) return `<div class="iempty"><p class="big">Nothing printed for &ldquo;${esc(S.q.trim())}&rdquo;.</p><p>Try a speaker's name or a topic:</p><div class="tries">${["MCP", "Valhalla", "testing"].map((w) => `<button data-try="${w}">${w}</button>`).join("")}</div>${INKS.some((k) => S.hide[k]) || S.hide.paper ? `<p>Some inks are switched off.</p>${keyline()}` : ""}</div>`;
    return listhead(`${hits.length} of ${N} talks`) + listWrap(hits.map((t) => row(t)).join(""));
  }
  function dayBody(day) {
    const count = (d) => TALKS.filter((t) => dayKey(t) === d).length;
    const tabs = DAYS.map(([d, short, long]) => `<button class="day" data-day="${d}"${d === day ? ' aria-current="date"' : ""} aria-label="${long}, ${count(d)} talks">${short}</button>`).join("");
    const talks = TALKS.filter((t) => dayKey(t) === day && shown(t)).sort((a, b) => a.start.localeCompare(b.start) || a.room.localeCompare(b.room, "en", { numeric: true }));
    const items = talks.map((t) => row(t, { noDate: true, time: true })).join("") || `<li class="iempty">Every talk of this day is in an ink you switched off.</li>`;
    return listhead(`${talks.length} talks`, `<div class="idays" role="group" aria-label="Programme by day">${tabs}</div>`) + listWrap(items);
  }

  function titleOf() {
    if (S.view === "story") return esc(STORIES[S.story].word);
    if (S.view === "verdict") return esc(STORIES[storyOfVerdict(S.verdict)].word);
    if (S.view === "talks") return esc(M.recap.trends[S.verdict].title);
    if (S.view === "picks") return "Watch first";
    if (S.view === "index") return "Search";
    if (S.view === "day") return (PHONE ? fDayShort : fDayLong).format(new Date(S.day + "T12:00:00Z")) + (PHONE ? " Oct" : "");
    return "";
  }
  function bodyOf() {
    if (S.view === "story") return storyBody(S.story);
    if (S.view === "verdict") return verdictBody(S.verdict);
    if (S.view === "talks") return talksBody(S.verdict);
    if (S.view === "picks") return picksBody();
    if (S.view === "index") return indexBody();
    if (S.view === "day") return dayBody(S.day);
    return "";
  }
  function inkOfView() {
    if (S.view === "story") return S.story;
    if (S.view === "verdict" || S.view === "talks") return storyOfVerdict(S.verdict);
    if (S.view === "picks") return "orange";
    return null;
  }

  function show(view, params, focusSel) {
    hidePeek(true);
    Object.assign(S, params || {}, { view });
    if (view === "sheet") {
      opened.hidden = true; opened.innerHTML = ""; opened.className = "";
      $("#search").value = S.q;
      const rf = S.returnFocus; S.returnFocus = null;
      if (rf && document.contains(rf)) rf.focus(); else $(".band-open").focus();
      return;
    }
    const ink = inkOfView();
    const wasHidden = opened.hidden;
    opened.className = ink ? `ink-${ink}` : "";
    opened.dataset.view = view;
    opened.innerHTML = headHTML(titleOf()) + `<div class="obody">${bodyOf()}</div>`;
    opened.hidden = false;
    if (wasHidden && !REDUCED) { void opened.offsetWidth; opened.classList.add("flood"); }   // the sheet floods in from the right
    after();
    const first = focusSel ? pick(focusSel)
      : view === "index" ? $("#search2", opened) : view === "picks" ? $(".pt", opened) : view === "story" ? $(".vrow", opened)
      : view === "talks" ? $(".list .row", opened) : $(".otitle", opened);
    if (first) { first.focus({ preventScroll: true }); if (first.id === "search2") { const n = first.value.length; first.setSelectionRange(n, n); } }
  }
  function pick(sel) { for (const s of sel.split("|")) { const e = $(s, opened); if (e) return e; } return $(".otitle", opened); }
  function rerender(focusSel) {            // the body only: the search input keeps its focus and caret
    if (S.view === "sheet") return;
    hidePeek(true);
    const b = $(".obody", opened); if (b) b.innerHTML = bodyOf();
    after();
    if (focusSel) { const f = pick(focusSel); if (f) f.focus({ preventScroll: true }); }
  }
  function after() {
    const body = $(".obody", opened); if (body) body.scrollTop = 0;
    const list = $(".win .list", opened);
    if (list) { list.scrollTop = 0; fitWin(); list.addEventListener("scroll", below, { passive: true }); below(); }
  }
  // on the wall the window ends on a whole row, never a row cut in half; the rest scroll inside it
  function fitWin() {
    const win = $(".win", opened); if (!win || PHONE) return;
    win.style.flex = ""; win.style.height = "";
    const list = $(".list", win), avail = list.clientHeight;
    if (list.scrollHeight <= avail + 1) return;
    let h = 0;
    for (const li of list.children) { const b = li.offsetTop + li.offsetHeight; if (b <= avail + 1) h = b; else break; }
    if (h) { win.style.flex = "none"; win.style.height = h + 6 + "px"; }
  }
  // "N more below" under a list window, counted from the rows past its lower edge
  function below() {
    const list = $(".win .list", opened), tag = $(".below", opened);
    if (!list || !tag) return;
    const edge = list.getBoundingClientRect().bottom;
    const n = $$(".row", list).filter((r) => r.getBoundingClientRect().bottom > edge + 2).length;
    tag.textContent = n ? `${n} more below, scroll` : "";
    list.parentNode.classList.toggle("has-more", n > 0);
  }

  function back() {
    if (S.view === "sheet") return;
    if (S.view === "talks") { show("verdict", null, ".primary"); return; }
    if (S.view === "verdict") { const v = S.verdict; show("story", { story: storyOfVerdict(v) }, `.vrow[data-verdict="${v}"]`); return; }
    show("sheet");
  }
  function step(d) {     // previous / next inside a verdict's story, or a page of picks
    if (S.view === "verdict") {
      const list = STORIES[storyOfVerdict(S.verdict)].verdicts, j = list.indexOf(S.verdict) + d;
      if (j >= 0 && j < list.length) show("verdict", { verdict: list[j] }, d > 0 ? ".pg.next|.pg.prev" : ".pg.prev|.pg.next");
    } else if (S.view === "picks") {
      const p = S.page + d;
      if (p >= 0 && p < Math.ceil(M.picks.length / PAGE)) { S.page = p; rerender(d > 0 ? "[data-act=pnext]:not(:disabled)|[data-act=pprev]" : "[data-act=pprev]:not(:disabled)|[data-act=pnext]"); }
    }
  }

  // ---- open a talk: the cinema walks you there (or opens its summary)
  const openTalk = (id) => watch(Number(id));


  // ---- the talk card: clicking a talk anywhere opens a printed card with what you need to choose it, and WATCH IT
  // confirms the walk to its room (or opens its summary). A modal on the wall, a sheet from the bottom on the phone.
  const peek = document.createElement("div");
  peek.id = "peek"; peek.hidden = true;
  menu.appendChild(peek);
  let peekFrom = null;
  const dur = (m) => m >= 60 ? `${Math.floor(m / 60)} h${m % 60 ? " " + (m % 60) + " min" : ""}` : `${m} min`;
  const LEVEL = { BEGINNER: "Beginner", INTERMEDIATE: "Intermediate", ADVANCED: "Advanced" };
  function peekHTML(t) {
    const ink = inkOf(t);
    const stars = t.rating != null ? `<span><b>${t.rating.toFixed(2)}</b> stars from ${nf.format(t.numRatings)} attendees</span>` : "";
    const stats = t.views == null ? `${stars}<span>No recording yet</span>`
      : `${stars}<span><b>${nf.format(t.views)}</b> views</span><span><b>${t.likeRate}</b> likes per 100 views${t.thin ? " (few votes)" : ""}</span><span><b>${nf.format(t.hearts)}</b> schedule saves</span>`;
    return `<div class="scrim" data-act="unpeek"></div><div class="tcard ${ink}" role="dialog" aria-modal="true" aria-labelledby="peek-t">` +
      `<div class="ph"><span class="ty">${esc(t.type)} &middot; ${dur(t.minutes)} &middot; ${esc(LEVEL[t.level] || t.level)}</span>${pickIds.has(t.id) ? '<span class="wf">Watch first</span>' : ""}</div>` +
      `<div class="pin"><div class="pm1"><div class="pid"><h3 id="peek-t">${esc(t.title)}</h3><p class="by">${t.speakers.map((s) => `${esc(s.name)}${s.company ? ` <span>${esc(s.company)}</span>` : ""}`).join(", ")}</p>` +
      `<p class="where">${esc(t.room)} &middot; ${esc(when(t))}</p></div>${thumb(t, ink, true)}</div>` +
      `<p class="sum">${esc(t.tldr)}</p><p class="if"><b>Watch if</b>${esc(t.watchIf)}</p><div class="stats">${stats}</div>` +
      `<div class="pact"><button class="primary" data-talk="${t.id}" data-go="1">Watch it</button><span class="gonote">${walks(t.id) ? `Walks you to ${esc(t.room)}` : "Opens the summary"}</span>` +
      `<button class="pg close" data-act="unpeek">Close<kbd>Esc</kbd></button></div></div></div>`;
  }
  const peekOpen = () => !peek.hidden;
  function showPeek(el) {
    const t = byId.get(Number(el.dataset.talk)); if (!t) return;
    peekFrom = el;
    peek.innerHTML = peekHTML(t);
    peek.hidden = false; peek.classList.remove("on");
    void peek.offsetWidth; peek.classList.add("on");
    $(".primary", peek).focus({ preventScroll: true });
  }
  function hidePeek(now, refocus) {
    if (!peekOpen()) return;
    const from = peekFrom; peekFrom = null;
    const done = () => { peek.hidden = true; peek.innerHTML = ""; peek.classList.remove("on", "off"); };
    if (now || REDUCED) done(); else { peek.classList.add("off"); setTimeout(done, 160); }
    if (refocus && from && document.contains(from)) from.focus({ preventScroll: true });
  }
  // Tab stays inside the card while it is open
  peek.addEventListener("keydown", (e) => {
    if (e.key !== "Tab") return;
    const f = $$("button", peek); if (!f.length) return;
    const i = f.indexOf(document.activeElement);
    e.preventDefault(); f[(i + (e.shiftKey ? f.length - 1 : 1)) % f.length].focus();
  });

  // ---- events
  menu.addEventListener("click", (e) => {
    const el = e.target.closest("[data-story],[data-verdict],[data-talk],[data-act],[data-day],[data-sort],[data-ink],[data-try]");
    if (!el || !menu.contains(el)) return;
    if (el.dataset.act === "unpeek") { hidePeek(false, true); return; }
    if (el.dataset.talk) {
      if (!el.dataset.go && !el.closest(".pdetail")) { showPeek(el); return; }   // a talk opens its card first; WATCH IT confirms
      hidePeek(false, true); openTalk(el.dataset.talk); return;
    }
    if (el.dataset.sort) { S.sort = el.dataset.sort; rerender(`[data-sort="${S.sort}"]`); return; }
    if (el.dataset.ink) { S.hide[el.dataset.ink] = !S.hide[el.dataset.ink]; rerender(`[data-ink="${el.dataset.ink}"]`); return; }
    if (el.dataset.try) { S.q = el.dataset.try; const s = $("#search2", opened); if (s) s.value = S.q; rerender(); if (s) s.focus(); return; }
    const a = el.dataset.act;
    if (a === "back") { back(); return; }
    if (a === "search") { show("index"); return; }
    if (a === "talks") { show("talks"); return; }
    if (a === "pprev") { step(-1); return; }
    if (a === "pnext") { step(1); return; }
    if (S.view === "sheet") S.returnFocus = el;
    if (el.dataset.story) { show("story", { story: el.dataset.story }); return; }
    if (el.dataset.verdict) { const pg = el.classList.contains("pg"); show("verdict", { verdict: Number(el.dataset.verdict) }, pg ? (el.classList.contains("next") ? ".pg.next|.pg.prev" : ".pg.prev|.pg.next") : null); return; }
    if (a === "picks") { show("picks", { page: 0, sel: 0 }); return; }
    if (a === "programme") { show("day", { day: DAYS[0][0] }); return; }
    if (el.dataset.day) { show("day", { day: el.dataset.day }, S.view === "day" ? `.day[data-day="${el.dataset.day}"]` : null); return; }
  });
  menu.addEventListener("mouseover", (e) => { const r = e.target.closest(".prow"); if (r) selectPick(Number(r.dataset.pick)); });
  menu.addEventListener("focusin", (e) => { const r = e.target.closest(".prow"); if (r) selectPick(Number(r.dataset.pick)); });
  menu.addEventListener("input", (e) => {
    if (!e.target.matches("#search, #search2")) return;
    S.q = e.target.value;
    if (S.view !== "index") { S.returnFocus = S.view === "sheet" ? $("#search") : S.returnFocus; show("index"); }
    else rerender();
  });
  menu.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && e.target.matches("#search, #search2")) {
      e.preventDefault();
      if (S.view !== "index") { S.q = e.target.value; show("index"); }
      const first = $(".list .row", opened); if (first) first.focus();
    }
  });
  document.addEventListener("keydown", (e) => {
    if (!root.isConnected) return;
    const typing = e.target.matches("input, textarea");
    if (e.key === "Escape" && peekOpen()) { e.preventDefault(); hidePeek(false, true); return; }
    if (peekOpen()) return;   // the card is modal: no shortcuts behind it
    if (e.key === "Escape") { if (typing && e.target.value && S.view === "index") { e.target.value = ""; S.q = ""; rerender(); return; } e.preventDefault(); back(); return; }
    if (e.key === "/" && !typing) { e.preventDefault(); if (S.view === "sheet" || S.view === "index") { const s = opened.hidden ? $("#search") : $("#search2"); s.focus(); s.select(); } else show("index"); return; }
    if (typing || e.altKey || e.ctrlKey || e.metaKey) return;
    if (e.key === "w" || e.key === "W") { e.preventDefault(); if (S.view !== "picks") { if (S.view === "sheet") S.returnFocus = document.activeElement; show("picks", { page: 0, sel: 0 }); } return; }
    if (e.key === "p" || e.key === "P") { e.preventDefault(); if (S.view !== "day") { if (S.view === "sheet") S.returnFocus = $("#prog"); show("day", { day: DAYS[0][0] }); } return; }
    if ((e.key === "ArrowDown" || e.key === "ArrowUp") && S.view === "picks" && !PHONE) {
      const rows = $$(".prow", opened), i = rows.indexOf(document.activeElement);
      e.preventDefault(); const r = rows[i < 0 ? 0 : (i + (e.key === "ArrowDown" ? 1 : rows.length - 1)) % rows.length]; if (r) r.focus(); return;
    }
    if (e.key === "1" || e.key === "2" || e.key === "3") { e.preventDefault(); if (S.view === "sheet") S.returnFocus = $(`.band-open[data-story="${INKS[Number(e.key) - 1]}"]`); show("story", { story: INKS[Number(e.key) - 1] }); return; }
    if ((e.key === "ArrowLeft" || e.key === "ArrowRight") && (S.view === "verdict" || S.view === "picks")) { e.preventDefault(); step(e.key === "ArrowRight" ? 1 : -1); return; }
    if ((e.key === "ArrowDown" || e.key === "ArrowUp") && S.view === "sheet") {
      const bands = $$(".band-open"); const i = bands.indexOf(document.activeElement);
      if (i >= 0) { e.preventDefault(); bands[(i + (e.key === "ArrowDown" ? 1 : bands.length - 1)) % bands.length].focus(); }
    }
  });

  // ---- the print-in at load is CSS; hand control back to transitions once the plates are in register
  setTimeout(() => menu.classList.remove("printing"), REDUCED ? 0 : 900);
  // the eight picks' thumbnails are fetched once the sheet is printed, so Watch first prints them at once
  setTimeout(() => M.picks.forEach((p) => { const t = byId.get(p.talkId); if (t && t.videoId) { const i = new Image(); i.src = `https://i.ytimg.com/vi/${t.videoId}/hqdefault.jpg`; } }), 1200);
  return root;
}
