import { describe, expect, it } from 'vitest'
import { addMove, removeLast, setModifier } from './editing'

describe('клавиатура FMC', () => {
  it('добавляет грани и перехваты', () => {
    expect(addMove(addMove([], 'R', false), 'x', false)).toEqual(['R', 'x'])
  })

  it('w делает широкий поворот только у граней', () => {
    expect(addMove([], 'U', true)).toEqual(['Uw'])
    expect(addMove([], 'y', true)).toEqual(['y'])
  })

  it("' и 2 меняют последний ход", () => {
    expect(setModifier(['R', 'U'], "'")).toEqual(['R', "U'"])
    expect(setModifier(["Rw'"], '2')).toEqual(['Rw2'])
    expect(setModifier(['x2'], "'")).toEqual(["x'"])
  })

  it('повторный модификатор снимается', () => {
    expect(setModifier(["R'"], "'")).toEqual(['R'])
    expect(setModifier(['Fw2'], '2')).toEqual(['Fw'])
  })

  it('модификатор без ходов ничего не делает', () => {
    expect(setModifier([], '2')).toEqual([])
  })

  it('backspace удаляет один ход', () => {
    expect(removeLast(['R', "U'", 'Fw2'])).toEqual(['R', "U'"])
    expect(removeLast([])).toEqual([])
  })
})
