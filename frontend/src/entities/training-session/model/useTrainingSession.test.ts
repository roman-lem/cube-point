// Restoring the session from storage. A Map-based storage replaces localStorage:
// tests run in node, without a browser.
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { effectScope, nextTick, ref, type EffectScope } from 'vue'
import { serializeSession } from './session'
import { sessionKey, useTrainingSession } from './useTrainingSession'

function memoryStorage(initial: Record<string, string> = {}) {
  const data = new Map(Object.entries(initial))
  return {
    data,
    getItem: (key: string) => data.get(key) ?? null,
    setItem: (key: string, value: string) => void data.set(key, value),
    removeItem: (key: string) => void data.delete(key),
  }
}

const KEY = sessionKey('333')
const saved = serializeSession([
  { value: 1000, penalty: 'none', at: 1 },
  { value: 1100, penalty: 'plus2', at: 2 },
])

let scope: EffectScope
beforeEach(() => {
  scope = effectScope()
})
afterEach(() => scope.stop())

function session(eventId: Parameters<typeof useTrainingSession>[0], storage = memoryStorage()) {
  return scope.run(() => useTrainingSession(eventId, storage))!
}

describe('useTrainingSession', () => {
  it('restores the session from storage', () => {
    const { solves, stats, last } = session('333', memoryStorage({ [KEY]: saved }))

    expect(solves.value.map((s) => s.value)).toEqual([1000, 1100])
    expect(stats.value.best).toBe(1000)
    expect(last.value).toEqual({ value: 1100, penalty: 'plus2', at: 2 })
  })

  it.each([
    ['broken JSON', '{"solves": [{'],
    ['old format without version', JSON.stringify([{ time: 1000 }])],
    ['another version', JSON.stringify({ version: 0, solves: [] })],
  ])('%s: empty session, work goes on', async (_, raw) => {
    const storage = memoryStorage({ [KEY]: raw })
    const s = session('333', storage)

    expect(s.solves.value).toEqual([])
    expect(s.last.value).toBeNull()

    s.add(1200, 'none')
    await nextTick()

    expect(JSON.parse(storage.data.get(KEY)!).solves).toHaveLength(1)
  })

  it('only invalid solves are dropped from a damaged session', () => {
    const raw = JSON.stringify({
      version: 1,
      solves: [{ value: 1000, penalty: 'none', at: 1 }, { value: 'x' }, { value: 900, penalty: 'dnf', at: 2 }],
    })

    const { solves } = session('333', memoryStorage({ [KEY]: raw }))

    expect(solves.value.map((s) => s.at)).toEqual([1, 2])
  })

  it('changes are saved to storage and survive a reload', async () => {
    const storage = memoryStorage()
    const first = session('333', storage)

    first.add(1000, 'none')
    first.add(1100, 'none')
    first.setPenalty(first.last.value!.at, 'dnf')
    first.remove(first.solves.value[0]!.at)
    await nextTick()

    const reloaded = session('333', storage)
    expect(reloaded.solves.value).toEqual(first.solves.value)
    expect(reloaded.solves.value.map((s) => [s.value, s.penalty])).toEqual([[1100, 'dnf']])
  })

  it('does not write an empty session to storage', () => {
    const storage = memoryStorage()

    session('333', storage)

    expect(storage.data.size).toBe(0)
  })

  it('a new session clears only its own event', async () => {
    const storage = memoryStorage({ [KEY]: saved, [sessionKey('222')]: saved })
    const s = session('333', storage)

    s.clear()
    await nextTick()

    expect(session('333', storage).solves.value).toEqual([])
    expect(session('222', storage).solves.value).toHaveLength(2)
  })

  it('changing the event reads its session, other data is not carried over', async () => {
    const storage = memoryStorage({ [KEY]: saved })
    const eventId = ref('333')
    const s = session(eventId, storage)

    eventId.value = '222'
    await nextTick()
    expect(s.solves.value).toEqual([])

    s.add(500, 'none')
    await nextTick()
    eventId.value = '333'
    await nextTick()

    expect(s.solves.value).toHaveLength(2)
    expect(JSON.parse(storage.data.get(sessionKey('222'))!).solves).toHaveLength(1)
    expect(storage.data.get(KEY)).toBe(saved)
  })
})
