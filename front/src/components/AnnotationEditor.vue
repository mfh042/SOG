<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'

const props = defineProps({
  imageUrl: { type: String, default: '' },
  modelValue: { type: Object, default: () => ({ tools: [] }) },
  readonly: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])

const canvasRef = ref(null)
const containerRef = ref(null)
const imgRef = ref(null)
const imgLoaded = ref(false)
const naturalSize = ref({ w: 0, h: 0 })
const displaySize = ref({ w: 0, h: 0 })

const activeTool = ref('arrow')
const activeColor = ref('#ff4444')
const labelText = ref('')
const history = ref([])
const historyIdx = ref(-1)

const drawing = ref(false)
const currentTool = ref(null)
const dragTool = ref(null)
const dragStart = ref(null)
const draggingPoint = ref(null)

const COLORS = ['#ff4444', '#ff8800', '#ffcc00', '#22cc66', '#2b7cff', '#aa44ff', '#ffffff', '#000000']

const tools = computed({
  get: () => props.modelValue?.tools || [],
  set: (val) => emit('update:modelValue', { ...(props.modelValue || {}), tools: val }),
})

function pushHistory() {
  const snap = JSON.stringify(tools.value)
  if (historyIdx.value < history.value.length - 1) {
    history.value = history.value.slice(0, historyIdx.value + 1)
  }
  history.value.push(snap)
  historyIdx.value = history.value.length - 1
  if (history.value.length > 50) {
    history.value.shift()
    historyIdx.value--
  }
}

function undo() {
  if (historyIdx.value > 0) {
    historyIdx.value--
    tools.value = JSON.parse(history.value[historyIdx.value])
  }
}

function redo() {
  if (historyIdx.value < history.value.length - 1) {
    historyIdx.value++
    tools.value = JSON.parse(history.value[historyIdx.value])
  }
}

function clearAll() {
  tools.value = []
  pushHistory()
}

function normalizeCoords(x, y) {
  if (!displaySize.value.w) return { nx: 0, ny: 0 }
  return { nx: x / displaySize.value.w, ny: y / displaySize.value.h }
}

function toDisplay(nx, ny) {
  return { x: nx * displaySize.value.w, y: ny * displaySize.value.h }
}

function onImgLoad() {
  imgLoaded.value = true
  naturalSize.value = { w: imgRef.value.naturalWidth, h: imgRef.value.naturalHeight }
  nextTick(() => {
    measureDisplay()
    draw()
  })
  pushHistory()
  history.value = [JSON.stringify(tools.value)]
  historyIdx.value = 0
}

function measureDisplay() {
  if (!containerRef.value) return
  const rect = containerRef.value.getBoundingClientRect()
  const iw = naturalSize.value.w || rect.width
  const ih = naturalSize.value.h || rect.height
  const ratio = iw / ih
  let w = rect.width
  let h = w / ratio
  if (h > rect.height) {
    h = rect.height
    w = h * ratio
  }
  displaySize.value = { w, h }
}

function getMousePos(e) {
  const rect = canvasRef.value.getBoundingClientRect()
  return {
    x: (e.clientX - rect.left) * (displaySize.value.w / rect.width),
    y: (e.clientY - rect.top) * (displaySize.value.h / rect.height),
  }
}

function hitTest(pos) {
  const hitRadius = 14
  for (let i = tools.value.length - 1; i >= 0; i--) {
    const t = tools.value[i]
    if (t.type === 'arrow') {
      const p1 = toDisplay(t.points[0][0], t.points[0][1])
      const p2 = toDisplay(t.points[1][0], t.points[1][1])
      if (dist(pos, p1) < hitRadius) return { tool: t, pointIdx: 0 }
      if (dist(pos, p2) < hitRadius) return { tool: t, pointIdx: 1 }
      if (pointToSegDist(pos, p1, p2) < hitRadius) return { tool: t, onLine: true }
    } else if (t.type === 'rect') {
      const p = toDisplay(t.x, t.y)
      if (Math.abs(pos.x - p.x) < 10 && Math.abs(pos.y - p.y) < 10) return { tool: t, corner: 'tl' }
      const br = toDisplay(t.x + t.w, t.y + t.h)
      if (Math.abs(pos.x - br.x) < 10 && Math.abs(pos.y - br.y) < 10) return { tool: t, corner: 'br' }
      if (pos.x >= p.x && pos.x <= br.x && pos.y >= p.y && pos.y <= br.y) return { tool: t, inside: true }
    } else if (t.type === 'circle') {
      const c = toDisplay(t.cx, t.cy)
      const dr = Math.sqrt((pos.x - c.x) ** 2 + (pos.y - c.y) ** 2)
      if (Math.abs(dr - t.r * (displaySize.value.w / (naturalSize.value.w || 1))) < hitRadius) return { tool: t, onEdge: true }
      if (dr < t.r * (displaySize.value.w / (naturalSize.value.w || 1))) return { tool: t, inside: true }
    } else if (t.type === 'text') {
      const p = toDisplay(t.x, t.y)
      const tw = t.text.length * 16 + 12
      const th = 24
      if (pos.x >= p.x - 4 && pos.x <= p.x + tw && pos.y >= p.y - th && pos.y <= p.y) return { tool: t, inside: true }
    }
  }
  return null
}

function dist(a, b) { return Math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2) }
function pointToSegDist(p, a, b) {
  const l2 = (b.x - a.x) ** 2 + (b.y - a.y) ** 2
  if (l2 === 0) return dist(p, a)
  let t = ((p.x - a.x) * (b.x - a.x) + (p.y - a.y) * (b.y - a.y)) / l2
  t = Math.max(0, Math.min(1, t))
  const proj = { x: a.x + t * (b.x - a.x), y: a.y + t * (b.y - a.y) }
  return dist(p, proj)
}

function onMouseDown(e) {
  if (props.readonly || !imgLoaded.value) return
  const pos = getMousePos(e)
  const hit = hitTest(pos)

  if (hit) {
    dragTool.value = hit.tool
    if (hit.pointIdx !== undefined) {
      draggingPoint.value = hit.pointIdx
    } else if (hit.corner) {
      draggingPoint.value = hit.corner
    } else {
      draggingPoint.value = 'move'
      dragStart.value = pos
    }
    return
  }

  drawing.value = true
  const { nx, ny } = normalizeCoords(pos.x, pos.y)

  if (activeTool.value === 'text') {
    const text = labelText.value || '标注文字'
    const newTool = { type: 'text', x: nx, y: ny, text, color: activeColor.value }
    tools.value.push(newTool)
    pushHistory()
    drawing.value = false
  } else if (activeTool.value === 'arrow') {
    currentTool.value = { type: 'arrow', points: [[nx, ny], [nx, ny]], color: activeColor.value, label: labelText.value || '' }
  } else if (activeTool.value === 'rect') {
    currentTool.value = { type: 'rect', x: nx, y: ny, w: 0, h: 0, color: activeColor.value, label: labelText.value || '' }
  } else if (activeTool.value === 'circle') {
    currentTool.value = { type: 'circle', cx: nx, cy: ny, r: 0, color: activeColor.value, label: labelText.value || '' }
  }
}

function onMouseMove(e) {
  if (!imgLoaded.value) return
  const pos = getMousePos(e)

  if (drawing.value && currentTool.value) {
    const { nx, ny } = normalizeCoords(pos.x, pos.y)
    if (currentTool.value.type === 'arrow') {
      currentTool.value.points[1] = [nx, ny]
    } else if (currentTool.value.type === 'rect') {
      currentTool.value.w = nx - currentTool.value.x
      currentTool.value.h = ny - currentTool.value.y
    } else if (currentTool.value.type === 'circle') {
      const c = toDisplay(currentTool.value.cx, currentTool.value.cy)
      currentTool.value.r = dist(pos, c) / (displaySize.value.w / (naturalSize.value.w || 1))
    }
    draw()
    return
  }

  if (dragTool.value && draggingPoint.value !== null) {
    const { nx, ny } = normalizeCoords(pos.x, pos.y)
    const t = dragTool.value
    if (t.type === 'arrow' && draggingPoint.value !== 'move') {
      t.points[draggingPoint.value] = [nx, ny]
    } else if (draggingPoint.value === 'move') {
      const dxn = (pos.x - dragStart.value.x) / displaySize.value.w
      const dyn = (pos.y - dragStart.value.y) / displaySize.value.h
      if (t.type === 'arrow') {
        t.points = [[t.points[0][0] + dxn, t.points[0][1] + dyn], [t.points[1][0] + dxn, t.points[1][1] + dyn]]
      } else if (t.type === 'rect' || t.type === 'circle' || t.type === 'text') {
        if (t.type === 'rect') { t.x += dxn; t.y += dyn }
        else if (t.type === 'circle') { t.cx += dxn; t.cy += dyn }
        else { t.x += dxn; t.y += dyn }
      }
      dragStart.value = pos
    } else if (t.type === 'rect' && draggingPoint.value === 'br') {
      t.w = nx - t.x
      t.h = ny - t.y
    }
    draw()
  }
}

function onMouseUp() {
  if (drawing.value && currentTool.value) {
    const t = currentTool.value
    if (t.type === 'arrow') {
      const p1d = toDisplay(t.points[0][0], t.points[0][1])
      const p2d = toDisplay(t.points[1][0], t.points[1][1])
      if (dist(p1d, p2d) > 5) tools.value.push(t)
    } else if (t.type === 'rect') {
      if (Math.abs(t.w) > 3 && Math.abs(t.h) > 3) {
        if (t.w < 0) { t.x += t.w; t.w = -t.w }
        if (t.h < 0) { t.y += t.h; t.h = -t.h }
        tools.value.push(t)
      }
    } else if (t.type === 'circle') {
      if (t.r > 3) tools.value.push(t)
    }
    currentTool.value = null
    pushHistory()
  }
  drawing.value = false
  dragTool.value = null
  draggingPoint.value = null
}

function drawArrow(ctx, x1, y1, x2, y2, color) {
  const headLen = 14
  const dx = x2 - x1
  const dy = y2 - y1
  const angle = Math.atan2(dy, dx)
  ctx.save()
  ctx.strokeStyle = color
  ctx.fillStyle = color
  ctx.lineWidth = 3
  ctx.lineCap = 'round'
  ctx.beginPath()
  ctx.moveTo(x1, y1)
  ctx.lineTo(x2, y2)
  ctx.stroke()
  ctx.beginPath()
  ctx.moveTo(x2, y2)
  ctx.lineTo(x2 - headLen * Math.cos(angle - Math.PI / 6), y2 - headLen * Math.sin(angle - Math.PI / 6))
  ctx.lineTo(x2 - headLen * Math.cos(angle + Math.PI / 6), y2 - headLen * Math.sin(angle + Math.PI / 6))
  ctx.closePath()
  ctx.fill()
  ctx.restore()
}

function draw() {
  const canvas = canvasRef.value
  if (!canvas || !imgLoaded.value) return
  const ctx = canvas.getContext('2d')
  const dpr = window.devicePixelRatio || 1
  canvas.width = displaySize.value.w * dpr
  canvas.height = displaySize.value.h * dpr
  canvas.style.width = displaySize.value.w + 'px'
  canvas.style.height = displaySize.value.h + 'px'
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.clearRect(0, 0, displaySize.value.w, displaySize.value.h)

  const scale = displaySize.value.w / (naturalSize.value.w || 1)

  const allTools = [...tools.value]
  if (currentTool.value) allTools.push(currentTool.value)

  for (const t of allTools) {
    if (t.type === 'arrow') {
      const p1 = toDisplay(t.points[0][0], t.points[0][1])
      const p2 = toDisplay(t.points[1][0], t.points[1][1])
      drawArrow(ctx, p1.x, p1.y, p2.x, p2.y, t.color)
      if (t.label) {
        ctx.font = 'bold 13px sans-serif'
        const mx = (p1.x + p2.x) / 2
        const my = (p1.y + p2.y) / 2
        const tw = ctx.measureText(t.label).width
        ctx.fillStyle = 'rgba(255,255,255,0.85)'
        ctx.fillRect(mx - tw / 2 - 4, my - 18, tw + 8, 18)
        ctx.fillStyle = t.color
        ctx.fillText(t.label, mx - tw / 2, my - 5)
      }
    } else if (t.type === 'rect') {
      const p = toDisplay(t.x, t.y)
      const wd = t.w * displaySize.value.w
      const hd = t.h * displaySize.value.h
      ctx.strokeStyle = t.color
      ctx.lineWidth = 3
      ctx.strokeRect(p.x, p.y, wd, hd)
      ctx.fillStyle = t.color + '22'
      ctx.fillRect(p.x, p.y, wd, hd)
      if (t.label) {
        ctx.font = 'bold 13px sans-serif'
        ctx.fillStyle = t.color
        ctx.fillText(t.label, p.x + 4, p.y - 4)
      }
    } else if (t.type === 'circle') {
      const c = toDisplay(t.cx, t.cy)
      const rd = t.r * scale
      ctx.strokeStyle = t.color
      ctx.lineWidth = 3
      ctx.beginPath()
      ctx.arc(c.x, c.y, rd, 0, Math.PI * 2)
      ctx.stroke()
      ctx.fillStyle = t.color + '18'
      ctx.fill()
      if (t.label) {
        ctx.font = 'bold 13px sans-serif'
        ctx.fillStyle = t.color
        ctx.fillText(t.label, c.x - rd, c.y - rd - 4)
      }
    } else if (t.type === 'text') {
      const p = toDisplay(t.x, t.y)
      ctx.font = 'bold 14px sans-serif'
      const tw = ctx.measureText(t.text).width
      ctx.fillStyle = 'rgba(255,255,255,0.9)'
      ctx.fillRect(p.x - 4, p.y - 22, tw + 8, 22)
      ctx.strokeStyle = t.color
      ctx.lineWidth = 1.5
      ctx.strokeRect(p.x - 4, p.y - 22, tw + 8, 22)
      ctx.fillStyle = t.color
      ctx.fillText(t.text, p.x, p.y - 6)
    }
  }
}

function onKeyDown(e) {
  if (props.readonly) return
  if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
    e.preventDefault()
    if (e.shiftKey) redo()
    else undo()
    draw()
  }
  if (e.key === 'Delete' || e.key === 'Backspace') {
    if (activeElementIsEditor()) {
      const hit = hitTestFromCurrent()
      if (hit && hit.tool) {
        const idx = tools.value.indexOf(hit.tool)
        if (idx >= 0) {
          tools.value.splice(idx, 1)
          pushHistory()
          draw()
        }
      }
    }
  }
}

function activeElementIsEditor() {
  const ae = document.activeElement
  return !ae || ae.tagName === 'BODY' || containerRef.value?.contains(ae)
}

function hitTestFromCurrent() {
  return null
}

watch(() => props.modelValue, () => draw(), { deep: true })

let ro = null
onMounted(() => {
  window.addEventListener('keydown', onKeyDown)
  window.addEventListener('resize', () => {
    measureDisplay()
    draw()
  })
  if (containerRef.value) {
    ro = new ResizeObserver(() => { measureDisplay(); draw() })
    ro.observe(containerRef.value)
  }
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeyDown)
  if (ro) ro.disconnect()
})

defineExpose({ undo, redo, clearAll })
</script>

<template>
  <div class="annotation-editor" :class="{ readonly }">
    <div class="toolbar" v-if="!readonly">
      <div class="tool-group">
        <button class="tool-btn" :class="{ active: activeTool === 'arrow' }" @click="activeTool = 'arrow'" title="箭头">
          ➡
        </button>
        <button class="tool-btn" :class="{ active: activeTool === 'rect' }" @click="activeTool = 'rect'" title="矩形">
          ▭
        </button>
        <button class="tool-btn" :class="{ active: activeTool === 'circle' }" @click="activeTool = 'circle'" title="圆圈">
          ○
        </button>
        <button class="tool-btn" :class="{ active: activeTool === 'text' }" @click="activeTool = 'text'" title="文字">
          T
        </button>
      </div>
      <div class="tool-sep"></div>
      <div class="tool-group">
        <button v-for="c in COLORS" :key="c" class="color-btn" :class="{ active: activeColor === c }"
          :style="{ background: c }" @click="activeColor = c"></button>
      </div>
      <div class="tool-sep"></div>
      <div class="label-input">
        <input v-model="labelText" placeholder="标注文字（可选）" class="label-field" />
      </div>
      <div class="tool-spacer"></div>
      <div class="tool-group">
        <button class="tool-btn" @click="undo" title="撤销 Ctrl+Z">↶</button>
        <button class="tool-btn" @click="redo" title="重做 Ctrl+Shift+Z">↷</button>
        <button class="tool-btn danger" @click="clearAll" title="清除全部">🗑</button>
      </div>
    </div>
    <div class="canvas-wrap" ref="containerRef" @mousedown="onMouseDown" @mousemove="onMouseMove" @mouseup="onMouseUp" @mouseleave="onMouseUp">
      <img v-if="imageUrl" ref="imgRef" :src="imageUrl" @load="onImgLoad" class="annot-img" :style="{ opacity: imgLoaded ? 1 : 0 }" />
      <canvas ref="canvasRef" class="annot-canvas"></canvas>
      <div v-if="!imageUrl" class="no-image">请先上传图片</div>
    </div>
    <div class="hint-bar" v-if="!readonly">
      💡 选择工具后在图片上拖拽绘制；已有标注可拖拽移动或删除；Ctrl+Z 撤销
    </div>
  </div>
</template>

<style scoped>
.annotation-editor { display: flex; flex-direction: column; height: 100%; }
.toolbar {
  display: flex; align-items: center; gap: 6px; padding: 8px 10px;
  background: #f5f8fd; border: 1px solid #dbe4f0; border-radius: 8px; margin-bottom: 8px;
  flex-wrap: wrap;
}
.tool-group { display: flex; gap: 2px; }
.tool-sep { width: 1px; height: 24px; background: #dbe4f0; margin: 0 4px; }
.tool-spacer { flex: 1; }
.tool-btn {
  width: 32px; height: 32px; border: 1px solid #dfe7f2; background: #fff; border-radius: 6px;
  cursor: pointer; font-size: 14px; display: grid; place-items: center; color: #1e2a3a;
  transition: all .15s;
}
.tool-btn:hover { border-color: #2b7cff; color: #2b7cff; }
.tool-btn.active { background: #2b7cff; color: #fff; border-color: #2b7cff; }
.tool-btn.danger:hover { border-color: #ff4444; color: #ff4444; }
.color-btn {
  width: 22px; height: 22px; border-radius: 50%; border: 2px solid #fff;
  box-shadow: 0 0 0 1px #dfe7f2; cursor: pointer;
}
.color-btn.active { box-shadow: 0 0 0 2px #2b7cff; }
.label-input .label-field {
  width: 160px; height: 30px; padding: 0 10px; border: 1px solid #dfe7f2;
  border-radius: 6px; font-size: 12px; outline: none;
}
.label-input .label-field:focus { border-color: #2b7cff; }

.canvas-wrap {
  flex: 1; position: relative; background: #2a2a2a;
  border-radius: 8px; overflow: hidden; display: flex;
  align-items: center; justify-content: center; min-height: 200px;
  user-select: none;
}
.annot-img { max-width: 100%; max-height: 100%; object-fit: contain; display: block; }
.annot-canvas { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); pointer-events: none; }
.canvas-wrap:not(.readonly) .annot-canvas { pointer-events: none; }

.no-image { color: #888; font-size: 14px; }
.hint-bar {
  font-size: 11px; color: #7b899a; padding: 6px 10px; background: #f7faff;
  border-radius: 0 0 6px 6px; margin-top: 6px;
}
</style>