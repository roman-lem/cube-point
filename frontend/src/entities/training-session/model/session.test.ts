import { describe, expect, it } from 'vitest'
import { DNF } from '@/shared/lib'
import {
  SESSION_VERSION,
  addSolve,
  parseSession,
  removeSolve,
  serializeSession,
  sessionStats,
  setPenalty,
  type TrainingSolve,
} from './session'

const solve = (value: number, at: number, penalty: TrainingSolve['penalty'] = 'none') => ({
  value,
  penalty,
  at,
})

const stored = (solves: unknown, version: unknown = SESSION_VERSION) =>
  JSON.stringify({ version, solves })

describe('parseSession', () => {
  it('читает сохранённую сессию', () => {
    const solves = [solve(1000, 1), solve(1100, 2, 'plus2'), solve(900, 3, 'dnf')]

    expect(parseSession(serializeSession(solves))).toEqual(solves)
  })

  it.each([
    ['нет данных', null],
    ['пустая строка', ''],
    ['битый JSON', '{"version": 1, "solves": ['],
    ['не объект', '42'],
    ['массив вместо объекта', JSON.stringify([solve(1000, 1)])],
    ['null в JSON', 'null'],
    ['другая версия', stored([solve(1000, 1)], 2)],
    ['нет версии', JSON.stringify({ solves: [solve(1000, 1)] })],
    ['версия строкой', stored([solve(1000, 1)], '1')],
    ['solves не массив', stored({ 0: solve(1000, 1) })],
    ['нет solves', JSON.stringify({ version: SESSION_VERSION })],
  ])('%s — пустая сессия', (_, raw) => {
    expect(parseSession(raw)).toEqual([])
  })

  it('выбрасывает только некорректные сборки', () => {
    const raw = stored([
      solve(1000, 1),
      null,
      'сборка',
      { value: 1100, penalty: 'none' }, // нет at
      { value: 11.5, penalty: 'none', at: 2 }, // дробное время
      { value: -100, penalty: 'none', at: 3 },
      { value: 0, penalty: 'none', at: 4 },
      { value: '1000', penalty: 'none', at: 5 },
      { value: 1000, penalty: 'dns', at: 6 }, // DNS в тренировке нет
      { value: 1000, penalty: 'oops', at: 7 },
      { value: null, penalty: 'dnf', at: 8 }, // у тренировочной сборки время есть всегда
      { value: 1000, penalty: 'none', at: '9' },
      solve(1200, 10, 'plus2'),
      solve(1300, 10), // повтор at
      solve(900, 11, 'dnf'),
    ])

    expect(parseSession(raw)).toEqual([
      solve(1000, 1),
      solve(1200, 10, 'plus2'),
      solve(900, 11, 'dnf'),
    ])
  })

  it('лишние поля сборки не сохраняются', () => {
    const raw = stored([{ ...solve(1000, 1), scramble: "R U R'" }])

    expect(parseSession(raw)).toEqual([solve(1000, 1)])
  })
})

describe('изменения сессии', () => {
  it('addSolve добавляет сборку в конец с моментом сборки', () => {
    const solves = addSolve([solve(1000, 100)], 1100, 'plus2', 500)

    expect(solves).toEqual([solve(1000, 100), solve(1100, 500, 'plus2')])
  })

  it('addSolve не повторяет at, даже если часы отстают', () => {
    const solves = addSolve([solve(1000, 500)], 1100, 'none', 500)

    expect(solves.map((s) => s.at)).toEqual([500, 501])
  })

  it('setPenalty и removeSolve меняют только нужную сборку и не трогают исходный массив', () => {
    const solves = [solve(1000, 1), solve(1100, 2)]

    expect(setPenalty(solves, 2, 'dnf')).toEqual([solve(1000, 1), solve(1100, 2, 'dnf')])
    expect(removeSolve(solves, 1)).toEqual([solve(1100, 2)])
    expect(solves).toEqual([solve(1000, 1), solve(1100, 2)])
  })
})

describe('sessionStats', () => {
  it('пустая сессия', () => {
    expect(sessionStats([])).toEqual({ ao5: null, ao12: null, best: null, count: 0 })
  })

  it('ao5 по последним пяти сборкам, ao12 — пока нет', () => {
    const values = [500, 1000, 1100, 1200, 1300, 1400]
    const solves = values.map((v, i) => solve(v, i + 1))

    expect(sessionStats(solves)).toEqual({ ao5: 1200, ao12: null, best: 500, count: 6 })
  })

  it('+2 учитывается, DNF в лучшую не попадает', () => {
    const solves = [solve(800, 1, 'dnf'), solve(1000, 2, 'plus2'), solve(1100, 3)]

    expect(sessionStats(solves).best).toBe(1100)
  })

  it('все DNF — лучшая DNF', () => {
    expect(sessionStats([solve(1000, 1, 'dnf')]).best).toBe(DNF)
  })

  it('ao12 из двенадцати сборок', () => {
    const solves = Array.from({ length: 12 }, (_, i) => solve(1000 + i * 100, i + 1))

    // Отброшены 10.00 и 21.00, среднее 11.00 … 20.00.
    expect(sessionStats(solves).ao12).toBe(1550)
  })
})
