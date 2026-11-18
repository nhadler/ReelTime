/**
 * @fileoverview The Notifications page: turns notifications on for this
 * browser and marks it in the device list.
 */

const config = JSON.parse(
  document.getElementById('notifications-config').textContent,
);
const csrf = JSON.parse(document.body.getAttribute('hx-headers') || '{}')[
  'X-CSRFToken'
];
const status = document.getElementById('notifications-status');

const supported =
  'serviceWorker' in navigator &&
  'PushManager' in window &&
  'Notification' in window;
const standalone =
  window.matchMedia('(display-mode: standalone)').matches ||
  navigator.standalone === true;
const appleTouch =
  /iPad|iPhone|iPod/.test(navigator.userAgent) ||
  (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);

/**
 * Shows one of the page's explanations and hides the others.
 * @param {string} which
 */
function show(which) {
  for (const part of document.querySelectorAll('[data-state]')) {
    part.hidden = part.dataset.state !== which;
  }
}

/**
 * The server's public key as the bytes subscribe() wants.
 * @param {string} text base64url
 * @return {!Uint8Array}
 */
function bytes(text) {
  const plain = text.replace(/-/g, '+').replace(/_/g, '/');
  const padded = plain + '='.repeat((4 - (plain.length % 4)) % 4);
  return Uint8Array.from(atob(padded), (c) => c.charCodeAt(0));
}

/**
 * Whether a subscription was made with the server's current key.
 * @param {!PushSubscription} subscription
 * @param {!Uint8Array} key
 * @return {boolean}
 */
function sameKey(subscription, key) {
  const used =
    subscription.options && subscription.options.applicationServerKey;
  if (!used) {
    return false;
  }
  const given = new Uint8Array(used);
  return given.length === key.length && given.every((b, i) => b === key[i]);
}

/**
 * Subscribes this browser and tells the server.
 * @return {!Promise<void>}
 */
async function turnOn() {
  // First thing in the tap: iOS only asks from a direct tap.
  const permission = await Notification.requestPermission();
  if (permission !== 'granted') {
    show('denied');
    return;
  }
  status.textContent = 'Turning on…';
  const registration = await navigator.serviceWorker.register('/sw.js', {
    scope: '/',
  });
  await navigator.serviceWorker.ready;
  const key = bytes(config.publicKey);
  let subscription = await registration.pushManager.getSubscription();
  if (subscription && !sameKey(subscription, key)) {
    await subscription.unsubscribe();
    subscription = null;
  }
  subscription =
    subscription ||
    (await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: key,
    }));
  const response = await fetch(config.subscribeUrl, {
    method: 'POST',
    credentials: 'same-origin',
    headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf},
    body: JSON.stringify(subscription.toJSON()),
  });
  if (response.ok) {
    window.location.reload();
    return;
  }
  const answer = await response.json().catch(() => ({}));
  status.textContent = answer.error || 'Not turned on: try again.';
}

/**
 * Whether notifications are blocked for ReelTime. Some browsers (headless
 * Chromium) say "denied" here while the Permissions API says otherwise;
 * believe the Permissions API when it answers.
 * @return {!Promise<boolean>}
 */
async function blocked() {
  if (Notification.permission !== 'denied') {
    return false;
  }
  try {
    const state = await navigator.permissions.query({name: 'notifications'});
    return state.state === 'denied';
  } catch {
    return true;
  }
}

/** Marks this browser's row in the device list. */
async function markThisDevice() {
  const registration = await navigator.serviceWorker.getRegistration('/');
  const subscription =
    registration && (await registration.pushManager.getSubscription());
  if (!subscription) {
    return;
  }
  for (const row of document.querySelectorAll('[data-endpoint]')) {
    if (row.dataset.endpoint === subscription.endpoint) {
      row.querySelector('[data-this-device]').hidden = false;
    }
  }
}

if (!supported) {
  show(appleTouch && !standalone ? 'install' : 'unsupported');
} else if (await blocked()) {
  show('denied');
} else {
  show('ready');
  markThisDevice().catch(() => {});
  document.getElementById('notifications-on').addEventListener('click', () => {
    turnOn().catch(() => {
      status.textContent = 'Not turned on: try again.';
    });
  });
}
