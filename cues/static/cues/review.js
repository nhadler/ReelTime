/**
 * @fileoverview The review page's player and comment box.
 *
 * The video has its own controls so comments can sit on the scrubber as
 * marks: play, frame steps, the timecode of the frame on screen, mute
 * and full screen. Positions are whole frames at the project's rate; the
 * timecode is the video's first frame's (from the server) plus the frame.
 *
 * Typing a comment pauses the video. A comment is about the frame on
 * screen unless "At" is unticked; Enter sends it, Shift+Enter breaks the
 * line. While a comment is being written (the box has the keyboard or
 * some text) it has a handle each side of the frame on screen; dragging
 * one stretches the comment over part of the video, and it then stays
 * where it was put until it's sent or reset. Reply on a comment turns
 * the box into a reply to it. Clicking a comment's timecode or its mark
 * goes to its frame. A comment about a stretch is a dot like any other,
 * and its stretch of the track is coloured while the video is inside it.
 *
 * A version can also have its audio alone, in a small player under the
 * video; playing one pauses the other, and a comment made while
 * listening to the audio is about the whole cue.
 *
 * This script runs after the video has started loading, so whatever it
 * listens for (the length arriving, an error) may already have happened:
 * each is also checked once at the end.
 */

const config = JSON.parse(document.getElementById('review-config').textContent);
const FPS = config.fps[0] / config.fps[1];
const JUMP_SECONDS = 5;

const video = document.getElementById('review-video');
const player = document.getElementById('review-player');
const seek = document.getElementById('review-seek');
const marks = document.getElementById('review-marks');
const spans = document.getElementById('review-spans');
const time = document.getElementById('review-time');
const list = document.getElementById('review-list');
const form = document.getElementById('review-form');
// A frame asked for before the video's length was known.
let pending = null;
// Whether the audio-only player was the last thing played.
let listening = false;
// The first and last frames the comment being written is about, once
// an end of its marker has been dragged; null while it follows the frame
// on screen.
let pinned = null;
// Whether the comment form, or the comment's marker, has the keyboard.
let writing = false;
// For each timed comment in the list, its stretch drawn on the track,
// or null for a comment at one frame.
let stretches = [];

/**
 * A frame count as a timecode label, e.g. 1:02:14:08, with ';' before
 * the frames and skipped labels at drop-frame rates.
 * @param {number} frames Frames since 00:00:00:00.
 * @return {string}
 */
function label(frames) {
  const nominal = config.nominal;
  let count = frames;
  if (config.dropFrame) {
    const drop = Math.floor(nominal / 15);
    const perMinute = nominal * 60 - drop;
    const perTen = nominal * 600 - 9 * drop;
    const tens = Math.floor(count / perTen);
    const rest = count % perTen;
    count += 9 * drop * tens;
    if (rest > drop) {
      count += drop * Math.floor((rest - drop) / perMinute);
    }
  }
  const pad = (value) => String(value).padStart(2, '0');
  const f = count % nominal;
  const seconds = Math.floor(count / nominal);
  const s = seconds % 60;
  const m = Math.floor(seconds / 60) % 60;
  const h = Math.floor(seconds / 3600);
  return `${h}:${pad(m)}:${pad(s)}${config.dropFrame ? ';' : ':'}${pad(f)}`;
}

/**
 * The frame on screen at a time in the video.
 * @param {number} seconds
 * @return {number}
 */
function frameAt(seconds) {
  return Math.max(0, Math.floor(seconds * FPS + 0.01));
}

/** @return {boolean} Whether the video's length is known yet. */
function known() {
  return Number.isFinite(video.duration) && video.duration > 0;
}

/** @return {number} The video's last frame (0 until its length is known). */
function lastFrame() {
  return known() ? Math.max(0, frameAt(video.duration) - 1) : 0;
}

/**
 * The frame on screen: never past the last one, where the video rests
 * when it ends.
 * @return {number}
 */
function position() {
  const frame = frameAt(video.currentTime);
  return known() ? Math.min(frame, lastFrame()) : frame;
}

/**
 * Shows a frame: the middle of it, so rounding can't land on the one
 * before. Before the video's length is known the frame is kept and
 * shown once it is.
 * @param {number} frame
 */
function show(frame) {
  listening = false;
  showAt();
  if (!known()) {
    pending = Math.max(0, frame);
    return;
  }
  const target = Math.min(Math.max(0, frame), lastFrame());
  video.currentTime = (target + 0.5) / FPS;
}

/** Updates the timecode, the scrubber and the comment box's "At". */
function update() {
  const frame = pending ?? position();
  const text = label(config.firstFrame + frame);
  if (time.value !== text) {
    time.value = text;
    seek.value = String(frame);
    seek.setAttribute('aria-valuetext', text);
    showDraft();
    highlight(frame);
  }
}

/**
 * @return {!Array<number>} The first and last frames a comment sent now
 *     would be about: the same frame twice unless it was stretched.
 */
function span() {
  const frame = pending ?? position();
  return pinned ?? [frame, frame];
}

/** @return {boolean} Whether the comment being written is a timed one. */
function placed() {
  const field = document.getElementById('review-timed-field');
  return Boolean(
    field && !field.hidden && document.getElementById('review-timed').checked,
  );
}

/**
 * @return {boolean} Whether a comment is being written: the form has
 *     the keyboard, the box some text, or the comment was stretched.
 */
function started() {
  const body = document.getElementById('review-body');
  return writing || pinned !== null || Boolean(body.value.trim());
}

/**
 * Says in the comment box what the comment is about, and while one is
 * being written puts its handles there on the timeline.
 */
function showDraft() {
  const at = document.getElementById('review-at');
  if (!at) {
    return;
  }
  const [from, to] = span();
  const texts = [from, to].map((frame) => label(config.firstFrame + frame));
  at.textContent = to > from ? texts.join(' – ') : texts[0];
  const last = lastFrame();
  const draft = document.getElementById('review-draft');
  draft.hidden = !last || !placed() || !started();
  draft.classList.toggle('is-pinned', pinned !== null);
  draft.style.setProperty('--at', String(from / (last || 1)));
  draft.style.setProperty('--to', String(to / (last || 1)));
  for (const [edge, id] of ['review-from', 'review-to'].entries()) {
    const handle = document.getElementById(id);
    handle.setAttribute('aria-valuemax', String(last));
    handle.setAttribute('aria-valuenow', String([from, to][edge]));
    handle.setAttribute('aria-valuetext', texts[edge]);
  }
  document.getElementById('review-unpin').hidden = pinned === null;
  document.getElementById('review-hint').hidden = draft.hidden;
}

/**
 * Keeps the comment where it was put, or with null lets it follow the
 * frame on screen again.
 * @param {?Array<number>} range Its first and last frames.
 */
function pin(range) {
  pinned = range;
  showDraft();
}

/**
 * Moves one end of the comment's marker to a frame, never past the
 * other end, and shows that frame.
 * @param {number} edge 0 for its start, 1 for its end.
 * @param {number} frame
 */
function stretch(edge, frame) {
  const [from, to] = span();
  const at = Math.min(Math.max(0, frame), lastFrame());
  video.pause();
  pin(edge ? [from, Math.max(at, from)] : [Math.min(at, to), to]);
  show(pinned[edge]);
}

/**
 * Marks the comments the video is at: every one about a stretch the
 * frame is inside (its stretch then shows on the track), and the
 * last one at a frame at or before it, for the two seconds after.
 * @param {number} frame
 */
function highlight(frame) {
  let latest = null;
  const items = list.querySelectorAll('[data-frame]');
  for (const [index, item] of items.entries()) {
    const at = Number(item.dataset.frame);
    const end = item.dataset.end;
    const inside = Boolean(end) && at <= frame && frame <= Number(end);
    item.classList.toggle('is-current', inside);
    stretches[index]?.classList.toggle('is-current', inside);
    if (!end && at <= frame && frame - at < 2 * FPS) {
      latest = item;
    }
  }
  latest?.classList.add('is-current');
}

/**
 * Draws each timed comment as a dot over the scrubber, and for one
 * about a stretch that stretch of the track, which shows while the
 * video is inside it.
 */
function drawMarks() {
  const last = lastFrame();
  marks.replaceChildren();
  spans.replaceChildren();
  stretches = [];
  if (!last) {
    return;
  }
  for (const item of list.querySelectorAll('[data-frame]')) {
    const frame = Math.min(Number(item.dataset.frame), last);
    const mark = document.createElement('button');
    mark.type = 'button';
    mark.className = 'review-scrub__mark';
    mark.classList.toggle(
      'is-resolved',
      item.classList.contains('is-resolved'),
    );
    mark.tabIndex = -1;
    mark.title = item.dataset.summary;
    mark.style.setProperty('--at', String(frame / last));
    mark.addEventListener('click', () => show(frame));
    marks.append(mark);
    let stretch = null;
    if (item.dataset.end) {
      const end = Math.min(Number(item.dataset.end), last);
      stretch = document.createElement('span');
      stretch.className = 'review-scrub__span';
      stretch.style.setProperty('--at', String(frame / last));
      stretch.style.setProperty('--to', String(end / last));
      spans.append(stretch);
    }
    stretches.push(stretch);
  }
  highlight(pending ?? position());
}

/** Plays or pauses. */
function toggle() {
  if (video.paused) {
    video.play().catch(() => {});
  } else {
    video.pause();
  }
}

/** Mutes or unmutes. */
function mute() {
  video.muted = !video.muted;
}

/** Enters or leaves full screen: the player with its controls. */
function fullScreen() {
  if (document.fullscreenElement) {
    document.exitFullscreen();
  } else if (player.requestFullscreen) {
    player.requestFullscreen().catch(() => {});
  } else {
    // iPhone: only the video itself can go full screen.
    video.webkitEnterFullscreen?.();
  }
}

/**
 * Steps frames from the one on screen, pausing first.
 * @param {number} frames
 */
function step(frames) {
  video.pause();
  show((pending ?? position()) + frames);
  update();
}

/** The video's length is known (or has changed): size what depends on it. */
function sized() {
  if (!known()) {
    return;
  }
  seek.max = String(lastFrame());
  drawMarks();
  if (pending !== null) {
    const frame = pending;
    pending = null;
    show(frame);
  }
  showDraft();
  update();
}

/**
 * Shows or hides the comment box's "At" and the comment's marker: only
 * the video has frames. A stretch that was set goes with them.
 */
function showAt() {
  const field = document.getElementById('review-timed-field');
  if (field) {
    field.hidden =
      listening ||
      player.classList.contains('is-broken') ||
      Boolean(document.getElementById('review-parent').value);
    pin(field.hidden ? null : pinned);
  }
}

/** The video can't play: say so, with nothing to comment "at". */
function broken() {
  document.getElementById('review-video-error').hidden = false;
  player.classList.add('is-broken');
  showAt();
}

video.addEventListener('loadedmetadata', sized);
video.addEventListener('durationchange', sized);
video.addEventListener('timeupdate', update);
video.addEventListener('seeked', update);
video.addEventListener('click', toggle);
video.addEventListener('error', broken);
video.addEventListener('play', () => {
  listening = false;
  showAt();
});
for (const name of ['play', 'pause', 'volumechange']) {
  video.addEventListener(name, () => {
    player.classList.toggle('is-playing', !video.paused);
    player.classList.toggle('is-muted', video.muted);
    const play = document.getElementById('review-play');
    play.setAttribute('aria-label', video.paused ? 'Play' : 'Pause');
    document
      .getElementById('review-mute')
      .setAttribute('aria-pressed', String(video.muted));
  });
}
// Between timeupdate events (four a second) while playing, follow each
// frame the browser shows, where it can say.
if ('requestVideoFrameCallback' in video) {
  const follow = () => {
    update();
    video.requestVideoFrameCallback(follow);
  };
  video.requestVideoFrameCallback(follow);
}

seek.addEventListener('input', () => show(Number(seek.value)));
const BUTTONS = {
  'review-play': toggle,
  'review-back': () => step(-1),
  'review-forward': () => step(1),
  'review-mute': mute,
  'review-full': fullScreen,
};
for (const [id, action] of Object.entries(BUTTONS)) {
  document.getElementById(id).addEventListener('click', (event) => {
    action();
    // After a mouse click the button would keep the keyboard, and Space
    // would press it again instead of playing.
    if (event.detail > 0) {
      event.currentTarget.blur();
    }
  });
}

// Keys held down repeat; these act once per press.
const ONCE = new Set([' ', 'k', 'm', 'f']);
const KEYS = {
  ' ': toggle,
  k: toggle,
  arrowleft: () => step(-1),
  arrowright: () => step(1),
  j: () => (video.currentTime -= JUMP_SECONDS),
  l: () => (video.currentTime += JUMP_SECONDS),
  m: mute,
  f: fullScreen,
};

/**
 * Whether a key belongs to what has focus rather than to the player:
 * anything typed into, a slider's own arrows, a button's Space or Enter.
 * @param {!KeyboardEvent} event
 * @return {boolean}
 */
function ownKey(event) {
  const target = event.target;
  if (!(target instanceof Element)) {
    return false;
  }
  const kind = target.matches('input') ? target.type : '';
  if (
    target.closest('textarea, select, [contenteditable]') ||
    (kind && !['range', 'checkbox', 'button'].includes(kind))
  ) {
    return true;
  }
  if (kind === 'range') {
    return event.key.startsWith('Arrow');
  }
  return (
    Boolean(target.closest('button, a, summary, input')) &&
    (event.key === ' ' || event.key === 'Enter')
  );
}

document.addEventListener('keydown', (event) => {
  // Letters whatever Caps Lock says.
  const key = event.key.toLowerCase();
  const action = KEYS[key];
  if (
    !action ||
    event.ctrlKey ||
    event.metaKey ||
    event.altKey ||
    ownKey(event) ||
    document.querySelector('dialog[open]')
  ) {
    return;
  }
  event.preventDefault();
  if (!(event.repeat && ONCE.has(key))) {
    action();
  }
});

// Comments: go to one's frame; redraw the marks when the list changes.
list.addEventListener('click', (event) => {
  const button = event.target.closest('[data-seek]');
  if (button) {
    video.pause();
    show(Number(button.dataset.seek));
  }
});
list.addEventListener('htmx:afterSwap', drawMarks);
// A refresh says which list it has, and gets nothing back while that's
// still the one. None is sent while a question is open over the page:
// the button that asked it would be replaced before the answer.
list.addEventListener('htmx:configRequest', (event) => {
  if (event.detail.verb !== 'get' || event.detail.elt !== list) {
    return;
  }
  if (document.querySelector('dialog[open]')) {
    event.preventDefault();
    return;
  }
  const stamp = list.querySelector('[data-stamp]')?.dataset.stamp;
  if (stamp) {
    event.detail.parameters.stamp = stamp;
  }
});

/**
 * Says under the comment box why something sent from the page failed.
 * @param {!CustomEvent} event htmx:responseError or htmx:sendError.
 */
function failed(event) {
  const told = document.getElementById('review-form-error');
  if (!told || event.detail.requestConfig?.verb === 'get') {
    return; // refreshes fail quietly and try again
  }
  const status = event.detail.xhr?.status;
  told.textContent =
    {
      403: 'This page is out of date. Reload it and try again.',
      404: 'This link no longer works. Reload the page.',
      429: 'Too many at once. Wait a minute and try again.',
    }[status] ?? "That couldn't be sent. Check your connection and try again.";
}
document.body.addEventListener('htmx:responseError', failed);
document.body.addEventListener('htmx:sendError', failed);

if (form) {
  const body = document.getElementById('review-body');
  const timed = document.getElementById('review-timed');
  const frame = document.getElementById('review-frame');
  const end = document.getElementById('review-end');
  const draft = document.getElementById('review-draft');
  document
    .getElementById('review-unpin')
    .addEventListener('click', () => pin(null));
  // A comment on the whole cue has no place on the timeline.
  timed.addEventListener('change', () => pin(null));
  // The ends of the comment's marker: dragged, or moved a frame at a
  // time with the arrow keys (a second with Shift).
  for (const [edge, id] of ['review-from', 'review-to'].entries()) {
    const handle = document.getElementById(id);
    // How far from the end's own frame the handle was taken hold of.
    let held = 0;
    const under = (x) => {
      const box = draft.getBoundingClientRect();
      return Math.round(((x - held - box.left) / box.width) * lastFrame());
    };
    handle.addEventListener('pointerdown', (event) => {
      if (event.button !== 0) {
        return;
      }
      event.preventDefault();
      const box = draft.getBoundingClientRect();
      held =
        event.clientX - box.left - (span()[edge] / lastFrame()) * box.width;
      handle.setPointerCapture(event.pointerId);
      handle.focus();
    });
    handle.addEventListener('pointermove', (event) => {
      if (handle.hasPointerCapture(event.pointerId)) {
        stretch(edge, under(event.clientX));
      }
    });
    handle.addEventListener('keydown', (event) => {
      const by = {ArrowLeft: -1, ArrowDown: -1, ArrowRight: 1, ArrowUp: 1}[
        event.key
      ];
      if (!by || event.ctrlKey || event.metaKey || event.altKey) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      stretch(edge, span()[edge] + by * (event.shiftKey ? Math.round(FPS) : 1));
    });
  }
  // The comment's marker shows while the comment form, or the marker
  // itself, has the keyboard; with some text typed it stays. The whole
  // form, so nothing in it moves as it's clicked.
  const ours = (target) =>
    target instanceof Node && (form.contains(target) || draft.contains(target));
  document.addEventListener('focusin', (event) => {
    writing = ours(event.target);
    showDraft();
  });
  document.addEventListener('focusout', (event) => {
    writing = ours(event.relatedTarget);
    showDraft();
  });
  // The comment as it was last sent, so only that text is cleared.
  let sent = null;
  body.addEventListener('input', () => {
    video.pause();
    document.getElementById('review-audio-source')?.pause();
    showDraft();
  });
  body.addEventListener('keydown', (event) => {
    // 229: Safari's Enter that finishes typing in an input method.
    const composing = event.isComposing || event.keyCode === 229;
    if (event.key === 'Enter' && !event.shiftKey && !composing) {
      event.preventDefault();
      form.requestSubmit();
    }
  });
  const parent = document.getElementById('review-parent');
  const replying = document.getElementById('review-replying');
  /**
   * Starts a reply to a note, or with no id goes back to a new comment.
   * @param {string=} id The note's id.
   * @param {string=} name Who wrote it.
   */
  const replyTo = (id = '', name = '') => {
    parent.value = id;
    replying.hidden = !id;
    document.getElementById('review-replying-name').textContent = name;
    // A reply is about its note, not a frame.
    showAt();
  };
  list.addEventListener('click', (event) => {
    const button = event.target.closest('[data-reply]');
    if (button) {
      replyTo(button.dataset.reply, button.dataset.replyName);
      body.focus();
    }
  });
  // The frame on screen as the comment is sent, or the stretch its
  // marker was dragged over, unless "At" is unticked or it's a reply.
  form.addEventListener('htmx:configRequest', (event) => {
    const [from, to] = placed() ? span() : [null, null];
    frame.value = from === null ? '' : String(from);
    end.value = from === null || to === from ? '' : String(to);
    event.detail.parameters.frame = frame.value;
    event.detail.parameters.end = end.value;
    sent = body.value;
  });
  document.body.addEventListener('review:posted', () => {
    // Anything typed since it was sent is the next comment: keep it.
    if (body.value === sent) {
      body.value = '';
    }
    pin(null);
    replyTo();
  });
  // The note being replied to was deleted meanwhile.
  document.body.addEventListener('review:reply-gone', () => replyTo());
  form.addEventListener('click', (event) => {
    if (event.target.closest('[data-reply-cancel]')) {
      replyTo();
    }
    if (event.target.closest('[data-review-rename]')) {
      const field = form.querySelector('.review-name .field');
      field.hidden = false;
      field.querySelector('input').focus();
    }
  });
}

// The music alone, in its own player under the video.
const audio = document.getElementById('review-audio-source');
if (audio) {
  const box = document.getElementById('review-audio');
  const audioSeek = document.getElementById('review-audio-seek');
  const audioTime = document.getElementById('review-audio-time');
  /**
   * Seconds as m:ss.
   * @param {number} seconds
   * @return {string}
   */
  const clock = (seconds) => {
    const whole = Number.isFinite(seconds) ? Math.floor(seconds) : 0;
    return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, '0')}`;
  };
  const showAudio = () => {
    if (Number.isFinite(audio.duration)) {
      audioSeek.max = String(audio.duration);
    }
    audioSeek.value = String(audio.currentTime);
    const text = `${clock(audio.currentTime)} / ${clock(audio.duration)}`;
    audioTime.value = text;
    audioSeek.setAttribute('aria-valuetext', text);
  };
  const audioBroken = () => {
    document.getElementById('review-audio-error').hidden = false;
    box.classList.add('is-broken');
  };
  audio.addEventListener('loadedmetadata', showAudio);
  audio.addEventListener('durationchange', showAudio);
  audio.addEventListener('timeupdate', showAudio);
  audio.addEventListener('error', audioBroken);
  for (const name of ['play', 'pause', 'ended']) {
    audio.addEventListener(name, () => {
      box.classList.toggle('is-playing', !audio.paused);
      document
        .getElementById('review-audio-play')
        .setAttribute(
          'aria-label',
          audio.paused ? 'Play the audio' : 'Pause the audio',
        );
    });
  }
  // One at a time: the video and the audio are the same music. While
  // the audio is what's being heard, a comment is on the whole cue.
  audio.addEventListener('play', () => {
    video.pause();
    listening = true;
    showAt();
  });
  video.addEventListener('play', () => audio.pause());
  audioSeek.addEventListener('input', () => {
    audio.currentTime = Number(audioSeek.value);
  });
  document.getElementById('review-audio-play').addEventListener('click', () => {
    if (audio.paused) {
      audio.play().catch(() => {});
    } else {
      audio.pause();
    }
  });
  if (audio.error) {
    audioBroken();
  } else {
    showAudio();
  }
}

// The visit: tell the server now and then how long has played and how
// far the video got, so whoever sent the link can see it was watched.
if (config.visit) {
  const REPORT_MS = 15000;
  const token = JSON.parse(document.body.getAttribute('hx-headers') || '{}')[
    'X-CSRFToken'
  ];
  let played = 0;
  let furthest = null;
  let last = performance.now();
  /** Adds the time since the last look, if anything was playing. */
  const count = () => {
    const now = performance.now();
    const sound = document.getElementById('review-audio-source');
    if (!video.paused || (sound && !sound.paused)) {
      played += (now - last) / 1000;
    }
    last = now;
  };
  const report = () => {
    count();
    const sent = new URLSearchParams({
      visit: config.visit,
      played: String(Math.round(played)),
    });
    if (furthest !== null) {
      sent.set('furthest', String(furthest));
    }
    // keepalive: it still goes when the page is being closed.
    fetch(config.watchingUrl, {
      method: 'POST',
      headers: {'X-CSRFToken': token},
      body: sent,
      keepalive: true,
    }).catch(() => {});
  };
  for (const name of ['play', 'pause', 'ended']) {
    video.addEventListener(name, count);
    document
      .getElementById('review-audio-source')
      ?.addEventListener(name, count);
  }
  video.addEventListener('timeupdate', () => {
    if (video.currentTime > 0) {
      furthest = Math.max(furthest ?? 0, position());
    }
  });
  setInterval(() => {
    if (document.visibilityState === 'visible') {
      report();
    }
  }, REPORT_MS);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') {
      report();
    }
  });
  window.addEventListener('pagehide', report);
}

// What may have happened before this script ran.
if (video.error) {
  broken();
} else {
  sized();
}
update();
