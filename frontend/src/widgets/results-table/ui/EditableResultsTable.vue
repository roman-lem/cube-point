<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import type { DeskAttempt, DeskEvent, DeskRow } from '@/entities/meetup'
import { RecordBadge } from '@/entities/record'
import {
  AttemptHistoryDialog, attemptToText, canRestore, fmcDnf, parseAttemptText, sameAttempt,
  SaveIndicator, toggleDnf, togglePlus2, type AttemptSaving,
} from '@/features/attempt-edit'
import {
  ATTEMPTS_COUNT, EVENTS, calcSeries, formatAttempt, formatResult, type Attempt, type EventId,
} from '@/shared/lib'
import { AppIcon } from '@/shared/ui'

// The organizer's result entry table, like a spreadsheet:
// arrows and Enter navigate, digits are a time (1234 → 12.34), "+" is +2, "d" is DNF.
// A cell saves itself on blur and on Enter. Delete, Backspace or an empty
// cell erase the attempt, only the last one in the series (a mistaken entry). A corner in a cell
// means the attempt was corrected; tapping shows its history and restoring the original result.
// FMC cells are not typed into: the organizer does not set moves, the result can only be
// replaced with DNF ("DNF" button or "d") and brought back with "Restore original".
const { event, saving } = defineProps<{
  event: DeskEvent
  saving: AttemptSaving
  /** The club's time zone: time of edits in the history. */
  timeZone: string
}>()

const count = computed(() => ATTEMPTS_COUNT[event.format])
const resultType = computed(() => EVENTS[event.event_id as EventId]?.resultType ?? 'time')
const hasAverage = computed(() => event.format === 'ao5' || event.format === 'mo3')
const isFmc = computed(() => resultType.value === 'moves')
const columns = computed(() => Array.from({ length: count.value }, (_, i) => i))

const active = ref({ row: 0, col: 0 })
/** The edited cell is separate from the active one: a click on another cell
 * changes the active cell before the edited one loses focus. */
const editCell = ref<{ userId: number; col: number } | null>(null)
const draft = ref('')
const table = ref<HTMLElement>()
const input = ref<HTMLInputElement[]>([])

function attemptsOf(row: DeskRow): (DeskAttempt | null)[] {
  return row.series?.attempts ?? Array(count.value).fill(null)
}

function doneCount(row: DeskRow) {
  return attemptsOf(row).filter(Boolean).length
}

/** Entered attempts can be edited and the next one in order entered. Not in FMC. */
function isEditable(row: DeskRow, col: number) {
  return !isFmc.value && col <= doneCount(row)
}

/** FMC cell with a result: no typing, only the DNF and restore actions. */
function hasFmcActions(row: DeskRow, col: number) {
  return isFmc.value && attemptsOf(row)[col] != null
}

function setFmcDnf(row: DeskRow, col: number) {
  const next = fmcDnf(attemptsOf(row)[col] ?? null)
  if (next) {
    save(row, col, next)
  }
}

function restore(row: DeskRow, col: number) {
  void saving.restore(event.event_id, row.user, col + 1)
}

function cellTexts(row: DeskRow) {
  const attempts = attemptsOf(row)
  const entered = attempts.slice(0, doneCount(row))
  const { counting } = calcSeries(entered, event.format, resultType.value)
  return attempts.map((attempt, i) => {
    if (!attempt) {
      return ''
    }
    const text = formatAttempt(attempt, resultType.value)
    return counting[i] ? text : `(${text})`
  })
}

function isActive(rowIndex: number, col: number) {
  return active.value.row === rowIndex && active.value.col === col
}

function isEditing(row: DeskRow, col: number) {
  return editCell.value?.userId === row.user.id && editCell.value.col === col
}

/** The attempt whose history is open. */
const historyCell = ref<{ user: DeskRow['user']; col: number } | null>(null)
const historyOpen = ref(false)
/** Current value of the attempt: the row updates after a restore and server polling. */
const historyAttempt = computed(() => {
  const cell = historyCell.value
  const row = event.rows.find((r) => r.user.id === cell?.user.id)
  return cell && row ? (attemptsOf(row)[cell.col] ?? null) : null
})

function showHistory(row: DeskRow, col: number) {
  historyCell.value = { user: row.user, col }
  historyOpen.value = true
}

// Navigation

function move(dRow: number, dCol: number) {
  const row = Math.min(Math.max(active.value.row + dRow, 0), event.rows.length - 1)
  const col = Math.min(Math.max(active.value.col + dCol, 0), count.value - 1)
  active.value = { row, col }
  nextTick(() => {
    table.value
      ?.querySelector(`[data-cell="${row}:${col}"]`)
      ?.scrollIntoView({ block: 'nearest', inline: 'nearest' })
  })
}

function select(rowIndex: number, col: number) {
  const row = event.rows[rowIndex]
  if (row && isEditing(row, col)) {
    // A click inside the input just moves the caret.
    return
  }
  if (editCell.value) {
    commit()
  }
  active.value = { row: rowIndex, col }
}

const activeRow = () => event.rows[active.value.row]

function startEdit(initial?: string) {
  const row = activeRow()
  if (!row || !isEditable(row, active.value.col)) {
    return
  }
  draft.value = initial ?? attemptToText(attemptsOf(row)[active.value.col] ?? null, resultType.value)
  editCell.value = { userId: row.user.id, col: active.value.col }
  nextTick(() => input.value[0]?.focus())
}

function save(row: DeskRow, col: number, attempt: Attempt | null) {
  void saving.save(event.event_id, row.user, col + 1, attempt)
}

function commit() {
  const cell = editCell.value
  editCell.value = null
  const row = event.rows.find((r) => r.user.id === cell?.userId)
  if (!cell || !row) {
    return
  }
  const col = cell.col
  const text = draft.value.trim()
  if (!text) {
    clear(row, col)
    return
  }
  const parsed = parseAttemptText(text, resultType.value)
  if (!parsed) {
    saving.markInvalid(event.event_id, row.user.id, col + 1)
  } else if (!sameAttempt(parsed, attemptsOf(row)[col] ?? null)) {
    save(row, col, parsed)
  }
}

/** Erases the attempt if there is one. The server will not erase a non-last one and will explain why. */
function clear(row: DeskRow, col: number) {
  if (!isFmc.value && attemptsOf(row)[col]) {
    save(row, col, null)
  }
}

/** "+" and "d" in a cell that is not being edited: the penalty is saved right away. */
function applyPenalty(toggle: (attempt: Attempt | null) => Attempt | null) {
  const row = activeRow()
  const col = active.value.col
  if (!row || !isEditable(row, col)) {
    return
  }
  const next = toggle(attemptsOf(row)[col] ?? null)
  if (next) {
    save(row, col, next)
  }
}

const MOVES: Record<string, [number, number]> = {
  ArrowUp: [-1, 0],
  ArrowDown: [1, 0],
  ArrowLeft: [0, -1],
  ArrowRight: [0, 1],
}

function onTableKey(e: KeyboardEvent) {
  if (editCell.value || e.ctrlKey || e.metaKey || e.altKey) {
    return
  }
  const step = MOVES[e.key]
  if (step) {
    e.preventDefault()
    move(...step)
  } else if (e.key === 'Enter' || e.key === 'F2') {
    e.preventDefault()
    startEdit()
  } else if (e.key === 'Delete' || e.key === 'Backspace') {
    e.preventDefault()
    const row = activeRow()
    if (row) {
      clear(row, active.value.col)
    }
  } else if (e.key === '+') {
    e.preventDefault()
    applyPenalty(togglePlus2)
  } else if (e.key === 'd' || e.key === 'D' || e.key === 'в' || e.key === 'В') {
    // "в" is the same key in the Russian layout.
    e.preventDefault()
    const row = activeRow()
    if (isFmc.value && row) {
      setFmcDnf(row, active.value.col)
    } else {
      applyPenalty(toggleDnf)
    }
  } else if (/^[\d.,:]$/.test(e.key)) {
    e.preventDefault()
    startEdit(e.key)
  }
}

function onInputKey(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    e.preventDefault()
    editCell.value = null
    table.value?.focus()
    return
  }
  const step =
    e.key === 'Enter' || e.key === 'ArrowDown' ? [1, 0]
    : e.key === 'ArrowUp' ? [-1, 0]
    : e.key === 'Tab' ? [0, e.shiftKey ? -1 : 1]
    : null
  if (step) {
    e.preventDefault()
    commit()
    move(step[0]!, step[1]!)
    table.value?.focus()
  }
}

function onInputBlur() {
  // Enter, arrows and a click on another cell have already saved the cell; this handles focus leaving the table.
  if (editCell.value) {
    commit()
  }
}
</script>

<template>
  <div class="results-table">
    <div v-if="saving.notice.value" class="results-table__notice" role="alert">
      <AppIcon name="error" :size="20" />
      <p>{{ saving.notice.value }}</p>
      <button
        type="button"
        class="results-table__notice-close"
        aria-label="Скрыть сообщение"
        @click="saving.notice.value = ''"
      >
        ×
      </button>
    </div>

    <div
      ref="table"
      class="results-table__scroll"
      tabindex="0"
      role="grid"
      :aria-label="`Результаты, ${EVENTS[event.event_id as EventId]?.name ?? event.event_id}`"
      @keydown="onTableKey"
    >
      <table class="results-table__table">
        <thead>
          <tr>
            <th class="results-table__place">#</th>
            <th class="results-table__name">Участник</th>
            <th v-for="col in columns" :key="col">Попытка {{ col + 1 }}</th>
            <th v-if="hasAverage">Среднее ({{ event.format }})</th>
            <th>Лучшая</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(row, rowIndex) in event.rows"
            :key="row.user.id"
            :class="{ 'results-table__row--disqualified': row.disqualified }"
          >
            <td class="results-table__place">{{ row.place ?? '—' }}</td>
            <td class="results-table__name">
              {{ row.user.display_name }}
              <span v-if="row.disqualified" class="results-table__tag">дискв.</span>
            </td>
            <td
              v-for="col in columns"
              :key="col"
              :data-cell="`${rowIndex}:${col}`"
              :class="[
                'results-table__cell',
                {
                  'results-table__cell--active': isActive(rowIndex, col),
                  'results-table__cell--locked': !isEditable(row, col) && !hasFmcActions(row, col),
                  'results-table__cell--dnf': ['dnf', 'dns'].includes(attemptsOf(row)[col]?.penalty ?? ''),
                  'results-table__cell--error':
                    saving.stateOf(event.event_id, row.user.id, col + 1)?.status === 'error',
                },
              ]"
              role="gridcell"
              :title="saving.stateOf(event.event_id, row.user.id, col + 1)?.message"
              @mousedown="select(rowIndex, col)"
              @dblclick="startEdit()"
            >
              <input
                v-if="isEditing(row, col)"
                ref="input"
                v-model="draft"
                class="results-table__input"
                autocomplete="off"
                @keydown="onInputKey"
                @blur="onInputBlur"
              />
              <span v-else class="results-table__value">{{ cellTexts(row)[col] }}</span>
              <template v-if="hasFmcActions(row, col)">
                <button
                  v-if="fmcDnf(attemptsOf(row)[col] ?? null)"
                  type="button"
                  class="results-table__action"
                  :aria-label="`Попытка ${col + 1}: заменить на DNF`"
                  @mousedown.stop
                  @click="setFmcDnf(row, col)"
                >
                  DNF
                </button>
                <button
                  v-else-if="canRestore(attemptsOf(row)[col] ?? null)"
                  type="button"
                  class="results-table__action"
                  :aria-label="`Попытка ${col + 1}: вернуть исходный результат`"
                  @mousedown.stop
                  @click="restore(row, col)"
                >
                  Вернуть исходный
                </button>
              </template>
              <button
                v-if="attemptsOf(row)[col]?.edited"
                type="button"
                class="results-table__edited"
                title="Попытку исправляли — история"
                :aria-label="`Попытка ${col + 1}: история исправлений`"
                @mousedown.stop
                @click="showHistory(row, col)"
              />
              <SaveIndicator
                class="results-table__state"
                :state="saving.stateOf(event.event_id, row.user.id, col + 1)"
              />
            </td>
            <td v-if="hasAverage" class="results-table__result">
              {{ formatResult(row.series?.average ?? null, resultType, true) }}
              <RecordBadge v-for="mark in row.marks.average" :key="mark" :mark="mark" />
            </td>
            <td class="results-table__result">
              {{ formatResult(row.series?.best ?? null, resultType) }}
              <RecordBadge v-for="mark in row.marks.single" :key="mark" :mark="mark" />
            </td>
          </tr>
          <tr v-if="event.rows.length === 0">
            <td :colspan="count + 4" class="results-table__empty">
              Подтверждённых участников пока нет
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <AttemptHistoryDialog
      v-if="historyCell"
      v-model:open="historyOpen"
      :saving="saving"
      :event-id="event.event_id"
      :user="historyCell.user"
      :number="historyCell.col + 1"
      :attempt="historyAttempt"
      :result-type="resultType"
      :time-zone="timeZone"
    />

    <p v-if="isFmc" class="results-table__hint">
      Результаты FMC сдают участники. Организатор может только заменить результат на DNF
      (кнопка или «d») и вернуть исходный; уголок в ячейке — история правок.
      Все изменения сохраняются автоматически.
    </p>
    <p v-else class="results-table__hint">
      Стрелки и Enter — переход по ячейкам, цифры — время (1234 → 12.34, 10234 → 1:02.34),
      «+» — +2, «d» — DNF, Delete — стереть последнюю попытку, Esc — отмена. Попытку,
      которую сдал сам участник, можно исправить, но не стереть; уголок в ячейке — история правок.
      Все изменения сохраняются автоматически.
    </p>
  </div>
</template>

<style scoped>
.results-table {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.results-table__notice {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-3);
  background: var(--color-surface);
  border: 1px solid var(--color-danger);
  border-radius: var(--radius-card);
  color: var(--color-danger);
}

.results-table__notice p {
  flex: 1;
  color: var(--color-text-primary);
}

.results-table__notice-close {
  padding: 0 var(--space-1);
  background: none;
  border: none;
  color: var(--color-text-secondary);
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
}

.results-table__scroll {
  overflow-x: auto;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  outline: none;
}

.results-table__scroll:focus-visible {
  box-shadow: 0 0 0 2px var(--color-primary);
}

.results-table__table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  height: 44px;
  padding: 0 var(--space-3);
  border-bottom: 1px solid var(--color-border);
  text-align: left;
  white-space: nowrap;
}

th {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
}

tbody tr:last-child td {
  border-bottom: none;
}

.results-table__place {
  width: 40px;
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
}

.results-table__name {
  font-weight: var(--font-weight-label);
}

.results-table__row--disqualified td {
  color: var(--color-text-secondary);
}

.results-table__tag {
  margin-left: var(--space-1);
  color: var(--color-danger);
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-body);
}

.results-table__cell {
  position: relative;
  min-width: 96px;
  padding-right: 28px;
  border-left: 1px solid var(--color-border);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  cursor: cell;
}

.results-table__cell--locked {
  background: var(--color-background);
  cursor: default;
}

.results-table__cell--dnf {
  color: var(--color-dnf);
}

.results-table__cell--active {
  box-shadow: inset 0 0 0 2px var(--color-primary);
}

.results-table__cell--error {
  box-shadow: inset 0 0 0 2px var(--color-danger);
}

.results-table__input {
  width: 100%;
  height: 32px;
  padding: 0 var(--space-1);
  background: var(--color-surface);
  border: none;
  outline: none;
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

/* Corner of a corrected attempt, like a note in a spreadsheet. */
.results-table__edited {
  position: absolute;
  top: 0;
  left: 0;
  width: 14px;
  height: 14px;
  padding: 0;
  background: linear-gradient(135deg, var(--color-primary) 50%, transparent 50%);
  border: none;
  cursor: pointer;
}

.results-table__action {
  margin-left: var(--space-2);
  padding: 2px var(--space-2);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-badge);
  color: var(--color-text-primary);
  font-family: var(--font-sans);
  font-size: var(--font-size-label);
  cursor: pointer;
}

.results-table__state {
  position: absolute;
  top: 50%;
  right: 4px;
  transform: translateY(-50%);
}

.results-table__result {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  font-weight: var(--font-weight-label);
}

.results-table__result :deep(.record-badge) {
  margin-left: var(--space-1);
}

.results-table__empty {
  color: var(--color-text-secondary);
  text-align: center;
}

.results-table__hint {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}
</style>
