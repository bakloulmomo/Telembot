import { nextTick } from 'vue'

export const motionOn = () =>
  !document.documentElement.classList.contains('motion-off') &&
  !window.matchMedia('(prefers-reduced-motion: reduce)').matches

// Runs a state change inside a View Transition, so elements with the same view-transition-name morph
// (composer → question title, prompt bar ↔ clarification card). Falls back to an instant change.
// Safety: the state change must never wait for an animation. If the browser does not start the
// transition within 250 ms (hidden tab, no frames), the animation is skipped and the change applied.
export function withTransition(fn) {
  if (!document.startViewTransition || !motionOn() || document.hidden) { fn(); return }
  let applied = false
  const apply = () => { if (!applied) { applied = true; fn() } }
  const vt = document.startViewTransition(async () => { apply(); await nextTick() })
  vt.ready.catch(() => {}); vt.finished.catch(() => {}); vt.updateCallbackDone.catch(() => {})
  setTimeout(() => { if (!applied) { vt.skipTransition(); apply() } }, 250)
}

export function setMotion(on) {
  document.documentElement.classList.toggle('motion-off', !on)
}
