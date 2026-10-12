(() => {
  "use strict";

  const DATA = window.DEVOXX || { talks: [] };
  // Framed (e.g. published as a claude.ai artifact): the sandbox blocks YouTube embeds and
  // third-party images, so link out to YouTube and use initials instead of speaker photos.
  const EMBED = window.self === window.top;
  const TZ = "Europe/Brussels";
  const talks = DATA.talks
    .filter((t) => t.type !== "Keynote Overflow")
    .map((t) => ({ ...t, blob: searchBlob(t) }));
  const byId = new Map(talks.map((t) => [t.id, t]));

  const $ = (sel, root = document) => root.querySelector(sel);
  const el = (tag, attrs = {}, ...kids) => {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v == null || v === false) continue;
      if (k === "class") node.className = v;
      else if (k === "text") node.textContent = v;
      else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v === true ? "" : v);
    }
    for (const kid of kids.flat()) if (kid != null && kid !== false) node.append(kid);
    return node;
  };

  // ---------- formatting ----------
  const fmt = (opts) => new Intl.DateTimeFormat("en-GB", { timeZone: TZ, ...opts });
  const fTime = fmt({ hour: "2-digit", minute: "2-digit" });
  const fDayKey = fmt({ year: "numeric", month: "2-digit", day: "2-digit" });
  const fWeekday = fmt({ weekday: "long" });
  const fShortDay = fmt({ weekday: "short", day: "numeric" });
  const fLongDate = fmt({ day: "numeric", month: "long" });
  const time = (iso) => fTime.format(new Date(iso));
  const dayKey = (iso) => fDayKey.format(new Date(iso));
  const speakerNames = (t) => t.speakers.map((s) => s.name).join(", ");
  const themesOf = (t) => (t.s && t.s.themes) || [];
  const toSeconds = (at) => {
    const [m, s] = String(at).split(":").map(Number);
    return (m || 0) * 60 + (s || 0);
  };

  function searchBlob(t) {
    const s = t.s || {};
    return [t.title, t.track, t.type, t.room, ...(t.keywords || []),
      ...t.speakers.flatMap((p) => [p.name, p.company]),
      s.tldr, ...(s.tech || []), ...(s.themes || [])]
      .filter(Boolean).join(" ").toLowerCase();
  }

  // ---------- theme (lights) ----------
  const root = document.documentElement;
  const lightsBtn = $("#lights");
  const storage = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch { /* storage unavailable */ } },
  };
  const isLight = () => root.dataset.theme
    ? root.dataset.theme === "light"
    : matchMedia("(prefers-color-scheme: light)").matches;
  function syncLights() {
    lightsBtn.textContent = isLight() ? "Lights down" : "Lights up";
    lightsBtn.setAttribute("aria-pressed", String(isLight()));
  }
  const savedTheme = storage.get("dvx-theme");
  if (savedTheme) root.dataset.theme = savedTheme;
  syncLights();
  lightsBtn.addEventListener("click", () => {
    root.dataset.theme = isLight() ? "dark" : "light";
    storage.set("dvx-theme", root.dataset.theme);
    syncLights();
  });

  // ---------- marquee ----------
  function seeded(n) {
    const x = Math.sin(n * 9301 + 49297) * 233280;
    return x - Math.floor(x);
  }
  function tileLine(node, text, startDelay) {
    node.textContent = "";
    let i = 0;
    for (const word of text.split(" ")) {
      const w = el("span", { class: "word", "aria-hidden": "true" });
      for (const ch of word) {
        const r = seeded(i + startDelay * 100);
        const tile = el("span", { class: "tile", text: ch });
        tile.style.setProperty("--rot", `${((r - 0.5) * 3).toFixed(2)}deg`);
        tile.style.setProperty("--dy", `${((seeded(i + 7) - 0.5) * 0.05).toFixed(3)}em`);
        tile.style.setProperty("--delay", `${(startDelay + i * 0.045).toFixed(3)}s`);
        w.append(tile);
        i++;
      }
      node.append(w);
    }
    return i;
  }
  const recorded = talks.filter((t) => t.videoId).length;
  const n = tileLine($("#board-letters"), "Devoxx Belgium 2026", 0.15);
  tileLine($("#board-sub"), `${talks.length} talks summarised`, 0.15 + n * 0.045 + 0.1);
  requestAnimationFrame(() => $("#marquee").classList.add("is-lit"));

  const rooms = new Set(talks.map((t) => t.room).filter(Boolean));
  const days = [...new Set(talks.filter((t) => t.start).map((t) => dayKey(t.start)))].sort();
  $("#hero-facts").append(
    el("span", {}, el("strong", { text: String(recorded) }), " recordings, with chapters you can jump to"), el("br"),
    el("span", {}, el("strong", { text: String(talks.length - recorded) }), " more summarised from their abstracts"), el("br"),
    el("span", {}, el("strong", { text: String(days.length) }), " days in ", el("strong", { text: String(rooms.size) }), " rooms"),
  );

  // ---------- recap ----------
  if (DATA.recap && DATA.recap.trends && DATA.recap.trends.length) {
    $("#recap").hidden = false;
    $("#recap-intro").textContent = DATA.recap.intro || "";
    const box = $("#trends");
    for (const tr of DATA.recap.trends) {
      const linked = (tr.talkIds || []).map((id) => byId.get(id)).filter(Boolean);
      box.append(el("article", { class: "trend" },
        el("h3", { text: tr.title }),
        tr.count ? el("p", { class: "trend-count", text: `${tr.count} talks touched on this` }) : null,
        el("p", { text: tr.body }),
        el("ul", { class: "trend-talks" }, linked.map((t) =>
          el("li", {}, el("a", { href: `#talk-${t.id}`, text: `${t.title}, ${speakerNames(t)}` })))),
      ));
    }
  } else {
    document.querySelector('.topbar a[href="#recap"]').remove();
  }

  // ---------- favourites ----------
  const favs = [...talks].sort((a, b) => b.favourites - a.favourites).slice(0, 10);
  $("#fav-list").append(...favs.map((t) => el("li", {},
    el("a", { href: `#talk-${t.id}` },
      el("span", {},
        el("span", { class: "fav-title", text: t.title }),
        el("span", { class: "fav-meta", text: `${speakerNames(t)}, ${t.favourites} bookmarks` }))))));

  // ---------- not on YouTube yet ----------
  const NOT_FILMED = new Set(["Hands-on Lab", "BOF"]);
  const missing = talks.filter((t) => !t.videoId)
    .sort((a, b) => (a.start || "").localeCompare(b.start || ""));
  const missingRecorded = missing.filter((t) => !NOT_FILMED.has(t.type));
  const missingUnfilmed = missing.filter((t) => NOT_FILMED.has(t.type));
  const checked = DATA.videosCheckedAt ? fLongDate.format(new Date(`${DATA.videosCheckedAt}T12:00:00Z`)) : null;
  $("#missing-intro").textContent = `${missing.length} of ${talks.length} sessions have no recording on the Devoxx YouTube channel`
    + (checked ? ` as of ${checked}.` : ".")
    + " Their summaries come from the abstract instead.";
  function missingByDay(list) {
    const filmedTotal = (d) => talks.filter((t) => !NOT_FILMED.has(t.type) && t.start && dayKey(t.start) === d).length;
    const counts = new Map();
    for (const t of list) counts.set(dayKey(t.start), (counts.get(dayKey(t.start)) || 0) + 1);
    const parts = [...counts.entries()].sort((a, b) => b[1] - a[1]).map(([d, c]) => {
      const iso = list.find((t) => dayKey(t.start) === d).start;
      return `${c} of ${filmedTotal(d)} on ${fWeekday.format(new Date(iso))}`;
    });
    return parts.length ? `Sessions that are normally filmed: ${parts.join(", ")}. The channel uploads day by day, so most of these are probably still in the queue.` : "";
  }
  const missingRow = (t) => el("li", {}, el("a", { href: `#talk-${t.id}` },
    el("span", { class: "m-title", text: t.title }),
    el("span", { class: "m-who", text: `${speakerNames(t)}, ${t.type}` }),
    el("span", { class: "m-when", text: t.start ? `${fShortDay.format(new Date(t.start))}, ${time(t.start)}` : "" })));
  $("#missing-cols").append(
    el("div", {}, el("h3", { text: `Recordings still missing (${missingRecorded.length})` }),
      el("p", { class: "missing-note", text: missingByDay(missingRecorded) }),
      el("ol", { class: "missing-list" }, missingRecorded.map(missingRow))),
    el("div", {}, el("h3", { text: `Labs and BOFs (${missingUnfilmed.length})` }),
      el("p", { class: "missing-note", text: "Hands-on labs and birds-of-a-feather sessions usually aren't filmed." }),
      el("ol", { class: "missing-list" }, missingUnfilmed.map(missingRow))));

  // ---------- filters ----------
  const state = { q: "", day: "all", theme: "", format: "", recording: "", sort: "time" };
  const daysBox = $("#days");
  const dayButtons = [["all", "All days"], ...days.map((d) => {
    const iso = talks.find((t) => t.start && dayKey(t.start) === d).start;
    return [d, fShortDay.format(new Date(iso))];
  })].map(([value, label]) => {
    const b = el("button", { type: "button", "aria-pressed": String(value === "all"), text: label,
      onclick: () => { state.day = value; render(); } });
    b.dataset.value = value;
    daysBox.append(b);
    return b;
  });

  const countBy = (fn) => {
    const m = new Map();
    for (const t of talks) for (const k of [].concat(fn(t))) if (k) m.set(k, (m.get(k) || 0) + 1);
    return [...m.entries()].sort((a, b) => b[1] - a[1]);
  };
  const themeSel = $("#theme");
  themeSel.append(el("option", { value: "", text: "All themes" }),
    ...countBy(themesOf).map(([k, c]) => el("option", { value: k, text: `${k} (${c})` })));
  const formatSel = $("#format");
  formatSel.append(el("option", { value: "", text: "All formats" }),
    ...countBy((t) => t.type).map(([k, c]) => el("option", { value: k, text: `${k} (${c})` })));

  let qTimer;
  $("#q").addEventListener("input", (e) => {
    clearTimeout(qTimer);
    qTimer = setTimeout(() => { state.q = e.target.value.trim().toLowerCase(); render(); }, 120);
  });
  themeSel.addEventListener("change", (e) => { state.theme = e.target.value; render(); });
  formatSel.addEventListener("change", (e) => { state.format = e.target.value; render(); });
  $("#sort").addEventListener("change", (e) => { state.sort = e.target.value; render(); });
  $("#recording").addEventListener("change", (e) => { state.recording = e.target.value; render(); });

  function filtered() {
    const terms = state.q.split(/\s+/).filter(Boolean);
    const list = talks.filter((t) =>
      (state.day === "all" || (t.start && dayKey(t.start) === state.day)) &&
      (!state.theme || themesOf(t).includes(state.theme)) &&
      (!state.format || t.type === state.format) &&
      (!state.recording || (state.recording === "yes") === Boolean(t.videoId)) &&
      terms.every((w) => t.blob.includes(w)));
    const roomNo = (t) => parseInt((t.room || "").replace(/\D/g, ""), 10) || 99;
    return state.sort === "fav"
      ? list.sort((a, b) => b.favourites - a.favourites)
      : list.sort((a, b) => (a.start || "").localeCompare(b.start || "") || roomNo(a) - roomNo(b));
  }

  // ---------- listing ----------
  function ticket(t) {
    const [roomWord, roomNum] = (t.room || "").split(" ");
    return el("a", { class: "ticket", href: `#talk-${t.id}` },
      el("div", { class: "stub" },
        el("span", { class: "stub-room" }, roomWord, roomNum ? el("b", { text: roomNum }) : null),
        el("span", { class: "stub-len", text: `${t.duration} min` }),
        t.videoId ? el("span", { class: "stub-play", title: "Recording available" },
          el("span", { class: "visually-hidden", text: "Recording available" })) : null),
      el("div", { class: "ticket-body" },
        el("h4", { class: "ticket-title", text: t.title }),
        el("p", { class: "ticket-who", text: speakerNames(t) }),
        t.s && t.s.tldr ? el("p", { class: "ticket-tldr", text: t.s.tldr }) : null,
        el("div", { class: "ticket-tags" },
          t.type !== "Conference" ? el("span", { class: "tag is-format", text: t.type }) : null,
          themesOf(t).slice(0, 2).map((th) => el("span", { class: "tag", text: th })))));
  }

  let currentOrder = [];
  function render() {
    for (const b of dayButtons) b.setAttribute("aria-pressed", String(b.dataset.value === state.day));
    const list = filtered();
    currentOrder = list.map((t) => t.id);
    const listing = $("#listing");
    listing.textContent = "";
    $("#count").textContent = list.length === talks.length
      ? `Showing all ${list.length} sessions.`
      : `${list.length} of ${talks.length} sessions match.`;

    if (!list.length) {
      listing.append(el("div", { class: "empty" },
        el("p", { text: "No session matches these filters." }),
        el("button", { type: "button", text: "Clear filters", onclick: resetFilters })));
      return;
    }
    if (state.sort === "fav") {
      listing.append(el("div", { class: "flat" }, el("div", { class: "slot-talks" }, list.map(ticket))));
      return;
    }
    const groups = new Map();
    for (const t of list) {
      const d = dayKey(t.start);
      if (!groups.has(d)) groups.set(d, new Map());
      const slots = groups.get(d);
      if (!slots.has(t.start)) slots.set(t.start, []);
      slots.get(t.start).push(t);
    }
    for (const [, slots] of groups) {
      const first = slots.values().next().value[0].start;
      const section = el("section", { class: "day" },
        el("h3", { class: "day-title" }, fWeekday.format(new Date(first)),
          el("small", { text: fLongDate.format(new Date(first)) })));
      for (const [start, group] of slots) {
        const ends = group.map((t) => t.end).sort();
        section.append(el("div", { class: "slot" },
          el("div", { class: "slot-time" }, time(start), el("small", { text: `until ${time(ends[ends.length - 1])}` })),
          el("div", { class: "slot-talks" }, group.map(ticket))));
      }
      listing.append(section);
    }
  }
  function resetFilters() {
    Object.assign(state, { q: "", day: "all", theme: "", format: "", recording: "" });
    $("#q").value = ""; themeSel.value = ""; formatSel.value = ""; $("#recording").value = "";
    render();
  }

  // ---------- the screen (talk detail) ----------
  const dialog = $("#screen");
  const body = $("#screen-body");
  let openedFromPage = false;

  const ytUrl = (t, seconds = 0) => `https://www.youtube.com/watch?v=${t.videoId}${seconds ? `&t=${seconds}s` : ""}`;

  function playerFor(t) {
    if (!t.videoId) {
      return el("div", { class: "player player-empty" },
        el("div", {}, el("strong", { text: "No recording yet" }),
          el("span", { text: "This summary is based on the session abstract. Devoxx usually uploads late recordings within a few weeks." })));
    }
    if (!EMBED) {
      return el("a", { class: "player player-link", href: ytUrl(t), target: "_blank", rel: "noopener" },
        el("span", { class: "player-link-cta", text: "Watch on YouTube" }),
        el("span", { class: "player-link-note", text: (t.s && t.s.chapters && t.s.chapters.length)
          ? "The recording opens in a new tab. Chapters and quotes below open it at that moment."
          : "The recording opens in a new tab." }));
    }
    const box = el("div", { class: "player" });
    const play = (start) => {
      box.textContent = "";
      box.append(el("iframe", {
        src: `https://www.youtube-nocookie.com/embed/${t.videoId}?autoplay=1&rel=0&start=${start}`,
        title: t.title, allow: "autoplay; encrypted-media; picture-in-picture; fullscreen", allowfullscreen: true,
      }));
    };
    box.play = play;
    box.append(
      el("img", { src: `https://i.ytimg.com/vi/${t.videoId}/hqdefault.jpg`, alt: "", loading: "lazy" }),
      el("button", { type: "button", "aria-label": `Play ${t.title}`, onclick: () => play(0) }));
    return box;
  }

  // A control that jumps to a moment: plays inline when embedding, otherwise opens YouTube there.
  function seekTo(t, at, player, cls, ...kids) {
    const seconds = toSeconds(at);
    if (!t.videoId) return el("button", { type: "button", class: cls, disabled: true }, ...kids);
    if (!EMBED) return el("a", { class: cls, href: ytUrl(t, seconds), target: "_blank", rel: "noopener" }, ...kids);
    return el("button", { type: "button", class: cls,
      onclick: () => { player.play(seconds); player.scrollIntoView({ behavior: "smooth", block: "start" }); } }, ...kids);
  }

  function avatar(sp) {
    const initials = sp.name.split(/\s+/).map((p) => p[0]).slice(0, 2).join("");
    if (!sp.image || !EMBED) return el("span", { class: "avatar", text: initials });
    const img = el("img", { class: "avatar", src: sp.image, alt: "", loading: "lazy", referrerpolicy: "no-referrer" });
    img.addEventListener("error", () => img.replaceWith(el("span", { class: "avatar", text: initials })));
    return img;
  }

  function screenFor(t) {
    const s = t.s || {};
    const player = playerFor(t);
    const when = t.start ? `${fWeekday.format(new Date(t.start))} ${time(t.start)}` : null;
    const section = (title, ...kids) => el("section", {}, el("h3", { text: title }), ...kids);

    const main = el("div", { class: "feature-main" },
      s.summary && s.summary.length ? section("The story", el("div", { class: "prose" }, s.summary.map((p) => el("p", { text: p })))) : null,
      s.keyPoints && s.keyPoints.length ? section("Key points", el("ul", { class: "points" }, s.keyPoints.map((p) => el("li", { text: p })))) : null,
      s.takeaways && s.takeaways.length ? el("section", { class: "monday" }, el("h3", { text: "Try this on Monday" }),
        el("ol", {}, s.takeaways.map((p) => el("li", { text: p })))) : null,
      s.quotes && s.quotes.length ? section("Heard on stage", el("div", { class: "quotes" }, s.quotes.map((q) =>
        el("blockquote", { class: "quote" }, el("p", { text: q.text }),
          el("footer", {}, seekTo(t, q.at, player, "seek", `at ${q.at}`)))))) : null,
      t.abstract.length ? el("details", { class: "abstract" }, el("summary", { text: "Original abstract" }),
        t.abstract.map((p) => el("p", { text: p }))) : null,
    );

    const aside = el("aside", { class: "feature-aside" },
      s.watchIf ? el("div", { class: "watch" }, el("h3", { text: "Watch it if" }), el("p", { text: s.watchIf })) : null,
      s.chapters && s.chapters.length ? section("Chapters", el("ol", { class: "chapters" }, s.chapters.map((c) =>
        el("li", {}, seekTo(t, c.at, player, "chapter", el("time", { text: c.at }), el("span", { text: c.title })))))) : null,
      s.tech && s.tech.length ? section("Mentioned", el("div", { class: "chips" }, s.tech.map((x) => el("span", { class: "tag", text: x })))) : null,
      section(t.speakers.length > 1 ? "Speakers" : "Speaker", el("div", { class: "speakers" }, t.speakers.map((sp) =>
        el("div", { class: "speaker" }, avatar(sp), el("div", {},
          el("b", { text: sp.name }), sp.company ? el("span", { text: sp.company }) : null,
          sp.bio ? el("details", {}, el("summary", { text: "Bio" }), el("p", { text: sp.bio })) : null))))),
      el("p", { class: "source-note", text: s.source === "transcript"
        ? "Summarised from a machine transcript of the recording. Check the video before quoting it."
        : "Summarised from the official abstract, so it describes what the session set out to cover." }),
      t.videoId ? el("p", {}, el("a", { href: ytUrl(t), target: "_blank", rel: "noopener", text: "Open on YouTube" })) : null,
    );

    return el("div", { class: "feature" },
      player,
      el("header", { class: "feature-head" },
        el("div", { class: "feature-meta" },
          el("span", { class: "tag is-format", text: `${t.type}, ${t.duration} min` }),
          t.track ? el("span", { class: "tag", text: t.track }) : null,
          when ? el("span", { class: "tag", text: `${when}, ${t.room}` }) : null,
          s.demo ? el("span", { class: "tag", text: "Live demo" }) : null),
        el("h2", { class: "feature-title", id: "screen-title", text: t.title }),
        el("p", { class: "feature-who" }, el("strong", { text: speakerNames(t) }),
          t.speakers.some((sp) => sp.company) ? `, ${[...new Set(t.speakers.map((sp) => sp.company).filter(Boolean))].join(", ")}` : ""),
        s.tldr ? el("p", { class: "tldr", text: s.tldr }) : null),
      el("div", { class: "feature-grid" }, main, aside));
  }

  function openTalk(id) {
    const t = byId.get(id);
    if (!t) return closeTalk();
    body.textContent = "";
    body.append(screenFor(t));
    const order = currentOrder.includes(id) ? currentOrder : talks.map((x) => x.id);
    const i = order.indexOf(id);
    const nav = (a, target) => {
      a.setAttribute("aria-disabled", String(target == null));
      a.href = target == null ? "#" : `#talk-${target}`;
    };
    nav($("#prev"), i > 0 ? order[i - 1] : null);
    nav($("#next"), i < order.length - 1 ? order[i + 1] : null);
    document.title = `${t.title}, Devoxx Programme 2026`;
    if (!dialog.open) {
      dialog.showModal();
      document.body.classList.add("modal-open");
    }
    dialog.scrollTop = 0;
    $("#close").focus({ focusVisible: false });
  }

  function closeTalk() {
    if (dialog.open) dialog.close();
    document.body.classList.remove("modal-open");
    body.textContent = ""; // stops playback
    document.title = "Devoxx Programme 2026";
  }

  function leaveTalk() {
    if (openedFromPage) history.back();
    else {
      history.replaceState(null, "", location.pathname + location.search);
      closeTalk();
    }
  }

  function route() {
    const m = location.hash.match(/^#talk-(\d+)$/);
    if (m) openTalk(Number(m[1]));
    else closeTalk();
  }

  document.addEventListener("click", (e) => {
    const a = e.target.closest('a[href^="#talk-"]');
    if (a && !dialog.contains(a)) openedFromPage = true;
  });
  $("#close").addEventListener("click", leaveTalk);
  // Previous/next replace the history entry so "Back to programme" always closes the screen.
  for (const a of [$("#prev"), $("#next")]) {
    a.addEventListener("click", (e) => {
      e.preventDefault();
      if (a.getAttribute("aria-disabled") === "true") return;
      history.replaceState(null, "", a.getAttribute("href"));
      route();
    });
  }
  dialog.addEventListener("cancel", (e) => { e.preventDefault(); leaveTalk(); });
  window.addEventListener("hashchange", route);

  render();
  route();
})();
