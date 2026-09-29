import { describe, it, expect } from 'vitest'
import { motywDlaKoloru } from '@/utils/motywOdznaki'

describe('motywDlaKoloru', () => {
  it('mapuje kolory podstawowe na siebie', () => {
    expect(motywDlaKoloru('gray')).toBe('gray')
    expect(motywDlaKoloru('blue')).toBe('blue')
    expect(motywDlaKoloru('green')).toBe('green')
    expect(motywDlaKoloru('amber')).toBe('amber')
    expect(motywDlaKoloru('red')).toBe('red')
    expect(motywDlaKoloru('violet')).toBe('violet')
  })

  it('mapuje kolory pochodne na najblizszy motyw Badge', () => {
    expect(motywDlaKoloru('cyan')).toBe('blue')
    expect(motywDlaKoloru('teal')).toBe('blue')
    expect(motywDlaKoloru('orange')).toBe('amber')
    expect(motywDlaKoloru('yellow')).toBe('amber')
    expect(motywDlaKoloru('purple')).toBe('violet')
    expect(motywDlaKoloru('pink')).toBe('violet')
    expect(motywDlaKoloru('black')).toBe('gray')
  })

  it('jest niewrazliwa na wielkosc liter', () => {
    expect(motywDlaKoloru('Blue')).toBe('blue')
    expect(motywDlaKoloru('CYAN')).toBe('blue')
  })

  it('zwraca gray dla pustego/nieznanego koloru', () => {
    expect(motywDlaKoloru('')).toBe('gray')
    expect(motywDlaKoloru(null)).toBe('gray')
    expect(motywDlaKoloru(undefined)).toBe('gray')
    expect(motywDlaKoloru('turkusowy')).toBe('gray')
  })
})
