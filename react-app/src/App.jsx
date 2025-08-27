import React, { useMemo, useState } from "react";
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  arrayMove,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

const COLORS = {
  bgDark: "#0b0f14",
  panel: "#121826",
  neonCyan: "#00E5FF",
  neonMagenta: "#FF00FF",
  neonLime: "#39FF14",
  textLight: "#E6F1FF",
  textDim: "#93a4c3",
  cardBg: "#0e1421",
  cardBorder: "#1f2a44",
};

let nextId = 1;
const makeTask = (text) => ({ id: `t-${nextId++}`, text });

const demoTasks = [
  "Patch proxies to 12.2.18",
  "Prepare AI Steering Committee slides",
  "Finish CrowdStrike DFD",
  "Schedule PCI policy review",
].map(makeTask);

export default function App() {
  const [activeTab, setActiveTab] = useState("tasks"); // 'tasks' | 'completed'
  const [tasks, setTasks] = useState(demoTasks);
  const [completed, setCompleted] = useState([]);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  function handleAdd() {
    const text = window.prompt("Describe the task:");
    if (text && text.trim()) {
      setTasks((prev) => [...prev, makeTask(text.trim())]);
      setActiveTab("tasks");
    }
  }

  function handleComplete(taskId) {
    setTasks((prev) => {
      const idx = prev.findIndex((t) => t.id === taskId);
      if (idx === -1) return prev;
      const t = prev[idx];
      setCompleted((c) => [makeTask(t.text), ...c]);
      return [...prev.slice(0, idx), ...prev.slice(idx + 1)];
    });
    setActiveTab("completed");
  }

  function handleRestore(taskId) {
    setCompleted((prev) => {
      const idx = prev.findIndex((t) => t.id === taskId);
      if (idx === -1) return prev;
      const t = prev[idx];
      setTasks((v) => [...v, makeTask(t.text)]);
      return [...prev.slice(0, idx), ...prev.slice(idx + 1)];
    });
    setActiveTab("tasks");
  }

  function onDragEnd(event) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = tasks.findIndex((t) => t.id === active.id);
    const newIndex = tasks.findIndex((t) => t.id === over.id);
    if (oldIndex === -1 || newIndex === -1) return;
    setTasks((items) => arrayMove(items, oldIndex, newIndex));
  }

  return (
    <div className="h-screen w-full overflow-hidden" style={{ background: COLORS.bgDark, color: COLORS.textLight }}>
      <div className="flex items-center justify-between px-5 py-4 border-b" style={{ borderColor: "#1f2a44" }}>
        <h1 className="text-xl md:text-2xl font-bold tracking-wider select-none"
            style={{ color: COLORS.neonCyan, textShadow: `0 0 12px ${COLORS.neonCyan}55` }}>
          CYBERPUNK TASK LIST
        </h1>
        <button
          onClick={handleAdd}
          className="px-4 py-2 rounded-2xl border text-lg font-bold transition active:scale-95"
          style={{
            background: COLORS.panel,
            borderColor: COLORS.cardBorder,
            boxShadow: `0 0 14px ${COLORS.neonMagenta}66 inset, 0 0 18px ${COLORS.neonCyan}22`,
          }}
          aria-label="Add Task"
          title="Add Task"
        >
          ＋
        </button>
      </div>

      <div className="px-5 pt-4">
        <div className="inline-flex rounded-full overflow-hidden border" style={{ borderColor: COLORS.cardBorder }}>
          <TabButton label="Tasks" active={activeTab === "tasks"} onClick={() => setActiveTab("tasks")} />
          <TabButton label="Completed Items" active={activeTab === "completed"} onClick={() => setActiveTab("completed")} />
        </div>
      </div>

      <div className="p-5 h-[calc(100vh-112px)] overflow-auto" style={{ background: COLORS.panel }}>
        {activeTab === "tasks" ? (
          <TasksPanel
            tasks={tasks}
            sensors={sensors}
            onDragEnd={onDragEnd}
            onComplete={handleComplete}
          />
        ) : (
          <CompletedPanel completed={completed} onRestore={handleRestore} />
        )}
      </div>
    </div>
  );
}

function TabButton({ label, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`px-5 py-2 text-sm md:text-base font-semibold transition ${active ? "" : "opacity-70 hover:opacity-100"}`}
      style={{
        background: active ? COLORS.bgDark : COLORS.panel,
        color: active ? COLORS.neonCyan : COLORS.textLight,
        boxShadow: active ? `0 0 16px ${COLORS.neonCyan}55 inset` : "none",
      }}
    >
      {label}
    </button>
  );
}

function TasksPanel({ tasks, sensors, onDragEnd, onComplete }) {
  const ids = useMemo(() => tasks.map((t) => t.id), [tasks]);
  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
      <SortableContext items={ids} strategy={verticalListSortingStrategy}>
        <div className="grid gap-4">
          {tasks.map((task) => (
            <SortableTaskCard key={task.id} task={task} onComplete={() => onComplete(task.id)} />
          ))}
          {tasks.length === 0 && (
            <EmptyState text="No tasks yet. Smash the ＋ button to add one!" />
          )}
        </div>
      </SortableContext>
    </DndContext>
  );
}

function CompletedPanel({ completed, onRestore }) {
  return (
    <div className="grid gap-4">
      {completed.map((task) => (
        <CompletedCard key={task.id} task={task} onRestore={() => onRestore(task.id)} />
      ))}
      {completed.length === 0 && (
        <EmptyState text="Nothing here... yet. Press '-' on a task to complete it." dim />
      )}
    </div>
  );
}

function EmptyState({ text, dim }) {
  return (
    <div
      className="rounded-2xl p-6 text-center border"
      style={{
        borderColor: COLORS.cardBorder,
        background: COLORS.cardBg,
        color: dim ? COLORS.textDim : COLORS.textLight,
      }}
    >
      {text}
    </div>
  );
}

function SortableTaskCard({ task, onComplete }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: task.id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <TaskCardBase task={task} onComplete={onComplete} dragging={isDragging} />
    </div>
  );
}

function TaskCardBase({ task, onComplete, dragging }) {
  return (
    <div
      className="rounded-2xl border px-4 py-3 md:px-5 md:py-4 cursor-grab active:cursor-grabbing select-none"
      style={{
        background: COLORS.cardBg,
        borderColor: COLORS.cardBorder,
        boxShadow: dragging
          ? `0 0 22px ${COLORS.neonMagenta}88, 0 0 32px ${COLORS.neonCyan}55`
          : `0 0 12px ${COLORS.neonCyan}22 inset`,
      }}
    >
      <div className="flex items-center gap-3">
        <div className="text-xl md:text-2xl leading-none" style={{ color: COLORS.neonCyan }}>≡</div>
        <div className="flex-1 text-sm md:text-base" style={{ color: COLORS.textLight }}>{task.text}</div>
        <button
          onClick={onComplete}
          className="px-3 md:px-4 py-1 rounded-xl border text-lg font-bold transition active:scale-95"
          style={{
            color: COLORS.neonLime,
            background: "#0b1a12",
            borderColor: COLORS.cardBorder,
            boxShadow: `0 0 10px ${COLORS.neonLime}44 inset`,
          }}
          aria-label="Complete task"
          title="Move to Completed Items"
        >
          -
        </button>
      </div>
      <div className="mt-3 h-[2px] w-full" style={{ background: COLORS.neonMagenta, opacity: 0.7 }} />
    </div>
  );
}

function CompletedCard({ task, onRestore }) {
  return (
    <div
      className="rounded-2xl border px-4 py-3 md:px-5 md:py-4 select-none"
      style={{
        background: COLORS.cardBg,
        borderColor: COLORS.cardBorder,
        boxShadow: `0 0 12px ${COLORS.neonLime}33 inset`,
        color: COLORS.textDim,
      }}
    >
      <div className="flex items-center gap-3">
        <div className="text-xl md:text-2xl leading-none" style={{ color: COLORS.neonLime }}>✓</div>
        <div className="flex-1 text-sm md:text-base">{task.text}</div>
        <button
          onClick={onRestore}
          className="px-3 md:px-4 py-1 rounded-xl border text-sm md:text-base transition active:scale-95"
          style={{
            color: COLORS.neonCyan,
            background: COLORS.panel,
            borderColor: COLORS.cardBorder,
          }}
          aria-label="Restore task"
          title="Move back to Tasks"
        >
          Restore
        </button>
      </div>
    </div>
  );
}
