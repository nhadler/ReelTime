/**
 * @fileoverview Notices when one of the page's scripts can't be fetched.
 *
 * A dropped request for one script makes the browser skip it, and every
 * module that imports it, without a word: the cue grid would stay empty.
 * A request that never gets an answer is worse: nothing fails, the page
 * just never finishes loading (it waits for its scripts). Either way this
 * reloads the page to fetch them again: at once, then after a pause, as a
 * connection that just dropped may drop again. If that doesn't help, it
 * says so. Only ReelTime's own scripts count: one a browser extension or
 * a proxy adds is blocked by the CSP, and the page works without it. A
 * classic script loaded before the others, so it's listening before any
 * of them can fail.
 */

(() => {
  const KEY = 'reeltime.reloadedForScript';
  const RETRY_WINDOW = 30000;
  const MESSAGE = "Part of this page didn't load. Reload the page.";
  // The pause before each reload, in turn.
  const PAUSES = [0, 3000];
  // Where the static files are served from, e.g. https://host/static/.
  const STATIC = new URL('..', document.currentScript.src).href;
  // How long the page may take to run its scripts before one counts as
  // stuck. Generous: a first visit over a slow link fetches them all.
  const STALL_AFTER = 15000;

  let recovering = false;

  /**
   * Counts this reload. Null once the tries are used up, or when the
   * browser won't let us count, so the page can't reload over and over.
   * @return {?number} How long to wait before reloading.
   */
  function nextPause() {
    try {
      const last = JSON.parse(sessionStorage.getItem(KEY)) || {};
      const recent = Date.now() - last.at < RETRY_WINDOW;
      const tries = recent ? last.tries : 0;
      if (tries >= PAUSES.length) {
        return null;
      }
      sessionStorage.setItem(
        KEY,
        JSON.stringify({at: Date.now() + PAUSES[tries], tries: tries + 1}),
      );
      return PAUSES[tries];
    } catch {
      return null;
    }
  }

  /** Shows the message at the top of the page, once. */
  function tell() {
    const main = document.getElementById('main');
    if (!main || document.getElementById('load-guard')) {
      return;
    }
    const list = document.createElement('ul');
    list.className = 'messages';
    list.id = 'load-guard';
    const item = document.createElement('li');
    item.className = 'error';
    item.setAttribute('role', 'alert');
    item.textContent = MESSAGE;
    list.append(item);
    main.prepend(list);
  }

  /**
   * Reloads, or says the page didn't load.
   * @param {string} what What went wrong, for the console.
   */
  function recover(what) {
    console.error(`ReelTime: ${what}`);
    if (recovering) {
      return;
    }
    recovering = true;
    const pause = nextPause();
    if (pause === 0) {
      window.location.reload();
    } else if (pause !== null) {
      setTimeout(() => window.location.reload(), pause);
    } else if (document.readyState === 'loading') {
      // Not parsed yet: say it once it is. A stuck script doesn't hold
      // this up; it only holds up DOMContentLoaded.
      document.addEventListener('readystatechange', tell, {once: true});
    } else {
      tell();
    }
  }

  window.addEventListener(
    'error',
    (event) => {
      const script = event.target;
      if (
        script instanceof HTMLScriptElement &&
        script.src.startsWith(STATIC)
      ) {
        recover(`${script.src}, or a script it imports, didn't load`);
      }
    },
    true,
  );

  // DOMContentLoaded waits for every script to run; not there after
  // STALL_AFTER means one is stuck.
  const stall = setTimeout(
    () => recover('a script is taking too long to load'),
    STALL_AFTER,
  );
  document.addEventListener('DOMContentLoaded', () => clearTimeout(stall), {
    once: true,
  });
})();
