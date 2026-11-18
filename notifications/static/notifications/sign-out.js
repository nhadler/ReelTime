/**
 * @fileoverview Signing out turns this browser's notifications off
 * first, so a shared device stops showing the last person's.
 */

const WAIT_MS = 2000;

/**
 * Unsubscribes this browser and tells the server.
 * @param {!HTMLFormElement} form
 * @return {!Promise<void>}
 */
async function forget(form) {
  const registration = await navigator.serviceWorker.getRegistration('/');
  const subscription =
    registration &&
    registration.pushManager &&
    (await registration.pushManager.getSubscription());
  if (!subscription) {
    return;
  }
  const token = form.querySelector('[name=csrfmiddlewaretoken]').value;
  await fetch(form.dataset.forgetUrl, {
    method: 'POST',
    credentials: 'same-origin',
    headers: {'Content-Type': 'application/json', 'X-CSRFToken': token},
    body: JSON.stringify({endpoint: subscription.endpoint}),
  });
  await subscription.unsubscribe();
}

for (const form of document.querySelectorAll('form[data-forget-url]')) {
  form.addEventListener('submit', (event) => {
    if (!('serviceWorker' in navigator) || form.dataset.forgotten) {
      return;
    }
    event.preventDefault();
    form.dataset.forgotten = 'true';
    const late = new Promise((resolve) => setTimeout(resolve, WAIT_MS));
    Promise.race([forget(form), late])
      .catch(() => {})
      .finally(() => form.submit());
  });
}
