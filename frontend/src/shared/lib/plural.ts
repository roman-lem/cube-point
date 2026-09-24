/**
 * Число со словом в нужной форме: plural(14, ['участник', 'участника', 'участников'])
 * → «14 участников».
 */
export function plural(count: number, forms: [one: string, few: string, many: string]): string {
  const mod10 = count % 10
  const mod100 = count % 100
  let form = forms[2]
  if (mod10 === 1 && mod100 !== 11) {
    form = forms[0]
  } else if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) {
    form = forms[1]
  }
  return `${count} ${form}`
}
