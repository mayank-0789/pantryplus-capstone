import test from 'node:test';
import assert from 'node:assert/strict';
import { expiryState } from './stockDisplay.js';

for (const [expires_on, quantity, expected] of [
  ['2026-10-15', 1, 'expired'], ['2026-10-16', 1, 'soon'],
  ['2026-10-23', 1, 'soon'], ['2026-10-24', 1, 'ok'],
  [null, 1, 'none'], ['2026-10-15', 0, 'none'],
]) {
  test(`expiry ${expires_on} with stock ${quantity}: ${expected}`, () => {
    assert.equal(expiryState({ expires_on, quantity }, '2026-10-16'), expected);
  });
}
