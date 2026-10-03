import { describe, expect, it } from 'vitest'
import { latestLoader } from './polling'

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (e: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

describe('latestLoader', () => {
  it('ignores a response that came after a newer one', async () => {
    const requests = [deferred<string>(), deferred<string>()]
    let call = 0
    const applied: string[] = []
    const { load } = latestLoader(() => requests[call++].promise, (d) => applied.push(d), () => {})

    const first = load()
    const second = load()
    requests[1].resolve('new')
    await second
    requests[0].resolve('old')
    await first

    expect(applied).toEqual(['new'])
  })

  it('reports only the error of the latest request', async () => {
    const requests = [deferred<string>(), deferred<string>()]
    let call = 0
    const errors: unknown[] = []
    const { load } = latestLoader(() => requests[call++].promise, () => {}, (e) => errors.push(e))

    const first = load()
    const second = load()
    requests[0].reject('old')
    requests[1].reject('new')
    await Promise.all([first, second])

    expect(errors).toEqual(['new'])
  })

  it('drops responses of requests sent before invalidate', async () => {
    const request = deferred<string>()
    const applied: string[] = []
    const { load, invalidate } = latestLoader(() => request.promise, (d) => applied.push(d), () => {})

    const pending = load()
    invalidate()
    request.resolve('stale')
    await pending

    expect(applied).toEqual([])
  })
})
