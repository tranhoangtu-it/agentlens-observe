# AgentLens v0.2.0 — Design Guidelines

## Design System Overview

AgentLens uses **shadcn/ui** + **Radix UI** + **Tailwind CSS 3** for a cohesive, dark-mode-first design.

**Core Principles:**
- **Clarity** — Information hierarchy is unambiguous
- **Dark-First** — Optimized for low-light agent monitoring
- **Responsive** — Works on desktop + tablet
- **Accessible** — WCAG 2.1 AA (keyboard nav, contrast ratios)
- **Performance** — CSS variables, no runtime style calculations

## Color Palette

### Semantic Colors (CSS Variables)

```css
/* Primary (Blue) */
--blue-50: #f0f9ff
--blue-600: #2563eb
--blue-700: #1d4ed8

/* Slate (Neutral) */
--slate-900: #0f172a
--slate-800: #1e293b
--slate-700: #334155
--slate-300: #cbd5e1
--slate-100: #f1f5f9

/* Status Colors */
--green-500: #22c55e    /* Completed */
--yellow-500: #eab308   /* Running */
--red-500: #ef4444      /* Error */

/* Semantic (Diff) */
--green-700: #15803d    /* Match */
--blue-700: #1d4ed8     /* Insertion */
--red-700: #b91c1c      /* Deletion */
```

### Theme Variables (Dark Mode)

```css
:root {
  /* Light mode (fallback) */
  --background: white;
  --foreground: #0f172a;
  --card: #f8fafc;
  --muted: #e2e8f0;
}

[data-theme="dark"] {
  --background: #0f172a;      /* slate-900 */
  --foreground: #f1f5f9;      /* slate-100 */
  --card: #1e293b;            /* slate-800 */
  --muted: #334155;           /* slate-700 */
}
```

## Typography

### Font Stack
```css
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  font-size: 14px;
  line-height: 1.5;
}
```

### Scale
- **Heading 1** (h1): 28px, 700 weight, letter-spacing -0.5px
- **Heading 2** (h2): 22px, 600 weight, letter-spacing -0.3px
- **Heading 3** (h3): 18px, 600 weight
- **Body** (p, div): 14px, 400 weight
- **Small** (small, caption): 12px, 400 weight
- **Code** (pre, code): 13px, monospace (Courier New, monospace)

### Usage
```html
<h1>Traces</h1>                    <!-- Page title -->
<h2>Filters</h2>                   <!-- Section title -->
<p>Search agent runs</p>            <!-- Description -->
<small>Last updated 2m ago</small>  <!-- Metadata -->
<code>span.cost_usd</code>           <!-- Code reference -->
```

## Components

### 1. Badge (Status)

```tsx
import { Badge } from "@/components/ui/badge";

// Usage
<Badge variant="default">running</Badge>     /* yellow background */
<Badge variant="secondary">completed</Badge> /* green background */
<Badge variant="destructive">error</Badge>   /* red background */
```

**Styling:** `inline-flex`, padding 4-8px, rounded-full, font-weight 500

### 2. Button

```tsx
import { Button } from "@/components/ui/button";

<Button>Primary</Button>
<Button variant="outline">Secondary</Button>
<Button variant="ghost">Tertiary</Button>
<Button disabled>Disabled</Button>
<Button size="sm">Small</Button>
```

**States:** default, hover, active, disabled, focus (ring outline)

### 3. Card

```tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

<Card className="p-4 bg-card rounded-lg shadow-sm">
  <CardHeader>
    <CardTitle>Trace Details</CardTitle>
  </CardHeader>
  <CardContent>
    {/* Content */}
  </CardContent>
</Card>
```

### 4. Input

```tsx
import { Input } from "@/components/ui/input";

<Input
  type="text"
  placeholder="Search traces..."
  className="bg-slate-900 border-slate-700"
/>
```

**States:** default, focus (blue ring), disabled, error (red border)

### 5. Table

```tsx
import { Table, TableHeader, TableRow, TableCell, TableBody } from "@/components/ui/table";

<Table>
  <TableHeader>
    <TableRow className="border-b border-slate-700">
      <TableCell>Agent</TableCell>
      <TableCell>Status</TableCell>
    </TableRow>
  </TableHeader>
  <TableBody>
    {traces.map(t => (
      <TableRow key={t.id}>
        <TableCell>{t.agent_name}</TableCell>
        <TableCell><Badge variant="secondary">{t.status}</Badge></TableCell>
      </TableRow>
    ))}
  </TableBody>
</Table>
```

### 6. Tooltip

```tsx
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

<Tooltip>
  <TooltipTrigger>?</TooltipTrigger>
  <TooltipContent>Cost breakdown: GPT-4 $0.50, Claude $0.25</TooltipContent>
</Tooltip>
```

### 7. Skeleton (Loading)

```tsx
import { Skeleton } from "@/components/ui/skeleton";

<Skeleton className="h-12 w-full rounded-md" />
<Skeleton className="h-4 w-3/4 mt-2" />
```

### 8. Scroll Area

```tsx
import { ScrollArea } from "@/components/ui/scroll-area";

<ScrollArea className="h-400 border rounded-md">
  {/* Long content */}
</ScrollArea>
```

### 9. Separator

```tsx
import { Separator } from "@/components/ui/separator";

<Separator className="my-4" />
```

## Spacing & Layout

### Spacing Scale
```
xs: 2px    (border widths)
sm: 4px    (tight spacing)
md: 8px    (default padding)
lg: 16px   (section padding)
xl: 32px   (page margins)
2xl: 64px  (hero sections)
```

### Grid System
- **Container:** max-width 1280px, margin auto
- **Sidebar:** 260px fixed width
- **Main:** flex 1, overflow auto

### Common Patterns
```tsx
<div className="space-y-4">          {/* Vertical stack (16px gap) */}
  <div>Item 1</div>
  <div>Item 2</div>
</div>

<div className="flex gap-2">         {/* Horizontal flex */}
  <Button>Action 1</Button>
  <Button variant="ghost">Action 2</Button>
</div>

<div className="grid grid-cols-3 gap-4">  {/* 3-column grid */}
  <Card>Chart 1</Card>
  <Card>Chart 2</Card>
  <Card>Chart 3</Card>
</div>
```

## Pages & Layouts

### 1. Traces List Page

**Layout:**
```
┌─────────────────────────────────────────────────┐
│  Search Bar (full width)                        │
├─────────────────────────────────────────────────┤
│  Filters (status, agent, date, cost)  │ Sort   │
├─────────────────────────────────────────────────┤
│  Virtualized Table (traces)                     │
│  ├─ Agent Name │ Status │ Cost │ Duration      │
│  ├─ Agent Name │ Status │ Cost │ Duration      │
│  └─ ...                                         │
├─────────────────────────────────────────────────┤
│  Pagination (limit, prev, next, page indicator)│
└─────────────────────────────────────────────────┘
```

**Colors:**
- Background: `bg-slate-900`
- Cards: `bg-slate-800`
- Borders: `border-slate-700`
- Text: `text-slate-100`

### 2. Trace Detail Page

**Layout:**
```
┌──────────────────────────────────────────────────┐
│  Trace ID │ Agent │ Status │ Cost │ Duration     │
├─────────────────────┬──────────────────────────┤
│  Topology Graph     │  Span Detail Panel       │
│  (React Flow DAG)   │  ├─ Input               │
│  - Nodes with pulse │  ├─ Output              │
│  - Edges            │  ├─ Cost breakdown      │
│  - Color by status  │  ├─ Duration            │
│                     │  └─ Metadata            │
└─────────────────────┴──────────────────────────┘
```

**Interactive:**
- Click node → Show span detail panel
- Hover node → Highlight parent & children
- Drag canvas → Pan topology
- Scroll → Zoom in/out

### 3. Trace Compare Page

**Layout:**
```
┌────────────────────────────────────────────────────┐
│  Left Trace ID │ Right Trace ID │ Swap │ Export   │
├────────────────────┬───────────────────────────────┤
│  Left Topology      │  Right Topology              │
│  (React Flow)       │  (React Flow)                │
│  - Green: match     │  - Green: match              │
│  - Red: deletion    │  - Blue: insertion           │
│  - Blue: insertion  │                              │
├────────────────────┴───────────────────────────────┤
│  Span Diff Panel (LCS line diff)                   │
│  ├─ Matching spans highlighted                    │
│  ├─ Line-by-line changes                          │
│  └─ JSON diff view                                │
└────────────────────────────────────────────────────┘
```

## Charts & Visualizations

### 1. Cost Summary (Recharts Pie)

```tsx
const data = [
  { name: "GPT-4", value: 0.50, fill: "#2563eb" },
  { name: "Claude", value: 0.25, fill: "#7c3aed" },
  { name: "Gemini", value: 0.15, fill: "#db2777" },
];

<PieChart width={400} height={300}>
  <Pie data={data} dataKey="value" />
  <Legend />
  <Tooltip formatter={(val) => `$${val.toFixed(2)}`} />
</PieChart>
```

### 2. Topology Graph (React Flow)

```tsx
const nodes = spans.map(s => ({
  id: s.id,
  data: { label: s.name },
  position: { x: 0, y: 0 },
  style: {
    background: statusColor(s.status),
    border: "1px solid #334155",
    borderRadius: "4px",
    padding: "10px",
    color: "#f1f5f9",
  },
}));

const edges = spans
  .filter(s => s.parent_id)
  .map(s => ({
    id: `${s.parent_id}-${s.id}`,
    source: s.parent_id,
    target: s.id,
    animated: s.status === "running",
  }));

<ReactFlow nodes={nodes} edges={edges}>
  <Background />
  <Controls />
</ReactFlow>
```

## Animations & Interactions

### 1. Pulse (Running Spans)
```css
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.animate-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
```

### 2. Slide-in (Modal/Panel)
```css
@keyframes slideIn {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}

.animate-slideIn {
  animation: slideIn 0.3s ease-out;
}
```

### 3. Transitions
```css
button {
  transition: background-color 0.2s, box-shadow 0.2s;
}

button:hover {
  background-color: #1d4ed8;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
}
```

## Dark Mode

### Implementation
```tsx
// App.tsx
const [theme, setTheme] = useState<"light" | "dark">("dark");

useEffect(() => {
  const html = document.documentElement;
  html.setAttribute("data-theme", theme);
  html.classList.toggle("dark", theme === "dark");
}, [theme]);

// CSS
:root[data-theme="dark"] {
  --background: #0f172a;
  --foreground: #f1f5f9;
}
```

### Contrast Ratios
- Text on background: 5:1+ (WCAG AA)
- Icons on background: 3:1+ (WCAG AA)
- Interactive elements: 3:1+ focus ring

## Responsive Design

### Breakpoints (Tailwind)
- `sm`: 640px
- `md`: 768px
- `lg`: 1024px
- `xl`: 1280px
- `2xl`: 1536px

### Mobile Optimizations
```tsx
<div className="flex flex-col lg:flex-row">
  <div className="w-full lg:w-1/3">Sidebar</div>
  <div className="flex-1">Main content</div>
</div>
```

## Accessibility

### Keyboard Navigation
- Tab: Focus next interactive element
- Shift+Tab: Focus previous
- Enter: Activate button/link
- Escape: Close modal/dropdown
- Arrow keys: Navigate table rows, dropdowns

### Screen Readers
- Use semantic HTML (button, a, form, etc.)
- Add aria-labels to icon buttons
- Use role="status" for live updates

### Color Contrast
- Text: 4.5:1 ratio minimum (AA)
- UI components: 3:1 ratio (AA)
- Focus indicators: Minimum 2px, 3:1 contrast

## Form Design

### Input Styling
```tsx
<div className="space-y-2">
  <label className="text-sm font-medium">Search</label>
  <Input
    placeholder="Enter agent name..."
    className="border-slate-700 bg-slate-900 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
  />
  <p className="text-xs text-slate-400">Full-text search on agent_name</p>
</div>
```

### Validation
```tsx
<Input
  value={value}
  onChange={handleChange}
  className={cn(error && "border-red-500")}
  aria-invalid={!!error}
/>
{error && <p className="text-xs text-red-500">{error}</p>}
```

## Performance Considerations

- Lazy-load compare page (14KB chunk)
- Virtualized tables (1000+ rows)
- React.memo on expensive components
- Debounce search input (300ms)
- Memoize color functions

## Testing Design

### Visual Regression Testing
- Screenshot comparisons for component changes
- Verify dark mode theme switching
- Check responsive layouts at different breakpoints

### Accessibility Testing
- axe-core for automated checks
- Keyboard navigation testing
- Screen reader testing (NVDA, JAWS)

## Future Enhancements

- Custom color schemes (user preferences)
- High-contrast mode for accessibility
- Light mode toggle
- Customizable themes per organization
